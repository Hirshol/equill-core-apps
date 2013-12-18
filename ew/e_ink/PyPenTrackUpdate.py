#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.

"""
Communicate with pentrackupdate server on EDO.

$Id: PyPenTrackUpdate.py 4531 2009-10-29 23:23:52Z rhodes $
$HeadURL: svn://yesbox/edo_apps/pentrackupdate/trunk/bin/PyPenTrackUpdate.py $
"""

DEFAULT_PORT=10021
DEFAULT_ADDR ='234.0.0.1'
DEFAULT_LOCAL_ADDR = '/tmp/PTU_localsocket'

import socket
import sys
import time
from struct import pack
import optparse
import os.path

from ew.util import ew_logging
from ew.util import comms

logger = ew_logging.getLogger('ew.e_ink.PyPenTrackUpdate')

class PenTrackUpdate:

    """
    Communicate with pentrackupdate server on EDO over a socket.
    """
    def __init__(self, **options):
        """
        Open socket. Try network INET socket first, if this fails,
        use local UNIX socket.
        """
        self.verbose = options.get('verbose')
        self.port = options.get('ptu_port', DEFAULT_PORT)
        self.addr = options.get('ptu_addr', DEFAULT_ADDR)
        self.ptu_socket_type = options.get('ptu_socket', 'local')
        self.ptu_local_address = options.get('ptu_local_address',
                DEFAULT_LOCAL_ADDR)
        if self.ptu_socket_type == 'multicast':
            try:
                # Create the socket
                self.mode = socket.AF_INET
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Make the socket multicast-aware, and set TTL.
                # Change TTL (=20) to suit
                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20) 
            except socket.error, ex:
                if self.verbose:
                    print 'trying local socket because: ' + str(ex)
                logger.debug('trying local socket because: %s', ex)
                self.ptu_socket_type = 'local'
                self.sock = None
        if self.ptu_socket_type == 'local':
            self.mode = socket.AF_UNIX
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            for n in xrange(20):
                try:
                    self.sock.connect(self.ptu_local_address)
                    break
                except socket.error:
                    time.sleep(2)
                    if self.verbose:
                        print 'Failed to connect to socket.. retrying.'
                    logger.debug('Failed to connect to socket.. retrying %r',
                            n + 1)
            else:
               self.sock.connect(self.ptu_local_address)
        if not self.sock:
            raise Exception('Bad socket type or could not create socket.')

    def send(self, data):
        """Multicasts a UDP datagram."""
        def do_send():
            #logger.debug('Starting datagram send')
            if self.mode == socket.AF_INET:
                # Send the data
                self.sock.sendto(data, (self.addr, self.port))
            elif self.mode == socket.AF_UNIX:
                self.sock.send(data)
            else:
                raise Exception("Bad mode in PenTrackUpdate.send.")
            #logger.debug('Completed datagram send')
        comms.try_until_connected('pentrackupdate server', do_send, logger,
                try_count=30)

    def enableStrokes(self, enabled):
        """
        Tell server to enable or disable strokes.
        """
        if (enabled):
            cmd = 8
        else:
            cmd = 7
        data = pack('!HH',0,cmd)
        if self.verbose:
            print 'cmd=%d' % cmd
        self.send(data)
        
    def enableAutoSparkle(self, enabled):
        if (enabled):
            cmd = 13
        else:
            cmd = 12
        data = pack('!HH',0,cmd)
        if self.verbose:
            print 'enableAutoSparkle(%s): cmd=%d' % (enabled, cmd)
        self.send(data)
            
    def enableSparkle(self, options):
        """
        Tell server to enable or disable sparkling of certain types.
        """
        cmd = 14
        # first look for disabling sparkle
        typemask = 0
        if (options.get('nostrokes')):
            typemask = typemask + 1
        if (options.get('noimages')):
            typemask = typemask + 2
        if (typemask != 0):
            data = pack('!HHH',0,cmd,typemask)
            if self.verbose:
                print 'cmd=%d (disable sparkle)' % cmd
                print 'typemask=%d' % typemask
            self.send(data)

        # now look for enabling sparkle
        cmd = 15
        typemask = 0
        if (options.get('strokes')):
            typemask = typemask + 1
        if (options.get('images')):
            typemask = typemask + 2
        if (typemask != 0):
            data = pack('!HHH',0,cmd,typemask)
            if self.verbose:
                print 'cmd=%d (enable sparkle)' % cmd
                print 'typemask=%d' % typemask
            self.send(data)
        
    def setInputFB(self, fbname=None, w=0, h=0):
        """
        Register a framebuffer to use for sendfbimage. The file should
        be a w-by-h array of 8-bit graymap pixels. If fbname not
        given, unsets inputFB.
        """
        cmd = 17
        opt = 0
        if fbname != None:
            fbname = os.path.abspath(fbname);
            if isinstance(fbname,unicode):
                fbname = fbname.encode('utf8')
            namelen = len(fbname)
            data = pack('!HHHHHH%ds' % namelen,0,cmd,opt,w,h,namelen,fbname)
            if not os.path.exists(fbname):
                raise Exception('Framebuffer "%s" does not exist' % fbname)
        else:
            namelen = 0
            data = pack('!HHHHHH',0,cmd,opt,w,h,namelen)

        if self.verbose:
            print 'cmd=%d' % cmd
            print 'opt=%d' % opt
            print '(w,h)=(%d, %d)' % (w, h)
            print 'namelen=%d' % namelen
            print 'fbname=%s' % fbname
            print 'len(data)=%d' % len(data)
            hexdata = ''.join(['%02x ' % ord(i) for i in data])
            print 'data=%s' % hexdata
        self.send(data)

    def sendInputFBWindow(self, xDest=0, yDest=0, xSrc=0, ySrc=0, wSrc=0, hSrc=0, requestid=0, options={}):
        return self.sendImgWindow(None, xDest, yDest, xSrc, ySrc, wSrc, hSrc, requestid, options)

    def sendImgWindow(self, imagename=None, xDest=0, yDest=0, xSrc=0, ySrc=0, wSrc=0, hSrc=0, requestid=0, options={}):
        """
        Tell server to draw image IMAGENAME at position (xDest,yDest).
        The image must either be a valid PGM file with 8-bit depth, or
        None. If None, display server will use frame buffer previously
        set with setInputFB.

        (xSrc, ySrc) and (wSrc,hSrc) specify the top-left corner and
        dimensions of a window within the given image or framebuffer
        that should be drawn. A value of 0 for w or h will default to
        the width of the entire image or framebuffer.

        requestid: If requestid is non-zero, application will receive
        notification when server has completed read of the image or
        framebuffer. This can be captured using the onReadComplete()
        callback in SocketListener.py.
        """
        # print('sendimg(self, %s, %d, %d, %d, %d, %d, %d, %d, %s)' % (imagename, xDest, yDest, xSrc, ySrc, wSrc, hSrc, requestid, options))
        cmd = 18
        opt = 0
        if (options.get('rot')):
            opt = opt + 1
        if (options.get('erasestrokes')):
            opt = opt + 2
        if (options.get('flash')):
            opt = opt + 4
        if (options.get('asink')):
            opt = opt + 8
        if (options.get('gc')):
            opt = opt + 16
        if (options.get('nodeghost')):
            opt = opt + 32

        #Note if imagename is a str we just pass it through, even if it contains 0xff chars
        if (imagename != None):
            imagename = os.path.abspath(imagename)
            if isinstance(imagename,unicode):
                imagename = imagename.encode('utf8')
            namelen = len(imagename)
            data = pack('!HHHHHHHHHHH%ds' % namelen,0,cmd,opt,xDest,yDest,xSrc,ySrc,wSrc,hSrc,requestid,namelen,imagename)
        else:
            namelen = 0
            data = pack('!HHHHHHHHHHH',0,cmd,opt,xDest,yDest,xSrc,ySrc,wSrc,hSrc,requestid,namelen)
            
        if self.verbose:
            print 'cmd=%d' % cmd
            print 'opt=%d' % opt
            print '(xDest,yDest)=(%d, %d)' % (xDest, yDest)
            print '(xSrc,ySrc)=(%d, %d)' % (xSrc, ySrc)
            print '(wSrc,hSrc)=(%d, %d)' % (wSrc, hSrc)
            print 'requestid=%d' % requestid
            print 'namelen=%d' % namelen
            print 'imagename=%s' % imagename
            print 'len(data)=%d' % len(data)
            hexdata = ''.join(['%02x ' % ord(i) for i in data])
            print 'data=%s' % hexdata
        if (imagename != None):
            if not os.path.exists(imagename):
                raise Exception('Image "%s" does not exist' % imagename)
        self.send(data)

    def sendimg(self, x, y, imagename, options):
        """
        Tell server to draw image IMAGENAME at position X,Y. The image
        must be a valid PGM file.
        """
        imagename = os.path.abspath(imagename)
        cmd = 0
        opt = 0
        if (options.get('rot')):
            opt = opt + 1
        if (options.get('erasestrokes')):
            opt = opt + 2
        if (options.get('flash')):
            opt = opt + 4
        if (options.get('asink')):
            opt = opt + 8
        if (options.get('gc')):
            opt = opt + 16
        if (options.get('nodeghost')):
            opt = opt + 32

        #Note if imagename is a str we just pass it through, even if it contains 0xff chars
        if isinstance(imagename,unicode):
            imagename = imagename.encode('utf8')

        namelen = len(imagename)
        data = pack('!HHHHHH%ds' % namelen,0,cmd,opt,x,y,namelen,imagename)
        if self.verbose:
            print 'cmd=%d' % cmd
            print 'opt=%d' % opt
            print '(x,y)=(%d, %d)' % (x, y)
            print 'namelen=%d' % namelen
            print 'imagename=%s' % imagename
            print 'len(data)=%d' % len(data)
            hexdata = ''.join(['%02x ' % ord(i) for i in data])
            print 'data=%s' % hexdata
        if not os.path.exists(imagename):
            raise Exception('Image "%s" does not exist' % imagename)
        self.send(data)

    def cleanup_and_exit(self):
        """
        Tell pentrackupdate server to exit after doing any necessary cleanup.
        """
        cmd = 10
        opt = 0
        data = pack('!HHH',0,cmd,opt);
        self.send(data)

    def change_config_var(self, var, val, opt=0):
        """
        Tell display server to change config environment variable (only implemented for partial set)
        """
        cmd = 23
        fmt = '!HHHH' + str(len(var)) + 'sH' + str(len(val)) + 's'
        pargs = [0,cmd,opt,len(var),var,len(val),val]
        data = pack(fmt, *pargs);
        self.send(data)

    def send_command(self, cmd, args=[], opt=0):
        """
        Send an arbitrary command to the pentrackupdate server
        """
        fmt = '!HHH'
        pargs = [0,cmd,opt]
        for arg in args:
            if arg.isdigit():
                fmt += 'H'
                pargs.append(int(arg))
            else:
                if isinstance(arg,unicode):
                    arg = arg.encode('utf8')
                fmt += 'H' + str(len(arg)) + 's'
                pargs.append(len(arg))
                pargs.append(arg)

        # print 'send_command:'
        # print fmt
        # print pargs
        data = pack(fmt, *pargs);
        self.send(data)

    def erase_strokes(self, start=0, end=65000):
        """
        Tell pentrackupdate server to erase a range of strokes via a socket.
        """
        cmd = 3
        opt = 0
        data = pack('!HHHHH',0,cmd,opt,start,end);
        self.send(data)

    def start_page_flipping(self, fpfFile, framesPerPage=0, startPage=0, rev=False, waitForCleanup=False):
        """
        Tell display server to start doing fast page flipping of FPF
        file, with given frames per page (0=stopped) and start
        page. Application is responsible for displaying starting page
        before calling this function.
        """
        if self.verbose:
            print('start page flipping: %s, framesPerPage=%d, startPage=%d, rev=%s, waitForCleanup=%s' % (fpfFile, framesPerPage, startPage, rev, waitForCleanup))
        if not os.path.exists(fpfFile):
            raise Exception('FPF file "%s" does not exist' % fpfFile)
        optflags = 0
        if rev:
            optflags |= 0x1
        if waitForCleanup:
            optflags |= 0x2
        self.send_command(6, [str(framesPerPage), str(startPage), fpfFile], optflags);

    def draw_grayscale_after_page_flipping(self, pageFile, flash=False, requestid=0):
        """
        Tell display server to draw full-grayscale version of page,
        for use when waitForCleanup option is used when calling
        start_page_flipping. Should be called after receiving an
        onPageStop() callback, and before any other draw commands.
        """
        if self.verbose:
            print 'draw_grayscale_after_page_flipping: %s' % (pageFile)
        if not os.path.exists(pageFile):
            raise Exception('page image file "%s" does not exist' % pageFile)
        if flash:
            self.send_command(22, [str(requestid), pageFile], 1);
        else:
            self.send_command(22, [str(requestid), pageFile], 0);

    def clear_flip_stop_page(self):
        """
        Clear out stop page that was set with flip_to_next_page or
        flip_to_stop_page.
        """
        self.send_command(20, [])
        if self.verbose:
            print('clearing stop page')
            
    def flip_to_next_page(self, fpp=0, rev=False):
        """
        Tell display server to increment (decrement if rev is True) to
        next page. This is additive, so calling it three times in a
        row will increment three pages, even if all three were called
        while the first page was still being rendered.
        """
        if (rev):
            self.send_command(21, [str(fpp)], 1)
            if self.verbose:
                print("decrementing page by one (fpp=%d)" % (fpp))
        else:
            self.send_command(21, [str(fpp)])
            if self.verbose:
                print("incrementing page by one (fpp=%d)" % (fpp))
            
    def change_page_flip_speed(self, fpp=0, rev=False):
        """
        Tell display server to change the fast page flip speed. Fpp is
        the number of 20ms frames per page, so fpp=5 would mean 100ms
        per page, or a flip-rate of 10 pages per second.  If rev is
        True, flip in reverse (towards front of document).
        """
        if (rev):
            self.send_command(16, [str(fpp)], 1)
            if self.verbose:
                print("changing flip speed to %d (in reverse)" % fpp)
        else:
            self.send_command(16, [str(fpp)])
            if self.verbose:
                print("changing flip speed to %d" % fpp)

    def stop_page_flipping(self):
        """
        Tell display server to stop fast page flipping and resume
        normal updating. This is equivalent to change_page_flip_speed(0).
        """
        self.send_command(16, ['0'])

    def flip_to_stop_page(self, stopPage, fpp):
        """
        Tell display server to flip to stopPage at speed fpp, then stop.
        """
        self.send_command(19, [str(stopPage), str(fpp)])
        if self.verbose:
            print('flip_to_stop_page flipping to page %d at speed %d' % (stopPage, fpp))

    def send_stroke(self, stroke):
        """
        Paint a stroke. 'stroke' is binary data in Display Server's format.

        WARNING: this is not supported in the current Display Server
        (27 Jan 2009) and may not be implemented in the future.
        6 Jun 2009 mjg is adding support
        """
        #raise Exception('send_stroke not supported by Display Server')
        cmd = 1
        color = 1
        width = 2
        opt = (color << 8 ) + width
        data = pack('!HHH', 0,cmd,opt)
        self.send(data + stroke)
        
