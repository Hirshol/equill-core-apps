from sdk.document import Document
from sdk.doc_page import DocumentPage
from sdk.widgets.page import Page 

from ew.util import ew_logging as log

logger = log.getLogger('ew.internal_decs.login_document')

class LoginPage(DocumentPage):
    def __init__(self, document, page_index, memphis_page):
        DocumentPage.__init__(self, document, page_index, memphis_page)
        self.gui_filled_in = False       
        self._gui = Page()
        self._gui.document_page = self

    def on_entry(self):
        #self.use_blank_clean_image()
        logger.debug('special provision page on_entry for page %s', self.page_id)
        self._delegate.on_page_entry(self)
        self._gui.activate(process_changes=True)
        if self._document.did_jump:  
            self._document.did_jump = False
            self._gui.micro_update()

    def unload_gui(self):
        self._gui.on_unload()

    def load_gui(self):
        pass

    def save_changes_to_disk(self, force_save=False, closing=False):
        pass

class LoginDocument(Document):
    def __init__(self, path, page_class=LoginPage,**kwargs):
        Document.__init__(self, path, page_class=page_class, **kwargs)
        self.mask_strokes(True)

    def refresh(self):
        logger.debug('Login document refresh called')