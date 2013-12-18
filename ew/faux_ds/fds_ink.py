# Copyright 2011 Ricoh Innovations, Inc.
import time
Default_Pressure = 1

class FDSInk:
    class InkNode:
        def __init__(self, coords, timestamp=None, pressure = Default_Pressure):
            self.x, self.y = coords
            self.pressure = pressure
            if not timestamp:
                timestamp = time.time()

    class Stroke:
        def __init__(self, index, points):
            self._nodes = []
            self._index = index
            for p in points:
                self._nodes.append(self.InkNode(p))

        def add_points(self, points):
            for p in points:
                self._nodes.append(self.InkNode(p))

    def __init__(self, window):
        self._index = 0
        self._window = window
        self.strokes = []

    def add_stroke(self, points):
        self._index += 1
        stroke = self.Stroke(self._index, points)
        self._strokes.append(stroke)
        return stroke
