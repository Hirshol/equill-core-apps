#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.

import os, sys, glob, shutil
from ew.internal_decs.chooser_document import ChooserDocument, ChooserDelegate
from inbox_page import InboxPage, InboxHeader1, InboxHeader2
from ew.internal_decs.inbox_item_panel import InboxItemPanel, InboxPanelWithSelect
from ew.util import system_config, ew_logging, standard_doc_path


from ew.internal_decs import INBOX_DOC_ID
from ew.util import system_config as sysconfig
from sdk.document import Document
from sdk.display import Display

logger = ew_logging.getLogger('ew.internal_decs.inbox_document')


def has_software_update():
    # ##################################################
    # If there is a .tar file waiting in /xtra, set the
    # build waiting parameter.
    if os.path.exists("/xtra") and len(glob.glob1("/xtra","*.tar")) == 1:
        logger.debug('Tablet has an update waiting. Showing update button.')
        return True
    else:
        return False

class InboxDelegate(ChooserDelegate):
    def __init__(self, document):
        ChooserDelegate.__init__(self,document)

    def ensure_widgets_known(self):
        logger.debug('InboxDelegate.ensure_widgets_known')
        self.ensure_widget_classes_known(InboxPage, InboxItemPanel,
                                         InboxPanelWithSelect,
                                         InboxHeader1, InboxHeader2)

    def on_select(self, widget):
        self._document.on_select(widget)

    def update_software(self, widget):
        self._document.update_software(widget)

    def delete_selected(self, widget):
        self._document.delete_selected()
        
class InboxDocument(ChooserDocument):
    _delegate_class = InboxDelegate

    @classmethod
    def document_path(cls):
        return os.path.join(system_config.internal_decs, INBOX_DOC_ID)

    def __init__(self, path, **kwargs):
        self.tablet_update_available = has_software_update()
        ChooserDocument.__init__(self, path, 'inbox',
                                 InboxPage, InboxPanelWithSelect,
                                 **kwargs)

    def refresh(self):
        ChooserDocument.refresh(self)
        self.tablet_update_available = has_software_update()

    def delete_selected(self):
        selected = [w for w in self.doc_widgets if w.is_selected]
        if not selected:
            logger.debug("nothing was selected to delete")
            self._delegate.inform_user("Nothing was selected to delete")
            return

        text = 'Are you sure you want to delete the selected documents?'


        should_delete = self._delegate.query_user(text)
        if selected and should_delete:
            with self._instance_lock:
                left = [w for w in self.doc_widgets if w not in selected]
                self.doc_widgets = left
                self.reflow_widgets(0) #could be made slightly more efficient
                for docid in [w.doc_id for w in selected]:
                    path = standard_doc_path(docid, self._subdir)
                    if os.path.isdir(path):
                        self.listings_updater().tablet_deleted_document(docid)
                        shutil.rmtree(path)
            
    
    def on_select(self, item_widget):
        """
        Close myself down and tell the launcher to load the
        document the widget refers to
        """
        doc_id = item_widget.metadata()['id']
        open_it = True
        error = item_widget.error_status()
        if error:
            text = 'The following error previously occurred on this document. Open it anyway? \n\n'
            text += error
            open_it = self._delegate.query_user(text)

        if not open_it: return

        #I need the path
        logger.debug('calling launcher to load document %s', doc_id)
        if not (item_widget.is_downloading() or item_widget.is_being_submitted()):
            #self.listings_updater().set_inbox_open(False)
            item_widget.set_status(item_widget.Status.modified)
            self.launcher().load_document(Document.standard_doc_path(doc_id))

    def update_software(self, widget):
        logger.debug('A software update has been downloaded and the user says to apply it')
        path = os.path.join(sysconfig.system_home, 'bin', 'upgrade.py')
        if os.path.isfile(path):
            import subprocess as sub
            pipe = sub.PIPE
            sub.Popen([sys.executable, path], stdout=pipe, stdin=pipe, stderr=pipe)

    def on_load(self):
        ChooserDocument.on_load(self)
        #self.listings_updater().set_inbox_open(True)

    def add_document(self, docid):
        with self._instance_lock:
            widget,_ = self.widget_with_id(docid)
            if widget:
                if widget.is_downloading():
                    widget.set_downloading(False)
                    widget.set_status(widget.Status.new)
                else:
                    path = standard_doc_path(docid, self._subdir)
                    info = self.item_info_for_memphisfile(path)
                    widget.set_fields(info) #reset from actual document
                    widget.redraw_containing_page()
            else:
                self.add_widget_for_docid(docid)
            if not self.is_loaded():
                self.save_page_changes()

    def remove_document(self, docid):
        with self._instance_lock:
            self.remove_widget_for_docid(docid)
            if not self.is_loaded():
                self.save_page_changes()

    def close(self):
        ChooserDocument.close(self)
        #self.listings_updater().set_inbox_open(False)

    def mark_modified_if_new(self, docid):
        logger.debug('attempting to mark widget for docid %s as modified', docid)
        widget,_ = self.widget_with_id(docid)
        logger.debug('found widget %r for docid %s', widget, docid)
        if widget:
            if widget.status == widget.Status.new:
                logger.debug('marking %r as modified', widget)
                widget.set_status(widget.Status.modified)
        else:
            logger.debug('no widget for docid %s', docid)

    def change_document_status(self, docid, newstatus):
        widget,_ = self.widget_with_id(docid)
        if widget:
            widget.set_status(newstatus)
            logger.debug('updating widget[%s].status to %s', docid, newstatus)
            widget.containing_page().document_page.save_changes_to_disk()
        else:
            logger.debug('could not find widget[%s]', docid)


