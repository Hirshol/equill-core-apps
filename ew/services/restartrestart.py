#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.

import os, sys, signal
from ew.util import restartlib
from ew.util import ew_logging as log

# ----------------------------------------------------
# Utility Functions
# ----------------------------------------------------

logger = log.getLogger('ew_tablet')

# ----------------------------------------------------
# Signal Handlers
# ----------------------------------------------------



def quithandler(signum, frame):
    global checker
    checker.setchecking(False)
    sys.exit()
    
# ----------------------------------------------------
# Main Program
# ----------------------------------------------------

if not restartlib.heavyweightcheck("restartrestart.py"):    
    # write out a pid file
    restartlib.writepid("restartrestart")
    
    # Instantiate checker object, read from proper config file
    checker = restartlib.PidChecker("/etc/restartrestart.conf")
    
    # once checker is up to speed, install quit handler
    signal.signal(signal.SIGTERM, quithandler)
    
    # start checking until quit signal
    checker.checkandrestart()
