from __future__ import annotations

from decimal import Decimal

import pytest

from cdm import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    DescriptorAssessmentState,
    FundingDescriptorV1,
    FundingMechanism,
    InstrumentCapability,
    InstrumentDescriptorV1,
    InstrumentKind,
    PayoffFamily,
    SettlementDescriptorV1,
    ValidationError,
    assess_instrument_descriptor,
    classify_instrument_descriptor,
)


def _classification_descriptor() -> InstrumentDescriptorV1:
    return InstrumentDescriptorV1(
        instrument_kind=InstrumentKind.PERPETUAL_SWAP,
        contract_value=ContractValueDescriptorV1(unit=ContractValueUnit.BASE),
        settlement=SettlementDescriptorV1(asset_relationship=AssetRelationship.QUOTE),
    )


def test_classification_requires_only_relevant_attributes() -> None:
    descriptor = _classification_descriptor()
    assessment = assess_instrument_descriptor(descriptor, InstrumentCapability.CLASSIFICATION)
    assert assessment.state is DescriptorAssessmentState.COMPLETE
    assert assessment.profile is None
    classification = classify_instrument_descriptor(descriptor)
    assert classification.payoff_family is PayoffFamily.LINEAR


def test_open_interest_conversion_has_distinct_requirements() -> None:
    descriptor = _classification_descriptor()
    assessment = assess_instrument_descriptor(
        descriptor,
        InstrumentCapability.OPEN_INTEREST_CONVERSION,
    )
    assert assessment.state is DescriptorAssessmentState.INCOMPLETE
    assert [issue.path for issue in assessment.issues] == ["$.contract_value.amount"]


def test_funding_interval_is_required_only_for_periodic_terms() -> None:
    descriptor = InstrumentDescriptorV1(
        instrument_kind=InstrumentKind.PERPETUAL_SWAP,
        funding=FundingDescriptorV1(mechanism=FundingMechanism.PERIODIC),
    )
    mechanism = assess_instrument_descriptor(
        descriptor,
        InstrumentCapability.FUNDING_MECHANISM,
    )
    interval = assess_instrument_descriptor(
        descriptor,
        InstrumentCapability.FUNDING_INTERVAL,
    )
    assert mechanism.state is DescriptorAssessmentState.COMPLETE
    assert interval.state is DescriptorAssessmentState.INCOMPLETE
    assert [issue.path for issue in interval.issues] == ["$.funding.interval_seconds"]


def test_fixed_expiry_funding_is_an_invalid_funding_capability() -> None:
    descriptor = InstrumentDescriptorV1(
        instrument_kind=InstrumentKind.FUTURE,
        funding=FundingDescriptorV1(mechanism=FundingMechanism.CONTINUOUS),
    )
    assessment = assess_instrument_descriptor(
        descriptor,
        InstrumentCapability.FUNDING_MECHANISM,
    )
    assert assessment.state is DescriptorAssessmentState.INVALID
    assert [issue.path for issue in assessment.issues] == ["$.funding.mechanism"]


def test_descriptor_does_not_coerce_scalar_types() -> None:
    with pytest.raises(ValidationError) as error:
        ContractValueDescriptorV1(amount=1, unit=ContractValueUnit.BASE)  # type: ignore[arg-type]
    assert error.value.code == "invalid_type"
    valid = ContractValueDescriptorV1(amount=Decimal("1"), unit=ContractValueUnit.BASE)
    assert valid.amount == Decimal("1")
