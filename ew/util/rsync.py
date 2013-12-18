#!/usr/bin/env python
"""
Module for communication between the "manage_docs" process on the EWS
tablet and other tablet applications.
"""

import subprocess as sub
from threading import Thread
from ew.util import ew_logging
import time,re,json,os

logger = ew_logging.getLogger('ew.util.rsync')

BUFSIZE=15

class Rsync(Thread):
    """ Run an rsync command in a separate thread. """

    def __init__(self, args, output=None, thisisanupdate=False):
        self.args = args
        self.thisisanupdate = thisisanupdate
        self.output = output
        Thread.__init__(self, name='rsync_daemon')

    def getSize(self):
        sargs = ' '.join( [ self.args[0] ] + [ '-n', '--stats' ] + self.args[1:] )
        p = sub.Popen(sargs,
            shell=True,
            stdout=sub.PIPE,
            stderr=sub.PIPE)
        guts = p.stdout.read()
        m = re.search('^.*total size is\s*(\d+).*$',guts,re.S)
        if m:
            return m.group(1)

    def run(self):
        sargs = ' '.join(self.args)
        logger.info('Rsync thread started(%s)' % sargs )
        try:
            # execute the rsync command in a shell
            p = sub.Popen(sargs,
                shell=True,
                stdout=sub.PIPE,
                stderr=sub.PIPE)
            returncode = None
            # poll if an output file was given
            s = ''
            if self.output:
                while 1:
                    returncode = p.poll()
                    
                    if returncode == None:
                        ss = ''
                        trigger = ''
                        while 1:
                            s = p.stdout.read(1)
                            if s == "/":
                                #logger.debug('--------------------> line completed!')
                                ss += "/s\n"
                                break
                            
                            else:
                               ss += s
                            time.sleep(0.1)
                               
                        #logger.debug( '\nAFTER readline: ss = %s\n' % ss  )
                        f = open(self.output,'w+')
                        f.write(ss)                        
                        f.flush()
                        f.close()                        
                        time.sleep(1)
                    else:
                        break

            else:
                returncode = os.waitpid(p.pid, 0)[1]

            logger.info( 'Rsync finished returncode = %s' % returncode )

            err = ''
            if p.stderr:
                err = p.stderr.read()
            if err:
                logger.error('Rsync: %s' % err)

        except Exception, e:
            logger.error('Rsync failed because: %r' % e)
            logger.exception('Rsync failed')            

        logger.debug('Rsync done')
        
        
