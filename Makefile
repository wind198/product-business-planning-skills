PYTHON ?= python3
PIP := $(PYTHON) -m pip
PROJECT ?= demo-product
OUTPUT ?= ./work
WORKSPACE ?= $(OUTPUT)/$(PROJECT)
PLATFORM ?= unspecified
KEY ?=
VALUE ?=
REF ?=

.DEFAULT_GOAL := help
.PHONY: help start install test check new status validate schema-check vendor vendor-check resolve fact propose override

help:
	@echo 'Product & Business Planning Skills'
	@echo '  make start                         Interactive project planning (recommended)'
	@echo '  make install                       Install dependencies'
	@echo '  make vendor                        Install selected pinned upstream skills (online)'
	@echo '  make vendor-check                  Verify upstream catalog structure'
	@echo '  make new PROJECT=name              Create a project non-interactively'
	@echo '  make status PROJECT=name           Print workflow/checkpoint for scripts'
	@echo '  make validate PROJECT=name         Validate project YAML'
	@echo '  make schema-check                  Validate framework templates and schemas'
	@echo '  make test                          Run Python tests'
	@echo '  make check                         Run all offline checks'
	@echo 'For scripting, see tools/knowledge.py --help (advanced).'

start:
	$(PYTHON) tools/interactive.py --output '$(OUTPUT)'

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

resolve:
	@test -n '$(KEY)' || (echo 'Required: KEY=canonical.key' >&2; exit 2)
	$(PYTHON) tools/knowledge.py --workspace '$(WORKSPACE)' resolve '$(KEY)'

fact propose override:
	@test -n '$(KEY)' && test -n '$(VALUE)' && test -n '$(REF)' || (echo 'Required: KEY=... VALUE=... REF=...' >&2; exit 2)
	$(PYTHON) tools/knowledge.py --workspace '$(WORKSPACE)' put --key '$(KEY)' --value '$(VALUE)' --source-ref '$(REF)' $(if $(filter propose,$@),--status proposed,--status confirmed) $(if $(filter override,$@),--override,)

validate:
	$(PYTHON) tools/knowledge.py --workspace '$(WORKSPACE)' validate

schema-check:
	$(PYTHON) tools/validate_framework.py

test:
	$(PYTHON) -m unittest discover -s tests -v

check: vendor-check schema-check test
