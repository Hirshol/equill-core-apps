#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
from chooser_panel import ChooserPanel, SubLayout, ratio
from ew.util import ew_logging, standard_date
from sdk.widgets.label import Label
from sdk.system_font import SystemFont
from sdk.widget_cache import ImageCache
import time

logger = ew_logging.getLogger('internal_decs.template_item_panel')

class TemplateItemPanel(ChooserPanel):
    _item_fields = ('id', 'title', 'mod_date', 'inst_date')

    class Layout:
        def __init__(self, w, h):
            sub_h = h/2
            self.title = SubLayout(40 *ratio, w * 2/3, sub_h)
            date_w = w / 6
            date_x = 2 * w / 3
            self.date = SubLayout(date_x, date_w, sub_h)
            status_x = 5 * w / 6
            self.inst_date = SubLayout(status_x + 40, w / 6, sub_h)

        def __repr__(self):
            return 'Layout(%r, %r, %r)' % (self.title, self.date, self.inst_date)

    def __init__(self, w=0, h=0, elements=(), widget_id=None):
        ChooserPanel.__init__(self, w, h, elements, widget_id)
        inbox_item_bg = ImageCache.instance().get_image("inbox_item_bg.pgm")
#        self.set_background(inbox_item_bg)
        self._invertable = True
        self._guis = None

    def set_instantiation_date(self):
        self.gui('inst_date').set_text(standard_date(time.time()))

    def guis(self):
        if not self._guis:
            self._guis = dict(title = self.elements[0],
                              date = self.elements[1],
                              inst_date = self.elements[2])
        return self._guis
    
    def gui(self, name):
        return self.guis()[name]

    def update_from_memphis(self):
        mtitle, error = self.title_and_error(self.doc_id)
        changes = False
        if mtitle != self.title:
            changes = True
            self.title = mtitle
            self.gui('title').set_text(mtitle)
    
    def create_elements(self):
        item_h = self.h

        def add_label(label, layout):
            logger.warn('!!!!!panel height < label height (%d, %d)', 
                        item_h, label.h)
            self.add(label, layout.x, item_h/2-label.h/2)

        layout = self.layout()
        self.title_gui = Label(self.title, layout.title.w, layout.title.h,
                               SystemFont.regular().size)
        self.title_gui.transparent = False
        add_label(self.title_gui, layout.title)


    def on_stroke(self, index, last, eraser, button, stroke_info, extra_data=None):
        stroke_info.set_consumed()
        logger.debug("%s has listeners %s", self, self.listeners())
        if not self.is_downloading():
            self.notify_listeners('instantiate_template', self)
        else:
            logger.warn("cannot instantiate %s as it is still downloading",
                    self.title)

    def fields(self):
        """Return the fields of this panel"""
        data = ChooserPanel.fields(self)
        data.update({'*type*': 'TemplateItemPanel',
                     'id': self.doc_id,
                     'title': self.title,
                     })
        return data


