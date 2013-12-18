#!/usr/bin/env python
# Copyright (c) 2010 __Ricoh Company Ltd.__. All rights reserved.

"""Define various device system locations
@author: Arnold Cabreza
@author: Bob Alexander

Environment variables used for off-tablet development environments.

EW_SYSTEM_DIR   (default: /usr/local/lib/ew).
EW_DATA_DIR     (default: /data).
EW_PYTHON_DIR   (default: $EW_SYSTEM_DIR/python).
TMP             (default: /tmp)

For MS-Windows, *both* EW_SYSTEM_DIR and EW_DATA_DIR must be defined
since the defaults are not valid Windows paths. E.g.
   set EW_SYSTEM_DIR=C:\ricoh_ews
   set EW_DATA_DIR=%EW_SYSTEM_DIR%\data
"""

import os

# Define some basic directories.
is_windows = os.sep == '\\'
default_system_dir = '/usr/local/lib/ew'
system_home = os.environ.get('EW_SYSTEM_DIR', default_system_dir)
data_home = os.environ.get('EW_DATA_DIR', '/data')
tmp = os.environ.get('TMP', '/tmp')
python_dir = (os.environ.get('EW_PYTHON_DIR') or
        os.path.join(system_home, 'python'))

# Define other EWS directories.
log_dir = os.environ.get('EW_LOG_DIR') or os.path.join(data_home, 'logs')
log_filename_default = "ew_tablet"
ew_dir = os.environ.get('EW_DIR') or os.path.join(python_dir, 'ew')
sdk_dir = os.environ.get('EW_SDK_DIR') or os.path.join(python_dir, 'sdk')
widget_resource_dir = (os.environ.get('EW_WIDGET_RESOURCE_DIR') or
        os.path.join(sdk_dir, 'widgets', 'images'))
config_dir = (os.environ.get('EW_CONFIG_DIR') or
        os.path.join(system_home, 'config'))
data_config_dir = (os.environ.get('EW_DATA_CONFIG_DIR') or
        os.path.join(data_home, 'config'))
internal_decs = os.path.join(data_home, 'internal_decs')
resource_dir = (os.environ.get('EW_RESOURCE_DIR') or
        os.path.join(system_home, 'resource'))
images_dir = (os.environ.get('EW_IMAGES_DIR') or
        os.path.join(resource_dir, 'images'))
audio_dir = (os.environ.get('EW_SOUNDS_DIR') or
        os.path.join(resource_dir, 'sounds'))
font_dir = os.environ.get('EW_FONT_DIR')
if not font_dir:
    if system_home == default_system_dir:
        font_dir = '/usr/share/fonts/truetype/ttf-dejavu'
    else:
        font_dir = os.path.join(resource_dir, 'truetype', 'ttf-dejavu')
cache_dir = os.environ.get('EW_DIR', tmp)
gui_cache_dir = (os.environ.get('EW_GUI_CACHE_DIR') or
        os.path.join(cache_dir, 'guitmp'))

image_type = 'jpg'
image_quality = os.environ.get('EW_DEFAULT_PHOTO_QUALITY', 90)
image_resolution = os.environ.get('EW_DEFAULT_PHOTO_RESOLUTION', 'full')
image_rotation = os.environ.get('EW_DEFAULT_PHOTO_ROTATION', 90)

audio_type = 'ogg'
dithering_algorithm = 2

layout_version = os.environ.get('EW_FORM_LAYOUT_VERSION', '1.0')

def dump():
    """Print the config variable values."""
    import sys
    mod = sys.modules[__name__]
    for k in dir(mod):
        if k == 'tmp' or (not k.startswith('_') and '_' in k):
            print k, '=>', getattr(mod, k)

# Main program prints all config variable values, or a specified variable value.
# Args: [variable-name]
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print getattr(sys.modules[__name__], sys.argv[1])
    else:
        dump()
