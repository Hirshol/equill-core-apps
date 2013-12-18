#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.

"""Infobar operations."""

from PIL import Image, ImageDraw

Infobar_Height = 66
Infobar_Size = 825,Infobar_Height
Infobar_Path = '/data/infobar.pgm'
Button_Size = 63  #width and height and with border at sides..

from ew.util import ew_logging, system_config as sysconfig
from sdk.display_window import DisplayWindow, pending_gui
from sdk.widgets.image_label import ImageLabel
from sdk.display import Display, get_font
from sdk.display_constants import PEN_RESOLUTION, COLOR_WHITE
from sdk.intersect import WidgetMap
from sdk.bounding_box import BoundingBox
from sdk.widgets.image_button import ImageButton
import threading, os

Infobar_Scaled_Height = Infobar_Height * PEN_RESOLUTION
Blank_Infobar = Image.new("L", (825,66), COLOR_WHITE)

logger = ew_logging.getLogger('ew.launcher.infobar')

class Infobar(DisplayWindow):
    _static_path = "/data/static-infobar.pgm"
    def __init__(self, doc_runner):
        self._runner = doc_runner
        DisplayWindow.__init__(self, 825, Infobar_Height,widget_id='Infobar')
        self._widget_map = WidgetMap(grid = (10,1),screen_size=Infobar_Size)
        self._battery_level = 2 #just made up for now
        self._active_button = None
        self._active_ip = None
        self._document_title = None
        self.create_gui()
        #self.on_inbox(self._inbox_button)
        self._disabled = False
        self._update_ds_lock = threading.RLock()
        self._page_id = None

    def launcher(self):
        return self._runner

    def identity(self):
        return self._page_id if self._page_id else DisplayWindow.identity(self)

    def adjusted_full_box(self):
        return BoundingBox((0,0), Infobar_Size)
    
    def current_page(self):
        pass

    def update_using_region_of_page(self, page_id):
        self._page_id = page_id
        with self._update_ds_lock:
            if not self._disabled:
                h, w = Infobar_Size
                self.launcher().update_region_of_page(0, 0, 0, 0, h, w, page_id, self._static_path)

    def owns_stroke(self, index, flags, display_id, millis, points):
        contains_point = (points[0][1] < Infobar_Scaled_Height) if points else False
        return flags & 0x10 or contains_point

    def set_title(self, doc_title):
        """draw the text using white-ish pen more or less centered in the available space.
        Append the current ip-addr in square brackets if there is room.  Consider appending
        the pagenumber instead at a later date"""
        if self._disabled: return
        if self._document_title != doc_title:
            self._document_title = doc_title
            self._draw_text()


    def set_active_button(self, button):
        with self._update_ds_lock:
            if button != self._active_button:
                if self._active_button:
                    self._active_button.state = 'default'
                    self._active_button.update()
                self._active_button = button
                if self._active_button:
                    self._active_button.state = 'selected'
                    self._active_button.update()

    def enable(self):
        """go back to normal state if in disabled state"""

        if self._disabled:
            with self._update_ds_lock:
                self._disabled = False
                self._settings_button.set_disabled(False)
                #self._templates_button.set_disabled(False)
                self._inbox_button.set_disabled(False)
                self.process_changes()

    def disable(self):
        """go to disabled state"""
        with self._update_ds_lock:
            self._settings_button.set_disabled(True)
            #self._templates_button.set_disabled(True)
            self._inbox_button.set_disabled(True)
            self._disabled = True
            try:
                self.process_changes()
            except:
                logger.exception('This is usually ok if we are blanking the infobar')

    def blank_image(self):
        Blank_Infobar.save(self._static_path)
        
    def restore_image(self):
        with self._update_ds_lock:
            self.working_image().save(self._static_path)

    def _draw_pointer(self, x_location):
        """draws the current item bottom pointer"""
        pass #TBD

    def create_gui(self):
        class NumberedImageLabel(ImageLabel):
            def __init__(self, name, root_name, index_range):
                self._range = index_range
                self._index = self._range[0]
                self._root = root_name
                ImageLabel.__init__(self, name, 63, 63,
                                    self._image_number(index_range[0]),widget_id=name)

            def _image_number(self, num):
                image_path = None
                if num in range(*self._range):
                    self._index = num
                    image_path = '%s_%d.pgm' % (self._root, self._index)
                else:
                    logger.error('%r is not in range %r', num, range(*self._range))
                return image_path

            def set_image(self, path):
                ImageLabel.set_image(self, path)
                self._index = None

            def set_image_number(self, num):

                if self._index != num:
                    path = self._image_number(num)
                    logger.debug('image path for %d is %s', num, path)
                    if path:
                        self.set_image(path)

        with Display.instance().pending:
            self._default_image_file = os.path.join(sysconfig.images_dir, 'static-infobar.pgm')
            self._working_image = Image.open(self._default_image_file).copy()
            button_top = Infobar_Height - Button_Size
            self._is_locked = False
            self._set_up_button_areas(button_top)
            self._wifi = NumberedImageLabel('wifi', 'wifi', (0,4))
            self._wifi.set_image_number(3)
            self._radio = NumberedImageLabel('radio', 'radio', (0,6))
            self._roaming_radio = NumberedImageLabel('radio_r', 'radio_r', (1,6))
            self._airplane_mode = ImageLabel("airplane_mode_icon", 63, 63, "airplane.pgm")
            self._no_connection = ImageLabel("no_connection", 63, 63, "no_connection.pgm")
            self._network_widgets = {'3GR' : self._roaming_radio, '3g' : self._radio, 'wifi' : self._wifi, 'airplane': self._airplane_mode, 'None': self._no_connection}
            #all our widgets on the infobar are 63,63 size and include sife border.
            #so just get our starting k and start adding
            x = self._settings_button.x + Button_Size
            self.add(self._wifi, x, button_top)
            self.net_location = x, button_top
            self._network_type = 'wifi'
            x += Button_Size
            self._battery = NumberedImageLabel('battery', 'battery', (0,5))
            self._battery.set_image_number(3)
            self.add(self._battery, x, button_top)
            self._text_min_x = self._inbox_button.x + 2 * Button_Size
            text_max_x = self._settings_button.x
            self._text_max_sz = text_max_x - self._text_min_x
            self._blank_text = self._working_image.crop((self._text_min_x, 0, text_max_x, Infobar_Height))
