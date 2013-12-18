# Copyright 2011 Ricoh Innovations, Inc.
import os, threading, struct
from PIL import Image
from ew.util import ew_logging as log, system_config as config
from ew.util import comms
from fds_document import FDSDocument
from fds_overlay import FDSOverlay, level_compare
from ds_parsing import UDPOutputSocket, UDPInputSocket, BinaryMessageReceiver
from ew.util.ds_message import DsMessage
from sdk.display_constants import COLOR_WHITE
from sdk.bounding_box import BoundingBox
import wx

Page_Size = 825,1200
Infobar_Height = 66
InputSocket = '/tmp/PTU_localsocket'
OutputSocket = '/tmp/PTU_sendsocket'

logger = log.getLogger('faux_ds.ds_calls')

def adjust_location(location, relative_pt):
    x0, y0 = relative_pt
    return location[0] - x0, location[1] - y0

def crop_to_box(image, box):
    return image.crop(box.as_points())

def box_from_location_image(loc, image):
    x,y = loc
    w,h = image.size
    return BoundingBox(loc, (x+w, y+h))

def cropbox(loc, size):
    x, y = loc
    w, h = size
    return (x, y, x + w, y + h)

class FauxDSServer:
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._document = None
        self._current_page = None
        self._infobar_image = self._open_infobar()
        self._page_image = Image.new("L", Page_Size)
        self._page_image.paste( self._infobar_image, (0,0))
        self._page_overlays = {}
        self._doc_overlays = {}
        
        self._config_vars = {}
        self._display = None
        self._set_up_xmlrpc_server()
        self._start_command_processing()
