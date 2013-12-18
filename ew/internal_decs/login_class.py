#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
from sdk.overlay_switch import InputText
from sdk.overlay_switch import Password
from sdk.widgets.label import Label
from sdk.widgets.button import Button
from sdk.widgets.panel import Panel
from sdk.widgets.image_label import ImageLabel
from sdk.display_constants import SCREEN_SIZE
from sdk.inform_overlay import InformationOverlay
from ew.util import ew_logging
from ew.util import login
from ew.internal_decs.settings_class import entry_font_size, \
        margin_left, start_body, input_font_size, start_divider
from ew.internal_decs.settings_class import SettingsBase

logger = ew_logging.getLogger('ew.internal_decs.login_class')

class LoginMain(SettingsBase):
    """Various tablet tools."""

    def create_gui(self, delegate, doc_page):
        input_start_x = 40
        input_start_y = 345
        logo = ImageLabel("logo-image", 376, 98, "logo-eWriter.pgm")
        doc_page.gui_page().add(logo, margin_left+10, 100)
        try:
            login_panel = Panel(400, 100)
            user_label = Label("Username:", font_size=entry_font_size)
            user_label.persist = False
            user_label.transparent = True
            self.last_position = input_start_y
            login_panel.add(user_label, login_panel.w/2 - user_label.w - 8, 0)
            self.user_input = InputText('', 300, font_size=input_font_size)
            self.user_input.persist = False
            login_panel.add(self.user_input, login_panel.w/2 + 8,0)
            password_label = Label("Password:", font_size=entry_font_size)
            password_label.persist = False
            password_label.transparent = True
            login_panel.add(password_label, login_panel.w/2 -
                    password_label.w - 8, self.user_input.y + self.user_input.h + 4)
            self.password_input = Password('', 300, font_size=input_font_size)
            self.password_input.persist = False
            login_panel.add(self.password_input, login_panel.w/2 + 8,
                    self.user_input.y + self.user_input.h + 4)
            self.login_button = Button('Login', 129, 48)
            self.login_button.persist = False
            self.login_button.add_callback(delegate.on_login, 'on_button_press')
            login_panel.add(self.login_button, login_panel.w/2 +
                    self.password_input.w - self.login_button.w,
                    self.password_input.h + self.password_input.y + 8)
            doc_page.gui_page().add(login_panel, input_start_x, input_start_y)
            self.last_position = SCREEN_SIZE[1]-1
        except Exception, e:
            logger.exception("Exception in login document %r", e)
        
    def refresh(self):
        pass

    def on_login(self):
        try:
            l = login.Login()
            self.login_button.set_disabled(True)
            logger.debug("Logging in..")
            logger.debug("user: %r password: %r", self.user_input.value, self.password_input.value)            
            
            # Try logging in.  We will either succeed (in which case we can open Inbox) or fail,
            # in which case we want to show an error message via popup dialog
            rtn = l.login(self.user_input.value, self.password_input.value)
            self.login_button.set_disabled(False)
            if rtn['status'] == 'error':
                page = self.doc_page._document.current_page._gui
                InformationOverlay.run_popup(rtn['message'], 220, 460, 400, parent_window=page)
            else:
                self.doc_page._document._runner.open_inbox_with_infobar()
        except Exception, e:
            logger.exception('Exception caught trying to log in: %r', e)