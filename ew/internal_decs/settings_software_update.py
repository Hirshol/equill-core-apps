#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.

import threading, subprocess, os, sys, time, json
from ew.util import ew_logging, ew_exec, system_config, tablet_config


logger = ew_logging.getLogger('ew.internal_decs.settings_software_update')

class SoftwareUpdate():
    """Software update is controlled by the existence of the "update" section
    in the tablet.conf configuration file.
    
    [update]
    build_name = rootfs_0.9.3-1853+master+customer+firmwareupdate_RK1.tar
    version = 0.9.3-1853
    file_path = /home/memphis/builds/rootfs_0.9.3-1853+master+customer+firmwareupdate_RK1.tar
    """
    INCOMPLETE = "Incomplete"
    DOWNLOADING = "Downloading"
    DOWNLOADED = "Downloaded"
    
    def __init__(self, parent):
        self.parent = parent
        self.tablet_conf = None
        try:
            self.tablet_conf = tablet_config.Config()
        except Exception, e:
            logger.warning("Could not load tablet configuration: (%r)", e)
        
    def has_update(self):
        """Update is available."""
        has_update = False
        if self.tablet_conf is not None:
            if self.tablet_conf.has_section('update'):
                has_update = True
        return has_update

    def get_available_version(self):
        """Get the available software from the server."""
        build_name = None
        if self.tablet_conf is not None:
            if self.tablet_conf.has_section('update'):
                build_name = self.tablet_conf.get("update", "build_name")
        return build_name

    def get_current_version(self):
        """Get the current software version running on the tablet."""
        build_id = None
        try:
            command_line = "cat /MANIFEST.TXT"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                if line[0:26] == "manifest: build_identifier":
                    build_id = line.split('=')[1].strip()[1:-1]
                    break
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return build_id
    
    def get_rsync_stat(self):
        """Get the state of the rsync download.
        build_name\n
        size\tpercentage\trate\n
        """
        rsync_info_file = "/tmp/dl.out"
        rsync_stat = None
        if os.path.exists(rsync_info_file):
            with open(rsync_info_file, 'r') as f:
                items = f.readlines()
                if len(items) > 0:
                    for sub_item in items[0].split():
                        if sub_item.endswith('%'):
                            rsync_stat = sub_item.strip()
                            break
                f.flush()
                f.close()
        return rsync_stat

    def get_update_status(self):
        """Get the state of the software update."""
        update_status = self.INCOMPLETE     
        if self.is_download_running():
            update_status = self.DOWNLOADING
            # Fire off a software update watcher.
            if not hasattr(self, "download_progress"):
                self.download_progress = SoftwareUpdateWatcher(self)
        else:
            if hasattr(self, "download_progress"):
                self.download_progress.stop()
            if self.is_download_completed():
                update_status = self.DOWNLOADED
        return update_status

    def _load_download_status(self):
        download_status = "/xtra/download_size"
        data = {}
        try:
            with open(download_status, "r") as json_file:
                data = json.load(json_file)
        except Exception, e:
            logger.warning('Error loading %r: %r', download_status, e)
        return data

    def is_download_completed(self):
        """Read the status file
        {"filename": "/xtra/rootfs_0.9.5-1881+master+customer+fw_RK1.tar", 
        "size": "231219200"}
        """
        complete = False
        download_status = self._load_download_status()
        download_name = download_status.get("filename", "")
        download_size = int(download_status.get("size", "-1"))
        current_download = os.path.join("/xtra", self.get_available_version())
        current_size = None
        if os.path.exists(download_name):
            current_size = os.path.getsize(download_name)
        logger.debug("DownloadName: %r DownloadSize: %r Expecting: %r Size: %r",
                download_name, download_size, current_download, current_size)
        if os.path.exists(current_download) and \
                current_download == download_name and \
                current_size == download_size:
            complete = True
        return complete
    
    def set_update_callback(self, update_callback):
        if hasattr(self, "download_progress") and \
                self.download_progress is not None:
            self.download_progress.set_callback(update_callback)
            self.download_progress.start()
            self.download_progress.join(2)
                
    def is_download_running(self):
        """The download is running.. perhaps also query for build id."""
        running = False
        try:
            output = subprocess.Popen(["pgrep", "-f", 
                    "/usr/bin/rsync -e /usr/bin/ssh"],
                    stdout = subprocess.PIPE).communicate()[0]
        except Exception, e:
            logger.exception("Error querying rsync update process.")
        if output.strip():
            running = True
        return running

    def update(self):
        """Fire off the update process"""
        path = os.path.join(system_config.system_home, 'bin', 'upgrade.py')
        if os.path.isfile(path):
            pipe = subprocess.PIPE
            subprocess.Popen([sys.executable, path], stdout=pipe, 
                    stdin=pipe, stderr=pipe)
            logger.debug("Starting update process..")
                
    def _stop_download_watcher(self):
        if hasattr(self, "download_progress") and \
                self.download_progress is not None:
            self.download_progress.stop()

    def clean_up(self):
        self._stop_download_watcher()
            
    
class SoftwareUpdateWatcher(threading.Thread):
    """The thread watching the download of updates from the web server."""
    
    def __init__(self, parent):
        threading.Thread.__init__(self, "settings-software-update-watcher")
        self.software_update = parent
        self.update_callback = None
        self.setDaemon(True)
        self.keep_running = True

    def set_callback(self, update_callback):
        self.update_callback = update_callback
        
    def _callback(self):
        if self.update_callback is not None:
            self.update_callback(self.software_update.get_update_status(),
                    self.software_update.get_rsync_stat())
        
    def run(self):
        """Continously watch the download and notify the callback for updates"""
        logger.debug("Started %s", self.name)
        while self.keep_running and \
                self.software_update.is_download_running():
            try:
                self._callback()
            except Exception, e:
                logger.exception("Error calling the update callback: %r", e)
            time.sleep(2)
        self._callback()
        logger.debug("%s - exiting", self.name)
        
    def stop(self):
        self.keep_running = False