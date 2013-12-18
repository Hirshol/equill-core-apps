# Copyright 2010 Ricoh Innovations, Inc.
# Example provisioning file. Edit and copy to
# /home/guest/provisioning.py to have it take effect.

# Start with splash screen. If False, load inbox on startup.
start_with_splash = True

# Storage server host, account and username. Set to None if working in
# off-line or ad-hoc networking mode (e.g. using
# submit_with_http_put_url)
ss_host='184.106.212.245'
ss_account='1996'
#ss_account='steve'

#ss_username='223'           
ss_username='1026'           

# If set, submissions will use legacy method for submission whereby
# the entire Memphis file is submitted as a zip file using an HTTP PUT
# request to the specified URL. This is currently used as an internal
# demo that operates with a laptop over an ad-hoc network.
submit_with_http_put_url = None

# Logging settings
verbose = True
logfile = '/tmp/notebook.py.log'
import logging  # necessary if you change the logging levels below
log_level_inbox = logging.DEBUG
log_level_infobar = logging.INFO
log_level_notebook = logging.DEBUG
log_level_memphis = logging.DEBUG
log_level_nbeventloop = logging.DEBUG
log_level_notebook_store = logging.DEBUG

# Other variables that affect the user experience
pen_width = 2
FPF_BASE_SPEED = 12   # frames per page to start at
FPF_HOLD_DELAY = 0.3 # seconds to hold before starting FPF
FPF_BASE_SPEED_CHANGE_DELAY = 0.2
FPF_INCREMENTAL_SPEED_CHANGE_DELAY = 0.02
inbox_refresh_check_period = 2.0 # seconds between checks whether inbox or templates cache has been updated
rsync_timeout = 30  # seconds of no I/O before should abort
clearcache = False       # delete /data/documents/* on startup
sparkle_delay = 20
