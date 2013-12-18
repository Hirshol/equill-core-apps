# Copyright 2011 Ricoh Innovations, Inc.
import wx, time, sys
from ew.util import ew_logging as log
from ds_calls import FauxDSServer
Display_Size = 825, 1200
Min_Partial_Points = 4

logger = log.getLogger('ew.faux_ds.display')

def pgm_to_bitmap(pgm_image):
    wxim = wx.EmptyImage(*pgm_image.size)
    imrgb = pgm_image.copy().convert('RGB')
    tstr = imrgb.tostring()
    wxim.SetData(tstr)
    wxb = wxim.ConvertToBitmap()
    del imrgb
    del tstr
    del wxim
    return wxb
    
class DisplayWindow(wx.Window):
    def __init__(self, parent, ID):
        wx.Window.__init__(self, parent, ID)
        self.SetBackgroundColour("WHITE")
        self.listeners = []
        self.thickness = 1
        self.SetColour("Black")
        self.lines = []
        self._seg_index = 0
        self.InitBuffer()
        self.SetCursor(wx.StockCursor(wx.CURSOR_PENCIL))
        self._ds = FauxDSServer.instance()
        self._ds.set_display(self)
        self.SetClientSize(Display_Size)
       
        # Hook some mouse events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)

        # the window resize event and idle events for managing the buffer
        #(sja) note that I probably don't want to allow resize. Figure how to
        # avoid it later
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        # and the refresh event
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        # When the window is destroyed, clean up resources.
        self.Bind(wx.EVT_WINDOW_DESTROY, self.Cleanup)

    def Cleanup(self, evt):
        if hasattr(self, "menu"):
            self.menu.Destroy()
            del self.menu
        FauxDSServer.instance().shutdown()

    def InitBuffer(self):
        """Initialize the bitmap used for buffering the display."""
        size = self.GetClientSize()
        self.buffer = wx.EmptyBitmap(max(1,size.width), max(1,size.height))
        dc = wx.BufferedDC(None, self.buffer)
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()
        self.DrawLines(dc)
        self.reInitBuffer = False


    def SetColour(self, colour):
        """Set a new colour and make a matching pen"""
        self.colour = colour
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        self.Notify()


    def SetThickness(self, num):
        """Set a new line thickness and make a matching pen"""
        self.thickness = num
        self.pen = wx.Pen(self.colour, self.thickness, wx.SOLID)
        self.Notify()


    def GetLinesData(self):
        return self.lines[:]


    def SetLinesData(self, lines):
        self.lines = lines[:]
        self.InitBuffer()
        self.Refresh()


    def OnLeftDown(self, event):
        """called when the left mouse button is pressed"""
        self.curLine = []
        self.line_start_time = time.time()
        self._seg_index = 0
        self.pos = event.GetPosition()
        self._send_line_points(start=True)
        self.CaptureMouse()


    def OnLeftUp(self, event):
        """called when the left mouse button is released"""
        if self.HasCapture():
            try:
                self._send_line_points(eol=True)
                self.lines.append( (self.colour, self.thickness, self.curLine) )
                self.curLine = []
            finally:
                self.ReleaseMouse()

    def OnMotion(self, event):
        """
        Called when the mouse is in motion.  If the left button is
        dragging then draw a line from the last event position to the
        current one.  Save the coordinants for redraws.
        """
        if event.Dragging() and event.LeftIsDown():
            dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
            #dc.SetMapMode(wx.MM_POINTS)
            dc.BeginDrawing()
            dc.SetPen(self.pen)
            pos = event.GetPosition()
            coords = (self.pos.x, self.pos.y, pos.x, pos.y)
            self.curLine.append(coords)
            if len(self.curLine) - self._seg_index > Min_Partial_Points:
                self._send_line_points()
            dc.DrawLine(*coords)
            self.pos = pos
            dc.EndDrawing()

    def OnSize(self, event):
        """
        Called when the window is resized.  We set a flag so the idle
        handler will resize the buffer.
        """
        self.reInitBuffer = True

    def OnIdle(self, event):
        """
        If the size was changed then resize the bitmap used for double
        buffering to match the window size.  We do it in Idle time so
        there is only one refresh after resizing is done, not lots while
        it is happening.
        """
        if self.reInitBuffer:
            self.InitBuffer()
            self.Refresh(False)

    def OnPaint(self, event):
        """
        Called when the window is exposed.
        """
        # Create a buffered paint DC.  It will create the real
        # wx.PaintDC and then blit the bitmap to it when dc is
        # deleted.  Since we don't need to draw anything else
        # here that's all there is to it.
        dc = wx.BufferedPaintDC(self, self.buffer)

    def DrawLines(self, dc):
        """
        Redraws all the lines that have been drawn already.
        """
        dc.BeginDrawing()
        for colour, thickness, line in self.lines:
            pen = wx.Pen(colour, thickness, wx.SOLID)
            dc.SetPen(pen)
            for coords in line:
                dc.DrawLine(*coords)
        dc.EndDrawing()

    # Observer pattern.  Listeners are registered and then notified
    # whenever doodle settings change.
    def AddListener(self, listener):
        self.listeners.append(listener)

    def Notify(self):
        for other in self.listeners:
            other.Update(self.colour, self.thickness)

    def on_next(self):
        self._ds.next_page()

    def on_prev(self):
        self._ds.prev_page()

    def _change_ink_to(self, ink):
        self.lines = ink
        self._new_index = len(self.lines)

    def clear_ink(self):
        self.lines = []

    def _segments_to_points(self, segments):
        points = []
        for seg in segments:
            x1, y1, x2, y2 = seg
            p1, p2 = (x1,y1), (x2,y2)
            if points:
                points.append(p2)
            else:
                points = [p1, p2]
        return points

    def on_close_document(self):
        self.lines = []
        self._seg_index = 0
    
    def _send_line_points(self, start=False, eol=False):
        millis = int (1000 *(time.time() - self.line_start_time))
        logger.debug('_send_line_points total segs: %d, index: %d ',
                     len(self.curLine), self._seg_index)
        points = [self.pos.Get()] if start else \
                 self._segments_to_points(self.curLine[self._seg_index:])
        if eol and not points:
            points = [self.pos.Get()]
        logger.debug('points = %s', points)
        index = len(self.lines)
        self._ds.handle_points(index, millis, points, start= start, end=eol)
        self._seg_index = 0 if eol else len(self.curLine)
        
    def get_new_ink(self):
        """returns all ink since the page was drawn.
        NOTE: self.curLine is the stroke under construction and
        is not yet in self.lines"""
        pass
    
    def draw_page(self, page_image, ink = None):
        self._change_ink_to(ink)
        self.update_region(self, (0,0), page_image)
    
    def update_region(self, location, pil_image):
        bitmap = pgm_to_bitmap(pil_image)
        dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
        dc.BeginDrawing()
        dc.DrawBitmap(bitmap, *location)
        self.DrawLines(dc)
        dc.EndDrawing()
        
#----------------------------------------------------------------------

class DisplayFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "DS Emulator", size=Display_Size,
                         style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        self._display = DisplayWindow(self, -1)

#----------------------------------------------------------------------

if __name__ == '__main__':
    app = wx.PySimpleApp()
    frame = DisplayFrame(None)
    frame.Show(True)
    import threading
    if 'all_in_one' in sys.argv:
        from ew.launcher import runner
        run_launcher = threading.Thread(name='DocumentRunner', target=runner.main)
        run_launcher.setDaemon(True)
        run_launcher.start()
    app.MainLoop()

