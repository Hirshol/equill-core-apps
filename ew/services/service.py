#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.
# @author: Scott Stephens

import os
import readline
import signal
import socket
import subprocess as sub
import sys
import traceback

from threading import Thread,Condition,RLock,Event
from time import sleep,time

from middleware.middleware_message import MiddlewareMessage as MM
from middleware.message import Message, check_opcode
from ew.util import ew_logging

TIMEOUT_RESPONSE = 120       # give up waiting for sync response

logger = ew_logging.getLogger('ew.services.service')

class Service(Thread):
    _path = None
    _prefix = None
    _class_id = None

    def __init__(self):
        super(Service,self).__init__()
        self.daemon = True
        self.finished = Event()
        if self._path is None: raise NotImplementedError('_path')
        if self._prefix is None: raise NotImplementedError('_prefix')
        if self._class_id is None: raise NotImplementedError('_class_id')
        self.sock = None
        self.is_connected = False
        # async callbacks
        self.operations = {}
        # sync responses
        self.response = None
        self.cv = Condition(RLock())

    @classmethod
    def check_running(cls,name):
        # start service if it is not already running
        try:
            with open('/var/run/%s.pid' % name) as f:
                pid = int(f.read().strip())
                os.kill(pid,0)
        except:
            sub.check_call('/etc/init.d/%s.sh start' % name, shell=True)

    def add_callback(self,op_code,callback):
        """add a callback by string or int opcode"""
        op_code = check_opcode(self._prefix,op_code)
        if not self.operations.has_key(op_code):
            self.operations[op_code] = []
        if callback not in self.operations[op_code]:
            self.operations[op_code].append(callback)

    def add_callbacks(self,**kwargs):
        """fancy form: add_callbacks(on_powerup=func1,on_powerdown=func2)"""
        for k,v in kwargs.items():
            self.add_callback(k,v)

    def del_callback(self,op_code,callback):
        op_code = check_opcode(self._prefix,op_code)
        if self.operations.has_key(op_code):
            self.operations[op_code].remove(callback)

    def open(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self._path)
        self.is_connected = True

    def run(self):
        logger.debug("starting listener")
        while not self.finished.is_set():
            if self.sock and self.is_connected:
                try:
                    logger.debug("waiting for message")
                    msg = Message.recv(self.sock)
                    if msg is None:
                        logger.debug("received empty message")
                        raise RuntimeError, "received empty message"
                    logger.debug("handling msg: %r", msg)
                    self.handle_msg(msg)
                except:
                    logger.warn("lost message, closing connection")
                    self.close()
            else:
                # wait for server to come up again
                if os.path.exists(self._path):
                    logger.debug("re-establishing connection to manager")
                    self.open()
                    logger.debug("we're connected to manager")
                self.finished.wait(1)
        logger.debug("\n\nListener exiting %r\n\n", self._path)

    def close(self):
        logger.debug("closing service socket")
        if self.sock:
            self.sock.close()
            self.sock = None
        self.is_connected = False

    def stop(self):
        self.close()
        self.finished.set()

    def handle_msg(self,msg):
        """called whenever manager sends a message to the client"""
        op_code = msg.op_code & 0xffff
        logger.debug("received message: %r", msg)
        if self.operations.has_key(op_code):
            for cb in self.operations[op_code]:
                logger.debug("passing message to callback: %r", cb.func_name)
                cb(*(msg.int_args + msg.char_args))
        # notify sync waiters
        logger.debug("notifying waiters: %r", msg)
        self.cv.acquire()
        logger.debug("listener lock acquired")
        self.response = msg
        self.cv.notify_all()
        self.cv.release()
        logger.debug("listener lock released: %r", msg)

    def do_cmd(self,
            op_code,
            options=0,
            request_id=0,
            int_args = None,
            char_args = None,
            wait = False
        ):
        if not os.path.exists(self._path):
            logger.error("command not sent because control socket is gone")
            return False
        if self.sock is None or not self.is_connected:
            self.open()
            if self.sock is None or not self.is_connected:
                return False
        op_code = check_opcode(self._prefix, op_code)
        op_code |= self._class_id << 16
        if wait and request_id == 0:
            # we must have a unique request id or waiters will conflict
            request_id = Message.new_request_id()
        msg = Message(op_code, options, request_id, int_args, char_args)
        try:
            logger.debug('sending message: %r', msg)
            msg.send(self.sock)
            logger.debug('message sent')
        except:
            # exception, most likely because listener is gone
            logger.exception("got exception while sending message")
            if self.is_connected: self.close()
            return None if wait else False
        if wait:
            logger.debug("waiting for response")
            msg = None
            self.cv.acquire()
            logger.debug("service lock acquired")
            timeout = time() + TIMEOUT_RESPONSE
            while not self.finished.is_set():
                self.cv.wait(2.5)
                if self.response is None: continue
                if self.response.request_id == request_id:
                    msg = self.response
                    break
                if time() > timeout:
                    logger.debug("response not seen in %d secs, timeout"
                        % TIMEOUT_RESPONSE)
                    break
                if isinstance(wait,tuple):
                    if self.response.op_code in wait:
                        msg = self.response
                        break
            self.response = None
            self.cv.release()
            logger.debug("service lock released")
            logger.debug("response received: %r", msg)
            return msg
        return True

    def help(self):
        print "You are now in console mode, enter the following commands:"
        print
        fmt = '%-20s -- %s'
        for n in dir(MM):
            if n.startswith(self._prefix):
                n = n[len(self._prefix+'_'):].lower()
                if n.startswith('on_'): continue        # callback
                fn = getattr(self,n.lower(),None)
                if fn:
                    if fn.func_doc:
                        print fmt % (n,fn.func_doc)
                    else:
                        print n
        print '-------------------'
        print fmt % ("wait", "enable sync commands")
        print fmt % ("nowait", "disable sync commands")
        print fmt % ("log", "log messages to console")
        print fmt % ("nolog", "don't log messages to console")
        print fmt % ("help", "display this menu")
        print fmt % ("host/!","run a shell command")
        print fmt % ("quit", "quit this console and shutdown the test")
        print

    def console(self):
        """
        This is a testing console that is useful for testing commands.
        """
        waiting = False
        if not self.finished.is_set() and not self.is_alive(): self.start()
        self.help()
        while True:
            try:
                line = raw_input('> ')
            except:
                break
            line = line.strip()
            while '  ' in line:
                line = line.replace('  ',' ')
            if line == '': continue
            if line.startswith('!'):
                try:
                    sub.call(line[1:].strip(), shell=True)
                except:
                    print "command failed: %r" % line[1:].strip()
                continue
            if line == 'wait':
                waiting = True
                print 'waiting enabled'
                continue
            if line == 'nowait':
                waiting = False
                print 'waiting disabled'
                continue
            if line == 'log':
                ew_logging.reinitialize(log_stderr=True)
                continue
            if line == 'nolog':
                ew_logging.reinitialize(log_stderr=False)
                continue
            if line == 'help':
                self.help()
                continue
            if line in ('quit','exit'):
                break
            line = line.split(' ')
            if line[0] == 'host':
                if len(line) == 1:
                    print "usage: host <command>"
                else:
                    try:
                        sub.call(line[1:])
                    except:
                        pass
                    continue
            func = getattr(self, line[0], None)
            if func:
                try:
                    if len(line) > 1:
                        for i in range(1,len(line)):
                            line[i] = eval(line[i])
                        rc = func(*line[1:],wait=waiting)
                    else:
                        rc = func(wait=waiting)
                    print 'rc: %r' % rc
                except TypeError, e:
                    traceback.print_exc()
                continue
            print "unrecognized command: %r" % line

