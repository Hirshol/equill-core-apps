#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""
author: Samantha Atkins
"""
from sdk.display_constants import SZ_1X_MULTIPLIER as ratio
from sdk.widgets.panel import Panel
import time, os
from ew.util import ew_logging, standard_doc_path
from ew.memphis.file import MemphisFile
logger = ew_logging.getLogger('ew.internal_decs.chooser_panel')

HEADER_VSIZE = 55
ITEM_PANEL_VSIZE = 50

class ChooserFont:
    __slots__ = ['family', 'type', 'size']

    """TODO: Move to utils and make smarter"""
    def __init__(self, family="DejaVuSansCondensed.ttf", type="", size=18):
        self.family = family
        self.type = type
        self.size = size

class SubLayout:
    def __init__(self,x_top, width, height):
        self.x = x_top
        self.w = width
        self.h = height

    def __repr__(self):
        return '(%d,%d,%d)' % (self.x, self.w, self.h)

class ChooserPanel(Panel):
    """A chooser panel abstracts out commonalities of the item panel
    inbox and text based template document per item widgets"""

    _panel_size = 805 * ratio, ITEM_PANEL_VSIZE * ratio
    _layout = None
    _mapped_names = dict(id = 'doc_id')
    _default_values = {}

    @classmethod
    def layout(cls):
        if not cls._layout:
            cls._layout = cls.Layout(*cls.panel_size())
        return cls._layout

    @classmethod
    def panel_size(cls):
        "return my size (width, height)"
        #taken from kanae's latest and scaled 12/13/10
        return cls._panel_size

    @classmethod
    def create_instance_with_data(cls, item_info):
        width,height = cls.panel_size()
        instance = cls(width, height)
        instance.set_fields(item_info)
        instance.creation_time = time.time()
        instance.create_elements()
        return instance

    @classmethod
    def per_item_fields(cls):
        return (('id', 'doc_id'), ('title', 'title'), ('mod_date', 'mod_date'))

    def create_elements(self):
        raise Exception('subclass must implement create_elements')

    def __init__(self, w=0, h=0, elements=(), widget_id=None):
        if w == 0:
            w,h = self.panel_size()
        super(ChooserPanel, self).__init__(w, h,
                                   widget_id=widget_id)
        self._flash = False
        self.pass_strokes_through = False
        self.location = -1
        self._is_downloading = False

    def is_downloading(self):
        return self._is_downloading

    def set_downloading(self, boolval):
        self._is_downloading = boolval

    def set_from_dict(self, data):
        Panel.set_from_dict(self, data)
        self.set_fields(data)

    def update_from_memphis(self):
        return False

    def title_and_error(self, docid):
        mtitle, error = self.title, None
        if not self.is_downloading():
            path = standard_doc_path(docid)
            if os.path.exists(path):
                with MemphisFile(standard_doc_path(docid)) as mf:
                    mtitle = mf.metadata.get('memphis.title', None)
                    if not mtitle:
                        logger.debug('!!!!%s missing normal title', self)
                        mtitle = mf.info.get('memphis.title', docid)
                    error = mf.info.get("memphis.delivery.errorstatus", None)
        return mtitle, error

    def set_fields(self, data):
        if not data.get('creation_time'):
            data['creation_time'] = time.time()
        def attribute_name(name):
            return self._mapped_names.get(name, name)
        def value_of(name):
            data_val = data.get(name)
            return data_val if data_val else self._default_values.get(name, '')

        for name in self._item_fields:
            setattr(self, attribute_name(name), value_of(name))
        self.creation_time = data['creation_time']
        if 'is_downloading' in data:
            self.set_downloading(True)

    def redraw_containing_page(self):
        page = self.containing_page()
        doc_page = page.document_page if page else None
        if doc_page: doc_page.display()

    def fields(self):
        data = Panel.fields(self)
        data.update(dict(creation_time = self.creation_time))
        if self.is_downloading():
            data['is_downloading'] = True

        return data

    @classmethod
    def instance_from_data(cls, data):
        """Recreate the panel instance"""
        panel = cls(data['w'], data['h'], (), data.get('widget_id'))
        return panel

    def set_background(self, background_file):
        self.background = background_file
