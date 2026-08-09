"""Access to the JSON Schemas shipped with the installed distribution."""

from __future__ import annotations

import json
from importlib import resources
from typing import Dict, Mapping, Tuple

from .errors import UnknownSchemaError
from .models import (
    DATAPOINT_SCHEMA_ID,
    FUNDING_SAMPLE_SCHEMA_ID,
    INSTRUMENT_ASSESSMENT_SCHEMA_ID,
    INSTRUMENT_CLASSIFICATION_SCHEMA_ID,
    INSTRUMENT_DESCRIPTOR_SCHEMA_ID,
    INSTRUMENT_PROFILE_SCHEMA_ID,
    INSTRUMENT_REFERENCE_SCHEMA_ID,
    INSTRUMENT_SCENARIO_SCHEMA_ID,
    MEASUREMENT_LINEAGE_SCHEMA_ID,
    NATIVE_IDENTITY_SELECTOR_SCHEMA_ID,
    OPEN_INTEREST_VALUE_SCHEMA_ID,
)

_SCHEMA_FILES: Mapping[str, str] = {
    INSTRUMENT_DESCRIPTOR_SCHEMA_ID: "instrument-descriptor.schema.json",
    INSTRUMENT_REFERENCE_SCHEMA_ID: "instrument-reference.schema.json",
    NATIVE_IDENTITY_SELECTOR_SCHEMA_ID: "native-identity-selector.schema.json",
    INSTRUMENT_PROFILE_SCHEMA_ID: "instrument-profile.schema.json",
    INSTRUMENT_CLASSIFICATION_SCHEMA_ID: "instrument-classification.schema.json",
    INSTRUMENT_SCENARIO_SCHEMA_ID: "instrument-scenario.schema.json",
    INSTRUMENT_ASSESSMENT_SCHEMA_ID: "instrument-assessment.schema.json",
    DATAPOINT_SCHEMA_ID: "datapoint.schema.json",
    MEASUREMENT_LINEAGE_SCHEMA_ID: "measurement-lineage.schema.json",
    OPEN_INTEREST_VALUE_SCHEMA_ID: "open-interest-value.schema.json",
    FUNDING_SAMPLE_SCHEMA_ID: "funding-sample.schema.json",
}


def schema_ids() -> Tuple[str, ...]:
    """Return supported schema identifiers in deterministic order."""

    return tuple(sorted(_SCHEMA_FILES))


def load_schema(schema_id: str) -> Dict[str, object]:
    """Load a fresh JSON Schema document by stable identifier."""

    filename = _SCHEMA_FILES.get(schema_id)
    if filename is None:
        raise UnknownSchemaError(schema_id, "$.schema_id")
    resource = resources.files("cdm").joinpath("schemas").joinpath("v1").joinpath(filename)
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):  # pragma: no cover - package integrity guard
        raise RuntimeError(f"schema resource {filename} is not an object")
    return value


def load_schemas() -> Dict[str, Dict[str, object]]:
    """Load every schema keyed by its stable identifier."""

    return {schema_id: load_schema(schema_id) for schema_id in schema_ids()}
