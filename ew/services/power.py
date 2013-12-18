#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__.  All rights reserved.

from middleware.middleware_message import MiddlewareMessage as MM
from ew.services.service import Service, startup, shutdown
from ew.util import ew_logging

logger = ew_logging.getLogger('ew.services.power')

class PowerService(Service):
    _path = MM.PWRMGR_CMD_SOCKET
    _prefix = 'POWER_MANAGER'
    _class_id = MM.POWER_MANAGER_CLASS

    def __init__(self, runner=None):
        """Only keep the current network as a field to the class."""
        super(PowerService,self).__init__()
        # Instantiate the object to send socket commands

    @classmethod
    def check_power_manager(cls):
        Service.check_running('power_manager')


    ##########################################
    # register status callbacks
    ##########################################
    def on_power_press(self,callback):
        op = MM.POWER_MANAGER_ON_POWER_PRESS
        self.add_callback(op, callback)

    def on_power_short_release(self, callback):
        op = MM.POWER_MANAGER_ON_POWER_SHORT_RELEASE
        self.add_callback(op, callback)

    def on_power_long_hold(self, callback):
        op = MM.POWER_MANAGER_ON_POWER_LONG_HOLD
        self.add_callback(op, callback)

    def on_battery_warning(self, callback):
        op = MM.POWER_MANAGER_ON_BATTERY_WARNING
        self.add_callback(op, callback)

    def on_fuel_gauge_change(self, callback):
        op = MM.POWER_MANAGER_ON_FUEL_GAUGE_CHANGE
        self.add_callback(op, callback)

    def on_suspend(self, callback):
        op = MM.POWER_MANAGER_ON_SUSPEND
        self.add_callback(op, callback)

    def on_wakeup(self, callback):
        op = MM.POWER_MANAGER_ON_WAKEUP
        self.add_callback(op, callback)

    # ########################################
    # commands
    # ########################################
    def active(self, request_id=0, wait=False):
        op = MM.POWER_MANAGER_ACTIVE
        return self.do_cmd(op, 0, request_id)

    def doze(self, duration=0, request_id=0, wait=False):
        op = MM.POWER_MANAGER_DOZE
        return self.do_cmd(op, 0, request_id, int_args=[duration])

    def getfuel(self, request_id=0, wait=False):
        op = MM.POWER_MANAGER_GETFUEL
        return self.do_cmd(op, 0, request_id, wait=wait)

    def off(self, request_id=0, wait=False):
        op = MM.POWER_MANAGER_OFF
        return self.do_cmd(op, 0, request_id)

    def ready(self, request_id=0, wait=False):
        op = MM.POWER_MANAGER_READY
        return self.do_cmd(op, 0, request_id)

    def sleep(self, duration=0, request_id=0, wait=False):
        op = MM.POWER_MANAGER_SLEEP
        return self.do_cmd(op, 0, request_id, int_args=[duration])

    def can_suspend(self, kind, request_id=0, wait=False):
        op = MM.POWER_MANAGER_CAN_SUSPEND
        return self.do_cmd(op, 0, request_id, char_args=[kind])

if __name__ == '__main__':
    def on_power_press(*args):
        print 'on_power_press',args

    def on_power_short_release(*args):
        print 'on_power_short_release',args

    def on_power_long_hold(*args):
        print 'on_power_long_hold',args

    def on_battery_warning(*args):
        print 'on_battery_warning',args

    def on_fuel_gauge_change(*args):
        print 'on_fuel_gauge_change',args

    def on_suspend(*args):
        print 'on_suspend',args

    def on_wakeup(*args):
        print 'on_wakeup',args

    svc = PowerService()
    svc.on_power_press(on_power_press)
    svc.on_power_short_release(on_power_short_release)
    svc.on_power_long_hold(on_power_long_hold)
    svc.on_battery_warning(on_battery_warning)
    svc.on_fuel_gauge_change(on_fuel_gauge_change)
    svc.on_suspend(on_suspend)
    svc.on_wakeup(on_wakeup)
    svc.start()

    startup()
    svc.console()
    shutdown()
