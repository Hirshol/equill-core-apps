#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
import threading, subprocess, os
import ew.util.tablet_config as tablet_config
from sdk.widget_cache import ImageCache
from sdk.widgets.button import Button
from sdk.widgets.checkbox import Checkbox
from sdk.widgets.image_button import ImageButton
from sdk.widgets.label import Label
from sdk.widgets.image_label import ImageLabel
from sdk.widgets.radio_button import RadioButton
from sdk.grouping import Grouping
from sdk.widgets.panel import Panel
from sdk.widgets.hotspot import Hotspot
from sdk.overlay_switch import InputText
from sdk.overlay_switch import Password
from sdk.widgets.progress_bar import ProgressBar
from sdk.widgets.dropdown import Dropdown
from sdk.widgets.level_selector import LevelSelector
from sdk.display_constants import SCREEN_SIZE, Infobar_Height
from ew.internal_decs.network_item_panel import NetworkItemPanel
from ew.internal_decs.network_action_dialog import NetworkActionDialog
from ew.internal_decs.network_action import NetworkAction
from ew.internal_decs.settings_software_update import SoftwareUpdate
from ew.util import ew_logging, ew_exec
if not os.getenv('emulate_tablet'):
    from ew.services.audio import AudioService

logger = ew_logging.getLogger('ew.internal_decs.settings_class')
testing = False

start_divider = 120
divider_height = 35
line_spacer = 16
margin_divider = 20
section_margin = 50
margin_left = 45
start_body = start_divider + divider_height + margin_divider
title_font_size = 22
entry_font_size = 20
warning_font_size = 18
input_font_size = 16

_refresh_lock = threading.Lock()
DOC_TITLE = "SETTINGS"


