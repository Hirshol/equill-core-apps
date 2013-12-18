#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
from __future__ import with_statement
import time
import ew.util.ew_logging

MODE = "simple"  #temp until config_file fixed

logger = ew.util.ew_logging.getLogger('ew.util.annotation')

class Timer:
    def __init__(self):
        import sys
        if sys.platform == "win32":
            # Windows time.clock()
            self.default_timer = time.clock
        else:
            # *nix time.time()
            self.default_timer = time.time

    def __enter__(self):
        self.t0 = self.default_timer()

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug('Elapsed time:', self.default_timer() - self.t0)

def print_timing(timed_function):
    """Annotation definition for timing a method or function call. The cProfile
    routine has a slight overhead. If simple timing is needed; "simple" is
    the preferred way.
    """
    #config = config_file.ConfigFile('developer')
    mode = MODE

    # cprofile has a slight overhead
    if mode is "cprofile":
        # complete profiler
        import cProfile as profiler
        import pstats
        func_name = timed_function.__name__
        stats_file = "/tmp/%s.profile" % func_name
        def wrapper(*args, **kw):
            def invoke_function(result):
                result.append(timed_function(*args, **kw))
            result = []
            profiler.runctx('invoke_function(result)', globals(), locals(),
                                filename=stats_file)
            stats = pstats.Stats(stats_file)
            stats.sort_stats('cumulative')
            stats.print_stats()
            # stats.print_callers()
            return result[0]
        wrapper.__name__ = func_name
        return wrapper
    elif mode is "simple":
        # simple time duration
        def wrapper(*arg):
            with Timer():
                res = timed_function(*arg)
            logger.debug('TIMER - Function: %s', timed_function.func_name)
            return res
        wrapper.__name__ = timed_function.__name__
        return wrapper
    else:
        # do nothing
        return timed_function

def log_time(f):
    def inner(*args, **kwargs):
        start = time.time()
        ret = f(*args, **kwargs)
        duration = time.time() - start
        frmt = '%s took %s seconds'
        args = f, duration
        a_logger = f.func_globals.get('logger')
        if a_logger:
            a_logger.debug(frmt, *args)
        else:
            print frmt % args
        return ret
    return inner
