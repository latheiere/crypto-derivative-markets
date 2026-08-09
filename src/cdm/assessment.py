"""Assessment of incomplete, provider-independent instrument descriptors."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Set, cast

from .errors import ValidationError
from .models import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    ContractValueV1,
    DescriptorAssessmentState,
    DescriptorIssueCode,
    DescriptorIssueV1,
    FundingDescriptorV1,
    FundingMechanism,
    FundingTermsV1,
    InstrumentAssessmentV1,
    InstrumentCapability,
    InstrumentDescriptorV1,
    InstrumentKind,
    InstrumentProfileV1,
    MarginAssetRelationship,
    SettlementDescriptorV1,
    SettlementMethod,
    SettlementTermsV1,
)


def _missing(path: str) -> DescriptorIssueV1:
    return DescriptorIssueV1(
        code=DescriptorIssueCode.MISSING_ATTRIBUTE,
        path=path,
        message="required economic metadata is missing",
    )


def _inconsistent(path: str, message: str) -> DescriptorIssueV1:
    return DescriptorIssueV1(
        code=DescriptorIssueCode.INCONSISTENT_TERMS,
        path=path,
        message=message,
    )


def assess_instrument_descriptor(
    descriptor: InstrumentDescriptorV1,
    capability: InstrumentCapability = InstrumentCapability.COMPLETE_PROFILE,
) -> InstrumentAssessmentV1:
    """Assess only the neutral metadata required by one operation."""

    if not isinstance(descriptor, InstrumentDescriptorV1):
        raise ValidationError("invalid_type", "$.descriptor", "expected InstrumentDescriptorV1")
    if not isinstance(capability, InstrumentCapability):
        raise ValidationError("invalid_type", "$.capability", "expected InstrumentCapability")

    required: Set[str]
    if capability is InstrumentCapability.CLASSIFICATION:
        required = {
            "$.instrument_kind",
            "$.contract_value.unit",
            "$.settlement.asset_relationship",
        }
    elif capability is InstrumentCapability.OPEN_INTEREST_CONVERSION:
        required = {
            "$.contract_value.amount",
            "$.contract_value.unit",
            "$.settlement.asset_relationship",
        }
    elif capability in (
        InstrumentCapability.FUNDING_MECHANISM,
        InstrumentCapability.FUNDING_INTERVAL,
    ):
        required = {"$.instrument_kind", "$.funding.mechanism"}
    else:
        required = {
            "$.instrument_kind",
            "$.contract_value.amount",
            "$.contract_value.unit",
            "$.settlement.method",
            "$.settlement.asset_relationship",
            "$.margin_asset_relationship",
            "$.funding.mechanism",
        }

    issues: List[DescriptorIssueV1] = []
    if "$.instrument_kind" in required and descriptor.instrument_kind is None:
        issues.append(_missing("$.instrument_kind"))

    contract_value: Optional[ContractValueDescriptorV1] = descriptor.contract_value
    if "$.contract_value.amount" in required and (
        contract_value is None or contract_value.amount is None
    ):
        issues.append(_missing("$.contract_value.amount"))
    if "$.contract_value.unit" in required and (
        contract_value is None or contract_value.unit is None
    ):
        issues.append(_missing("$.contract_value.unit"))

    settlement: Optional[SettlementDescriptorV1] = descriptor.settlement
    if "$.settlement.method" in required and (settlement is None or settlement.method is None):
        issues.append(_missing("$.settlement.method"))
    if "$.settlement.asset_relationship" in required and (
        settlement is None or settlement.asset_relationship is None
    ):
        issues.append(_missing("$.settlement.asset_relationship"))

    if "$.margin_asset_relationship" in required and descriptor.margin_asset_relationship is None:
        issues.append(_missing("$.margin_asset_relationship"))

    funding: Optional[FundingDescriptorV1] = descriptor.funding
    if "$.funding.mechanism" in required and (funding is None or funding.mechanism is None):
        issues.append(_missing("$.funding.mechanism"))
    elif (
        capability in (InstrumentCapability.FUNDING_INTERVAL, InstrumentCapability.COMPLETE_PROFILE)
        and funding is not None
        and funding.mechanism is FundingMechanism.PERIODIC
    ):
        if funding.interval_seconds is None:
            issues.append(_missing("$.funding.interval_seconds"))
    elif (
        capability in (InstrumentCapability.FUNDING_INTERVAL, InstrumentCapability.COMPLETE_PROFILE)
        and funding is not None
        and funding.mechanism is not None
        and funding.interval_seconds is not None
    ):
        issues.append(
            _inconsistent(
                "$.funding.interval_seconds",
                "an interval is only valid for periodic funding",
            )
        )

    if (
        capability
        in (
            InstrumentCapability.FUNDING_MECHANISM,
            InstrumentCapability.FUNDING_INTERVAL,
            InstrumentCapability.COMPLETE_PROFILE,
        )
        and descriptor.instrument_kind is InstrumentKind.FUTURE
        and funding is not None
        and funding.mechanism is not None
        and funding.mechanism is not FundingMechanism.NONE
    ):
        issues.append(
            _inconsistent(
                "$.funding.mechanism",
                "a fixed-expiry future cannot carry perpetual funding terms",
            )
        )

    if issues:
        state = (
            DescriptorAssessmentState.INVALID
            if any(issue.code is DescriptorIssueCode.INCONSISTENT_TERMS for issue in issues)
            else DescriptorAssessmentState.INCOMPLETE
        )
        return InstrumentAssessmentV1(
            capability=capability,
            state=state,
            issues=tuple(issues),
        )

    if capability is not InstrumentCapability.COMPLETE_PROFILE:
        return InstrumentAssessmentV1(
            capability=capability,
            state=DescriptorAssessmentState.COMPLETE,
            issues=(),
        )

    complete_contract = cast(ContractValueDescriptorV1, contract_value)
    complete_settlement = cast(SettlementDescriptorV1, settlement)
    complete_funding = cast(FundingDescriptorV1, funding)
    profile = InstrumentProfileV1(
        instrument_kind=cast(InstrumentKind, descriptor.instrument_kind),
        contract_value=ContractValueV1(
            amount=cast(Decimal, complete_contract.amount),
            unit=cast(ContractValueUnit, complete_contract.unit),
        ),
        settlement=SettlementTermsV1(
            method=cast(SettlementMethod, complete_settlement.method),
            asset_relationship=cast(AssetRelationship, complete_settlement.asset_relationship),
        ),
        margin_asset_relationship=cast(
            MarginAssetRelationship, descriptor.margin_asset_relationship
        ),
        funding=FundingTermsV1(
            mechanism=cast(FundingMechanism, complete_funding.mechanism),
            interval_seconds=complete_funding.interval_seconds,
        ),
    )
    return InstrumentAssessmentV1(
        capability=capability,
        state=DescriptorAssessmentState.COMPLETE,
        issues=(),
        profile=profile,
    )
