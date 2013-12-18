#!/usr/bin/env python -OO
# Copyright 2011 Ricoh Innovations, Inc.

# Based on a simple unix/linux daemon in Python 2.5 by Sander Marechal
# Oct.15, 2009
# Original source:
#   http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
#   License: Public Domain
#

from __future__ import with_statement

import sys, os, time, atexit, fcntl, signal, threading
from errno import ESRCH, ENOENT

from ew.util import ew_logging

class Daemon(object):
    """A generic daemon class.
    Usage: subclass the Daemon class and override the run() method

    """
    default_date_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self, daemon_id,
            stdin=None, stdout=None, stderr=None):
        self.daemon_id = daemon_id
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.is_foreground = False
        self.pidfile = self.get_pid_file_path(daemon_id)
        self.cleanup_done = False

    def daemonize(self):
        """Make this process a daemon.
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16

        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.exit("fork #1 failed: %s" % e)


        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.exit("fork #2 failed: %s" % e)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(self.stdin or '/dev/null', 'r')
        so = open(self.stdout or '/dev/null', 'a')
        se = open(self.stderr or '/dev/null', 'a', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # install a SIGTERM trap
        signal.signal(signal.SIGTERM, self.cleanup_handler)

        # write pidfile
        atexit.register(self.finish)
        f = open(self.pidfile, 'w')
        print >>f, os.getpid()
        f.flush()
        try:
            fcntl.lockf(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            sys.exit(
                'Could not obtain exclusive lock on the created PID file.!')
        # Store the open pidfile file object such that it will retain a
        # reference throughout execution of the daemon. If there were
        # no reference, the file object would be deleted, the file closed,
        # and the lock released -- not what we want.
        self.pidfile_object = f

    def cleanup_handler(self, signum, frame):
        """A signal handler, used by this class as a SIGTERM handler."""
        sys.exit(0)

    def finish(self):
        # execute custom cleanup code
        if not self.cleanup_done:
            self.cleanup()
            self.cleanup_done = True
        #try:
        #    # execute custom cleanup code
        #    if not self.cleanup_done:
        #        self.cleanup()
        #        self.cleanup_done = True
        #finally:
        #    self.try_remove(self.pidfile)

    def start(self):
        """Start the daemon"""
        # Check for a pidfile to see if the daemon already runs
        pid = self.get_pid(self.daemon_id)
        if pid:
            sys.exit("Daemon already running.")

        # Start the daemon
        self.daemonize()
        self.do_run()

    def foreground(self):
        """Run the daemon in foreground for debugging."""
        self.is_foreground = True
        os.environ['EW_DAEMON_FOREGROUND'] = 'true'
        self.do_run()

    def do_run(self):
        # ew_logging must be reinitialized *after* the setting of
        # environment variable "EW_FOREGROUND" is made.
        os.environ['EW_DAEMON_ID'] = self.daemon_id
        ew_logging.reinitialize(self.daemon_id)
        logger = ew_logging.getLogger('ew.util.daemon')
        logger.info('======== Daemon started: %r ========', self.daemon_id)
        try:
            self.run()
        except KeyboardInterrupt:
            pass
        except Exception:
            logger.exception("Exception thrown by daemon %s", self.daemon_id)
            raise
        finally:
            logger.debug('Daemon %s finished', self.daemon_id)
            first = True
            while 1:
                nondaemon_threads = [thread for thread in threading.enumerate()
                        if not thread.daemon]
                if len(nondaemon_threads) <= 1:
                    break
                if first:
                    first = False
                else:
                    for thread in nondaemon_threads:
                        logger.debug('Daemon %s --'
                                ' non-daemon thread %s still running',
                                self.daemon_id, thread.name)
                time.sleep(5.0)
            self.finish()

    def stop(self):
        """Stop the daemon"""
        # Get the pid from the pidfile
        pid = self.get_pid(self.daemon_id)
        if not pid:
            print >>sys.stderr, "Daemon not running."
            return # not an error in a restart

        # Try killing the daemon process
        try:
            tries = 100
            interval = 0.2
            for _ in xrange(tries):
                os.kill(pid, signal.SIGTERM)
                time.sleep(interval)
            print >>sys.stderr, (
                    'Could not stop process after trying for %s sec. (SIGTERM)'
                    ' -- killing (SIGKILL).' % (tries * interval))
            os.kill(pid, signal.SIGKILL)
        except OSError, e:
            if e.errno != ESRCH:
                sys.exit(str(e))
            self.try_remove(self.pidfile)

    @classmethod
    def get_pid(cls, daemon_id):
        """Get the PID of a daemon that was started by this class.
        Parameters:
          daemon_id -- The daemon_id specified when the daemon instance
            was created.
        Return: The PID (a positive integer) if the process is alive,
            otherwise None.
        """
        pidfile = cls.get_pid_file_path(daemon_id)
        try:
            # Read the PID from the pid file.
            with open(pidfile) as f:
                try:
                    fcntl.lockf(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    # We got the lock, so its process is gone.
                    return None
                except IOError:
                    # The file is locked, so its process is running.
                    try:
                        # Return the PID.
                        return int(f.readline())
                    except ValueError, e:
                        # PID file is corrupted. Raise an exception.
                        raise ValueError('PID file is corrupted: (%s) %s' %
                                (e, pidfile))
        except IOError, e:
            # Trouble opening the pid file. Assume not running if ENOENT,
            # otherwise re-raise the exception.
            if e.errno == ENOENT:
                return None
            raise

    @classmethod
    def get_pid_file_path(cls, daemon_id):
        """Get the PID file path of a daemon that was started by this class.
        Parameters:
          daemon_id -- The daemon_id specified when the daemon instance
            was created.
        Return: The PID file path.
        """
        return os.path.join('/tmp', daemon_id + '.pid')

    @staticmethod
    def try_remove(path):
        try:
            os.remove(path)
            return True
        except EnvironmentError:
            return False

    def restart(self):
        """Restart the daemon."""
        self.stop()
        self.start()

    def run(self):
        """Perform the daemon's functionality.
        You should override this method when you subclass Daemon. It will be
        called after the process has been daemonized by start() or restart().
        """
        raise NotImplementedError("Daemon run method not implemented")

    def cleanup(self):
        """Perform cleanup operations efore shutdown.
        You can optionally override this method when you subclass Daemon.
        It will be called before the process exits, but after the pid file is
        removed.
        """


# Main program -- invoked when this file in run as a command.
# A tool that prints a daemon's PID given its daemon ID string, or prints
# nothing if the daemon is not alive.
if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print >>sys.stderr, 'Args: daemon-ID'
        sys.exit(2)
    pid = Daemon.get_pid(args[0])
    if pid:
        print pid
