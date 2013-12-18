#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__.  All rights reserved.

import threading
import subprocess as sub

from middleware.middleware_message import MiddlewareMessage as MM
from ew.services.service import Service, startup, shutdown
from ew.util import tablet_config, ew_exec, ew_logging

logger = ew_logging.getLogger('ew.services.network')

class NetworkService(Service):
    _path = MM.NETMGR_CMD_SOCKET
    _prefix = 'NETWORK_MANAGER'
    _class_id = MM.NETWORK_SERVICE_CLASS

    @classmethod
    def check_network_manager(cls):
        Service.check_running('network_manager')

    def __init__(self):
        super(NetworkService,self).__init__()
        self.on_location(self.keep_location)
        self.tablet_conf = None

        self.tablet_conf = tablet_config.Config()
        self.synchronize()

    ####################################################
    # commands
    ####################################################
    def scan_wifi(self, request_id=0, wait=False):
        """initiate wifi scan"""
        op = MM.NETWORK_MANAGER_SCAN_WIFI
        return self.do_cmd(op, 0, request_id, wait=wait)

    def get_conn_info(self, request_id=0, wait=False):
        """request current connection info"""
        op = MM.NETWORK_MANAGER_GET_CONN_INFO
        return self.do_cmd(op, 0, request_id, wait=wait)

    def add_suppl_entry(self, ssid, password, key_type='WPA',
            hidden=False, request_id=0, wait=False):
        """add a given nework to the password list"""
        op = MM.NETWORK_MANAGER_ADD_SUPPL_ENTRY
        return self.do_cmd(op, 0, request_id,
            int_args=[int(hidden)],
            char_args=[ssid,password,key_type])

    def rm_suppl_entry(self, ssid, request_id=0, wait=False):
        """remove a given network from the password list"""
        op = MM.NETWORK_MANAGER_RM_SUPPL_ENTRY
        return self.do_cmd(op, 0, request_id, char_args=[ssid])

    def get_settings(self, request_id=0, wait=False):
        """request wifi settings"""
        op = MM.NETWORK_MANAGER_GET_SETTINGS
        return self.do_cmd(op, 0, request_id, wait=wait)

    def enable_3g(self, request_id=0, wait=False):
        """turn on 3g"""
        if self.is_airplane_mode(): return False
        op = MM.NETWORK_MANAGER_ENABLE_3G
        return self.do_cmd(op, 0, request_id)

    def disable_3g(self, request_id=0, wait=False):
        """disable 3g network connection"""
        op = MM.NETWORK_MANAGER_DISABLE_3G
        return self.do_cmd(op, 0, request_id)

    def enable_wifi(self, request_id=0, wait=False):
        """allow wifi network connections"""
        if self.is_airplane_mode(): return False
        self.tablet_conf.set('core_app', 'wifi', 1)
        op = MM.NETWORK_MANAGER_ENABLE_WIFI
        return self.do_cmd(op, 0, request_id)

    def disable_wifi(self, request_id=0, wait=False):
        """disallow wifi network connections"""
        self.tablet_conf.set('core_app', 'wifi', 0)
        op = MM.NETWORK_MANAGER_DISABLE_WIFI
        return self.do_cmd(op, 0, request_id)

    def wifi_reconfigure(self, request_id=0, wait=False):
        """initiate wpa_supplicate reconfigure"""
        op = MM.NETWORK_MANAGER_WIFI_RECONFIGURE
        return self.do_cmd(op, 0, request_id)

    def set_3g_roaming(self, allow, request_id=0, wait=False):
        """enable/disable 3g roaming"""
        op = MM.NETWORK_MANAGER_SET_3G_ROAMING
        return self.do_cmd(op, 0, request_id, [allow])

    def want_network(self, want, request_id=0, wait=False):
        op = MM.NETWORK_MANAGER_WANT_NETWORK
        return self.do_cmd(op, 0, request_id, int_args=[want], wait=wait)

    def rfkill(self, request_id=0, wait=False):
        """turn off fusion"""
        op = MM.NETWORK_MANAGER_RFKILL
        return self.do_cmd(op, 0, request_id)

    def get_3g_conf(self, request_id=0, wait=False):
        """get 3g configuration"""
        op = MM.NETWORK_MANAGER_GET_3G_CONF
        return self.do_cmd(op, 0, request_id, wait=wait)

    def sledgehammer(self, request_id=0, wait=False):
        """send sledgehammer command to reset fusion to factory defaults"""
        op = MM.NETWORK_MANAGER_SLEDGEHAMMER
        return self.do_cmd(op, 0, request_id)

    def get_location(self, request_id=0, wait=False):
        """get last known location of tablet"""
        op = MM.NETWORK_MANAGER_GET_LOCATION
        return self.do_cmd(op, 0, request_id)

    def want_gps(self, want, interval, request_id=0, wait=False):
        """enable GPS polling"""
        int_args = [int(want), interval]
        logger.debug('want_gps:%r' % int_args)
        op = MM.NETWORK_MANAGER_WANT_GPS
        return self.do_cmd(op, 0, request_id, int_args=int_args)

    def get_ipaddress(self, request_id=0, wait=False):
        """get current ip address of connected interface"""
        op = MM.NETWORK_MANAGER_GET_IPADDRESS
        return self.do_cmd(op, 0, request_id, wait=wait)

    ####################################################
    # register status callbacks
    ####################################################
    def on_wifi_scan_results(self, callback):
        op = MM.NETWORK_MANAGER_ON_WIFI_SCAN_RESULTS
        self.add_callback(op, callback)

    def on_connection_info(self, callback):
        op = MM.NETWORK_MANAGER_ON_CONNECTION_INFO
        self.add_callback(op, callback)

    def on_settings_info(self,callback):
        op = MM.NETWORK_MANAGER_ON_SETTINGS_INFO
        self.add_callback(op, callback)

    def on_3g_conf(self, callback):
        op = MM.NETWORK_MANAGER_ON_3G_CONF
        self.add_callback(op, callback)

    def on_location(self, callback):
        op = MM.NETWORK_MANAGER_ON_LOCATION
        self.add_callback(op, callback)

    def on_connect(self, callback):
        op = MM.NETWORK_MANAGER_ON_CONNECT
        self.add_callback(op, callback)

    def on_timeout(self, callback):
        op = MM.NETWORK_MANAGER_ON_TIMEOUT
        self.add_callback(op, callback)

    def on_ipaddress(self, callback):
        op = MM.NETWORK_MANAGER_ON_IPADDRESS
        self.add_callback(op, callback)

    def on_disconnect(self, callback):
        op = MM.NETWORK_MANAGER_ON_DISCONNECT
        self.add_callback(op, callback)

    def keep_location(self, *args):
        """native callback"""
        pass
        #if self.tablet_conf is not None:
        #    if self.tablet_conf.has_section('core_app'):
        #        self.tablet_conf.set('core_app','location',','.join(args))

    ####################################################
    # utility commands, (these should be moved somewhere else)
    ####################################################
    def is_3g_enabled(self):
        """check if 3g is enabled in tablet.conf"""
        if not self.tablet_conf.has_section('parameters'): return False
        return self.tablet_conf.getboolean('parameters','three_g')

    def is_3g_roaming(self):
        """check if 3g roaming is enabled in tablet.conf"""
        if not self.tablet_conf.has_section('parameters'): return False
        return self.tablet_conf.getboolean('parameters','three_g_roaming')

    def is_gps_enabled(self):
        """check if gps is enabled in tablet.conf"""
        if not self.tablet_conf.has_section('parameters'): return False
        return self.tablet_conf.getboolean('parameters','gps')

    def get_gps_interval(self):
        """return gps interval setting from tablet.conf"""
        if not self.tablet_conf.has_section('parameters'): return False
        return int(self.tablet_conf.get('parameters','gps_interval') or 300)

    def is_wifi_enabled(self):
        """check if wifi is enabled in tablet.conf"""
        if not self.tablet_conf.has_section('core_app'): return True
        return self.tablet_conf.getboolean('core_app','wifi')

    def is_airplane_mode(self):
        """check if airplane mode is enabled in tablet.conf"""
        if not self.tablet_conf.has_section('core_app'): return False
        return self.tablet_conf.getboolean('core_app','airplane')

    def wants_gps(self):
        """check if GPS is enabled"""
        if not self.tablet_conf.has_section('parameters'): return False
        return self.tablet_conf.getboolean('parameters','gps')

    def synchronize(self,wait=False):
        """synchronize with tablet.conf"""
        logger.debug("Synchronizing networking...")
        if self.tablet_conf is None: return
        with self.tablet_conf.read_lock() as config:
            if self.is_airplane_mode():
                self.enable_airplane_mode(wait=wait)
            else:
                if self.is_wifi_enabled():
                    self.enable_wifi(wait=wait)
                else:
                    self.disable_wifi(wait=wait)
                if self.is_3g_enabled():
                    self.enable_3g(wait=wait)
                else:
                    self.disable_3g(wait=wait)
                if self.is_gps_enabled():
                    self.want_gps(True,self.get_gps_interval())
                else:
                    self.want_gps(False,0)

    def on(self, request_id=0, wait=False):
        """turn on network request"""
        return self.want_network(True, request_id, wait=wait)

    def off(self, request_id=0, wait=False):
        """turn off network request"""
        return self.want_network(False, request_id, wait=wait)

    def toggle_connection(self):
        """restart 3g"""
        self.off()
        self.on()

    def enable_airplane_mode(self, request_id=0, wait=False):
        """go into airplane mode"""
        self.tablet_conf.set('core_app', 'airplane', '1')
        self.rfkill(wait=wait)

    def disable_airplane_mode(self, request_id=0, wait=False):
        """exit airplane mode"""
        self.tablet_conf.set('core_app', 'airplane', '0')
        self.tablet_conf.set('core_app', 'wifi', '1')
        self.synchronize(wait=wait)

    def list_networks(self):
        """return a dictionary of known networks keyed by ssid"""
        known_networks = {}
        try:
            command_line = 'wpa_cli list_networks'
            for line in ew_exec.command_output(command_line,
                    stdout=sub.PIPE, stderr=sub.PIPE, close_fds=True):
                fields = line.split()
                if len(fields) > 1:
                    known_networks[fields[1]] = fields
        except sub.CalledProcessError, e:
            logger.exception(e)
        return known_networks

    def set_network(self, id):
        """activate id as the current network."""
        try:
            command_line = 'wpa_cli select_network %d' % id
            for line in ew_exec.command_output(command_line,
                    stdout=sub.PIPE, stderr=sub.PIPE, close_fds=True):
                if line.find('OK') > -1:
                    return True
        except sub.CalledProcessError, e:
            logger.exceptione(e)
        return False

