#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
"""Utility generators/functions to execute command line programs.
"""
import shlex, subprocess
from ew.util import ew_logging

logger = ew_logging.getLogger('ew.util.ew_exec')

def command_output(command, **kwargs):
    """Run a command and read stdout using a generator."""
    try:
        args = shlex.split(command)
        p = subprocess.Popen(args, **kwargs)
        out, err = p.communicate()
        for line in out.splitlines(True):
            yield line
        if p:
            p.terminate()
            p = None
    except OSError, e:
        if e.errno != 3:
            logger.error("command_output: %r %r", e, command)
    except ValueError:
        logger.error("command_output: %r %r", e, command)
    except subprocess.CalledProcessError, e:
        raise e

def run_command(command):
    """Run a command with no output"""
    try:
        args = shlex.split(command)
        p = subprocess.Popen(args)
    except OSError, e:
        if e.errno != 3:
            logger.error("run_command: %r %r", e, command)
    except ValueError, e:
        logger.error("run_command: %r %r", e, command)
    except subprocess.CalledProcessError, e:
        raise e
