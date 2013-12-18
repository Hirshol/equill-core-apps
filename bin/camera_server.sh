#!/bin/sh
# Copyright 2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          ews_camera_server
# Required-Start:    $syslog $local_fs ept_early_init ews_initialize_data ews_display_server
# Required-Stop:     $syslog
# Default-Start:     2
# Default-Stop:      0 1 6
### END INIT INFO

# Camera Server system startup script
set -e

getplat() {
    if  uname -r | grep -q "EPT" ; then
	echo "EPT"
    else
	echo "EDO21"
    fi
}
# Must be a valid filename
NAME=camera_server
PIDFILE=/tmp/$NAME.pid
CAM_PIDFILE=/tmp/camera_server.pid
CAMERA_EXE=/usr/local/bin/camera_server
LOGDIR=/data/logs
CAMLOG=$LOGDIR/camera_server.log 
DAEMON_OPTS=""

platform=`getplat`
camera_server()
{
	if [ "on" = "${1}" ]; then
		# launch Camera Server
		export PATH=$PATH:/usr/local/lib/ew/bin
		if [ "$platform" = "EDO21" ] ; then
		   echo "Camera not supported"
		elif [ "$platform" = "EPT" ] ; then
		   modprobe ssd1331
		   modprobe ov564x
		   local campid=`pidof $CAMERA_EXE`
		   if [ "" != "${campid}" ]; then
                        echo "Camera Server already running"
		   else
			mkdir "$LOGDIR" || true
			$CAMERA_EXE | \
	                /usr/local/bin/rotating_log_filter \
                        --max-bytes=500000 --max-backups=10 $CAMLOG &
                        sleep 1
                        pidof $CAMERA_EXE > $CAM_PIDFILE
		   fi
		fi
	elif [ "off" = "${1}" ]; then
		# try to gently shutdown the camera server
		local campid=`pidof $CAMERA_EXE`
		if [ "" != "${campid}" ]; then
			kill -TERM "${campid}" # this is signal 15
		fi
		sleep 1
		iter=5
		while [ "${iter}" -gt "0" ]; do
			local campid=`pidof $CAMERA_EXE`
			if [ "" != "${campid}" ]; then
				sleep 1
			else
				echo "Camera Server process killed with SIGTERM." >&2
				rm -f $CAM_PIDFILE
				return 0
			fi
			iter=$((iter - 1))
		done
		local campid=`pidof $CAMERA_EXE`
		if [ "" != "${campid}" ]; then
			# cannot shut it down, just kill!
			kill -9 "${campid}"
			rm -f $CAM_PIDFILE
		fi
		echo "Camera Server process killed with SIGKILL." >&2
	else
		echo "ERR: camera_server() called without on/off param" >&2
		return 1
	fi

	return 0
}

case "$1" in
  start)
        echo "Starting daemon: "$NAME
        camera_server "on"
        echo "."
	;;
  stop)
        echo "Stopping daemon: "$NAME
	camera_server "off"
        echo "."
	;;
  restart)
        echo "Restarting daemon: "$NAME
	camera_server "off"
        camera_server "on"
	echo "."
	;;
  reload)
        echo "Reloading daemon: "$NAME
	camera_server "off"	
	camera_server "on"
	echo "."
	;;
  foreground)
        echo "Starting daemon on foreground: "$NAME
	$CAMERA_EXE
        echo "."
	;;
  *)
	echo "Usage: "$1" {start|stop|restart|reload|foreground}"
	exit 1
esac


exit 0
