#!/bin/sh
# Copyright 2010-2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          ews_launcher
# Required-Start:    $syslog $local_fs ept_early_init ews_display_server ews_listing_updater ews_initialize_data
# Required-Stop:     $syslog
# Default-Start:     2
# Default-Stop:      0 1 6
### END INIT INFO

# Launcher system startup script
set -e

# Must be a valid filename
NAME=launcher
PIDFILE=/tmp/$NAME.pid
#This is the command to be run, give the full pathname
export EW_SYSTEM_DIR=/usr/local/lib/ew
export DAEMON="nice -n -5 $EW_SYSTEM_DIR/bin/launcher_daemon.py"
export DAEMON_OPTS=""

launcher_start()
{
	# TODO - This sleep is a KLUDGE covering for proper daemon rendezvous
	sleep 2
	$DAEMON start
}

case "$1" in
  start)
 	echo -n "Starting daemon: "$NAME
	launcher_start $2
        echo "."
	;;
  stop)
        echo -n "Stopping daemon: "$NAME
	$DAEMON stop
	;;
  restart)
        echo -n "Restarting daemon: "$NAME
	$DAEMON stop
	launcher_start $2
	echo "."
	;;
  reload)
        echo -n "Reloading daemon: "$NAME
	$DAEMON stop
	launcher_start $2
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

