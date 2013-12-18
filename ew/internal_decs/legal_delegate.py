#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
import os, itertools
from sdk.delegate import Dec
from ew.util import locate
from ew.util import ew_logging


logger = ew_logging.getLogger('ew.internal_decs.legal_delegate')

class LegalDelegate(Dec):

    def on_submit(self):
        return False

    def on_first_load(self):
        pass

    def on_load(self):
        self.document().mask_strokes(True)

    def on_close(self):
        self.remove_strokes()

    def on_page_entry(self, doc_page):
        Dec.on_page_entry(self, doc_page)
#        self.doc_page = doc_page
#        logger.debug('on_page_entry for %s', doc_page.page_id)
#        page = doc_page.gui_page()
#        navigation_widget = ImageButton("about", 36, 36, 
#                "default", "nav_home.pgm", widget_id="about")
#        navigation_widget.add_callback(self.on_hotspot, 
#                'on_button_press')
#        page.add(navigation_widget, SCREEN_SIZE[0]-navigation_widget.w*2, 
#                SCREEN_SIZE[1]-navigation_widget.h*2)

    def on_page_exit(self, doc_page):
        pass
    
#    def on_hotspot(self, *args):
#        self.doc_page._document.launcher().load_document(
#                os.path.join(system_config.internal_decs, 
#                'Settings_Document.memphis'))
#        self.doc_page._document.go_to_page("about")

    def remove_strokes(self):
        path = self.document().path
        logger.debug('removing stokes in %s', path)
        ink_files = locate('*.ink', path)
        edit_files = locate('*.edit', path)
        for f in itertools.chain(ink_files, edit_files):
            if os.path.exists(f):
                logger.debug("removing %s", f)
                os.remove(f)
