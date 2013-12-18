#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.

"""Launcher code related to the camera server"""

import socket, threading, time

from ew.util import ew_logging

from ew.util.ew_binary_message import EwBinaryMessage

logger = ew_logging.getLogger('ew.launcher.camera_server')

CAM_MAGIC = 0x141C0140

# Camera socket addresses
CAMERA_SOCKET = "/var/run/camera"

def _enum(start, n): return xrange(start, start + n)

# Camera function opcodes
(
    CAMERA_COMMAND_START_PREVIEW,
    CAMERA_COMMAND_STOP_PREVIEW,
) = _enum(1, 2)

# Camera event opcodes
(
    CAM_STATUS_INVALID_COMMAND,
    CAM_STATUS_PREVIEW_STARTED,
    CAM_STATUS_PREVIEW_FAILED,
    CAM_STATUS_PREVIEW_STOPPED,
    CAM_STATUS_HAVE_IMAGE,
    CAM_STATUS_CANNOT_WRITE_IMAGE,
    CAM_STATUS_SHUTTER,
) = _enum(128, 7)

# Event opcodes client -> server
CAM_OPTION_REPORT_ONLY_ERROR = 1
CAM_OPTION_TAKE_SNAPSHOT     = 2  # for CAMERA_COMMAND_START_PREVIEW

# Event opcodes server -> client
CAM_OPTION_PREVIEW_ACTIVE    = 8


class CsFunctionMessage(EwBinaryMessage):
    """Message for function calls to server (client -> server)"""

    __slots__ = ()

    def __init__(self):
        EwBinaryMessage.__init__(self, magic_number=CAM_MAGIC, endian='@',
                option_bit_values=dict(
                    report_only_error = CAM_OPTION_REPORT_ONLY_ERROR,
                    take_snapshot = CAM_OPTION_TAKE_SNAPSHOT,
                )
        )

# Message and options objects for function calls to server (client -> server)
function_message = CsFunctionMessage()
function_options = function_message.options_factory


class CsEventMessage(EwBinaryMessage):
    """Message for event calls from server (server -> client)"""

    __slots__ = ()

    def __init__(self):
        EwBinaryMessage.__init__(self, magic_number=CAM_MAGIC, endian='@',
                option_bit_values=dict(
                    preview_active = CAM_OPTION_PREVIEW_ACTIVE,
                )
        )

# Message and options objects for event calls from server (server -> client)
event_message = CsEventMessage()
event_options = event_message.options_factory


# Table of event op codes vs. listener method names for events that fit the
# common signature of taking only the following arguments:
#   - options
#   - request_id
#   - report_error_only
function_for_0_arg_event = {
    CAM_STATUS_INVALID_COMMAND: 'on_invalid_command',
    CAM_STATUS_PREVIEW_STARTED: 'on_preview_started',
    CAM_STATUS_PREVIEW_FAILED: 'on_preview_failed',
    CAM_STATUS_PREVIEW_STOPPED: 'on_preview_stopped',
    CAM_STATUS_CANNOT_WRITE_IMAGE: 'on_cannot_write_image',
    CAM_STATUS_SHUTTER: 'on_shutter',
}


camera_file = None
lock = threading.Lock()


def ensure_camera_socket(local_socket_address):
    """Create the camera socket if not already created."""
    global camera_file
    retry_max = 5
    retry_count = 0
    while retry_count < retry_max:
        try:
            with lock:
                if camera_file is None:
                    camera_socket = socket.socket(socket.AF_UNIX, 
                            socket.SOCK_STREAM)
                    addr = local_socket_address or CAMERA_SOCKET
                    camera_socket.connect(addr)
                    camera_file = camera_socket.makefile()
                    logger.debug('Camera server connected via socket %r', addr)
        except Exception, e:
            logger.error("Failed to connect to camera server.. retrying.") 
        if camera_file is None:
            logger.debug("Failed to obtain camera connection. Attempt: %r", 
                    retry_count)
            retry_count += 1
            time.sleep(3)
        else:
            logger.debug("Got camera server connection")
            break
    if camera_file is None:
        raise Exception("Failed to connect to camera server after %r attempts.",
                retry_count)


class CameraSender(object):
    """Contains methods representing camera server commands."""

    def __init__(self, local_socket_address=None):
        """Initialize this instance.

        Parameters:
          local_socket_address   Allows specification of a socket
              address other than the default.

        """
        self._camera_available = False
        try:
            ensure_camera_socket(local_socket_address)
            self._camera_available = True
        except Exception, e:
            logger.error('Camera sender failed to connect to server: %r', e)

    def camera_start_preview(self, request_id, report_only_error=False,
            take_snapshot=False):
        """Start camera preview mode."""
        if not self._camera_available: return
        self._write(request_id, function_message.encode(
                CAMERA_COMMAND_START_PREVIEW,
                function_options.int_from_keyword_args(
                    report_only_error=report_only_error,
                    take_snapshot=take_snapshot
                ),
                request_id))

    camera_start_preview.opcode = CAMERA_COMMAND_START_PREVIEW

    def camera_stop_preview(self, request_id, report_only_error=False):
        """Stop camera preview mode."""
        if not self._camera_available: return
        self._write(request_id, function_message.encode(
                CAMERA_COMMAND_STOP_PREVIEW,
                function_options.int_from_keyword_args(
                    report_only_error=report_only_error
                ),
                request_id))

    camera_stop_preview.opcode = CAMERA_COMMAND_STOP_PREVIEW

    def _write(self, request_id, message):
        """Private -- write a command message to the camera server."""
        if not request_id:
            raise ValueError('Request ID 0 is not allowed')
        camera_file.write(message)
        camera_file.flush()


class CameraListener(object):
    """Calls methods to handle camera server events."""

    def __init__(self, listener, local_socket_address=None):
        """Initialize an instance.

        Parameters:
          listener  The object containing event functions.
          local_socket_address   Allows specification of a socket
              address other than the default.

        """
        self.listener = listener
        self.local_socket_address = local_socket_address

    def run(self):
        """Read events from the camera server and invoke listener methods."""
        try:
            try:
                ensure_camera_socket(self.local_socket_address)
            except Exception, e:
                logger.error("Camera event listener failed"
                        " to connect to the server: %r", e)
                return

            # Loop to read event messages.
            while 1:
                message = event_message.read_from_stream(camera_file)
                if message is None:
                    break
                event_code = message.op_code
                options = message.options.options_int
                request_id = message.request_id

                # Dispatch "on_have_image" event.
                if event_code == CAM_STATUS_HAVE_IMAGE:
                    func = getattr(self.listener, 'on_have_image', None)
                    if func:
                        image_path = message.char_args[0]
                        func(options, request_id, image_path)
                else:

                    # Handle several common events that fit a specific
                    # signature. See table "function_for_0_arg_event"
                    # in this module for event names.
                    func_name = function_for_0_arg_event.get(event_code)
                    if func_name:
                        func = getattr(self.listener, func_name, None)
                        if func:
                            func(options, request_id)
                    else:
                        logger.warn('Unknown event ID received: %r', event_code)
        except:
            logger.exception('Error in camera listener')
        logger.error('End of file on camera server event stream.')
