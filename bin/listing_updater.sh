#!/bin/sh
# Copyright 2010-2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          ews_listing_updater
# Required-Start:    $syslog $local_fs ept_early_init  ews_initialize_data
# Required-Stop:     $syslog
# Default-Start:     2
# Default-Stop:      0 1 6
### END INIT INFO


# Listing Updater system startup script
# Inbox helper daemon
set -e

# Must be a valid filename
NAME=listing_updater
PIDFILE=/tmp/$NAME.pid
#This is the command to be run, give the full pathname
EW_SYSTEM_DIR=/usr/local/lib/ew
DAEMON="nice -n -5 $EW_SYSTEM_DIR/bin/listing_updater.py"
DAEMON_OPTS=""

case "$1" in
  start)
        echo -n "Starting daemon: "$NAME
        # TODO - This sleep is a KLUDGE covering for proper daemon rendezvous
        sleep 2
	$DAEMON $@
        echo "."
	;;
  stop)
        echo -n "Stopping daemon: "$NAME
	$DAEMON $@
        echo "."
	;;
  restart)
        echo -n "Restarting daemon: "$NAME
	shift 1
	$DAEMON stop $@
	$DAEMON start $@
	echo "."
	;;
  reload)
        echo -n "Reloading daemon: "$NAME
	shift 1
	$DAEMON stop $@
	$DAEMON start $@
	echo "."
	;;
  foreground)
        echo -n "Starting daemon on foreground: "$NAME
	$DAEMON $@
        echo "."
	;;
  *)
	echo "Usage: "$1" {start|stop|restart|reload|foreground}"
	exit 1
esac

exit 0