class SettingsBase:
    """Base class to use for all the settings pages. Creates a singleton."""

    _instance_lock = threading.RLock()
    _instance = None

    @classmethod
    def instance(cls):
        with cls._instance_lock:
            if not cls._instance:
                cls()
            return cls._instance

    def __init__(self):
        with self._instance_lock:
            if self._instance:
                raise RuntimeError(
                        "Additional instances of singleton class %r should"
                        " not be created -- use '%s.instance()' method" %
                        ((self.__class__.__name__,) * 2))
            self.__class__._instance = self
            self.tablet_conf = None
            self._widgets_bound = False
            try:
                self.tablet_conf = tablet_config.Config()
                if not self.tablet_conf.is_provisioned():
                    logger.warning("Ricoh eQuill not provisioned")
            except Exception, e:
                logger.warning("Exception: Tablet not provisioned? %r", e)
            self.initialize_data()

    def gui(self):
        return self.doc_page.gui_page()

    def initialize_data(self):
        self.sync_data = self.get_sync()
        if self.sync_data and 'tablet_version' in self.sync_data:
            self.software_version = self.sync_data['tablet_version']
        else:
            self.software_version = self.get_build_id()
        if self.sync_data and 'tablet_id' in self.sync_data:
            self.serial_number = self.sync_data['tablet_id']
        else:
            self.serial_number = self._get_serial_number()
    
    def _get_network_service(self):
        if not hasattr(self, '_network_service') or self._network_service is None:
            self._network_service = self.doc_page._document.launcher()._network
        return self._network_service

    def on_entry(self, doc_page):
        self.doc_page = doc_page

    def on_page_entry(self, delegate, doc_page):
        self.delegate = delegate
        self.doc_page = doc_page
        self.network_action = NetworkAction(self._get_network_service())
        if not doc_page.gui_filled_in:
            self.last_position = Infobar_Height + 1
            self.create_gui(delegate, doc_page)
            if not self._widgets_bound:
                self.doc_page.bind_widgets()
                self._widgets_bound = True
            self.doc_page.gui_filled_in = True
        else:
            self.doc_page.display(True)
        self.refresh()

    def on_page_exit(self):
        #let change settings page clean up the gui properly instead of doing a hack
        self.doc_page.gui_filled_in = False
        self.gui() #for side effects

    def refresh(self):
        pass

    def clean_widgets(self, parent):
        parent.elements = []
        self.doc_page.gui_page().remap_widgets()

    def _get_last_position(self, component):
        return component.y + component.h

    def create_title(self, title):
        title_label = Label(title, font_size=title_font_size)
        title_label.transparent = True
        self.doc_page.gui_page().add(title_label,
                SCREEN_SIZE[0]/2-title_label.w/2, 66 + 10)
        self.last_position = self._get_last_position(title_label)
        return title_label

    def create_divider(self, x, y, title):
        divider_widget = Panel(SCREEN_SIZE[0], 35)
        self.doc_page.gui_page().add(divider_widget, x, y)
        divider_bg = ImageCache.instance().get_image("settings_divider.pgm")
        divider_widget.set_background(divider_bg)
        divider_label = Label(title, font_size=title_font_size)
        divider_label.transparent = True
        divider_widget.add(divider_label, 34, 4)
        self.last_position = self._get_last_position(divider_widget)
        return divider_widget

    def _add_settings_line(self, x, y, label, value_widget, widget_id=None):
        name_widget = Label(label, font_size=entry_font_size,
                widget_id='label_' + widget_id if widget_id else None)
        name_widget.transparent = False
        name_value_panel = Panel(SCREEN_SIZE[0]-margin_left-x,
                name_widget.h, (), widget_id=widget_id)
        name_value_panel.add(name_widget, 0, 0)
        value_x = name_value_panel.w-value_widget.w
        name_value_panel.add(value_widget, value_x, 0)
        page = self.gui()
        page.add(name_value_panel, x, y)
        logger.debug('added panel %r to page %r with id %d', 
                name_value_panel,  page, id(page))
        self.last_position = self._get_last_position(name_value_panel)
        return name_value_panel

    def add_navigation_divider(self, x, y, w, h):
        image_label = ImageLabel("navigation_divider", w, h, 
                "navigation_divider.pgm")
        self.doc_page.gui_page().add(image_label, x, y)
        self.last_position = self._get_last_position(image_label)
        return image_label

    def add_navigation_entry(self, x, y, name, page_id):
        name_widget = Label(name, font_size=entry_font_size)
        name_widget.transparent = False
        navigation_icon = ImageLabel("navigation_forward", 56, 28, 
                "navigation_forward.pgm")
        name_value_panel = Panel(SCREEN_SIZE[0]-margin_left-x, navigation_icon.h)
        hotspot_panel = Hotspot(SCREEN_SIZE[0]-margin_left-x, 
                navigation_icon.h, widget_id=page_id)
        hotspot_panel.add_listener(self.delegate)
        name_value_panel._invertable = True
        name_value_panel.add(navigation_icon, 
                name_value_panel.w-navigation_icon.w, 0)
        name_value_panel.add(name_widget, 0, 0)
        name_value_panel.add(hotspot_panel, 0, 0)
        page = self.gui()
        page.add(name_value_panel, x, y)
        self.last_position = self._get_last_position(name_value_panel)
        return name_value_panel

    def add_footer_navigation(self, x, y, navigation_entries):
        spacer = 20
        nav_icon_size = 36, 36
        num_items = len(navigation_entries)
        panel_w = (nav_icon_size[0] * num_items) + (spacer * (num_items-1))
        panel_h = nav_icon_size[1]
        navigation_panel = Panel(panel_w, panel_h)
        panel_x = 0
        for item in navigation_entries:
            icon = None
            key = item[0]
            value = item[1]
            if key == "back":
                icon = "nav_left.pgm"
            elif key == "home":
                icon = "nav_home.pgm"
            elif key == "forward":
                icon = "nav_right.pgm"                 
            navigation_widget = ImageButton(value, nav_icon_size[0], 
                        nav_icon_size[1], "default", icon, widget_id=value)
            navigation_widget.add_callback(self.delegate.on_hotspot, 
                    'on_button_press')
            navigation_panel.add(navigation_widget, panel_x, 0)
            panel_x = panel_x + nav_icon_size[0] + spacer
        return self._add_settings_line(x, y, "", navigation_panel)    

    def add_name_value(self, x, y, name, value, widget_id=None):
        w, h = 400, 25
        value_widget = Label(value, w, h, font_size=entry_font_size,
                widget_id='value_' + widget_id if widget_id else None)
        value_widget.align = "right"
        value_widget.transparent = False
        return self._add_settings_line(x, y, name, value_widget, widget_id)

    def add_radio_choice(self, header, group_id, is_on, callback, panel_id=None):
        def make_button(suffix):
            name = '%s_%s' % (group_id, suffix)
            return RadioButton(name, 26, 26, group_id=group_id, widget_id=name)

        def panel_horizontal_wrapping(sep, *widgets):
            def x_after(widget):
                return (widget.x + widget.w + sep) if widget else 0

            width = sep * (len(widgets) - 1)
            height = widgets[0].h
            for w in widgets: width += w.w

            panel = Panel(width, height, (), widget_id=panel_id)

            last_widget=None
            for w in widgets:
                panel.add(w, x_after(last_widget), 0)
                last_widget = w
            
            return panel
                

        mode_on = make_button('on')
        mode_off = make_button('off')
        on_label = Label("On", font_size=entry_font_size)
        off_label = Label("Off", font_size=entry_font_size)

        choice_panel = panel_horizontal_wrapping(6,  mode_on, on_label, mode_off,
                                                  off_label) 
        choice_group = Grouping.with_id(group_id)

        
        self._add_settings_line(margin_left, self.last_position + line_spacer,
                                header, choice_panel)
        choice_group.set_selection(mode_on if is_on else mode_off)
        choice_group.add_callback(callback, 'on_group_selection')

        return choice_panel, choice_group

    def create_radio_choice(self, group_id, state="on", widget_id=None):
        mode_on = RadioButton(group_id+"_on", 26, 26,
                group_id=group_id, widget_id=group_id+"_on")
        mode_on.transparent = False
        mode_on.style = 'image'
        mode_on_label = Label("On", font_size=entry_font_size)
        mode_on_label.transparent = False
        mode_off = RadioButton(group_id+"_off", 26, 26,
                group_id=group_id, widget_id=group_id+"_off")
        mode_off.transparent = False
        mode_off.style = 'image'
        mode_off_label = Label("Off", font_size=entry_font_size)
        mode_off_label.transparent = False
        sep = 6
        w = mode_on.w + mode_on_label.w + mode_off.w + mode_off_label.w + sep*3
        h = mode_on.h
        choice_panel = Panel(w, h, (), widget_id=widget_id)
        choice_panel.add(mode_on, 0, 0)
        choice_panel.add(mode_on_label, mode_on.x+mode_on.w+sep, 0)
        choice_panel.add(mode_off, mode_on_label.x+mode_on_label.w+sep, 0)
        choice_panel.add(mode_off_label, mode_off.x+mode_off.w+sep, 0)
        choice_group = Grouping.with_id(group_id)
        if state == "on":
            choice_group.set_selection(mode_on)
        else:
            choice_group.set_selection(mode_off)
        return choice_panel

    def create_choice_panel(self, group_id, choices, state=None, widget_id=None):
        choice_list = {}
        sep = 6
        w = h = 0
        count = 0
        for item in choices:
            choice_item = RadioButton(group_id+"_"+item, 26, 26, group_id)
            choice_item.transparent = False
            choice_item.style = 'image'
            choice_label = Label(item, font_size=entry_font_size)
            choice_label.transparent = False
            choice_list[count] = (choice_item, choice_label)
            count += 1
            w = w + choice_item.w + choice_label.w + sep*6
            h = choice_label.h
        x = y = 0
        choice_panel = Panel(w, h, (), widget_id=widget_id)
        for key, value in choice_list.iteritems():
            choice_item, choice_label = value
            default_state = "%s_%s" % (group_id, state)
            if choice_item.name == default_state:
                choice_item.state = "SELECTED"
            else:
                choice_item.state = "DEFAULT"
            choice_panel.add(choice_item, x, y)
            x = x + choice_item.w + sep
            choice_panel.add(choice_label, x, y)
            x = x + choice_label.w + sep*4
        return choice_panel

    def update_value(self, container_widget, value):
        if hasattr(container_widget, "elements"):
            for item in container_widget.elements:
                if isinstance(item, Label) and item.widget_id.startswith("value"):
                    item.set_text(value)

    def get_session(self):
        if self.tablet_conf and self.tablet_conf.has_section('session'):
            items = dict(self.tablet_conf.items('session'))
            return items

    def get_sync(self):
        if self.tablet_conf and self.tablet_conf.has_section('sync'):
            items = dict(self.tablet_conf.items('sync'))
            return items

    def get_tablet_info(self):
        items = {}
        if self.tablet_conf and self.tablet_conf.has_section('3G_info'):
            items.update(self.tablet_conf.items('3G_info'))
        if self.tablet_conf and self.tablet_conf.has_section('core_app'):
            items.update(self.tablet_conf.items('core_app'))
        if self.tablet_conf and self.tablet_conf.has_section('parameters'):
            items.update(self.tablet_conf.items('parameters'))
        return items

    def is_3g_capable(self):
        capable = False
        try:
            command_line = "/usr/local/bin/3Gcapable.py"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                capable = line
                break
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return capable

    def get_3g_info(self):
        params = {}
        CONF_FILE = "/data/etc/network.conf"
        if os.path.exists(CONF_FILE):
            with open(CONF_FILE,'r') as f:
                for line in f.readlines():
                    name,value = line.strip().split('=',1)
                    params[name] = value
        return params

    def get_build_id(self):
        build_id = ""
        try:
            command_line = "cat /MANIFEST.TXT"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                if line[0:26] == "manifest: build_identifier":
                    build_id = line.split('=')[1].strip()[1:-1]
                    break
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        if build_id.find("_") > -1 and build_id.find("+") > -1:
            build_id = build_id.split('_')[1].split('+')[0]
        return build_id

    def _get_serial_number(self):
        serial_number = ""
        try:
            command_line = "cat /nvram0/serialno.txt"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                if line:
                    serial_number = line.strip()
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return serial_number
    
    def _ping(self):
        return_message = ""
        try:
            command_line = "wpa_cli ping" 
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                line = line.strip()
                return_message = line
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return return_message

    def show_message(self, message):
        self.delegate.inform_user(message, 100, 200, 700, 
                parent_window=self.gui())       


