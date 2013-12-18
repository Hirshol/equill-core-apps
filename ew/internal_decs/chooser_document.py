#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.
"""
@author Samantha Atkins

A ChooserDocument is a DEC Document that contains
an ordered list of compound widget per item (document or template).
It allows choosing (selecting) the corresponding item by
interacting with the compound widget.
"""
from __future__ import with_statement
from sdk.document import Document
from sdk.delegate import Dec
from sdk.display_window import pending_gui
from ew.util import standard_doc_path, locate, docid_from_path, comms, ew_logging
from ew.util import system_config as sysconfig
from ew.memphis.file import MemphisFile
import threading, os, time, itertools

logger = ew_logging.getLogger("ew.internal_decs.chooser_document")

class ChooserDelegate(Dec):
    def on_submit(self):
        return False

    def on_refresh(self, widget):
        self._document.on_refresh(widget)

    def on_load(self):
        #re PROCOREAPP-398 remove *.ink, *.edit files from pages so user doesn't see old strokes
        self._document.remove_strokes()
        if not self._document.pages:
            self._document.add_page()
        for page in self._document.pages:
            page.bind_widgets()

def creation_subsort(field):
    def compare(widget1, widget2):
        prime_order = cmp(getattr(widget1,field), getattr(widget2, field))
        return prime_order if prime_order else cmp(widget1.creation_time, widget2.creation_time)
    return compare

Sort_Functions = dict (
    title = creation_subsort('title'),
    modification_date = creation_subsort('mod_date'),
    status = creation_subsort('status'),
    creation_date = lambda x,y: cmp(x.creation_date, y.creation_date))


