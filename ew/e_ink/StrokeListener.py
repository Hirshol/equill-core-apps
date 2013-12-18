#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.


"""
Get stroke information from pentrackupdate server on EDO.

Protocol '2009a' is::

  In src/socket_comm.c method encode_stroke_data() has been changed to
  send stroke_obj->statusFlag (short) in place of the rnd (random)
  field.

  in src/pen_tracking_1.5.c I have defined:

  // SC: for pen, eraser, and stylus flag
  #define PEN     0x01
  #define ERASER  0x02
  #define STYLUS  0x04

  And statusFlag is constructed in that file as:

  statusFlag = statusFlag | (samp.pen ? PEN : 0) | (samp.eraser ? ERASER :
  0) | (samp.stylus ? STYLUS :0);

  The values for status are:
     1 - normal pen
     2 - eraser
     5 - pen with button pressed
  Other values (e.g. 4, 6) should not occur.

It is expected that a future version will provide time information
about strokes. See README in svn://yesbox/edo_apps/pyedo/trunk/ for
more information.

python StorkListener.py  - test
python StorkListener.py  multicast - test multicast
python StorkListener.py  select - test select

-
 - $Id: StrokeListener.py 4400 2009-10-15 00:29:59Z rhodes $
 - $HeadURL: svn://yesbox/edo_apps/pentrackupdate/trunk/bin/StrokeListener.py $
"""

DEFAULT_PORT = 10022
DEFAULT_ADDR = '234.0.0.1'
PROTOCOL_VER = '2009d'     # adds partial stroke events
BUFF_SIZE = 65536

ON_STROKE_EVENT_TYPE = 0
ON_PAGE_EVENT_TYPE = 1
ON_SUBMIT_EVENT_TYPE = 2
ON_READ_COMPLETE_EVENT_TYPE = 3
ON_RENDER_COMPLETE_EVENT_TYPE = 4
ON_ERROR_EVENT_TYPE = 5
ON_STROKE_FILE_READY_EVENT_TYPE = 6
ON_LANDSCAPE_EVENT_TYPE = 7
ON_PORTRAIT_EVENT_TYPE = 8
ON_SLEEP_EVENT_TYPE = 9
ON_DOZE_EVENT_TYPE = 10
ON_WAKE_EVENT_TYPE = 11
ON_SHUTDOWN_EVENT_TYPE = 12
ON_FUEL_GAUGE_CHANGE_EVENT_TYPE = 13

# END_STROKE_EVENT_TYPE = 0
# PAGE_STOP_EVENT_TYPE = 1
# READ_COMPLETE_EVENT_TYPE = 2
# IMAGE_RENDER_COMPLETE_EVENT_TYPE = 3
# PARTIAL_STROKE_EVENT_TYPE = 4
# STROKE_FILE_READY_EVENT_TYPE = 5

import socket
import sys
import struct
import time
import os
import traceback


from ew.util import ew_logging
import logging
logger = ew_logging.getLogger('ew.e_ink.StrokeListener')

endian = '!'
uint = endian + 'I'
uint2 = endian + 'II'

