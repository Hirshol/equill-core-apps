#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
import threading, subprocess, shlex
from ew.util import ew_logging, ew_exec
from ew.internal_decs.scan_wifi_dialog import ScanWifiDialog
from ew.internal_decs.network_action_dialog import NetworkActionDialog
from sdk.widgets.label import Label
from sdk.widgets.button import Button
from sdk.widgets.checkbox import Checkbox
from sdk.widgets.panel import Panel
from sdk.widgets.dropdown import Dropdown
from sdk.widgets.image_button import ImageButton
from sdk.widgets.password import Password
from sdk.widgets.image_label import ImageLabel
from sdk.widget_cache import ImageCache
from sdk.overlay_switch import InputText
from sdk.display_constants import SCREEN_SIZE
from ew.internal_decs.settings_class import SettingsTools, SettingsBase

logger = ew_logging.getLogger('ew.internal_decs.provision_class')
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
input_font_size = 16
input_start_x = 155
        
_refresh_lock = threading.RLock()
DOC_TITLE = "Provision Ricoh eQuill"


class ProvisionMain(SettingsBase):

    def create_title(self, title):
        pass
    
    def create_gui(self, delegate, doc_page):
        screen_w, screen_h = SCREEN_SIZE
        self.last_position = 350
        provision_tool_message = Label("This Ricoh eQuill has not been set up.", 
                font_size=title_font_size)
        doc_page.gui_page().add(provision_tool_message,
                screen_w/2-provision_tool_message.w/2, self.last_position)
        self.last_position = provision_tool_message.y + provision_tool_message.h
        tablet_image = ImageLabel("tablet_image", 71, 88, "tablet_icon.pgm")
        doc_page.gui_page().add(tablet_image, screen_w/2-tablet_image.w/2, 
                self.last_position + 50)
        setup_button = Button('Setup', 129, 48)
        setup_button.add_callback(delegate.on_setup_tablet, 'on_button_press')
        self.last_position = tablet_image.y + tablet_image.h
        doc_page.gui_page().add(setup_button, screen_w/2-setup_button.w/2, 
                self.last_position + 50)
        self.last_position = setup_button.h + setup_button.y

    def on_page_exit(self):
        pass
    
    
class ProvisionTool(SettingsBase):
    """Provision main page."""

    def create_title(self, title):
        title_label = Label(title, font_size=title_font_size)
        title_label.transparent = True
        self.doc_page.gui_page().add(title_label,
                SCREEN_SIZE[0]/2-title_label.w/2, 20)
        self.last_position = self._get_last_position(title_label)
        return title_label

    def create_network_gui(self):
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
                    logger.error('%r is not in range %r', 
                            num, range(*self._range))
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
        self._wifi = NumberedImageLabel('wifi', 'wifi', (0,4))
        self._wifi.set_image_number(3)
        self._radio = NumberedImageLabel('radio', 'radio', (0,6))
        self._roaming_radio = NumberedImageLabel('radio_r', 'radio_r', (1,6))
        self._no_connection = ImageLabel("no_connection", 63, 63, 
                "no_connection.pgm")
        self._network_widgets = {'3GR' : self._roaming_radio, 
                '3g' : self._radio, 'wifi' : self._wifi, 
                'None': self._no_connection} 

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.create_network_gui()
        self.create_divider(0, self.last_position, "Connection")
        self.connection_panel = Panel(250, 150)
        _gray_bg = ImageCache.get_image("connection_bg.pgm")
        self.connection_panel.set_background(_gray_bg)
        self.label_current = Label("Current Address", font_size=entry_font_size)
        self.label_current.transparent = True
        self.connection_panel.add(self.label_current, 20, 20)
        self._network_type = self._no_connection
        self.connection_x = self.label_current.x
        self.connection_y = self.label_current.y + \
                self.label_current.h + line_spacer
        self.connection_panel.add(self._network_type, 
                self.connection_x, self.connection_y)
        self.address_label = Label("", 140, 25, font_size=entry_font_size)
        self.address_label.transparent = False
        self.connection_panel.add(self.address_label, 
                self._network_type.x + 
                self._network_type.w + 10,
                self._network_type.y)
        self.curr_ssid = Label("", 140, 25, font_size=entry_font_size)
        self.curr_ssid.transparent = False
        self.connection_panel.add(self.curr_ssid, 
                self._network_type.x + 
                self._network_type.w + 10,
                self.address_label.h + self.address_label.y + 5)
        msg = "Configure your internet connection. (%s)" % \
                self._get_mac_address()
        connection_label = Label(msg, font_size=entry_font_size)
        connection_label.transparent = False
        doc_page.gui_page().add(connection_label, margin_left,
                self.last_position + margin_divider)
        self.last_position = connection_label.y + connection_label.h
        doc_page.gui_page().add(self.connection_panel, 
                SCREEN_SIZE[0] - self.connection_panel.w - 40, 
                self.last_position + margin_divider)
        ssid_label = Label("SSID",
                font_size=entry_font_size)
        ssid_label.transparent = False
        doc_page.gui_page().add(ssid_label, 
                margin_left, self.last_position + 12)
        self.ssid_input = InputText('', 300,
                font_size=input_font_size)
        doc_page.gui_page().add(self.ssid_input,
                ssid_label.x + ssid_label.w + 50, 
                self.last_position+line_spacer)
        password_label = Label("Password", font_size=entry_font_size)
        password_label.transparent = False
        doc_page.gui_page().add(password_label, 
                ssid_label.x,
                ssid_label.y + ssid_label.h + 20)
        self.password_input = Password('', 300, font_size=input_font_size)
        doc_page.gui_page().add(self.password_input, self.ssid_input.x,
                self.ssid_input.y + self.ssid_input.h + 4)
        self.last_position = self.password_input.y + self.password_input.h
        # TODO: change to dropdown
        security_label = Label("Security", font_size=entry_font_size)
        security_label.transparent = True
        doc_page.gui_page().add(security_label, margin_left, 
                password_label.y + password_label.h + 20)
        security_types = {"Open":"Open", "Wired Equivalent Privacy":"WEP", 
                "Wireless Protected Access I/II":"WPA"}
        self.security_choice = Dropdown(300, 40, security_types)
        self.doc_page.gui_page().add(self.security_choice, self.password_input.x, 
                self.last_position + 4)
        self.last_position = self.security_choice.h + self.security_choice.y
