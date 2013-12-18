# Copyright 2010-2011 Ricoh Innovations, Inc.
#ROOT=$(CURDIR)/root
PYTHON_VERSION=2.6
ROOT=/
RULB=$(ROOT)/usr/local/bin
ew_prefix=/usr/local/lib/ew
py_prefix=/usr/local/lib/ew/python
EW_ROOT=$(ROOT)/$(ew_prefix)
EW_LIB=$(EW_ROOT)
EW_BIN=$(EW_ROOT)/bin
EW_PYTHON=$(EW_ROOT)/python
EW_DECS=$(EW_ROOT)/data
EW_CONFIG=$(EW_ROOT)/config
EW_RESOURCE=$(EW_ROOT)/resource
PYPATH=$(PYTHONPATH):$(CURDIR):$(CURDIR)/../device_sdk
# NOTE: DISPLAY_SERVER is now configured and installed via the Makefile in 
# .../pentrackupdate/;  please run make install from that location to get newest
SUBS = ew
export

default: dirs
	echo $(MAKE)
	(cd ew; $(MAKE))

dirs:
	mkdir -p $(EW_LIB) $(EW_BIN) $(EW_PYTHON) $(EW_DOCS) $(EW_CONFIG) $(EW_RESOURCE)

clean:
	rm -rf ./root
	rm -f $(ROOT)/etc/init.d/tablet
	rm -f $(ROOT)/etc/init.d/mainrestart.sh
	rm -f $(ROOT)/etc/init.d/restartrestart.sh
	rm -f $(ROOT)/etc/mainrestart.conf
	rm -f $(ROOT)/etc/restartrestart.conf
	rm -f $(EW_ROOT)/python/ew/util/restartlib.py
	rm -f $(EW_ROOT)/python/ew/services/mainrestart.py
	rm -f $(EW_ROOT)/python/ew/services/restartrestart.py
	rm -f $(RULB)/rmanage
	rm -f $(RULB)/rcontrol
	(cd ew && $(MAKE) clean)

test: 
	( cd ew && $(MAKE) test )

