#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.

from __future__ import with_statement

#------------------------------------------------------------------------------
# Constants
#------------------------------------------------------------------------------
# The standard PIL image format that images are saved to
STDIMAGEFORMAT = "PPM"

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------
import errno
import os
import zipfile

import json


import constants as mc
from mlogging import MemphisLog, filecbi, hashobject, hashprefix

from ew.util.lock import ExclusiveLock, SharedLock

from ew.util import ew_logging
logger = ew_logging.getLogger('ew.memphis.file')

PIL_EXISTS = False
try:
    import PIL
    from PIL.Image import Image
    PIL_EXISTS = True
except ImportError:
    print "Warning: PIL not imported"
    logger.warn("PIL not imported")

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class IncompleteCacheError(Exception):
    def __init__(self, msg):
        self.msg = msg

class FormatError(Exception):
    def __init__(self, msg):
        self.msg = msg

class MemphisFile(object):
    '''MemphisFile
    The Memphisfile class is a generalized editing library for Memphis
    format documents. Instances are created by passing a file path to the
    constructor, and then opening the instance using the open() function.

    The primary access to the document itself are provided through three
    instance variables: pages, metadata, info, and localinfo.

    The pages variable contains an object that emulates an array of
    pages. The metadata and info objects emulate dictionaries of metadata
    information. The info variable should never be used by a developer, all
    developer metadata should be placed in the metadata object. Both of these
    objects are intended to have keys and values that are string objects.

    '''
    def __init__(self,filepath):
        self.filepath = filepath
        self.metadata = None
        self.pages = None
        self.info = None
        self.localinfo = None
        self._page_log_hashes = {} #will only have entries for pages whose logs have been added to

    def __enter__(self): 
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def open(self):
        """Open the file for reading and editing.
        All instances MUST be opened before use.

        """
        self.__makeifneeded()
        self.metadata = MemphisMetadata(self,self.filepath)
        self.mlog = MemphisLog(self.metadata.metadatadir)
        self.info = MemphisInfo(self,self.filepath)
        self.localinfo = MemphisLocalInfo(self,self.filepath)
        self.pages = MemphisFilePageList(self)
        return self


    def add_stroke_file(self, stroke_file_path):
        parts = stroke_file_path.split('.memphis/')
        page_parts = parts[1].split('.d/')
        page_id, stroke_file = page_parts
        try:
            page = self.page(page_id)
            page.add_stroke_file(stroke_file)
        except:
            logger.exception('malformed ink file %s', stroke_file_path)

    def page_log_monitor(self, page_id):
        """returns a function that adds a cbi entry to self._page_log_hashes each time
        the page log is updated.  This is useful for tracking page log changes for document
        authenication"""
        def save_hash(hash_value):
            self._page_log_hashes[page_id] = hash_value

        return save_hash

    def save(self):
        '''Sync the memphis file to disk'''
        self.info.save()
        self.localinfo.save()
        self.pages.save()
        #for any pages whose log has been extended write the hash of the last item to my log
        for page_id, hash_value in self._page_log_hashes.iteritems():
            self.mlog.writePageUpdated(page_id, hash_value)
        self.metadata.save()

    close = save

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.pages.page(key.start, key.stop, key.step)
        return self.pages.page(key)

    def page(self, *args):
        """Get the page object(s) for the specified page(s).
        See class MemphisPageFileList.

        """
        return self.pages.page(*args)

    def sanityCheck(self):
        if (self.pages == None):
            raise IncompleteCacheError('Pages object not defined')
        if (not os.path.exists(self.pages.pagelistpath)):
            raise IncompleteCacheError('Pagelist file %s does not exist' % (
                    self.pages.pagelistpath))
        if (len(self.pages) == 0):
            raise FormatError('Document is empty')
        self.sanityCheckPages()
        return True

    def sanityCheckPages(self):
        for p in self.pages:
            if not os.path.exists(os.path.join(
                    self.pages.memphisfile.filepath, p)):
                raise IncompleteCacheError(
                        'Page path "%s" does not exist' % (p))
        return True

    def saveZipTo(self,destpath):
        self.save()

        l = len(self.filepath)
        file = zipfile.ZipFile(destpath, "w")
        for membername in walk_files(self.filepath):
            if os.path.basename(membername) != "memphis.localinfo.json":
                file.write(membername,membername[l:],zipfile.ZIP_DEFLATED)
        file.close()

        # open the file again, to see what's in it

        #file = zipfile.ZipFile(destpath, "r")
        #for info in file.infolist():
        #   print info.filename, info.date_time, info.file_size, \
        #           info.compress_size


    def addMetaFile(self,frompath,newchildpath):
        addMetaFile(self.filepath,frompath,newchildpath)

    def get_lock(self, name, exclusive, non_blocking=False):
        """Return an ExclusiveLock or SharedLock object for the specified
           lock name.
        Parameters:
          name -- The lock name as a string, e.g. 'loaded', 'document',
            'status', ...
          exclusive -- If true returns an exclusive lock, otherwise a shared
            lock
          non_blocking -- If true, the lock object has non_blocking=True
        """
        lock_dir = os.path.join(self.filepath, "local/memphis-locks")
        try:
            os.makedirs(lock_dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        return (ExclusiveLock if exclusive else SharedLock)(
                os.path.join(lock_dir, name + '.lock'), non_blocking)

    #--------------------------------------------------------------------------
    #   Internal utilities
    #--------------------------------------------------------------------------

    def __makeifneeded(self):
        '''Test the existence of the document directory, and if it does not
           exist create both the main directory and its document metadata
           directory.
        '''
        if os.path.exists(self.filepath):
            if not os.path.isdir(self.filepath):
                raise IOError
        else:
            # note: side effect of making metadata directory this way is that
            #       base dir is also created
            os.makedirs(os.path.join(self.filepath, mc.BASEMETADATADIR))

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

class MemphisFilePageList(list):
    '''MemphisFilePageList sparsely emulates the list of pages in the
       document. Pages can be referred to by either page image file name
       or by index. The elements of the page list can be manipulated
       using the usual list operators, to insertions, deletions, and
       such can all be performed using this class. Maintains a metadata
       file, the 'memphis.pagelist' file which contains the list of page
       image files, in order, that represent the pages of this document.
       Returns MemphisPage objects, but does not instantiate them until
       some caller asks for a specific page.
    '''

    def __init__(self,memphisfile):
        self.memphisfile = memphisfile
        self.pagelistpath = os.path.join(self.memphisfile.filepath,
                mc.BASEMETADATADIR,mc.PAGELISTFILENAME)
        self.needs_rewrite = False
        self.pagesopened = {}

        if os.path.exists(self.pagelistpath):
            with open(self.pagelistpath,"r") as infile:
                for line in infile:
                    self.append(line.strip())

    def save(self):
        if self.needs_rewrite:
            with open(self.pagelistpath,"w") as outfile:
                for p in self:
                    outfile.write(p)
                    outfile.write('\r\n')
            self.needs_rewrite = False
        for p in self.pagesopened.values():
            p.save()

    close = save

    #   Overridden list methods
    #--------------------------------------------------------------------------

    @classmethod
    def write_ops(cls):
        """Generates overriding mutator methods to set the dirty attribute.
        This instead of hand-writing a dozen almost identical methods to
        set needs_rewrite in all list methods that can modify the
        list.

        """
        for op in [ # Mutating list methods:
                    list.__delitem__,
                    list.__delslice__,
                    list.__iadd__,
                    list.__imul__,
                    list.__setitem__,
                    list.__setslice__,
                    list.append,
                    list.extend,
                    list.insert,
                    list.pop,
                    list.remove,
                    list.reverse,
                    list.sort,
               ]:

            def create_override(op):
                """Function to privide an environment to hold the "op"
                   variable."""
                def delegate(self, *args, **kwargs):
                    value = getattr(super(cls, self), op.__name__)(
                            *args, **kwargs)
                    self.needs_rewrite = True
                    return value
                delegate.__name__ = op.__name__
                setattr(cls, op.__name__, delegate)
            create_override(op)

    def normalize_key(self, key):
        if not key in self:
            for actual_key in self:
                ak = actual_key.split('.')[0]
                if ak == key:
                    return actual_key
        return key
            
    def page(self, *args):
        '''Fetches page objects either by file name or index in the page list.
        If more that one argument is given, a list of page objects 
        If the specified page object has not yet been created, it is created.

        '''
        if len(args) == 1:
            key = args[0]
            if isinstance(key, str):
                pkey = self.normalize_key(key) #pagelist has page image extension garbage in 1.0
                if not super(MemphisFilePageList, self).__contains__(pkey):
                    logger.debug('no %s in %s', pkey, self)
                    raise KeyError(key)
                return self.page_for(pkey)
            elif isinstance(key, int):
                return self.page_for(
                        super(MemphisFilePageList, self).__getitem__(key))
        else:
            key = slice(*args)
            return [self.page_for(name) for
                   name in super(MemphisFilePageList, self).__getitem__(key)]

    def page_for(self, name):
        """Get page object from a page name.
        Retrieves page from cache if already instantiated, otherwise creates
        and caches a new page object.

        """
        page = self.pagesopened.get(name)
        if not page:
            page = MemphisFilePage(self.memphisfile,name)
            self.pagesopened[name] = page
        return page

    def path(self, name):
        """Get the full path of the page image.
        Accepts a page id or index.
        Raises IndexError if name is a list index out of range.

        """
        if isinstance(name, int):
            name = self[name]
        return os.path.join(self.memphisfile.filepath, name)

# Generate the MemphisFilePageList overridden mutator methods, then delete
# the special method that did it.
MemphisFilePageList.write_ops()
del MemphisFilePageList.write_ops

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------

class MemphisFilePage(object):
    def __init__(self,memphisfile,page):
        self.memphisfile = memphisfile
        self.pagename = page
        self.filepath = os.path.join(self.memphisfile.filepath,page)
        self.metadata = MemphisMetadata(self.memphisfile,self.filepath)
        self.mlog = MemphisLog(self.metadata.metadatadir)
        self.mlog.set_entry_monitor(self.memphisfile.page_log_monitor(page))
        #self.data = MemphisMetadata(self.memphisfile, self.filepath, "memphis.data.json")

    def setBaseImage(self,image,isOriginal=False):
        if isinstance(image,str):
            simplefilecopy(image,self.filepath)
        elif PIL_EXISTS:
            if isinstance(image,PIL.Image.Image):
                image.save(self.filepath,STDIMAGEFORMAT)
        self.mlog.writeBaseImageUpdated(self.pagename,filecbi(self.filepath))

        if isOriginal:
            self.__makeifneeded()
            basename = os.path.basename(self.filepath)
            origpath = os.path.join(metadataPathFor(self.filepath),"%s.%s" % (
                    "original",basename))
            self.addMetaFile(self.filepath,origpath)


    def add_stroke_file(self,strokedataFile):
        """chops strokedataFile to be page relative and logs it"""
        def relative_path(path):
            return path.split('/')[-1]
        
        self.mlog.writeAddStrokeFile(relative_path(strokedataFile))
        
    def removeStrokeFile(self,strokeid):
        pass # TBD
        #self.memphisfile.removeStroke(strokedata)

    def addMetaFile(self,frompath,newchildpath):
        self.__makeifneeded()
        addMetaFile(self.filepath,frompath,newchildpath)

    def save(self):
        self.metadata.save()
        #self.data.save()

    close = save

    def __makeifneeded(self):
        mp = metadataPathFor(self.filepath)
        if not os.path.exists(mp):
            os.makedirs(mp)

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class MemphisInfo(dict):

    def __init__(self,memphisfile,path):
        self.memphisfile = memphisfile
        self.basepath = path

        # choose appropriate metadata path
        if os.path.isdir(self.basepath):
            # document wide metadata
            self.metadatadir = os.path.join(self.basepath,mc.BASEMETADATADIR)
        else:
            # specific page metadata
            raise IOError,"Can only have info for document directories"

        self.jsonpath = os.path.join(self.metadatadir,"memphis.info.json")

        # load from metadata file if it already exists
        data = load_json(self.jsonpath)
        super(MemphisInfo, self).__init__(data)

        self.needs_rewrite = False

    def save(self):
        if self.needs_rewrite:
            with open(self.jsonpath,"w") as jsonfile:
                json.dump(self, jsonfile, sort_keys=True, indent=4)
            self.needs_rewrite = False

    close = save

    #--------------------------------------------------------------------------
    #   Overridden dict methods
    #--------------------------------------------------------------------------

    @classmethod
    def write_ops(cls):
        """Generates overriding mutator methods to set the dirty attribute.
        This instead of hand-writing several almost identical methods to
        set needs_rewrite in all dict methods that can modify the
        dict.

        """
        for op in [ # Mutating dict methods:
                    dict.__delitem__,
                    dict.__setitem__,
                    dict.clear,
                    dict.pop,
                    dict.popitem,
                    dict.setdefault,
                    dict.update,
               ]:

            def create_override(op):
                """Function to privide an environment to hold the "op"
                   variable."""
                def delegate(self, *args, **kwargs):
                    value = getattr(super(cls, self), op.__name__)(
                            *args, **kwargs)
                    self.needs_rewrite = True
                    return value
                delegate.__name__ = op.__name__
                setattr(cls, op.__name__, delegate)
            create_override(op)

# Generate the MemphisInfo overridden mutator methods, then delete
# the special method that did it.
MemphisInfo.write_ops()
del MemphisInfo.write_ops

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class MemphisLocalInfo(dict):

    def __init__(self,memphisfile,path):
        self.memphisfile = memphisfile
        self.basepath = path

        # choose appropriate metadata path
        if os.path.isdir(self.basepath):
            # document wide metadata
            self.metadatadir = os.path.join(self.basepath,'local')
        else:
            # specific page metadata
            raise IOError,"Can only have local info for document directories"

        self.jsonpath = os.path.join(self.metadatadir,"memphis.localinfo.json")

        # load from metadata file if it already exists
        data = load_json(self.jsonpath)
        super(MemphisLocalInfo, self).__init__(data)

        if not os.path.exists(self.metadatadir):
            os.mkdir(self.metadatadir)
            
        self.needs_rewrite = False


    def save(self):
        if self.needs_rewrite:
            if not os.path.exists(self.metadatadir):
                os.mkdir(self.metadatadir)
            with open(self.jsonpath,"w") as jsonfile:
                json.dump(self, jsonfile, sort_keys=True, indent=4)
            self.needs_rewrite = False

    close = save

    #--------------------------------------------------------------------------
    #   Overridden dict methods
    #--------------------------------------------------------------------------

    @classmethod
    def write_ops(cls):
        """Generates overriding mutator methods to set the dirty attribute.
        This instead of hand-writing several almost identical methods to
        set needs_rewrite in all dict methods that can modify the
        dict.

        """
        for op in [ # Mutating dict methods:
                    dict.__delitem__,
                    dict.__setitem__,
                    dict.clear,
                    dict.pop,
                    dict.popitem,
                    dict.setdefault,
                    dict.update,
               ]:

            def create_override(op):
                """Function to privide an environment to hold the "op"
                   variable."""
                def delegate(self, *args, **kwargs):
                    value = getattr(super(cls, self), op.__name__)(
                            *args, **kwargs)
                    self.needs_rewrite = True
                    return value
                delegate.__name__ = op.__name__
                setattr(cls, op.__name__, delegate)
            create_override(op)

# Generate the MemphisLocalInfo overridden mutator methods, then delete
# the special method that did it.
MemphisLocalInfo.write_ops()
del MemphisLocalInfo.write_ops

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class MemphisMetadata(dict):
    def __init__(self,memphisfile,path, json_file="memphis.metadata.json"):
        self.memphisfile = memphisfile
        self.basepath = path

        # choose appropriate metadata paths
        self.metadatadir = metadataPathFor(self.basepath)
        self.jsonpath = os.path.join(
                self.metadatadir, json_file)

        # load from metadata file if it already exists
        data = load_json(self.jsonpath)
        super(MemphisMetadata, self).__init__(data)

        self.needs_rewrite = False
        self.originalkeys = set(super(MemphisMetadata, self).keys())
        self.logentrieswrite = set()
        self.logentriesdelete = set()

    def save(self):
        if self.needs_rewrite:
            mlog = MemphisLog(self.metadatadir)

            # this removes any keys
            self.logentrieswrite = self.logentrieswrite - self.logentriesdelete
            for e in self.logentrieswrite:
                #self[META_CURRENTHASH] = mlog.writeSetMetaEntry(e,self[e])
                super(MemphisMetadata, self).__setitem__(
                        mc.META_CURRENTHASH, mlog.writeSetMetaEntry(e,self[e]))

            # this removes any delete entries that are not part of the
            # original set of keys when we opened.
            self.logentriesdelete = self.logentriesdelete & self.originalkeys
            for e in self.logentriesdelete:
                #self[META_CURRENTHASH] = mlog.writeRemoveMetaEntry(e)
                super(MemphisMetadata, self).__setitem__(
                        mc.META_CURRENTHASH, mlog.writeRemoveMetaEntry(e))

            # NOTE = JSON Write must follow all metadata writes, so that
            # rolling hash is properly updated in JSON
            with open(self.jsonpath,"w") as jsonfile:
                json.dump(self, jsonfile, sort_keys=True, indent=4)

            if self.memphisfile.metadata.basepath is not self.basepath:
                # Updating page metadata, must entangle with main document log
                mainmlog = MemphisLog(self.memphisfile.metadata.metadatadir)
                mainmlog.writePageMetaUpdated(self.basepath,
                        self[mc.META_CURRENTHASH])

            self.needs_rewrite = False

    close = save

    #--------------------------------------------------------------------------
    #   Overridden dict methods
    #--------------------------------------------------------------------------

    def __setitem__(self,key,value):
        value = super(MemphisMetadata, self).__setitem__(key ,value)
        self.needs_rewrite = True
        self.logentrieswrite.add(key)
        return value

    def __delitem__(self,key):
        value = super(MemphisMetadata, self).__delitem__(key)
        self.needs_rewrite = True
        self.logentriesdelete.add(key)
        return value

    def clear(self):
        keys = self.keys()
        value = super(MemphisMetadata, self).clear()
        self.needs_rewrite = True
        for key in keys:
            self.logentriesdelete.add(key)
        return value

    def update(self,pairs):
        items = pairs.items() if isinstance(pairs, dict) else pairs
        value = super(MemphisMetadata, self).update(pairs)
        self.needs_rewrite = True
        for key, _ in items:
            self.logentrieswrite.add(key)
        return value

    def setdefault(self,key,default=None):
        had_key = key in self
        value = super(MemphisMetadata, self).setdefault(key, default)
        if not had_key:
            self.needs_rewrite = True
            self.logentrieswrite.add(key)
        return value

    def pop(self,*args):
        if args and (args[0] in self):
            self.needs_rewrite = True
            self.logentriesdelete.add(args[0])
        value = super(MemphisMetadata, self).pop(*args)
        return value

    def popitem(self):
        value = super(MemphisMetadata, self).popitem()
        self.needs_rewrite = True
        self.logentriesdelete.add(value[0])
        return value

#------------------------------------------------------------------------------
#   Utility Functions
#------------------------------------------------------------------------------

def addMetaFile(baseitempath,frompath,newchildpath):
    # incoming path must include a file name, and may include subdirectory
    # structure
    newp = os.path.split(newchildpath)
    targetdir = metadataPathFor(baseitempath)
    subdir = targetdir #write in main doc dir if needed
    if newp[0]:
        # then path includes new subdirectory, make it
        subdir = os.path.join(targetdir,newp[0])
        if not os.path.exists(subdir):
            logger.info("making dir %s", subdir)
            os.makedirs(subdir)

    # copy the file, generate a hash as we do
    targetfname = os.path.join(subdir,newp[1])
    infile = open(frompath,"r")
    outfile = open(targetfname,"w")
    h = hashobject()
    block = infile.read(4096)
    while block:
        outfile.write(block)
        h.update(block)
        block = infile.read(4096)
    outfile.close()
    infile.close()

    mlog = MemphisLog(targetdir)
    mlog.writeAddMetaFile(targetfname,hashprefix()+h.hexdigest())

def addExistingMetaFile(baseitempath,newchildpath):
    # incoming path must include a file name, and may include subdirectory
    # structure
    newp = os.path.split(newchildpath)
    targetdir = metadataPathFor(baseitempath)
    subdir = targetdir #write in main doc dir if needed
    if newp[0]:
        # then path includes new subdirectory, make it
        subdir = os.path.join(targetdir,newp[0])
        if not os.path.exists(subdir):
            logger.info("making dir %s", subdir)
            os.makedirs(subdir)

    # copy the file, generate a hash as we do
    targetfname = os.path.join(subdir,newp[1])
    infile = open(targetfname,"r")
    h = hashobject()
    block = infile.read(4096)
    while block:
        h.update(block)
        block = infile.read(4096)
    infile.close()

    mlog = MemphisLog(targetdir)
    file_hash = hashprefix()+h.hexdigest()
    mlog.writeAddMetaFile(targetfname,file_hash)
    return file_hash

def getMetaFileHash(baseitempath,newchildpath):
    # incoming path must include a file name, and may include subdirectory
    # structure
    newp = os.path.split(newchildpath)
    targetdir = metadataPathFor(baseitempath)
    subdir = targetdir #write in main doc dir if needed

    # copy the file, generate a hash as we do
    targetfname = os.path.join(subdir,newp[1])
    infile = open(targetfname,"r")
    h = hashobject()
    block = infile.read(4096)
    while block:
        h.update(block)
        block = infile.read(4096)
    infile.close()
    file_hash = hashprefix()+h.hexdigest()
    return file_hash

def metadataPathFor(path):
    # choose appropriate metadata path
    if os.path.isdir(path):
        return os.path.join(path,mc.BASEMETADATADIR)   # document wide metadata
    else:
        return os.path.splitext(path)[0] + ".d"     # specific page metadata

def simplefilecopy(source,dest):
    infile = open(source,"r")
    outfile = open(dest,"w")
    block = infile.read(4096)
    while block:
        outfile.write(block)
        block = infile.read(4096)
    infile.close()
    outfile.close()

def walk_files(directory):
    """Produces all regular file paths in a directory."""
    for dirpath, dirnames, filenames in os.walk(directory)[-1]:
        len(dirnames) #BS to make pylint shut up
        for filename in filenames:
            yield os.path.join(dirpath, filename)

def load_json(jsonpath):
    """Load JSON data from file "jsonpath"
    Return an empty dict if file "jsonpath" is not found or if the
    JSON data is not valid (such as file empty).
    """
    try:
        with open(jsonpath) as jsonfile:
            try:
                return json.load(jsonfile)
            except ValueError, e:
                logger.error("Invalid JSON data: %s: %s", jsonpath, e)
    except IOError, e:
        if e.errno != errno.ENOENT:
            logger.error("IO error reading JSON data: %s: %s", jsonpath, e)
        #else:
        #    logger.info("JSON file not found: %s", jsonpath)
    return {}

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
if __name__ == "__main__":

    from PIL import ImageDraw
    testimg = Image.new("L",(825,1140),"#ffffff")
    draw = ImageDraw.Draw(testimg)
    draw.line((0, 0) + testimg.size, fill=128)
    draw.line((0, testimg.size[1], testimg.size[0], 0), fill=128)
    del draw

    f = MemphisFile("doctest")
    f.open()
    f.metadata["destinationURL"] = "http://my.test.site.com"
    f.info["title"] = "Test Document - Memphis File Format"

    f.pages.append("P1.pgm")
    f.pages["P1.pgm"].metadata["Author"]="Kurt Piersol"
    f.pages["P1.pgm"].setBaseImage("P1.pgm",isOriginal=True)
    f.pages[0].metadata["Type"]="Test Page"

    f.pages.append("P3.ppm")
    f.pages[1].setBaseImage(testimg)
    f.pages[1].metadata["Type"]="Test Page"
    f.pages[1].metadata["Help"]="Me"
    del f.pages[1].metadata["Help"]
    f.close()

    f.saveZipTo("doctest.zip")