#        self.doc_page.gui_page().add(choice_panel, self.password_input.x, 
#                self.last_position + line_spacer)
#        self.wifi_type_group = Grouping.with_id("wifi_type")
#        self.last_position = choice_panel.h + choice_panel.y
        self.hidden_network = Checkbox(26, 26)
        doc_page.gui_page().add(self.hidden_network, self.password_input.x, 
                self.last_position + 20)
        self.hidden_label = Label("Hidden", font_size=entry_font_size)
        doc_page.gui_page().add(self.hidden_label, self.password_input.x + \
                self.hidden_network.w + 10, 
                self.last_position + 20)
        connect = Button('Connect', 129, 48)
        connect.add_callback(delegate.on_connect, 'on_button_press')
        doc_page.gui_page().add(connect, 
                self.password_input.x + self.password_input.w - connect.w,
                self.last_position + 10)
        self.search_wifi = ImageButton("ssid_search", 36, 36,
                "default", "ssid_ssidsearch.pgm")
        self.search_wifi.add_callback(delegate.on_search_wifi, 'on_button_press')
        doc_page.gui_page().add(self.search_wifi, 
                self.ssid_input.x + self.ssid_input.w + 10, self.ssid_input.y)
        self.search_wifi.set_disabled(False)
        self.last_position = connect.y + connect.h
        self.create_divider(0, self.last_position + section_margin, "Provision")    
        description_label = Label("To provision this Ricoh eQuill, fill out the "
                "fields below with the information provided",
                font_size=entry_font_size)
        description_label.transparent = False
        doc_page.gui_page().add(description_label, margin_left,
                self.last_position + margin_divider)
        description_label1 = Label("to you by your service provider.",
                font_size=entry_font_size)
        description_label1.transparent = False
        doc_page.gui_page().add(description_label1, margin_left,
                description_label.y + \
                description_label.h)
        self.last_position = description_label1.y + description_label1.h
        inbox_hostname_label = Label("Inbox Hostname",
                font_size=entry_font_size)
        inbox_hostname_label.transparent = False
        doc_page.gui_page().add(inbox_hostname_label, margin_left,
                self.last_position + line_spacer)
        self.inbox_hostname_input = InputText('', 300,
                font_size=input_font_size)
        doc_page.gui_page().add(self.inbox_hostname_input,
                margin_left + input_start_x, self.last_position + line_spacer)
        account_label = Label("Account", font_size=entry_font_size)
        account_label.transparent = False
        doc_page.gui_page().add(account_label, margin_left + 72,
                self.inbox_hostname_input.y + self.inbox_hostname_input.h + 4)
        self.account_input = InputText('', 300, font_size=input_font_size)
        doc_page.gui_page().add(self.account_input, margin_left + input_start_x,
                self.inbox_hostname_input.y + self.inbox_hostname_input.h + 4)
        self.last_position = self.account_input.y + self.account_input.h
        self.provision = Button('Provision', 129, 48)
        self.provision.add_callback(delegate.on_provision, 'on_button_press')
        doc_page.gui_page().add(self.provision, 376,
                self.last_position + 8)
        logger.debug("Register on_connection_info")
        self._get_network_service().on_connection_info(
                self.handle_connection_info)

    def refresh(self):
        if "PONG" not in self._ping():
            self._get_network_service().enable_wifi()
            self._get_network_service().want_network(1)
        self.network_action.keep_alive(True)
        self._get_network_service().get_conn_info()
    
    def handle_connection_info(self, signal, conn_type, ssid_info, 
                address, *args):
        signal = min(3, signal // 25)
        if address == 'Roam':
            conn_type = '3GR'
        logger.debug('connection info: %s, %s, %s, %s', 
                signal, conn_type, ssid_info, address)
        try:
            if conn_type in ('wifi', '3g', '3GR'):
                self.address_label.set_text(address)
                if conn_type != 'wifi':
                    ssid_info = "3G"
                self.curr_ssid.set_text(ssid_info)
                self.set_network_info(conn_type, signal)
            else:
                self.address_label.set_text("")
                self.curr_ssid.set_text("")
                self.set_network_info(None, None)
        except Exception, e:
            logger.debug("Exception: (%r)", e)

    def set_network_level(self, level):
        """level is 0..3 inclusive for wifi and 0..5 inclusive for 
        3G."""
        self._network_type.set_image_number(level)
        self._network_type.update(True)

    def set_network_info(self, network_type, network_level):
        logger.debug("Setting network type: %r", network_type)
        self.set_network_type(network_type)
        if network_type in ('wifi', '3g', '3GR'):
            logger.debug("Setting network level: %r", network_level)
            self.set_network_level(network_level)

    def set_network_type(self, network_type):
        'set network type to either "wifi" or "3G" or "3GR"'
        if network_type is None:
            network_type = 'None'
        new_widget = self._network_widgets.get(network_type)
        old_widget = self._network_type
        if new_widget != old_widget:
            widgets_list = self.connection_panel.elements
            if old_widget in widgets_list:
                logger.debug("Removing old: %r", old_widget)
                widgets_list.remove(old_widget)
                old_widget.parent = None
            logger.debug("Adding new: %r", new_widget)
            self.connection_panel.add(new_widget, self.connection_x, 
                    self.connection_y)
            self._network_type = new_widget
            self.connection_panel.update(True)

    def on_search_wifi(self, *args):
        logger.debug("Search wifi networks..")
        self.set_status("searching")
        self._get_network_service().add_callback("on_wifi_scan_results", 
                self.update_wifi_list)
        self.search_wifi.set_disabled(True)
        if "PONG" not in self._ping():
            self._get_network_service().want_network(1)
        self._get_network_service().scan_wifi()

    def update_wifi_list(self, *args):
        try:
            self.set_status("")            
            self.doc_page._gui.deactivate_keyboard()
            self.network_list = ScanWifiDialog(568, 597, 
                    parent_window=self.doc_page._gui)
            if len(args) > 0:
                logger.debug("Drawing wifi items")
                self.network_list.draw_net_list(args)
            else:
                self.network_list.set_scan_state("No wireless networks found.")
            self.network_list.add_callback(self.select_wifi_network, 
                    'on_select_item')
            self.network_list.show_overlay()
            self._get_network_service().del_callback("on_wifi_scan_results", 
                    self.update_wifi_list)
            self._get_network_service().get_conn_info()
        except Exception as e:
            logger.debug("Error scanning for wifi networks: %r", e)
        finally:
            self.search_wifi.set_disabled(False)

    def select_wifi_network(self, *args):
        selected_wifi = args[0]
        logger.debug("Add wifi network: %r type: %r", selected_wifi, 
                selected_wifi.security_type)
        if selected_wifi.known:
            network_name = selected_wifi.name.value
            self.network_action_dialog = NetworkActionDialog(568, 500, 
                    network_name, parent_window=self.doc_page._gui)
            self.network_action_dialog.add_callback(self.on_connect_network, 
                    "on_connect_network")
            self.network_action_dialog.add_callback(self.on_forget_network, 
                    "on_forget_network")
            self.network_action_dialog.is_current_connection = selected_wifi.connected
            self.network_action_dialog.show_overlay()
        else:
            self.ssid_input.value = selected_wifi.name.value
            self.ssid_input.update(True)
            self.security_choice.set_selection(selected_wifi.security_type)

    def on_connect(self, *args):
        logger.debug("Adding network entry..")
        if hasattr(self, 'ssid_input') and \
                hasattr(self, 'password_input'):
            ssid = self.ssid_input.value
            password = self.password_input.value
            key_type = self.security_choice.get_selection().value if self.security_choice.get_selection() is not None else "" 
            hidden = False
            added = False
            if self.hidden_network.is_checked():
                hidden = True
            if key_type == "Open":
                logger.debug("Adding open network: %r", ssid)
                added = self.network_action.add_open_wifi(ssid, hidden)
            else:
                logger.debug("Adding secured network: %r", ssid)
                added = self.network_action.add_secured_wifi(ssid, password, 
                        key_type, hidden)
            # close opening keyboard for temporary fix on losing inverse_video and focus on other input text
            # see PROCOREAPP-862 and PROCOREAPP-935 
            self.doc_page._gui.deactivate_keyboard()
            if added:
                self.set_status("connecting")
                self._clear_and_transition_wifi()
            else:
                self.show_message("Failed to add wireless network.")

    def on_connect_network(self, *args):
        network_name = args[0]
        logger.debug("Connecting to network: %r", network_name)
        if not self.network_action.connect_network(network_name):
            self.show_message("Connect request failed.")
        else:
            self.set_status("connecting")
            self._clear_and_transition_wifi()
        
    def on_forget_network(self, *args):
        network_name = args[0]
        logger.debug("Forgetting network: %r", network_name)
        if not self.network_action.forget_network(network_name):
            self.show_message("Forget request failed.")
        else:
            self._clear_and_transition_wifi()

    def _clear_and_transition_wifi(self):
        logger.debug("Clear and transition provisioner wifi")
        self._get_network_service().wifi_reconfigure()
        self._get_network_service().want_network(1)
        self.ssid_input.value=""
        self.ssid_input.remove_screen_cursor()
        self.ssid_input.update(False)
        self.password_input.value=""
        self.password_input.remove_screen_cursor()
        self.password_input.update(True)
        self.security_choice.set_selection(None)
        self._get_network_service().get_conn_info()

    def set_status(self, status):
        if status == "connecting":
            self.curr_ssid.set_text("Connecting..")
        elif status == "searching":
            self.curr_ssid.set_text("Searching..")
        else:
            self.curr_ssid.set_text("")
        
    def on_provision(self, *args):
        logger.debug("Starting provision..")
        if hasattr(self, 'inbox_hostname_input') and \
                hasattr(self, 'account_input'):
            inbox_host = self.inbox_hostname_input.value
            account = self.account_input.value
            if inbox_host is not None and inbox_host.strip() != "" and \
                    account is not None and account.strip() != "":
                self.provision.set_disabled(True)
                return_message = self._provision(inbox_host, account)
                self.provision.set_disabled(False)
                if return_message[0] != 0:
                    self.show_message(return_message[1])
            else:
                self.show_message("Please input a valid hostname or account.")

    def _provision(self, inbox_host, account):
        command_line = "/usr/local/bin/provision.py -i %s -a %s" % \
                (inbox_host, account)
        args = shlex.split(command_line)
        logger.debug('run:%r',args)
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            close_fds=True)
        out,err = p.communicate()
        returncode = p.returncode
        if returncode != 0:
            logger.error("Provision error: %r", err)
            message = err.strip().split('\n')[-1]
        else:
            message = "Provisioned tablet with: %s." % inbox_host
        return (returncode, message)
    
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
    
    def on_page_exit(self):
        self.network_action.keep_alive(False)
    
    
