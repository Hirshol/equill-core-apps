#!/usr/bin/env python
# Copyright 2010 Ricoh Innovations, Inc.

GSCMD = "gs"
RENDERCMD = " -q -DNOPAUSE -dBATCH -sDEVICE=pgmraw -dPDFFitPage -r300x300 -sOutputFile=$1_p%04d.pgm "
MOGRIFYCMD = "mogrify -rotate 270 -scale 1068x825 -extent 1200x825  -gravity South %s -depth 8"
# The following would be used to make double-resolution (zoomable) page images
#MOGRIFYCMD = "mogrify -rotate 270 -scale 2136x1650 -extent 2400x1650  -gravity South %s -depth 8"
import os
import tempfile
import glob
import file
from ew.memphis.constants import META_HIRES, STDGEOM_MAINIMAGE, STDGEOM_HIRES, META_MAINIMAGEGEOM, META_HIRESIMAGEGEOM

def convert2memphis(pdfpath, savepath,hires=False):
	# get a temp dir to work in, change to it
	targetpath = os.path.abspath(savepath)
	tmpdir = tempfile.mkdtemp()
	os.chdir(tmpdir)
	print "Tmpdir =",tmpdir
	
	filename = os.path.basename(savepath)
	
	# prepare gs command and execute it in tmpdir
	cmdtoexecute = GSCMD + RENDERCMD + '"' + pdfpath + '"'
	os.system(cmdtoexecute)
	
	# find rendered pages
	foundpages = glob.glob("*.pgm")
	foundpages.sort()
	
	mf = file.MemphisFile(filename)
	mf.open()
	mf.info["title"] = filename

	for p in foundpages:
		# create the new page
		pagefilepath = os.path.join(tmpdir,p)
		mf.pages.append(p)
		
		# put the high res image version into the metadata of each page
		if hires:
			hirespath = "hires.%s" % (p)
			mf.pages.page_for(p).addMetaFile(p,hirespath)
			mf.pages.page_for(p).metadata[META_HIRES] = hirespath
			mf.pages.page_for(p).metadata[META_HIRESIMAGEGEOM] = STDGEOM_HIRES
		
		# create the proper rotated lo res version for the tablet, add it
		os.system(MOGRIFYCMD % (p))
		mf.pages.page_for(p).metadata[META_MAINIMAGEGEOM] = STDGEOM_MAINIMAGE
		mf.pages.page_for(p).setBaseImage(pagefilepath,isOriginal=True)
	
	mf.close()
	if not targetpath.endswith(".memphis.zip"):
		targetpath += ".memphis.zip"
	mf.saveZipTo(targetpath)
	os.system("/bin/rm -rf '" + tmpdir + "'")
	return targetpath
	
	
