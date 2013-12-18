#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.

"""Logging config reader
Importing of this module ensures that the logging configuration file has
been read. To use it properly, every module that has a logging.getLogger()
call should have an import of this module before calling logging.getLogger().

For example:
---- my_module.py ---------------
...
import ew.util.ew_logging
...
logger = ew.util.ew_logging.getLogger('my_module')
...
---------------------------------

Note that the getLogger call references method
  (1) "ew.util.ew_logging.getLogger"
instead of
  (2) "logging.getLogger",
which would also work. The reference (1) is preferable because:

  - It can be confusing to import something but never actually reference
    the imported name. If reference (2) is used, a programmer looking at
    the importing module in the future might remove the import, thinking
    it is unused. That would cause mysterious failures in logging.
  - Some IDE's (such as Eclipse/PyDev) flag the import as unused if
    reference (2) is used. Using reference (1) satisfies that demand.
"""

from __future__ import with_statement

import os
import threading
import logging.config

import ew.util.system_config as system_config

_lock = threading.Lock()


# Create a new logging level: VERBOSE -- more verbose than DEBUG.
def set_up_logging():
    VERBOSE = 5
    logging.VERBOSE = VERBOSE
    logging.addLevelName(logging.VERBOSE, 'VERBOSE')
    def verbose(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'VERBOSE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.verbose("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)
    logging.Logger.verbose = verbose
set_up_logging()
del set_up_logging


# Contains the last initialized log file path, which is typically the
# log file used by all modules in this EW process. This variable is
# intended as read-only -- changing it will not affect the logging
# configuration.
log_path = None

def reinitialize(log_name=None, disable_existing_loggers=False,
        log_stderr=False):
    """Initializes logging.
    Logger initialization is performed automatically by simply importing
    this module.
    This method is typically called explicitly only by certain system-level
    modules such as ew.util.daemon.
    Parameters:
      log_name -- the name used to form the log name. If a false value,
        uses the system default log name.
      disable_existing_loggers -- If false (the default), does not disable
        existing, non-explicitly-configured loggers, otherwise it does.
    """
    global log_path
    if not log_name:
        log_name = system_config.log_filename_default
    log_dir = system_config.log_dir.replace('\\', '/')
    log_path = (os.path.join(log_dir, log_name + '.log').replace('\\', '/'))

    log_stderr = log_stderr or os.environ.get("EW_DAEMON_FOREGROUND")
    default_config = {
        "log_dir": log_dir,
        "log_name": log_name,
        "log_path": log_path,
        "stream_handler": (",root_stream_handler" if log_stderr else ""),
    }

    # If logging configuration has not been read, read it now.
    with _lock:
        if not os.path.exists(system_config.log_dir):
            os.makedirs(system_config.log_dir)
        config_file = os.path.join(system_config.config_dir, 'logging.config')
        if os.path.exists(config_file):
            logging.config.fileConfig(config_file, default_config,
                    disable_existing_loggers=disable_existing_loggers)
        else:
            logging.error("EW logging config file not found: %s", config_file)


# Reference to Python's logging.getLogger, to facilitate reference (1) of the
# module comments above.
getLogger = logging.getLogger


reinitialize()
