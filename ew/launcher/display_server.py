#!/usr/bin/env python
# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.

"""Python class-oriented interface to display server operations."""


# Enable experimental technique for method specification if true.
API_GEN_EXPERIMENT = False
if API_GEN_EXPERIMENT:
    from ds_api_util import DsApiUtil
    make_method = DsApiUtil().make_method

#import atexit
import random
from struct import pack, calcsize
import threading, pdb, types

from ew import e_ink
import ew.util.ew_logging
import logging  # Must be imported *after* ew_logging.



logger = ew.util.ew_logging.getLogger('ew.launcher.display_server')

def isEnabledFor(level=logging.DEBUG, isEnabledFor=logger.isEnabledFor):
    """Performs a fast check for logger enabled for DEBUG messages.
    Runs fast since the binding of logger to checking method and
    resolution of logging.DEBUG is done at function *definition* time.
    """
    return isEnabledFor(level)

def perhaps_wait(method):
    def wait_wrapped(self, *args, **kwargs):
        logger.debug('perhaps wait on args=%s, kwargs=%s',
                     args, kwargs)
        wait = kwargs.get('wait', False)
        if wait:
            #logger.debug('waiting on %s%s%s', method.__name__,
            #             args,kwargs)
            wait_event = self._wait.prewait(method.__name__)
            kwargs['request_id'] = wait_event.request_id
        retval = method(self, *args, **kwargs)
        if wait:
            self._wait.wait_for(wait_event)
        return retval

    return wait_wrapped

def no_unicode(method):
    def convert(x):
        return str(x) if type(x) == types.UnicodeType else x
    def wrapped(self, *args, **kwargs):
        args = map(convert, args)
        method(self, *args, **kwargs)
    return wrapped


lock = threading.Lock()

interface_testing = False


# The "wait" facility.
#
class DSWait:
    def __init__(self):
        self._id = self.id_generator()
        self._waiting_events = {}
        self._lock = threading.Lock()

    def id_generator(self):
        next = random.randint(1, 0xffff)
        while 1:
             yield next
             next = (next + 1) & 0xffff
             if not next: next = 1

    def prewait(self, func_name):
        """Performs start of function tasks for wait option."""
        def make_event():
            event = threading.Event()
            event.func_name = func_name
            event.error = None
            event.request_id = self._id.next()
            return event
        with self._lock:
            event = make_event()
            self._waiting_events[event.request_id] = event
        logger.debug('Calling: %s with generated request ID: %s',
                func_name, event.request_id)
        return event

    def wait_for(self, event):
        """Performs end of function tasks for wait option."""
        logger.debug('Waiting for: %s, request ID: %s', event.func_name, event.request_id)
        event.wait()
        with lock:
            self._waiting_events.pop(event.request_id)
        logger.debug('Returned after wait: %s, request ID: %r, error: %r',
                event.func_name, event.request_id, event.error)
        return event.error

    def notify_event(self, request_id, error=None):
        """
        Notifies a function call waiting on the specified request ID that
        its completion event has arrived.
        """
        with lock:
            event = self._waiting_events[request_id]
            if event:
                event.error = error
                event.set()
            else:
                logger.info("Did not find a waiting event on request_id %d", request_id)

    def terminate_all_waiting_events(self):
        logger.debug('Terminating all waiting events')
        for event in self._waiting_events.values():
            event.error = 999
            event.set()
        self._waiting_events = {}