class SettingsGeneral(SettingsBase):
    """Settings main page."""

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.last_position = start_divider
        self.create_divider(0, start_divider, "General")
        self.last_position+=margin_divider
        nav_w = SCREEN_SIZE[0]
        nav_h = 2
        navigation_spacer = 10
        airplane_mode_state = self._get_network_service().is_airplane_mode()
        self.add_radio_choice("Airplane Mode (Disable Radios)", "airplane_mode", 
                airplane_mode_state, delegate.on_airplane_mode)
        is_on = AudioService().is_audio_enabled()
        self.add_radio_choice("Sounds", "sound_settings", is_on, delegate.on_sound_settings)
#        self.sound_volume = LevelSelector(170, 30)
#        self._add_settings_line(margin_left, self.last_position+line_spacer,
#                "Volume", self.sound_volume)
#        current_level = int(AudioService().read_volume())
#        self.sound_volume.set_level(current_level)
#        self.sound_volume.add_callback(delegate.on_volume_change, 'on_volume_change')
        self.create_divider(0, self.last_position + section_margin, 
                "Other Settings")
        self.add_navigation_entry(margin_left,
                self.last_position + margin_divider, "Network", "network")
        self.add_navigation_divider(0, self.last_position+navigation_spacer, 
                nav_w, nav_h)
        self.last_position += navigation_spacer
        self.add_navigation_entry(margin_left, 
                self.last_position, "User", "user")
        self.add_navigation_divider(0, self.last_position+navigation_spacer, 
                nav_w, nav_h)
        self.last_position += navigation_spacer
        self.add_navigation_entry(margin_left, self.last_position, 
                "Tools", "tools")
        self.add_navigation_divider(0, self.last_position+navigation_spacer, 
                nav_w, nav_h)
        self.last_position += navigation_spacer
        self.add_navigation_entry(margin_left, self.last_position,
                "Software Update", "software_update")
        self.add_navigation_divider(0, self.last_position+navigation_spacer, 
                nav_w, nav_h)
        self.last_position += navigation_spacer
        self.add_navigation_entry(margin_left, self.last_position,
                "About", "about")
        self.add_navigation_divider(0, self.last_position+navigation_spacer, 
                nav_w, nav_h)
        self.last_position += navigation_spacer

    def refresh(self):
        pass
        
    def on_volume_change(self, *args):
        try:
            sound_volume = args[0]
            level = sound_volume.get_level()
            AudioService().set_volume(level)
        except Exception, e:
            logger.exception("Caught exception while setting volume %r", e)
        
    def on_airplane_mode(self, *args):
        airplane_mode_group = args[0]
        logger.debug("Selected: %r", airplane_mode_group) 
        name = airplane_mode_group.get_selection().name
        if name == "airplane_mode_on":
            self.enable_airplane_mode()
        else:
            self.disable_airplane_mode()

    def on_sound_settings(self, *args):
        sound_settings_group = args[0]
        logger.debug("Selected: %r", sound_settings_group) 
        name = sound_settings_group.get_selection().name
        if name == "sound_settings_on":
            self.enable_audio()
            #self.sound_volume.set_disabled(False)
        else:
            self.disable_audio()
            #self.sound_volume.set_disabled(True)
        
    def enable_audio(self):
        audio_service = AudioService()
        if not audio_service.is_audio_enabled():
            logger.debug("Enable audio..")
            audio_service.enable_audio()     
        
    def disable_audio(self):
        audio_service = AudioService()
        if audio_service.is_audio_enabled():
            logger.debug("Disable audio..")
            audio_service.disable_audio()

    def enable_airplane_mode(self):
        network_service = self._get_network_service()
        if not network_service.is_airplane_mode():
            logger.debug("Enable airplane mode..")
            network_service.enable_airplane_mode()

    def disable_airplane_mode(self):
        network_service = self._get_network_service()
        if network_service.is_airplane_mode():
            logger.debug("Disable airplane mode..")
            network_service.disable_airplane_mode()


