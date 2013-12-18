# Copyright 2010-2011 Ricoh Innovations, Inc.

SHELL=bash
SUBS = e_ink internal_decs launcher memphis services util

default:
	for i in $(SUBS); do \
		(cd $$i && $(MAKE)); done

clean:
	for i in $(SUBS); do \
		(cd $$i && $(MAKE) clean); done

test: 
	(cd test;for i in test_*.py; do PYTHONPATH=$(PYPATH) python $$i; done)
	for i in $(SUBS); \
		do (cd $$i; $(MAKE) test); done

copy:
	mkdir -p $(EW_PYTHON)/ew/test
	cp *.py $(EW_PYTHON)/ew
	cp test/*.py $(EW_PYTHON)/ew/test
	for i in $(SUBS); do \
		( cd $$i && $(MAKE) copy ); done

install:
	python -c "import compileall; compileall.compile_dir('.',1)"
	mkdir -p $(EW_PYTHON)/ew/test
	cp *.py *.pyc $(EW_PYTHON)/ew
	cp test/*.py test/*.pyc $(EW_PYTHON)/ew/test
	for i in $(SUBS); do \
		( cd $$i && $(MAKE) install ); done

.PHONY: clean default test install all
