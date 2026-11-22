PYTHON ?= python3
PIP := $(PYTHON) -m pip
PROJECT ?= demo-product
OUTPUT ?= ./work
WORKSPACE ?= $(OUTPUT)/$(PROJECT)
PLATFORM ?= unspecified

.DEFAULT_GOAL := help
.PHONY: help start discover install test check new status validate schema-check vendor vendor-check resolve fact propose override

help:
	@echo 'Product & Business Planning Skills'
	@echo '  make start                           Project menu + persistent guided discovery'
	@echo '  make discover PROJECT=name           Continuous discovery with input status list
	@echo '  make fact PROJECT=name               Select key and enter answer''
	@echo '  make resolve PROJECT=name            Select key and view saved answer'
	@echo '  make propose PROJECT=name            Select key and propose value'
	@echo '  make override PROJECT=name           Confirm an answer correction'
	@echo '  make install                         Install dependencies'
	@echo '  make vendor                          Install pinned upstream skills (online)'
	@echo '  make vendor-check                    Validate upstream catalog'
	@echo '  make new PROJECT=name                Create project without prompts'
	@echo '  make validate PROJECT=name           Validate project YAML'
	@echo '  make check                           Run offline checks'
	@echo '  python tools/interactive.py --help   Full CLI help'

start:
	$(PYTHON) tools/interactive.py start --output '$(OUTPUT)'

resolve fact propose override discover:
	$(PYTHON) tools/interactive.py $@ --project '$(PROJECT)' --output '$(OUTPUT)'

install:
	$(PIP) install -r requirements-dev.txt

vendor:
	$(PYTHON) tools/vendor_skills.py install

vendor-check:
	$(PYTHON) tools/vendor_skills.py check

new:
	$(PYTHON) tools/new_project.py --name '$(PROJECT)' --output '$(OUTPUT)' --platform '$(PLATFORM)'

status:
	$(PYTHON) tools/knowledge.py --workspace '$(WORKSPACE)' status

validate:
	$(PYTHON) tools/knowledge.py --workspace '$(WORKSPACE)' validate

schema-check:
	$(PYTHON) tools/validate_framework.py

test:
	$(PYTHON) -m unittest discover -s tests -v

check: vendor-check schema-check test
