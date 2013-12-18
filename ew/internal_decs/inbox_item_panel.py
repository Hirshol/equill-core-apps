#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
"""
This file will define the InboxItemPanel which is the Panel
information about a single selectable document.
"""
import sys,time,threading
from sdk.widgets.panel import Panel
from sdk.widgets.label import Label
from sdk.widget_cache import ImageCache
from sdk.widgets.checkbox import Checkbox
from sdk.widgets.hotspot import Hotspot
import pdb

try:
    from sdk.widgets.image_status import ImageStatus
except Exception, ex:
    raise Exception('at failure the path was %s with exception %s' % (sys.path, ex))

#from sdk.widgets.image_button import ImageButton
from sdk.display_constants import SZ_1X_MULTIPLIER as ratio
import ew.util.ew_logging
from ew.util import exclusive_document_lock, standard_date_time, short_date_time
from ew.internal_decs.chooser_panel import SubLayout, ChooserPanel
from sdk.system_font import SystemFont

logger = ew.util.ew_logging.getLogger('ew.internal_decs.inbox_item_panel')

#ERROR_STATUS = "error"

#perhaps more..

class NamedStruct:
    def __init__(self, **fields):
        self.__dict__.update(fields)


class InboxPanelWithSelect(ChooserPanel):
    _inner_panel_offset = 40
    
    @classmethod
    def per_item_fields(cls):
        return InboxItemPanel.per_item_fields
    
    def __init__(self, w, h, elements=(), widget_id=None):
        ChooserPanel.__init__(self, w, h, elements, widget_id)
        self.pass_strokes_through = True
        self._inner_x = self._inner_panel_offset
        self.inner = None
        self.is_selected = False
        
    def __repr__(self):
        return 'InboxPanelWithSelect inner: %r' % self.inner

    def _ensure_inner(self):
        if not self.inner:
            self.inner = InboxItemPanel(self.w - self._inner_x, self.h)

    def add_listener(self, target):
        self.inner.add_listener(target)

    def set_fields(self, data):
        if not self._is_being_loaded:
            self._ensure_inner()
            self.inner.set_fields(data)
 
    def create_elements(self):
        self._ensure_inner()
        self.inner.create_elements()
        self.inner.creation_time = self.creation_time
        self.inner.widget_id='inner'
        box_size = 15
        self.select_button = Checkbox(box_size, box_size, style='check', widget_id='select')
        self.add(self.select_button, 10, (self.h - box_size) / 2)
        self.add(self.inner, self._inner_panel_offset, 0)
        self.select_button.add_listener(self)
        #surround with hotspot to make it easier to fire the checkbox due to tablet limitations
        self.hotspot = Hotspot(self._inner_panel_offset - 1, self.h, widget_id='hotspot')
        self.add(self.hotspot, 0, 0)
        self.hotspot.add_listener(self)

    def on_hotspot(self, widget):
        self.select_button.toggle_checked()
        self.on_checked(self.select_button)

    def on_checked(self, widget):
        self.is_selected = widget.is_checked()
        logger.debug('%s is selected = %s', self, self.is_selected)

    def load_elements(self, data):
        ChooserPanel.load_elements(self, data)
        if self.elements:
            logger.debug('elements ===> %s', self.element_dict())
            self.select_button = self.element_dict()['select']
            self.hotspot = self.element_dict()['hotspot']
            self.inner = self.element_dict()['inner']
            self.select_button.add_listener(self)
            self.hotspot.add_listener(self)

    def set_status(self, new_status):
        self._ensure_inner()
        self.inner.set_status(new_status)
        if self.inner.is_downloading() or self.inner.is_being_submitted():
            self.select_button.set_disabled(True)
        else:
            self.select_button.set_disabled(False)
            
    def is_downloading(self):
        return self.inner.is_downloading()

    def error_status(self):
        return self.inner.error_status()

    def update_from_memphis(self):
        return self.inner.update_from_memphis()

    def set_downloading(self, boolean):
        self.inner.set_downloading(boolean)
        self.select_button.set_disabled(boolean)

    def deselect(self):
        self.is_selected = False
        self.select_button.force_unchecked()
            
    def __getattr__(self, name):
        #pdb.set_trace()
        self._ensure_inner()
        return getattr(self.inner, name)
     
    def fields(self):
        res = ChooserPanel.fields(self)
        res['*type*'] = 'InboxPanelWithSelect'
        return res

