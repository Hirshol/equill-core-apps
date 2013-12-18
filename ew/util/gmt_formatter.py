#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""Logging formatter producing GMT timestamps"""

import logging, time

class GmtFormatter(logging.Formatter):

    converter = time.gmtime
