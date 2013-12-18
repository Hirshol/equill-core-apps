# Copyright 2011 Ricoh Innovations, Inc.
from sdk.bounding_box import BoundingBox
from fds_window import FDSWindow
from ew.util import ew_logging

logger = ew_logging.getLogger('ew.faux_ds.overlay')

def level_compare(overlay1, overlay2):
    return cmp(overlay1.level, overlay2.level)

class FDSOverlay(FDSWindow):
    def __init__(self, name, position, image):
        self._image = image
        self._name = name
        self.level = 0
        self._position = position
        (x,y),(w,h) = self._position, self._image.size
        self._box = BoundingBox.from_bbox((x,y,w,h))
        self._drop_if_index = -1

    def __repr__(self):
        return 'Overlay[%s] at %s of size %s' % (\
            self._name, self._position, self._image.size)
    
    def identity(self):
        return self._name

    def update_region(self, dest, image):
        w, h = image.size
        x, y = dest
        x0, y0 = self._position
        if ((x0 + w) <= self._box.x_max) and ((y0 + h) <= self._box.y_max):
            self._image.paste(image, dest)
        else:
            logger.error('modifying overlay %r with image(loc,size) %s is out of bounds %r', self, (x,y,w,h), self._box)

    def screen_location(self, local_location):
        return local_location[0] + self._position[0], \
               local_location[1] + self._position[1]

    def relative_location(self, screen_location):
        return screen_location[0] - self._position[0], \
               screen_location[1] - self._position[1]

    def get_image(self):
        return self._image
    
    def filtered_outbound_points(self, points):
        x, y = self._position
        return [(p[0] - x, p[1] - y) for p in points]

    def contains_point(self, point):
        logger.debug('%s contains_point %s in %s',
                     self.identity(), point, self._box)
        return self._box.contains_point(point)
        
    def adjusted_points(self, index, points):
        #if clipping as close as possible we would change last segment leaving
        #to closest to edge. Cheap version here simply drops starting at 1st
        #out of bounds point and remembers this state by stroke index.
        inbounds = []
        if index != self._drop_if_index:
            self._drop_if_index = -1
            for p in points:
                if not self._box.contains_point(p):
                    self._drop_if_index = index
                    break
                inbounds.append(p)
        return inbounds

    def close(self):
        del self._image

    def bounding_box(self):
        return self._box
        
