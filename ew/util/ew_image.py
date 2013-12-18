# Copyright 2011 Ricoh Innovations, Inc.
from __future__ import division
import os, datetime, uuid, array
from PIL import Image

from ew.util import ew_logging
from ew.util import system_config
import pyimage

logger = ew_logging.getLogger('ew.util.ew_image')
    
RAW_IMAGE_SIZE = (2592, 1944)
resize_algorithm = Image.BILINEAR
IMAGE_SIZES = {'s': .25, 'm': .5, 'l': .75, 'full': 1.0}
 
ERROR_LOAD = "Error loading image."
ERROR_CREATE = "Error encountered while creating image."
ERROR_CONVERT = "Error converting image."
ERROR_ROTATE = "Error encountered while rotating image."
ERROR_RESIZE = "Error encountered while resizing image."
ERROR_DITHER = "Error encountered while dithering image."
ERROR_PASTE = "Error encountered while pasting image."
ERROR_FILL_IMAGE = "Error encountered while creating new blank image."
ERROR_SAVE = "Error encountered while saving the image."
    
    
def get_error(message):
    return "%s: %r" % (message, pyimage.error_message())
    

class EwImage:
    """Small wrapper to make the C image library simpler.
    TODO:
    Not used yet.
    Eventually, PIL should be rolled into this module as a fallback.
    Need to take advantage of re-using buffers.
    """
    
    def __init__(self, size, path=None):
        self.w, self.h = size
        if path is not None:
            self.name, self.extension = os.path.basename(path).split('.')
        self.path = path
        self.image = None

    def _load(self):
        if self.image is None and self.path is not None:
            logger.debug("Loading image file: %r", self.path)
            image_type = self.extension.upper()
            if image_type in ['Y', 'UYVY']:
                self.image = pyimage.image(self.w, self.h, image_type)
                if not self.image:
                    raise RuntimeError(ERROR_CREATE)
                if pyimage.load_data(self.image, self.path) != 0:
                    raise RuntimeError(ERROR_LOAD)
            else:
                self.image = self._load_pgm()
                
    @classmethod
    def _create_new(cls, w, h, image, type):
        _instance =  cls((w, h))
        _instance.image = image
        _instance.extension = type
        return _instance
                
    def new_image(self, type="Y", color=(0x80 << 16 | 0x80 << 8 | 0x80)):
        self.extension = type
        self.image = pyimage.image(self.w, self.h, self.extension)
        if not self.image:
            raise RuntimeError(ERROR_CREATE)
        if pyimage.fill(self.image, 0, 0, self.w, self.h, color) != 0:
            raise RuntimeError(ERROR_FILL_IMAGE)
                
    def _load_pgm(self):
        pnm = pyimage.load_pnm(self.path)
        if not pnm:
            raise RuntimeError(ERROR_LOAD)
        width = int(pyimage.image_width(pnm)/2)
        height = int(pyimage.image_height(pnm)/2)
        self.size = (width, height)
        self.extension = pyimage.image_type(pnm)
        image = pyimage.image(self.w, self.h, self.extension)
        if not image:
            raise RuntimeError(ERROR_CREATE)
        return image

    def get_bw(self):
        self._load()
        bw_image = pyimage.image(self.w, self.h, 'Y')
        if not bw_image:
            raise RuntimeError(ERROR_CREATE)
        if pyimage.convert(bw_image, self.image) != 0:
            raise RuntimeError(ERROR_CONVERT)
        return EwImage._create_new(self.w, self.h, bw_image, 'Y') 

    def get_color(self, type="UYVY"):
        self._load()
        if type == self.extension.upper():
            return self
        else:
            color_image = pyimage.image(self.w, self.h, type)
            if not color_image:
                raise RuntimeError(ERROR_CREATE)
            if pyimage.convert(color_image, self.image) != 0:
                raise RuntimeError(ERROR_CONVERT)
            return EwImage._create_new(self.w, self.h, color_image, type)
        
    def rotate(self):
        self._load()
        rotated_image = pyimage.image(self.h, self.w, 
                self.extension.upper())
        if not rotated_image:
            raise RuntimeError(ERROR_CREATE)
        if pyimage.rotate(rotated_image, self.image) != 0:
            raise RuntimeError(ERROR_ROTATE)
        return EwImage._create_new(self.h, self.w, rotated_image, 
                self.extension.upper())
        
    def _resize_simple(self, size):
        w, h = size
        resized_image = pyimage.image(w, h, self.extension.upper())
        if not resized_image:
            raise RuntimeError(ERROR_CREATE)
        if pyimage.convert(resized_image, self.image) != 0:
            raise RuntimeError(ERROR_RESIZE)
        return EwImage._create_new(w, h, resized_image, 
                self.extension.upper())

    def _resize_two_step(self, size):
        pass

    def resize(self, size):
        self._load()
        #from fractions import Fraction
        #source_size_w, source_size_h = self.w, self.h
        #target_size_w, target_size_h = size
        #factor_w = Fraction(source_size_w/target_size_w)
        #factor_h = Fraction(source_size_h/target_size_h)
        return self._resize_simple(size)

    def dither(self, algorithm=2):
        self._load()
        bw_image = self.image        
        if self.extension != 'Y':
            logger.debug("Converting to bw before dithering.")
            bw_image = self.get_bw()
        dithered_image = pyimage.image(self.w, self.h, "Y")
        if not dithered_image:
            raise RuntimeError(ERROR_CREATE)
        if pyimage.dither(dithered_image, bw_image, int(algorithm)) != 0:
            raise RuntimeError(ERROR_DITHER)
        return EwImage._create_new(self.w, self.h, dithered_image, 'Y')

    def paste(self, dest_x, dest_y, ew_image, box=None):
        self._load()
        x = y = 0
        w, h = ew_image.w, ew_image.h
        if box:
            x, y, w, h = box
        if pyimage.bitblt(self.image, dest_x, dest_y, ew_image.image, x, y, w, h) != 0:
            raise RuntimeError(ERROR_PASTE)
        return self

    def save(self, path, type="RAW", quality=system_config.image_quality):
        type = type.upper()
        if type == "RAW" or type == "UYVY" or type == "Y" or type == "RGB24":
            pyimage.save_data(self.image, path)
        elif type == "JPEG" or type == "JPG":
            pyimage.save_jpeg(self.image, path, int(quality))
        elif type == "BMP":
            pyimage.save_bitmap(self.image, path)
        elif type == "PGM" or type == "PNM":
            pyimage.save_pnm(self.image, path)

    def cleanup(self, path):
        if os.path.exists(path):
            os.remove(path)
    

