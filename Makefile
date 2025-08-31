.PHONY: all unit story lint lint-fix typecheck deps help

# Internal stamp to track dependency installation freshness
.deps-stamp: pyproject.toml
	@set -e; \
	if [ ! -f .deps-hash ]; then \
		echo "[deps] Initializing dependencies (poetry lock/install)..."; \
		poetry lock && poetry install; \
		shasum -a 256 pyproject.toml > .deps-hash; \
	else \
		if ! shasum -a 256 --status -c .deps-hash >/dev/null 2>&1; then \
			echo "[deps] pyproject.toml changed; updating dependencies..."; \
			poetry lock && poetry install; \
			shasum -a 256 pyproject.toml > .deps-hash; \
		else \
			echo "[deps] Dependencies up-to-date."; \
		fi; \
	fi; \
	touch .deps-stamp

deps: .deps-stamp

all: deps
	$(MAKE) lint-fix
	$(MAKE) typecheck
	$(MAKE) unit
	$(MAKE) story

unit: deps
	poetry run pytest --cov --cov-branch -q tests/unit

story: deps
	poetry run pytest -q tests/story

lint:
	poetry run ruff check .

lint-fix:
	poetry run ruff check . --fix

typecheck:
	poetry run pyright

help:
	@echo "Available targets:"
	@echo "  deps       - Run 'poetry lock' and 'poetry install' if pyproject.toml changed"
	@echo "  all        - Run deps, lint-fix, typecheck, unit, story"
	@echo "  unit       - Run unit tests with coverage (tests/unit)"
	@echo "  story      - Run story tests (tests/story)"
	@echo "  lint       - Run ruff without fixing"
	@echo "  lint-fix   - Run ruff with --fix"
	@echo "  typecheck  - Run pyright"
