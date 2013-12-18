# Copyright (c) 2011 __Ricoh Company Ltd.__. All rights reserved.
from ew.util import ew_logging
from sdk.widgets.button import Button
from sdk.widgets.label import Label
from sdk.dialog_overlay import DialogOverlay
from sdk.inform_overlay import InformationOverlay


logger = ew_logging.getLogger('ew.internal_decs.network_action_dialog')

class NetworkActionDialog(DialogOverlay):

    def __init__(self, w, h, network_name, **kwargs):
        self.title = "Network"
        self.network_name = network_name
        DialogOverlay.__init__(self, w, h, **kwargs)
        self.line_spacer = 20
        self.add_title()
        self.is_current_connection = False

    def show_error(self, message):
        InformationOverlay.run_popup(message, 
                100, 100, 600, parent_window=self)
    
    def has_title(self):
        if hasattr(self, 'title') and self.title: 
            return True
        else:
            return False
        
    def load_gui(self):
        DialogOverlay.load_gui(self)
        self.network_name_label = Label(self.network_name, font_size=20)
        self.add(self.network_name_label, 
                self.w/2-self.title_label.w/2, 
                self.title_label.y + self.title_label.h + self.line_spacer*4)
        button_line = self.network_name_label.y + self.network_name_label.h + self.line_spacer*2
        logger.debug("Adding connect button")
        self.connect_button = Button('Connect', 129, 48)
        self.connect_button.add_callback(self.connect_network, 'on_button_press')
        self.add(self.connect_button, self.w/2+10, button_line)
        if self.is_current_connection:
            self.connect_button.set_disabled(True)
        logger.debug("Adding forget button")
        self.forget_button = Button('Forget', 129, 48)
        self.forget_button.add_callback(self.forget_network, 'on_button_press')
        self.add(self.forget_button, self.w/2-self.forget_button.w-10, button_line)      
            
    def add_title(self):
        if self.has_title():
            logger.debug("Adding title label")
            self.title_label = Label(self.title, font_size=22)
            self.add(self.title_label, 
                    self.w/2-self.title_label.w/2, self.title_label.h/2)

    def add_close_buttons(self):
        logger.debug("Adding close button")
        close_button = Button('Close', 129, 48)
        close_button.add_callback(self.close_dialog, 'on_button_press')
        self.add(close_button, self.w/2-close_button.w/2, 
                self.h - close_button.h - close_button.h/2)

    def close_dialog(self, *args):
        logger.debug("Closing overlay window")
        self._done.set()
    
    def connect_network(self, *args):
        self.notify_listeners("on_connect_network", self.network_name)
        self.close_dialog()
        
    def forget_network(self, *args):
        self.notify_listeners("on_forget_network", self.network_name)
        self.close_dialog()