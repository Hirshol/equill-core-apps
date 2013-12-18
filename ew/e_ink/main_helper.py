#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.

"""
Helper functions such as handling configuration options.

 - $Id$
 - $HeadURL$
"""
import os
import os.path
import sys

import demo_config

sd_path = '/mnt/sd'

config_usage = """
    Defaults for command line options can be set from a file.

    The CONFIG environment variable specifies the name of the file.
    "options" for "options.py" is used by default. The CONFIG_DIR
    environment variable can specify the directory, otherwise
    /tmp/demo_switcher or /mnt/sd/config/APPLICATION or
    the executable's directory is used. Bash examples::

      CONFIG=options_test program.py
      CONFIG=myoptions CONFIG_DIR=path program.py
"""

def do_options(parser, object=None, directory=None, **options):
    """
    Get defaults for command line options from file specified by
    environment variable, parse command line options, optionally set
    class members (e.g. for 'self' for some object). Parameter
    directory is default directory for file with options, it can
    specified by using a path such as __file__.

    Returns opts, args, ok, msg which are the results
    of parse.parse_args and get_default_options.

    For 'options', see get_default_options.
    """
    ok, msg = get_default_options(parser, directory, **options)

    # ? Wrap parse.parse_args in "try" block?
    (opts, args) = parser.parse_args()

    if object:
        for k in opts.__dict__.keys():
            object.__dict__[k] = opts.__dict__[k]
    opts_dict = {}
    for k in opts.__dict__.keys():
        opts_dict[k] = opts.__dict__[k]

    return opts, opts_dict, args, ok, msg

def get_default_options(parser, default_directory, **options):
    """
    Get defaults for command line options from a file. See config_usage.

    Use __file__ for default_directory to use same directory
    as caller.

    Returns ok, message where ok is True or False based on if
    file is found and message is a string.

    options::
       tmp=False  Do not look in /tmp/demo_switcher
    """
    config = os.environ.get('CONFIG', 'options')
    config_dir = os.environ.get('CONFIG_DIR')
    if config.lower().endswith('.py'):
        config = config[:-3]
    if config_dir:
        ok, msg = default_options_from_file(parser, config, config_dir)
    else:
        ok = False

        tmp_path = demo_config.get_tmp_path()
        if os.path.exists(tmp_path) and options.get('tmp', True):
            ok, msg = default_options_from_file(parser, config, tmp_path)

        if not ok:
            # see if /mnt/sd/config/APPLICATION exists
            # (Make this a function/methon)
            global sd_path
            sd_config_path = os.path.join(sd_path, 'config')
            if os.path.exists(sd_config_path):
                f = os.path.dirname(os.path.abspath(__file__))
                while 1:
                    application = os.path.basename(f)
                    if application == 'bin':
                        f = os.path.dirname(f)
                    else:
                        break
                d = os.path.join(sd_config_path, application)
                if os.path.exists(d):
                    ok, msg = default_options_from_file(parser, config, d)
        if not ok:
            if os.path.isfile(default_directory):
                # allow passing in __file__ or other path to a file,
                # use directory that contains the file
                default_directory = os.path.dirname(default_directory)
            ok, msg = default_options_from_file(
                parser, config, default_directory)
    return ok, msg

def default_options_from_file(parser, name, directory):
    """
    If module 'name' exists (e.g. options.py), use it to set
    defaults for command line options. parser is an optparse.OptionParser
    object.
    """
    if not name:
        name = 'options'
    if not directory:
        directory = os.path.curdir
    p = os.path.join(directory, name + '.py')
    if not os.path.exists(p):
        return (False, 'Not using an file with option defaults.')
    save = sys.path
    sys.path = [directory]
    options = __import__(name)
    sys.path = save
    msg = 'Using "%s" for option defaults' % p

    defaults = {}
    for obj in parser.option_list:
        k = obj.dest
        if (not k is None) and (options.__dict__.has_key(k)):
            defaults[k] = options.__dict__[k]

    parser.set_defaults(**defaults)
    return (True, msg)

def cgi_header_html():
    """Return a string with a HTTP header for a text/html response."""
    return """CONTENT-TYPE: text/html
CACHE-CONTROL: NO-CACHE
PRAGMA: NO-CACHE
EXPIRES: 0

"""

def cgi_header_text():
   """Return a string with a HTTP header for a text/plain response."""
   return """CONTENT-TYPE: text/plain
CACHE-CONTROL: NO-CACHE
PRAGMA: NO-CACHE
EXPIRES: 0

"""

if __name__ == "__main__":
    print "This python module is a library for use by other python programs."
