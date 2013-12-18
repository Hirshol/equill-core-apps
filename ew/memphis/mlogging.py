#!/usr/bin/env python
# Copyright 2010-2011 Ricoh Innovations, Inc.

import os
import logging
import datetime
import json


import hashlib
import fcntl
import random
import glob
from types import ListType

import constants as mc

HASHTYPEPREFIX = "sha1."
NEWLINE = '\r\n'
LINE_PREFIX = 'Entry: '

class MemphisLog:
    def __init__(self,path):
        self.path = path
        self.logfilepath = os.path.join(self.path,'memphis.log')
        self.ispartiallog = False
        self.previoushash = None
        self._entry_monitor = None
        
        if not os.path.exists(self.logfilepath):
            #first, check to see if plog file exists
            plogs = glob.glob(os.path.join(self.path,"memphis.*.plog"))
            if plogs:
                #aha, a partial log is here. should only ever be one at a time
                self.logfilepath = plogs[0]
                self.ispartiallog = True
            else:
                # hmmm, possible either a new document or one whose log
                # has not been synced to conserve bandwidth, test in json file
                jsonpath = os.path.join(self.path,"memphis.metadata.json")
                # load from metadata file if it already exists
                if os.path.exists(jsonpath):
                    print "loading jsonfile because missing log"
                    jsonfile = open(jsonpath,"r")
                    metadict = json.load(jsonfile)
                    jsonfile.close()
                    if mc.META_CURRENTHASH in metadict:
                        # ah, this is not a new document, we must make a new plog file
                        self.logfilepath = os.path.join(self.path,'memphis.%s.plog' % hex(random.getrandbits(128)))
                        self.previoushash = metadict[mc.META_CURRENTHASH]
                        self.ispartiallog = True
            
        

    def set_entry_monitor(self, monitor):
        """on writing an entry we will invoke the monitor function with the cbi hash of what we 
        just wrote"""
        self._entry_monitor = monitor

    def writeAddPageEntry(self,pageimagefilepath):
        return self.writelogentry("AddPage",PageID=pageimagefilepath)

    def writeRemovePageEntry(self,pageimagefilepath):
        return self.writelogentry("RemovePage",PageID=pageimagefilepath)

    def writeSetMetaEntry(self,attribute,value):
        return self.writelogentry("SetMetadata",Key=attribute,Value=value)

    def writeRemoveMetaEntry(self,attribute):
        return self.writelogentry("RemoveMetadata",Key=attribute)
    
    def writeAddMetaFile(self,filepath,hash):
        return self.writelogentry("AddMetaFile",Path=filepath,Hash=hash)
    
    def writeAddStrokeFile(self,filepath):
        hash_val = filecbi(os.path.join(self.path, filepath))
        return self.writelogentry("AddStrokeFile", Hash=hash_val, Path=filepath)
    
    def writePageMetaUpdated(self,pageID,lastentry):
        return self.writelogentry("PageMetadataUpdated",PageID=pageID,LastEntry=lastentry)

    def writePageUpdated(self, pageID, lastentry):
        return self.writelogentry("PageUpdated", PageID=pageID, LastEntry=lastentry)

    def writeBaseImageUpdated(self,pageID,imagehash,isOriginal=False):
        return self.writelogentry("BaseImageUpdated",PageID=pageID,ImageHash=imagehash)
        
    def writeMerge(self,serverhash='unspecified',tablethash='unspecified',mergebase='unspecified'):
        return self._writelogentry("Merged",Serverhash=serverhash,Tablethash=tablethash,MergeBase=mergebase)

    def writefirstentryifneeded(self):
        '''make sure a logfile exists, then pass the path to newr code.'''
        #print self.logfilepath, self.previoushash
        if not os.path.exists(self.logfilepath):
            #print self.previoushash
            #raise IOError
            f = open(self.logfilepath,'wb')
            if not self.previoushash:
                f.write('%snull.%s' % (LINE_PREFIX,NEWLINE)  )
            f.close()
        
        
    def _writelogentry(self,opcode,**keywords):
        logrecord = createlogrecord(opcode,keywords)

        # mke sure a log directory exists
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        elif not os.path.isdir(self.path):
            raise IOError,"Log path does not point at directory"
            
        self.writefirstentryifneeded()
            
        cbi = stringcbi(logrecord)

        # write the stand alone entry file
        filepath = os.path.join(self.path,cbi)
        f = open(filepath,'wb')
        f.write(logrecord)
        f.close()
        return cbi

    def writelogentry(self,opcode,**keywords):
        cbi = self._writelogentry(opcode,**keywords)
        prev = addCBIsettolog(self.logfilepath,[cbi],self.previoushash)
        if self._entry_monitor:
            self._entry_monitor(prev)
        return prev

