#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.

import os, sys, signal
from ew.util import restartlib


def quithandler(signum, frame):
    global checker
    checker.setchecking(False)
    checker.shutdownall()
    sys.exit()


if not restartlib.heavyweightcheck("mainrestart.py"):    
    #write out a pid file
    restartlib.writepid("mainrestart")
    
    # Instantiate checker object, read from proper config file
    checker = restartlib.PidChecker("/etc/mainrestart.conf")
    
    # once checker is up to speed, install quit handler
    signal.signal(signal.SIGTERM, quithandler)
    
    # start checking until quit signal
    checker.start()
    checker.checkandrestart()
