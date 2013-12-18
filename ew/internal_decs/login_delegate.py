#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
import os, itertools
from sdk.delegate import Dec
from ew.util import locate
from ew.util import ew_logging
from ew.internal_decs.login_class import LoginMain


logger = ew_logging.getLogger('ew.internal_decs.login_delegate')

class LoginDelegate(Dec):

    def on_submit(self):
        return False

    def on_first_load(self):
        pass
                
    def on_button_press(self, *args):
        image_button = args[0]
        logger.debug("Pressed button %r", image_button.name)
        self.go_to_page(image_button.name)

    def on_load(self):
        self.document().mask_strokes(True)
        
    def on_close(self):
        self.remove_strokes()

    def on_page_entry(self, doc_page):
        logger.debug('on_page_entry for %s', doc_page.page_id)
        Dec.on_page_entry(self, doc_page)
        doc_page._document._runner._infobar.disable()
        if True:
            self.doc_page = doc_page
            page_class = self.get_page_class(doc_page.page_id)
            page_class.instance().on_page_entry(self, doc_page)
            #self.doc_page.display(True)

    def on_page_exit(self, doc_page):
        page_class = self.get_page_class(doc_page.page_id)
        page_class.instance().on_page_exit()

    def go_to_page(self, page_id):
        if page_id:
            self.document().go_to_page(page_id)
            page_class = self.get_page_class(page_id)
            page = self.document().find_page(page_id)
            page_class.instance().on_entry(page)

    def get_page_class(self, page_id):
        page_classes = dict(login=LoginMain)
        page_id = page_id.replace('.pgm', '')
        return page_classes[page_id]

    def on_login(self, *args):
        LoginMain.instance().on_login()

    def on_select(self, *args):
        page_class = self.get_page_class(self.doc_page.page_id)
        page_class.instance().on_select(*args)

    def remove_strokes(self):
        path = self.document().path
        logger.debug('removing stokes in %s', path)
        ink_files = locate('*.ink', path)
        edit_files = locate('*.edit', path)
        for f in itertools.chain(ink_files, edit_files):
            if os.path.exists(f):
                logger.debug("removing %s", f)
                os.remove(f)