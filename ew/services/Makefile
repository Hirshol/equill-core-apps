# Copyright 2011 Ricoh Innovations, Inc.

SHELL=bash


default:
	echo "Nothing to do for python leaf module"


clean:
	-rm -f *.pyc test/*.pyc

test:
	(cd test;for i in test_*.py; do PYTHONPATH=$(PYPATH) python $$i; done)

copy:
	mkdir -p $(EW_PYTHON)/ew/services/test
	cp *.py $(EW_PYTHON)/ew/services
	cp test/*.py $(EW_PYTHON)/ew/services/test

install:
	python -c "import compileall; compileall.compile_dir('.',1)"
	mkdir -p $(EW_PYTHON)/ew/services/test
	cp *.py *.pyc $(EW_PYTHON)/ew/services
	cp test/*.py test/*.pyc $(EW_PYTHON)/ew/services/test
	chmod -f 755 $(EW_PYTHON)/ew/services/mainrestart.py
	chmod -f 755 $(EW_PYTHON)/ew/services/restartrestart.py

.PHONY: clean default test install all
