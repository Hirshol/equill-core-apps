#!/usr/bin/python
from __future__ import with_statement
# Copyright 2011 Ricoh Innovations, Inc.
#
# This module provisions a tablet from the tablet, and
# should work by being called from The Provisionator,
# or by a future QR Code mechanism.
#

import os, sys
import urllib
import time
import subprocess as sub
import re
import json
import socket
import logging
from ew.services import network
from optparse import OptionParser
from ew.util import tablet_config
from ew.util.lock import ExclusiveLock, LockUnavailableError

# ##################################################
# Setup statics
DIR_HOME     = os.environ["HOME"]
LOG_FILENAME = '/data/logs/provision.log'

# ##################################################
# Start logging
if os.path.exists(LOG_FILENAME):
    os.remove(LOG_FILENAME)

formatter   = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
logger      = logging.getLogger('ProvisionLogger')
handler     = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

# ##################################################
# Setup config
config = tablet_config.Config()

class provision():
    
    def __init__(self):
        # ##################################################
        # Instantiate some vars
        self.response       = {}
        self.serial_no_file = "serialno.txt"
        self.public_key     = ""
        self.fingerprint    = ""
        self.api_key        = ""
        self.config_wifi    = False
        self.try_provision  = False
        self.try_login      = False
        self.try_calibrate  = False
        self.try_audit      = False
        self.try_min        = False

        # ##################################################
        # Set up and grab our command line options
        usage = ""
        parser = OptionParser(usage)
        parser.add_option("-i", "--inbox", dest="inbox")
        parser.add_option("-a", "--account", dest="account")
        parser.add_option("-u", "--user", dest="user")
        parser.add_option("-p", "--password", dest="password")
        parser.add_option("-s", "--wifi_ssid", dest="wifi_ssid")
        parser.add_option("-t", "--wifi_type", dest="wifi_type")
        parser.add_option("-w", "--wifi_password", dest="wifi_password")
        parser.add_option("-d", "--wifi_wipe", dest="wifi_wipe", action="store_true")
        parser.add_option("-c", "--calibrate", dest="calibrate", action="store_true")
        parser.add_option("-A", "--audit", dest="audit", action="store_true")
        parser.add_option("-D", "--debug", dest="debug", action="store_true")