class SettingsNetwork(SettingsBase):
    """Network related settings."""

    line_spacer=4 
    row_height=30 
    num_rows=10
    padding_x = 8

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self._get_network_service().add_callback("on_connection_info", 
                self.update_connection_info)
        self._get_network_service().add_callback("on_wifi_scan_results", 
                self.update_wifi_list)
        self.start_position = start_divider
        self.create_divider(0, self.start_position, "Network")
        is_on = self._get_network_service().is_wifi_enabled()
        self.add_radio_choice("Wi-Fi", "wifi_settings", is_on, 
                delegate.on_wifi_settings)
        description_label = Label("To join a network, click on the desired"
                " network in the list, then enter its password",
                font_size=entry_font_size)
        description_label.transparent = False
        doc_page.gui_page().add(description_label, margin_left,
                self.last_position + line_spacer)
        network_name_label = Label("Network Name",
                font_size=entry_font_size)
        network_name_label.transparent = False
        doc_page.gui_page().add(network_name_label, margin_left,
                description_label.y + \
                description_label.h + 10)
        self.main_network_panel = Panel(794, 
                (self.row_height + self.line_spacer)*self.num_rows + \
                self.padding_x*2, widget_id="settings_main_network_panel")
        network_list_bg = ImageCache.instance().get_image("network_list_bg.pgm")
        self.main_network_panel.set_background(network_list_bg)
        self.doc_page.gui_page().add(self.main_network_panel, 15, 
                network_name_label.y+network_name_label.h+4)
        add_network = ImageButton("settings_network_add", 36, 36, 
                "DEFAULT", "plus.pgm")
        add_network.add_callback(delegate.on_open_add_network, 'on_button_press')
        doc_page.gui_page().add(add_network, margin_left + 694,
                description_label.y + \
                description_label.h + 2)
        refresh_network = ImageButton("settings_network_refresh", 36, 36, 
                "DEFAULT", "refresh.pgm")
        refresh_network.add_callback(delegate.on_refresh_network,
                'on_button_press')
        doc_page.gui_page().add(refresh_network,  margin_left + 730,
                description_label.y + \
                description_label.h + 2)
        self.last_position = self.main_network_panel.y + self.main_network_panel.h
        if self.is_3g_capable():
            self.create_divider(0, self.last_position + section_margin, "3G Radio")
            three_g = "Enabled" \
                    if self._get_network_service().is_3g_enabled() \
                    else "Disabled"
            self.three_g_status = self.add_name_value(margin_left, 
                    self.last_position + margin_divider,
                    "Status:", three_g, widget_id="three_g_status")
            three_g_roaming = "Enabled" \
                    if self._get_network_service().is_3g_roaming() \
                    else "Disabled"
            self.three_g_roaming = self.add_name_value(margin_left, 
                    self.last_position + line_spacer, "Roaming:", 
                    three_g_roaming, widget_id="three_g_roaming_status")
        self.create_divider(0, self.last_position + section_margin,
                "Connection")
        self.ip_info = self.add_name_value(margin_left, 
                self.last_position + margin_divider, "Address:", "", 
                widget_id="ip_info")
        self.ssid_info = self.add_name_value(margin_left, self.last_position + 
                line_spacer, "Network:", "", widget_id="ssid_info")
        self.add_footer_navigation(margin_left, SCREEN_SIZE[1] - 80, 
                (("back","general"), ("home","general"), ("forward","user")))

    def refresh(self):
        with _refresh_lock:
            self.update_3g_info()
            if self._get_network_service().is_wifi_enabled():
                self._get_network_service().scan_wifi()
            self._get_network_service().get_conn_info()

    def update_3g_info(self):
        three_g = "Enabled" \
                if self._get_network_service().is_3g_enabled() \
                else "Disabled"
        three_g_roaming = "Enabled" \
                if self._get_network_service().is_3g_roaming() \
                else "Disabled"
        self.update_value(self.three_g_status, three_g)
        self.update_value(self.three_g_roaming, three_g_roaming)
                
    def on_add(self, *args):
        logger.debug("Adding network entry..")

    def on_delete(self, *args):
        logger.debug("Deleting network entry..")

    def on_refresh(self, *args):
        logger.debug("Refreshing network list..")
        if self._get_network_service().is_wifi_enabled():
            self.set_scan_state("Scanning..")
            if "PONG" not in self._ping():
                self._get_network_service().want_network(1)
            self._get_network_service().scan_wifi()
        else:
            self.show_message("Please enable wireless networking to search for "
                    "available access points.")

    def update_connection_info(self, *args):
        try:
            logger.debug("Callling update_connection_info")
            signal, conn_type, ssid_info, address = args[0:4]            
            with _refresh_lock:
                if address == 'Roam':
                    conn_type = '3GR'
                logger.debug("Updating connection info: %r %r %r %r", 
                        signal, conn_type, ssid_info, address)
                self.update_value(self.ip_info, address)
                if conn_type in ['3g', '3GR']:
                    ssid_info = "3G"
                self.update_value(self.ssid_info, ssid_info)
        except Exception as e:
            logger.error("Connection info error: args(%r) exception(%r)", args, e)

    def update_wifi_list(self, *args):
        try:
            with _refresh_lock:
                self.clear_net_list()
                if len(args) > 0:    
                    self.draw_net_list(args)
                else:
                    self.set_scan_state("No wireless networks found.")
        except Exception as e:
            logger.error("Scan wifi error: args(%r) exception(%r)", args, e)

    def set_scan_state(self, state):
        self.clear_net_list()
        if self.main_network_panel:
            logger.debug("Scan state: %r", state)
            state_label = Label(state, 700, 30, 16)
            self.main_network_panel.add(state_label, 46, 12)
            self.main_network_panel.update(False)
            self.doc_page.gui_page().process_changes()

    # ##################################################
    # Clear the network list box
    def clear_net_list(self):
        logger.debug("Clearing net list")
        if self.main_network_panel is not None:
            self.clean_widgets(self.main_network_panel)
            offset = 5
            top_left = (self.main_network_panel.box.top_left()[0]+offset, 
                    self.main_network_panel.box.top_left()[1]+offset)
            bottom_right = (self.main_network_panel.box.bottom_right()[0]-offset,
                    self.main_network_panel.box.bottom_right()[1]-offset)
            self.doc_page.gui_page().clear_area(top_left, bottom_right)

    # ##################################################
    # Draw the network list box entries
    def draw_net_list(self, available_networks):
        # Code to build network list
        logger.debug("Drawing net list")         
        if self.main_network_panel:
            count = 0
            padding_x, padding_y = (8,8)
            y = padding_y
            known_list = []
            for item in available_networks:
                # TODO: Support more than 8 entries when we have a listbox widget.
                entries = item.split('\t')
                if count > self.num_rows - 1:
                    break
                w_id = "ssid_%s" % entries[0]
                if w_id not in known_list and entries[0].strip():
                    net_row = NetworkItemPanel(
                            self.main_network_panel.w-padding_x-padding_y, 
                            self.row_height, w_id)
                    net_row.create_gui(self)
                    net_row.set_from_data(entries)
                    net_row.add_listener(self.delegate)
                    self.main_network_panel.add(net_row, padding_x, y)
                    known_list.append(w_id)
                    y = y + self.row_height + self.line_spacer
                    count = count + 1
            known_list = []
            self.main_network_panel.update(False)
            self.doc_page.gui_page().process_changes()

    def on_select(self, *args):
        logger.debug("Selected: %r", args[0])
        selected_panel = args[0]
        network_name = selected_panel.name.get_text()
        if selected_panel.known:
            self.network_action_dialog = NetworkActionDialog(568, 500, 
                    network_name, parent_window=self.gui())
            self.network_action_dialog.add_callback(self.on_connect_network, 
                    "on_connect_network")
            self.network_action_dialog.add_callback(self.on_forget_network, 
                    "on_forget_network")
            self.network_action_dialog.is_current_connection = selected_panel.connected
            self.network_action_dialog.show_overlay()
        else:
            logger.debug("TODO: Should pop up a password input dialog.")

    def on_connect_network(self, *args):
        network_name = args[0]
        logger.debug("Connecting to network: %r", network_name)
        if not self.network_action.connect_network(network_name):
            self.show_message("Connect request failed.")
        else:
            self._clear_and_transition_wifi()
        
    def on_forget_network(self, *args):
        network_name = args[0]
        logger.debug("Forgetting network: %r", network_name)
        if not self.network_action.forget_network(network_name):
            self.show_message("Forget request failed.")
        else:
            self._clear_and_transition_wifi()            

    def _clear_and_transition_wifi(self):
        logger.debug("Clear and transition settings wifi")
        self._get_network_service().wifi_reconfigure()
        self._get_network_service().want_network(1)
        self._get_network_service().get_conn_info()

    def on_wifi_settings(self, *args):
        wifi_settings_group = args[0]
        logger.debug("Selected: %r", wifi_settings_group) 
        name = wifi_settings_group.get_selection().name
        if name == "wifi_settings_on":
            self.enable_wifi()
        else:
            self.disable_wifi()
            self.clear_net_list()
        
    def enable_wifi(self):
        network_service = self._get_network_service()
        if not network_service.is_wifi_enabled():
            logger.debug("Enable wifi..")
            network_service.enable_wifi()
            network_service.want_network(1)
        
    def disable_wifi(self):
        network_service = self._get_network_service()
        if network_service.is_wifi_enabled():
            logger.debug("Disable wifi..")
            network_service.disable_wifi()

    def on_page_exit(self):
        SettingsBase.on_page_exit(self)
        try:
            self._get_network_service().del_callback("on_connection_info", 
                    self.update_connection_info)
            self._get_network_service().del_callback("on_wifi_scan_results", 
                    self.update_wifi_list)
        except Exception, e:
            logger.debug("Error deleting network service callbacks: %r", e)
            pass


