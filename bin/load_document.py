#!/usr/bin/python
# Copyright 2010 Ricoh Innovations, Inc.
"""
@author - Samantha Atkins

Temporary shim file to get launcher to switch doucments.  Only needed 
until we have the Infobar.  Make also be useful for some types of
unit test.
"""

import sys, os
from sdk.document import Document 
from ew.util import comms

def usage(args, file = None):
    print "Expected 1 orgument which is a valid docid. Got %s" % args 
    if file:
        print "No document at %s"% file
    sys.exit(-2)
    
if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage(sys.argv)
    
    file = Document.standard_doc_path(sys.argv[1])
    if not os.path.isdir(file):
        usage(sys.argv, file)

    client = comms.create_XMLRPC_client('localhost', 
                                        comms.LAUNCHER_PORT)
    client.load_document(file)
    
