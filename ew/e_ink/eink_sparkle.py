#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
"""
Python interface to trackupdate Eink display with Sparkle.

See README for information about trackupdate binaries used.

 - $Id$
 - $HeadURL$
"""

import socket
import subprocess
import os.path
import time
import shutil
import signal
import commands

#import Sparkle
import demo_config
from ew.util import ew_logging

logger = ew_logging.getLogger('ew.e_ink.eink_sparkle')

class EinkSparkle:
    """
    Python interface to display_server Eink display with Sparkle.
    """
    LIVEINK="/tmp/PTU_inkimage.pgm"
    LIVESTROKES="/tmp/PTU_stroke.ink"

    WHITE_FORM="/tmp/white.ppm"
    UPDATE_LONG_CMD= ""
    UPDATE_SHORT_CMD= ""
    WAVEFORM_FNAME = "sparkle-merge-d6c5-choose-24.wf"
    WAVEFORM_DST = "/tmp"
    PTU_BINARY = "display_server"

    def __init__(self, homeDir, strokesFile, **options):
        """

        Parameter homeDir is currently not used, OK to use None.
        Parameter strokesFile is optional, can use None.

        options::
          logfile='/tmp/display_server.log'
          verbose=True                    output DEBUG messages
        """
        #if options.get('verbose'):
        #    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s')
        # self.binDir1 = homeDir + "bin"
        # self.binDir2 = homeDir + "bin/Sparkle"
        self.binDir1 = os.path.dirname(os.path.abspath(__file__))
        # self.binDir2 = os.path.join(self.binDir1, 'Sparkle')
        self.logFile = options.get('logfile', "/tmp/display_server.log")
        #Get PTU_BINARY based on kernel settings
        try:
            machtype = subprocess.Popen(["uname", "-m"], stdout=subprocess.PIPE).communicate()[0]
            EinkSparkle.PTU_BINARY = 'display_server_' + machtype.strip()
        except IOError:
            logger.debug('Error finding machtype with uname -m')

        self.cmdTrackupdate = os.path.join(
            self.binDir1, EinkSparkle.PTU_BINARY + " &> " + self.logFile)
        self.strokesFile = strokesFile
        self.pid = None
        self.own_display_server = False
        wf_dst = os.path.join(EinkSparkle.WAVEFORM_DST, EinkSparkle.WAVEFORM_FNAME)
        self.ptu_socket = "local" # "multicast" or "local"
        self.ptu = None
        self.ptu_tsscale = 1
        if not os.path.exists(wf_dst):
            wf_src = os.path.join(self.binDir1, "resources",
                                  EinkSparkle.WAVEFORM_FNAME)
            if os.path.exists(wf_src):
                os.symlink(wf_src, wf_dst)
            else:
                raise Exception('EinkSparkle: neither %s nor %s found'%
                                (wf_dst, wf_src))

    def __del__(self):
        """Call cleanup()"""
        self.cleanup()

    def cleanup(self):
        """Clear E-Ink and stop Display server."""
        logger.debug("EinkSparkle.cleanup()")
        try:
            self.whipeOut()
            # Wait?
            self.stop()
        except socket.error, ex:
            logger.warning("Exception '%s' occured in EinkSparkle.clearup()", ex)


    def strokesInit(self):
        """
        Initialize stroke file.
        """
        if not self.strokesFile:
            logger.warning('Strokes file not specified.')
        try:
#            os.remove(self.strokesFile)
            f1 = open(self.strokesFile, "w")
            f1.truncate()
            f1.write("1 1\n-1 -1\n")
            f1.close()
        except OSError:
            logger.warning("could not delete %s", self.strokesFile)

    def trackupdate_pid(self):
        """
        Determine PID of trackupdate process from file. If no PID file
        exists, search by executable name.

        If the process that matches the PID file does not exist, should
        a search for the process be made?  Should more than one possible
        name for the binary be searched for?
        """
        pf = '/tmp/display_server.pid'
        if not os.path.exists(pf):
            pids = commands.getoutput('/bin/pidof '+ EinkSparkle.PTU_BINARY).split()
            int_pids = [int(i) for i in pids if i.isdigit]
            if int_pids:
                minpid = min(int_pids)
                logger.warning(
                    "Cannot find file /tmp/display_server.pid, 'pidof %s' resulted in %d",
                    EinkSparkle.PTU_BINARY, minpid)
                return minpid
            logger.warning(
                "Cannot find file /tmp/display_server.pid and 'pidof %s' produced no results",
                EinkSparkle.PTU_BINARY)
            return None
        try:
            f = open(pf)
            s = f.read()
            f.close()
            s = s.strip()
            if s:
                pid = int(s)
                return pid
        except Exception, ex:
            logger.warning("'%s':\n%s", pf, ex)
        return None


    def start(self, **opt):
        """
        Start Eink and pentracking server with Sparkle.

        opt can be any valid environment setting for the server,
        e.g. PTU_TSSCALE='1' (EDO screen resolution, lowest resolution) or
        PTU_TSSCALE='16' (highest resolution). (All settings are strings,
        but integers will be converted to strings as a convenience).

        more opt::

           enable_strokes=True          # turn on stokes
           enable_strokes=False         # turn off stokes
           PyPenTrackUpdate_options={}  # Options passed to
                                          Sparkle.PyPenTrackUpdate

        """
        logger.debug("EinkSparkle.start()")
        if self.connect_to_server(**opt.get('PyPenTrackUpdate_options', {})):
            v = opt.get('enable_strokes')
            if v in [True, False]:
                self.ptu.enableStrokes(v)
            self.pid = self.trackupdate_pid()
            self.own_display_server = False
            logger.debug("Using already runnning Eink server")
            return
        # /etc/profile on EDO normally sets TSLIB_TSDEVICE
        # so the overide from os.environ is normally used
        tsdevice = "/dev/input/touchscreen"
        if not os.path.exists(tsdevice):
            tsdevice = "/dev/ttyUSB0"
        if not os.path.exists(tsdevice):
            tsdevice = ''
        ts_env = {  # defaults
            "TSLIB_CONFFILE" : "/usr/local/etc/ts.conf",
            "TSLIB_CALIBFILE" : "/usr/local/etc/pointercal",
            "TSLIB_CONSOLEDEVICE" : "none",
            "TSLIB_FBDEVICE" : "/dev/fb2",
            "TSLIB_PLUGINDIR" : "/usr/local/share/ts/plugins",
            "TSLIB_TSDEVICE" : tsdevice,
            "PTU_SOCKET" : self.ptu_socket, # "multicast" or "local"
            "PTU_SENDSOCKET" : self.ptu_socket, # "multicast" or "local"
            "PTU_PENWIDTH" : "3", #width of pen stroke in pixels
            "PTU_STYLUSWIDTH" : "1", #width of stylus (with button) stroke in pixels
            "PTU_ERASERWIDTH" : "15", #width of eraser in pixels
            "PTU_TSSCALE" : "1"
        }
        # override defaults from options passed in or environment
        keys = ts_env.keys() + ['PTU_NFRAMES_DIRECT_MULTIPLIER', 'PTU_NSPARKLES',
                                'PTU_SPARKLESPREAD','PTU_IGNORE','PTU_SPARKLEDELAY']
        for k in keys:
            v = opt.get(k)
            if not v is None:
                if type(v) == type(1):
                    v = str(v)
                ts_env[k] = v
            else:
                v = os.environ.get(k)
                if not v is None:
                    logger.debug("Setting '%s' to '%s' from environment",
                            k, v)
                    ts_env[k] = v
        self.ptu_tsscale = int(ts_env['PTU_TSSCALE'])
        if (self.ptu_tsscale < 1) or (self.ptu_tsscale > 16):
            raise Exception ('PTU_TSSSCALE is %d, not in [0..16]' %
                             self.ptu_tsscale)
        logger.debug("EinkSparkle.start(): using %s with SCALE %d",
                      ts_env['TSLIB_TSDEVICE'], self.ptu_tsscale)
        try:
            os.remove(self.logFile)
        except OSError:
            logger.warning("could not delete %s", self.logFile)

        try:
            trackupdate = subprocess.Popen(self.cmdTrackupdate, env = ts_env, shell=True, close_fds=True)
            self.pid = trackupdate.pid
            self.own_display_server = True
            time.sleep(2)
            logger.debug("EinkSparkle.start(): display_server PID %s", self.pid)
        except OSError:
            logger.exception('')

        ex = ''
        for _ in range(30):
            logger.debug("EinkSparkle.start(): connecting...")
            if self.connect_to_server(**opt.get('PyPenTrackUpdate_options', {})):
                break
            time.sleep(0.3)
        if not self.ptu:
            raise Exception(
               'Cannot connect to %s.\n%s', EinkSparkle.PTU_BINARY, ex)
        v = opt.get('enable_stokes')
        if v in [True, False]:
            self.ptu.enableStrokes(v)
        logger.debug("EinkSparkle.start(): done")



    def connect_to_server(self, **options):
        """
        Attempt to connect to Display Server, used by start().
        options are passed to sparkle.PenTrackUpdate.
        """
        from PyPenTrackUpdate import PenTrackUpdate
        try:
            self.ptu = PenTrackUpdate(ptu_socket=self.ptu_socket,
                                              **options)
        except socket.error, _:
            self.ptu = None
        return self.ptu

    def stop(self, **opts):
        """
        Stop Display Server. By default, only kill Display Server if
        this process started it.

        opts::
            force=True   Stop Display Server even if this object
                         did not start it.
        """
        logger.debug("EinkSparkle.stop()")

        self.ptu = None
        all_pids = []
        if opts.get('force') and not self.pid:
            self.pid = self.trackupdate_pid()
        try:
            if self.pid and (self.own_display_server or opts.get('force')):
                logger.debug('Killing Display Server PID %s', self.pid)
                all_pids = demo_config.find_child_processes(self.pid)
                os.kill(int(self.pid), signal.SIGINT)
                # os.kill(self.pid, signal.SIGHUP)
                # os.system("killall -q " + EinkSparkle.PTU_BINARY)

        except OSError:
            logger.debug("display_server process not found")
        self.pid = None
        self.own_display_server = False

        # if necessary, merge strokes
        if self.strokesFile:
            f1 = open(self.strokesFile, "a")
            try:
                f2 = open(EinkSparkle.LIVESTROKES, "r")
                f2lines = f2.readlines()
                for f2line in f2lines:
                    f1.write(f2line)
                f2.close()
            except Exception:
                logger.exception("%s not found", EinkSparkle.LIVESTROKES)
            f1.close()

        # If processes are still running, first try to kill them,
        # If that doesn't work, try kill -9.
        demo_config.kill_processes_in_list(all_pids)

        logger.debug("EinkSparkle.stop(): done")

    def whipeOut(self, erasestrokes=False, flash=False, gc=False):
        """
        Clear E-Ink display.
        Normally returns True. Returns False if image does not exist.
        """
        logger.debug("EinkSpakle.whipeOut()")
        if not os.path.exists(EinkSparkle.WHITE_FORM):
            logger.error (
                'EnkSparkle.requestNormal: image "%s" does not exist.',
                EinkSparkle.WHITE_FORM)
            return False
        if self.ptu:
            try:
                opt = {}
                if erasestrokes:
                    opt['erasestrokes']=True
                if flash:
                    opt['flash']=True
                if gc:
                    opt['gc']=True
                self.ptu.sendimg(0, 0, EinkSparkle.WHITE_FORM, opt)
            except TypeError:
                try:
                    # Old API
                    self.ptu.sendimg(0, 0, EinkSparkle.WHITE_FORM, False)
                except TypeError:
                    # Old API
                    self.ptu.sendimg(0, 0, EinkSparkle.WHITE_FORM)
        return True

    def requestClean(self, image):
        """
        No need to clean with sparkle? Or writing white still
        needed at start? Use requestNormal() instead.
        """
        logger.debug("EinkSparkle.Clean()")
        self.requestNormal(image)

    def setInputFB(self, fbname=None, w=0, h=0):
        """
        Register a framebuffer to use for sendfbimage. The file should
        be a w-by-h array of 8-bit graymap pixels. If fname is not
        specified or zero length, the display server will simply clear
        and unmap any previously-set frame buffer.
        """
        self.ptu.setInputFb(fbname, w, h)

    def requestInputFB(self, xDest=0, yDest=0, xSrc=0, ySrc=0, wSrc=0, hSrc=0, requestid=0, **opts):
        """
        Put image on E-Ink display from framebuffer that was
        previously set using setInputFB(). Optionally limit update to
        a rectangular region of frame buffer with top-left corner
        (xSrc, ySrc) and size (wSrc x hSrc). If requestid is non-zero,
        server will send an event when read has been completed (events
        can be received by registering an onReadComplete() callback in
        StrokeListener.py). Returns True.

        opts::
          rot=True          rotate images so right way up on EDO
          rotate=True       (same as 'rot')
          erasestokes=True  erase all strokes while drawing image (image should span entire screen, or at least all strokes)
        """
        logger.debug(
            "requestInputFb(dest=(%d, %d), requestid=%d, window=(%d, %d),%d x %d)",
            xDest, yDest, requestid, xSrc, ySrc, wSrc, hSrc)
        options = opts
        if options.has_key('rotate'):
            options = opts.copy()
            options['rot'] = options['rotate']
            del options['rotate']
        if self.ptu:
            self.ptu.sendFBWindow(xDest, yDest, requestid, xSrc, ySrc, wSrc, hSrc, options)
        return True

    def requestWindow(self, image=None, xDest=0, yDest=0, xSrc=0, ySrc=0, wSrc=0, hSrc=0, requestid=0, **opts):
        """
        Put image on E-Ink display from PGM file. Optionally limit
        update to a rectangular region of frame buffer with top-left
        corner (xSrc, ySrc) and size (wSrc x hSrc). If requestid is
        non-zero, server will send an event when read has been
        completed (events can be received by registering an
        onReadComplete() callback in StrokeListener.py). Returns false
        if image file does not exist, otherwise returns True.

        opts::
          rot=True          rotate images so right way up on EDO
          rotate=True       (same as 'rot')
          erasestokes=True  erase all strokes while drawing image (image should span entire screen, or at least all strokes)
          flash=True        'flash' to deghost instead of sparkle
          asink=True        write to ink layer instead of framebuffer (with white == transparent)
        """
        logger.debug(
            "requestInputFb(dest=(%d, %d), requestid=%d, window=(%d, %d),%d x %d)",
            xDest, yDest, requestid, xSrc, ySrc, wSrc, hSrc)
        options = opts
        if not os.path.exists(image):
            logger.error (
                'EnkSparkle.requestWindow: image "%s" does not exist.', image)
            return False
        if options.has_key('rotate'):
            options = opts.copy()
            options['rot'] = options['rotate']
            del options['rotate']
        if self.ptu:
            self.ptu.sendImgWindow(image, xDest, yDest, xSrc, ySrc, wSrc, hSrc, requestid, options)
        return True

    def requestNormal(self, image, x=0, y=0, **opts):
        """
        Put image on E-Ink display.
        Normally returns True. Returns False if image does not exist.

        opts::
          rot=True          rotate images so right way up on EDO
          rotate=True       (same as 'rot')
          erasestokes=True  erase all strokes while drawing image (image should span entire screen, or at least all strokes)
          flash=True        instead of sparkle, do a flashing deghosting after direct-drive drawing
          asink=True        write to ink buffer instead of background
          gc=True           use normal Grayscale Clear waveforms instead of direct-drive drawing (implies nodeghost)
          nodeghost=True    don't do sparkle or flash deghosting
        """
        logger.debug("EinkSparkle.Normal(%s)", image)
        options = opts
        if not os.path.exists(image):
            logger.error (
                'EnkSparkle.requestNormal: image "%s" does not exist.', image)
            return False
        if options.has_key('rotate'):
            options = opts.copy()
            options['rot'] = options['rotate']
            del options['rotate']
        if self.ptu:
            try:
                self.ptu.sendimg(x, y, image, options)
            except TypeError:
                try:
                    # Old API
                    self.ptu.sendimg(x, y, image, options.get('rot', False))
                except TypeError:
                    # Old API
                    self.ptu.sendimg(x, y, image)
        return True

    def requestQuick(self, image):
        """
        Put image on E-Ink display 'quick'. Use requestNormal instead.
        """
        logger.debug("EinkSparkle.Quick()")
        self.requestNormal(image)

    def send(self, data):
        """
        send(data[, port[, addr]]) - multicasts a UDP datagram.
        Not implemented."""
        raise Exception("send not implemented for EinkSparkle")

    def requestNewImage(self, imagename):
        """
        Prepare a command string to send via socket to display_server.
        Not implemented.
        """
        raise Exception("requestNewImage not implemented for EinkSparkle")


    def markInkOnPage(self, file,ink,dest=None):
        """
        Take the ink pgm file and apply to file, result is put in dest
        or original if no dest.
        """
        if dest!=None:
            outname = dest
        else:
            outname = "/tmp/merged_image.pgm"

        os.system('pnmarith -min %s %s >%s' % (file,ink,outname))
        if dest==None:
            shutil.move(outname,file)

    def enableSparkle(self,**options):
        '''Pass these options to PyPenTrackUpdate.py.'''
        self.ptu.enableSparkle(options)

    def enableAutoSparkle(self,enabled):
        '''Pass these options to PyPenTrackUpdate.py.'''
        self.ptu.enableAutoSparkle(enabled)

    def erase(self, start=0, end=65000):
        """
        Erase strokes.
        START and END are 'frame' values from the display server.
        Example using pyedo.Stroke() object::
          frame = self.strokes.live_strokes[-1]['frame']
        Example for inside callback from Strokes.group_strokes()::
          frame = strokes[start_idx]['frame']
        """
        logger.debug("EinkSparkle.Erase:")
        if self.ptu:
            self.ptu.erase_strokes(start, end)

    def process_exists(self):
        """Check is Display Server (main) process exists."""
        return demo_config.process_exists(self.pid)
