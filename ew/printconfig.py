# Copyright 2010 Ricoh Innovations, Inc.
#
# Script to read, parse, and print contents of a config file, such as a
# logger config.
#

import sys
import ConfigParser

args = sys.argv[1:]
paths = args if args else 'dec_logger.config'
print >>sys.stderr, 'config paths:', paths
cp = ConfigParser.ConfigParser()
paths_read = cp.read(paths)
print >>sys.stderr, 'Paths read successfullly:', paths_read
cp.write(sys.stdout)
