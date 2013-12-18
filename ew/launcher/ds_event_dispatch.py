#!/usr/bin/env python
import re, os, threading
from struct import unpack_from
import socket

MAX_EVENT_SIZE = 65535

from ew.util.editable_queue import EditableQueue
import ew.util.ew_logging
# "logging" must be imported *after* ew.util.ew_logging
from logging import DEBUG

logger = ew.util.ew_logging.getLogger('ew.launcher.ds_event_dispatch')

pat_pat = re.compile(r'[sS]|[^sS]+')

endian = '!'

end_pos = None

class AbortedEventLoopWait(Exception):
    def __init__(self):
        Exception.__init__(self, 'DS event loop thread context went away')

class DSEventLoop(threading.Thread):
    def __init__(self, dispatcher, base_name='ds_event_loop'):
        self.dispatcher = dispatcher;
        threading.Thread.__init__(self, name=base_name)
        self.setDaemon(True)
        self._should_stop = False

    def run(self):
        while not self._should_stop:
            fun, args = self.dispatcher._queue.get()
            if fun == "STOP":
                break
            else:
                try:
                    logger.debug('calling %s%s', fun.__name__, args)
                    fun(*args)
                    logger.debug('returned from calling %s', fun.__name__)
                except AbortedEventLoopWait:
                    logger.debug('%s exited from context close during wait', self)
                    break
                except:
                    logger.exception('exception calling %s%s', fun.__name__,args)

    def wait_on_event(self):
        self._should_stop = True #however we leave event
        logger.debug('%s is waiting on event so starting new DSEventLoop', self)
        DSEventLoop(self.dispatcher).start()
        
    def wait_interrupted(self):
        raise AbortedEventLoopWait()
            
class DSDatagramReceiver:
    def __init__(self, doc_runner):
        self.runner = doc_runner
        self._queue = EditableQueue()
        self._event_map = dict(
            on_stroke = (0, 'iiSii', self._stroke_data_unpacker),
            on_page = (1, 's',),
            on_submit = (2,),
            on_read_complete = (3, 'i'),
            on_render_complete = (4, 'i'),
            on_error = (5, 'ii'),
            on_stroke_file_ready = (6, 'SS'),
            on_landscape = (7,),
            on_portrait = (8,),
            on_sleep = (9,),
            on_doze = (10,),
            on_wake = (11,),
            on_shutdown = (12,),
            on_fuel_gauge_change = (13,),
            on_viewport_change = (14, 'ii'))
        self._event_by_number = dict([(v[0],(getattr(self.runner,k), v[1:])) for \
                                          k,v in self._event_map.iteritems()])



    def get_ds_event_id(self, data):
        return unpack_from(endian + 'I', data)[0]

    def unpack_ds_event_data(self, format, data, pos=4):
        """Decode a display server event.
        ...as defined in the Display Server API document in effect on 3/31/2011.
        From the document:

        "Events are sent with event codes and integer arguments as 4-byte
        integers and text as length-delimited ASCII strings. The general form
        of an event is:
            event_code [arg1] [arg2] [...]
        where event_code is an int indicating the event type."

        The document does not say whether the values are byte-aligned. Inspection
        has shown that they *are not* aligned, so this implementation works as
        such.

        The document does not say what the byte order is -- inspection has shown
        that they are "network" order (big-endian), so this implementation works
        as such.

        This function works similarly to the "struct.unpack" function in the
        Python library. It takes a pattern (a string) as its argument and
        returns a sequence of data values (integers and strings). The event ID
        integer is implicit and not reflected in the pattern. The pattern
        characters are:
        "i": signed integer
        "I": unsigned integer
        "s": string (preceded by its integer length)
        "S": string (preceded by its integer length, chars padded to
          integer boundary)
        """
        global end_pos
        values = []
        try:
            for m in pat_pat.finditer(format):
                fmt = m.group(0)
                if fmt in 'sS':
                    length, = unpack_from(endian + 'I', data, pos)
                    values.append(unpack_from(
                            endian + '%ds' % length, data, pos + 4)[0])
                    pos += 4 + length
                    if fmt == 'S':
                        align = pos % 4
                        if align:
                            pos += 4 - align
                else:
                    values.extend(unpack_from(endian + fmt, data, pos))
                    pos += 4 * len(fmt)
            end_pos = pos
        except Exception:
            logger.exception('bad data received')
        return values

    # Event decoding ======================


    _listener = None

    def listen_for_events(self, listener=None, local_socket_path='/tmp/PTU_sendsocket'):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        #sock.setblocking(True)
        if os.path.exists(local_socket_path):
            os.remove(local_socket_path)
        sock.bind(local_socket_path)
        while 1:
            logger.debug('Waiting for datagram...')
            data = sock.recv(MAX_EVENT_SIZE)
            if False or logger.isEnabledFor(DEBUG):
                logger.debug('Event datagram received -- %s bytes:\n%s',
                        len(data),
                        ' '.join(
                          ''.join("%02x" % ord(c) for c in data[i:i + 4])
                            for i in xrange(0, len(data), 4)))
            function, args = self._get_handler_information(data)
            if not function: 
                logger.warn('Unrecognized DS message received.. ignored')
                continue
            fname = function.__name__
            entry = function,args
            priority = self._queue.Priority_Normal
            if fname == 'on_page':
                #switching pages so remove queue on_stroke commands
                def is_on_stroke(function, args):
                    return function.__name__ == 'on_stroke'
                #self._queue.remove_all(is_on_stroke)
                self._queue.put(entry, self._queue.Priority_High)
            elif fname == 'on_stroke':
                priority = self._queue.Priority_Immediate if \
                           self.runner.infobar().owns_stroke(*args) else \
                           self._queue.Priority_Normal
                self._queue.put(entry, priority)
            elif fname in ('on_read_complete', 'on_error', 'on_render_complete'):
                #logger.debug('wait ending function %s called immediately', fname)
                function(*args)
            else: #probably more special cases here for power events..
                self._queue.put(entry)


    def start_service(self):
        self._listener_thread = threading.Thread(
            target = self.listen_for_events, name='ds_event_queue')
        self._listener_thread.setDaemon(True)
        self._listener_thread.start()
        DSEventLoop(self).start()

    def stop_service(self):
        self._queue.put(("STOP", ()), self._queue.Priority_Immediate)

    def _get_handler_information(self, data):
        event_id = self.get_ds_event_id(data)
        function, args = None, None
        unpacking_info = self._event_by_number.get(event_id)
        if unpacking_info:
            args = ()
            function, rest = unpacking_info
            logger.debug("handling DS event %s with format.. %s", function.__name__, rest)
            if rest:
                format = rest[0]
                unpacker = self.unpack_ds_event_data
                if len(rest) > 1:
                    unpacker = rest[1]
                args = unpacker(format, data)
        else:
            logger.error('Received DS packet with unknown event id %d',
                         event_id)

        fname = function.__name__ if function else 'None'
        logger.debug('DS incoming gives call %s%s', fname, args)
        return function, args

    def _stroke_data_unpacker(self,format, data):
        unpacked = self.unpack_ds_event_data(format, data)
        index, flags, window_id, milliseconds, sample_count = unpacked
        sample_coordinates = unpack_from(endian + '%dH' % (sample_count * 2),
                                         data, end_pos)
        samples = [sample_coordinates[i:i + 2]
                   for i in xrange(0, len(sample_coordinates), 2)]
        logger.debug('unpacked on_stroke points %s', samples)
        return (index, flags, window_id, milliseconds, samples)


