#!/usr/bin/env python
# Copyright 2011 Ricoh Innovations, Inc.
"""Patches PGM-type images into other PGM images."""

import re
from collections import namedtuple

__all__ = ['patch_pgm', 'read_header', 'PgmData', 'Insertion', 'CopySpec']


PgmData = namedtuple('PgmData',
        ['magic', 'width', 'height', 'maxval', 'data_offset', 'pixel_size'])

Insertion = namedtuple('Insertion', ['x', 'y', 'path_or_file', 'copy_specs'])
CopySpec = namedtuple('CopySpec', ['dx', 'dy', 'sx', 'sy', 'w', 'h'])


def patch_pgm(dst_path, insertions):
    """Patch PGM-type images into other PGM images.
    Each invocation modifies a single PGM file by inserting 1 or more
    rectangular regions from other PGM files.
    Parameters:
        dst_path -- the destination PGM file path
        insertions -- iterable of insertion copy specifications (Insertion
            instances) each containing:
          x -- the base x coordinate for copy specs' relative coordinate dx
          y -- the base y coordinate for copy specs' relative coordinate dy
          path_or_file -- either a file path or a file-like object from which
              to load the source image
          copy_specs -- an iterable of copy specifications (CopySpec
              instances), each containing:
            dx -- the destination x coordinate relative to x (above)
            dy -- the destination y coordinate relative to y (above)
            sx -- the x coordinate of the upper left corner of the source rect
            sy -- the y coordinate of the upper left corner of the source rect
            w -- the width of the rect to copy
            h -- the height of the rect to copy

    """
    with open(dst_path, 'r+b') as dst_f:
        dst = read_header(dst_f)
        dst_row_size = dst.width * dst.pixel_size
        for ins in insertions:
            src_f = ins.path_or_file
            is_path = isinstance(src_f, (str, unicode))
            try:
                if is_path:
                    src_f = open(src_f, 'rb')
                else:
                    src_f.seek(0)
                src = read_header(src_f)
                if src.pixel_size != dst.pixel_size:
                    raise RuntimeError('Pixel size of source and destination'
                        ' must be the same: %s' % ins.path)
                src_row_size = src.width * src.pixel_size

                def patch_1(src_rect_row_size, src_height, src_pos, dst_pos):
                    for row_index in xrange(src_height):
                        src_f.seek(src_pos)
                        row = src_f.read(src_rect_row_size)
                        if len(row) != src_rect_row_size:
                            raise RuntimeError('Early EOF')
                        dst_f.seek(dst_pos)
                        dst_f.write(row)
                        dst_pos += dst_row_size
                        src_pos += src_row_size

                if ins.copy_specs:
                    for sr in ins.copy_specs:
                        patch_1(
                            sr.w * src.pixel_size,
                            sr.h,
                            src.data_offset +
                                (sr.sy * src_row_size +
                                    sr.sx) * src.pixel_size,
                            dst.data_offset +
                                ((ins.y + sr.dy) * dst.width + ins.x + sr.dx) *
                                    dst.pixel_size)
                else:
                    patch_1(
                        src_row_size,
                        src.height,
                        src.data_offset,
                        dst.data_offset +
                            (ins.y * dst.width + ins.x) * dst.pixel_size)
            finally:
                if is_path:
                    src_f.close()


def read_header(f):
    """Read the header information of a PGM-type file.
    Returns a PgmData object.

    """
    header = f.read(100)
    m = re.match(r'(..)\s+(\d+)\s+(\d+)\s+(\d+)(?:\#[^\r\n]*[\r\n]*)*\s',
            header)
    if not m:
        raise RuntimeError('Corrupt header information: %r' % header)
    magic, width, height, maxval = m.group(1, 2, 3, 4)
    maxval = int(maxval)
    pixel_size = 1 if maxval < 256 else 2
    data_offset = m.end()
    f.seek(data_offset)
    if magic != 'P5':
        raise RuntimeError('**** NOT A PGM (P5) FILE ****: %s' % f.name)
    return PgmData(magic, int(width), int(height), maxval,
            data_offset, pixel_size)