class SettingsAddNetwork(SettingsBase):

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.create_divider(0, start_divider,
                "Add Network")
        warning_label = Label("Do not attempt to connect to wireless access points"
                " requiring a browser.", font_size=entry_font_size)
        doc_page.gui_page().add(warning_label, margin_left,
                self.last_position + margin_divider)
        self.last_position = warning_label.y + warning_label.h
        ssid_label = Label("SSID", font_size=entry_font_size)
        ssid_label.transparent = True
        doc_page.gui_page().add(ssid_label, margin_left,
                self.last_position + 10)
        self.ssid_input = InputText('', 300, font_size=input_font_size)
        doc_page.gui_page().add(self.ssid_input, margin_left +
                ssid_label.w + 40, ssid_label.y)
        self.last_position = self.ssid_input.y + self.ssid_input.h
        key_label = Label("Key", font_size=entry_font_size)
        key_label.transparent = True
        doc_page.gui_page().add(key_label, margin_left,
                self.last_position + 4)
        self.key_input = Password('', 300, font_size=input_font_size)
        doc_page.gui_page().add(self.key_input, self.ssid_input.x, key_label.y)
        self.last_position = self.key_input.y + self.key_input.h
        # TODO: change to dropdown
        #{"Open":"Open", "Wired Equivalent Privacy":"WEP", 
        #        "Wireless Protected Access I/II":"WPA"}