def get_network(timeout):
    svc = NetworkService()
    svc.start()

    def on_timer(svc):
        svc.stop()      # make listener stop listening
        svc = None

    timer = threading.Timer(timeout, on_timer,(svc,))
    timer.start()
    msg = svc.want_network(True,wait=(
        MM.NETWORK_MANAGER_ON_CONNECT,
    ))
    timer.cancel()
    if msg:
        msg = svc.get_ipaddress(wait=True)
    if svc: svc.stop()
    return msg.char_args[0] if msg else ''

if __name__ == '__main__':
    def on_wifi_scan_results(*args):
        print 'on_wifi_scan_results',args

    def on_connection_info(*args):
        print 'on_connection_info',args

    def on_settings_info(*args):
        print 'on_settings_info',args

    def on_3g_conf(*args):
        print 'on_3g_conf',args

    def on_location(*args):
        print 'on_location',args

    def on_connect(*args):
        print 'on_connect',args

    def on_timeout(*args):
        print 'on_timeout',args

    def on_ipaddress(*args):
        print 'on_ipaddress',args

    def on_disconnect(*args):
        print 'on_disconnect',args

    svc = NetworkService()
    svc.on_wifi_scan_results(on_wifi_scan_results)
    svc.on_connection_info(on_connection_info)
    svc.on_settings_info(on_settings_info)
    svc.on_3g_conf(on_3g_conf)
    svc.on_location(on_location)
    svc.on_ipaddress(on_ipaddress)
    svc.on_disconnect(on_disconnect)
    svc.start()

    startup()
    svc.console()
    shutdown()
