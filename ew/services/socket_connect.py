#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.
# @author: Hirshol Pheir

import os, sys
import threading
import socket
from ew.util import ew_exec, ew_logging
from middleware.middleware_message import MiddlewareMessage, MiddlewareMessageError

logger = ew_logging.getLogger('ew.util.ew_logging')

class SocketWatcher(threading.Thread):

    _socket        = None
    _callback_func = None
    _request_id    = 0

    def open_socket(self, socketname):

        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        if os.path.exists(socketname):
            os.remove(socketname)

        self._csock = self._socket.bind(socketname) # For SOCK_DGRAM this is a default address

        # listen and accept are for socket.SOCK_STREAM
        self._socket.listen(5) # only 1? since we aren't serving many?

        if not self._socket:
            raise Exception('Bad socket type or could not open socket.')

    # ##################################################
    # Register the function to call when messages are received from the socket
    def register_callback(self, func):
        self._callback_func = func

    # ##################################################
    # Thread.start() event
    # Loop forever waiting for messages from the socket.
    def run(self):

        myDsMessage = MiddlewareMessage()

        while (1):

            (clientsocket,addr) = self._socket.accept() #blocking (addr is '' for localsockets)

            if not clientsocket:
                raise Exception('Bad socket type or could not open socket.')

            connected = 1
            while (connected):
                try:
                    msg = myDsMessage.read_from_socket(clientsocket)
                    self._callback_func(msg)

                except MiddlewareMessageError as detail:
                    raise Exception(detail)

                except:
                    connected = 0

# ##################################################
# Inherit from this class to send commands to the socket.
# Maybe we just want to keep the socket open all the time
# since the class sending commands is a singleton.
class SocketSender(object):

    def __init__(self, classcode = None, socketpath = None):
        """Initializes the instance.
        """
        self.nm_socket = None
        self._send_lock = threading.Lock()
        self.mwmsg = MiddlewareMessage()

        self.classcode = classcode
        self.socketpath = socketpath
        self.request_id = 0

        #setup the socket
        self.nm_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self.nm_socket.connect(self.socketpath)
        except:
            logger.exception("Could not open %s socket" % self.socketpath)

    def _send(self,
        op_code,        # Op code integer value
        options=0,      # Option bits as integer
        request_id=0,   # Request ID integer value
        int_args=(),    # Sequence of int argument values integers
        char_args=()):  # Sequence of char argument values as strings

        if request_id == 0:
            self.request_id += 1
            request_id = self.request_id

        message = ((self.classcode << 16 | op_code), options, request_id, int_args, char_args)

        encoded = self.mwmsg.encode(*message)
        decoded = self.mwmsg.decode(encoded)

        with self._send_lock:
            try:
                self.nm_socket.send(encoded)
            except:
                logger.exception("Error sending to socket %s" % self.socketpath)
                raise Exception("Error sending to socket %s" % self.socketpath)

        logger.debug("Message sent to command socket: %s" % str(message))

    def release_socket(self):
        self.nm_socket.close()

