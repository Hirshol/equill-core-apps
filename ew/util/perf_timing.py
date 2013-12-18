#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""
Framework for performance timing tests.

Facilitates running specified code for a specified number of repetitions
and printing timing information: elapsed time, user CPU time, and system
CPU time in seconds.
"""

import time, sys, os
from sys import stderr
from collections import namedtuple
from types import FunctionType

CLK_TCK = 100.0  # Value for system variable sysconf(_SC_CLK_TCK) for tablet.

class PerfTiming(object):

    Test = namedtuple('Test', ['func', 'description'])

    def __init__(self):
        """Initialize an instance."""
        self.tests = {}
        self.test_names = []
        self.my_stat_path = '/proc/%s/stat' % os.getpid()

    def add(self, *funcs):
        """Add the specified functions to the test set."""
        for func in funcs:
            fname = func.func_name
            if fname.startswith('test_'):
                fname = fname[5:]
            self.tests[fname] = func
            self.test_names.append(fname)

    def add_class(self, cls):
        """Add all methods in class "cls" with names starting with "test_".
        Methods are ordered by the ascii collating sequence of their names.
        """
        for x in cls.__dict__.values():
            if isinstance(x, FunctionType) and x.func_name.startswith('test_'):
                self.add(x)

    def main(self):
        """Provide "main program" functionality.
        In the client's main program, after setting up the test set, call
        this function to process command line arguments and run the test set.
        """
        from optparse import OptionParser
        usage = "%prog [options] [test-name...]"
        op = OptionParser(usage=usage, description='Runs performance tests')
        op.add_option('-r', '--reps', type='int', default=2,
            help='Number of repetitions for each test')
        op.add_option('-p', '--progress', action='store_true',
            help='Print progress dots')
        self.opts, args = op.parse_args()
        test_names = args if args else sorted(self.test_names)
        for test_name in test_names:
            self.run_test(test_name)

    def run_test(self, name):
        """Run a single test."""
        func = self.tests[name]
        print '\n%s: %s...' % (name, func.__doc__)
        progress = self.opts.progress
        self.start_cpu_timing()
        t0 = time.time()
        for _ in xrange(self.opts.reps):
            func()
            if progress:
                stderr.write('.')
        if progress:
            stderr.write('\n')
        total_time = time.time() - t0
        self.print_cpu_timing()
        print >>stderr, 'Total time: %.3f sec, %.3f/repetition' % (
                total_time, total_time / self.opts.reps)

    def start_cpu_timing(self):
        """Start a timer for utime (user time) and stime (system time).
        Mainly for internal use by "run_test", but can be called directly.
        """
        with open(self.my_stat_path) as f:
            data = f.read().split()
        self.utime = int(data[13])
        self.stime = int(data[14])

    def print_cpu_timing(self):
        """Print the utime (user time) and stime (system time).
        Prints times since "start_cpu_timing" was called.
        Mainly for internal use by "run_test", but can be called directly.
        """
        with open(self.my_stat_path) as f:
            data = f.read().split()
        print 'Stats -- utime: %.2f, stime: %.2f' % (
                (int(data[13]) - self.utime) / CLK_TCK,
                (int(data[14]) - self.stime) / CLK_TCK)
