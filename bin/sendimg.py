#!/usr/bin/env python
# Copyright 2010 Ricoh Innovations, Inc.

"""
Tell pentrackupdate server to draw an image via a socket. The image
must be a valid PGM file. See 'sendimage.py --help' for usage.

$Id$
$HeadURL$
"""

import sys
from ew.e_ink import PyPenTrackUpdate

usage = """
Tell pentrackupdate server to draw an image via a socket. The image
must be a valid PGM file.

usage: %prog [options] imagefilename [xDest yDest] [xSrc ySrc] [wSrc hSrc] [requestid] 

where imagefilename is the filename of the PGM file to render
      xDest,yDest is the position of the image on the display.
      xSrc,ySrc is the top-left corner of the window on the image to render
      wSrc,hSrc is the dimention of the window on the image to render (0,0 == whole image)
      requestid is the ID to use when reporting a read complete (0 to not generate an event)
"""
parser = PyPenTrackUpdate.get_commandline_parser(usage)

parser.add_option("--rot", dest="rot",
                  action="store_true", default=False, help="rotate images to fit Edo's vertical orientation")

parser.add_option("--erasestrokes", dest="erasestrokes",
                  action="store_true", default=False, help="clear all strokes from memory before doing update, and overwrite strokes with new image")

parser.add_option("--flash", dest="flash",
                  action="store_true", default=False, help="do direct update, then flash to deghost (instead of sparkle)")

parser.add_option("--asink", dest="asink",
                  action="store_true", default=False, help="draw image to ink layer rather than as background image")

(options, args) = PyPenTrackUpdate.parse_command_line(parser, None)

xDest = yDest = xSrc = ySrc = wSrc = hSrc = requestid = 0

if len(args) == 0 or len(args) > 8:
    print usage
    sys.exit(1)
if len(args) >= 1:
    imagename = args[0]
if len(args) >= 2:
    xDest = int(args[1])
if len(args) >= 3:
    yDest = int(args[2])
if len(args) >= 4:
    xSrc = int(args[3])
if len(args) >= 5:
    ySrc = int(args[4])
if len(args) >= 6:
    wSrc = int(args[5])
if len(args) >= 7:
    hSrc = int(args[6])
if len(args) == 8:
    requestid = int(args[7])

ptu = PyPenTrackUpdate.PenTrackUpdate(**options)
ptu.sendImgWindow(imagename, xDest, yDest, xSrc, ySrc, wSrc, hSrc, requestid, options)

