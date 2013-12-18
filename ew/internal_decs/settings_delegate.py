#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.
import os, itertools
from sdk.delegate import Dec
from ew.util import locate
from ew.util import ew_logging
from ew.internal_decs.settings_class import SettingsGeneral, SettingsNetwork, \
        SettingsAddNetwork, SettingsUser, SettingsTools, SettingsSoftwareUpdate, \
        SettingsAbout


logger = ew_logging.getLogger('ew.internal_decs.settings_delegate')

class SettingsDelegate(Dec):

    def on_submit(self):
        return False

    def on_first_load(self):
        pass
                
    def on_hotspot(self, *args):
        hotspot = args[0]
        logger.debug("Pressed button %r", hotspot)
        self.go_to_page(hotspot.widget_id)

    def on_load(self):
        pass

    def on_close(self):
        self.remove_strokes()

    def on_page_entry(self, doc_page):
        Dec.on_page_entry(self, doc_page)
        logger.debug('on_page_entry for %s', doc_page.page_id)
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
        page_classes = dict(general=SettingsGeneral, network=SettingsNetwork,
                add_network=SettingsAddNetwork, user=SettingsUser, 
                tools=SettingsTools, software_update=SettingsSoftwareUpdate,
                about=SettingsAbout)
        page_id = page_id.replace('.pgm', '')
        return page_classes[page_id]

    def on_airplane_mode(self, *args):
        SettingsGeneral.instance().on_airplane_mode(*args)
        
    def on_sound_settings(self, *args):
        SettingsGeneral.instance().on_sound_settings(*args)

    def on_volume_change(self, *args):
        SettingsGeneral.instance().on_volume_change(*args)

    def on_open_add_network(self, *args):
        self.go_to_page('add_network')

    def on_wifi_settings(self, *args):
        SettingsNetwork.instance().on_wifi_settings(*args)

    def on_add_network(self, *args):
        SettingsAddNetwork.instance().on_add()
    
    def on_cancel_add_network(self, *args):
        self.go_to_page('network')
    
    def on_wifi_type(self, *args):
        SettingsAddNetwork.instance().on_wifi_type(*args)

    def on_delete_network(self, *args):
        SettingsNetwork.instance().on_delete(*args)

    def on_refresh_network(self, *args):
        SettingsNetwork.instance().on_refresh(*args)

    def on_open_license(self, *args):
        SettingsAbout.instance().on_open_license(*args)

    def on_open_regulatory(self, *args):
        SettingsAbout.instance().on_open_regulatory(*args)
    
    def on_open_legal(self, *args):
        SettingsAbout.instance().on_open_legal(*args)

    def on_calibrate(self, *args):
        SettingsTools.instance().on_calibrate(*args)

    def on_provision(self, *args):
        SettingsTools.instance().on_provision(*args)

    def on_install_update(self, *args):
        SettingsSoftwareUpdate.instance().on_install_update()

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
