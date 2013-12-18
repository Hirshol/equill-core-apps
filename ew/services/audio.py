#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.

import os
from middleware.middleware_message import MiddlewareMessage as MM
from ew.services.service import Service, startup, shutdown
from ew.util import ew_logging
from ew.util import tablet_config, system_config

logger = ew_logging.getLogger('ew.services.audio')

class AudioService(Service):
    _path = MM.AUDMGR_CMD_SOCKET
    _prefix = 'AUDIO_MANAGER'
    _class_id = MM.AUDIO_SERVICE_CLASS

    @classmethod
    def check_audio_server(cls):
        Service.check_running('audio_server')

    def on_stop(self,callback):
        op = MM.AUDIO_MANAGER_ON_STOP
        self.add_callback(op, callback)

    def on_start(self,callback):
        op = MM.AUDIO_MANAGER_ON_START
        self.add_callback(op, callback)

    def on_volume(self,callback):
        op = MM.AUDIO_MANAGER_ON_VOLUME
        self.add_callback(op, callback)

    def play(self, file_path, volume=50, start_time=0,
            request_id=0, wait=False):
        if not file_path: return False
        op = MM.AUDIO_MANAGER_PLAY
        return self.do_cmd(op, 0, request_id,
            int_args=[volume, start_time],
            char_args=[file_path]
        )

    def record(self, file_path,
            sample_rate=44100, timeout=30, start_time=0, 
            request_id=0, wait=False):
        op = MM.AUDIO_MANAGER_RECORD
        return self.do_cmd(op, 0, request_id,
            int_args=[sample_rate, timeout, start_time],
            char_args=[file_path]
        )

    def stop(self, request_id=0, wait=False):
        op = MM.AUDIO_MANAGER_STOP
        return self.do_cmd(op, 0, request_id, wait)

    def get_volume(self, request_id=0, wait=False):
        op = MM.AUDIO_MANAGER_GET_VOLUME
        return self.do_cmd(op, 0, request_id, wait=wait)

    def set_volume(self, volume, request_id=0, wait=False):
        self.write_volume(volume)
        op = MM.AUDIO_MANAGER_SET_VOLUME
        return self.do_cmd(op, 0, request_id, int_args=[volume], wait=wait)

    def play_audio(self, audio_name=""):
        if self.is_audio_enabled():
            audio_path = os.path.join(system_config.audio_dir, audio_name)
            volume = self.read_volume()
            logger.debug("Trying to play audio file: %r volume: %r", audio_path, volume)
            if os.path.exists(audio_path):
                self.play(audio_path, volume)

    def is_audio_enabled(self):
        """check if audio settings is enabled in tablet.conf"""
        tablet_conf = tablet_config.Config()
        if tablet_conf is not None \
                and tablet_conf.has_section('core_app') \
                and tablet_conf.has_option('core_app','audio'):
            return tablet_conf.get('core_app','audio') == '1'
        return False

    def enable_audio(self):
        """enable audio"""
        tablet_conf = tablet_config.Config()
        if tablet_conf is not None \
                and tablet_conf.has_section('core_app'):
            tablet_conf.set('core_app', 'audio', '1')

    def disable_audio(self):
        """disable audio"""
        tablet_conf = tablet_config.Config()
        if tablet_conf is not None \
                and tablet_conf.has_section('core_app'):
            tablet_conf.set('core_app', 'audio', '0')    

    def write_volume(self, volume):
        """enable audio"""
        tablet_conf = tablet_config.Config()
        if tablet_conf is not None \
                and tablet_conf.has_section('core_app'):
            tablet_conf.set('core_app', 'audio_volume', volume)
            
    def read_volume(self):
        """enable audio"""
        volume = 50
        tablet_conf = tablet_config.Config()
        if tablet_conf is not None \
                and tablet_conf.has_section('core_app'):
            volume = tablet_conf.get('core_app', 'audio_volume', volume)
        return volume
            
    
if __name__ == '__main__':
    # callbacks
    def on_start(*args):
        print 'on_start',args

    def on_stop(*args):
        print 'on_stop',args

    def on_volume(*args):
        print 'on_volume',args

    svc = AudioService()
    svc.on_start(on_start)
    svc.on_stop(on_stop)
    svc.on_volume(on_volume)
    svc.start()

    startup()
    svc.console()
    shutdown()
