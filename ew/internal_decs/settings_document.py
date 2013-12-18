from settings_delegate import SettingsDelegate
from sdk.document import Document
from sdk.doc_page import DocumentPage
from sdk.widgets.page import Page 

from ew.util import ew_logging as log

logger = log.getLogger('ew.internal_decs.settings_document')

class SettingsPage(DocumentPage):
    def __init__(self, document, page_index, memphis_page):
        DocumentPage.__init__(self, document, page_index, memphis_page)
        self.gui_filled_in = False
        self._gui = Page()
        self._gui.document_page = self
        self._has_gui = True

    def on_entry(self):
        self.use_blank_clean_image()
        logger.debug('special settings page on_entry for page %s', self.page_id)
        self._delegate.on_page_entry(self)
        self.gui_page().activate(process_changes=True) #should have already drawn them by now
        if self._document.did_jump:  
            self._document.did_jump = False
            self._gui.micro_update()

    def gui_page(self):
        if not self._gui:
            self._gui = Page(widget_id = self.identity())
            self._gui.document_page = self
        return self._gui

    def unload_gui(self):
        self._gui.on_unload()
        self.drop_gui()

    def load_gui(self):
        pass #interal dec will do this

    def save_changes_to_disk(self, force_save=False, closing=False):
        pass #never do this for settings pages

class SettingsDocument(Document):
    def __init__(self, path, page_class=SettingsPage,**kwargs):
        Document.__init__(self, path, page_class=page_class, **kwargs)
        self._mask_strokes = True

    def refresh(self):
        logger.debug('settings document refresh called')
        #self.set_current_page(self.pages[0])
