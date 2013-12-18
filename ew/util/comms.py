#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
#Here are all our communication ports and the what and various server classes
#and Server and Client instance creation functions

from xmlrpclib import ServerProxy, Fault
import SimpleXMLRPCServer
import socket
import SocketServer
import threading
import time
import itertools
import traceback

from ew.util import ew_logging

logger = _logger = ew_logging.getLogger('ew.util.comms')

SYNC_PORT = 8764
DEC_PORT = 8765
INBOX_PORT = 8767  #same as launcher on purpose
LAUNCHER_PORT = 8767
LISTINGS_UPDATER_PORT = 8768
TEMPLATES_PORT = 8767 #same as launcher on purpose
SETTINGS_PORT = 8767  #same as launcher on purpose
DS_INPUT_PORT = 8772

DEFAULT_IP='0.0.0.0'

ServerNames = dict(SYNC_PORT = "Sync", DEC_PORT = "DEC", INBOX_PORT = "Inbox",
                   LAUNCHER_PORT = "Launcher",
                   LISTINGS_UPDATER_PORT = "ListingsUpdater",
                   TEMPLATES_PORT = "Templates", SETTINGS_PORT = "Settings")

Fault_repr_fixed = False

class AsyncXMLRPCServer(SocketServer.ThreadingMixIn,
                        SimpleXMLRPCServer.SimpleXMLRPCServer): pass

def fixed_fault_repr(self):
    return "<Fault %s: %s>" % (self.faultCode, self.faultString)

def ensure_Fault_fix():
    global Fault_repr_fixed
    if not Fault_repr_fixed:
        Fault.__repr__ = fixed_fault_repr
        Fault_repr_fixed = True

class ErrorLoggingXMLRPCServer(AsyncXMLRPCServer):

    def server_name(self):
        port = self.server_address[1]
        return ServerNames.get(port, "Unknown")

    def _dispatch(self, method, params):
        try:
            return  SimpleXMLRPCServer.SimpleXMLRPCDispatcher._dispatch(self, method, params)
        except:
            ensure_Fault_fix()
            trace = traceback.format_exc()
            logger.debug('%s', trace)
            raise Exception('Remote server: %s\n%s' % (self.server_name(), trace))

def create_XMLRPC_server(port, server_class=ErrorLoggingXMLRPCServer,server_ip=DEFAULT_IP):
    server = server_class((server_ip, port), allow_none=True,
        logRequests=False)
    server.register_introspection_functions()
    server.register_function(__nonzero__)
    return server

def __nonzero__():
    return True

class XMLRPCClient(object):
    def __init__(self, port):
        self._client = create_XMLRPC_client('localhost', port)

    def __getattr__(self, name):
        return getattr(self._client, name)


def create_threaded_server(port, **kwargs):
    return create_XMLRPC_server(port, **kwargs)


def create_unthreaded_server(port, **kwargs):
    return create_XMLRPC_server(port,
            server_class=SimpleXMLRPCServer.SimpleXMLRPCServer, **kwargs)



def create_XMLRPC_client(host, port, verbose=False):
    client =  ServerProxy('http://%s:%d' % (host, port), allow_none=True,
            verbose=verbose)
    ensure_Fault_fix()
    return client

def try_until_connected(server_name, connect_function, logger=None,
        try_count=5, retry_interval=1.0):
    """Tries and retries an operation that requires a socket connection.
    Tries "connect_function", catching "connection refused" exception. If
    that exception occurs, the operation will be retried until "try_count"
    attempts have been performed, after which it will propagate the failure.
    Parameters:
      server_name -- The server name to use in logged messages.
      connect_function -- The function to perform a socket operation. The
        function takes no arguments, and its return value is returned as the
        result of this function.
      logger -- Logger of caller, so that log messages will contain the
        caller's identity.
      try_count -- Number of times to try the operation, < 1 (or None) means
        unlimited.
      retry_interval -- Time to wait between trials, in seconds as float.
    """
    if not logger:
        logger = _logger
    t0 = time.time()
    for trial_nbr in (xrange(try_count) if try_count and try_count > 0
            else itertools.count()):
        try:
            connection = connect_function()
            logger.debug('%s connected after %d tries, %.1f seconds',
                    server_name, trial_nbr + 1, time.time() - t0)
            return connection
        except socket.error, ex:
            if ex.errno != 111:
                raise
        logger.debug('Waiting for %s to be ready, trial %d', server_name,
                trial_nbr + 1)
        time.sleep(retry_interval)
    logger.error('Timed out waiting for %s (%s)', server_name, ex)
    raise ex


def create_local_client(port, host=DEFAULT_IP):
    return create_XMLRPC_client(host, port)

def create_sync_client():
    return create_local_client(SYNC_PORT)

def create_LU_client():
    return create_local_client(LISTINGS_UPDATER_PORT)

def create_launcher_client():
    return create_local_client(LAUNCHER_PORT)

def create_DEC_client():
    return create_local_client(DEC_PORT)

class ServerThread(threading.Thread):
    def __init__(self, name, server):
        super(ServerThread, self).__init__(name=name)
        self.server = server
        self.setDaemon(True)

    def run(self):
        try:
            self.server.serve_forever()
        except Exception:
            logger.exception('Error in server thread')
            raise
