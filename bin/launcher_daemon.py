#!/usr/bin/python -OO

# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.

"""
Daemonization of the launcher.py using util.daemon.py
"""

import os, sys, logging

os.environ['EW_NEW_DS'] = 'true'

import ew.launcher.runner as launcher
import ew.util.ew_logging
from ew.util import daemon

logger = ew.util.ew_logging.getLogger('ew.launcher.launcher_daemon')

class LauncherDaemon(daemon.Daemon):
    """Subclass of ew.e_ink.daemon.Daemon that creates a launcher daemon."""

    def __init__(self):
        daemon.Daemon.__init__(self, 'launcher_daemon')

    def run(self):
        """Overrides base class run()."""
        try:
            logger.debug("Calling launcher main")
            launcher.main()
        except Exception:
            logger.exception("Exception in launcher daemon")
            raise
        logger.debug('done')

    def cleanup(self):
        """Overrides base class cleanup()."""
        logging.shutdown()
        launcher.shutdown()


def usage(message=None):
    """Print a usage message and quits with exit code 2."""
    if message:
        print >> sys.stderr, message
    print >> sys.stderr, \
            "Launcher daemon\nArgs: start|stop|restart|foreground"
    sys.exit(2)


# When invoked as a main program, instantiate the above daemon class and
# invoke a command as specified on the command line.
if __name__ == "__main__":

    if len(sys.argv) != 2:
        usage()

    arg = sys.argv[1]
    daemon = LauncherDaemon()

    if 'start' == arg:
        daemon.start()
    elif 'stop' == arg:
        daemon.stop()
    elif 'restart' == arg:
        daemon.restart()
    elif 'foreground' == arg:
        daemon.foreground()
    else:
        usage("Unknown command")

    print "Done! Launcher daemon terminating."
