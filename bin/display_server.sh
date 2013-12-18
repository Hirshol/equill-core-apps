#!/bin/sh
# Copyright 2010-2011 Ricoh Innovations, Inc.
### BEGIN INIT INFO
# Provides:          ews_display_server
# Required-Start:    $syslog $local_fs ept_early_init ews_initialize_data
# Required-Stop:     $syslog
# Default-Start:     2
# Default-Stop:      0 1 6
### END INIT INFO

# Display Server system startup script
set -e

getplat() {
	echo "EPT"
}
# Must be a valid filename
NAME=display_server
PIDFILE=/tmp/$NAME.pid
#This is the command to be run, give the full pathname
EW_SYSTEM_DIR=/usr/local/lib/ew
DAEMON=$EW_SYSTEM_DIR/bin/display_server
LOGDIR=/data/logs
LOG=$LOGDIR/display_server.log
DAEMON_OPTS=""

platform=`getplat`
display_server()
{

	if [ "on" = "${1}" ]; then
                /usr/local/bin/test_wacom 
		. /usr/local/bin/ts_helper.sh
                modprobe omap3epfb
		modprobe msp430_button
		# tslib-related environment variables
		local DISPLAY_SERVER_PID=/tmp/display_server.pid

		# launch Display Server
		export PATH=$PATH:/usr/local/lib/ew/bin
		    # launch display server
		   
                   #Set kernel verbosity level to show kernel warning messages 
		   #and higher priority messages (error, critical, alert, emergency)
		   echo 5 > /proc/sys/kernel/printk

		   local pid=`pidof $EW_SYSTEM_DIR/bin/display_server`
		   if [ "" != "${pid}" ]; then
                   	echo "Display Server already running"
                   else
		       mkdir "$LOGDIR" || true
		       $EW_SYSTEM_DIR/bin/display_server | \
			   /usr/local/bin/rotating_log_filter \
			   --max-bytes=500000 --max-backups=10 $LOG &
		       sleep 3
		   fi
		   # TODO:  in main_app_lib.sh: search for metronom, rdy, and fclk, and fuji
	elif [ "off" = "${1}" ]; then
		local DISPLAY_SERVER_PID=/tmp/display_server.pid
		# advise display_server to exit
		local pid=`pidof $EW_SYSTEM_DIR/bin/display_server`
		if [ "" != "${pid}" ]; then
			kill -TERM "${pid}" # this is signal 15
		fi
		iter=5
		while [ "${iter}" -gt "0" ]; do
			local pid=`pidof $EW_SYSTEM_DIR/bin/display_server`
			if [ "" != "${pid}" ]; then
				sleep 1
			else
				echo "Display Server process killed with SIGTERM." >&2
				rm -f $PIDFILE
				return 0
			fi
			iter=$(( iter - 1))
		done
			
		# cannot shut it down, just kill!
		local pid=`pidof $EW_SYSTEM_DIR/bin/display_server`
		if [ "" != "${pid}" ]; then
			kill -9 "${pid}" # KEEL KEEL KEEL!
			rm -f $PIDFILE
		fi
		rmmod msp430_button
		rmmod omap3epfb
		echo "Display Server process killed with SIGKILL." >&2
	else
		echo "ERR: display_server() called without on/off param" >&2
		return 1
	fi

	return 0
}

case "$1" in
  start)
        echo "Starting daemon: "$NAME
	#start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
	#display_server "on" "startup_page"
        display_server "on"
        echo "."
	;;
  stop)
        echo "Stopping daemon: "$NAME
	#start-stop-daemon --stop --quiet --oknodo --retry 30 --pidfile $PIDFILE
	display_server "off"
        echo "."
	;;
  restart)
        echo "Restarting daemon: "$NAME
	#start-stop-daemon --stop --quiet --oknodo --retry 30 --pidfile $PIDFILE
	#start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
	display_server "off"
	#display_server "on" "startup_page"
        display_server "on"
	echo "."
	;;
  reload)
        echo "Reloading daemon: "$NAME
	#start-stop-daemon --stop --quiet --oknodo --retry 30 --pidfile $PIDFILE
	#start-stop-daemon --start --quiet --background --pidfile $PIDFILE --exec $DAEMON -- $DAEMON_OPTS
	display_server "off"
	#display_server "on" "startup_page"	
	display_server "on"
	echo "."
	;;
  foreground)
        echo "Starting daemon on foreground: "$NAME
	/usr/local/lib/ew/bin/display_server
        echo "."
	;;
  *)
	echo "Usage: "$1" {start|stop|restart|reload|foreground}"
	exit 1
esac


exit 0