class StrokeListener:
    """
    Get stroke information from pentrackupdate server on EDO.

    This object has a fileno() method, so it can be used
    with select.select and select.poll.
    """
    def __init__(self, **options):
        """
        Open socket.

        options::
            verbose=True
            ptu_port=10022
            ptu_addr='234.0.0.1'
            blocking=0
            eventListener=EVENTLISTENER
                 The onStrokeCapture method of this object is called
                 for stroke with (index, points)

                 The onPageStop method of this object is called for
                 page-stop events with (page_id)

                 The onReadComplete method of this object is called for
                 read completion events with (requestId)

                 The onRenderComplete method of this object is called for
                 render completion events with (requestId)

            discard_old_strokes=True
                 start() discards any old strokes. Default is False.
            start=False
                 Do not call start() during __init__(). Default is to
                 to call start().
            discard_first_point=True
                 Discard the first point in each stroke.  Default is False.
            discard_negative_points=True
                 Discard any points where X or Y is negative. Default is False.
        """
        self.drop_params = None
        self.verbose = False

        self.port = options.get('ptu_port', DEFAULT_PORT)
        self.addr = options.get('ptu_addr', DEFAULT_ADDR)
        self.eventListener = options.get('eventListener')
        self.discard_old_strokes = options.get('discard_old_strokes', False)
        self.discard_first_point = options.get('discard_first_point', False)
        self.discard_negative_points = options.get('discard_negative_points',
                                                   False)
        self.ptu_socket_type = options.get('ptu_socket', 'local')
        if 'blocking' in options and 'timeout' in options:
            raise Exception('Please use only one of "blocking" and "timeout"')
        blocking = options.get('blocking')
        self.blocking = None if blocking is None else bool(blocking)
        self.timeout = options.get('timeout')
        self.socket = None
        self.event_cmd_fmt = uint   # unsigned int
        self.event_cmd_len = struct.calcsize(self.event_cmd_fmt)
        if options.get('start', True):
            self.start()

    def start(self):
        if self.socket:
            logger.error(
                'StrokeListener start() called while socket existed. Call stop() first.')
            return
        if self.ptu_socket_type == 'multicast':
            try:
                self.mode = socket.AF_INET
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                # Set some options to make it multicast-friendly
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except AttributeError:
                    #print 'no suport for SO_REUSEPORT'
                    # Some systems don't support SO_REUSEPORT
                    # (mac requires it, yesbox doesn't have it)
                    pass
                s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
                s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

                #This is the right format for socket.INADDR_ANY
                intf = socket.inet_aton('0.0.0.0')

                #This was in sample code, but caused listener not to work on it's own
                #s.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, intf)

                s.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.addr) + intf)

                self.drop_params = (socket.SOL_IP, socket.IP_DROP_MEMBERSHIP,
                             socket.inet_aton(self.addr) + socket.inet_aton('0.0.0.0'))
                s.bind(('', self.port))
                self.socket = s
            except socket.error, ex:
                if self.verbose:
                    print 'trying local socket because: ' + str(ex)
                logger.debug('Trying local socket because: %s', ex)
                self.ptu_socket_type = 'local'
                self.socket = None
        if self.ptu_socket_type == 'local':
            self.mode = socket.AF_UNIX
            # socket_type = socket.SOCK_STREAM
            socket_type = socket.SOCK_DGRAM
            s = socket.socket(socket.AF_UNIX, socket_type)
            self.socket = s
            #fileno is actually fixed at socket creation not binding with file
            logger.debug('socket.fileno: %s', self.socket.fileno())
            socketname = '/tmp/PTU_sendsocket'
            if os.path.exists(socketname):
                os.remove(socketname)
            csock = self.socket.bind(socketname) # For SOCK_DGRAM this is a default address
            # listen and accept are for socket.SOCK_STREAM
            # self.socket.listen(5) # only 1? since we aren't serving many?
            # (clientsocket,addr) = self.socket.accept() #blocking (addr is '' for localsockets)
        if not self.socket:
            raise Exception('Bad socket type or could not open socket.')

        if self.discard_old_strokes:
            self.old_strokes()

        if self.blocking is not None:
            s.setblocking(self.blocking)
        elif self.timeout:
            s.settimeout(self.timeout)

        # For future use of SOCK_STREAM sockets, accumulate parts
        # of messages about strokes. With SOCK_DGRAM sockets,
        # each time the socket is read, a complete message is
        # returned, so the code for accumulating parts is harmless
        # but unnecessary.

        # One issue with SOCK_STREAM is that if someone jumps into the
        # conversation (especially on multicast), we have to figure
        # out where we are, whereas with DGRAM you know you are
        # getting a stroke from the beginning.

        self.data = ''
        self.data_needed = self.event_cmd_len
        # self.data_needed = self.stroke_header_len


    def old_strokes(self):
        """clean-up input queue"""
        self.socket.settimeout(0.1)
        while True:
            logger.verbose('in strokecapture.old_strokes()')
            try:
                data = self.socket.recv(BUFF_SIZE)
            except socket.timeout:
                break

    def __del__(self):
        self.clean_up()

    def clean_up(self):
        self.eventListener = None
        self.stop()

    def stop(self):
        s = self.socket
        if s:
            # if this is called by __del__, socket may no longer
            # be imported, so used previously saved parameters
            if self.drop_params:
                s.setsockopt(*self.drop_params)
            s.close()
            self.socket = None
        if self.verbose:
            print "StrokeListener.stop(): socket closed()"
        logger.debug("StrokeListener.stop(): socket closed()")

    def read_more_data(self, needed):
        """
        Read from socket if we have less than amount of data needed
        """
        # logger.debug('StrokeListener.read_more_data(%d), needed)
        tmp_data = None
        n = len(self.data)
        if needed > n:
            # if self.verbose: print "Ready to read from socket..."
            try:
                # Maximum DGRAM size is 64K
                # (64K - 8)/4 = 16,382 points in a stoke
                tmp_data, _ = self.socket.recvfrom(BUFF_SIZE)
                logger.debug(
                        'Data received by read_more_data (%s bytes): %s',
                        len(tmp_data),
                        ' '.join(
                          ''.join("%02x" % ord(c) for c in tmp_data[i:i + 4])
                            for i in xrange(0, len(tmp_data), 4)))
            # except socket.timeout, ex  # Handle timeout?
            except socket.error, ex:
                # 'Resource temporarily unavailable
                if (not self.blocking) and ex.args[0] == 11:
                    if n > 0:
                        logger.warn('StrokeListener.read_more_data(): '
                                     'needed %s, only read %s', needed, n)
                    return None
                raise socket.error(ex)
        if not tmp_data:
            return n
        len_temp_data = len(tmp_data)
        if self.verbose: print "Read %d bytes from socket" % len_temp_data
        logger.verbose("Read %d bytes from socket", len_temp_data)
        self.data += tmp_data
        return len_temp_data

    def read_event_type(self):
        if (len(self.data) < self.event_cmd_len):
            # logger.debug('StrokeListener.read_event_type(None)')
            return None
        else:
            etype = struct.unpack(self.event_cmd_fmt, self.data[:self.event_cmd_len])[0]
            logger.debug('StrokeListener.read_event_type(etype: %d)', etype)
            return etype

    def event_type(self, event):
        """
        Return type of event returned from read_event_data
        """
        if (event):
            logger.debug('StrokeListener.event_type(event[0]=%d)', event[0])
            return event[0]
        logger.verbose('StrokeListener.event_type(None)')
        return None

    def get_stroke(self):
        """
        Return the next stroke in the event queue, or None if no more
        strokes have been received. Any other type of events (page
        stop or read complete) before the next stroke will be dropped
        on the floor, though the appropriate callback for those events
        will be called if defined.
        """
        # logger.debug('StrokeListener.get_stroke()')
        data = self.read_event_data()
        while (data != None):
            eventType, event = data
            if (eventType == ON_STROKE_EVENT_TYPE):
                return event
            else:
                data = self.read_event_data()
        return None

    def read_event_data(self):
        """
        Read data from socket and parse into appropriate
        event. Returns eventType, event or None.
        """
        # logger.debug('StrokeListener.read_event_data()')
        self.read_more_data(self.event_cmd_len)
        event_type = self.read_event_type()
        if (event_type == None):
            # logger.debug('StrokeListener.read_event_data(): event_type is None')
            return None
        elif (event_type == ON_STROKE_EVENT_TYPE):   # stroke
            logger.debug(
                'StrokeListener.read_event_data(): calling read_stroke()')
            return event_type, self.read_stroke(False)
        elif (event_type == ON_PAGE_EVENT_TYPE): # page change
            logger.debug(
                'StrokeListener.read_event_data(): calling read_page_stop()')
            return event_type, self.read_page_stop()
        elif (event_type == ON_SUBMIT_EVENT_TYPE): # submit button pressed
            logger.debug(
                'StrokeListener.read_event_data(): calling read_submit()')
            return event_type, self.read_submit()
        elif (event_type == ON_READ_COMPLETE_EVENT_TYPE): # image read completed
            logger.debug(
                'StrokeListener.read_event_data(): calling read_read_complete()')
            return event_type, self.read_read_complete()
        elif (event_type == ON_RENDER_COMPLETE_EVENT_TYPE): # image render completed
            logger.debug(
                'StrokeListener.read_event_data(): calling read_render_complete()')
            return event_type, self.read_render_complete()
        elif (event_type == ON_ERROR_EVENT_TYPE): # error reported
            logger.debug(
                'StrokeListener.read_event_data(): calling read_error()')
            return event_type, self.read_error()
        elif (event_type == ON_STROKE_FILE_READY_EVENT_TYPE): # stroke file ready for logging
            logger.debug(
                'StrokeListener.read_event_data(): calling read_stroke_file_ready()')
            return event_type, self.read_stroke_file_ready()
        else:
            logger.error('read_event_data(): type %d not known', event_type)
            n = 1000
            logger.info(' Next %d bytes:', n)
            logger.info('   0:  0x%08x  %d', event_type, event_type)
            for a in xrange(4, n, 4):
                x, = self.read_fixed_length_data(uint, 4)
                logger.info('%4d:  0x%08x  %d', a, x, x)
        return None

    def read_string_data(self):
        """
        Parse and return for a single string, where the next short in the data is the length of the string.
        """
        logger.debug('StrokeListener.read_string_data()')
        string_len_fmt = uint
        string_len_fmt_len = struct.calcsize(string_len_fmt)
        string_len, = self.read_fixed_length_data(string_len_fmt, string_len_fmt_len)
        string_fmt = '%c%ds' % (endian, string_len)
        string_fmt_len = struct.calcsize(string_fmt)
        data = self.read_fixed_length_data(string_fmt, string_fmt_len)
        return data

    def read_fixed_length_data(self, fmt, len):
        """
        Parse and return data for one fixed-length event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_fixed_length_data(%s, %d)', fmt, len)
        n = self.read_more_data(len)
        if (n < len):
            msg = "Not enough data (%s), want at %s" % (n, len)
            if self.verbose:
                print msg
            # return None
            raise Exception(msg) # only one chance to read DGRAM socket
        d = self.data[:len]
        self.data = self.data[len:]
        return struct.unpack(fmt, d)

    def call_handler(self, method_name, *args):
        """Call an event handler."""
        if self.eventListener:
            logger.debug('about to call %s%s', method_name, args)
            method = None
            try:
                method = getattr(self.eventListener, method_name)
            except AttributeError:  # no callback set, ignore
                pass
            if method:
                return method(*args)

    def read_page_stop(self):
        """
        Return one page event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_page_stop()')
        data = self.read_fixed_length_data(self.event_cmd_fmt, self.event_cmd_len)
        if data == None:
            return None
        scmd, = data
        logger.debug('StrokeListener.read_page_stop(): scmd=%s, data=%s',
            scmd, data)
        data = self.read_string_data()
        if data == None:
            return None
        page_id, = data
        logger.debug('StrokeListener.read_page_stop(): page_id=%s, data=%s',
            page_id, data)

        if self.verbose:
            print 'cmd: %d\npage_id: %s\n' % (scmd, page_id)
        logger.debug('cmd: %d, page_id: %s', scmd, page_id)
        self.call_handler('onPageStop', page_id)
        return scmd, page_id

    def read_read_complete(self):
        """
        Return one page event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_read_complete()')
        read_complete_fmt = uint2
        read_complete_len = struct.calcsize(read_complete_fmt)
        data = self.read_fixed_length_data(read_complete_fmt, read_complete_len)
        if data == None:
            return None
        scmd, readId = data
        if self.verbose:
            print 'cmd: %d\nrequest_id: %d\n' % (scmd, readId)
        logger.debug('cmd: %d, request_id: %d', scmd, readId)
        self.call_handler('onReadComplete', readId)
        return scmd, readId

    def read_render_complete(self):
        """
        Return one page event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_render_complete()')
        render_complete_fmt = uint2
        render_complete_len = struct.calcsize(render_complete_fmt)
        data = self.read_fixed_length_data(render_complete_fmt, render_complete_len)
        if data == None:
            return None
        scmd, request_id = data
        if self.verbose:
            print 'cmd: %d\nrequest_id: %d\n' % (scmd, request_id)
        logger.debug('cmd: %d, request_id: %d', scmd, request_id)
        self.call_handler('onRenderComplete', request_id)
        return scmd, request_id

    def read_submit(self):
        """
        Return one page event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_submit()')
        submit_fmt = uint
        submit_len = struct.calcsize(submit_fmt)
        data = self.read_fixed_length_data(submit_fmt, submit_len)
        if data == None:
            return None
        scmd = data
        if self.verbose:
            print 'cmd: %s\n' % (scmd)
        logger.debug('cmd: %s', scmd)
        self.call_handler('onSubmit')
        return scmd

    def read_error(self):
        """
        Return one page event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_error()')
        error_fmt = endian + 'III'
        error_len = struct.calcsize(error_fmt)
        data = self.read_fixed_length_data(error_fmt, error_len)
        if data == None:
            return None
        scmd, request_id, error_code = data
        if self.verbose:
            print 'cmd: %d\nrequest_id: %d\nerror_code: %d' % (scmd, request_id, error_code)
        logger.debug('cmd: %d, request_id: %d, error_code: %d', scmd, request_id, error_code)
        self.call_handler('onError', request_id, error_code)
        return scmd, request_id, error_code

    def read_stroke_file_ready(self):
        """
        Return one page event or None. Read from socket if data for
        event isn't already available.
        """
        logger.debug('StrokeListener.read_stroke_file_ready()')
        data = self.read_fixed_length_data(self.event_cmd_fmt, self.event_cmd_len)
        if data == None:
            return None
        scmd, = data
        logger.debug(
            'StrokeListener.read_stroke_file_ready(): scmd=%s, data=%s',
            scmd, data)
        data = self.read_string_data()
        if data == None:
            return None
        page_id, = data
        logger.debug(
            'StrokeListener.read_stroke_file_ready(): page_id=%s, data=%s',
            page_id, data)
        data = self.read_string_data()
        if data == None:
            return None
        stroke_path, = data
        logger.debug(
            'StrokeListener.read_stroke_file_ready(): stroke_path=%s, data=%s',
            stroke_path, data)
        if self.verbose:
            logger.debug('cmd: %d, page_id: %s, stroke_path: %s',
                scmd, page_id, stroke_path)
        self.call_handler("onStrokeFileReady", page_id, stroke_path)
        return scmd, page_id, stroke_path

    def read_stroke(self, isPartial):
        """
        Return one stroke or None. Read from socket if
        data for a stroke isn't already available.

        The final value in a returned tuple (save_data) is the
        binary data for the stroke. This can saved and sent back
        to the display server to draw the stroke again.
        """
        logger.debug('StrokeListener.read_stroke(%s)', isPartial)
        stroke_header_fmt = endian + 'IHHH'
        stroke_header_len = struct.calcsize(stroke_header_fmt)
        sample_point_fmt = endian + 'HH'
        sample_point_len = struct.calcsize(sample_point_fmt)
        self.read_more_data(self.data_needed)
        n = len(self.data)
        if (n < stroke_header_len) or (n < self.data_needed):
            if self.verbose:
                print "Not enough data (%d), want min(%d,%d)" % (
                    n, stroke_header_len, self.data_needed)
            logger.debug("Not enough data (%d), want min(%d,%d)",
                    n, stroke_header_len, self.data_needed)
            # return None
            raise Exception(msg) # only one chance to read DGRAM socket
        scmdHaveStroke, frame, status, npts = struct.unpack(
            stroke_header_fmt, self.data[:stroke_header_len])
        if self.verbose:
            print 'shs: %d\nframe: %d\nstatus: %d\nnpts: %d' % (
                scmdHaveStroke, frame, status, npts)
        logger.debug('shs: %d, frame: %d, status: %d, npts: %d',
                scmdHaveStroke, frame, status, npts)
        size = stroke_header_len + npts * sample_point_len
        if n < size:
            self.data_needed = size
            # return None
            # only one chance to read DGRAM socket
            raise Exception("Not enough data for all points in stroke")
        points = []
        p = stroke_header_len
        for i in xrange(npts):
            points.append(struct.unpack(sample_point_fmt,
                                        self.data[p:p + sample_point_len]))
            p += sample_point_len
        if self.discard_first_point:
            points = points[1:]
        if self.discard_negative_points:
            points = [i for i in points if (i[0] >= 0) and (i[1] >= 0)]
        if self.verbose:
            print "  " + ' '.join(['(%d,%d)' % i for i in points])
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("  " + ' '.join(['(%d,%d)' % i for i in points]))
        save_data = self.data[:p]
        self.data = self.data[p:]
        self.data_needed = stroke_header_len
        # frame is an index (identifier) for the stroke
        if isPartial:      # if partial stroke set the appropriate status flag bit
            status |= 0x8
        try:
            self.call_handler('onStrokeCapture', frame, status, points,
                    save_data)
        except TypeError, e:
            print 'StrokeListener.read_stroke got exception', e
            logger.exception('StrokeListener.read_stroke got exception')
            traceback.print_exc()
            self.call_handler('onStrokeCapture', frame, points)
        return  frame, scmdHaveStroke, status, npts, points, save_data

    def loop(self, callback, **opts):
        """
        Call 'callback(frame, scmdHaveStroke, rnd, ntps, points)' for
        each stroke from inside a loop. Can sleep in loop if not
        using socket that blocks (or at least blocks until some timeout).

        This method can be run in a thread.

        opts::
            sleep=1.0    Sleep in loop.
        """
        while 1:
            rval = self.get_stroke()
            if rval and callback:
                callback(*rval)
            sleep = opts.get('sleep')
            if sleep:
                time.sleep(sleep)

    def selectloop(self):
        '''just for testing'''
        while 1:
            ready_r, ready_w, ready_x = select.select([self.fileno()], [], [], 5.0)
            if len(ready_r) > 0:
                print str(ready_r[0])
                self.get_stroke()
            else:
                print 'time out.'

    def fileno(self):
        """
        fileno() allows this object to be used with select.select and
        select.poll.
        """
        if self.socket:
            return self.socket.fileno()
        raise Exception("Error in StrokeListener.fileno(), socket does not exist. (clean-up() called?)")

    def test(self, pollTimeout):
        """
        Similar to get_stroke.
        """
        if self.socket:
            self.socket.settimeout(pollTimeout)
            return self.get_stroke()

class StrokeCapture(StrokeListener):
    """
    Poll for strokes on EDO Pad and call listener. Provides an alternative
    interface to StrokeListener.
    """
    def __init__(self, eventListener=None, **options):
        StrokeListener.__init__(eventListener=eventListener, start=False,
                                discard_old_strokes=True,
                                discard_negative_points=True
                                ** options)

class TestPrint(object):
    def onStrokeCapture(self, frame, points):
        '''test method.'''
        for pt in points:
            print str(pt)

if __name__ == "__main__":
    import select
    if 'select' in sys.argv[1:]:
        myListener = TestPrint()
        sl = StrokeListener(verbose=True, eventListener=myListener, start=True)
        sl.selectloop()
        exit()
    if 'multicast' in sys.argv[1:]:
        sl = StrokeListener(verbose=True, blocking=1, ptu_socket='multicast')
    else:
        sl = StrokeListener(verbose=True, blocking=1)
    sl.loop(None)
