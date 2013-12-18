#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
import os, sys, signal, random, time
from ew.util import restartlib

WAIT_TIME = 20              # seconds between random server kills

if len(sys.argv) > 1:
    WAIT_TIME = float(sys.argv[1])

print "-------------------------------------------"
print "-------------------------------------------"
print "-------------------------------------------"
print "Monte Carlo Process killer begins, wait time = %s" % WAIT_TIME
print "-------------------------------------------"
    
# Instantiate checker object, read from proper config file
checker = restartlib.PidChecker("/home/developer/Restart/mainrestart.conf")
    
while 1:
    servernames = checker.servers.keys()
    victim = random.choice(servernames)
    checker.hardkillserver(victim)
    time.sleep(WAIT_TIME)
    