class InboxItemPanel(ChooserPanel):
    """

    """
    Status = NamedStruct(new='New', error='Error', submitted='Submitted', 
                         modified='Modified',
                         incoming='Incoming')

    _item_fields = ('id', 'title', 'mod_date', 'status')
    _default_values = dict(status = Status.new)
    _instance_lock = threading.RLock()
    
    class Layout:
        def __init__(self, w, h):
            sub_h = h/2
            title_x = 0
            self.title = SubLayout(title_x *ratio, w/2, sub_h)
            date_w = w / 4 - 20
#            date_x = w / 2
            date_x = 7 * w / 12
            self.date = SubLayout(date_x, date_w, sub_h)
            status_x = 5 * w / 6
            self.status = SubLayout(status_x + 40, w / 6, sub_h)

    def __repr__(self):
        return 'InboxItemPanel doc_id: %s, title: %s' % (
            getattr(self, 'doc_id', None),
            getattr(self, 'title', None))

    def is_being_submitted(self):
        with self._instance_lock:
            return self.status == self.Status.submitted

    def submit_requested(self):
        with self._instance_lock:
            return self.status == self.Status.submitted

    def item_id(self):
        return getattr(self,'doc_id', None)

    def set_downloading(self, boolvalue):
        ChooserPanel.set_downloading(self, boolvalue)
        if boolvalue:
            self.set_status(self.Status.incoming)

    def error_status(self):
        estatus = None
        if self.status == self.Status.error:
            _, estatus = self.title_and_error(self.doc_id)
        return estatus

    def update_from_memphis(self):
        mtitle, error = self.title_and_error(self.doc_id)
        changes = False
        if mtitle != self.title:
            changes = True
            self.title = mtitle
            self.gui('title').set_text(mtitle)
            #self.bump_modified()
        if error and (self.status != self.Status.error):
            changes = True
            self.set_status(self.Status.error)
        return changes

    def create_elements(self):
        item_h = self.h

        def add_label(label, layout):
            self.add(label, layout.x, item_h/2-label.h/2)

        layout = self.Layout(self.w, self.h)
        self.title_gui = Label(self.title, layout.title.w, layout.title.h,
                               SystemFont.regular().size)
        self.title_gui.transparent = False

        #note that only the ones using the defined constants are implemented (sja)

        status_dictionary = {
            'New':          'status_new.pgm',
            'Error':        'status_error.pgm',
            'Incoming':     'status_incoming.pgm',
            'Modified' :    'status_modiedsaved.pgm',
            'Submitted':    'status_submitted.pgm'
        }

        self.status_gui = ImageStatus("InboxStatus", 32, 32,
            status_dictionary, self.status)

        self.date_gui = Label(short_date_time(self.creation_time), layout.date.w, layout.date.h,
                              SystemFont.regular().size)
        self.date_gui.transparent = False

        add_label(self.title_gui, layout.title)
        add_label(self.date_gui, layout.date)
        add_label(self.status_gui, layout.status)

    def __init__(self, w=0, h=0, elements=(), widget_id=None):
        ChooserPanel.__init__(self, w, h, elements, widget_id)
        inbox_item_bg = ImageCache.instance().get_image("inbox_item_bg.pgm")
        w,h = inbox_item_bg.size
        self._invertable = True
        cropby = (40, 0, w, h)
        self.set_background(inbox_item_bg.crop(cropby))
        self._guis = None

    def bump_modified(self):
#        self.mod_date = standard_date(time.time())
#        self.gui('date').set_text(self.mod_date)
        pass #no longer a mod date

    def guis(self):
        if not self._guis:
            self._guis = dict(title = self.elements[0],
                              date = self.elements[1],
                              status = self.elements[2])
        return self._guis
    
    def gui(self, name):
        return self.guis()[name]

    def set_status(self, status):
        with self._instance_lock:
            self.gui('status').set_status(status)
            self.status = status
            self.bump_modified()

    def on_stroke(self, index, last, eraser, button, stroke_info, extra_data=None):
        stroke_info.set_consumed()
        logger.debug("%s has listeners %s", self, self.listeners())
        self.notify_listeners('on_select', self)

    def fields(self):
        """Return the fields of this panel"""
        data = ChooserPanel.fields(self)
        data.update({'*type*': 'InboxItemPanel',
                     'id': self.doc_id,
                     'title': self.title,
                     'mod_date': self.mod_date,
                     'status': self.status
                     })
        return data


