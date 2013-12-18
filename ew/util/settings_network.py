#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
"""
@author: Hirshol Pheir
Wrapper for wpa_cli and functions to display and edit wifi info
on the tablet.
@change: Arnold Cabreza
Use ew_logging
Create exec generator utility
"""
from __future__ import with_statement
import os, re
import subprocess as sub
from ew.util import ew_exec, ew_logging


logger = ew_logging.getLogger('ew.util.ew_logging')

class Network:
    """Gather all network data and make available for display
    in tablet settings.
    """

    def __init__(self):
        """Only keep the current network as a field to the class."""
        self.current_network = {}
        # Create wpa_cli method calls that doesn't have output
        for method in ['scan', 'reassociate', 'reconfigure', 'terminate',
                'save_config', 'quit']:
            Network._add_cli_call(method)

    def status(self):
        """Get the status of the configured network."""
        print "--------------------------------------------------"
        print "pinging wpa_supplicant..."
        if not self.ping():
            print "Failed"
            return False

        print "--------------------------------------------------"
        print "checking status..."
        self.current_network = self.get_current_network()
        if not self.current_network:
            print "Failed"
            return False

        print "--------------------------------------------------"
        print "scanning networks..."
        if not self.scan_results():
            print "Failed"
            return False

        print "--------------------------------------------------"
        print "END"
        print "--------------------------------------------------"

    def add_network(self, ssid, password):
        """Add a given network to the known list."""
        try:
            if not os.path.exists('/data/etc/wpa_supplicant.conf'):
                logger.error("Cannot find /data/etc/wpa_supplicant.conf file")
                return - 1

            with open('/data/etc/wpa_supplicant.conf') as f:
                s = f.read()

            # ##################################################
            # Delete any instances of the SSID that's going to be added
            rxstr = '^network=\{\s*ssid="%s"[^}]*[}]' % ssid
            regex = re.compile(rxstr, re.I | re.M)
            s = regex.sub('', s)

            # ##################################################
            # Next, generate the entry
            cmd = "echo %s | wpa_passphrase '%s'" % (password, ssid)
            p = sub.Popen(cmd, shell = True, stdout = sub.PIPE, stderr = sub.PIPE)

            output, error = p.communicate()

            logger.debug("error::%s" % (error))
            logger.debug("output::%s" % (output))

            s = s + output

            with open('/data/etc/wpa_supplicant.conf', 'w') as f:
                f.write(s)

            # Force wpa_supplicant to re-read its config file
            self.reconfigure()
        except:
            logger.exception("Exception error caught in add_network()")

    def set_network(self, id):
        """Activate id as the current network."""
        try:
            command_line = "wpa_cli select_network %d" % id
            for line in ew_exec.command_output(command_line,
                    stdout = sub.PIPE, stderr = sub.PIPE, close_fds=True):
                if line.find('OK') > 0:
                    return True
        except sub.CalledProcessError, e:
            logger.exception(e)
        return False

    def ping(self):
        """Ping wpa supplicant
        Return true if running, false if not.
        """
        try:
            command_line = "wpa_cli ping"
            for line in ew_exec.command_output(command_line,
                    stdout = sub.PIPE, stderr = sub.PIPE, close_fds=True):
                if line.find('PONG') > 0:
                    return True
        except sub.CalledProcessError, e:
            logger.exception(e)
        return False

    def get_current_network(self):
        """Return a dictionary of the currently active network
        keyed by ssid
        """
        network_status = {}
        try:
            command_line = "wpa_cli status"
            for line in ew_exec.command_output(command_line,
                    stdout = sub.PIPE, stderr = sub.PIPE, close_fds=True):
                fields = line.split()
                if line.find('=') >= 0:
                    rec = line.split('=')
                    network_status[rec[0]] = rec[1].strip()
        except sub.CalledProcessError, e:
            logger.exception(e)
        return network_status

    def scan_results(self):
        """Scan for available networks. One or more dictionary
        keyed by ssid.
        """
        available_networks = {}
        try:
            known_networks = self.list_networks()
            command_line = "wpa_cli scan_results"
            for line in ew_exec.command_output(command_line,
                    stdout = sub.PIPE, stderr = sub.PIPE, close_fds=True):
                # Use the ssid as the key
                if line.find('Selected interface') >= 0 or \
                        line.find('bssid') >= 0:
                    continue
                net = {}
                fields = line.strip().split()
                if len(fields) == 5:
                    ssid = fields[4]
                    net['bssid'] = fields[0]
                    net['frequency'] = fields[1]
                    net['signal_level'] = fields[2]
                    net['flags'] = fields[3]
                    net['ssid'] = ssid
                    net['connected'] = None
                    net['known'] = False
                    if ssid in known_networks:
                        net['known'] = True
                        current_network = self.get_current_network()
                        known_entry = known_networks.get(ssid)
                        if len(known_entry) == 4 and \
                                known_entry[3] == "[CURRENT]":
                            net['connected'] = current_network['wpa_state']
                    available_networks[ssid] = net
                else:
                    logger.warning("Invalid wpa scan_results line: %r", line)
        except sub.CalledProcessError, e:
            logger.exception(e)
        return available_networks

    def list_networks(self):
        """Return a dictionary of known networks keyed by ssid."""
        known_networks = {}
        try:
            command_line = "wpa_cli list_networks"
            for line in ew_exec.command_output(command_line,
                    stdout = sub.PIPE, stderr = sub.PIPE, close_fds=True):
                # Use the ssid as the key
                fields = line.split()
                if len(fields) > 1:
                    known_networks[fields[1]] = fields
        except sub.CalledProcessError, e:
            logger.exception(e)
        return known_networks

    @classmethod
    def _add_cli_call(cls, method):
        """Add a wpa_cli call with no output as a method to this class."""
        try:
            getattr(cls, method)
        except AttributeError:
            def _wpa_cli(self):
                try:
                    command_line = "wpa_cli %s" % method
                    ew_exec.run_command(command_line)
                except sub.CalledProcessError, e:
                    logger.exception(e)
            _wpa_cli.__doc__ = "cli_method %s" % method
            _wpa_cli.__name__ = "%s" % method
            setattr(cls, _wpa_cli.__name__, _wpa_cli)
