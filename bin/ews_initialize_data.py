#!/usr/bin/python
# ##################################################
# This module is executed every time the tablet reboots and
# checks to see if we have data waiting in /xtra/recover.
# There will only be data there if this is the first time rebooting
# after installing a new build.
#
# @author: Hirshol Pheir
# @copyright: Ricoh EWS 2011

import os, sys
import subprocess as sub
import re
def nowtime():
	import time
	return  time.asctime(time.localtime())


class initialize():
    def __init__(self, *args, **kwds):
        self.pid  = os.getpid()
        self.bu_dir      = "/data/.backup.%s" % self.pid
        self.fp_manifest = "/MANIFEST.TXT"
        self.fp_skeleton = "/var/cache/ews/payloads/home.tar.bz2"

    def run(self):
        # ##################################################
        # If there are files in the recovery directory, save them
        # them to /data/.backup.$$ , create skeleton, then
        # restore from /xtra/recover then /data/.backup.$$/ directories.
        if os.path.exists('/xtra/recover'):
            print "### Found /xtra/recover files: will restore provision/documents"
            self.backup()
            self.createSkeleton()
            self.restore()
        elif not os.path.exists("/data/inbox"):
            print "### Missing inbox: creating skeleton"
            self.createSkeleton()
        else:
            print "Inbox exists: no need to restore or unpack skeleton"
        # ##################################################
        # Get the version number if the file isn't there
        self.setVersion()

    def backup(self):
        if not os.path.exists(self.bu_dir):
            os.makedirs(self.bu_dir)
        print "### BACKUP"
        cmd="mv -f /data/* /data/.ssh %s" % self.bu_dir
        print '%s: cmd: %s' % ( nowtime() , cmd )
        p=sub.Popen(cmd, shell=True)
        out, err = p.communicate()
        print 'stdout: %s' % out
        print 'stderr: %s' % err
        print "===="

    def createSkeleton(self):
        # ##################################################
        # We can also parse the manifest and put the new version
        # number in the tablet.conf file.  This will be passed
        # as an argument for versioning.
        if not os.path.exists(self.fp_skeleton):
            print "skeleton %s missing\n" % ( self.fp_skeleton)
            return 1

        print "### SKELETON"
        cmd="tar -C /data --atime-preserve -xRaf '%s' 2>/dev/null" % (self.fp_skeleton)
        print '%s: cmd: %s' % ( nowtime() , cmd )
        p=sub.Popen(cmd, shell=True)
        out, err = p.communicate()
        print 'stdout: %s' % out
        print 'stderr: %s' % err
        print "===="

    def restore(self):
        # ##################################################
        # Copy the files back to /data/etc
        print "### RESTORE"
        print 'Copying /xtra/recover/data/etc/* -> /data/etc'
        cmd='test -d /data/etc || mkdir /data/etc ; cp -v /xtra/recover/data/etc/* /data/etc 2>&1'
        print '%s: cmd: %s' % ( nowtime() , cmd )
        p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
        out, err = p.communicate()
        print 'stdout: %s' % out
        print 'stderr: %s' % err
        print "===="

        print 'Copying /xtra/recover/data/.ssh/* -> /data/.ssh'
        cmd='test -d /data/.ssh || mkdir /data/.ssh ; cp -v /xtra/recover/data/.ssh/* /data/.ssh'
        print '%s: cmd: %s' % ( nowtime() , cmd )
        p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
        out, err = p.communicate()
        print 'stdout: %s' % out
        print 'stderr: %s' % err
        print "===="

        # ##################################################
        # Delete the recover directory
        print 'Removing /xtra/recover'
        cmd = 'rm -rf /xtra/recover'
        print '%s: cmd: %s' % ( nowtime() , cmd )
        p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
        out, err = p.communicate()
        #print 'stdout: %s' % out
        #print 'stderr: %s' % err
        #print "===="

        # ##################################################
        # Restore backed up inbox and templates files, if any.
        if os.path.exists(self.bu_dir):
            cmd = "/bin/mv %s/inbox/* /data/inbox; /bin/rm -rf /data/inbox/Settings_Document* /data/inbox/Inbox_Document* /data/inbox/Templates_Document* || true" % self.bu_dir
            print '%s: cmd: %s' % ( nowtime() , cmd )
            p=sub.Popen(cmd, shell=True)
            out, err = p.communicate()
            #print 'stdout: %s' % out
            #print 'stderr: %s' % err
            #print "======"

            cmd = "mv %s/logs/* /data/logs" % self.bu_dir
            print '%s: cmd: %s' % ( nowtime() , cmd )
            p=sub.Popen(cmd, shell=True)
            out, err = p.communicate()
            #print 'stdout: %s' % out
            #print 'stderr: %s' % err
            #print "======"

            cmd="mv %s/templates/* /data/templates" % self.bu_dir
            print '%s: cmd: %s' % ( nowtime() , cmd )
            p=sub.Popen(cmd, shell=True)
            out, err = p.communicate()
            #print 'stdout: %s' % out
            #print 'stderr: %s' % err
            #print "======"

            cmd="/bin/ls -lad /data/inbox/* /data/templates/*"
            print '%s: cmd: %s' % ( nowtime() , cmd )
            p=sub.Popen(cmd, shell=True)
            out, err = p.communicate()
            print 'stdout: %s' % out
            #print 'stderr: %s' % err
            #print "======"
        # ##################################################
        # Delete the backup directory
        print "Removing backup dir %s" % self.bu_dir
        cmd = 'rm -rf %s' % self.bu_dir 
        print '%s: cmd: %s' % ( nowtime() , cmd )
        p = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
        out, err = p.communicate()
        #print 'stdout: %s' % out
        #print 'stderr: %s' % err
        #print "===="
    def setVersion(self):
        # ##################################################
        # We can also parse the manifest and put the new version
        # number in the tablet.conf file.  This will be passed
        # as an argument for versioning.
        if not os.path.exists(self.fp_manifest):
            return 0

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
            from ew.util import tablet_config
            conf = tablet_config.Config()
            conf.set('sync', 'tablet_version', version)

        except:
            print 'Exception writing tablet version to tablet.conf.'

        return 1

# ##################################################
# Run
if __name__ == "__main__":
    print "%s: BEGINNING EWS_INITIALIZE_DATA" % nowtime()
    init = initialize()
    init.run()