#        choice_panel = self.create_choice_panel("wifi_type", 
#                ["Open", "Wired Equivalent Privacy", "Wireless Protected Access"], "Open")
#        self.doc_page.gui_page().add(choice_panel, margin_left, 
#                self.last_position + line_spacer)
#        self.wifi_type_group = Grouping.with_id("wifi_type")
#        self.wifi_type_group.add_callback(delegate.on_wifi_type, 
#                'on_group_selection')
#        self.last_position = choice_panel.h + choice_panel.y
        security_label = Label("Security", font_size=entry_font_size)
        security_label.transparent = True
        doc_page.gui_page().add(security_label, margin_left, 
                self.last_position + 4)
        security_types = {"Open":"Open", "Wired Equivalent Privacy":"WEP", 
                "Wireless Protected Access I/II":"WPA"}
        self.security_choice = Dropdown(300, 40, security_types)
        self.doc_page.gui_page().add(self.security_choice, self.key_input.x, 
                self.last_position + 4)
        self.last_position = self.security_choice.h + self.security_choice.y
        self.hidden_network = Checkbox(26, 26)
        doc_page.gui_page().add(self.hidden_network, ssid_label.x, 
                self.last_position + 20)
        self.hidden_label = Label("Hidden", font_size=entry_font_size)
        doc_page.gui_page().add(self.hidden_label, ssid_label.x + \
                self.hidden_network.w + 10, 
                self.last_position + 20)
        self.last_position = self.hidden_label.y + self.hidden_label.h
        add_network = Button('Add', 129, 48)
        add_network.add_callback(delegate.on_add_network, 'on_button_press')
        doc_page.gui_page().add(add_network, self.key_input.x +
                self.key_input.w - add_network.w,
                self.last_position + line_spacer)
        cancel_network = Button('Cancel', 129, 48)
        cancel_network.add_callback(delegate.on_cancel_add_network, 
                'on_button_press')
        doc_page.gui_page().add(cancel_network, self.key_input.x +
                self.key_input.w - add_network.w - cancel_network.w - 10,
                self.last_position + line_spacer)
        self.last_position = cancel_network.y + cancel_network.h

    def refresh(self):
        pass

    def on_add(self):
        logger.debug("Adding network entry..")
        if hasattr(self, 'ssid_input') and \
                hasattr(self, 'key_input'):
            ssid = self.ssid_input.value
            key = self.key_input.value
            key_type = self.security_choice.get_selection().value if self.security_choice.get_selection() is not None else "" 
            logger.debug("Selected key type: %r", key_type)
            hidden = False
            added = False
            if self.hidden_network.is_checked():
                hidden = True
            if key_type == "Open":
                logger.debug("Adding open network: %r", ssid)
                added = self.network_action.add_open_wifi(ssid, hidden)
            else:
                logger.debug("Adding secured network: %r", ssid)
                added = self.network_action.add_secured_wifi(ssid, key, 
                        key_type, hidden)
            if added:
                self._clear_and_transition_wifi()
            else:
                self.show_message("Failed to add wireless network.")

    def _clear_and_transition_wifi(self):
        logger.debug("Clear and transition settings wifi")
        self._get_network_service().wifi_reconfigure()
        self._get_network_service().want_network(1)        
        self.ssid_input.value=""
        self.ssid_input.update(False)
        self.key_input.value=""
        self.key_input.update(False)
        self.security_choice.set_selection(None)
        self.delegate.go_to_page('network')


class SettingsUser(SettingsBase):
    """User related settings."""

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.create_divider(0, start_divider, "Sync")
        sync_info = self.get_sync()
        if sync_info and 'ssh_host' in sync_info:
            self.add_name_value(margin_left, self.last_position + margin_divider,
                    "Server:", sync_info.get('ssh_host', ''))
        else:
            self.add_name_value(margin_left, self.last_position + \
                    margin_divider, "Server:", "")
        self.create_divider(0, self.last_position + section_margin, "User")
        session_info = self.get_session()
        if session_info:
            self.add_name_value(margin_left, self.last_position + margin_divider, "ID:",
                    session_info.get('user', ''))
            self.add_name_value(margin_left, self.last_position +
                    line_spacer, "Name:", session_info.get('name', ''))
            self.add_name_value(margin_left, self.last_position +
                    line_spacer, "Email:", session_info.get('email', ''))
            self.add_name_value(margin_left, self.last_position +
                    line_spacer, "Account:",
                    session_info.get('account', ''))
        else:
            self.add_name_value(margin_left, self.last_position, "ID:", "")
        self.add_footer_navigation(margin_left, SCREEN_SIZE[1] - 80, 
                (("back","network"), ("home","general"), ("forward","tools")))

    def refresh(self):
        pass


class SettingsTools(SettingsBase):
    """Various tablet tools."""

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.last_position = start_divider
        self.create_divider(0, self.last_position, "Pen Calibration")
        calibrate_label = Label("During calibration, hold the pen in your "
                "natural writing position.", font_size=entry_font_size)
        calibrate_label.transparent = False
        doc_page.gui_page().add(calibrate_label, margin_left,
                self.last_position + margin_divider)
        self.calibrate = Button('Calibrate', 129, 48)
        self.calibrate.add_callback(delegate.on_calibrate, 'on_button_press')
        doc_page.gui_page().add(self.calibrate, margin_left, 
                calibrate_label.y+calibrate_label.h+line_spacer)
        self.last_position = self.calibrate.y + self.calibrate.h
        self.add_footer_navigation(margin_left, SCREEN_SIZE[1] - 80, 
                (("back","user"), ("home","general"), ("forward","software_update")))

    def refresh(self):
        pass

    def on_calibrate(self, *args):
        logger.debug("Starting pen calibration..")
        try:
            self.calibrate.set_disabled(True)
            command_line = "/usr/local/bin/provision.py -c"
            ew_exec.run_command(command_line)
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        
        
