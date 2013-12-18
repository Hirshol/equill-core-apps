#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
"""Module to simplify programming of file locks."""

from __future__ import with_statement

from os import open as os_open, close as os_close, O_CREAT, O_WRONLY, O_APPEND
from fcntl import lockf, LOCK_EX, LOCK_SH, LOCK_NB, LOCK_UN
from errno import EAGAIN, EACCES

import ew_logging

logger = ew_logging.getLogger("ew.util.lock")

__all__ = "ExclusiveLock", "SharedLock", "LockUnavailableError"

class _GenericLock(object):
    """Generic file lock.
    Abstract superclass for classes such as ExclusiveLock and SharedLock

    """

    def __init__(self, lockpath, non_blocking):
        self.lockpath = lockpath
        self.non_blocking = non_blocking
        self.fd = os_open(self.lockpath, self.flags)
        self.acquired = self.closed = False

    def acquire(self, non_blocking=False):
        """Acquire the lock.
        Returns this lock object except in the case of non_blocking=true and
        the lock is not available, when a LockUnavailableError is raised.

        """
        if self.non_blocking:
            non_blocking = True
        if non_blocking:
            try:
                lockf(self.fd, self.lock_type | LOCK_NB)
                self.acquired = True
            except IOError, e:
                if e.errno in (EAGAIN, EACCES):
                    raise LockUnavailableError(self.lockpath)
                raise
        else:
            lockf(self.fd, self.lock_type)
            self.acquired = True

        return self

    def release(self, force=False):
        """Release the lock.
        Normally a exception is raised if the lock is not currently held
        by this lock object, to prevent accidentally releasing a lock held
        by another lock object. If "force" is true, the object will be
        released anyway.

        """
        if not (force or self.acquired):
            raise RuntimeError(
                    "Attempt to release lock not acquired by this lock object")
        lockf(self.fd, LOCK_UN)
        self.acquired = False

    def close(self):
        """Close the lock-file.
        The Lock object should not be used again after closing.

        """
        if not self.closed:
            os_close(self.fd)
            self.closed = True

    __del__ = close

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        if self.acquired:
            self.release()


class ExclusiveLock(_GenericLock):
    """
    Exclusive file lock.  This class makes file locking a lot more friendly for
    mere mortals.
    See also SharedLock.

    """

    lock_type_name = "exclusive"
    flags = O_CREAT | O_WRONLY | O_APPEND
    lock_type = LOCK_EX

    def __init__(self, lockpath, non_blocking=False):
        _GenericLock.__init__(self, lockpath, non_blocking)


class SharedLock(_GenericLock):
    """
    Shared file lock.  This class makes file locking a lot more friendly for
    mere mortals.
    See also ExclusiveLock.

    """

    lock_type_name = "shared"
    flags = O_CREAT
    lock_type = LOCK_SH

    def __init__(self, lockpath, non_blocking=False):
        _GenericLock.__init__(self, lockpath, non_blocking)


class LockUnavailableError(Exception):
    """Exception raised if an attempted non-blocking lock acquisition fails."""


if __name__ == "__main__":
    import sys, time

    lock_type = SharedLock
    non_blocking = False
    args = sys.argv[1:]
    if args and args[0] == "e":
        lock_type = ExclusiveLock
    if len(args) >= 2 and args[1] == "n":
        non_blocking = True

    path = "/tmp/testlock"
    lock = lock_type(path, non_blocking=non_blocking)
    print "Acquiring lock..."
    try:
        with lock:
            print "Got lock."
            for n in xrange(10, 0, -1):
                sys.stderr.write("\r" + str(n) + "  ")
                sys.stderr.flush()
                time.sleep(1.0)
    except LockUnavailableError, e:
        print "%s: %s" % (e.__class__.__name__, e)
    print "\rDone.    "
