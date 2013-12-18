#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
from ew.internal_decs import TEMPLATES_DOC_ID
from ew.internal_decs.chooser_document import ChooserDocument, ChooserDelegate
from ew.internal_decs.template_item_panel import TemplateItemPanel
from ew.util import comms, ew_logging, system_config, standard_doc_path, standard_date
from templates_page import TemplatesPage, TemplateHeader1, TemplateHeader2
from sdk.widgets import known_widgets, add_widget_class
import os, time, random, threading, uuid
import ew.memphis.file as mfile
from ew.internal_decs.inbox_item_panel import InboxItemPanel as IP

logger = ew_logging.getLogger('ew.internal_decs.templates_document')

class TemplatesDelegate(ChooserDelegate):
    def __init__(self, document):
        ChooserDelegate.__init__(self, document)

    def ensure_widgets_known(self):
        self.ensure_widget_classes_known(TemplatesPage,TemplateItemPanel, TemplateHeader1, TemplateHeader2)

    def instantiate_template(self, widget):
        self._document.instantiate_template(widget)

class TemplatesDocument(ChooserDocument):
    _delegate_class = TemplatesDelegate
    @classmethod
    def document_path(cls):
        return os.path.join(system_config.internal_decs, TEMPLATES_DOC_ID)

    def __init__(self, path, **kwargs):
        ChooserDocument.__init__(self, path, 'templates',
                                 TemplatesPage, TemplateItemPanel,
                                 **kwargs)
        self.server = None

    def item_info_for_memphisfile(self, path):
        info = ChooserDocument.item_info_for_memphisfile(self, path)
        info['inst_date'] = ''
        return info

    def new_docid_from_template(self, template_title):
        return uuid.uuid4().hex

    def instantiate_template(self, widget):
        def get_title(path, doc_id):
            with mfile.MemphisFile(path) as mf:
                title = mf.metadata.get('memphis.title', None)
                if not title:
                    title = doc_id
                    mf.info['memphis.title'] = title
            return title
        dst_id = str(uuid.uuid4().hex)
        dst_path = standard_doc_path(dst_id)
        template_doc_id = widget.metadata()['id']
        src_path = standard_doc_path(template_doc_id, subdir='templates')
        title = get_title(src_path, template_doc_id) #for side effect of insuring source has a title
        logger.debug('instantiating template with title %s', title)
        logger.debug('new docid = %s, doc_path = %s', dst_id, dst_path)
        from shutil import copytree, ignore_patterns
        copytree(src_path, dst_path, ignore=ignore_patterns('*.pyo','*.pyc'))
        self._runner.immediately_add_to_inbox(dst_id)
        self.listings_updater().tablet_instantiated_template(template_doc_id, dst_id)
        self._runner.load_document(str(dst_path))

    def on_load(self):
        ChooserDocument.on_load(self)
        #self.listings_updater().set_templates_open(True)

    def add_template(self, docid):
        with self._instance_lock:
            widget,_ = self.widget_with_id(docid)
            if widget and widget.is_downloading():
                widget.set_downloading(False)
            else:
                self.add_widget_for_docid(docid)
            if not self.is_loaded():
                self.save_page_changes()

    def remove_template(self, docid):
        with self._instance_lock:
            self.remove_widget_for_docid(docid)
            if not self.is_loaded():
                self.save_page_changes()


    def close(self):
        logger.debug("templates close got called")
        ChooserDocument.close(self)
        #self.listings_updater().set_templates_open(False)
