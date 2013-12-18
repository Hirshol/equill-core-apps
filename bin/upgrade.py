#!/usr/bin/python
# ##################################################
# This module upgrades a tablet to new build
#
# @author: Hirshol Pheir
# @copyright: Ricoh EWS 2011

import os, sys, time
import subprocess as sub
import re

# ##################################################
# This file is called from the tablet's UPGRADE button 
# which only appears if a tar file lives in /xtra. 
# 
# Assumptions:
#   - some.tar file exists in /xtra 

class Upgrade():
    def __init__(self, *args, **kwds):
        pass
    
    def run(self):
        # ##################################################
        # TODO: Verify that there is one and only one .tar file
        # in the /xtra directory
        
        
        # ##################################################
        # Make the recovery directories
        sub.Popen('mkdir -p /xtra/recover/data/etc', shell=True)
        sub.Popen('mkdir -p /xtra/recover/data/.ssh', shell=True)
        
        # ##################################################
        # Copy the files in the keeplist dirs
        sub.Popen('cp /data/etc/* /xtra/recover/data/etc', shell=True)
        sub.Popen('cp /data/.ssh/* /xtra/recover/data/.ssh', shell=True)
        
        # ##################################################
        # Here, show the upgrading splash screen 
        # DON'T REALLY NEED THIS NOW THAT THE RECOVERY HAS STEPS
        
        # Stop rogue process
        p = sub.Popen("ps -Al | grep epd_controller_", shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        out,err = p.communicate()
        
        if out.find('epd_controller') >= 0:
            lines = out.splitlines()
            for line in lines:
                flds = line.split()
                pid  = flds[3]
                print "killing %s" % pid
                p = sub.Popen("kill %s" % pid, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
                out,err = p.communicate()
                print out
                   
        p = sub.Popen("tablet stop", shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        out,err = p.communicate()
        print out
        
        p = sub.Popen("ps -Al | grep display_server", shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        out,err = p.communicate()
        print out
        
        if out.find('display_server') >= 0:
            flds = out.split()
            pid  = flds[3]
            p = sub.Popen("kill -9 %s" % pid, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
            out,err = p.communicate()
            print out
            
        # show the splash page
        sub.Popen("cd /usr/local/bin/ && ./show_upgrade_splash", shell=True)
        
        # give the page time to show before entering recovery
        time.sleep(3)
        
        # ##################################################
        # Put tablet into recovery mode
        sub.Popen('echo 0 > /sys/bus/msp430/devices/powermgr/boot_to_recovery && halt', shell=True)
        
    
# ##################################################
# Run 
if __name__ == "__main__":
    upgrade = Upgrade()
    upgrade.run()
