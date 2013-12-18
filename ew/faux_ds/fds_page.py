# Copyright 2011 Ricoh Innovations, Inc.
from fds_window import FDSWindow
from PIL import Image

class FDSPage(FDSWindow):
    def __init__(self, document, memphis_page, index):
        self._document = document
        self._index = index
        self._memphis = memphis_page
        self.page_id = self._memphis.pagename
        FDSWindow.__init__(self, self.page_id.split('.')[0])
        self._dir = self._memphis.filepath.split('.pgm')[0] + '.d'
        self._image_path = self._dir.split('.d')[0] + '.pgm'
        self._image = None
        self._overlay_map = {}

    def get_image(self):
        if not self._image:
            self._image = Image.open(self._image_path).copy()
        return self._image
