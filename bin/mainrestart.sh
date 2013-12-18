#!/bin/sh
# Copyright 2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          mainrestart
# Required-Start:    $syslog $local_fs ept_early_init ews_initialize_data
# Required-Stop:     $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
### END INIT INFO

# Restart engine system startup script
set -e
cancel() {
    echo "$@"
    exit 1
}

# Must be a valid filename
NAME=mainrestart
DESC='EWS Restart System'

#This is the command to be run, give the full pathname
DAEMON=/usr/local/lib/ew/python/ew/services/mainrestart.py
export EW_SYSTEM_DIR=/usr/local/lib/ew

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
  status)      
       NETWORK_MANAGER_PID=`pgrep -f '/usr/local/bin/network_manager.py'` || true
       POWER_MANAGER_PID=`pgrep -f '/usr/local/bin/power_manager.py'` || true
       AUDIO_MANAGER_PID=`pgrep -f '/usr/local/bin/audio_manager.py'` || true
       CAMERA_SERVER_PID=`pgrep -f '/usr/local/bin/camera_server'` || true
       DS_PID=`pgrep -f $EW_SYSTEM_DIR'/bin/display_server'` || true
       LAUNCHER_PID=`python $EW_SYSTEM_DIR/python/ew/util/daemon.py launcher_daemon` || true
       LISTING_PID=`python $EW_SYSTEM_DIR/python/ew/util/daemon.py listing_updater` || true
       SYNC_PID=`python $EW_SYSTEM_DIR/python/ew/util/daemon.py tablet_sync` || true
       MAINRESTART_PID=`pgrep -f  /usr/local/lib/ew/python/ew/services/mainrestart.py` || true
       RESTARTRESTART_PID=`pgrep -f  /usr/local/lib/ew/python/ew/services/restartrestart.py` || true

       echo "EW Processes:
       network_manager    $NETWORK_MANAGER_PID
       power_manager    $POWER_MANAGER_PID
       audio_manager       $AUDIO_MANAGER_PID
       camera_server       $CAMERA_SERVER_PID
       display_server       $DS_PID
       launcher_daemon.py   $LAUNCHER_PID
       listing_updater.py   $LISTING_PID
       sync_daemon.py       $SYNC_PID
       mainrestart.py       $MAINRESTART_PID
       restartrestart.py    $RESTARTRESTART_PID"
       /usr/local/bin/rmanage list 
       ;;

  *)        
        echo "Usage: "$1" {start|stop|restart}"
        exit 1
esac        

exit 0