class SettingsSoftwareUpdate(SettingsBase):

    def create_gui(self, delegate, doc_page):
        self.has_upgrade_section = False
        self.create_title(DOC_TITLE)
        self.software_update = SoftwareUpdate(self)
        self.create_divider(0, start_divider, "Software Update")
        build_id = self.software_update.get_current_version()
        build_label = Label("Current Version:", font_size=entry_font_size)
        build_label.transparent = False
        build_value = Label(build_id,
                font_size=entry_font_size)
        build_value.transparent = False
        self.doc_page.gui_page().add(build_label, margin_left,
                self.last_position + line_spacer)
        self.doc_page.gui_page().add(build_value, margin_left + 
                build_label.w + 24, self.last_position + line_spacer)
        self.last_position = build_label.y + build_label.h + 20
        self.create_divider(0, self.last_position + section_margin, "Updates")
        update_status = None
        if self.software_update.has_update():
            update_status = self.software_update.get_update_status()
            self.build_name = self.software_update.get_available_version()
            if self.build_name is not None:
                update_string = self.build_name.replace(".tar", "").replace("_RK1", "")
                update_label = Label("Software update is available.", 400, 25,
                        font_size=entry_font_size)
                update_label.transparent = False
                self.doc_page.gui_page().add(update_label, margin_left, 
                        self.last_position + margin_divider)
                self.last_position = update_label.y + update_label.h
                update_state_str = "%s:" % update_status
                self.new_build_label = Label(update_state_str, 165, 25,
                        font_size=entry_font_size)
                self.new_build_label.transparent = False
                new_build_value = Label(update_string, 500, 25,
                        font_size=entry_font_size)
                new_build_value.transparent = False
                self.doc_page.gui_page().add(self.new_build_label, margin_left,
                        self.last_position + line_spacer)
                self.doc_page.gui_page().add(new_build_value, margin_left + 
                        self.new_build_label.w, self.last_position + line_spacer)
                self.last_position = self.new_build_label.y + \
                        self.new_build_label.h
                self.progress_bar = ProgressBar(new_build_value.w, 30)
                doc_page.gui_page().add(self.progress_bar, 
                        new_build_value.x, self.last_position + line_spacer)
                self.last_position = self.progress_bar.y + self.progress_bar.h
                self.create_divider(0, self.last_position + \
                        section_margin, "Upgrade")
                warning_label_1 = Label("WARNING: The update process may "
                        "take a while. Please do not power down the", 
                        font_size=entry_font_size)
                warning_label_1.transparent = False
                self.doc_page.gui_page().add(warning_label_1, margin_left,
                        self.last_position + line_spacer)
                self.last_position = warning_label_1.y + warning_label_1.h
                warning_label_2 = Label("Ricoh eQuill during this operation.", 
                        font_size=entry_font_size)
                warning_label_2.transparent = False
                self.doc_page.gui_page().add(warning_label_2, margin_left,
                        self.last_position + line_spacer/2)
                self.last_position = warning_label_2.y + warning_label_2.h
                self.install_update_button = Button('Upgrade', 129, 48)
                self.install_update_button.add_callback(
                        self.delegate.on_install_update, 'on_button_press')
                self.doc_page.gui_page().add(self.install_update_button, 
                        SCREEN_SIZE[0]-self.install_update_button.w-margin_left, 
                        self.last_position + line_spacer)
                self.last_position = self.install_update_button.y + \
                        self.install_update_button.h
        else:
            up_to_date_label = Label("Your Ricoh eQuill software is up to date.", 400, 25,
                    font_size=entry_font_size)
            up_to_date_label.transparent = False
            self.doc_page.gui_page().add(up_to_date_label, margin_left, 
                    self.last_position + margin_divider)
            self.last_position = up_to_date_label.y + up_to_date_label.h
        if update_status == SoftwareUpdate.DOWNLOADING:
            self.progress_bar.set_invisible(False)
            self.install_update_button.set_disabled(True)
        elif update_status == SoftwareUpdate.DOWNLOADED:
            self.progress_bar.set_invisible(True)
            self.install_update_button.set_disabled(False)
        elif update_status == SoftwareUpdate.INCOMPLETE:
            self.progress_bar.set_invisible(True)
            self.install_update_button.set_disabled(True)
        self.software_update.set_update_callback(self.update_progress)
        self.add_footer_navigation(margin_left, SCREEN_SIZE[1] - 80, 
                (("back","tools"), ("home","general"), ("forward","about")))

    def refresh(self):
        pass

    def update_progress(self, *args):
        with _refresh_lock:
            logger.verbose("update_progress: %r", args)
            if len(args) == 2:
                state, rsync_info = args
                update_state_str = "%s:" % state
                self.new_build_label.set_text(update_state_str)
                if state == SoftwareUpdate.DOWNLOADING:
                    self.progress_bar.set_invisible(False)
                    self.install_update_button.set_disabled(True)
                    if rsync_info:
                        percentage = int(rsync_info.replace('%', ''))*2
                        if percentage is not None:
                            self.progress_bar.set_progress(percentage)
                elif state == SoftwareUpdate.DOWNLOADED:
                    self.progress_bar.set_invisible(True)
                    self.install_update_button.set_disabled(False)
                    self.doc_page.display(True)
                elif state == SoftwareUpdate.INCOMPLETE:
                    self.progress_bar.set_invisible(True)
                    self.install_update_button.set_disabled(True)
                    self.doc_page.display(True)
            else:
                logger.warning("Got the wrong number of arguments: %r", args)   
            
    def on_install_update(self, *args):
        logger.debug("Installing software update..")
        self.progress_bar.set_invisible(True)
        self.install_update_button.set_disabled(True)
        self.software_update.update()

    def on_page_exit(self):
        SettingsBase.on_page_exit(self)
        self.software_update.clean_up()


class SettingsAbout(SettingsBase):

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.create_divider(0, start_divider, "About")
        self.add_name_value(margin_left, self.last_position + margin_divider, 
                "Serial Number:", self.serial_number)
        self.add_name_value(margin_left, self.last_position + \
                line_spacer, "Software Version:", self.software_version)
        self.add_name_value(margin_left, self.last_position + \
                line_spacer, "MAC:", self._get_mac_address())
        self.add_name_value(margin_left, self.last_position + \
                line_spacer, "MSP Version:", self._get_msp_info())
        if self.is_3g_capable():
