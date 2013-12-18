#!/bin/sh
# Copyright 2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          ews_initialize_data
# Required-Start:    $syslog $local_fs ept_early_init
# Required-Stop:     $syslog
# Default-Start:     2
# Default-Stop:      0 1 6
### END INIT INFO

# Launcher system startup script
set -e

# Must be a valid filename
NAME=ews_initialize_data
PIDFILE=/var/run/$NAME.pid
#This is the command to be run, give the full pathname
EW_SYSTEM_DIR="/usr/local/lib/ew"
COMMAND="$EW_SYSTEM_DIR/bin/ews_initialize_data.py"
LOGDIR="/data/logs"
LOG="$LOGDIR/ews_initialize_data.log"
export PYTHONUNBUFFERED=y

case "$1" in
  start)
        echo "Starting: $NAME"
	mkdir "$LOGDIR" 2>/dev/null || true 
	python "$COMMAND" 2>&1 | tee -a "$LOG"
        echo "."

	/usr/local/bin/ts_helper.sh
	echo "EWS - INITIALIZE DATA: pointercal: " `stat --printf=%N /tmp/pointercal`

	/usr/local/bin/wpa_helper.sh
	echo "EWS - INITIALIZE DATA: wpa_supplicant: " `stat --printf=%N /tmp/wpa_supplicant.conf`
	;;
  stop)
	# intentionally left blank
	:
	;;
  restart)
	# intentionally left blank
	:
	;;
  *)
	echo "Usage: "$1" {start|stop|restart}"
	exit 1
esac

exit 0

