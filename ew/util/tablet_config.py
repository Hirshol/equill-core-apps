#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""
Module for communication between the "manage_docs" process on the EWS
tablet and other tablet applications.
"""

import os, time, json, threading
import ConfigParser
import subprocess as sub

from ew.util.lock import ExclusiveLock, SharedLock
from ew.util.safe_write import SafeWrite
from ew.util import ew_logging

# ##################################################
# Get what we need
from ew.util import comms
dr = comms.create_launcher_client()

logger = ew_logging.getLogger('ew.util.tablet_config')
DOWNLOAD_SIZE_FILE = "/xtra/download_size"

class AugmentedConfigParser(ConfigParser.ConfigParser):
    def __init__(self):
        ConfigParser.ConfigParser.__init__(self)
        
    def get_option(self, section, option, default = None):
        return self.get(section, option, raw=True) if \
               self.has_option(section, option) else default

    def getboolean(self, section, option, default = False):
        raw = self.get_option(section,option,default)
        return False if (raw == '0') else bool(raw)

    def set_option(self, section, option, value):
        if not self.has_section(section):
            self.add_section(section)
        self.set(section, option, value)

    def setboolean(self, section, option, booleanValue):
        val = '1' if booleanValue else '0'
        self.set_option(section, option, val)

class Config(object):

    _conf_path_ewriter = '/data/etc/ewriter.conf'
    _conf_path_tablet  = '/data/etc/tablet.conf'
    _provisioned = False
    _params = {}
    cp_tablet = None
    time_tablet = 0
    cp_ewriter = None
    thread_lock = threading.RLock()

    class InnerLocked:
        def __init__(self, outer, lock):
            self._outer = outer
            self._lock = lock

        def __enter__(self):
            Config.thread_lock.acquire()
            self._lock.acquire()
            self._outer._ensure_latest()
            return self._outer.cp_tablet
        
        def __exit__(self, type, value, traceback):
            try:
                Config.thread_lock.release()
                self._lock.release()
            except:
                pass

    class ReadLocked (InnerLocked):
        def __init__(self, outer):
            Config.InnerLocked.__init__(self, outer, outer._read_lock)

    class WriteLocked (InnerLocked):
        def __init__(self, outer):
            Config.InnerLocked.__init__(self, outer, outer._write_lock)
            
        def __exit__(self, type, value, traceback):
            Config.InnerLocked.__exit__(self, type, value, traceback)
            self._outer._save_config()

    def __init__(self, tablet_config_path=None):
        self._config_path = tablet_config_path if tablet_config_path else \
                            self._conf_path_tablet
        self._read_lock = SharedLock(self._config_path)
        self._write_lock = ExclusiveLock(self._config_path)
        self._is_developer_tablet = None

    def _ensure_latest(self):
        if self.time_tablet < self._last_changed_time() or not self.cp_tablet:
            self._load_tablet_config()

    def _tablet_config(self):
        with self._read_lock:
            self._ensure_latest
            return self.cp_tablet

    def read_lock(self):
        return self.ReadLocked(self)

    def write_lock(self):
        return self.WriteLocked(self)
        
    def is_provisioned(self):
        with self.read_lock() as config:
            self._provisioned = bool(config.get_option("sync","ssh_host"))
            return self._provisioned
    
    def is_developer_tablet(self):
        if self._is_developer_tablet is  None:
            self._is_developer_tablet = self.getboolean('core_app', 'is_developer_tablet') or \
                os.getenv('is_developer_tablet') == '1'
        return self._is_developer_tablet

    def unprovisioned_allowed(self):
        return os.getenv('allow_unprovisioned')
    
    def has_section(self, section):
        with self.read_lock() as config:
            return config.has_section(section)
            
    def has_option(self, section, option):
        with self.read_lock() as config:
            return config.has_option(section, option)
    
    def items(self, section):
        with self.read_lock() as config:
            return config.items(section) if config.has_section(section) else []
    
    def get(self, section, option, default=None):
        with self.read_lock() as config:
            return config.get_option(section, option, default)
    
    def getboolean(self, section, option, default = False):
        raw = self.get(section,option,default)
        return False if (raw == '0') else bool(raw)

    def sections(self):
        with self.read_lock() as config:
            return config.sections()
    
    def set(self, section, option, value):
        with self.write_lock() as config:
            config.set_option(section, option, value)
        
    def add_section(self, section):
        with self.write_lock() as config:
            config.add_section(section)
        
    def remove_section(self, section):
        with self.write_lock() as config:
            config.remove_section(section)
        
    def _save_config(self):
        try:
            logger.debug("Writing data: %r", self.cp_tablet.sections())
            with SafeWrite(self._config_path, 'wb') as f:
                self.cp_tablet.write(f)
                self.time_tablet = self._last_changed_time()
        except Exception, e:
            logger.exception("Exception caught saving tablet.conf. %r" , e)

    def _load_config(self, cfg_path, config_class=ConfigParser.ConfigParser):
        """Read the current config file."""
        try:
            cfg = config_class()
            
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    cfg.readfp(f)
            
            logger.debug("Loaded config: %r", cfg.sections())
            return cfg
        except:
            logger.exception("Exception caught loading configuration file.")
            
            # If there's a malformed or corrupted document, open the provisioning screen.
            from ew.util import comms
            dr = comms.create_launcher_client()
            dr.require_provisioning()
            return

    def _last_changed_time(self):
        return os.path.getmtime(self._config_path)

    def _load_tablet_config(self):
        self.cp_tablet = self._load_config(self._config_path, config_class=AugmentedConfigParser)
        self.time_tablet = self._last_changed_time()
        
    def process(self):
        """
        Process the ewriter.conf file.
        """
        try:
            logger.debug('Processing: %r', self._conf_path_ewriter)
            self.cp_ewriter = self._load_config(self._conf_path_ewriter)

            # First, process commands, if any.
            self._process_commands()

            # Next, process parameters.
            self._process_params()
                
            # Next, process update, if any.
            self._process_update()
            
        except:
            logger.exception("Exception caught processing ewriter.conf.")

    def _process_commands(self):
        # ##################################################
        # If we have any powerful commands to run (wipe, lock, unlock)
        try:
            if self.cp_ewriter.has_section("command") and self.cp_ewriter.has_option("command", "command"):
                logger.debug("Found a command to process...")
                val = self.cp_ewriter.get("command", "command")
                
                if val == 'wipe':
                    self._wipe()
                elif val == 'lock':
                    self._lock()
                elif val == 'unlock':
                    self._lock(False)
                elif val == 'logout':
                    self._logout()
                elif val == 'getlogs':
                    self._getlogs()
                elif val == 'sledgehammer_3g':
                    self._sledgehammer_3g

        except:
            logger.exception("Exception caught processing commands.")
        
    def _process_params(self):
        # ##################################################
        # Get the parameter list from each config
        try:
            logger.debug("Processing parameters...")
            ewcfg = dict(self.cp_ewriter.items('parameters'))
            
            # ##################################################
            # Loop through the parameters.  If they don't match
            # call the corresponding function.
            pchange = {}

            with self.write_lock() as config:
                for k, v in ewcfg.iteritems():
                    config.set_option("parameters",k, v)
                    pchange[k] = v
                
            self._run_params(pchange)
            
            # ##################################################
            # If we're collecting GPS/location data, send location.log 
            # to the Inbox Server.
            if int(self.get("parameters", "gps_interval")) > 0:
                self._getlocation()
            
        except:
            logger.exception("Exception caught processing parameters.")
        
    def _run_params(self, params):
        
        try:
            if len(params) < 1:
                logger.debug('No parameters to process.')
                return 0
            
            
            # ##################################################
            # Loop through the standard parameters and process

            def enable_disable(what, boolean):
                from ew.services import network
                mgr = network.NetworkService()
                action = 'enable' if boolean else 'disable'
                fn = '%s_%s' % (action, what)
                logger.info('%s %sd', what, action)
                getattr(mgr, fn)()
            
            for k,v in params.iteritems():
                logger.debug("Processing parameter %s = %s" % (k,v))
                # Radio Params
                if v in ['0','1']: v = v == '1'
                if k in ('wifi','three_g','threeg_roaming'):
                    cleanup = dict(wifi='wifi', three_g='3g',
                                   threeg_roaming='3g_roaming')
                    enable_disable(cleanup[k], v)
                
                elif k == 'authorized_key':
                    if v:
                        self._enable_ssh()
                        logger.info("Authorized SSH enabled")
                
                # Doc Runner
                elif k == 'name':
                    dr.set_title(v)
                    
                elif k == 'log_level':
                    dr.set_log_level(v)
                
                elif k == 'gps_interval':
                    from ew.services import network
                    net = network.NetworkService()
                    net.want_gps(True, 1)
                
                elif k == 'doze_timer':
                    self.set("core_app", "minutes_until_sleep", int(v))
                    dr.setup_ready_sleep_timers()
                    
                # --------------------------------------------------
                # To be implemented 
                #if name == 'home_lat' = 0
                #if name == 'home_lng' = 0
                #if name == 'radius' = 0
                
                # --------------------------------------------------
                # Nothing to do, just sets the params in tablet.conf
                #if name == 'three_g_ota' = 0
                #if name == 'wifi_edit' = 1
                #if name == 'admin_pwd': = pwd
                #if name == 'req_pwd_inbox' = 1
                #if name == 'req_pwd_template' = 1
                #if name == 'req_pwd_admin' = 1
        except:
            logger.exception("Exception caught processing parameters.")

    """
    Determine if we need to start an OTA download.
    """
    def _process_update(self):
        try:
            logger.debug("Processing update...")
            restart_rsync = False
            current_ver   = self.get("sync", "tablet_version")
            
            # ##################################################
            # Set conf section
            if self.cp_ewriter.has_section("update"):
                # ##################################################
                # First, see if we already have an OTA request from tablet.conf
                # If the versions differ, we need to restart sync.
                if self.has_section("update"):
                    if self.cp_ewriter.get("update", "version") != self.get("update", "version"):
                        logger.debug("Killing previous rsync.")
                        sub.Popen("pkill rsync", shell=True)
                        
                        # Remove all old tar files
                        logger.debug("Cleaning directory.")
                        import glob
                        old = []
                        old = glob.glob("/xtra/*.tar*")
                        for f in old:
                            logger.debug("Removing bad tar file %s." % f)
                            sub.Popen("rm %s" % f, shell=True)
                else:
                    self.add_section("update")
                
                self.set("update", "version", self.cp_ewriter.get("update", "version"))
                self.set("update", "build_name", self.cp_ewriter.get("update", "build_name"))
                self.set("update", "file_path", self.cp_ewriter.get("update", "file_path"))
            
            # ##################################################
            # If we don't have an update section in conf we can skip
            if self.has_section("update"):
                version     = self.get("update", "version")
                build_name  = self.get("update", "build_name")
                remote_path = self.get("update", "file_path")
                local_path = "/xtra/%s" % build_name
            else:
                return 0
            
            # ##################################################
            # If the admin is trying to OTA the current version, don't let them.
            if current_ver == version:
                self.remove_section("update")
                return 0
            
            # ##################################################
            # Get the file info
            last_file,last_size = self.get_download_info()
            
            if last_file != None and local_path != last_file:
                os.remove(DOWNLOAD_SIZE_FILE)
            
            # ##################################################
            # Is the correct build already in /xtra, i.e. has it finished downloading?
            #  If so, we can remove the [update] section and return.
            if os.path.exists( local_path ) :
                logger.debug('checking for rsync on existing file: os.path.getsize( local_path ) = %s, last_size = %s' % (os.path.getsize( local_path ),last_size) )
                logger.debug('checking for rsync on existing file: local_path = %s, last_file=%s' % (local_path,last_file) )
                if (os.path.getsize( local_path ) == last_size) and local_path==last_file:
                    logger.info("Build version %s download finished." % version)
                    self.remove_section("update")
                else:
                    logger.info("Build version %s exists but download is not finished." % version)
                    
                return 0
            
            # ##################################################
            # Also make sure we're not already running an rsync
            # process.  If we are, we're already rsync'ing correct build.
            # We might improve to pgrep the build name.
            p = sub.Popen("pgrep -f 'rsync.*partial'", stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            out, err = p.communicate()

            logger.debug('pgrep rsync: out = %s, err = %s' % (out,err))
            if len(out.strip()) > 0:
                logger.debug("Build version %s is currently downloading." % version)
                return 0

            # ##################################################
            # If we're on 3g, make sure downloads are allowed (PROCOREAPP-323)
            #    Check ew_config for [parameters]three_g = 1, three_g_ota = 0.
            #    if so, make sure we're connected using WiFi.
            #    NOTE:  assumes that we won't have simultaneous 3G and WiFi connections
            if self.get("parameters", "three_g") == '1' and self.get("parameters", "three_g_ota") == '0':
                if not self._using_wifi():
                    logger.info("3g not allowed and not using WiFi: NOT downloading update")
                    return 0

            # ##################################################
            # Start rsync'ing the new build
            from ew.util import rsync
            args = []
            host = self.get('sync','ssh_host')
            port = self.get('sync','ssh_port')
            
            args = ['/usr/bin/rsync',
                    '-e',
                    '"/usr/bin/ssh -p %s -l memphis -i /data/.ssh/id_rsa"' % port ,
                    '--partial',
                    '--progress',
                    '%s:%s' % (host, remote_path),
                    '/xtra']
            r = rsync.Rsync( args, output="/tmp/dl.out" )

            download_size = r.getSize()
            if not download_size:
                logger.info('could not determine size of update to download.  aborting')
                return 0
            self._write_download_info( r, download_size, local_path )            
            
            logger.debug("Downloading build version %s." % version)
            r.start()
    
        except:
            logger.exception('Exception caught trying to rsync new build.')

    @classmethod
    def get_download_info(cls):
        if os.path.exists( DOWNLOAD_SIZE_FILE ):
            jsonstr = open(DOWNLOAD_SIZE_FILE,'r').read()
            jsonobj = json.loads( jsonstr )
            return jsonobj['filename'], int(jsonobj['size'])
        return None,None
        
    def _write_download_info(self,rsyncobj,size,filename):
        download_size = rsyncobj.getSize()
        if not download_size:
            logger.info('could not determine size of update to download.  aborting')
            return 0
        jsonstr = json.dumps( {'size':download_size,'filename':filename} )

        with open(DOWNLOAD_SIZE_FILE,'w') as f:
            f.write( jsonstr )

    def _lock(self, set_lock = True):
        """
        Locks or Unlocks the tablet.  The core_app section holds the current 
        status in case of reboot.  Doc Runner looks at value and sets the state.
        """
        try:
            if set_lock == True:
                self.set("core_app", "locked", 1)
                dr.lock_tablet()
            else:
                self.set("core_app", "locked", 0)
                dr.lock_tablet(False)
        except:
            logger.exception("Exception caught trying to lock/unlock tablet...")
            
    def _wipe(self):
        """
        Wipes the tablet causing it to need provisioning.
          - internal docs (inbox, template, settings, etc) need to get moved to internal_decs
        """
        try:
            logger.debug("Wiping Tablet...")
            p = sub.Popen("rm -rf /data/* /data/.ssh", stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            so,se = p.communicate()
                        
            if len(se) > 0:
                logger.error("Error wiping tablet: %s" % se)
            
            # This should put up the OFF blank screen w/ new DS. 
            logger.debug("Shutting down...")
            dr.blank_screen()
            time.sleep(1)
            sub.Popen("shutdown -r now", shell=True)
            
        except:
            logger.exception("Exception caught wiping tablet.")
        
    def _logout(self):
        try:
            if os.path.exists("/data/etc/login_hash"):
                os.remove("/data/etc/login_hash")
            dr.request_login()
        except:
            logger.exception('Exception caught processing logout')
            return
    
    def _reboot(self):
        sub.Popen('shutdown -r now', shell=True)
        time.sleep(999)
    
    def _boot_to_recovery(self):
        sub.Popen("echo 0 > /sys/bus/msp430/devices/powermgr/boot_to_recovery", shell=True)
        sub.Popen("shutdown -h now", shell=True)
    
    def _getlogs(self):
        try:
            """
            send logs from tablet to server
            """
            from ew.util import rsync
            logger.debug('uploading logs')
            
            args = [
                    # options
                    '/usr/bin/rsync',
                    '-e',
                    '"/usr/bin/ssh -p %s -l memphis -i /data/.ssh/id_rsa"' % self.get('sync','ssh_port') ,
                    '--archive',
                    '--compress',
                    "--exclude='#*'",
                    "--exclude='*~'",
                    "--exclude='.*'",
                    "--include='*log*'",
                    "--include='*log.[0-9]+'",
                    # src
                    '/data/logs/',
                    # dest
                    self.get('sync','ssh_user')
                        + '@' + self.get('sync','ssh_host')
                        + ':' + self.get('sync','server_root')
                        + '/account/' + self.get('session','account')
                        + '/tablet/logs/' + self.get('sync','tablet_id')
                  ]

            r = rsync.Rsync(args)
            r.start()
    
        except:
            logger.exception('Exception caught running special commands.')
            
    def _enable_ssh(self):
        # WARNING!  The ssh user will be the same as the user running sync.
        #           Until the sync daemon is switched over to running as memphis,
        #           the ssh user will be root!  
        # FIXME:  Really ought to sanitize the key text
        if self.cp_ewriter.has_option('ssh', 'authorized_key'):
            try:
                cmd = "umask 022; echo '%s' > /data/.ssh/authorized_keys" % self.cp_ewriter.get('parameters', 'authorized_key')
                logger.debug( '_enable_ssh: executing command %s' % cmd )
                result = sub.call(cmd, shell=True)
                logger.debug( '_enable_ssh: command result %d' % result )

                cmd = "/etc/init.d/dropbear start"
                logger.debug( '_enable_ssh: executing command %s' % cmd )
                result = sub.call(cmd, shell=True)
                logger.debug( '_enable_ssh: command result %d' % result )
                # If no authorized_keys parameter but authorized_keys exists,
                #    delete the authorized_keys file and kill the ssh daemon
            except:        
                logger.exception("Exception caught enabling SSH.")
        else:
            if os.path.exists("/data/.ssh/authorized_keys"):
                cmd = "rm /data/.ssh/authorized_keys"
                result = sub.call(cmd, shell=True)
                cmd = "/etc/init.d/dropbear stop"
                result = sub.call(cmd, shell=True)
                
    def _using_wifi(self):
        """
        Returns True if we are connected using WiFi.
        """
        cmd = 'ifconfig tiwlan0 2>&1 | grep "inet addr"'
        result = sub.call(cmd, shell=True)
        return result == 0
    
    def _sledgehammer_3g(self):
        from ew.services import network
        net = network.NetworkService()
        net.sledgehammer()
        
    def _getlocation(self):
        try:
            """
            TODO: REFACTOR
            send just location logs from tablet to server
            """
            from ew.util import rsync
            logger.debug('uploading location logs')
            
            args = [
                    # options
                    '/usr/bin/rsync',
                    '-e',
                    '"/usr/bin/ssh -p %s -l memphis -i /data/.ssh/id_rsa"' % self.get('sync','ssh_port') ,
                    '--archive',
                    '--compress',
                    "--exclude='#*'",
                    "--exclude='*~'",
                    "--exclude='.*'",
                    "--include='location.log*'",
                    "--include='location.log.[0-9]+'",
                    # src
                    '/data/logs/',
                    # dest
                    self.get('sync','ssh_user')
                        + '@' + self.get('sync','ssh_host')
                        + ':' + self.get('sync','server_root')
                        + '/account/' + self.get('session','account')
                        + '/tablet/logs/' + self.get('sync','tablet_id')
                  ]

            r = rsync.Rsync(args)
            r.start()
    
        except:
            logger.exception('Exception caught running special commands.')        




