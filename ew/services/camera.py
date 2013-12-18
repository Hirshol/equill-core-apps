#!/usr/bin/env python
from __future__ import with_statement
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.

import time, threading, os
from ew.launcher import camera_server
from ew.util import ew_logging
from ew.util.lock import ExclusiveLock, LockUnavailableError
if not os.getenv('emulate_tablet'):
    from ew.services.audio import AudioService

logger = ew_logging.getLogger('ew.services.camera')


class Camera(object):
    """Class to wrap system camera functionality. Centralizes use of camera from various
    modules, camera_server, document, and widget. This class is a singleton and only one item
    can own the camera at a time.. either an ImageDrop widget or the Document itself.
    ImageDrop use:
        -can be bound to metadata
        -can be positioned/overlayed on a form
        -keeps images on the page level metadata
    Document use:
        -attaches images as a page on the document
    """
    _request_id   = 0
    _instance_lock = threading.RLock()
    _instance = None

    @classmethod
    def instance(cls, client=None):
        with cls._instance_lock:
            if not cls._instance:
                cls(client)
            return cls._instance

    def __init__(self, client=None):
        with self._instance_lock:
            if self._instance:
                raise RuntimeError(
                        "Additional instances of singleton class %r should"
                        " not be created -- use '%s.instance()' method" %
                        ((self.__class__.__name__,) * 2))
            self.__class__._instance = self
            self.cs = camera_server.CameraSender()
            self._connect_to_camera_events()
            self._streaming = False
            self._client = client
            self.cam_lock = "/tmp/camera_server.lck"
            if not os.path.exists(self.cam_lock):
                with open(self.cam_lock, 'w') as f:
                    f.write("")
            self._camera_lock = ExclusiveLock(self.cam_lock)

    def _camera_start_preview(self, *args, **kwargs):
        if args and isinstance(args[-1],dict) and not kwargs:
            kwargs = args[-1]
            args = args[:-1]
        logger.debug('Delegating camera_start_preview'
                '(*args=%r, **kwargs=%r)', args, kwargs)
        return self.cs.camera_start_preview(*args, **kwargs)

    def _camera_stop_preview(self, *args, **kwargs):
        if args and isinstance(args[-1],dict) and not kwargs:
            kwargs = args[-1]
            args = args[:-1]
        logger.debug('Delegating camera_stop_preview'
                '(*args=%r, **kwargs=%r)', args, kwargs)
        return self.cs.camera_stop_preview(*args, **kwargs)

    def _request_id(self):
        request_id = id(self)
        if self._client is not None:
            request_id = id(self._client)
        return request_id

    def _connect_to_camera_events(self):
        """Private - start the listener for camera server events."""

        class CameraServerListener(threading.Thread):

            def __init__(self):
                super(CameraServerListener, self).__init__(
                        name='camera server listener')

            def run(self):
                camera_server.CameraListener(self).run()

            def on_have_image(self, options, request_id, image_path):
                logger.debug('on_have_image: options: %r, request_id=%r,'
                        ' image_path=%r',
                        options, request_id, image_path)
                logger.debug("camera.event on_have_image: %r %r", image_path, request_id)
                camera_instance = Camera.instance()
                if camera_instance.create_blocking_event():
                    AudioService().play_audio("camera.wav")
                    camera_instance.forward_event("on_have_image", image_path)
                else:
                    logger.debug("Couldn't copy image to client.")
                camera_instance.clear_blocking_event()    
                camera_instance.set_client(None)
                camera_instance.set_streaming(False)

            def on_invalid_command(self, options, request_id):
                logger.debug('on_invalid_command: options: %r, request_id=%r',
                        options, request_id)

            def on_preview_started(self, options, request_id):
                logger.debug('on_preview_started: options: %r, request_id=%r',
                        options, request_id)
                AudioService().play_audio("camera_on.wav")
                camera_instance = Camera.instance()
                camera_instance.clear_blocking_event()
                camera_instance.set_streaming(True)

            def on_preview_failed(self, options, request_id):
                logger.debug('on_preview_failed: options: %r, request_id=%r',
                        options, request_id)
                camera_instance = Camera.instance()
                camera_instance.clear_blocking_event()
                camera_instance.set_streaming(False)

            def on_preview_stopped(self, options, request_id):
                logger.debug('on_preview_stopped: options: %r, request_id=%r',
                        options, request_id)
                camera_instance = Camera.instance()
                camera_instance.clear_blocking_event()                
                camera_instance.set_client(None)
                camera_instance.set_streaming(False)

            def on_cannot_write_image(self, options, request_id):
                logger.debug('on_preview_stopped: options: %r, request_id=%r',
                        options, request_id)

            def on_shutter(self, options, request_id):
                logger.debug('on_shutter: options: %r, request_id=%r',
                        options, request_id)
                logger.debug("camera.event on_shutter: %r %r", options, request_id)
                camera_instance = Camera.instance()
                if camera_instance.create_blocking_event():
                    camera_instance.forward_event("on_shutter")
                else:
                    logger.debug("Couldn't acquire camera.")

        # Start the thread.
        cs_event_thread = CameraServerListener()
        cs_event_thread.setDaemon(True)
        cs_event_thread.start()
        logger.info('Camera server event listener thread started')
        time.sleep(1.0)

    def forward_event(self, event, *args, **kwargs):
        try:
            if self._client is not None and getattr(self._client, event):
                event_method = getattr(self._client, event)
                event_method(*args, **kwargs)
            else:
                logger.debug("No client for camera event, dropping event.")
        except Exception, e:
            logger.debug("Exception forwarding camera event: %r", e)

    def create_blocking_event(self):
        status = False
        try:
            self._camera_lock.acquire()
            if self._camera_lock.acquired:
                status = True
        except LockUnavailableError, e:
            logger.debug("Exception getting camera lock %r", e)
            status = False
        return status

    def clear_blocking_event(self):
        if self._camera_lock.acquired:
            self._camera_lock.release()
            
    def on(self, widget=None):
        """Turn on OLED for camera streaming.
        """
        if widget is not None:
            self._client = widget
        logger.debug("Streaming: %r", self._streaming)
        if not self._streaming:
            self._camera_start_preview(self._request_id(),
                    dict(report_only_error=False, take_snapshot=True))

    def off(self):
        """Turn off OLED.
        """
        if self._streaming:
            self._camera_stop_preview(self._request_id())
            self._streaming = False

    def get_client(self):
        return self._client

    def set_client(self, widget):
        if widget is not None:
            self._client = widget
        else:
            self.off()

    def is_streaming(self):
        return self._streaming

    def set_streaming(self, streaming):
        self._streaming = streaming