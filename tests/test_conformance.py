from __future__ import annotations

from typing import Dict

import pytest
from jsonschema import FormatChecker
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for
from referencing import Registry, Resource

from cdm import (
    DecodeError,
    InstrumentDescriptorV1,
    InstrumentProfileV1,
    assess_instrument_descriptor,
    classify_instrument,
    conformance_vector_names,
    from_data,
    load_conformance_vectors,
    load_schemas,
    to_data,
)


def _validators() -> Dict[str, Validator]:
    schemas = load_schemas()
    registry = Registry().with_resources(
        (schema_id, Resource.from_contents(schema)) for schema_id, schema in schemas.items()
    )
    return {
        schema_id: validator_for(schema)(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for schema_id, schema in schemas.items()
    }


def test_conformance_vectors_match_codecs_and_schemas() -> None:
    validators = _validators()
    for vector_name in conformance_vector_names():
        vectors = load_conformance_vectors(vector_name)
        validator = validators[vectors["schema_id"]]
        for case in vectors["valid"]:
            value = case["value"]
            validator.validate(value)
            decoded = from_data(value)
            assert to_data(decoded) == value

            if isinstance(decoded, InstrumentProfileV1):
                classification = classify_instrument(decoded)
                expected = case["classification"]
                assert classification.payoff_family.value == expected["payoff_family"]
                assert classification.maturity_family.value == expected["maturity_family"]
            if isinstance(decoded, InstrumentDescriptorV1):
                assessment = assess_instrument_descriptor(decoded)
                assert assessment.state.value == case["assessment_state"]
                assert [issue.path for issue in assessment.issues] == case["issue_paths"]

        for case in vectors["invalid"]:
            value = case["value"]
            with pytest.raises(JsonSchemaValidationError):
                validator.validate(value)
            with pytest.raises(DecodeError) as error:
                from_data(value)
            assert error.value.code == case["error_code"]


def test_every_schema_has_exactly_one_conformance_vector_set() -> None:
    schema_ids = set(load_schemas())
    vector_schema_ids = [
        load_conformance_vectors(name)["schema_id"] for name in conformance_vector_names()
    ]
    assert len(vector_schema_ids) == len(set(vector_schema_ids))
    assert set(vector_schema_ids) == schema_ids


def test_schema_documents_are_fresh_values() -> None:
    first = load_schemas()
    first_schema = first[next(iter(first))]
    first_schema["title"] = "modified"
    second = load_schemas()
    assert all(schema.get("title") != "modified" for schema in second.values())
