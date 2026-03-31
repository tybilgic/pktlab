.PHONY: build build-dpdkd install-py test test-dpdkd test-py fmt lint clean run-dev

build:
	@$(MAKE) build-dpdkd
	@$(MAKE) install-py

build-dpdkd:
	@printf '%s\n' 'dpdkd build scaffold is in place; Meson targets land in later tickets.'

install-py:
	@printf '%s\n' 'Python package scaffolding is in place; install wiring lands in later tickets.'

test:
	@$(MAKE) test-dpdkd
	@$(MAKE) test-py

test-dpdkd:
	@printf '%s\n' 'dpdkd tests are not implemented yet.'

test-py:
	@printf '%s\n' 'Python tests are not implemented yet.'

fmt:
	@printf '%s\n' 'Formatting targets land in a later ticket.'

lint:
	@printf '%s\n' 'Lint targets land in a later ticket.'

clean:
	@rm -rf build dist .pytest_cache .ruff_cache .mypy_cache

run-dev:
	@printf '%s\n' 'Development orchestration lands in a later ticket.'
