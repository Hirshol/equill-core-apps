# Copyright 2010-2011 Ricoh Innovations, Inc.

SHELL=bash


default:
	echo "Nothing to do for python leaf module"


clean:
	-rm -f *.pyc test/*.pyc

test:
	(cd test;for i in test_*.py; do PYTHONPATH=$(PYPATH) python $$i; done)

copy:
	mkdir -p $(EW_PYTHON)/ew/util/test
	cp *.py $(EW_PYTHON)/ew/util
	cp test/*.py $(EW_PYTHON)/ew/util/test

install:
	python -c "import compileall; compileall.compile_dir('.',1)"
	mkdir -p $(EW_PYTHON)/ew/util/test
	cp *.py *.pyc $(EW_PYTHON)/ew/util
	cp test/*.py test/*.pyc $(EW_PYTHON)/ew/util/test

.PHONY: clean default test install all
