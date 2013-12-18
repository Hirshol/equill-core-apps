#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
import os
from ew.internal_decs.chooser_page import ChooserPage
from ew.internal_decs.chooser_panel import ChooserPanel
from ew.internal_decs.template_item_panel import TemplateItemPanel
from ew.util import ew_logging
from ew.util import system_config
from sdk.widgets.panel import Panel
from sdk.widgets.label import Label
from sdk.widgets.image_button import ImageButton
from sdk.system_font import SystemFont
from sdk.widget_cache import ImageCache

logger = ew_logging.getLogger('internal_decs.templates_page')


class TemplatesPage(ChooserPage):

    def __init__(self, document, index, mpage, **args):
        ChooserPage.__init__(self, document, index, mpage,
                             panel_class = TemplateItemPanel,
                             headers = (TemplateHeader1, TemplateHeader2))

class TemplateHeader1(Panel):

    def __init__(self, w, h, elements = (), widget_id=None):
        Panel.__init__(self, w, h, elements,
                                          widget_id=widget_id)
        self.refresh_event_id = "inbox_refresh"
        self.templates_label = None
        self._refresh_button = None
        inbox_header1_bg = ImageCache.instance().get_image("inbox_header1_bg.pgm")
        self.set_background(inbox_header1_bg)

    def create_elements(self):
        _label = Label("Blank Forms", 0, 0, SystemFont.h1().size)

        img_refresh_def_btn_path = os.path.join(system_config.resource_dir, "images",
                                                'delete_refresh_refresh.pgm')
        img_refresh_sel_btn_path = img_refresh_def_btn_path
        img_refresh_dis_btn_path = img_refresh_def_btn_path

        self._refresh_button = ImageButton("R", 36, 36, "DEFAULT",
            img_refresh_def_btn_path, img_refresh_sel_btn_path,
            img_refresh_dis_btn_path, "refresh_button")
        self.add(_label, self.w/2 - _label.w/2,
                 self.h/2 - _label.h/2)
        self.add(self._refresh_button, self.w-self._refresh_button.w,
                 self.h/2-self._refresh_button.h/2)


    def fields(self):
        """Return the fields of this panel"""
        data = Panel.fields(self)
        data.update({'*type*': 'TemplateHeader1'})
        return data

class TemplateHeader2(Panel):

    def __init__(self, w, h, elements=(), widget_id=None):
        Panel.__init__(self, w, h, elements,
                                           widget_id=widget_id)
        inbox_header2_bg = ImageCache.instance().get_image("template_header2_bg.pgm")
        self.set_background(inbox_header2_bg)

    def create_elements(self):
        layout = self.doc_page.panel_layout()
        form_name_label = Label("Form Name", 0, 0, SystemFont.h2().size)
        form_name_label.transparent = True
        y = self.h/2-form_name_label.h/2
        self.add(form_name_label, layout.title.x, y)

    def fields(self):
        """Return the fields of this panel"""
        data = Panel.fields(self)
        data.update({'*type*': 'TemplateHeader2'})
        return data
