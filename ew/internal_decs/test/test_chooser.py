# Copyright 2011 Ricoh Innovations, Inc.
from ew.internal_decs.chooser_document import ChooserDocument
from ew.internal_decs.chooser_page import ChooserPage
from ew.internal_decs.inbox_item_panel import InboxItemPanel
import unittest, os, shutil
from ew.util import system_config, standard_doc_path
from sdk.document import Document
from sdk.widgets import add_widget_class_if_missing

class TestChooserPage(ChooserPage):
    def __init__(self, document, index, memphis_page, **kwargs):
        ChooserPage.__init__(self, document, index, memphis_page, 
                             panel_class=InboxItemPanel, headers=[])
 
class TestChooserDoc(ChooserDocument):

    def __init__(self, path, subdir, **kwargs):
        add_widget_class_if_missing(InboxItemPanel)
        ChooserDocument.__init__(self, path, subdir, TestChooserPage, InboxItemPanel, **kwargs)
    
    def on_select(self, item_widget):
        pass

#    def find_item_index(self, docid):
#        """for these test we always want to add to the end"""
#        return len(self.doc_widgets)

test_dir = os.path.join('test', 'chooser_doc')
subdir = os.path.join(test_dir, 'data')
doc_path = standard_doc_path('TestChooserDoc', test_dir)
doc_dir = os.path.join(system_config.data_home, subdir)

def ensure_dirs():
    if not os.path.isdir(doc_dir):
        os.makedirs(doc_dir)
    
def create_document(docid):
    ensure_dirs()
    doc = Document(standard_doc_path(docid, subdir))
    doc.add_page()
    doc.close()
    print "foo"

def make_doc(docid):
    ensure_dirs()
    doc = Document(standard_doc_path(docid, subdir))
    if not doc.pages:
        doc.add_page()
    doc.close()

def remove_document_on_disk(docid):
    path = standard_doc_path(docid, subdir)
    if os.path.isdir(path):
        shutil.rmtree(path)

def remove_all_documents():
    if os.path.isdir(doc_dir):
        shutil.rmtree(doc_dir)
        os.mkdir(doc_dir)

class TestChooser(unittest.TestCase):
    def open_doc(self):
        self.doc = TestChooserDoc(doc_path, subdir)
        
    def setUp(self):
        print "setting up"
        #create_document('A')
        make_doc('A')
        print "created A"
        #create_document('B')
        make_doc('B')
        print "created B"
        #create_document('C')
        make_doc('C')
        print "created C"
        self.open_doc()

    def tearDown(self):
        self.doc.close()
        remove_all_documents()
        shutil.rmtree(doc_path)

    def test_documents_seen(self):
        self.widget_count_location_test(3)
        self.doc_ids_test('A', 'B', 'C')

    def doc_ids_test(self, *docids):
        for docid in docids:
            self.assertTrue(docid in self.doc.widget_index)

    def widget_count_location_test(self, count):
        locations = self.doc.page_class.widget_pane_locations()
        self.assertTrue(len(self.doc.doc_widgets) == count)
        page = self.doc.pages[0]
        self.assertTrue(len(page.chooser_panes) == count, 'chooser panes %s' % [(p.doc_id,i) for p,i in page.chooser_panes])
        for i in range(count):
            widget = self.doc.doc_widgets[i]
            docid = widget.doc_id
            self.assertTrue(self.doc.widget_index[docid] == i)
            self.assertTrue(widget.y == locations[i][1], 'y value was %d in location %d of %s' % (widget.y, i, locations))  #no gaps or reordering
            
        
    def doc_init_cleanup(self):
        self.doc.load_main_widgets()
        self.doc.check_initial_state()

    def gen_remove_test(self, index, remove_function, rerun_init = True):
        """remove one item, close, open, test expectations"""
        self.assertTrue(len(self.doc.doc_widgets) > index)
        docids = [w.doc_id for w in self.doc.doc_widgets]
        docid = docids[index]
        self.assertTrue(docid in self.doc.widget_index)
        remove_function(docid)
        print 'orginal: %s docids: %s, indices %s, docid %s' % (docids, [w.doc_id for w in self.doc.doc_widgets], \
            self.doc.widget_index.keys(), docid)
        if rerun_init:
            self.doc_init_cleanup()
        self.widget_count_location_test(2)
        self.assertFalse(docid in self.doc.widget_index)

    #next three tests remove a documents file and reinitialize the ChooserDoc
    def test_remove_first_file(self):
        self.gen_remove_test(0, remove_document_on_disk)

    def test_remove_middle_file(self):
        self.gen_remove_test(1, remove_document_on_disk)

    def test_remove_last_file(self):
        self.gen_remove_test(2, remove_document_on_disk)

    #next three tests tell the ChooserDoc to remove a document
    def test_remove_first(self):
        func = self.doc.remove_widget_for_docid
        self.gen_remove_test(0, func, rerun_init=False)

    def test_remove_middle(self):
        func = self.doc.remove_widget_for_docid
        self.gen_remove_test(1, func, rerun_init=False)

    def test_remove_last(self):
        func = self.doc.remove_widget_for_docid
        self.gen_remove_test(2, func, rerun_init=False)

    def dup_at_position_test(self, index):
        docid = self.doc.doc_widgets[index].doc_id
        #bypass the checks against adding duplication widgets
        path = standard_doc_path(docid, subdir)
        info = self.doc.item_info_for_memphisfile(path)
        self.doc.add_item(info)
        #do our standard startup cleansing
        self.doc_init_cleanup()
        #run checks that the dup was removed
        self.widget_count_location_test(3)
        self.doc_ids_test('A', 'B', 'C')


    def test_cleanup_dups(self):
        for i in range(3):
            self.dup_at_position_test(i)

    def test_adding_dup_blocked(self):
        self.doc.add_widget_for_docid('A')
        self.widget_count_location_test(3)
        self.doc_ids_test('A', 'B', 'C')
        

    
if __name__ == "__main__":
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (-1, -1))
    if os.path.isdir(doc_path):
       shutil.rmtree(doc_path)
    print "testing Inbox/Template base classe..\n"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestChooser)
    unittest.TextTestRunner(verbosity=2).run(suite)


        
        



        
