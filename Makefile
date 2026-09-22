#!/usr/bin/env make -f
#
# Makefile for recipe static site generator
#

# ---------------------------------------------------------------------------
#
# General setup
#

# Set default target
.DEFAULT_GOAL := test

# Decide if use python3 or python
ifeq (, $(@shell which python3))
	py = python3
else
	py = python
endif
# Decide if use pip3 or pip
ifeq (, $(@shell which pip3))
	pip = pip3
else
	pip = pip
endif
# Decide if use firefox or firefox.exe
ifeq (, $(@shell which firefox.exe))
	browser = firefox.exe
else
	browser = firefox
endif


# Detect OS
OS = $(shell uname -s)

# Defaults
ECHO = echo

# Make adjustments based on OS
ifneq (, $(findstring CYGWIN, $(OS)))
	ECHO = /bin/echo -e
endif

# Colors and helptext
NO_COLOR	= \033[0m
ACTION		= \033[32;01m
OK_COLOR	= \033[32;01m
ERROR_COLOR	= \033[31;01m
WARN_COLOR	= \033[33;01m

# Which makefile am I in?
WHERE-AM-I = $(CURDIR)/$(word $(words $(MAKEFILE_LIST)),$(MAKEFILE_LIST))
THIS_MAKEFILE := $(call WHERE-AM-I)

# Echo some nice helptext based on the target comment
HELPTEXT = $(ECHO) "$(ACTION)--->" `egrep "^\# target: $(1) " $(THIS_MAKEFILE) | sed "s/\# target: $(1)[ ]*-[ ]* / /g"` "$(NO_COLOR)"



# ----------------------------------------------------------------------------
#
# Highlevel targets
#
# target: help                         - Displays help with targets available.
.PHONY:  help
help:
	@$(call HELPTEXT,$@)
	@echo "Usage:"
	@echo " make [target] ..."
	@echo "target:"
	@egrep "^# target:" Makefile | sed 's/# target: / /g'



# target: add-ssh                         - Add ssh key to agent
.PHONY: add-ssh
add-ssh:
	eval `ssh-agent -s`
	ssh-add <path/too/ssh-key>



# target: info                         - Displays versions.
.PHONY: info
info:
	@${py} --version
	@${py} -m pip --version
#@virtualenv --version



# target: validate                     - Validate code with pylint
.PHONY: validate
validate:
	@pylint --rcfile=.pylintrc app tests



# target: validate-docker              - Validate Dockerfile with hadolint
.PHONY: validate-docker
validate-docker:
	@docker run --rm -i hadolint/hadolint < docker/Dockerfile_prod
	@docker run --rm -i hadolint/hadolint < docker/Dockerfile_test



# target: validate-ci                  - Validate CircleCi config with CircleCi CLI
.PHONY: validate-ci
validate-ci:
	@circleci config validate



# target: test-integration             - Run tests in tests/integration with coverage.py
.PHONY: test-integration
test-integration: clean
	@$(ECHO) "$(ACTION)---> Running all tests in tests/integration" "$(NO_COLOR)"
	@${py} \
		-m coverage run --rcfile=.coveragerc \
		-m pytest -c pytest.ini tests/integration
	$(MAKE) clean-py



# target: test-unit                    - Run tests in tests/unit with coverage.py
.PHONY: test-unit
test-unit: clean
	@$(ECHO) "$(ACTION)---> Running all tests in tests/unit" "$(NO_COLOR)"
	@${py} \
		-m coverage run --rcfile=.coveragerc \
		-m pytest -c pytest.ini tests/unit
	$(MAKE) clean-py



# target: run-test test=test-file.py   - Run one test file
.PHONY: run-test
run-test:
	@${py} \
		-m pytest --pylint --pylint-rcfile=.pylintrc $(test)



## target: exec-tests                   - Run all tests in tests/ with coverage.py
.PHONY: exec-tests
exec-tests: test-unit test-integration



# target: test                         - Run tests and display code coverage
.PHONY: test
test: validate exec-tests
	${py} -m coverage report  --rcfile=.coveragerc
	$(MAKE) clean-cov



## target: test-html                    - Run tests and display detailed code coverage with html
.PHONY: test-html
test-html: exec-tests
	${py} -m coverage html  --rcfile=.coveragerc && ${browser} tests/coverage_html/index.html &



## target: clean-py                     - Remove generated python files
.PHONY: clean-py
clean-py:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.pytest_cache' -exec rm -fr {} +



## target: clean-cov                    - Remove generated coverage files
.PHONY: clean-cov
clean-cov:
	rm -f .coverage
	rm -rf tests/coverage_html



# target: clean                        - Remove all generated files
.PHONY: clean
clean: clean-py clean-cov
	find . -name '*~' -exec rm -f {} +
	find . -name '*.log*' -exec rm -fr {} +



# target: install                      - Install all Python packages specified in requirement.txt (requirements/prod.txt)
.PHONY: install
install:
	${pip} install -r requirements.txt



# target: install-dev                  - Install all Python packages specified in requirements/*
.PHONY: install-dev
install-dev:
	${pip} install -r requirements/dev.txt
	$(MAKE) install-deploy


# target: install-test                 - Install all Python packages specified in requirements/{test.txt, prod.txt}
.PHONY: install-test
install-test:
	${pip} install -r requirements/test.txt



# target: install-deploy                 - Install all Python packages specified in requirements/{deploy.txt} and ansible galaxy collections in ansible/requirements.yml
.PHONY: install-deploy
install-deploy:
	${pip} install -r requirements/deploy.txt
	${pip} install -r ~/.ansible/collections/ansible_collections/azure/azcollection/requirements.txt
	cd ansible && ansible-galaxy install -r requirements.yml

# Continuous security: use the same commands locally and in GitHub Actions.
IMAGE ?= local-microblog:kmom04
TRIVY_IMAGE ?= aquasec/trivy:latest
DOCKLE_IMAGE ?= goodwithtech/dockle:v0.4.15
TRIVY_FLAGS = --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --exit-code 1 --no-progress

# target: build-prod                   - Build the production image for security checks
.PHONY: build-prod
build-prod:
	docker build --pull -t $(IMAGE) -f docker/Dockerfile_prod .

# target: bandit                       - Scan application Python code, including low severity findings
.PHONY: bandit
bandit:
	${py} -m bandit -r app

# target: trivy-image                  - Scan the locally built production image
.PHONY: trivy-image
trivy-image:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v microblog-trivy-cache:/root/.cache/trivy $(TRIVY_IMAGE) \
		image $(TRIVY_FLAGS) $(IMAGE)

# target: trivy-fs                     - Scan the repository for vulnerabilities, secrets and misconfiguration
.PHONY: trivy-fs
trivy-fs:
	docker run --rm -v "$(CURDIR):/repo:ro" -w /repo \
		-v microblog-trivy-cache:/root/.cache/trivy $(TRIVY_IMAGE) \
		fs $(TRIVY_FLAGS) --skip-dirs .venv,venv,.deployment \
		--file-patterns 'dockerfile:docker/Dockerfile_*' \
		--file-patterns 'pip:requirements/.*\.txt' .

# target: dockle                       - Lint the production image using Dockle through Docker
.PHONY: dockle
dockle:
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v "$(CURDIR)/.dockleignore:/.dockleignore:ro" \
		$(DOCKLE_IMAGE) --exit-code 1 --exit-level warn $(IMAGE)

# target: security                     - Build and run all required security checks
.PHONY: security
security: build-prod
	$(MAKE) bandit
	$(MAKE) trivy-image
	$(MAKE) trivy-fs
	$(MAKE) dockle

# target: monitoring-up                - Start the complete local monitoring demo
.PHONY: monitoring-up
monitoring-up:
	${py} monitoring/render_local.py
	docker compose -f monitoring/compose.yml up -d --build

# target: monitoring-check             - Validate alert rules and check error-to-webhook delivery
.PHONY: monitoring-check
monitoring-check:
	docker compose -f monitoring/compose.yml run --rm --no-deps -v "$(CURDIR)/monitoring:/work:ro" -w /work --entrypoint promtool prometheus test rules rules.test.yml
	${py} monitoring/check.py

# target: monitoring-down              - Stop the local demo while preserving data
.PHONY: monitoring-down
monitoring-down:
	docker compose -f monitoring/compose.yml down