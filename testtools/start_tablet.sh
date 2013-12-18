#!/bin/sh
# Copyright 2010 Ricoh Innovations, Inc.
# This wants to run a pretty regular launcher and environment automatically
# starting the Inbox. 
# author - Samantha Atkins


root=/usr/local/lib/ew
python_path=$root/python
ew_bin=$root/bin
ew_internal=/data/internal_decs
ew_docs=/data/inbox
my_doc=$ew_docs/Inbox_Document

# Create the environment for Python to run the new device software
# Run the daemons
echo 'Starting launcher...'
exec sudo \
  EW_INITIAL_DOC=$my_doc PYTHONPATH=$python_path $ew_bin/launcher_daemon.py "$@"
echo 'Starting ListingsUpdater...'

