#!/bin/sh
# Copyright 2010 Ricoh Innovations, Inc.

# Runs a test of "launcher".

test_doc=${EW_TEST_DOC:=inbox}
root=${EW_TEST_DIR:=/usr/local/lib/ew}

# Make sure we have our test memphis document in place.
if [ ! -e /data/inbox/$test_doc.memphis/memphis.document.d/code ]; then
  echo "Test doc not present -- install it..."
  sudo tar -xzvf $root/bin/$test_doc.tgz -C /
fi

# Copy latest version of our DEC code into our test memphis document.
echo 'Copying latest DEC code into document...'
# Set file system read-write mode for some copy operation...
sudo mount / -o remount,rw,noatime
sudo mkdir -p /data/inbox/$test_doc.memphis/memphis.document.d/code
sudo cp $root/python/sdk/samples/a_dec.py \
/data/inbox/$test_doc.memphis/memphis.document.d/code/dec.py
# Set back to read-only mode.
sudo mount / -o remount,ro,noatime

# if "-d" is first argument, delete the GUI save file.
if [ "$1" = "-d" ]; then
  shift
else
  echo 'Deleting any existing GUI save...'
  rm -f /data/inbox/$test_doc.memphis/memphis.document.d/gui_save
fi

# Create the environment for Python to run the launcher.
# Run the launcher.
echo 'Starting launcher...'
export PYTHONPATH=${EW_SYSTEM_DIR:=/usr/local/lib/ew}/${EW_PYTHON_DIR:=python}
exec ./ew/launcher/launcher_daemon.py "$@"

