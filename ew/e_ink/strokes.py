#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.

"""
Watch strokes and map to events.

See README for information about trackupdate binaries used.

 - $Id$
 - $HeadURL$
"""

import time
import logging
import os
import sys

from ew.util import ew_logging

logger = ew_logging.getLogger('ew.e_ink.strokes')

ptu_tsscale = 16  # default is 16

def set_ptu_tsscale(n=None):
    """
    PTU_TSSCALE controls pentracking resolution, 1=EDO screen resolution,
    16=highest resolution.

    If n is None, set from PTU_TSSCALE environment variable.
    """
    if n is None:
        n = int(os.environ.get('PTU_TSSCALE', '16'))
    if (n < 1) or (n > 16):
        raise Exception ('PTU_TSSSCALE is %d, not in [0..16]' % n)
    global ptu_tsscale
    ptu_tsscale = n

try:
    set_ptu_tsscale() # try to set from enviroment
#    logger.debug("strokes.ptu_tsscale=%d" % ptu_tsscale)
except:
    pass

def get_ptu_tsscale():
    """
    PTU_TSSCALE controls pentracking resolution, 1=EDO screen resolution,
    16=highest resolution.
    """
    global ptu_tsscale
    return ptu_tsscale

def rotate_to_ts(xy):
    """
    Convert X,Y in EDO upright coordinates to touch screen/wacom coordinates
    (USB and LEDs at top).
    """
    global ptu_tsscale
    x, y = xy
    return y*ptu_tsscale, (825-x)*ptu_tsscale

def rotate_to_ts2(xy1_xy2):
    """
    Convert two pairs of XY points in EDO upright coordinates in to touch
    screen/wacom coordinates (USB and LEDs at top). XY1 remains top left,
    smaller and XY2 remains bottom right, bigger.
    """
    xy1, xy2 = xy1_xy2
    x1, y1 = rotate_to_ts(xy1)
    x2, y2 = rotate_to_ts(xy2)
    return ((x1, y2), (x2, y1))

def rotate_to_eink(xy):
    """
    Convert X,Y in touch screen/wacom coordinates
    (USB and LEDs at top) to EDO upright coordinates.
    """
    global ptu_tsscale
    x, y = xy
    return 825 - (y/ptu_tsscale), x/ptu_tsscale

def rotate_to_eink2(xy1_xy2):
    """
    Convert two pairs of XY points in touch screen/wacom coordinates
    (USB and LEDs at top) to EDO upright coordinates. XY1
    remains top left, smaller and XY2 remains bottom right, bigger.

    NOT DEBUGGED YET

    """
    xy1, xy2 = xy1_xy2
    x1, y1 = rotate_to_eink(xy1)
    x2, y2 = rotate_to_eink(xy2)
    return ((x1, y2), (x2, y1))

def scale_to_ts(xy):
    """
    Convert X,Y in EDO landscape / horizontal coordinates to touch
    screen/wacom coordinates (USB and LEDs at top on both input
    and output).
    """
    global ptu_tsscale
    x, y = xy
    return x * get_ptu_tsscale(), y * get_ptu_tsscale()

def scale_to_ts2(xy1_xy2):
    """
    Convert two pairs of XY points in EDO landscape / horizontal
    coordinates to touch screen/wacom coordinates (USB and LEDs at
    top on both input and output).
    """
    xy1, xy2 = xy1_xy2
    x1, y1 = scale_to_ts(xy1)
    x2, y2 = scale_to_ts(xy2)
    return ((x1, y1), (x2, y2))

