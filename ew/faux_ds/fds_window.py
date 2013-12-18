# Copyright 2011 Ricoh Innovations, Inc.
from ew.util import ew_logging as log

logger = log.getLogger('faux_ds.ds_calls')

class FDSWindow:
    """Superclass of display surfaces (pages and overlays) that may process
    strokes and perhaps ink"""

    def __init__(self, identity):
        self._ink = None
        self._identity = identity
        self._widget_map = None
        from ds_calls import FauxDSServer
        self._ds = FauxDSServer.instance()

    def screen_location(self, local_location):
        return local_location

    def relative_location(self, screen_location):
        return screen_location
    
    def set_ink(self, ink):
        self._ink = ink

    def identity(self):
        return self._identity

    def adjusted_points(self, index, points):
        #depending on policy we will do different things here for overlay case
        #standard case is just to keep all points and no adjustment
        return points
    
    def set_widget_map(self, widget_map):
        self._widget_map = widget_map

    def _handle_points(self, index, flags, millis, points):
        """take points or segments, convert to point list possibly
        translated if self is overlay. Send on_stroke message.  If
        a widget map is present send and on_widgets_stoked."""
        filtered_pts = self._filtered_outbound_points(points)
        if self._widget_map:
            widgets = self._widget_map.intersected_widgets(filtered_pts)
            flags = self._ink.flags()
            if widgets:
                self._ds.send.on_widgets(flags, widgets)
        else:
            self._ds.send.on_stroke(flags, filtered_pts)
            

    
