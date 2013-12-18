#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2011 Ricoh Innovations, Inc.
# ##################################################
# Tablet getty restricting serial/usb gadget access
# enabling only the following actions:
#   - Provisioning
#   - Retrieving Logs
#   - Setting wifi nodes
#   - diagnostic utils
#
# @author: Hirshol Pheir, Steve Savitzky
#
# ##################################################

import os, sys
import subprocess
import exceptions
import shlex
import signal
import ConfigParser

from optparse import OptionParser
from ew.util import tablet_config
config = tablet_config.Config()

class ExitException(exceptions.BaseException):
    """"exit" command is given to the shell."""
    pass
class UsageException(exceptions.BaseException):
    """print usage"""
    pass

class FailureException(exceptions.BaseException):
    """provisioning failed"""
    pass

class SIGINTException(exceptions.BaseException):
    """SIGINT has been received."""
    pass

class provShell:
    """A primitive interactive shell."""

    def __init__(self):
        """Initializes shell."""
        signal.signal(signal.SIGINT, self.sigint_handler)

        # get the build identifier (as a line of text ended with \n)
        p = subprocess.Popen('echo -e `cat /etc/issue` | head -1', 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = p.communicate()
        self.buildId = output
       
    def run(self):
        """Starts the infinite loop for receiving input
        until one of the exceptions is raised.
        """
        while(True):
            try:
                args = shlex.split(raw_input("EWS eQuill> "))

                if not len(args) > 0:
                    continue

                if args[0] == "exit":
                    raise ExitException
                elif args[0] == "help":
                    self.help(args)
                elif args[0] == "provision":
                    self.provision(args)
                elif args[0] == "calibrate":
                    self.calibrate(args)
                elif args[0] == "showlog":    # Note: Deliberately obscured feature, not in help
                    self.showlog(args)
                else:
                    print "Invalid command"

            except IndexError:
                continue

            except EOFError:
                print "<EOF received>"
                return 0

            except ExitException:
                print "<exit called>"
                return 0

            except SIGINTException:
                print >> sys.stderr, \
                    "<SIGINT received, logged and reported>"
                return 1

    def sigint_handler(self, signum, frame):
        """Handler for the SIGINT signal."""
        raise SIGINTException

    def tabletIsProvisioned(self):
        try:
            if config.is_provisioned():
                return True
        except:
            return False
        return False

    def showlog(self, args):
        """display specified log files."""
        try:
            import glob
            # first arg - api key
            args=args[1:]
            api_key = args[0]
            # next set of args - glob matches to select files in /data/logs
            args=args[1:]
            # Secured by account's API Key
            if self.auth_api_key(api_key):
                for arg in args:
                    logfiles = glob.glob('/data/logs/' + arg)
                    for log in logfiles:
                        print '< ==================== cut here ==================== > %s' % log
                        fh = open(log,'r')
                        lines = fh.readlines()
                        fh.close()
                        sys.stdout.writelines(lines)
            else:
                print 'Not authorized'
        except:
            print 'showlog exception ... sorry'

    def auth_api_key(self, api_key):
        """compare given api key with the one placed in tablet.conf during provisioning"""
        try:
            # Note: for some reason, during this config.get call, the following junk gets printed:
            # <ew.util.tablet_config.AugmentedConfigParser instance at 0x404fc5a8> <type 'instance'>
            configured_api_key = config.get('sync','api_key')
            if configured_api_key == None:
                return False
            if configured_api_key == api_key:
                return True
            return False
        except:
            print 'auth_api_key exception ... sorry'
            return False

    def provision(self, args):
        try:

            # Replace the provision command with the path to provision.py

            # flags for various possible argument combinations
            try_wifi      = False
            try_calibrate = False
            try_login     = False
            try_provision = False
            try_audit     = False
            debug	  = False

            #parser = OptionParser(usage=self.provisionUsage)
            parser = OptionParser()
            parser.add_option("-i", "--inbox", dest="inbox")
            parser.add_option("-a", "--account", dest="account")
            parser.add_option("-K", "--api_key", dest="api_key")
            parser.add_option("-u", "--user", dest="user")
            parser.add_option("-p", "--password", dest="password")
            parser.add_option("-s", "--wifi_ssid", dest="wifi_ssid")
            parser.add_option("-t", "--wifi_type", dest="wifi_type")
            parser.add_option("-w", "--wifi_password", dest="wifi_password")
            parser.add_option("-d", "--wifi_wipe", dest="wifi_wipe", action="store_true")
            parser.add_option("-c", "--calibrate", dest="calibrate", action="store_true")
            parser.add_option("-A", "--audit", dest="audit", action="store_true")
            parser.add_option("-D", "--debug", dest="debug", action="store_true")

            args=args[1:]

            (options, args) = parser.parse_args(args)

            if len(args) != 0:
                print "!!! ERROR !!! args too long"
                raise UsageException

            # ss.FIXME need to worry about wipe, login; possible future commands

            if options.calibrate == True:
                try_calibrate = True

            if options.audit == True:
                try_audit = True

            if options.wifi_ssid <> None:
                try_wifi = True

#            if options.inbox <> None or options.account <> None:
#                if self.tabletIsProvisioned() == True:
#                    if config.get('sync', 'ssh_host') == options.inbox:
#                        # If the tablet is already provisioned to the correct inbox,
#                        # don't mess with it.
#                        try_provision = False
#                    else:
#                        # Otherwise, it's an error, because we're locked.
#                        print "!!! ERROR !!! Tablet already provisioned."
#                        raise FailureException
#                        try_provision = True
#                else:
#                    try_provision = True

            try_provision = True
            # If we want to provision and anything is missing, fail
#            if try_provision == True:
#                if options.inbox == None:
#                    print "!!! ERROR !!! missing inbox option"
#                    raise FailureException
#                if options.account == None :
#                    print "!!! ERROR !!! missing account option"
#                    raise FailureException
#                if options.user <> None and options.password == None:
#                    print "!!! ERROR !!! missing user password option"
#                    raise FailureException

            args.append("python")
            args.append("/usr/local/bin/provision.py")

            if try_provision == True:
                if options.inbox <> None:
                    args.append("-i")
                    args.append(options.inbox)
                if options.account <> None:
                    args.append("-a")
                    args.append(options.account)

            if options.user <> None:
                args.append("-u")
                args.append(options.user)
            if options.password <> None:
                args.append("-p")
                args.append(options.password)
            if options.wifi_ssid <> None:
                args.append("-s")
                args.append(options.wifi_ssid)
            if options.wifi_type <> None:
                args.append("-t")
                args.append(options.wifi_type)
            if options.wifi_password <> None:
                args.append("-w")
                args.append(options.wifi_password)
            if (options.calibrate == True):
                args.append("-c")
            if (options.audit == True):
                args.append("-A")
            if (options.wifi_wipe == True):
                args.append("-d")
            if options.api_key <> None:
                args.append("-K")
                args.append(options.api_key)
            if options.debug:
                args.append("-D")

            try:
                subprocess.Popen(args,
                    stdin = sys.stdin,
                    stdout = sys.stdout,
                    stderr = sys.stderr)

            except OSError, e:
                print e
                raise e


        except UsageException, e:
            print e
            print self.provisionUsage

        except FailureException, e:
            print e

    def calibrate(self):
        pass

    def help(self, args):
        if len(args) == 1:

            print """
This serial port only accepts parameters for provisioning
a tablet.  Please use the Ricoh EWS Provisioning Tool or the
command line parameters if you would like to provision a tablet.
Type "help provision" for more detail.

Available commands:

    help      - brings up this message
    provision - provisions a tablet, type "help provision" for more detail

Build identifier:

    %s
""" % self.buildId
        elif len(args) > 1:
            if args[1] == "provision":
                self.printHelpProvision()
            elif args[1] == "calibrate":
                print self.printHelpCalibrate()
            else:
                print "no entry"


    provisionUsage="""Provision Tool

NAME
        provision [OPTION]...

DESCRIPTION

        Provisions a tablet to a named inbox server and account. Tablets that
        have already been provisioned must be unlocked by your administrator
        before they can be re-provisioned.

        -i, --inbox=INBOX (required)
            specify the inbox hostname by IP Address or hostname
            (xxx.ricohcloud.com)

        -a, --account=ACCOUNT (required)
            the 6 or 8 digit account identifier provided by your service host

        -u, --user=USER (optional)
            inbox account user

        -p, --password=PASSWORD (required with -u)
            the user's password

        -s, --wifi_ssid=SSID (optional)
            the ssid of a wifi node to connect to if no tablet connections
            already exist

        -t, --wifi_type=TYPE (optional)
            the authorization type of the ssid wifi node.  Default WPA2;
            choices are Open, WPA2, and WEP.

        -w, --wifi_password=PASSWORD (optional)
            the WPA password or WEP hex key for the ssid wifi node.  
            If omitted, the type is assumed to be Open.

        -d, --wifi_wipe (optional)
            wipes the current wifi configuration file

        -c, --calibrate (optional)
            calibrate the tablet after provisioning

        -A, --audit (optional)
            audit the tablet's configuration

USAGE
        coming soon...

Examples
        coming soon...

"""

    def printHelpProvision(self):
        print self.provisionUsage

    def printHelpCalibrate(self):
        print """Pen Calibration Tool

NAME
        calibrate

DESCRIPTION
        Calibrates the pen (stylus) to your tablet.

USAGE
        Click on the points as they appear on the screen.

"""

if __name__ == "__main__":
    sys.exit(provShell().run())
