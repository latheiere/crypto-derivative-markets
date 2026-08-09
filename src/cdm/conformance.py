"""Access to portable conformance vectors shipped with the package."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any, Dict, Tuple

_VECTOR_FILES = (
    "datapoints.json",
    "funding-samples.json",
    "instrument-assessments.json",
    "instrument-classifications.json",
    "instrument-descriptors.json",
    "instrument-profiles.json",
    "instrument-references.json",
    "instrument-scenarios.json",
    "measurement-lineages.json",
    "native-identity-selectors.json",
    "open-interest-values.json",
)


def conformance_vector_names() -> Tuple[str, ...]:
    """Return the names of all bundled conformance vector sets."""

    return _VECTOR_FILES


def load_conformance_vectors(name: str) -> Dict[str, Any]:
    """Load one conformance vector set by filename."""

    if name not in _VECTOR_FILES:
        raise ValueError(f"unknown conformance vector set: {name!r}")
    resource = resources.files("cdm").joinpath("conformance").joinpath("v1").joinpath(name)
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):  # pragma: no cover - package integrity guard
        raise RuntimeError(f"conformance resource {name} is not an object")
    return value