#            self._blank_text = Image.new('L', (self._text_max_sz, Infobar_Height), color=23)
            self._text_font = get_font(22)

    def send_changes_to_DS(self):
        if not self._disabled:
            if self._changed_region:
                x,y,w,h = self._changed_region.as_xywh()
            else:
                x,y = 0,0
                w,h = Infobar_Size
            logger.debug('sending changes for %s to DS updating %s',
                     self.identity(), (x,y,w,h))
            self._runner.update_region_of_page(x, y, x, y, w, h, 
                                           self.identity(), self.image_path())
            self.reset_changed_region()
    
    def _draw_text(self):
        def too_big(text):
            return self._text_font.getsize(text)[0] > self._text_max_sz

        def adjust_text(text):
            n_off = 3
            if too_big(text):
              text = text[:-n_off] + '..'
              while too_big(text):
                  n_off += 1
                  text = text[:-n_off] + '..'
            return text, self._text_font.getsize(text)

        text = '%s' % (self._document_title)
        text, size = adjust_text(text)
        self._document_title = text
        #calculate text start to center it
        width = size[0]

        x = self._text_min_x + (self._text_max_sz - width) / 2
        y = (Infobar_Height - size[1]) / 2
        #clear the text area
        self._working_image.paste(self._blank_text, (self._text_min_x, 0))
        #draw the text
        draw = ImageDraw.ImageDraw(self._working_image)
        draw.text((x,y), text, font=self._text_font, fill=255)
        with self._update_ds_lock:
            self.set_dirty()
            self.process_changes()

    def image_path(self):
        return self._static_path

    def is_infobar(self):
        return True

    def _set_up_button_areas(self, button_top):
        def make_button(name, main_image_name, handler):
            default = '%s.pgm' % main_image_name
            selected = '%s_selected.pgm' % main_image_name
            button = ImageButton(name, Button_Size, Button_Size, "DEFAULT", default,
                                 selected_path = selected,
                                 widget_id = name)
            button.add_callback(handler, 'on_button_press')
            return button

        x = 10
        self._inbox_button = make_button('inbox','inbox', self.on_inbox)
        self.add(self._inbox_button, x, button_top)
        x += Button_Size
        self._lock_button = ImageButton('lock', 63, 63, "DEFAULT", 'inbox_disabled.pgm', 
                                        selected_path = 'large_lock.pgm', widget_id = 'lock')
        self.add(self._lock_button, x, button_top)
        self._lock_button.add_callback(self.unlock_document, 'on_button_press')
        self._settings_button = make_button('settings', 'settings', self.on_settings)
        self.add(self._settings_button, 634, button_top)

    def unlock_document(self, widget):
        if self._is_locked:
            self._settings_button.set_disabled(False)
            self._inbox_button.set_disabled(False)
            self._lock_button.state = 'default'
            self._runner.unlock_document()
            self._is_locked = False

    def lock_document(self):
        self._settings_button.set_disabled(True)
        self._inbox_button.set_disabled(True)
        self._lock_button.state = 'selected'
        self._is_locked = True

    def _call_in_thread(self, function):
        logger.debug('Starting infobar thread executing %s',
                     function.__name__)
        thread = threading.Thread(target=function, name='infobar_thread')
        thread.setDaemon(True)
        thread.start()

    def mark_inbox_active(self):
        self.set_active_button(self._inbox_button)

    def on_inbox(self, button):
        self.set_active_button(button)
        self._call_in_thread(self._runner.open_inbox)

    def on_templates(self, button):
        self.set_active_button(button)
        self._call_in_thread(self._runner.open_templates)


    def on_settings(self, button):
        self.set_active_button(button)
        self._call_in_thread(self._runner.open_settings)

    def set_battery_level(self, level, charging=False):
        """should redraw battery level indicator by call
        back to the doc_runner if it has changed enough"""
        #assumes level is 0-4 inclusive and that if charging
        #we display the battery_none (lightning bold overlaid icon).
        #change to do the converting math if we get a percentage full instead
        if charging:
            self._battery.set_image('battery_none.pgm')
        else:
            self._battery.set_image_number(level)
        self.process_changes()

    def _network_widget(self):
        return self._network_widgets[self._network_type]

    def set_network_level(self, level, active_ip = None):
        """level is 0..3 inclusive for wifi and 0..5 inclusive for 3G. active_ip is the ip address of
        the current wireless."""
        self._network_widget().set_image_number(level)
        if active_ip != self._active_ip:
            self._active_ip = active_ip

    def set_network_info(self, network_type, network_level, ssid, active_ip = None):
        with pending_gui():
            if network_type == None or network_type == 'None':
                self._network_widget().set_image('no_connection.pgm')
            else:
                self.set_network_type(network_type)
                if network_type == 'wifi' and not ssid:
                    self._network_widget().set_image('wifi_none.pgm')
                elif network_type != "airplane":
                    self.set_network_level(network_level, active_ip)
        self.process_changes()

    def set_network_type(self, network_type):
        'set network type to either "wifi" or "3G" or "3GR" or "airplane"'
        if not network_type in ('wifi', '3g', '3GR', 'airplane', 'None'):
            logger.debug('unknown network type %r ignored', network_type)
            return

        if network_type != self._network_type:
            old_widget = self._network_widgets.get(self._network_type)
            new_widget = self._network_widgets.get(network_type)
#            logger.debug('network types are %s', self._network_widgets)
            if old_widget in self.elements:
                self.elements.remove(old_widget)
                old_widget.parent = None
            self.add(new_widget, *self.net_location)
            self._network_type = network_type

