from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from cdm import (
    DecodeError,
    InstrumentDescriptorV1,
    OpenInterestMeasure,
    OpenInterestValueV1,
    UnknownSchemaError,
    from_data,
    from_json,
    to_json,
)


def test_json_codec_is_canonical_and_round_trips() -> None:
    value = OpenInterestValueV1(
        amount=Decimal("1.2300"),
        measure=OpenInterestMeasure.BASE_QUANTITY,
    )
    encoded = to_json(value)
    assert encoded == (
        '{"amount":"1.23","measure":"base_quantity",'
        '"schema_id":"urn:cdm:schema:open-interest-value:1"}'
    )
    assert from_json(encoded) == OpenInterestValueV1(
        amount=Decimal("1.23"),
        measure=OpenInterestMeasure.BASE_QUANTITY,
    )


def test_unknown_schema_and_fields_are_rejected() -> None:
    with pytest.raises(UnknownSchemaError):
        from_data({"schema_id": "urn:cdm:schema:instrument-profile:2"})
    with pytest.raises(DecodeError) as error:
        from_data(
            {
                "schema_id": "urn:cdm:schema:instrument-descriptor:1",
                "consumer_policy": "opaque",
            }
        )
    assert error.value.code == "unknown_field"


def test_public_values_are_immutable() -> None:
    descriptor = InstrumentDescriptorV1()
    with pytest.raises(FrozenInstanceError):
        descriptor.instrument_kind = None  # type: ignore[misc]