class ChooserDocument(Document):
    _delegate_class = ChooserDelegate
    def __init__(self, path, subdir, page_class, widget_factory, **kwargs):
        self._mask_strokes = True
        Document.__init__(self, path, page_class, **kwargs)
        self.doc_widgets = []
        self.widget_factory = widget_factory
        self.widget_index = {}
        self._subdir = subdir
        self._instance_lock = threading.RLock()
        self._launcher_client = None
        self._server = None
        #must must load_widgets and such here as the non-gui access
        #from listing_updater depends on the information
        self.load_main_widgets()
        self.refresh()
        if not self.pages:
            self.add_page()
        self._has_gui = True

    def refresh(self):
        #not clear we have to do all this work in the DocumentRunner case.
        self.remove_strokes()
        added_or_removed = self.check_docids()
        resorted = self.check_sorting(False)
        if added_or_removed or resorted:
            with self._instance_lock:
                self.reflow_widgets(0)
            
    def sort_function(self):
        if not hasattr(self, '_sort_function'):
            sort_main_field = self.localinfo.get('sort_main_field', None)
            if not sort_main_field:
                logger.debug('no chooser doc sort specified. setting default')
                sort_main_field = 'title'
                self.localinfo['sort_main_field'] = sort_main_field
                self.localinfo.save()
            self._sort_function = Sort_Functions[sort_main_field]
        return self._sort_function

    def check_sorting(self, reflow_on_change = True):
        sorted_widgets = sorted(self.doc_widgets, cmp = self.sort_function())
        changes = sorted_widgets != self.doc_widgets
        if changes:
            self.doc_widgets = sorted_widgets
            if reflow_on_change:
                self.reflow_widgets(0)
        return changes

    def clear_images(self):
        for page in self.pages:
            page.clear_images()

    def check_docids(self):
        """minimal sanity check after 1st load"""
        known = set([w.doc_id for w in self.doc_widgets if \
                        not w.is_downloading()])
        logger.debug('refresh.doc_widgets: %s', self.doc_widgets)
        logger.debug('refresh.known docids in gui: %s', known)
        directory = os.path.join(sysconfig.data_home, self._subdir)

        def doc_title(memphis_path):
            path = os.path.join(directory, memphis_path)
            logger.debug('getting info from memphis doc @%s', path)
            with MemphisFile(path) as mf:
                title = mf.metadata.get('memphis.title', None)
            return title
            
        memphis_docs = dict([(docid_from_path(x), doc_title(x)) for x in os.listdir(directory) \
                    if x.endswith('.memphis')])
        docs = set(memphis_docs.keys())
        logger.debug('refresh.docs: %s', docs)
        changes = docs != known
        if changes:
            missing = docs.difference(known)
            extra = known.difference(docs)
            logger.debug('extra doc_ids in gui: %s, missing in gui %s',
                         extra, missing)
            self.doc_widgets = filter(lambda x: x.doc_id not in extra,
                                      self.doc_widgets)
            for doc in missing:
                self.add_widget_for_docid(doc)

        for widget in self.doc_widgets:
            cur_title = memphis_docs.get(widget.doc_id, None)
            if cur_title and (cur_title != widget.title):
                widget.title = cur_title
                widget.gui('title').set_text(cur_title)
                changes = True
        return changes

    def load_main_widgets(self):
        """ Just load existing widgets here.  Don't worry about whether they exist or not.  
        That will be sorted in the check_docids and such."""

        for page in self.pages:
            widgets = page.item_widgets()
            for widget in widgets:
                self.widget_index[widget.doc_id] = len(self.doc_widgets)
                self.doc_widgets.append(widget)

    def widget_with_id(self, item_id):
        where = self.widget_index.get(item_id, None)
        return (self.doc_widgets[where] if where != None  else None), where

    def check_initial_state(self):
        directory = os.path.join(sysconfig.data_home, self._subdir)
        known = self.widget_index.keys()
        docs = [docid_from_path(x) for x in os.listdir(directory) \
                    if x.endswith('.memphis')]
        logger.debug('found documents: %s, known: %s', docs, known)
        missing = (doc_id for doc_id in docs if doc_id not in known)

        with pending_gui():
            for doc_id in missing:
                self.add_widget_for_docid(doc_id)


    def doc_exists(self, docid):
        return os.path.isdir(standard_doc_path(docid, self._subdir))

    def add_widget_for_docid(self, docid):
        if not docid in self.widget_index:
            path = standard_doc_path(docid, self._subdir)
            info = self.item_info_for_memphisfile(path)
            self.add_item(info)

    def remove_widget_for_docid(self, docid):
        self.remove_item(dict(id = docid))

    def on_refresh(self, _):
        self.listings_updater().tablet_request_refresh()

    def find_item_index(self, item_id):
        index  = self.widget_index.get(item_id, None)
        if index == None:
            index = len(self.doc_widgets)
        return index

    def listings_updater(self):
        with self._instance_lock:
            if not self._listings_updater_client:
                self._listings_updater_client = \
                    comms.create_XMLRPC_client('localhost',
                                               comms.LISTINGS_UPDATER_PORT)
        return self._listings_updater_client

    def on_select(self, item_widget):
        """
        Take whatever action is appropriate for this type of chooser. Subclass
        responsibility.  Generally tell the launcher to do something.
        """
        raise "Subclass must implement on_select(item_widget)"

    def downloading_documents(self,doc_title_pairs):
        with self._instance_lock:
            for doc_id, title in doc_title_pairs:
                if not doc_id in self.widget_index:
                    info = dict(id=doc_id, title=title)
                    widget = self.make_widget_with_info(info)
                    widget.set_downloading(True)
                    self.doc_widgets.append(widget)
            self.doc_widgets.sort(self.sort_function())
            self.reflow_widgets(0)
            self.save_page_changes()

    def stopped_downloading(self, docids):
        with self._instance_lock:
            remaining = [w for w in self.doc_widgets 
                         if not (w.is_downloading() and w.doc_id in docids)]
            if len(remaining) < len(self.doc_widgets):
                self.doc_widgets = remaining
                self.reflow_widgets(0)
                self.save_page_changes()

    def item_info_for_memphisfile(self, path):
        """Creates standard file based item_info with id=doc_id, mod_date=
        file system file date and title from the memphis file info"""
        logger.debug("creating chooser_item_info for %s", path)
        docid = docid_from_path(path)
        with MemphisFile(path) as mfile:
            title = mfile.info.get('memphis.title', docid)
        mod = time.strftime('%Y/%m/%d', time.localtime(os.path.getmtime(path)))
        return dict(id = docid, mod_date = mod, title = title)

    def add_item(self, item_info):
        """To add GUI for an item requires we
        have our widget_factory create an
        appropriate widget wrapping the item_info.

        If our current last page contains as many
        widgets as oru widget_factory say can
        fit on a page or if we have no pages yet,
        we will add a page.

        Note that it is sufficient wo update json
        widget_info in the widget metadata on all
        pages the insert of the new widget would
        cause a mod to.  Whether we gen images
        depends on whether  we are open on the device
        or not"""
        with self._instance_lock:
            logger.debug('add_item %s', item_info)
            widget = self.make_widget_with_info(item_info)
            self.doc_widgets.append(widget)
            self.doc_widgets.sort(cmp=self.sort_function()) #bisect equiv better later
            self.reflow_widgets(0)

            
    def make_widget_with_info(self, item_info):
        widget = self.widget_factory.create_instance_with_data(item_info)
        widget.add_listener(self._delegate)
        return widget
    
    def add_page(self):
        Document.add_page(self,panel_class=self.widget_factory)

    def reflow_widgets(self, starting_index):
        logger.debug("starting reflow")
        per_page = self.page_class.chooser_panes_per_page()
        page_index = starting_index/per_page
        pages_needed = len(self.doc_widgets) / per_page + 1
        while len(self.pages) < pages_needed:
            self.add_page()
        for page in self.pages[page_index:]:
            start = page.page_index * per_page
            widgets = self.doc_widgets[start: start + per_page]
            page.set_widgets(widgets)
        self.reindex_widgets()

    def reindex_widgets(self):
        pairs = zip([w.doc_id for w in self.doc_widgets], range(len(self.doc_widgets)))
        self.widget_index = dict(pairs)
            
        
    def remove_item(self, item_info):
        """Inverse of the add item.  Find the widget
        for the item and remove it if found."""

        with self._instance_lock:
            logger.debug('processing remove_item %s', item_info)
            docid = item_info['id']
            widget, location = self.widget_with_id(docid)
            if widget:
                logger.debug('removing widget %s with doc_id %s at location %i', widget, docid, location)
                self.doc_widgets[location:] = self.doc_widgets[location + 1:]
                self.widget_index.pop(docid, None)
                self.reflow_widgets(location)
            else:
                logger.debug('attempt to remove non-existent widget[%s]', docid)

    def remove_strokes(self):
        logger.debug('removing stokes in %s', self.path)
        ink_files = locate('*.ink', self.path)
        edit_files = locate('*.edit', self.path)
        for f in itertools.chain(ink_files, edit_files):
            logger.debug("removing %s", f)
            os.remove(f)

    def close(self):
        Document.close(self)
        self.file.open() #we need to access parts of it and we are in-memory