def get_commandline_parser(usage = "usage: %prog [options]"):
    """
    Return an optparse command line parser with options for PenTrackUpdate.
    """
    parser = optparse.OptionParser(usage=usage)
    add_options(parser)
    return parser

def add_options(parser):
    """
    Add optparse options to optparse command line parser.
    """
    parser.add_option("--ptu-port", dest="ptu_port",
                      type = "int", default = DEFAULT_PORT,
                      help="Port that pentrackupdate server listens to (default: %default)")
    parser.add_option("--ptu-addr", dest="ptu_addr",
                      default = DEFAULT_ADDR,
                      help="Address that pentrackupdate server listens to (default: %default)")
    choices = ['local', 'multicast']
    parser.add_option("--ptu-socket", dest="ptu_socket", type="choice",
                      default="local",  choices=choices,
                      help="Type of socket. (default: %%default, choices: %s)"
                      % choices)
    if not parser.has_option('-v'):
        parser.add_option("-v", "--verbose", dest="verbose",
                          action='store_true', default=False,
                          help="output more debug messages")

def parse_command_line(parser=None, usage="usage: %prog [options]"):
    """
    Usage::
      (options, args) = parse_command_line
    or::
      parser = get_commandline_parser()
      parser.add_option(...) # add more options
      (options, args) = parse_command_line(parser)

    options is a dictionary (not an object with values as members)
    """
    if not parser:
        parser = get_commandline_parser(usage)
    (opt, args) = parser.parse_args(sys.argv[1:])
    options = {}
    for obj in parser.option_list:
        k = obj.dest
        if (not k is None):
            options[k] = opt.__dict__.get(k)
    return options, args


if __name__ == "__main__":
    print "This is a library to be used by other programs."
