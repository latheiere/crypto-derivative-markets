.PHONY: build docs-check format lint test verify

format:
	python -m ruff format .
	python -m ruff check --fix .

lint:
	python -m ruff check .
	python -m ruff format --check .
	python -m mypy

test:
	python -m pytest

docs-check:
	python tools/generate_vocabulary_reference.py --check

build:
	python -m build
	python -m twine check dist/*

verify: lint test docs-check build

