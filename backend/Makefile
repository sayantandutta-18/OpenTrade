.PHONY: test lint typecheck run clean

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PYTEST ?= $(VENV)/bin/pytest
RUFF ?= $(VENV)/bin/ruff
MYPY ?= $(VENV)/bin/mypy
UVICORN ?= $(VENV)/bin/uvicorn

# Fallback for Windows if bin doesn't exist
ifeq ($(OS),Windows_NT)
	PYTHON := $(VENV)/Scripts/python.exe
	PYTEST := $(VENV)/Scripts/pytest.exe
	RUFF := $(VENV)/Scripts/ruff.exe
	MYPY := $(VENV)/Scripts/mypy.exe
	UVICORN := $(VENV)/Scripts/uvicorn.exe
endif

test:
	$(PYTEST) tests/ -v --cov=impactlab

lint:
	$(RUFF) check .
	$(RUFF) format --check .

typecheck:
	$(MYPY) src

run:
	$(UVICORN) impactlab.api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
