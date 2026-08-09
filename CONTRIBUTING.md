# Contributing

Contributions should preserve CDM as a provider-independent leaf library. Before proposing a change,
check [REQUIREMENTS.md](REQUIREMENTS.md) and explain the affected economic category, triggering
conditions, and reusable behavior.

## Development environment

Use an isolated virtual environment and install the project in editable mode:

```console
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Run the complete local verification:

```console
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy
.venv/bin/python -m pytest
PYTHONPATH=src .venv/bin/python tools/generate_vocabulary_reference.py --check
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

## Contract changes

A vocabulary or wire change must update, as applicable:

- immutable Python values and validation;
- JSON Schemas;
- codecs;
- valid and invalid conformance vectors;
- normative requirements;
- generated and explanatory documentation;
- compatibility or migration guidance.

Do not add provider names, native identifiers, catalog identifiers, network behavior, configuration,
storage, or service policy. Provider-native mappings belong to the integrating adapter project.

Pull requests should remain focused and include tests covering all known economically equivalent
cases, not only the observed input that motivated the change.