#        self._setup_event_sending()

    def _ensure_event_sending_ready(self):
        if hasattr(self, '_output'):
            return

        self._output = UDPOutputSocket(OutputSocket).sock
        self._event_map = dict(
            on_stroke = (0, 'iiSii'),
            on_page = (1, 's'),
            on_submit = (2,''),
            on_read_complete = (3, 'i'),
            on_render_complete = (4, 'i'),
            on_error = (5, 'ii'),
            on_stroke_file_ready = (6, 'ss'),
            on_landscape = (7,''),
            on_portrait = (8,''),
            on_sleep = (9,''),
            on_doze = (10,''),
            on_wake = (11,''),
            on_shutdown = (12,''),
            on_fuel_gauge_change = (13,''))
        
    def _start_command_processing(self):
        inputsock = UDPInputSocket(InputSocket)
        self._buffered_input = BinaryMessageReceiver(DsMessage, inputsock.sock)
        message_options = self._buffered_input.options_as_dict
        
        self._option_map = {
            100: self.load_document,
            101: self.insert_page,
            102: self.delete_page,
            103: self.update_region_of_page,
            104: self.update_region_of_infobar,
            105: self.jump_to_page,
            106: self.next_page,
            107: self.prev_page,
            110: self.create_overlay_window,
            111: self.modify_overlay_window,
            112: self.close_overlay_window,
            120: self.change_config,
            130: self.erase_strokes_by_index}

        def do_items():
            while 1:
                msg = self._input_buffer.get()
                self._ensure_event_sending_ready()
                if msg == 'STOP':
                    break
                else:
                    fun = self._option_map.get(msg.op_code, None)
                    if fun:
                        try:
                            options = message_options(msg)
                            args = msg.int_args + msg.char_args
                            logger.debug('executing %s(%s) with options %s',
                                         fun.__name__,
                                         args, options)
                            fun(*args, **options)
                        except:
                            logger.exception('Error running %s',
                                             fun.__name__)
                    else:
                        logger.error("Received message with unknown opcode %r",
                                     msg)
        self._buffered_input.start()
        self._input_buffer = self._buffered_input.queue()
        self._input = threading.Thread(name='ds_input', target = do_items)
        self._input.setDaemon(True)
        self._input.start()

    def _set_up_xmlrpc_server(self):
        server = comms.create_threaded_server(
            comms.DS_INPUT_PORT)
        self._xmlserver = comms.ServerThread('ds_server', server)
        server.register_function(self.load_document)
        server.register_function(self.insert_page)
        server.register_function(self.delete_page)
        server.register_function(self.update_region_of_page)
        server.register_function(self.update_region_of_infobar)
        server.register_function(self.jump_to_page)
        server.register_function(self.next_page)
        server.register_function(self.prev_page)
        server.register_function(self.change_config)
        server.register_function(self.create_overlay_window)
        server.register_function(self.modify_overlay_window)
        server.register_function(self.close_overlay_window)
        server.register_function(self.erase_strokes_by_index)
        server.register_function(self.no_ink_in_region)
        server.register_function(self.doze)
        server.register_function(self.sleep)
        server.register_function(self.set_doze_timer)
        server.register_function(self.do_test)
        self._xmlserver.start()

    def shutdown(self):
        logger.debug('shutting down')
        self._xmlserver.server.shutdown()
        self._instance = None
        self._display = None
        del self

    def _open_infobar(self):
        path = os.path.join(config.data_home, 'static-infobar.pgm')
        return Image.open(path).copy()

    def set_display(self, display):
        self._display = display

    def _save_ink(self):
        if self._display:
            ink = self._display.get_new_ink()
            #TBD code to write ink file

    def _get_ink(self):
        #TBD real code to read ink for current page
        return [] #temp hack

    def _close_current_page(self):
        if self._current_page:
            self._save_ink()
            self._page_overlays.clear()
            
    def _close_current_document(self):
        if self._document:
            self._close_current_page()
            self._doc_overlays.clear()
            del self._document
            self._document = None
            self._display.on_close_document()
        
    def load_document(self, page_num, doc_path, flash=False, force_reload=False):
        try:
            self._close_current_document()
            self._document = FDSDocument(doc_path)
            self._current_page = self._document.page_by_index(page_num)
            self._display_page()
            self._send_on_page()
        except:
            logger.exception("Counld not load document at %s, page_id %d",
                         doc_path, page_num)
            
    def insert_page(self, page_id, before_id = None):
        self._document.insert_page(page_id, before_id)

    def delete_page(self, page_id):
        try:
            if page_id == self._current_page.pageid:
                self.next_page() if not self._current_page.is_last_page() else \
                             self.prev_page()
            self._document.delete_page(page_id)
        except:
            logger.error("Could not delete page %s", page_id)
    
    def update_region_of_page(self, x_d, y_d, x_src, y_src, w_src, h_src,
                              page_id, path, clear_ink=False, delete_image=False, flash=False, redraw=False):
        dest = x_d, y_d
        source = x_src, y_src, w_src, h_src
        page = self._document.page_by_id(page_id)
        if page:
            image = self._load_and_crop_image(source, path)
            if image:
                self._update_display(dest, image)
        else:
            logger.debug("Unknown page id %s", page_id)

    def _load_and_crop_image(self, src_dimensions, path):
        try:
            image = Image.open(path)
        except:
            logger.debug("Could not load image from %s", path)
            return
        sz = src_dimensions[-2:]
        loc = src_dimensions[:2]
        if sz != image.size:
            image = image.crop(cropbox(loc, sz))
        return image
        
    def update_region_of_infobar(self, x_d, y_d, x_src, y_src, w_src, h_src, path, clear_ink=False, flash=False, redraw=False):
        dest = x_d, y_d
        src = x_src, y_src, w_src, h_src
        image = self._load_and_crop_image(src, path)
        if image:
            if self._display:
                self._update_display(dest, image)

    def jump_to_page(self, page_id):
        self._close_current_page()
        self._current_page = self._document.page_by_id(page_id)
        self._display_page()
        self._send_on_page()

    def _display_infobar(self):
        self._update_display((0,0), self._infobar.image)

    def _display_page(self):
        """display the current page"""
        image = self._current_page.get_image()
        image = image.crop((0, Infobar_Height, 825, 1200))
        self._update_display((0, Infobar_Height), image)

    def _update_display(self, location, image):
        self._page_image.paste(image, location)
        wx.CallAfter(self._display.update_region, location, image)
        
    def next_page(self):
        self._handle_next_page()

    def prev_page(self):
        self._handle_prev_page()

    def change_config(self, name, value):
        self._config_vars[name] = value

    
    def _top_window_containing(self, point):
        for overlay in self._overlays_descending_order():
            if overlay.contains_point(point):
                return overlay
        return self._current_page

    def handle_points(self, index, millis, points, start=False, end=False):
        """break points up into parts over windows if needed,
        send the on_stroke events setting the flags"""
        flags = 0x01 if start else 0
