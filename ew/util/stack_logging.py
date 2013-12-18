#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.

"""Module to log the callers of a function
The logging.Logger.exception method does not provide caller information --
it prints only the portion of the stack below the point of its invocation
down to the occurrence of the exception. (Callers are in the stack *above*
the invocation point.) This module provides functions to make it easy to
log the callers, or the stack in general.

"""

import logging
from traceback import format_list, extract_stack


def log_callers(logger, message, level=logging.DEBUG, limit=None):
    """
    Logs the callers of the function that invokes this function, in
    Python traceback format.
    """
    if logger.isEnabledFor(level):
        log_stack(logger, message, level, limit, -3)


def log_stack(logger, message, level=logging.DEBUG, limit=None, start_index=-1):
    """
    Logs the invocation stack in Python traceback format. By default, the
    stack starts with the function that invokes this function, but the
    start point can be specified through "start_index", which should nearly
      always be negative since the stack is closest-caller-last:
      start_index=-1 (the default) gets the stack starting with the caller
          of this function.
      start_index=-2 gets the stack starting with the caller of the caller
          of this function (see "log_callers" function).
      Other negative values can trim more close callers as desired.
    """
    if logger.isEnabledFor(level):
        logger.log(level, message + '\n' +
                ''.join(format_list(extract_stack(limit=limit)[:start_index])).
                rstrip())