#        parser.add_option("-K", "--api_key", dest="api_key", default="1234567890")

        (options, args) = parser.parse_args()
        self.options    = options

        # ##################################################
        # From options, determine which elements to run

        if self.options.wifi_ssid <> None:
            self.config_wifi = True
            self.try_min = True
            
        if self.options.inbox <> None and self.options.account <> None:
            self.try_provision = True
            self.try_min = True

        if self.options.user <> None and self.options.password <> None:
            self.try_login = True
            self.try_min = True

        if self.options.calibrate == True:
            self.try_calibrate = True
            self.try_min = True

        # We never actually look at try_audit; it gets done automagically in post()
        if self.options.audit == True:
            self.try_audit == True

        # Set log level to INFO unless the -D (--debug) option was passed
        if self.options.debug == True:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        
        self._init_calibrate_lock()

    def _init_calibrate_lock(self):
        self._calibrate_lock = "/tmp/provision_calibrate.lck"
        if not os.path.exists(self._calibrate_lock):
            with open(self._calibrate_lock, 'w') as f:
                f.write("")
        self.calibrate_lock = ExclusiveLock(self._calibrate_lock)

    def start(self):

        self.need_restart = False
        self.need_login = True
        
        if self.pre() == -1:
            self.fail("failed to configure environment")

        if self.config_wifi == True:
            self.configureWifi()

        if self.getSerialNo() == -1:
            self.fail("Could not get serial number")
            
        if self.try_provision == True:

            # note that establishWifi is only needed if we're provisioning
            if self.establishWifi() == -1:
                self.fail("Could not establish WiFi connection")

            if self.writeFiles() == -1:
                self.fail("Could not write tablet configuration file")

            if self.setCurrentVersion() == -1:
                self.fail("Could not determine current build version")

            if self.pingInboxServer() == -1:
                self.fail("Could not contact inbox server")

            if self.addServerToKnownHosts() == -1:
                self.fail("Could not add server to known hosts")

            if self.genPubKey() == -1:
                self.fail("Could not generate public key")

            if self.getPubKey() == -1:
                self.fail("Could not get public key")

            if self.getFingerprint() == -1:
                self.fail("Could not get fingerprint")

            if self.getMacAddr() == -1:
                self.fail("Could not get Mac Address")

            if self.getMEID() == -1:
                self.fail("Could not get MEID")

            if self.provision() == -1:
                self.fail("Failed to provision")

        if not self.try_min:
            logger.info("[!] provide at least one parameter")
            return -1

        if self.try_login == True:
            if self.login() == -1:
                self.need_login = True
                self.fail("Failed to login")
            else:
                self.need_login = False
                
            
        if self.try_calibrate:
            try:
                with self.calibrate_lock:
                    if not self.is_calibrate_running():
                        self.calibrate()
            except LockUnavailableError, e:
                logger.debug("Could not get calibration lock %r", e)

        self.post()

        return

    # ##################################################
    # If we get a fail anywhere, add the error messages
    # and exit.
    def fail(self, msg=""):
        logger.error("-----------------------------------------------------")
        logger.error("!!! ERROR !!! %s" % msg)
        logger.error("-----------------------------------------------------")

        sys.exit('Error: %s' % msg)

    # ##################################################
    # If we get a warning anywhere, add the error messages
    # but don't exit.
    def warn(self, msg):
        logger.error("-----------------------------------------------------")
        logger.error("!!! WARNING !!! %s" % msg)
        logger.error("-----------------------------------------------------")

    # ##################################################
    # Verify fields
    def pre(self):
        logger.debug("Configuring environment...")

        logger.debug("Home: %s" % (DIR_HOME))

        # ##################################################
        # Add the /data/etc directory if necessary.
        # we can take this out once dirs are in the build
        # (or in the skeleton tar to be extracted).
        dirs = ('/data/etc', '/data/.ssh')
        for dir in dirs:
            if not os.path.exists(dir):
                try:
                    logger.debug("Creating %s..." % dir)
                    p = sub.Popen('/bin/mkdir %s' % dir, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
                    output, error = p.communicate()

                    logger.debug("error::%s" % (error))
                    logger.debug("output::%s" % (output))

                except:
                    logger.exception("Error adding %s. (Exception)" % dir)

    # ##################################################
    # Tests to see if the tablet has inet connection
    def establishWifi(self):
        
        # ##################################################
        # Now, search ifconfig for an IP address on wlan(0|?)
        # Try it a few times in case the wifi is acting up.
        try:
            logger.info("[ ] Searching for a WiFi connection...")
            self.ip = network.get_network(60)
            
            if len(self.ip) > 0:
                logger.info("[*] Established WiFi connection. IP Address: %s." % (self.ip))
                return 1
            else:
                logger.info("[X] Could not establish a WiFi connection.")
                return -1
            
        except:
            logger.exception("Exception caught establishing a Wifi connection. (Exception)")
            return -1

    # ##################################################
    # Set up the wifi
    def configureWifi(self):
        # ##################################################
        # Before we ADD a new wifi node, delete existing SSID(s) from wpa_supplicant.conf
        try:

            if not len(self.options.wifi_ssid) > 1:
                logger.error("WiFi SSID too short.")
                return -1
            
            # ##################################################
            # If we're starting wifi from scratch
            if self.options.wifi_wipe == True:
                logger.debug("Resetting wpa_supplicant.conf file...")
                cmd = "echo '# wpa_supplicant file reset by provisioner\nap_scan=1\nctrl_interface=/var/run/wpa_supplicant\n' > /data/etc/wpa_supplicant.conf"
                p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)

                output, error = p.communicate()
    
                logger.debug("error::%s" % (error))
                logger.debug("output::%s" % (output))
                logger.info("[*] Wiped old WiFi information")

            if not os.path.exists('/data/etc/wpa_supplicant.conf'):
                with open('/data/etc/wpa_supplicant.conf', 'w') as f:
                    s = '# wpa_supplicant created by provisioner\n'
                    f.write(s)

            with open('/data/etc/wpa_supplicant.conf') as f:
                s = f.read()

            # ##################################################
            # Make sure that the wpa_supplicant file has the lines:
            #   ctrl_interface=/var/run/wpa_supplicant
            #   ap_scan=1

            if not s.find('ap_scan=1') >= 0:
                s = 'ap_scan=1\n' + s

            if not s.find('ctrl_interface=/var/run/wpa_supplicant') >= 0:
                s = 'ctrl_interface=/var/run/wpa_supplicant\n' + s

            # ##################################################
            # Delete any instances of the SSID that's going to be set

            # Note that characters that might cause trouble in the regex aren't
            # allowed in SSIDs:  ?, ", $, [, \, ], and +
            rxstr = '^network=\{\s*ssid="%s"[^}]*[}]' % self.options.wifi_ssid
            regex = re.compile(rxstr, re.I | re.M)

            s = regex.sub('', s)

            # ##################################################
            # append the new network stanza.

            logger.debug("Adding ssid entry to wpa_supplicant...")
            # steve@rii.ricoh.com: need -single- double quotes around passphrase and ssid
            # Note that the following characters are not allowed:   ?, ", $, [, \, ], and +
            # (this needs to move when we fix EPTSSH-167)
            if self.options.wifi_password == None:
                s = s + """
network={
        ssid="%s"
        key_mgmt=NONE
}
""" % self.options.wifi_ssid
            elif self.options.wifi_type == "WEP":
                s = s + """
network={
        ssid="%s"
        key_mgmt=NONE
	wep_key0=%s
	wep_tx_keyidx=0
}
""" % (self.options.wifi_ssid, self.options.wifi_password)
            else:
                cmd = ['/usr/bin/wpa_passphrase', self.options.wifi_ssid, self.options.wifi_password]
                p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE)

                output, error = p.communicate()

                logger.debug("error::%s" % (error))
                logger.debug("output::%s" % (output))

                if len(error) > 0:
                    return -1

                s = s + output

            # ##################################################
            # Delete the pesky automated comments
            rxstr = '^# reading[^\n]*\n'
            regex = re.compile(rxstr, re.I | re.M)

            s = regex.sub('', s)

            # ##################################################
            # Write the wpa_supplicant file back to disk
            with open('/data/etc/wpa_supplicant.conf', 'w') as f:
                f.write(s)
            # === do we need to close here, or does the with handle it?

            logger.info("[*] wrote WiFi configuration entry for SSID=%s" % self.options.wifi_ssid)

        except:
            logger.exception("Error editing wpa_supplicant.conf. (Exception)")
            return -1

        # ##################################################
        # tell wpa_supplicant that the config file has changed.
        try:
            logger.debug("Configuring WiFi...")

            logger.debug("Calling wpa_helper.sh...")
            cmd = "/usr/local/bin/wpa_helper.sh"
            p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)

            output, error = p.communicate()

            logger.debug("error::%s" % (error))
            logger.debug("output::%s" % (output))

            if len(error) > 0:
                return -1

            logger.debug("Calling wpa_cli reconfigure...")
            cmd = "/sbin/wpa_cli reconfigure"
            p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)

            output, error = p.communicate()

            logger.debug("error::%s" % (error))
            logger.debug("output::%s" % (output))

            if len(error) > 0:
                return -1

            # ##################################################
            # We assume that wpa_cli is running... Should we
            # do a down and up here?

            logger.info("[*] Configured WiFi for SSID=%s" % self.options.wifi_ssid)

        except:
            logger.exception("Error configuring wifi. (Exception)")
            return -1

    # ##################################################
    # Write the tablet.conf file
    def writeFiles(self):
        try:
            logger.debug("Creating tablet.conf file...")
            with open('/data/etc/tablet.conf', 'w') as f:
                f.write(self.getTabletConfFile())
            logger.info("[*] Wrote tablet config file.")
        except:
            logger.exception("Error creating tablet.conf file. (Exception)")
            return -1

    # ##################################################
    # Write the wpa_supplicant.conf and tablet.conf files
    def setCurrentVersion(self):
        # ##################################################
        # We can also parse the manifest and put the new version
        # number in the tablet.conf file.  This will be passed
        # as an argument for versioning.
        self.fp_manifest = "/MANIFEST.TXT"

        with open(self.fp_manifest) as f:
            for line in f.readlines():
                if line.find('build_identifier') > 0:
                    regex = re.compile('^.*rootfs_([^+]*)[+]', re.I | re.M)
                    result = regex.match(line)
                    version = result.group(1)
                    if len(version) > 0:
                        sub.Popen("echo '%s' > /data/etc/version.txt" % version, shell=True)

        # Set the config file version
        try:
            config.set('sync', 'tablet_version', version)
        except:
            logger.exception("Exception caught setting current build version")
    
    # ##################################################
    # Do a DNS lookup on the inbox server and make sure port 80 is open.
    # Try 3 times in case the lookup times out.
    def pingInboxServer(self):
        count = 1
        while count < 4:
            try:
                logger.info("[ ] getting address for inbox server %s, try %s..." % (self.options.inbox, count))
                inbxsrv = socket.getaddrinfo(self.options.inbox, 80, 0, 0, socket.SOL_TCP)
                # get the IP address
                m   = re.search("[0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}", str(inbxsrv))
                self.inbox_ip = m.group(0)
                logger.info("[*] got address for inbox server at %s" % self.inbox_ip)
                return 0
            except:
                count = count + 1

        logger.error("[X] failed to get address for inbox server %s" % self.options.inbox)
        return -1

    # ##################################################
    # Add the Inbox Server to known hosts
    def addServerToKnownHosts(self):
        try:
            logger.debug("Adding Inbox Server public id_rsa file to known_hosts file...")
            p = sub.Popen('/usr/bin/ssh-keyscan %s' % self.options.inbox, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            out, error = p.communicate()

            logger.debug("error::%s" % (error))
            
            # Set port 2077
            id1a = out
            id1b = out.replace(self.options.inbox, "[%s]:2077" % self.options.inbox)
            
            logger.debug("Added key::%s" % (id1a))
            logger.debug("Added key::%s" % (id1b))
            
            p = sub.Popen('/usr/bin/ssh-keyscan %s' % self.inbox_ip, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            out, error = p.communicate()

            logger.debug("error::%s" % (error))
            logger.debug("output::%s" % (out))
            
            id2a = out
            id2b = out.replace(self.inbox_ip, "[%s]:2077" % self.inbox_ip)
            
            logger.debug("Added key::%s" % (id2a))
            logger.debug("Added key::%s" % (id2b))

            logger.info("[*] Retrieved inbox server's public key")
            
        except:
            logger.exception("Error adding Inbox Server to known_hosts file. (Exception)")
            return -1

        try:
            with open("/data/.ssh/known_hosts", "w") as f:
                f.write(id1a + id1b + id2a + id2b)
            logger.info("[*] Stored inbox server's public key")
                
        except:
            logger.exception("Error writing to known_hosts file. (Exception)")
            return -1

        logger.debug("Inbox Server added to /data/.ssh/known_hosts file.")

    # ##################################################
    # Generate the Public Key files if necessary
    def genPubKey(self):
        try:
            logger.info("[ ] generating public ssh key")

            if os.path.exists("/data/.ssh/id_rsa"):
                p = sub.Popen("/bin/rm /data/.ssh/id*", stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
                output, error = p.communicate()
                
            p = sub.Popen(["/usr/bin/ssh-keygen", "-N", "", "-f", "/data/.ssh/id_rsa"], stdout=sub.PIPE, stderr=sub.PIPE)
            output, errors = p.communicate()

            if len(errors) > 0:
                logger.error("Error executing 'ssh-keygen'.")
                return -1

        except:
            logger.exception("Error executing 'ssh-keygen'. (Exception)")
            return -1

        logger.info("[*] generated public ssh key")
        return 1

    # ##################################################
    # Get necessary Inbox Server params (fingerprint, public_key)
    # To get the public_key, just read the file
    def getPubKey(self):
        try:
            logger.debug("Getting Public Key...")
            f = open("/data/.ssh/id_rsa.pub")
            self.public_key = f.read()
        except:
            logger.exception("Error opening '/data/.ssh/id_rsa.pub'. (Exception)")
            return -1

        logger.debug("Public Key read.")
        return 1

    # ##################################################
    # To get the fingerprint, use ssh-keygen
    def getFingerprint(self):
        try:
            logger.debug("Generating fingerprint from id_rsa.")
            p = sub.Popen(["/usr/bin/ssh-keygen", "-l", "-f", "/data/.ssh/id_rsa.pub"], stdout=sub.PIPE, stderr=sub.PIPE)
            output, errors = p.communicate()

            if len(errors) > 0:
                logger.error("Error executing 'ssh-keygen' to get fingerprint.")
                return -1

        except:
            logger.exception("Error executing 'ssh-keygen' to get fingerprint. (Exception)")
            return -1

        # Parse output to get fingerprint
        try:
            output = output.split()
            self.fingerprint = output[1]
        except:
            logger.exception("Error parsing output to get fingerprint. (Exception)")
            return -1

        logger.debug("Fingerprint: %s" % (self.fingerprint))
        return 1

    # ##################################################
    # For the time being, we're going to use the MAC address
    # until we write something to get the serial_no from the tablet.
    def getMacAddr(self):
        try:
            logger.debug("Retrieving MAC Address...")
            p = sub.Popen(["/sbin/ifconfig"], stdout=sub.PIPE, stderr=sub.PIPE)
            output, errors = p.communicate()

            if len(errors) > 0:
                logger.error("Error calling '/sbin/ifconfig'.")
                return -1

        except:
            logger.exception("Error calling '/sbin/ifconfig'. (Exception)")
            return -1

        try:
            lines = output.splitlines()

            for line in lines:
                if line.find("Ether") > -1:
                    mac = line.split()
                    break

            self.mac_addr = mac[4]
        except:
            logger.exception("Error parsing ifconfig to get HWaddr for serial_no. (Exception)")
            return -1

        self.hardware_id = self.mac_addr

        logger.debug("MAC Address: %s" % (self.mac_addr))

        return 1

    # ##################################################
    # get the tablet's serial number
    def getSerialNo(self):

        path_nvram = "/nvram"
        start_num  = 0
        max_num    = 12

        logger.debug("Getting Serial No...")

        try:
            while 1:
                if start_num > max_num:
                    logger.error("Exceeded count checking nvram directories for serial_no.txt.  Using Mac Address as Serial No.")
                    self.serial_no = self.mac_addr
                    # We can exit gracefully and just use the mac addr as serial no.
                    return 1

                path = path_nvram + str(start_num)
                logger.debug("Checking in %s..." % path)

                npath = "%s/%s" % (path, self.serial_no_file)

                if os.path.exists(npath):
                    break
                else:
                    start_num += 1
                    continue

            f = open(npath)
            fc = f.read()
            f.close()
            lines = fc.splitlines()
            self.serial_no = lines[0]
            logger.info("[!] Serial Number: %s" % self.serial_no)

        except:
            logger.exception("Error getting Serial No. (Exception)")
            return -1

        return 1
    
    # ##################################################
    # TODO: replace with calling network class when available.
    def getMEID(self):
        try:
            self.meid = None
            if os.path.exists('/data/etc/network.conf'):
                with open('/data/etc/network.conf') as f:
                    mf = f.read()
                m = re.search('meid=([^\n]*)\n', mf)
                self.meid = m.group(1)[2:]
            
            if not len(self.meid) > 1: 
                self.meid = 'None'
                logger.info("[!] No MEID found. Possibly due to no Fusion module.")
                return 1
            
            logger.info("[*] obtained cellular modem MEID: %s" % self.meid)
            return 1
        except:
            logger.exception("Exception adding meid to tablet.conf")
            return -1

    # ##################################################
    # Provision (Register) the tablet with the Inbox Server
    def provision(self):
        try:
            logger.info("[ ] Contacting Inbox server to provision tablet")
            logger.debug("Calling Inbox Server API::provisionTablet...")
            url    = "https://" + self.options.inbox + "/tablet/provision/tablet"

            # ##################################################
            # Put together the POST parameters and urlencode
            params = {"account": self.options.account, "serial_no": self.serial_no,
                      "hardware_id": self.hardware_id, "meid": self.meid, 
                      "fingerprint": self.fingerprint, "public_key": self.public_key}
            
            params = urllib.urlencode(params)

            # Add Tablet via WS API
            rtn = urllib.urlopen(url, params)
            rtn = rtn.read()

            lines = rtn.splitlines()
            got_json = False
            for line in lines:
                if line[0:1] == "{":
                    rtn = line
                    got_json = True
                    break
                else:
                    logger.debug(line)

            if got_json == False:
                logger.error("Error getting JSON object back from WSAPI. [Contact Ricoh Support]")
                return -1

            logger.debug(rtn)

            self.response["provision"] = json.loads(rtn)
            
            if self.response["provision"]["status"] == "error":
                logger.error(self.response["provision"]["message"])
                return -1
            else:
                self.api_key = self.response["provision"]["api_key"]
                config.set("sync", "ssh_host", self.options.inbox)
                config.set("sync", "tablet_id", self.serial_no)
                config.set("sync", "api_key", self.api_key)
                
        except:
            logger.exception("Error calling WSAPI::tablet/provision/tablet. (Exception)")
            return -1

        logger.info("[*] Tablet provisioned.")

        return 1

    # ##################################################
    # Log in the user and add the session information to tablet.conf
    def login(self):
        try:
            logger.info("[ ] Logging in user %s..." % self.options.user)
            from ew.util import login
            l = login.Login()
            rtn = l.login(self.options.user, self.options.password)
        except:
            logger.exception("Error logging in to Inbox Server.")
            return -1
        
        logger.info("[*] Logged in user %s." % self.options.user)
        return 1

    def is_calibrate_running(self):
        running = False
        import subprocess
        try:
            output = subprocess.Popen(["pgrep", "-f", "/usr/local/bin/ts_calibrate_ept.sh"],
                    stdout = subprocess.PIPE).communicate()[0]
            if output is not None and output.strip() != "":
                running = True
        except Exception, e:
            logger.debug("Error looking for calibrate process %r", e)
        return running

    def calibrate(self):
        try:
            logger.debug("-----------------------------------------------------")
            logger.info("[ ] Calibrating tablet...")
            logger.debug("-----------------------------------------------------")

            logger.debug("Stopping display server...")
            p = sub.Popen('/usr/local/bin/tablet stop', stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            output, error = p.communicate()

            logger.debug("error::%s" % (error))
            logger.debug("output::%s" % (output))

            logger.debug("-----------------------------------------------------")
            logger.info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.info("CLICK ON THE SCREEN DOTS TO CALIBRATE...")
            logger.info("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("-----------------------------------------------------")
            p = sub.Popen('/usr/local/bin/ts_calibrate_ept.sh', stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            output, error = p.communicate()

            logger.debug("error::%s" % (error))
            logger.debug("output::%s" % (output))

        except:
            logger.exception("Error running calibrate tablet. (Exception)")
            return -1

        logger.debug("-----------------------------------------------------")
        logger.info("[*] Tablet calibrated.")
        logger.debug("-----------------------------------------------------")
        self.need_restart = True

    def audit(self):
        try:
            logger.debug("-----------------------------------------------------")
            logger.debug("Auditing tablet configuration...")
            logger.debug("-----------------------------------------------------")

            p = sub.Popen('/usr/local/bin/nvram_sanity.py', stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            output, error = p.communicate()

            logger.debug("stderr::%s" % (error))
            logger.debug("output::%s" % (output))
            logger.debug("returncode::%s" % (p.returncode))
            if p.returncode <> 0:
                logger.info("[!] inconsistencies found in tablet configuration")
                self.warn("inconsistencies found in tablet configuration")
                logger.error(output)
            else:
                logger.info("[*] Successfully audited tablet configuration")

            return p.returncode
        except:
            logger.exception("Error running audit tablet. (Exception)")
            return -1

    def post(self):
        # ##################################################
        # Post actions

        self.audit()
        
        logger.info("[*] Successfully provisioned %s" % self.serial_no)

        if self.need_restart:
            try:
                logger.debug("-----------------------------------------------------")
                logger.info("[*] Success... rebooting tablet to reset calibration...")
                logger.debug("-----------------------------------------------------")
                sub.Popen("shutdown -r now", shell=True)
                return 0
            except:
                logger.exception("Error restarting. (Exception)")
                return -1
            
        if self.need_login == True:
            logger.debug("-----------------------------------------------------")
            logger.info("[*] Success... loading Login page...")
            logger.debug("-----------------------------------------------------")
#            comms.create_launcher_client().request_login()
        else:
            logger.debug("-----------------------------------------------------")
            logger.info("[*] Success... loading Inbox...")
            logger.debug("-----------------------------------------------------")
#            comms.create_launcher_client().open_inbox_with_infobar()
            
        sub.Popen("/usr/local/bin/launcherd restart", shell=True)
        return 0

    def getTabletConfFile(self):
        return '''
[tablet_config]
loaded_lock = loaded.lock
document_lock = document.lock
status_lock = status.lock

[sync]
php_domain = localhost
log_level = DEBUG
server_branch = sync
ssh_port = 2077
git_port = 2002
sync_daemon_lock_path = /tmp/sync_daemon_lock
tunnel_port = 2001
server_root = /home/memphis
tablet_id = 0
tablet_name = Ricoh eQuill
ssh_user = memphis
git_user = memphis
max_tries = 3
debug = True
tablet_root = /data
manifest = MANIFEST
doc_suffix = .memphis
manage_docs = manage_docs.py
auto_sync_period = 900
max_documents = 2000

[parameters]
req_wakeup_login = 0

[core_app]
wifi = 1
airplane = 0
locked = 0
minutes_until_ready = 5
minutes_until_sleep = 10

[session]

[tablet]


'''

if __name__ == "__main__":
    pro = provision()
    pro.start()