#        return
        if end: flags |= 0x02
        if start:
            self._window_for_stroke = self._top_window_containing(points[0])
        if self._window_for_stroke:
            points = self._window_for_stroke.adjusted_points(index, points)
            if points or end:
                unwrapped = []
                for p in points:
                    unwrapped.extend(p)
                self._send('on_stroke', index, flags,
                       self._window_for_stroke.identity(), millis, *unwrapped)
        else:
            logger.debug('sampled ignored as no document is open')

    def _send(self, command, *args):
        endian = '!'
        logger.debug('attempting to send %s%s',
                     command, args)
        info = self._event_map.get(command)
        logger.debug('send info = %s', info)
        def expand_format(fmt, *args):
            exp_fmt = ''
            exp_args = []
            for i in range(len(fmt)):
                f = fmt[i]
                a = args[i]
                if f in 'Ss':
                    exp_args.append(len(a))
                    exp_fmt += 'I%d' % len(a)
                exp_fmt += f
                exp_args.append(a)
            return exp_fmt, exp_args

        if info:
            if command != 'on_stroke':
                efmt, eargs = expand_format('i' + info[1], info[0], *args)
                logger.debug('format: %s args: %s', efmt, eargs)
                fmt = endian + efmt
                msg = struct.pack(fmt, *eargs)
                logger.debug('pack of: %s with format: %s gives: %s',
                             eargs,
                             efmt, msg)
            else:
                index, flags, display, millis = args[:4]
                rest = args[4:] #point x y values
                samples = len(rest) / 2
                dis_len = len(display)
                m_dis = dis_len % 4
                pad = 4 - m_dis if m_dis else 0
                if pad:
                    fmt = 'iiii%ds%dxii%dH' % (dis_len, pad, len(rest))
                else:
                    fmt = 'iiii%dsii%dH' % (dis_len, len(rest))

                logger.debug('onstroke(fmt: %s, index: %d, flags: %d, display: %s, millis: %d, samples: %d, %s',
                             fmt, index, flags, display, millis, samples, rest)
                msg = struct.pack(endian + fmt, info[0], index, flags, dis_len,
                                  display, millis, samples, *[4*x for x in rest])
            self._output.send(msg)
        else:
            logger.error('unknown command %s could not be sent',
                         command)
                
    def _send_on_page(self):
        self._send('on_page', self._current_page.page_id)
        
    def _handle_next_page(self):
        if self._index < self._document.max_index - 1:
            self._index += 1
            self._close_current_page()
            self._current_page, self._pageid = \
                            self._document.page_by_index(self._index)
            self._display_page()
            self._send_on_page()

    def _handle_prev_page(self):
        if self._index > 0:
            self._adjust_overlays()
            self._index -= 1
            self._close_current_page()
            self._current_page, self._pageid = \
                            self._document.page_by_index(self._index)
            self._display_page()
            self._send_on_page()

    def _handle_submit(self):
        self._send('on_submit')

    def _adjust_overlays(self):
        """we are doing a page change.  close any single page overlays"""
        pass

    def _all_overlays(self):
        return self._page_overlays.values() + self._doc_overlays.values()
        
    def _overlays_ascending_order(self):
        return sorted(self._all_overlays(), cmp=level_compare)
    
    def _overlays_descending_order(self):
        return sorted(self._all_overlays(), cmp=level_compare, \
                      reverse=True)

    def _overlapping_overlays(self, box, level):
        overlays = [other for other in self._overlays_ascending_order() \
                    if other.level > level]
        overlaps = []
        for other in overlays:
            intersect = box.intersection_with(other.bounding_box())
            if intersect:
                overlaps.append((other, intersect))
        return overlaps
            
        
    def _overlaid_regions(self, overlay):
        overlays = [other for other in self._overlays_ascending_order() \
                    if other.level < overlay.level]
        box = overlay.bounding_box()
        overlaps = [(self._current_page, box)]
        for other in overlays:
            intersect = box.intersection_with(other.bounding_box())
            if intersect:
                overlaps.append((other, intersect))
        return overlaps

    def _draw_beneath_overlay(self, overlay):
        obox = overlay.bounding_box()
        o_x,o_y,o_w,o_h = obox.as_xywh()
        working = Image.new("L",(o_x, o_y), COLOR_WHITE)
        for window, box in self._overlaid_regions(overlay):
            logger.debug('drawing_under window %s with box %s',
                         window, box)
            x,y,w,h = box.as_xywh()
            image = window.get_image()
            loc = window.relative_location((x,y))
            im = image.crop(cropbox(loc, (w,h)))
            working.paste(im, overlay.relative_location((x,y)))
        self._update_display((o_x, o_y), working) 

    def _draw_image_at_level(self, dest, image, level=0):
        """draw the image and any part of anything at a higher level that should
        cover it"""
        working = image.copy()
        obox = box_from_location_image(dest, image)
        for window, box in self._overlapping_overlays(obox, level):
            x,y,w,h = box.as_xywh()
            im = window.image_in_box(box)
            working.paste(im, adjust_location((x,y), dest))
        self._update_display(dest, working) 
        
            
    def _draw_overlay(self, overlay):
        obox = overlay.bounding_box()
        self._draw_image_at_level(overlay.bounding_box().top_left(),
                                  overlay.get_image(), overlay.level)

    def _draw_removing_overlay(self, overlay):
        #assumes overlay not registered by now
        image = crop_to_box(self._current_page.get_image(),
                            overlay.bounding_box())
        self._draw_image_at_level(overlay.bounding_box().top_left(),
                                  image, -1)
        
        
        
    def _set_overlay_level(self, overlay):
        overlays = self._overlays_descending_order()
        box = overlay.bounding_box()
        for other in overlays:
            if box.intersects_box(other.bounding_box()):
                overlay.level = other.level + 1
                break
        return

    def _get_overlay(self, display_id):
        return self._page_overlays.get(display_id) or \
               self._doc_overlays.get(display_id)

    def create_overlay_window(self, x_d, y_d, x_src, y_src, w_src, h_src, page_id, display_id, path, clear_ink=False, 
                              delete_image=False, disable_page_turn=False, flash=False, redraw=False):
        dest = x_d, y_d
        src = x_src, y_src, w_src, h_src
        if page_id and (page_id != self._current_page.identity()):
            logger.debug("can't create ovelay. current page is %s not %s",
                         self._current_page.page_id, page_id)
            return
        
        image = self._load_and_crop_image(src, path)
        overlay = FDSOverlay(display_id, dest, image)
        if page_id:
            self._set_overlay_level(overlay)
            self._page_overlays[display_id] = overlay
        else:
            self._doc_overlays[display_id] = overlay

        self._draw_overlay(overlay)
            

    def modify_overlay_window(self, x_d, y_d, x_src, y_src, w_src, h_src, display_id, path, clear_ink=False, delete_image=False, flash=False, redraw=False):
        dest = x_d, y_d
        src = x_src, y_src, w_src, h_src
        overlay = self._get_overlay(display_id)
        if overlay:
            image = self._load_and_crop_image(src, path)
            overlay.update_region(dest, image)
            self._draw_image_at_level(overlay.screen_location(dest),
                                      image, overlay.level)
        else:
            logger.debug('No overlay named %s', display_id)
            
    def close_overlay_window(self, display_id, flash=False, redraw=False):
        overlay = self._get_overlay(display_id)
        if overlay:
            self._page_overlays.pop(overlay.identity(), None)
            self._doc_overlays.pop(overlay.identity(), None)
            self._draw_removing_overlay(overlay)
            del overlay
        else:
            logger.debug('No overlay named %s', display_id)

    def erase_strokes_by_index(self, start, end, window_id):
        pass  

    def erase_ink_in_region(self, region, window_id):
        pass 

    def no_ink_in_region(self, region, window_id):
        pass
    
    def doze(self):
        pass

    def sleep(self):
        pass

    def set_doze_timer(self, timeout):
        pass

    def do_test(self):
        pass
     
    def show_page(self, page):
        pass

    

        
    
    
        
