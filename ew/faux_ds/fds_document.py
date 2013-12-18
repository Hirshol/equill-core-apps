# Copyright 2011 Ricoh Innovations, Inc.
from ew.memphis.file import MemphisFile
from fds_page import FDSPage

class FDSDocument:
    def __init__(self, doc_path):
        self.path = doc_path
        self._memphis = MemphisFile(doc_path)
        self._memphis.open()
        self._pages = []
        self._page_map = {}
        self.wrap_pages()

    def page_by_id(self, page_id):
        return self._page_map.get(page_id)
    
    def page_by_index(self, index):
        return self._pages[index]

    def wrap_pages(self):
        for mpage in [self._memphis.page(m) for m in self._memphis.pages]:
            page = FDSPage(self, mpage, len(self._pages))
            self._pages.append(page)
            
            self._page_map[page.identity()] = page

    def insert_page(self, page_id, before_id=None):
        """expects that a Memphis page with the given id now exist at proper
        place in the pagelist and with a corresponding image and directory"""
        mpage = self._memphis.page(page_id)
        index = self._memphis
        if mpage:
            index = len(self.pages)
            before = self.get_page_by_id(before_id) if before_id else None
            index = before._index if before else len(self.pages)
                
            page = FDSPage(self, mpage, index)
            self._page_map[page.page_id] = page
            if before:
                for page in self._pages[index:]:
                    page._index += 1
            self._pages.insert(index, page)

    def delete_page(self, page_id):
        page = self.get_page_by_id(page_id)
        if page:
            index = page._index
            for page in self._pages[index+1:]:
                page._index += -1
            self._pages.pop(index)
    
    def handle_camera(self, image):
        pass
    
    def handle_submit(self):
        self.send('on_submit', self._doc_path)

    def close(self):
        self._memphis.close()

