# Copyright 2010-2011 Ricoh Innovations, Inc.

SHELL=bash


default:
	echo "Nothing to do for python leaf module"


clean:
	-rm -f *.pyc test/*.pyc

test:
	(cd test;for i in test_*.py; do echo "RUNNING test $$i"; PYTHONPATH=$(PYPATH) python $$i; echo "DONE test $$i" ; done)
	echo "TESTS COMPLETED for ew/internal_decs"

copy:
	mkdir -p $(EW_PYTHON)/ew/internal_decs/test
	cp *.py $(EW_PYTHON)/ew/internal_decs
	cp test/*.py $(EW_PYTHON)/ew/internal_decs/test

install:
	python -c "import compileall; compileall.compile_dir('.',1)"
	mkdir -p $(EW_PYTHON)/ew/internal_decs/test
	cp *.py *.pyc $(EW_PYTHON)/ew/internal_decs
	cp test/*.py test/*.pyc $(EW_PYTHON)/ew/internal_decs/test

.PHONY: clean default test install all