#            self._get_network_service().add_callback("on_3g_conf", 
#                    self.update_3g_info)
            self.create_divider(0, self.last_position + section_margin, "3G")
            meid, vmdn, vmin, nai = self._get_three_g_settings()
            self.add_name_value(margin_left, 
                self.last_position + margin_divider, 
                "MEID:", meid, widget_id="about_meid")
            self.add_name_value(margin_left, self.last_position + \
                line_spacer, "Mobile Director:", vmdn, widget_id="about_mdn")
            self.add_name_value(margin_left, self.last_position + \
                line_spacer, "Mobile System ID:", vmin, widget_id="about_msid")
            self.add_name_value(margin_left, self.last_position + \
                line_spacer, "NAI:", nai, widget_id="about_nai")            

        self.create_divider(0, self.last_position + section_margin, "Legal")
        icon_position = self.last_position+margin_divider
        license_button = ImageButton("settings_about_license", 80, 100,
                "DEFAULT", "icon_license.pgm")
        license_button.add_callback(delegate.on_open_license,
                'on_button_press')
        doc_page.gui_page().add(license_button, margin_left + \
                margin_left, icon_position)
        regulatory_button = ImageButton("settings_about_regulatory", 80, 100,
                "DEFAULT", "icon_regulatory.pgm")
        regulatory_button.add_callback(delegate.on_open_regulatory,
                'on_button_press')
        doc_page.gui_page().add(regulatory_button, 
                license_button.x + license_button.w + \
                (margin_left * 2), icon_position)
        legal_button = ImageButton("settings_about_legal", 80, 100,
                "DEFAULT", "icon_legal.pgm")
        legal_button.add_callback(delegate.on_open_legal,
                'on_button_press')
        doc_page.gui_page().add(legal_button, 
                regulatory_button.x + regulatory_button.w + \
                (margin_left * 2), icon_position)
        self.last_position = license_button.y + license_button.h  
        self.add_footer_navigation(margin_left, SCREEN_SIZE[1] - 80, 
                (("back","software_update"), ("home","general")))

    def _get_three_g_settings(self):
        three_g_info = self.get_3g_info()
        meid = vmdn = vmin = nai = ""
        if three_g_info:
            meid = three_g_info.get("meid", "")
            meid = meid.replace("0x", "").upper()
            vmdn = three_g_info.get("vmdn", "")
            vmin = three_g_info.get("vmin", "")
            profile = three_g_info.get("profile", "")
            nai_items = profile.split(",")
            if len(nai_items) > 5:
                nai = nai_items[5].replace("\"", "")
        return meid, vmdn, vmin, nai

#    def update_3g_info(self, *args):
#        try:
#            with _refresh_lock:
#                logger.debug("Setting 3g info on settings page %r", args)
#                meid, nai, mdn, msid = args
#                meid = meid.replace("0x", "").upper()
#                nai_items = nai.split(",")
#                logger.debug("nai_items %r len(%r)", nai_items, len(nai_items))
#                self.update_value("about_meid", meid)
#                self.update_value("about_mdn", mdn)
#                self.update_value("about_msid", msid)
#                if len(nai_items) > 5:
#                    self.update_value("about_nai", nai_items[5].replace("\"", ""))
#        except Exception as e:
#            logger.error("Update 3G info error: args(%r) exception(%r)", args, e)

    def _get_disk_info(self):
        disk_info = ""
        try:
            command_line = "fdisk -l /dev/mmcblk0"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                line = line.strip()
                if line[0:17] == "Disk /dev/mmcblk0":
                    disk_info = line.split(':')[1].split(',')[0].strip()
                    break
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return disk_info
    
    def _get_msp_info(self):
        msp_info = ""
        try:
            command_line = "/usr/local/bin/msp430_swversion.sh"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                line = line.strip()
                msp_info = line.split('=')[1]
                break
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return msp_info.strip()
    
    def _get_data_info(self):
        data_info = []
        try:
            command_line = "df -h /data/inbox/"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                line = line.strip()
                if line[0:5] == "/dev/":
                    data_info = line.split()
                    break
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return data_info

    def _get_mem_info(self):
        mem_info = {}
        try:
            command_line = "cat /proc/meminfo"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                line = line.strip()
                if line:
                    mem_tuple = line.split(':')
                    mem_info[mem_tuple[0].strip()] = mem_tuple[1].strip()
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return mem_info

    def _get_cpu_info(self):
        cpu_info = {}
        try:
            command_line = "cat /proc/cpuinfo"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                line = line.strip()
                if line:
                    cpu_tuple = line.split(':')
                    cpu_info[cpu_tuple[0].strip()] = cpu_tuple[1].strip()
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return cpu_info

    def _get_mac_address(self):
        mac_address = ""
        try:
            command_line = "cat /nvram0/macaddress.txt"
            for line in ew_exec.command_output(command_line, close_fds=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                if line:
                    mac_address = line.strip()
        except subprocess.CalledProcessError, e:
            logger.exception(e)
        return mac_address

#    def refresh(self):
#        if self.is_3g_capable():
#            self._get_network_service().get_3g_conf()

    def on_open_license(self, *args):
        logger.debug("Opening license doc..")
        self.doc_page._document._runner.legal_document("License")

    def on_open_regulatory(self, *args):
        logger.debug("Opening regulatory doc..")
        self.doc_page._document._runner.legal_document("Regulatory")
        
    def on_open_legal(self, *args):
        logger.debug("Opening legal doc..")
        self.doc_page._document._runner.legal_document("Legal")
                
#    def on_page_exit(self):
#        if self.is_3g_capable():
#            try:
#                self._get_network_service().del_callback("on_3g_conf", 
#                        self.update_3g_info)
#            except Exception, e:
#                logger.warning("Error deleting network service %r", e)