def startup():
    logger.debug("installing signal handlers")
    for s in signal.SIGINT, signal.SIGHUP, signal.SIGTERM:
        signal.signal(s, shutdown)

def shutdown(*args):
    pass

if __name__ == '__main__':
    if '-l' in sys.argv:
        ew_logging.reinitialize(log_stderr=True)

    # example Service
    class CmdService(Service):
        _path = '/tmp/cmdctl'
        _prefix = 'NETWORK_MANAGER'
        _class_id = MM.NETWORK_SERVICE_CLASS

        def scan_wifi(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_SCAN_WIFI
            return self.do_cmd(op, 0, request_id, wait=wait)

        def get_conn_info(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_GET_CONN_INFO
            return self.do_cmd(op, 0, request_id, wait=wait)

        def get_settings(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_GET_SETTINGS
            return self.do_cmd(op, 0, request_id, wait=wait)

        def enable_3g(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_ENABLE_3G
            return self.do_cmd(op, 0, request_id)

        def disable_3g(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_DISABLE_3G
            return self.do_cmd(op, 0, request_id)

        def enable_wifi(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_ENABLE_WIFI
            return self.do_cmd(op, 0, request_id)

        def disable_wifi(self, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_DISABLE_WIFI
            return self.do_cmd(op, 0, request_id)

        def set_3g_roaming(self, allow, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_SET_3G_ROAMING
            return self.do_cmd(op, 0, request_id, [allow])

        def want_network(self, want, request_id=0, wait=False):
            op = MM.NETWORK_MANAGER_WANT_NETWORK
            return self.do_cmd(op, 0, request_id, [want], wait=wait)

        def on_wifi_scan_results(self,callback):
            op = MM.NETWORK_MANAGER_ON_WIFI_SCAN_RESULTS
            self.add_callback(op, callback)

        def on_connection_info(self,callback):
            op = MM.NETWORK_MANAGER_ON_CONNECTION_INFO
            self.add_callback(op, callback)

        def on_settings_info(self,callback):
            op = MM.NETWORK_MANAGER_ON_SETTINGS_INFO
            self.add_callback(op, callback)

        def on_connect(self, callback):
            op = MM.NETWORK_MANAGER_ON_CONNECT
            self.add_callback(op, callback)

    # this is what a client does:
    def on_wifi_scan_results(*args):
        print 'on_wifi_scan_results: ',args

    def on_connection_info(*args):
        print 'on_connection_info: ',args

    def on_settings_info(*args):
        print 'on_settings_info: ',args

    def on_connect(*args):
        print 'on_connect: ',args

    svc = CmdService()
    svc.add_callback(MM.NETWORK_MANAGER_ON_CONNECTION_INFO,on_connection_info)
    svc.add_callback('on_settings_info',on_settings_info)
    svc.add_callbacks(on_wifi_scan_results=on_wifi_scan_results)
    svc.start()

    startup()
    svc.console()
    svc.stop()