def _uyvy_to_rgb(source_image):
    w, h = RAW_IMAGE_SIZE
    logger.debug("Converting UYVY to RGB")
    name, extension = os.path.basename(source_image).split('.')
    raw_image = pyimage.image(w, h, extension.upper())
    rgb_image = pyimage.image(w, h, 'RGB24')
    if not raw_image or not rgb_image:
        raise RuntimeError(ERROR_CREATE)
    if pyimage.load_data(raw_image, source_image) != 0:
        raise RuntimeError(ERROR_LOAD)
    if pyimage.convert(rgb_image, raw_image) != 0:
        raise RuntimeError(ERROR_CONVERT)
    return rgb_image
    
def _uyvy_to_y(source_image):
    w, h = RAW_IMAGE_SIZE
    logger.debug("Converting UYVY to Y")
    name, extension = os.path.basename(source_image).split('.')
    raw_image = pyimage.image(w, h, extension.upper())
    raw_bw_image = pyimage.image(w, h, 'Y')
    if not raw_image or not raw_bw_image:
        raise RuntimeError(ERROR_CREATE)
    if pyimage.load_data(raw_image, source_image) != 0:
        raise RuntimeError(ERROR_CREATE)
    if pyimage.convert(raw_bw_image, raw_image) != 0:
        raise RuntimeError(ERROR_CONVERT)
    return raw_bw_image

def _resize_y(bw_image, w, h):
    logger.debug("Resizing Y")
    sized_bw_image = pyimage.image(w, h, 'Y')
    if not sized_bw_image:
        raise RuntimeError(ERROR_CREATE)
    if pyimage.convert(sized_bw_image, bw_image) != 0:
        raise RuntimeError(ERROR_CONVERT)
    return sized_bw_image
    
def _resize_rgb(rgb_image, w, h):
    logger.debug("Resizing RGB")
    resized_image = pyimage.image(w, h, 'RGB24')
    if not resized_image:
        raise RuntimeError(ERROR_CREATE)
    if pyimage.convert(resized_image, rgb_image) != 0:
        raise RuntimeError(ERROR_CONVERT)
    return resized_image

def _rotate_rgb(rgb_image, w, h):
    logger.debug("Rotating image to correct")
    rotated_rgb_image = pyimage.image(w, h, 'RGB24')
    if not rotated_rgb_image:
        raise RuntimeError(ERROR_CREATE)
    if pyimage.rotate(rotated_rgb_image, rgb_image) != 0:
        raise RuntimeError(ERROR_ROTATE)
    return rotated_rgb_image

def _get_temp_file(image_type):
    _final_name = "%s.%s" % (uuid.uuid4().hex, image_type)
    _final_path = os.path.join(system_config.tmp, _final_name)
    return _final_path

