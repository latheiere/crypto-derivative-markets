"""Pure classification of complete economic profiles."""

from __future__ import annotations

from typing import Union, cast

from .assessment import assess_instrument_descriptor
from .errors import ValidationError
from .models import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    DescriptorAssessmentState,
    InstrumentCapability,
    InstrumentClassificationV1,
    InstrumentDescriptorV1,
    InstrumentKind,
    InstrumentProfileV1,
    InstrumentScenarioV1,
    MaturityFamily,
    PayoffFamily,
    SettlementDescriptorV1,
)


def classify_payoff(
    contract_value_unit: ContractValueUnit,
    settlement_asset_relationship: AssetRelationship,
) -> PayoffFamily:
    """Classify payoff economics from only the two relevant relationships."""

    if settlement_asset_relationship is AssetRelationship.THIRD:
        return PayoffFamily.QUANTO
    if (
        contract_value_unit is ContractValueUnit.BASE
        and settlement_asset_relationship is AssetRelationship.QUOTE
    ):
        return PayoffFamily.LINEAR
    if (
        contract_value_unit is ContractValueUnit.QUOTE
        and settlement_asset_relationship is AssetRelationship.BASE
    ):
        return PayoffFamily.INVERSE
    return PayoffFamily.OTHER


def classify_maturity(instrument_kind: InstrumentKind) -> MaturityFamily:
    """Classify maturity behavior from the lifecycle kind alone."""

    return (
        MaturityFamily.OPEN_ENDED
        if instrument_kind is InstrumentKind.PERPETUAL_SWAP
        else MaturityFamily.FIXED_EXPIRY
    )


def classify_instrument(profile: InstrumentProfileV1) -> InstrumentClassificationV1:
    """Classify an economic profile without provider or catalog knowledge."""

    return InstrumentClassificationV1(
        payoff_family=classify_payoff(
            profile.contract_value.unit,
            profile.settlement.asset_relationship,
        ),
        maturity_family=classify_maturity(profile.instrument_kind),
    )


def classify_instrument_descriptor(
    descriptor: InstrumentDescriptorV1,
) -> InstrumentClassificationV1:
    """Classify a descriptor using only classification-relevant attributes."""

    assessment = assess_instrument_descriptor(descriptor, InstrumentCapability.CLASSIFICATION)
    if assessment.state is not DescriptorAssessmentState.COMPLETE:
        issue = assessment.issues[0]
        raise ValidationError(
            "descriptor_not_classifiable",
            issue.path,
            "classification-relevant economic metadata is incomplete or inconsistent",
        )
    contract_value = cast(ContractValueDescriptorV1, descriptor.contract_value)
    settlement = cast(SettlementDescriptorV1, descriptor.settlement)
    return InstrumentClassificationV1(
        payoff_family=classify_payoff(
            cast(ContractValueUnit, contract_value.unit),
            cast(AssetRelationship, settlement.asset_relationship),
        ),
        maturity_family=classify_maturity(cast(InstrumentKind, descriptor.instrument_kind)),
    )


def instrument_scenario(
    instrument: Union[InstrumentProfileV1, InstrumentDescriptorV1],
) -> InstrumentScenarioV1:
    """Build the canonical amount-independent scenario key for an instrument."""

    if isinstance(instrument, InstrumentProfileV1):
        instrument_kind = instrument.instrument_kind
        contract_value_unit = instrument.contract_value.unit
        settlement_relationship = instrument.settlement.asset_relationship
        classification = classify_instrument(instrument)
    elif isinstance(instrument, InstrumentDescriptorV1):
        classification = classify_instrument_descriptor(instrument)
        contract_value = cast(ContractValueDescriptorV1, instrument.contract_value)
        settlement = cast(SettlementDescriptorV1, instrument.settlement)
        instrument_kind = cast(InstrumentKind, instrument.instrument_kind)
        contract_value_unit = cast(ContractValueUnit, contract_value.unit)
        settlement_relationship = cast(AssetRelationship, settlement.asset_relationship)
    else:
        raise ValidationError(
            "invalid_type",
            "$.instrument",
            "expected InstrumentProfileV1 or InstrumentDescriptorV1",
        )
    return InstrumentScenarioV1(
        instrument_kind=instrument_kind,
        contract_value_unit=contract_value_unit,
        settlement_asset_relationship=settlement_relationship,
        payoff_family=classification.payoff_family,
        maturity_family=classification.maturity_family,
    )
