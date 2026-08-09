from __future__ import annotations

import pytest

from cdm import (
    InstrumentDescriptorV1,
    InstrumentReferenceV1,
    NativeIdentityNamespace,
    NativeIdentityRole,
    NativeIdentitySelectionStatus,
    NativeIdentitySelectorV1,
    NativeIdentityV1,
    ValidationError,
    from_data,
    select_native_identity,
    to_data,
)


def _identity(value: str) -> NativeIdentityV1:
    return NativeIdentityV1(
        role=NativeIdentityRole.INSTRUMENT,
        namespace=NativeIdentityNamespace.REST_INSTRUMENT_CATALOG,
        value=value,
    )


def test_reference_round_trip_omits_an_empty_identity_container() -> None:
    reference = InstrumentReferenceV1(descriptor=InstrumentDescriptorV1())
    encoded = to_data(reference)
    assert "native_identities" not in encoded
    assert from_data(encoded) == reference


def test_exact_duplicate_identity_is_rejected() -> None:
    identity = _identity("native-primary-key")
    with pytest.raises(ValidationError) as error:
        InstrumentReferenceV1(
            descriptor=InstrumentDescriptorV1(),
            native_identities=(identity, identity),
        )
    assert error.value.code == "duplicate_identity"


def test_same_selector_aliases_produce_ambiguity_without_order_selection() -> None:
    primary = _identity("native-primary-key")
    alias = _identity("native-alias-key")
    selector = NativeIdentitySelectorV1(
        role=NativeIdentityRole.INSTRUMENT,
        namespace=NativeIdentityNamespace.REST_INSTRUMENT_CATALOG,
    )
    forward = select_native_identity((primary, alias), selector)
    reverse = select_native_identity((alias, primary), selector)
    assert forward.status is NativeIdentitySelectionStatus.AMBIGUOUS
    assert reverse.status is NativeIdentitySelectionStatus.AMBIGUOUS
    assert forward.identity is None
    assert reverse.identity is None


def test_selection_distinguishes_unique_and_missing_cardinality() -> None:
    identity = _identity("native-primary-key")
    exact_selector = NativeIdentitySelectorV1(
        role=NativeIdentityRole.INSTRUMENT,
        namespace=NativeIdentityNamespace.REST_INSTRUMENT_CATALOG,
    )
    different_selector = NativeIdentitySelectorV1(
        role=NativeIdentityRole.INSTRUMENT,
        namespace=NativeIdentityNamespace.REST_DERIVATIVE_STATUS,
    )
    unique = select_native_identity((identity,), exact_selector)
    missing = select_native_identity((identity,), different_selector)
    assert unique.status is NativeIdentitySelectionStatus.UNIQUE
    assert unique.identity == identity
    assert missing.status is NativeIdentitySelectionStatus.MISSING
    assert missing.identity is None


def test_namespace_requires_a_supported_protocol_and_canonical_scope() -> None:
    assert str(NativeIdentityNamespace("rest:instrument-catalog")) == ("rest:instrument-catalog")
    with pytest.raises(ValidationError):
        NativeIdentityNamespace("http:instrument-catalog")
    with pytest.raises(ValidationError):
        NativeIdentityNamespace("rest:InstrumentCatalog")
