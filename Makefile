PYTHON ?= python3
VERSION ?= 0.1.0

.PHONY: check package
check:
	$(PYTHON) -m unittest discover -s tests -v
	sh -n scripts/package.sh

package: check
	sh scripts/package.sh "$(VERSION)"
