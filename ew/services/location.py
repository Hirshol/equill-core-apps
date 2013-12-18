#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.

from middleware.middleware_message import MiddlewareMessage as MM
from ew.services.service import Service, startup, shutdown
from ew.util.ew_logging import getLogger

logger = getLogger('ew.services.location')

class LocationService(Service):
    _path = MM.LOCMGR_CMD_SOCKET
    _prefix = 'LOCATION_MANAGER'
    _class_id = MM.LOCATION_SERVICE_CLASS

    @classmethod
    def check_location_manager(cls):
        Service.check_running('location_manager')

    ##########################################
    # register status callbacks
    ##########################################
    def on_location(self,callback):
        op = MM.LOCATION_MANAGER_ON_LOCATION
        self.add_callback(op, callback)

    ##########################################
    # commands
    ##########################################
    def determine_location(self, timeout=30, request_id=0, wait=False):
        """request a location from the location manager"""
        op = MM.LOCATION_MANAGER_DETERMINE_LOCATION
        return self.do_cmd(op, 0, request_id, [timeout], wait=wait)

if __name__ == '__main__':
    def on_location(*args):
        print 'on_location',args

    svc = LocationService()
    svc.on_location(on_location)
    svc.start()
    
    startup()
    svc.console()
    shutdown()