#----------------------------------------------------------------------------------------------
#     Utility Functions
#----------------------------------------------------------------------------------------------

def hashobject():
    return hashlib.sha1()

def hashprefix():
    return HASHTYPEPREFIX

def stringcbi(message):
    '''return a cbi for the provided message.'''
#    return 'sha1.'+ sha1.new(message).hexdigest()
    h = hashobject()
    h.update(message)
    return hashprefix()+ h.hexdigest()

def filecbi(pathname):
    '''return a cbi for the file.'''
    f = open(pathname,'rb')
#    h = sha1.new()
    h = hashobject()
    d = f.read(64000)
    while(len(d)>0):
        h.update(d)
        d = f.read(64000)
    f.close()
    return hashprefix()+h.hexdigest()
    
def getlastentry(teststring, strict=False):
    '''return a string which is the last valid entry from the teststring or None'''
    start = teststring.rfind( LINE_PREFIX )
    if start == -1:
        return None
    end = teststring.find(NEWLINE, start) #here could check for '\r' or '\n'
    if end == -1:
        return None
    #print start, end
    testentry = teststring[start + len(LINE_PREFIX):end] # Drop LINE_PREFIX
    return testentry


def getlastentryfromfile(logfile):
    '''return a string which is the last valid entry from the file or None, assumes object supports read and seek, uses getlastentry to evaluate strings'''
    logfile.seek(0,2)
    logfilesize = logfile.tell()
    #need to get the last line of the file
    # lines are supposed to look like 'Entry: cbi-cbiCRLF' but any ending is should be accepted
    foundlast = None
    bytesleft = logfilesize
    teststring = ''
    while not foundlast and bytesleft:
        bytesback = min(210,bytesleft) #210 is enough for 3 cbis and some text
        logfile.seek(-bytesback,1) # size from end
        addstring =  logfile.read(bytesback)
        #print 'read:',bytesback,addstring
        logfile.seek(-bytesback,1)
        bytesleft -= bytesback
        teststring = addstring + teststring
        foundlast = getlastentry(teststring)
    return foundlast



def addCBIsettolog(logfilepath,cbilist,previoushash=None):
    '''lock & open file, compute previous cbi, format entry, append, closefile.'''

    if type(cbilist) == ListType:
        cbilist = '-'.join(cbilist)
    logf = open(logfilepath,'rb+')
    fcntl.lockf(logf.fileno(), fcntl.LOCK_EX) # OS level file lock, should block until file is free
    if previoushash:
        prevcbi = previoushash
    else:
        prev = getlastentryfromfile(logf)
    
        if not prev:
            prev = stringcbi('') ## HERE start value.
            logging.warn('starting new log in %s' % logfilepath)
        prevcbi = stringcbi(prev)
    
    entry = prevcbi+'-'+cbilist
    line = LINE_PREFIX + entry + NEWLINE
    logf.seek(0,2)
    logf.write(line)
    fcntl.lockf(logf.fileno(), fcntl.LOCK_UN)  # OS level file unlock
    logf.close()
    
    #logging.debug('newraddcbilisttofile %s' % entry)
    return stringcbi(entry)

def createlogrecord(opcode,keywords):
    #logging.debug('logcontents with ' + str(keywords))
    oprecord = ""
    keywords['Opcode'] = opcode
    keywords['Time'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    for key in keywords.keys():
        oprecord += key
        oprecord += ": "
        oprecord += str(keywords[key])
        oprecord += NEWLINE
    oprecord += NEWLINE
    return oprecord


