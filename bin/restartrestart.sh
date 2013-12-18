#!/bin/sh
# Copyright 2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          restartrestart
# Required-Start:    $syslog $local_fs ept_early_init ews_initialize_data
# Required-Stop:     $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
### END INIT INFO

# Restart Engine secondary watcher
set -e
cancel() {
    echo "$@"
    exit 1
}

# Must be a valid filename
NAME=restartrestart
DESC='EWS Restart System Watcher'

#This is the command to be run, give the full pathname
DAEMON=/usr/local/lib/ew/python/ew/services/restartrestart.py

test -x "$DAEMON" || cancel "$DAEMON does not exist or is not executable."

case "$1" in
  start)
        echo -n "Starting $DESC: "
        start-stop-daemon --start --quiet --background --make-pidfile --pidfile /tmp/"$NAME".pid \
          --exec "$DAEMON" --
        echo "$NAME."
        ;;  
  stop)     
        echo -n "Stopping $DESC: "
        start-stop-daemon --stop --quiet --oknodo --pidfile /tmp/"$NAME".pid
        echo "$NAME."
        ;;  
  restart)  
        echo -n "Restarting $DESC: "
                start-stop-daemon --stop --quiet --oknodo --pidfile /tmp/"$NAME".pid
        sleep 5
        start-stop-daemon --start --quiet --background --make-pidfile --pidfile /var/run/"$NAME".pid \
          --exec "$DAEMON" --
        echo "$NAME."
        ;;  
  *)        
        echo "Usage: "$1" {start|stop|restart}"
        exit 1
esac        

exit 0