class Strokes:
    """
    Watch strokes and map to events.

    self.live_strokes is a list of strokes.
    self.live_strokes[-1]['strokes'] is the list of points in the stroke.

    This object has a fileno() method, so it can be used
    with select.select and select.poll.
    """
    def __init__(self, **options):
        """

        options::
            verbose=True         Print debug messages.
            StrokeListener = {}  Options passed to Sparkle.StrokeListener.
            PyPenTrackUpdate={}  Options passed to Sparkle.PenTrackUpdate.
        """
        from StrokeListener import StrokeListener
        from PyPenTrackUpdate import PenTrackUpdate
        self.last_stroke_time = 0
        self.verbose = options.get('verbose')
        stroke_options = options.get('StrokeListener', {})
        if not stroke_options.has_key('verbose'):
            stroke_options['verbose'] = self.verbose
        self.stroke_listener = StrokeListener(**stroke_options)
        pentrack_options = options.get('PyPenTrackUpdate', {})
        if not pentrack_options.has_key('verbose'):
            pentrack_options['verbose'] = self.verbose
        self.pentrack = PenTrackUpdate(**pentrack_options)
        self.pentrack.enableStrokes(True)

        self.erase()

    def __del__(self):
        if self.verbose:
            print "Strokes.__del__()"
        self.pentrack.enableStrokes(False)

    def erase(self):
        """
        Clear list of strokes.
        """
        self.live_strokes = []
        self.already_grouped = 0

    def fileno(self):
        """
        fileno() allows this object to be used with select.select and
        select.poll.
        """
        return self.stroke_listener.fileno()

    def get_stroke(self, s=None):
        """
        If new stroke is available, computer bounding box and other
        information, add stroke to self.live_strokes and return dict
        describing stroke. dict['strokes'] is list of points in stroke.
        Return None if no new stroke is available.
        """
        import StrokeListener
        if not s:
            s = self.stroke_listener.get_stroke()
        if not s:
            return None
        self.last_stroke_time = time.time()
        if StrokeListener.PROTOCOL_VER == "2008a":
            frame, _, _, _, strokes, binary = s
        else:
            frame, _, status, _, strokes, binary = s
        # filter out invalid strokes that have negative coordinates
        strokes = [i for i in strokes if (i[0] >= 0) and (i[1] >=0)]
        if not strokes:
            return None
        cur = {}
        cur['strokes'] = strokes
        cur['xmin'] = min([i[0] for i in strokes])
        cur['xmax'] = max([i[0] for i in strokes])
        cur['xcenter'] = (cur['xmin'] + cur['xmax']) / 2
        cur['ymin'] = min([i[1] for i in strokes])
        cur['ymax'] = max([i[1] for i in strokes])
        cur['ycenter'] = (cur['ymin'] + cur['ymax']) / 2
        cur['time'] = self.last_stroke_time
        cur['frame'] = frame
        cur['binary'] = binary
        if StrokeListener.PROTOCOL_VER != "2008a":
            cur['pen'] = (status & 0x01) != 0
            cur['eraser'] = (status & 0x02) != 0
            cur['stylus'] = (status & 0x04) != 0
        self.live_strokes.append(cur)
        return cur

    def is_erase(self, stroke):
        """Return true if stroke is an eraser stroke"""
        return stroke and stroke['eraser']

    def match_for_erase(self, erase_stroke, other_strokes):
        """
        Find other_strokes that intersect with erase_stroke.
        A threshold is used so that strokes do not have to
        intersect exactly.
        """
        global ptu_tsscale
        _ = erase_stroke['strokes']
        rval = []
        for index2, j in enumerate(other_strokes):
            if j and self.stroke_intersects(erase_stroke, j,
                                            threshold=5*ptu_tsscale):
                rval.append((index2, j))
        return rval

    def erase_with_other_end_of_pen(self, start, eink_sparkle):
        """
        Use 'other end of stylus' as an eraser.
        Find overlapping previous strokes.
        Tell Display Server to erase overlapping strokes and this
        stroke.
        Replace overlapping strokes and this stroke in
        self.live_strokes with None.

        eink_sparkle is a EinkSparkle object from eink_sparkle.py

        Note that if this function is used, indices in
        self.live_strokes for particular strokes will not change,
        however, self.live_strokes will contain None entries. Take
        care to test for None before accessing a stroke::

            if self.live_strokes[-1]:
                a = self.live_strokes[-1]['strokes']

        """
        for index1, i in enumerate(self.live_strokes[start:]):
            if not self.is_erase(i):
                continue
            for index2, j in self.match_for_erase(
                i, self.live_strokes[:index1+start]):
                eink_sparkle.erase(j['frame'], j['frame'])
                self.live_strokes[index2] = None
            eink_sparkle.erase(i['frame'], i['frame'])
            self.live_strokes[index1+start] = None

    def label_strokes(self, start, areas):
        """
        Label strokes that are relevant to a particular
        area and have that area process them.
        areas is a list of dict.
        dict['maxsize'] = (x, y) to ignore strokes that are larger
        dict['minsize'] = (x, y) to ignore strokes that are smaller
        dict['tight'] = ((x0, y0), (x1, y1)) for certainly in area
        dict['loose'] = ((x0, y0), (x1, y1)) for possibly in area
        dict['intersects'] = ((x0, y0), (x1, y1)) for intersects with an area

        The following select based on the end of stylus or stylus button.
        dict['pen'] = True
        dict['eraser'] = False
        dict['stylus'] = True

        See also group_strokes for more dict items.
        This should be called after get_stroke() and before group_strokes().
        """

        for i in self.live_strokes[start:]:
            if not i:
                continue
            xmin = i['xmin']
            xmax = i['xmax']
            ymin = i['ymin']
            ymax = i['ymax']
            points = i['strokes']
            dx = xmax - xmin
            dy = ymax - ymin
            i['areas'] = []
            for j, a in enumerate(areas):

                # end of stylus or stylus button
                pen_flag = False
                for k in ['pen', 'erase', 'stylus']:
                    v = a.get(k)
                    if not v is None:
                        if v != i.get(k):
                            pen_flag = True
                            break
                if pen_flag:
                    continue

                xy = a.get('minsize')
                if xy:
                    x, y = xy
                    if dx < x:
                        continue
                    if dy < y:
                        continue
                xy = a.get('maxsize')
                if xy:
                    x, y = xy
                    if dx > x:
                        continue
                    if dy > y:
                        continue
                if self.in_rect(xmin, ymin, xmax, ymax, a.get('tight')):
                    i['areas'].append(('tight', j, a))
                elif self.in_rect(xmin, ymin, xmax, ymax, a.get('loose')):
                    i['areas'].append(('loose', j, a))
                elif self.intersects(points, a.get('intersects')):
                    i['areas'].append(('intersects', j, a))
                elif not (a.has_key('tight') or a.has_key('loose') or a.has_key('intersects')):
                    i['areas'].append(('anywhere', j, a))
        logger.debug('%d,%d -> %d,%d delta=%d,%d %s'
                          % (xmin,ymin, xmax,ymax,dx,dy,
                             str([j[:2] for j in i['areas']])))

    def intersects(self, points, rect):
        """
        Does any on the points in a stroke intersect a rectangle?
        """
        if not rect:
            return False
        xy0, xy1 = rect
        x0, y0 = xy0
        x1, y1 = xy1
        for px,py in points:
            if (px < x0): continue
            if (px > x1): continue
            if (py < y0): continue
            if (py > y1): continue
            return True
        return False

    def bb_intersects(self, stroke1, stroke2, **opts):
        """
        Do the bounding boxes for the strokes intersect?

        opts::
          threshold=0  >0 for looser, <0 for tighter
        """
        if not stroke1: return False
        if not stroke2: return False
        t = opts.get('threshold', 0)
        if stroke1['xmax'] < stroke2['xmin'] - t: return False
        if stroke1['xmin'] > stroke2['xmax'] + t: return False
        if stroke1['ymax'] < stroke2['ymin'] - t: return False
        if stroke1['ymin'] > stroke2['ymax'] + t: return False
        return True

    def stroke_intersects(self, stroke1, stroke2, **opts):
        """
        Do two strokes intersect? Based on bounding boxes
        of pairs of points in stroke.

        opts::
          threshold=0  >0 for looser, <0 for tighter
        """
        if not self.bb_intersects(stroke1, stroke2, **opts):
            return False
        points1 = stroke1['strokes']
        points2 = stroke2['strokes']
        t = opts.get('threshold', 0)
        for i in range(len(points1)-1):
            ix0, iy0 = points1[i]
            ix1, iy1 = points1[i+1]
            if ix0 > ix1: ix0, ix1 = ix1, ix0
            if iy0 > iy1: iy0, iy1 = iy1, iy0
            for j in range(len(points2)-1):
                jx0, jy0 = points2[j]
                jx1, jy1 = points2[j+1]
                if jx0 > jx1: jx0, jx1 = jx1, jx0
                if jy0 > jy1: jy0, jy1 = jy1, jy0
                flag = True
                if ix1 < jx0 - t:
                    flag = False ; continue
                if ix0 > jx1 + t:
                    flag = False ; continue
                if iy1 < jy0 - t:
                    flag = False ; continue
                if iy0 > jy1 + t: flag = False
                if flag:
                    return True
        return False

    def in_rect(self, xmin, ymin, xmax, ymax, rect, **opts):
        """
        Is bounding box for stroke in rect?
        opts::
          threshold=0  >0 for looser, <0 for tighter
        """
        if not rect:
            return False
        t = opts.get('threshold', 0)
        if t:
            xmin += t
            ymin += t
            xmax -= t
            ymax -= t
        xy0, xy1 = rect
        x0, y0 = xy0
        x1, y1 = xy1
        if ymin < y0: return False
        if ymax > y1: return False
        if xmin < x0: return False
        if xmax > x1: return False
        return True

    def in_stroke_bb(self, x, y, stroke_dict, **opts):
        """
        Is point x,y in bounding box for stroke?

        opts::
          threshold=0  >0 for looser, <0 for tighter
        """
        t = opts.get('threshold', 0)
        if x < stroke_dict['xmin']+t: return False
        if x > stroke_dict['xmax']-t: return False
        if y < stroke_dict['ymin']+t: return False
        if y > stroke_dict['ymax']-t: return False
        return True

    def group_strokes(self):
        """
        Group strokes that are relevant to a particular
        area and have that area process them.
        Uses areas (a list of dict) from label_strokes::

          dict['group_max']=int  maximum number of strokes in group
          dict['group_min']=int  minimum number strokes in group
          dict['time_threshold']=float  wait this long for user to add more
                                        strokes to the group
          dict['callback']=func  function to call for group, return False/None
                                 to allow adding more strokes, True to
                                 not add more strokes

        This should be called after get_stroke() and label_stroke().
        """
        active = {}
        tight = {}
        save = {}
        nstrokes = len(self.live_strokes)
        for i in range(self.already_grouped, nstrokes):
            stroke = self.live_strokes[i]
            if not stroke:
                continue
            a = stroke['areas']
            found = []
            for j in a:
                # label in ['tight', 'loose', 'intersects']
                # index in range(len(areas))
                label, index, area = j
                group_max = area.get('group_max')
                if group_max:
                    if (nstrokes-i) > group_max:
                        continue
                found.append(index)
                if not active.has_key(index):
                    active[index] = i
                    tight[index] = False
                    save[index] = area
                if label == 'tight':
                    tight[index] = True
            last = False
            if i == nstrokes-1:
                last = True
                age = time.time() - self.last_stroke_time
            for j in active.keys():
                if (not j in found) or last:
                    if last:
                        time_threshold = save[j].get('time_threshold')
                        if time_threshold:
                            if age < time_threshold:
                                continue
                    end_i = i
                    if last:
                        end_i = i + 1
                    # print "End field", j, active[j], end_i
                    callback = save[j].get('callback')
                    if callback:
                        rval = callback(
                               save[j], active[j], end_i, self.live_strokes)
                    if rval or not last:
                        del active[j]
        n = len(self.live_strokes)
        for v in active.values():
            n = min(n, v)
        self.already_grouped = n

    def group_is_x(self, area, start_idx, end_idx, strokes):
        """
        Detector for 'Draw and "X"'.
        """
        # print area, start_idx, end_idx, strokes[:-1]
        verbose = self.verbose
        if verbose:
            print "group_is_x"
        if (end_idx > 1) and (end_idx <= len(strokes)):
            s1 = strokes[end_idx-2]
            s2 = strokes[end_idx-1]
            # if verbose: print 'S1', s1
            # if verbose: print 'S2', s2
            # if verbose: print 'AREA', area
            if verbose:
                print 'S1 min/max', s1['xmin'], s1['ymin'], ':', s1['xmax'], s1['ymax']
                print 'S2 min/max', s2['xmin'], s2['ymin'], ':', s2['xmax'], s2['ymax']
                print 'S1 start/end', s1['strokes'][0], s1['strokes'][-1]
                print 'S2 start/end', s2['strokes'][0], s2['strokes'][-1]
            # Detect drawing an X
            if not area in [i[2] for i in s1['areas']]:
                if verbose: print 'Previous stroke not in same area'
                return

            if not self.in_stroke_bb(
                s1['xcenter'], s1['ycenter'], s2, threshold=-3):
                if verbose: print "Center 1 not in BB 2"
                return

            if not self.in_stroke_bb(
                s2['xcenter'], s2['ycenter'], s1, threshold=-3):
                if verbose: print "Center 2 not in BB 1"
                return

            # An X has one endpoint in each of four quandrants
            xc = (s1['xcenter'] + s2['xcenter']) / 2
            yc = (s1['ycenter'] + s2['ycenter']) / 2
            if self.verbose: print "Center", xc, yc
            quadrant_list = []
            dist_list = []
            for x, y in [s1['strokes'][0], s1['strokes'][-1],
                         s2['strokes'][0], s2['strokes'][-1]]:
                a = 0
                if x > xc:
                    a += 1
                    dist_list.append(x - xc)
                else:
                    dist_list.append(xc - x)
                if y > yc:
                    a += 2
                    dist_list.append(y - yc)
                else:
                    dist_list.append(yc - y)
                quadrant_list.append(a)
            if verbose: print quadrant_list
            if verbose: print dist_list
            for i in range(4):
                if quadrant_list.count(i) != 1:
                    if verbose: print "X endpoints", quadrant_list
                    return
            dist_list.sort()
            dmin = dist_list[0]
            dmax = dist_list[-1]
            dmid = dist_list[3]
            if dmin <= 2:
                if verbose: print "Min stroke distance from center:"
                return
            if dmax > 2*dmid:
                if verbose: print "Max > 2*mid distance from center"
                return
            if verbose: print "X detected"
            return True

