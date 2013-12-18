# Copyright 2010 Ricoh Innovations, Inc.
import logging
#from pyedo import network
import os

# User-defined variables (can be overridden by /home/guest/provisioning.py)
start_with_splash = True
ss_host = None
ss_account = None
ss_username = None
submit_with_http_put_url = None
pen_width = 2
FPF_BASE_SPEED = 12   # frames per page to start at
FPF_HOLD_DELAY = 0.3 # seconds to hold before starting FPF
FPF_BASE_SPEED_CHANGE_DELAY = 0.2
FPF_INCREMENTAL_SPEED_CHANGE_DELAY = 0.02
inbox_refresh_check_period = 2 # seconds between checks whether inbox or templates cache has been updated
rsync_timeout = 30  # seconds of no I/O before should abort
clearcache = False       # delete /data/documents/* on startup
logfile = '/tmp/notebook.py.log'
verbose = True
sparkle_delay = 20
log_level_sync = logging.DEBUG
log_level_inbox = logging.DEBUG
log_level_infobar = logging.DEBUG
log_level_notebook = logging.DEBUG
log_level_memphis = logging.DEBUG
log_level_nbeventloop = logging.DEBUG
log_level_notebook_store = logging.DEBUG

submit_check = False

try:
    from provisioning import *
except ImportError:
    pass

# Non-user-defined variables
demo_mode = False  # demo_mode no longer supported
use_ssh = True     # if true, use SSH when accessing the storage server (required for accessing cloud-based nile2)
if demo_mode:
    ss_rsync_url = '/data/demo-ss'
elif use_ssh:
    ss_rsync_url='%s::%s'%(ss_host, ss_username)
else:
    ss_rsync_url='%s@%s::%s'%(ss_username, ss_host, ss_username)

# ss_submit_url and ss_password are only used if use_ssh is False
ss_submit_url='http://%s/~%s/users/%s/'%(ss_account, ss_host, ss_username)
ss_password='password' 

submit_lock = '/tmp/submit_lock'

# other startup vars (probably will break things if these are changed)
docdir = '/home/guest/clipboard/forms/SplashScreen.edo'
enableinfobar = True
flash_infobar = True
http = False   # Should we enable the HTTP server for pushing to EDO (default is pull only)?
flash = True

# Resource files
# File Interface to DisplayServer
LIVEINK = '/tmp/PTU_inkimage.pgm'  # unused
BGIMAGE = '/tmp/PTU_bgimage.pgm'  # unused
LIVESTROKES = '/tmp/PTU_stroke.ink'
EXTERNALSTROKES = '/tmp/external_strokes.ink'  # unused

# File Interface between notebook/inbox and notebook_store.py
sync_process_command = '/home/guest/clipboard/bin/notebook_store.py'
sync_request_path = '/tmp/sync_request'
template_copy_lock_path = '/tmp/template_copy_lock'
template_copy_queue_path = '/data/queues/template_copy_queue'
submit_queue_path = '/data/queues/submit_queue'
sync_request_poll_delay = 1.0

# Resource Files
BASEDIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
SPLASHIMAGE = os.path.join(BASEDIR, 'data', 'splash.pgm')
WHITEIMAGE = os.path.join(BASEDIR, 'data', 'white.pgm')
BLACKIMAGE = os.path.join(BASEDIR, 'data', 'black.pgm')
DOWNLOADINGIMAGE = os.path.join(BASEDIR, 'data', 'DOWNLOADINGr.pgm')
LOADERRORIMAGE = os.path.join(BASEDIR, 'data', 'LOADERRORr.pgm')
SUBMITQUEUEDIMAGE = os.path.join(BASEDIR, 'data', 'SUBMITQUEUEDr.pgm')
LOADINGIMAGE = os.path.join(BASEDIR, 'data', 'LOADINGr.pgm')
UNCOMPRESSINGIMAGE = os.path.join(BASEDIR, 'data', 'UNCOMPRESSINGr.pgm')
COMPRESSINGIMAGE = os.path.join(BASEDIR, 'data', 'COMPRESSINGr.pgm')
SUBMITTINGIMAGE = os.path.join(BASEDIR, 'data', 'SUBMITTINGr.pgm')
SUBMITTEDIMAGE = os.path.join(BASEDIR, 'data', 'SUBMITTEDr.pgm')
BUTTON_THRESHOLD = 100
MESSAGE_POSITION = [0, 250]

DEBUG         = True
VERSION       = 1.1
DOC_SUFFIX    = ".memphis"
TABLET_ROOT   = "/data"
SERVER_ROOT   = "/home/memphis"

# manage_docs is run on the server through a specialized alteration of ssh
# called sshell which interprets the ssh command sent and then calls the appropriate 
# functions in the real manage_docs.py
MANAGE_DOCS   = "manage_docs.py"
#SSH_HOST      = "184.106.212.245"
SSH_HOST      = ""
SSH_PORT      = 2077
SSH_USER      = "memphis"
SSH_PASSWD    = ""
GIT_USER      = "memphis" # memphis
MANIFEST      = 'MANIFEST'
SERVER_BRANCH = 'sync'
PHP_DOMAIN    = 'localhost'
SSH_ENV = {
   'PYTHONPATH':'~/.memphis',
}

