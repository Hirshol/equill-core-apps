#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""
Login handles the login logic for the tablet.

First try to login locally using the hash on the tablet,
otherwise, establish a network connection and login via the Inbox Server.

"""

import os, time, json
import subprocess as sub
import urllib
import hashlib
import threading
from ew.util import tablet_config
from ew.util import ew_logging
from ew.util import comms

logger = ew_logging.getLogger('ew.util.login')
config = tablet_config.Config()
dr = comms.create_launcher_client()

class Login(object):
    _path_to_hash  = "/data/etc/login_hash"
    _salt          = "h4ngMh14@<$$..."
    _previous_user = None
    _dirty         = False
    
    def __init__(self):
        pass
    
    def require_login(self):
        """
        See if we have a session from before sleep/power-off, and if so,
        see if we need to require login anyway before Inbox.
        """
        try:
            if int(config.get('session', 'user')) > 0:
                if config.get('parameters', 'req_wakeup_login') == '0':
                    return False
                
            return True
        except:
            return True
    
    
    def login(self, username, password):
        from ew.services import network
            
        # ##################################################
        # If there's not session info, delete the login hash 
        # to force Inbox login.
        # Otherwise, get the previous username. 
        try:
            if len(config.items('session')) < 5:
                if os.path.exists("/data/etc/login_hash"):
                    os.remove("/data/etc/login_hash")
            else:
                self._previous_user = config.get('session', 'username')
        except:
            logger.exception("Exception caught removing login_hash.")
        
        # ##################################################
        # Compare the previous and current username and perform
        # a sync check if necessary.
        try:
            if self._previous_user <> None and self._previous_user <> username:
                from sync.tablet import login_dirty
                self._dirty = login_dirty()
            
            # ##################################################
            # If we have dirty documents that exist from the previous user
            # we need to sync them.
            # If we can't sync them, we need to prevent anyone but the previous
            # user from logging in.
            if self._dirty:
                # Connect
                rtn = {}
                ip = network.get_network(60)
                
                if ip == '':
                    rtn['status'] = 'error'
                    rtn['message'] = '''There are unsynchronized documents on this tablet. 
Tablet could not find a network to sync documents. 
Only the previous user, %s, may log in at this time.''' % self._previous_user
                    
                    return rtn
                else:
                    # Sync current docs
                    from sync import tablet
                    
                    logger.debug("Starting tablet sync for previous user documents.")
                    sync_tablet = tablet.SyncTablet( suppress_sync=False, force_sync=False )
                    if sync_tablet.run() != 1:
                        logger.error("Error Synchronizing previous users documents.")
                        rtn['status']  = 'error'
                        rtn['message'] =  'Error Synchronizing previous users documents.'
                        return rtn

        except:
            logger.exception("Exception caught sync'ing previous user documents.")
        
        # ##################################################
        # Delete the previous users documents.
        # The tablet can continue processing.  We don't need to wait.
        try:
            if self._previous_user <> None and self._previous_user <> username:
                sub.Popen("rm -rf /data/inbox/* /data/templates/*", shell=True)
        except:
            logger.exception("Exception caught deleting previous users documents.")
        
        # ##################################################
        # If there's a login hash, hash the values and compare,
        # otherwise, just drop down to Inbox Server login
        try:
            if os.path.exists(self._path_to_hash):
                with open(self._path_to_hash) as f:
                    hash1 = f.read().splitlines()[0]
                
                hash2 = hashlib.md5(self._salt + username + password).hexdigest()
                
                # Login success, open Inbox.
                if hash1 == hash2:
                    rtn = {}
                    rtn['status'] = 'Success'
                    rtn['message'] = 'Hash matches that on tablet.'
                    return rtn
        except:
            rtn = {}
            rtn['status'] = 'error'
            rtn['message'] = 'Exception Error. Check your code, buddy.'
            return rtn
            
        # ##################################################
        # Try logging in via Inbox Server.
        
        # Establish network connection
        try:
            ip = network.get_network(45)
            
            if ip == '':
                rtn = {}
                rtn['status'] = 'error'
                rtn['message'] = 'Could not establish a network connection.'
                return rtn
            
        except Exception as e:
            logger.exception("Exception Error. Exception caught establishing a network connection.")
            rtn = {}
            rtn['status'] = 'error'
            rtn['message'] = 'Exception Error. Exception caught establishing a network connection.'
            return rtn
        
        
        # Get params for the WS API Login call.
        try:
            hostname = config.get("sync", "ssh_host")
            api_key  = config.get("sync", "api_key")
            ser_no   = config.get("sync", "tablet_id")
            
            logger.info("Logging in user %s..." % username)
            params = { "api_key": api_key, "tablet": ser_no, 
                       "username": username, "password": password }
            
            params = urllib.urlencode(params)

            url    = "https://%s/tablet/sync/login" % hostname
            rtn    = urllib.urlopen(url, params)
            
            response = json.load(rtn)
            
            if response["status"] == "error":
                rtn = {}
                rtn['status'] = 'error'
                rtn['message'] = '   Invalid Username or Password.'
                return rtn
            
            # Hash the info for next login
            hash = hashlib.md5(self._salt + username + password).hexdigest()
            
            sub.Popen('echo %s > %s' % (hash, self._path_to_hash), shell=True)
            
            # Set the params in tablet.conf
            record = response['record']
            
            config.set("session", "account", record["account_id"])
            config.set("session", "user", record["user_id"])
            config.set("session", "username", record["username"])
            config.set("session", "name", record["name"])
            config.set("session", "email", record["email"])
            
            logger.debug("[*] Logged in in user %s." % username)
            
            rtn = {}
            rtn['status'] = 'success'
            return rtn

        except:
            rtn = {}
            rtn['status'] = 'error'
            rtn['message'] = 'Exception Error. Network connection established but error calling Login WS API.'
            return rtn