def _uyvy_to_base_bw(source_image):
    # open file as yu/yv stream
    size = RAW_IMAGE_SIZE
    data = im = None
    logger.debug("Opening %r", source_image)
    with open(source_image,'rb') as f:
        data = array.array('H',f.read())
    if data:
        logger.debug("Opened uyvy data file")
        # extract y stream (grayscale)
        out = array.array('B',[b >> 8 for b in data])
        logger.debug("Loading into PIL")
        im = Image.frombuffer('L',size,out.tostring(),'raw','L', 0, 1)
        base_w, base_h = tuple([int(i/2) for i in RAW_IMAGE_SIZE])
        logger.debug("Resizing image")
        im = im.resize((base_w, base_h), resize_algorithm)
    return im

def _dither_threshold(image_data):
    def closest_g16(i):
        raw = i & 0xf0
        if i & 0xf > 7 and raw < 0xf0:
            raw += 0x10
        return raw
    # generate palette
    palette = [closest_g16(i) for i in range(256)]
    out = array.array('B',[palette[b] for b in image_data])
    return out

def _dither_data(image_data, algorithm=0):
    if algorithm == 0:
        return _dither_threshold(image_data)
    elif algorithm == 1:
        return _dither_threshold(image_data)

def dither(image, algorithm=system_config.dithering_algorithm):
    _temp_path = _get_temp_file("pgm")
    size = image.size
    image.save(_temp_path)
    source_image = pyimage.load_pnm(_temp_path)
    if not source_image:
        raise RuntimeError(ERROR_LOAD)
    logger.debug("Dithering size: %r", size)
    x, y = size
    dithered_image = pyimage.image(x, y, 'Y')
    if not dithered_image:
        raise RuntimeError(ERROR_LOAD)
    if pyimage.dither(dithered_image, source_image, int(algorithm)) != 0:
        raise RuntimeError(ERROR_DITHER)
    if pyimage.save_pnm(dithered_image, _temp_path) != 0:
        raise RuntimeError(ERROR_SAVE)
    return Image.open(_temp_path), _temp_path

def convert_to_bw(source_image):
    """Get a black and white image from the current photo."""
#    base_bw = _uyvy_to_base_bw(source_image)
#    after = datetime.datetime.now()
#    logger.debug("get_bw took: %r", (after - now))
#    return base_bw.rotate(90), ''
    now = datetime.datetime.now()
    name, extension = os.path.basename(source_image).split('.')
    raw_bw = _uyvy_to_y(source_image)
    
    base_w, base_h = tuple([int(i/2) for i in RAW_IMAGE_SIZE])
    raw_bw = _resize_y(raw_bw, base_w, base_h)
    
    _temp_path = _get_temp_file("pgm")
    if pyimage.save_pnm(raw_bw, _temp_path) != 0:
        raise RuntimeError(ERROR_SAVE)

    after = datetime.datetime.now()
    logger.debug("get_bw took: %r", (after - now))
    return Image.open(_temp_path).rotate(90), _temp_path
        
def convert_to_color(source_image, target_path=None, image_type="jpg", 
            image_quality=system_config.image_quality, 
            image_resolution=system_config.image_resolution, 
            image_rotation=system_config.image_rotation):
    """Get a color image from the current photo."""
    now = datetime.datetime.now()
    name, extension = os.path.basename(source_image).split('.')
    # Convert UYVY to RGB
    w, h = RAW_IMAGE_SIZE
    rgb_image = _uyvy_to_rgb(source_image)
    
    temp_buffer = rgb_image
    # Resize image
    factor_size = IMAGE_SIZES[image_resolution]
    if factor_size < 1.0:
        logger.debug("Resizing image to factor: %r", factor_size)
        w, h = tuple([int(factor_size*i) for i in RAW_IMAGE_SIZE])
        temp_buffer = _resize_rgb(rgb_image, w, h)
    
    # Rotate image up
    # TODO: we do not use the rotate feature yet
    temp_buffer = _rotate_rgb(temp_buffer, h, w)
    
    _final_path = target_path
    if _final_path is None:
        _final_path = _get_temp_file(image_type)
    if image_type == 'bmp':
        if pyimage.save_bitmap(temp_buffer, _final_path) != 0:
            raise RuntimeError(ERROR_SAVE)
    else:
        if pyimage.save_jpeg(temp_buffer, _final_path, int(image_quality)) != 0:
            raise RuntimeError(ERROR_SAVE)
    after = datetime.datetime.now()
    logger.debug("get_color took: %r", (after - now))
    return Image.open(_final_path), _final_path