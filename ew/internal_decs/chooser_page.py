#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
"""
A ChooserPage is a DocumentPage that tracks the ChoicePane widgets
and can rearrange them.
"""

from sdk.doc_page import DocumentPage
from ew.util import ew_logging
from sdk.display_constants import SZ_1X_MULTIPLIER as ratio, SCREEN_SIZE, COLOR_WHITE
from chooser_panel import ChooserPanel, HEADER_VSIZE
from sdk.display import Display
from sdk.display_window import pending_gui
logger = ew_logging.getLogger('ew.internal_decs.chooser_page')
from PIL import Image
import pdb, threading

SPACE_BETWEEN_PANES = 1 #1x based
OFFSET_INBOX_TITLE = 366 #1x based
OFFSET_REFRESH_BUTTON = 715 #1x based
WIDTH_INBOX_TITLE = 100 #1x based

class ChooserPage(DocumentPage):

    _items_per_page = 8
    _pane_locations = None
    _blank_page = Image.new('L', SCREEN_SIZE, COLOR_WHITE)

    @classmethod
    def widget_pane_locations(cls):
        if not cls._pane_locations:
            vertical_start = 66 * ratio
            per_pane_height = ChooserPanel.panel_size()[1]
            space = SPACE_BETWEEN_PANES * ratio
            x,y = 0, vertical_start + 2 * (HEADER_VSIZE + space)
            pane_locations = []
            max_y = SCREEN_SIZE[1] - per_pane_height
            while y < max_y:
                pane_locations.append((x, y))
                y += per_pane_height + space
            cls._pane_locations = pane_locations
            cls.set_items_per_page(len(pane_locations))
        return cls._pane_locations

    @classmethod
    def chooser_panes_per_page(cls):
        """
        Returns the number of choosable items that will fit on a page.
        Simple constant in default case.  Should be overridden by subclass
        """
        return len(cls.widget_pane_locations())

    @classmethod
    def set_items_per_page(cls, count):
        cls._items_per_page = count

    def __init__(self, document, index, memphis_page, panel_class, headers):
        self.panel_class = panel_class
        self._choser_pane_locations = self.widget_pane_locations()
        self.chooser_panes=[]
        DocumentPage.__init__(self, document, index, memphis_page)
        self.chooser_panes = self.load_panes()
        self.item_start = 0
        self.header_classes = headers
        self._instance_lock = threading.RLock()

    def panel_layout(self):
        return self.panel_class.layout()

    def create_gui(self):
        """
        Creates an empty Inbox page. This should have two rows of
        panes.
        """
        logger.debug("%r creating gui",self)
        DocumentPage.create_gui(self)
        self.add_headers()

    def create_header(self, header_class):
        w,h = self.panel_class.panel_size()
        h = HEADER_VSIZE
        header = header_class(w, h)
        header.doc_page = self
        header.create_elements()
        return header

    def add_headers(self):
        """
        Add the Inbox page header panes. Faked for now with one big
        label.
        """
        vertical_start = 66 * ratio
        self._headers = []
        for header_class in self.header_classes:
            self._headers.append(self.create_header(header_class))

        start = vertical_start
        for header in self._headers:
            self.gui_page().add(header, 0, start)
            start += header.h

        self.item_start = 0, start + (SPACE_BETWEEN_PANES * ratio)

    def _ensure_gui(self):
        if not self._gui:
            self.load_panes()

    def item_widgets(self):
        """
        Returns the panes encapsulating each choosable item
        on this page.  Each pane is wired to have my document as listener.
        """
        return [widget for widget,_ in self.chooser_panes]

    def load_panes(self):
        logger.debug("entering load_panes, panel_class = %s", self.panel_class)
        if not self._gui: self.load_gui()
        if not self._gui:
            logger.debug("we have no gui in load_panes!!!!")
            return []
        self._headers = self._gui.elements[:2]
        self.use_blank_clean_image()
        chooser_panes = []
        logger.debug('in load_panes gui has %d elements',
                     len(self._gui.elements))
        if self._gui:
            for i in range(len(self._gui.elements)):
                w = self._gui.elements[i]
                if isinstance(w, self.panel_class):
                    chooser_panes.append((w,i))
        logger.debug('load_panes found %d item panes', len(chooser_panes))
        return chooser_panes

    def update_pane(self, index, data):
        with self._instance_lock:
            self.chooser_panes[index][0].update_metadata(data)
            self._qui.process_changes()

    def widget_at_index(self, index):
        return self.chooser_panes[index][0] if index < len(self.chooser_panes) \
            else None

    def drop_gui(self):
        pass  #don't do this for ChooserPage instances

    def refresh_button(self):
        return self._headers[0].element_dict()['refresh_button']
    
    def bind_widgets(self, delegate=None):
        if not delegate:
            delegate = self._document._delegate
        DocumentPage.bind_widgets(self, delegate)
        logger.debug('page %s is binding widgets', self.page_id)
        self.refresh_button().add_callback(
            delegate.on_refresh, 'on_button_press')
        for pane,_ in self.chooser_panes:
            pane.add_listener(delegate)

    def set_widgets(self, widgets):
        info = [(w.doc_id, w.title) for w in widgets]
        logger.debug('set_widgets on %s to %s', self.page_id, info)
        self.use_blank_clean_image()
        with self._instance_lock:
            old_widgets = [c[0] for c in self.chooser_panes]
            if widgets == old_widgets:
                logger.debug('set_widgets: no change from current widgets')
                return
            self.chooser_panes = []
            #pdb.set_trace()
            self._gui.elements = self._gui.elements[:2]
            if widgets:
                for widget, location in zip(widgets, self.widget_pane_locations()):
                    widget.parent = None
                    self._gui.add(widget, *location)
                    self.chooser_panes.append((widget,
                                       len(self._gui.elements) - 1))
            logger.debug('processing_changes(True) for page %s', self.page_id)
            self._gui.process_changes(True)
            self._gui.remap_widgets()

    def update_using_memphis(self):
        found_changes = False
        for widget,_ in self.chooser_panes:
            if widget.update_from_memphis():
                found_changes = True
        if found_changes or self._gui.has_changed():
            self._gui.process_changes()

    def on_entry(self):
        with self._instance_lock:
            self._ensure_gui()
            self._delegate.on_page_entry(self)
            self.update_using_memphis()
            self._gui.activate()
            logger.debug('%s has %d items', self.page_id, len(self.chooser_panes))

    def original_image(self):
        return self._blank_page

    def close(self):
        with self._instance_lock:
            self.save_changes_to_disk(closing=True)