def group_is_mark_in_box(self, area, start_idx, end_idx, strokes):
        # print area, start_idx, end_idx, strokes[:-1]
        verbose = self.verbose
        if verbose:
            print "group_is_x"
        if (end_idx > 0) and (end_idx <= len(strokes)):
            s2 = strokes[end_idx-1]
            # if verbose: print 'S2', s2
            # if verbose: print 'AREA', area
            if verbose:
                print 'S2 min/max', s2['xmin'], s2['ymin'], ':', s2['xmax'], s2['ymax']
                print 'S2 start/end', s2['strokes'][0], s2['strokes'][-1]


def example_callback(area, start_idx, end_idx, strokes):
    """
    Example callback for use with group_strokes().
    """
    print area['id']
    for i in range(start_idx, end_idx):
        print strokes[i]

if __name__ == "__main__":
    eink = None
    if 'server' in sys.argv[1:]:
        # start a pentrack server if one is not running already
        import eink_sparkle
        eink = eink_sparkle.EinkSparkle(None, None)
        eink.start()
    else:
        print "If pentrack server is not running, use 'server' command line argument\nto start server"

    areas = []
    xy = rotate_to_ts2
    areas.append(dict(tight=xy(((0, 0), (412, 512))),
                             id='1 top left\n*.\n..',
                             callback=example_callback))
    areas.append(dict(tight=xy(((412, 0), (825, 512))),
                             id='2 top right\n.*\n..',
                             callback=example_callback))
    areas.append(dict(tight=xy(((0, 512), (412, 1024))),
                             id='3 bottom left\n..\n*.',
                             callback=example_callback))
    areas.append(dict(tight=xy(((412, 512), (825, 1024))),
                             id='4 bottom right\n..\n.*',
                             callback=example_callback))
    for i in areas:
        print i

    strokes = Strokes(verbose=1)
    while 1:
        start = len(strokes.live_strokes)
        v = strokes.get_stroke()
        print "STROKE", v
        if v:
            strokes.label_strokes(start, areas)
            print strokes.live_strokes[-1]
            strokes.group_strokes()
        if not v:
            time.sleep(3)

    if eink:
        eink.stop()