patch-python:
	cp -v patch/python/$(PYTHON_VERSION)/* /usr/lib/python$(PYTHON_VERSION)/

copy: dirs
	cp -v config/* $(EW_CONFIG)
	echo "copying bin"
	cp -v bin/* $(EW_BIN) 
	echo "chmodding bin"
	chmod +x $(EW_BIN)/*
	# make /data dir (ROOT)/data
	echo "making /data/* dirs"
	mkdir $(ROOT)/data || true
	mkdir $(ROOT)/data/logs || true
	mkdir $(ROOT)/data/.ssh || true
	mkdir $(ROOT)/data/inbox || true
	mkdir $(ROOT)/data/cache || true
	mkdir $(ROOT)/data/templates || true
	mkdir $(ROOT)/data/etc || true
	mkdir $(ROOT)/data/internal_decs || true
	# fix perms
	chmod 777 $(ROOT)/data/logs 
	chmod 777 $(ROOT)/data/inbox
	chmod 777 $(ROOT)/data/cache
	chmod 777 $(ROOT)/data/templates
	chmod 777 $(ROOT)/data/etc
	chmod 700 $(ROOT)/data/.ssh
	chmod 777 $(ROOT)/data/internal_decs
	echo "copying resources"
	rsync -a resource/ $(EW_RESOURCE)/
	cp -v -f resource/images/static-infobar.pgm $(ROOT)/data/static-infobar.pgm || true
	rm $(EW_RESOURCE)/static-infobar.pgm || true
	ln -s /data/static-infobar.pgm $(EW_RESOURCE)/static-infobar.pgm || true
	( cd ew && $(MAKE) copy )

# problem:
install: install-real install-scripts

install-real: dirs
	cp -v config/* $(EW_CONFIG)
	echo "copying bin"
	cp -v bin/* $(EW_BIN)
	echo "chmodding"
	chmod +x $(EW_BIN)/*
	# RESTARTD CONFIG
	-mkdir $(ROOT)/etc || true
	cp -f config/mainrestart.conf $(ROOT)/etc/mainrestart.conf
	cp -f config/restartrestart.conf $(ROOT)/etc/restartrestart.conf
	# RESTARTD BIN
	-mkdir $(RULB) || true
	-mkdir $(ROOT)/etc/init.d || true
	-mkdir $(ROOT)/etc/rc0.d || true
	-mkdir $(ROOT)/etc/rc1.d || true
	-mkdir $(ROOT)/etc/rc2.d || true
	-mkdir $(ROOT)/etc/rc6.d || true
	cp -f bin/monte_carlo_kill.py $(RULB)/monte_carlo_kill.py
	chmod -f 755 $(RULB)/monte_carlo_kill.py
	cp -f bin/mainrestart.sh $(ROOT)/etc/init.d/mainrestart.sh
	chmod -f 755 $(ROOT)/etc/init.d/mainrestart.sh
	cp -f bin/restartrestart.sh $(ROOT)/etc/init.d/restartrestart.sh
	chmod -f 755 $(ROOT)/etc/init.d/restartrestart.sh
	cp -f bin/rmanage $(RULB)/rmanage
	chmod -f 755 $(RULB)/rmanage
	cp -f bin/tabletdaemons $(RULB)/tabletdaemons
	chmod -f 755 $(RULB)/tabletdaemons
	cp -f bin/mainrestart.sh $(RULB)/tablet
	chmod -f 755 $(RULB)/tablet
	cp -f bin/rcontrol $(RULB)/rcontrol
	chmod -f 755 $(RULB)/rcontrol
	ln -sf /usr/local/bin/rcontrol $(RULB)/audiod
	ln -sf /usr/local/bin/rcontrol $(RULB)/camd
	ln -sf /usr/local/bin/rcontrol $(RULB)/ds
	ln -sf /usr/local/bin/rcontrol $(RULB)/launcherd
	ln -sf /usr/local/bin/rcontrol $(RULB)/lud
	ln -sf /usr/local/bin/rcontrol $(RULB)/netmgr
	ln -sf /usr/local/bin/rcontrol $(RULB)/syncd
	# RESTARTD RC.D & INIT.D
	ln -s ../init.d/mainrestart.sh $(ROOT)/etc/rc2.d/S90mainrestart.sh || { echo "mainrestart start link exists";}
	ln -s ../init.d/mainrestart.sh $(ROOT)/etc/rc0.d/K10mainrestart.sh || { echo "mainrestart stop link exists";}
	ln -s ../init.d/mainrestart.sh $(ROOT)/etc/rc1.d/K10mainrestart.sh || { echo "mainrestart stop link exists";}
	ln -s ../init.d/mainrestart.sh $(ROOT)/etc/rc6.d/K10mainrestart.sh || { echo "mainrestart stop link exists";}
	
	# make /data dir (ROOT)/data
	mkdir $(ROOT)/data || true
	mkdir $(ROOT)/data/logs || true
	mkdir $(ROOT)/data/inbox || true
	mkdir $(ROOT)/data/cache || true
	mkdir $(ROOT)/data/templates || true
	mkdir $(ROOT)/data/etc || true
	mkdir $(ROOT)/data/internal_decs || true
	# fix perms
	chmod 777 $(ROOT)/data/logs 
	chmod 777 $(ROOT)/data/inbox
	chmod 777 $(ROOT)/data/cache
	chmod 777 $(ROOT)/data/templates
	chmod 777 $(ROOT)/data/etc
	chmod 777 $(ROOT)/data/internal_decs
	echo "copying resources"
	rsync -a resource/ $(EW_RESOURCE)/
	cp -v -f resource/images/static-infobar.pgm $(ROOT)/data/static-infobar.pgm || true
	rm $(EW_RESOURCE)/static-infobar.pgm || true
	ln -s /data/static-infobar.pgm $(EW_RESOURCE)/static-infobar.pgm || true
	( cd ew && $(MAKE) install )

install-scripts:
	mkdir -p $(ROOT)/etc/init.d || true
	mkdir -p $(ROOT)/etc/rc2.d || true
	
	rm $(ROOT)/etc/init.d/display_server.sh || true
	rm $(ROOT)/etc/init.d/camera_server.sh || true
	rm $(ROOT)/etc/init.d/launcher.sh || true
	rm $(ROOT)/etc/init.d/listing_updater.sh || true
	rm $(ROOT)/etc/init.d/ews_initialize_data.sh || true
	# CLEANUP OLD STYLE LAUNCHERS IN RC2.D
	rm $(ROOT)/etc/rc2.d/S??display_server.sh || true
	rm $(ROOT)/etc/rc2.d/S??camera_server.sh || true
	rm $(ROOT)/etc/rc2.d/S??launcher.sh || true
	rm $(ROOT)/etc/rc2.d/S??listing_updater.sh || true
	rm $(ROOT)/etc/rc2.d/S??ews_initialize_data.sh || true
	
	cp -v bin/display_server.sh $(ROOT)/etc/init.d/
	cp -v bin/camera_server.sh $(ROOT)/etc/init.d/
	cp -v bin/launcher.sh $(ROOT)/etc/init.d/
	cp -v bin/listing_updater.sh $(ROOT)/etc/init.d/
	cp -v bin/ews_initialize_data.sh $(ROOT)/etc/init.d/
	
	chmod +x $(EW_BIN)/sendimg.py
	chmod +x $(EW_BIN)/launcher_daemon.py
	chmod +x $(ROOT)/etc/init.d/display_server.sh
	chmod +x $(ROOT)/etc/init.d/camera_server.sh
	chmod +x $(EW_BIN)/listing_updater.py
	chmod +x $(ROOT)/etc/init.d/launcher.sh
	chmod +x $(ROOT)/etc/init.d/listing_updater.sh
	chmod +x $(ROOT)/etc/init.d/ews_initialize_data.sh
		
	mkdir -p $(RULB)/ || true
	cp -v bin/provision.py $(RULB)/ || true
	cp -v bin/provision $(RULB)/ || true
	cp -v bin/gadget_getty.py $(RULB)/ || true
	chmod +x $(RULB)/gadget_getty.py || true
	chmod +x $(RULB)/provision.py || true
	chmod +x $(RULB)/provision || true
	cp -v tools/* $(RULB)// || true
	(for f in tools/*; do \
	    p=$(RULB)/$$(basename $$f); \
	    if [ -f $$p ]; then chmod og=rx,u=rwx $$p; fi; \
	done) || true
	ln -s ../init.d/ews_initialize_data.sh $(ROOT)/etc/rc2.d/S80ews_initialize_data.sh || { echo "ews_initialize_data start link exists";}
	
	# mkdir & symlink 
	mkdir -p $(ROOT)/usr/local/lib/python2.6/dist-packages || true
	rm $(ROOT)/usr/local/lib/python2.6/dist-packages/ew  || true
	rm $(ROOT)/usr/local/lib/python2.6/dist-packages/sdk || true
	rm $(ROOT)/usr/local/lib/python2.6/dist-packages/sync || true
	rm $(ROOT)/usr/local/lib/python2.6/dist-packages/middleware || true
	ln -s $(py_prefix)/ew $(ROOT)/usr/local/lib/python2.6/dist-packages/ew
	ln -s $(py_prefix)/sdk $(ROOT)/usr/local/lib/python2.6/dist-packages/sdk
	ln -s $(py_prefix)/sync $(ROOT)/usr/local/lib/python2.6/dist-packages/sync
	ln -s $(py_prefix)/middleware $(ROOT)/usr/local/lib/python2.6/dist-packages/middleware

.PHONY: clean default test install all