class DSDatagramSender(object):

    _instance_lock = threading.RLock()
    _instance = None

    _pen_track_update_options = {}

    @classmethod
    def instance(cls):
        """Returns the instance of this singleton class."""
        with cls._instance_lock:
            if not cls._instance:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        """Initializes the instance.
        Raises socket.error if display server not reachable, typically
        error 111, 'Connection refused'.
        Raises RuntimeError if attempt to create an additional instance of
        this singleton class.

        """
        if self._instance:
            raise RuntimeError(
                "Additional instances of singleton class %r should not"
                " be created -- use '%s.instance()' method" %
                ((self.__class__.__name__,) * 2))
        self._ptu_send = None
        self._send_lock = threading.Lock()
        self._wait = DSWait()
        self.__class__._instance = self

    def clear(self):
        self._wait.terminate_all_waiting_events()

    def handle_request_completion(self, request_id, error_code=None):
        self._wait.notify_event(request_id, error_code)

    def _send(self, packet):
        #logger.debug('_send called: %r', packet)
        if not interface_testing:
            with self._send_lock:
                if not self._ptu_send:
                    self._ptu_send = e_ink.PenTrackUpdate(
                            **self._pen_track_update_options).send
                self._ptu_send(packet)
        #logger.debug('_send returned')




        # New binary function call message protocol (in pseudo-C):
        #
        # int magic_word      // 0x131C014E
        # int total_length    // Total length in bytes of *all* fields
        # int op_code         // Operation code
        # int options         // Options flag bits
        # int request_id      // Request ID (0 is null request_id)
        #
        # int integer_parameter_count    // Count of integer parameters (IPC)
        # int char_parameter_count       // Count of char parameters (CPC)
        #
        # int integer_parameter_1        // First integer parameter value
        # ...
        # int integer_parameter_IPC      // Last  integer parameter value
        #
        # int char_parameter_length_1    // First char parameter length in bytes
        # ...
        # int char_parameter_length_CPC  // Last char parameter length in bytes
        #
        # char[] char_data_1             // First char parameter data
        # char[] char_data_2             // First char parameter data (not aligned)
        # ...
        # char[] char_data_CPC           // Last  char parameter data (not aligned)


    def load_document(self,
            start_page_num,
            document_path,
            flash=True,
            force_reload=False,
            request_id=0,
            wait=False,
            mask_ink=False):
        """Load document. (opcode: 100)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-loaddocument
        """
        #
        logger.debug('sending load_document page:%d path:%s mask_ink:%s', start_page_num, 
                     document_path, mask_ink)
        fmt = "@9L%ds" % len(document_path)
        if wait:
            wait_event = self._wait.prewait('load_document')
            request_id = wait_event.request_id
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                100, ((0x02 if flash else 0) |
                        (0x01 if force_reload else 0) | (0x40 if mask_ink else 0)),
                request_id,
                # Int and char arg counts
                1, 1,
                # Int args
                start_page_num,
                # String arg lengths
                len(document_path),
                # String args
                str(document_path)))
        if wait:
            self._wait.wait_for(wait_event)

    load_document.opcode = 100

    #@perhaps_wait
    def insert_page(self,
            page_id,
            insert_before,
            request_id=0,
            wait=False):
        """Insert page. (opcode: 101)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-insertpage%5C
        """
        fmt = "@9L%ds%ds" % (
                tuple(len(arg) for arg in (
                    page_id, insert_before)))
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                101, 0,
                request_id,
                # Int and char arg counts
                0, 2,
                # String arg lengths
                len(page_id), len(insert_before),
                # String args
                str(page_id), str(insert_before)))

    insert_page.opcode = 101

    def mask_page_strokes(self, mask_strokes, page_id):
        fmt = "@9L%ds" % len(page_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                        #opcode and options
                        170, 0, 
                        #request id 
                        0,
                        #num int and string args
                        1, 1,
                        (1 if mask_strokes else 0),
                        len(page_id),
                        str(page_id)))
                        

    mask_page_strokes.opcode = 170

    #@perhaps_wait
    def delete_page(self,
            page_id,
            request_id=0,
            wait=False):
        """Delete page. (opcode: 102)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-deletepage%5C
        """
        fmt = "@8L%ds" % len(page_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                102, 0,
                request_id,
                # Int and char arg counts
                0, 1,
                # String arg lengths
                len(page_id),
                # String args
                str(page_id)))

    delete_page.opcode = 102

    #@perhaps_wait
    def update_region_of_page(self,
            x_dest,
            y_dest,
            x_src,
            y_src,
            width_src,
            height_src,
            page_id,
            src_path,
            clear_ink=False,
            delete_image=False,
            flash=False,
            redraw=False,
            request_id=0,
            wait=False):
        """Update region of page. (opcode: 103)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-updateregionofpage
        """
        logger.debug('DS.update_region_of_page(%s,%s,%s,%s)',
                     (x_dest, y_dest), (x_src, y_src, width_src, height_src), 
                     page_id, src_path)
        fmt = "@15L%ds%ds" % (
                tuple(len(arg) for arg in (
                    page_id, src_path)))
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                103, ((0x10 if clear_ink else 0) |
                        (0x08 if delete_image else 0) |
                        (0x02 if flash else 0) |
                        (0x04 if redraw else 0)),
                request_id,
                # Int and char arg counts
                6, 2,
                # Int args
                x_dest, y_dest, x_src, y_src, width_src, height_src,
                # String arg lengths
                len(page_id), len(src_path),
                # String args
                str(page_id), str(src_path)))

    update_region_of_page.opcode = 103

    #@perhaps_wait
    def update_region_of_infobar(self,
            x_dest,
            y_dest,
            x_src,
            y_src,
            width_src,
            height_src,
            clear_ink=False,
            flash=False,
            redraw=False,
            request_id=0,
            wait=False):
        """Update region of infobar. (opcode: 104)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-updateregionofinfobar%5C
        """
        fmt = "@13L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                104, ((0x10 if clear_ink else 0) |
                        (0x02 if flash else 0) |
                        (0x04 if redraw else 0)),
                request_id,
                # Int and char arg counts
                6, 0,
                # Int args
                x_dest, y_dest, x_src, y_src, width_src, height_src))

    update_region_of_infobar.opcode = 104

    #@perhaps_wait
    def jump_to_page(self,
            page_id,
            request_id=0,
            wait=False):
        """Jump to page. (opcode: 105)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-jumptopage
        """
        logger.debug('attempting to jump to page %s', page_id)
        fmt = "@8L%ds" % len(page_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                105, 0,
                request_id,
                # Int and char arg counts
                0, 1,
                # String arg lengths
                len(page_id),
                # String args
                str(page_id)))

    jump_to_page.opcode = 105

    #@perhaps_wait
    def next_page(self, request_id=0, wait=False):
        """Next page. (opcode: 106)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-nextpage
        """
        fmt = "@7L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                106, 0,
                request_id,
                # Int and char arg counts
                0, 0))

    next_page.opcode = 106

    #@perhaps_wait
    def prev_page(self, request_id=0, wait=False):
        """Prev page. (opcode: 107)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-prevpage
        """
        fmt = "@7L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                107, 0,
                request_id,
                # Int and char arg counts
                0, 0))

    prev_page.opcode = 107

    #@perhaps_wait
    def create_overlay_window(self,
            x_dest,
            y_dest,
            x_src,
            y_src,
            width_src,
            height_src,
            page_id,
            display_window_id,
            src_path,
            clear_ink=False,
            delete_image=False,
            disable_page_turn=False,
            flash=False,
            redraw=False,
            request_id=0,
            wait=False):
        """Create overlay window. (opcode: 110)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-createoverlaywindow
        """
        fmt = "@16L%ds%ds%ds" % (
                tuple(len(arg) for arg in (
                    page_id, display_window_id, src_path)))
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                110, ((0x10 if clear_ink else 0) |
                        (0x08 if delete_image else 0) |
                        (0x20 if disable_page_turn else 0) |
                        (0x02 if flash else 0) |
                        (0x04 if redraw else 0)),
                request_id,
                # Int and char arg counts
                6, 3,
                # Int args
                x_dest, y_dest, x_src, y_src, width_src, height_src,
                # String arg lengths
                len(page_id), len(display_window_id), len(src_path),
                # String args
                str(page_id), str(display_window_id), str(src_path)))

    create_overlay_window.opcode = 110

    #@perhaps_wait
    def modify_overlay_window(self,
            x_dest,
            y_dest,
            x_src,
            y_src,
            width_src,
            height_src,
            display_window_id,
            src_path,
            clear_ink=False,
            delete_image=False,
            flash=False,
            redraw=False,
            request_id=0,
            wait=False):
        """Modify overlay window. (opcode: 111)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-modifyoverlaywindow
        """
        fmt = "@15L%ds%ds" % (
                tuple(len(arg) for arg in (
                    display_window_id, src_path)))
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                111, ((0x10 if clear_ink else 0) |
                        (0x08 if delete_image else 0) |
                        (0x02 if flash else 0) |
                        (0x04 if redraw else 0)),
                request_id,
                # Int and char arg counts
                6, 2,
                # Int args
                x_dest, y_dest, x_src, y_src, width_src, height_src,
                # String arg lengths
                len(display_window_id), len(src_path),
                # String args
                str(display_window_id), str(src_path)))

    modify_overlay_window.opcode = 111

    #@perhaps_wait
    def close_overlay_window(self,
            display_window_id,
            flash=False,
            redraw=False,
            request_id=0,
            wait=True):
        """Close overlay window. (opcode: 112)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-closeoverlaywindow
        """
        fmt = "@8L%ds" % len(display_window_id)
        if wait:
            wait_event = self._wait.prewait('close_overlay_window')
            request_id = wait_event.request_id
            logger.debug('close_overlay waits on %r %d', wait_event, request_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                112, ((0x02 if flash else 0) |
                        (0x04 if redraw else 0)),
                request_id,
                # Int and char arg counts
                0, 1,
                # String arg lengths
                len(display_window_id),
                # String args
                str(display_window_id)))
        if wait:
            self._wait.wait_for(wait_event)

    close_overlay_window.opcode = 112

    def mask_region(self,
                    top, left, width, height,
                    display_id,
                    request_id = 0,
                    wait = False):
        """mask drawing and storing ink in the window (page or overlay) with the given
        display_id"""
        fmt = "@12L%ds" % len(display_id)
        logger.debug('DS <= mask_region(%s,%s)', (top,left,width,height), display_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                175, 0,
                request_id,
                # Int and char arg counts
                4, 1,
                # Int args
                top, left, width, height,
                # String arg lengths
                len(display_id), 
                # String args
                str(display_id)))
        
    mask_region.opcode = 175

    def invert_video_in_regions(self,
                                display_id, *regions):
        """video will be inverted in the given regions each of which is (x,y,w,h).
        Inversion will happen on pen down in a region and continue to either leaving
        the region or pen up.  At that point it will revert"""
        fmt = '@%dL%ds' % (9 + len(regions), len(display_id))
        var_stuff = [len(regions)/4]
        var_stuff.extend(regions)
        var_stuff.append(len(display_id))
        var_stuff.append(display_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                190, 0,
                0,
                # Int and char arg counts
                len(regions) + 1, 1,
                # Int args
                *var_stuff))
        
    invert_video_in_regions.opcode = 190

    #@perhaps_wait
    def change_config(self,
            Variable,
            Value,
            request_id=0,
            wait=False):
        """Change config. (opcode: 120)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-changeconfig%5C
        """
        fmt = "@9L%ds%ds" % (
                tuple(len(arg) for arg in (
                    Variable, Value)))
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                120, 0,
                request_id,
                # Int and char arg counts
                0, 2,
                # String arg lengths
                len(Variable), len(Value),
                # String args
                str(Variable), str(Value)))

    change_config.opcode = 120

    #@perhaps_wait
    def erase_strokes_by_index(self,
            start_index,
            end_index,
            page_id,
            request_id=0,
            wait=False):
        """Erase strokes by index. (opcode: 130)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-erasestrokesbyindex%5C
        """
        fmt = "@10L%ds" % len(page_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                130, 0,
                request_id,
                # Int and char arg counts
                2, 1,
                # Int args
                start_index, end_index,
                # String arg lengths
                len(page_id),
                # String args
                str(page_id)))

    erase_strokes_by_index.opcode = 130

    #@perhaps_wait
    def erase_ink_in_region(self,
            x,
            y,
            width,
            height,
            page_id,
            request_id=0,
            wait=False):
        """Erase ink in region. (opcode: 131)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-eraseinkinregion%5C
        """
        fmt = "@12L%ds" % len(page_id)
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                131, 0,
                request_id,
                # Int and char arg counts
                4, 1,
                # Int args
                x, y, width, height,
                # String arg lengths
                len(page_id),
                # String args
                str(page_id)))

    erase_ink_in_region.opcode = 131

    #@perhaps_wait
    def doze(self, request_id=0, wait=False):
        """Doze. (opcode: 140)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-doze%5C
        """
        fmt = "@7L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                140, 0,
                request_id,
                # Int and char arg counts
                0, 0))

    doze.opcode = 140

    #@perhaps_wait
    def sleep(self, request_id=0, wait=False):
        """Sleep. (opcode: 141)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-sleep%5C
        """
        fmt = "@7L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                141, 0,
                request_id,
                # Int and char arg counts
                0, 0))

    sleep.opcode = 141

    #@perhaps_wait
    def set_doze_timer(self,
            timeout,
            request_id=0,
            wait=False):
        """Set doze timer. (opcode: 142)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-setdozetimer%5C
        """
        fmt = "@8L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                142, 0,
                request_id,
                # Int and char arg counts
                1, 0,
                # Int args
                timeout))

    set_doze_timer.opcode = 142

    #@perhaps_wait
    def do_test(self, request_id=0, wait=False):
        """Do test. (opcode: 255)
        Documentation at:
          http://eptwiki.rii.ricoh.com:8080/display/ePro/
            Display+Server+API#DisplayServerAPI-dotest
        """
        fmt = "@7L"
        self._send(pack(fmt, 0x131C014E, calcsize(fmt),
                # Op code and options
                255, 0,
                request_id,
                # Int and char arg counts
                0, 0))



    do_test.opcode = 255

