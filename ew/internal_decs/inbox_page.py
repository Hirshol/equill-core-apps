#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
"""
@author - Samantha Atkins

InboxPage class handles the Inbox specific portions of the basic
ChooserPage algorithm
"""
import os, threading
from ew.internal_decs.chooser_page import ChooserPage, SPACE_BETWEEN_PANES
from sdk.widgets.label import Label
from sdk.widgets.image_label import ImageLabel
from sdk.widgets.image_button import ImageButton
from ew.internal_decs.inbox_item_panel import InboxItemPanel, InboxPanelWithSelect
from sdk.widgets.panel import Panel
from sdk.display_constants import SZ_1X_MULTIPLIER as ratio
from sdk.system_font import SystemFont
from sdk.widget_cache import ImageCache
import ew.util.ew_logging
logger = ew.util.ew_logging.getLogger('internal_decs.inbox_page')



class InboxPage(ChooserPage):


    def __init__(self, document, index, mpage, **args):
        ChooserPage.__init__(self, document, index, mpage,
                             panel_class = InboxPanelWithSelect,
                             headers = (InboxHeader1, InboxHeader2))

    def bind_widgets(self, delegate=None):
        if not delegate:
            delegate = self._document._delegate
            ChooserPage.bind_widgets(self, delegate)
            update_button = self.update_button()
            update_button.add_callback(
                delegate.update_software, 'on_button_press')
            self.delete_button().add_callback(
                delegate.delete_selected, 'on_button_press')
            self.templates_button().add_callback(
                self.open_templates, 'on_button_press')

            update_button.hide() if not self._document.tablet_update_available else \
                update_button.show()

    def update_button(self):
        logger.debug("%r", self._headers[0].element_dict())
        return self._headers[0].element_dict()['update_button']
    
    def delete_button(self):
        return self._headers[0].element_dict()['delete_button']

    def templates_button(self):
        return self._headers[0].element_dict()['templates_button']

    def open_templates(self, widget):
        def do_it():
            self._document._runner.open_templates()
        thread = threading.Thread(target=do_it, name='templates_thread')
        thread.setDaemon(True)
        thread.start()

    def on_exit(self):
        for widget in self.item_widgets():
            widget.deselect()
        ChooserPage.on_exit(self)
    
    def on_entry(self):
        ChooserPage.on_entry(self)
        update_button = self.update_button()
        update_button.hide() if not self._document.tablet_update_available else \
                    update_button.show()

class InboxHeader1(Panel):
    _total_buttons = 4

    def __init__(self, w, h, elements = (), widget_id=None):
        super(InboxHeader1,self).__init__(w, h, elements,
                                          widget_id=widget_id)
        inbox_header1_bg = ImageCache.instance().get_image("inbox_header1_bg.pgm")
        self.set_background(inbox_header1_bg)

    def create_elements(self):
        _inbox_label = Label("INBOX", 0, 0, SystemFont.h1().size)

        img_refresh= 'delete_refresh_refresh.pgm'
        img_trash = 'delete_refresh_trash.pgm'
        img_update = 'software_update_icon.pgm'
        img_templates = 'inbox_templates.pgm'

        def make_button(image, widget_id):
            return ImageButton("", 36, 36, "DEFAULT", image,
                               image, image, widget_id)

        def add_button(button, left_order):
            buttons_to_right = (self._total_buttons -1) - left_order
            w_displace = (self._total_buttons - left_order) * button.w + (buttons_to_right * 10)
            x = self.w - w_displace
            y = self.h/2 - button.h/2
            self.add(button, x, y)

        self._delete_button = make_button(img_trash, 'delete_button')
        self._refresh_button = make_button(img_refresh, 'refresh_button')
        self._update_button = make_button(img_update, 'update_button')
        self._templates_button = make_button(img_templates, 'templates_button')


        self.add(_inbox_label, self.w/2 - _inbox_label.w/2,
                 self.h/2 - _inbox_label.h/2)
        add_button(self._update_button, 0)
        add_button(self._templates_button, 1)
        add_button(self._delete_button, 2)
        add_button(self._refresh_button, 3)

    def set_from_dict(self, data):
        Panel.set_from_dict(self, data)

    def fields(self):
        """Return the fields of this panel"""
        data = Panel.fields(self)
        data.update({'*type*': 'InboxHeader1'})
        return data


class InboxHeader2(Panel):

    def __init__(self, w, h, elements=(), widget_id=None):
        super(InboxHeader2, self).__init__(w, h, elements,
                                           widget_id=widget_id)
        inbox_header2_bg = ImageCache.instance().get_image("inbox_header2_bg.pgm")
        self.set_background(inbox_header2_bg)

    def create_elements(self):
        layout = InboxItemPanel.layout()
        form_name_label = Label("Form Name", 0, 0, SystemFont.h2().size)
        form_name_label.transparent = True
        form_date_label = Label("   Date (UTC)", 0, 0, SystemFont.h2().size)
        form_date_label.transparent = True
        form_status_label = Label("Status", 0, 0, SystemFont.h2().size)
        form_status_label.transparent = True
        y = self.h/2-form_name_label.h/2
        offset = InboxPanelWithSelect._inner_panel_offset
        self.add(form_name_label, layout.title.x + offset, y)
        self.add(form_date_label, layout.date.x, y)
        self.add(form_status_label, layout.status.x, y)


    def fields(self):
        """Return the fields of this panel"""
        data = Panel.fields(self)
        data.update({'*type*': 'InboxHeader2'})
        return data