class CalibratePanel(Panel):
    
    type_responds_to_strokes = True
    
    def on_stroke(self, index, last, eraser, button, current_stroke, save_data=None):
        if last:
            self.notify_listeners("on_select", self)
    
    def responds_to_strokes(self):
        return self.type_responds_to_strokes
        
    
class CalibrateTool(SettingsTools):
    """Provision main page."""

    def create_title(self, title):
        title_label = Label(title, font_size=title_font_size)
        title_label.transparent = True
        self.doc_page.gui_page().add(title_label,
                SCREEN_SIZE[0]/2-title_label.w/2, 20)
        self.last_position = self._get_last_position(title_label)
        return title_label

    def create_gui(self, delegate, doc_page):
        self.create_title(DOC_TITLE)
        self.create_divider(0, self.last_position, "Pen Calibration")
        calibrate_label = Label("Tap on the screen to start pen calibration.", 
                font_size=entry_font_size)
        calibrate_label.transparent = False
        doc_page.gui_page().add(calibrate_label, margin_left,
                self.last_position + margin_divider)
        self.last_position = calibrate_label.y + calibrate_label.h
        self.calibrate = CalibratePanel(SCREEN_SIZE[0], SCREEN_SIZE[1]-self.last_position)
        self.calibrate.add_callback(delegate.on_calibrate, 'on_select')
        doc_page.gui_page().add(self.calibrate, 0, self.last_position)

    def refresh(self):
        pass

    def on_calibrate(self, *args):
        logger.debug("Starting pen calibration..")
        try:
            command_line = "/usr/local/bin/provision.py -c"
            ew_exec.run_command(command_line)
        except subprocess.CalledProcessError, e:
            logger.exception(e)
    
    def on_page_exit(self):
        pass