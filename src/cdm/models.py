"""Immutable, provider-independent economic contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import ClassVar, Dict, FrozenSet, Mapping, Optional, Tuple

from .errors import ValidationError

INSTRUMENT_PROFILE_SCHEMA_ID = "urn:cdm:schema:instrument-profile:1"
INSTRUMENT_CLASSIFICATION_SCHEMA_ID = "urn:cdm:schema:instrument-classification:1"
DATAPOINT_SCHEMA_ID = "urn:cdm:schema:datapoint:1"
MEASUREMENT_LINEAGE_SCHEMA_ID = "urn:cdm:schema:measurement-lineage:1"
INSTRUMENT_DESCRIPTOR_SCHEMA_ID = "urn:cdm:schema:instrument-descriptor:1"
INSTRUMENT_ASSESSMENT_SCHEMA_ID = "urn:cdm:schema:instrument-assessment:1"
OPEN_INTEREST_VALUE_SCHEMA_ID = "urn:cdm:schema:open-interest-value:1"
FUNDING_SAMPLE_SCHEMA_ID = "urn:cdm:schema:funding-sample:1"
INSTRUMENT_SCENARIO_SCHEMA_ID = "urn:cdm:schema:instrument-scenario:1"
INSTRUMENT_REFERENCE_SCHEMA_ID = "urn:cdm:schema:instrument-reference:1"
NATIVE_IDENTITY_SELECTOR_SCHEMA_ID = "urn:cdm:schema:native-identity-selector:1"


class InstrumentKind(str, Enum):
    """Lifecycle shape of a derivative contract."""

    PERPETUAL_SWAP = "perpetual_swap"
    FUTURE = "future"


class ContractValueUnit(str, Enum):
    """Economic unit in which one contract's fixed value is expressed."""

    BASE = "base"
    QUOTE = "quote"


class SettlementMethod(str, Enum):
    """How contractual obligations are discharged."""

    CASH = "cash"
    PHYSICAL = "physical"


class AssetRelationship(str, Enum):
    """Relationship between an asset role and the price pair."""

    BASE = "base"
    QUOTE = "quote"
    THIRD = "third"


class MarginAssetRelationship(str, Enum):
    """Relationship of the margin asset to other economic roles."""

    BASE = "base"
    QUOTE = "quote"
    SETTLEMENT = "settlement"
    THIRD = "third"


class FundingMechanism(str, Enum):
    """How an open-ended contract transfers funding between positions."""

    NONE = "none"
    PERIODIC = "periodic"
    CONTINUOUS = "continuous"


class PayoffFamily(str, Enum):
    """Canonical family derived from contract value and settlement roles."""

    LINEAR = "linear"
    INVERSE = "inverse"
    QUANTO = "quanto"
    OTHER = "other"


class MaturityFamily(str, Enum):
    """Canonical maturity behavior."""

    OPEN_ENDED = "open_ended"
    FIXED_EXPIRY = "fixed_expiry"


class DataPointKind(str, Enum):
    """Canonical market-data meaning independent of source field names."""

    OPEN_INTEREST_CONTRACT_COUNT = "open_interest.contract_count"
    OPEN_INTEREST_BASE_QUANTITY = "open_interest.base_quantity"
    OPEN_INTEREST_NOTIONAL = "open_interest.notional"
    FUNDING_INDICATIVE_RATE = "funding.indicative_rate"
    FUNDING_NEXT_RATE = "funding.next_rate"
    FUNDING_SETTLED_RATE = "funding.settled_rate"
    FUNDING_INTERVAL = "funding.interval"
    FUNDING_PREMIUM_RATE = "funding.premium_rate"
    FUNDING_INTEREST_RATE = "funding.interest_rate"
    FUNDING_RATE_FLOOR = "funding.rate_floor"
    FUNDING_RATE_CAP = "funding.rate_cap"


class TemporalMode(str, Enum):
    """Time semantics of a datapoint."""

    CURRENT = "current"
    NEXT = "next"
    SETTLED = "settled"
    HISTORICAL = "historical"


class MeasurementUnit(str, Enum):
    """Canonical unit class carried by a datapoint."""

    CONTRACT_COUNT = "contract_count"
    BASE_QUANTITY = "base_quantity"
    NOTIONAL = "notional"
    RATE_FRACTION = "rate_fraction"
    DURATION_SECONDS = "duration_seconds"


class NotionalDenomination(str, Enum):
    """Economic denomination of a notional value."""

    BASE = "base"
    QUOTE = "quote"
    SETTLEMENT = "settlement"
    REPORTING = "reporting"


class DerivationKind(str, Enum):
    """How a measurement enters or changes within a calculation lineage."""

    NATIVE_REPORTED = "native_reported"
    PROVIDER_FORMULA = "provider_formula"
    CANONICAL_CONVERSION = "canonical_conversion"
    ESTIMATED = "estimated"


class DescriptorIssueCode(str, Enum):
    """Machine-readable reason that a descriptor cannot form a profile."""

    MISSING_ATTRIBUTE = "missing_attribute"
    INCONSISTENT_TERMS = "inconsistent_terms"


class DescriptorAssessmentState(str, Enum):
    """Completeness state of a canonical instrument descriptor."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"


class InstrumentCapability(str, Enum):
    """Neutral operation whose metadata requirements are being assessed."""

    CLASSIFICATION = "classification"
    OPEN_INTEREST_CONVERSION = "open_interest_conversion"
    FUNDING_MECHANISM = "funding_mechanism"
    FUNDING_INTERVAL = "funding_interval"
    COMPLETE_PROFILE = "complete_profile"


class OpenInterestMeasure(str, Enum):
    """Economic measure represented by an open-interest value."""

    CONTRACT_COUNT = "contract_count"
    BASE_QUANTITY = "base_quantity"
    NOTIONAL = "notional"


class FundingRateKind(str, Enum):
    """Lifecycle meaning of a funding-rate sample."""

    INDICATIVE = "indicative"
    NEXT = "next"
    SETTLED = "settled"


class FundingIntervalKind(str, Enum):
    """Evidence available for a funding sample's accrual interval."""

    EXPLICIT_DURATION = "explicit_duration"
    OBSERVED_WINDOW = "observed_window"
    PROTOCOL_SCHEDULE = "protocol_schedule"
    UNSPECIFIED = "unspecified"


class NativeIdentityRole(str, Enum):
    """Semantic role played by an opaque native identity."""

    INSTRUMENT = "instrument"
    PAIR = "pair"
    UNDERLYING = "underlying"
    INDEX = "index"
    SETTLEMENT_ASSET = "settlement_asset"
    PRODUCT_FAMILY = "product_family"
    OTHER = "other"


class NativeIdentitySelectionStatus(str, Enum):
    """Cardinality outcome of exact native-identity selection."""

    UNIQUE = "unique"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"


_METHOD_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
NATIVE_IDENTITY_NAMESPACE_PATTERN = (
    r"^(?:rest|websocket|fix|rpc)(?::[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*)*$"
)
_NATIVE_IDENTITY_NAMESPACE_PATTERN = re.compile(NATIVE_IDENTITY_NAMESPACE_PATTERN)


def _require_enum(value: object, expected: type, path: str) -> None:
    if not isinstance(value, expected):
        raise ValidationError("invalid_type", path, f"expected {expected.__name__}")


def _require_positive_decimal(value: object, path: str) -> None:
    if not isinstance(value, Decimal):
        raise ValidationError("invalid_type", path, "expected Decimal")
    if not value.is_finite() or value <= 0:
        raise ValidationError("invalid_value", path, "expected a finite value greater than zero")


class NativeIdentityNamespace(str):
    """Validated protocol identity domain with optional neutral scopes."""

    REST: ClassVar[NativeIdentityNamespace]
    REST_INSTRUMENT_CATALOG: ClassVar[NativeIdentityNamespace]
    REST_DERIVATIVE_STATUS: ClassVar[NativeIdentityNamespace]
    WEBSOCKET: ClassVar[NativeIdentityNamespace]
    FIX: ClassVar[NativeIdentityNamespace]
    RPC: ClassVar[NativeIdentityNamespace]

    def __new__(cls, value: str) -> NativeIdentityNamespace:
        if not isinstance(value, str):
            raise ValidationError("invalid_type", "$.namespace", "expected a string")
        if not _NATIVE_IDENTITY_NAMESPACE_PATTERN.fullmatch(value):
            raise ValidationError(
                "invalid_value",
                "$.namespace",
                "expected a supported protocol identity namespace",
            )
        return str.__new__(cls, value)


NativeIdentityNamespace.REST = NativeIdentityNamespace("rest")
NativeIdentityNamespace.REST_INSTRUMENT_CATALOG = NativeIdentityNamespace("rest:instrument-catalog")
NativeIdentityNamespace.REST_DERIVATIVE_STATUS = NativeIdentityNamespace("rest:derivative-status")
NativeIdentityNamespace.WEBSOCKET = NativeIdentityNamespace("websocket")
NativeIdentityNamespace.FIX = NativeIdentityNamespace("fix")
NativeIdentityNamespace.RPC = NativeIdentityNamespace("rpc")


def standard_native_identity_namespaces() -> Tuple[NativeIdentityNamespace, ...]:
    """Return standard protocol identity namespaces in deterministic order."""

    return (
        NativeIdentityNamespace.REST,
        NativeIdentityNamespace.REST_INSTRUMENT_CATALOG,
        NativeIdentityNamespace.REST_DERIVATIVE_STATUS,
        NativeIdentityNamespace.WEBSOCKET,
        NativeIdentityNamespace.FIX,
        NativeIdentityNamespace.RPC,
    )


@dataclass(frozen=True)
class NativeIdentityV1:
    """Opaque native value qualified by semantic role and protocol domain."""

    role: NativeIdentityRole
    namespace: NativeIdentityNamespace
    value: str

    def __post_init__(self) -> None:
        _require_enum(self.role, NativeIdentityRole, "$.role")
        if not isinstance(self.namespace, NativeIdentityNamespace):
            raise ValidationError(
                "invalid_type",
                "$.namespace",
                "expected NativeIdentityNamespace",
            )
        if not isinstance(self.value, str):
            raise ValidationError("invalid_type", "$.value", "expected a string")
        if not self.value:
            raise ValidationError("invalid_value", "$.value", "expected a non-empty value")


@dataclass(frozen=True)
class NativeIdentitySelectorV1:
    """Exact role-and-namespace requirement for a native identity."""

    schema_id: ClassVar[str] = NATIVE_IDENTITY_SELECTOR_SCHEMA_ID

    role: NativeIdentityRole
    namespace: NativeIdentityNamespace

    def __post_init__(self) -> None:
        _require_enum(self.role, NativeIdentityRole, "$.role")
        if not isinstance(self.namespace, NativeIdentityNamespace):
            raise ValidationError(
                "invalid_type",
                "$.namespace",
                "expected NativeIdentityNamespace",
            )

    def matches(self, identity: NativeIdentityV1) -> bool:
        """Return whether an identity has this exact role and namespace."""

        if not isinstance(identity, NativeIdentityV1):
            raise ValidationError("invalid_type", "$.identity", "expected NativeIdentityV1")
        return identity.role is self.role and identity.namespace == self.namespace


@dataclass(frozen=True)
class ContractValueV1:
    """Fixed economic value represented by one contract."""

    amount: Decimal
    unit: ContractValueUnit

    def __post_init__(self) -> None:
        _require_positive_decimal(self.amount, "$.contract_value.amount")
        _require_enum(self.unit, ContractValueUnit, "$.contract_value.unit")


@dataclass(frozen=True)
class SettlementTermsV1:
    """Settlement behavior without identifying a concrete asset."""

    method: SettlementMethod
    asset_relationship: AssetRelationship

    def __post_init__(self) -> None:
        _require_enum(self.method, SettlementMethod, "$.settlement.method")
        _require_enum(
            self.asset_relationship,
            AssetRelationship,
            "$.settlement.asset_relationship",
        )


@dataclass(frozen=True)
class FundingTermsV1:
    """Funding behavior for an open-ended derivative."""

    mechanism: FundingMechanism
    interval_seconds: Optional[int] = None

    def __post_init__(self) -> None:
        _require_enum(self.mechanism, FundingMechanism, "$.funding.mechanism")
        if self.mechanism is FundingMechanism.PERIODIC:
            if type(self.interval_seconds) is not int or self.interval_seconds <= 0:
                raise ValidationError(
                    "invalid_value",
                    "$.funding.interval_seconds",
                    "periodic funding requires a positive integer interval",
                )
        elif self.interval_seconds is not None:
            raise ValidationError(
                "invalid_value",
                "$.funding.interval_seconds",
                "an interval is only valid for periodic funding",
            )


@dataclass(frozen=True)
class ContractValueDescriptorV1:
    """Possibly incomplete contract-value terms from a neutral catalog view."""

    amount: Optional[Decimal] = None
    unit: Optional[ContractValueUnit] = None

    def __post_init__(self) -> None:
        if self.amount is not None:
            _require_positive_decimal(self.amount, "$.contract_value.amount")
        if self.unit is not None:
            _require_enum(self.unit, ContractValueUnit, "$.contract_value.unit")


@dataclass(frozen=True)
class SettlementDescriptorV1:
    """Possibly incomplete neutral settlement terms."""

    method: Optional[SettlementMethod] = None
    asset_relationship: Optional[AssetRelationship] = None

    def __post_init__(self) -> None:
        if self.method is not None:
            _require_enum(self.method, SettlementMethod, "$.settlement.method")
        if self.asset_relationship is not None:
            _require_enum(
                self.asset_relationship,
                AssetRelationship,
                "$.settlement.asset_relationship",
            )


@dataclass(frozen=True)
class FundingDescriptorV1:
    """Possibly incomplete neutral funding terms."""

    mechanism: Optional[FundingMechanism] = None
    interval_seconds: Optional[int] = None

    def __post_init__(self) -> None:
        if self.mechanism is not None:
            _require_enum(self.mechanism, FundingMechanism, "$.funding.mechanism")
        if self.interval_seconds is not None and (
            type(self.interval_seconds) is not int or self.interval_seconds <= 0
        ):
            raise ValidationError(
                "invalid_value",
                "$.funding.interval_seconds",
                "a supplied funding interval must be a positive integer",
            )


@dataclass(frozen=True)
class InstrumentDescriptorV1:
    """A canonical instrument description that may lack required metadata."""

    schema_id: ClassVar[str] = INSTRUMENT_DESCRIPTOR_SCHEMA_ID

    instrument_kind: Optional[InstrumentKind] = None
    contract_value: Optional[ContractValueDescriptorV1] = None
    settlement: Optional[SettlementDescriptorV1] = None
    margin_asset_relationship: Optional[MarginAssetRelationship] = None
    funding: Optional[FundingDescriptorV1] = None

    def __post_init__(self) -> None:
        if self.instrument_kind is not None:
            _require_enum(self.instrument_kind, InstrumentKind, "$.instrument_kind")
        if self.contract_value is not None and not isinstance(
            self.contract_value, ContractValueDescriptorV1
        ):
            raise ValidationError(
                "invalid_type",
                "$.contract_value",
                "expected ContractValueDescriptorV1",
            )
        if self.settlement is not None and not isinstance(self.settlement, SettlementDescriptorV1):
            raise ValidationError("invalid_type", "$.settlement", "expected SettlementDescriptorV1")
        if self.margin_asset_relationship is not None:
            _require_enum(
                self.margin_asset_relationship,
                MarginAssetRelationship,
                "$.margin_asset_relationship",
            )
        if self.funding is not None and not isinstance(self.funding, FundingDescriptorV1):
            raise ValidationError("invalid_type", "$.funding", "expected FundingDescriptorV1")


@dataclass(frozen=True)
class InstrumentReferenceV1:
    """Economic descriptor paired with optional opaque native identities."""

    schema_id: ClassVar[str] = INSTRUMENT_REFERENCE_SCHEMA_ID

    descriptor: InstrumentDescriptorV1
    native_identities: Tuple[NativeIdentityV1, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, InstrumentDescriptorV1):
            raise ValidationError(
                "invalid_type",
                "$.descriptor",
                "expected InstrumentDescriptorV1",
            )
        if type(self.native_identities) is not tuple:
            raise ValidationError(
                "invalid_type",
                "$.native_identities",
                "expected a tuple",
            )
        seen = set()
        for index, identity in enumerate(self.native_identities):
            if not isinstance(identity, NativeIdentityV1):
                raise ValidationError(
                    "invalid_type",
                    f"$.native_identities[{index}]",
                    "expected NativeIdentityV1",
                )
            if identity in seen:
                raise ValidationError(
                    "duplicate_identity",
                    f"$.native_identities[{index}]",
                    "an exact native identity may appear only once",
                )
            seen.add(identity)


@dataclass(frozen=True)
class NativeIdentitySelectionV1:
    """Structured cardinality result for exact native-identity selection."""

    selector: NativeIdentitySelectorV1
    status: NativeIdentitySelectionStatus
    candidates: Tuple[NativeIdentityV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.selector, NativeIdentitySelectorV1):
            raise ValidationError(
                "invalid_type",
                "$.selector",
                "expected NativeIdentitySelectorV1",
            )
        _require_enum(self.status, NativeIdentitySelectionStatus, "$.status")
        if type(self.candidates) is not tuple or not all(
            isinstance(candidate, NativeIdentityV1) for candidate in self.candidates
        ):
            raise ValidationError(
                "invalid_type",
                "$.candidates",
                "expected a NativeIdentityV1 tuple",
            )
        if not all(self.selector.matches(candidate) for candidate in self.candidates):
            raise ValidationError(
                "inconsistent_selection",
                "$.candidates",
                "every candidate must match the selector",
            )
        expected_status = (
            NativeIdentitySelectionStatus.MISSING
            if not self.candidates
            else NativeIdentitySelectionStatus.UNIQUE
            if len(self.candidates) == 1
            else NativeIdentitySelectionStatus.AMBIGUOUS
        )
        if self.status is not expected_status:
            raise ValidationError(
                "inconsistent_selection",
                "$.status",
                "selection status must match candidate cardinality",
            )

    @property
    def identity(self) -> Optional[NativeIdentityV1]:
        """Return the sole identity only when selection is unique."""

        if self.status is NativeIdentitySelectionStatus.UNIQUE:
            return self.candidates[0]
        return None


@dataclass(frozen=True)
class DescriptorIssueV1:
    """Structured issue produced while completing an instrument descriptor."""

    code: DescriptorIssueCode
    path: str
    message: str

    def __post_init__(self) -> None:
        _require_enum(self.code, DescriptorIssueCode, "$.issues[].code")
        if not isinstance(self.path, str) or not self.path.startswith("$."):
            raise ValidationError(
                "invalid_value", "$.issues[].path", "expected a canonical field path"
            )
        if not isinstance(self.message, str) or not self.message:
            raise ValidationError(
                "invalid_value", "$.issues[].message", "expected a non-empty message"
            )


@dataclass(frozen=True)
class InstrumentProfileV1:
    """Complete economic profile needed for neutral classification."""

    schema_id: ClassVar[str] = INSTRUMENT_PROFILE_SCHEMA_ID

    instrument_kind: InstrumentKind
    contract_value: ContractValueV1
    settlement: SettlementTermsV1
    margin_asset_relationship: MarginAssetRelationship
    funding: FundingTermsV1

    def __post_init__(self) -> None:
        _require_enum(self.instrument_kind, InstrumentKind, "$.instrument_kind")
        if not isinstance(self.contract_value, ContractValueV1):
            raise ValidationError("invalid_type", "$.contract_value", "expected ContractValueV1")
        if not isinstance(self.settlement, SettlementTermsV1):
            raise ValidationError("invalid_type", "$.settlement", "expected SettlementTermsV1")
        _require_enum(
            self.margin_asset_relationship,
            MarginAssetRelationship,
            "$.margin_asset_relationship",
        )
        if not isinstance(self.funding, FundingTermsV1):
            raise ValidationError("invalid_type", "$.funding", "expected FundingTermsV1")
        if (
            self.instrument_kind is InstrumentKind.FUTURE
            and self.funding.mechanism is not FundingMechanism.NONE
        ):
            raise ValidationError(
                "inconsistent_terms",
                "$.funding.mechanism",
                "a fixed-expiry future cannot carry perpetual funding terms",
            )


@dataclass(frozen=True)
class InstrumentClassificationV1:
    """Deterministic classification of an instrument profile."""

    schema_id: ClassVar[str] = INSTRUMENT_CLASSIFICATION_SCHEMA_ID

    payoff_family: PayoffFamily
    maturity_family: MaturityFamily

    def __post_init__(self) -> None:
        _require_enum(self.payoff_family, PayoffFamily, "$.payoff_family")
        _require_enum(self.maturity_family, MaturityFamily, "$.maturity_family")


@dataclass(frozen=True)
class InstrumentScenarioV1:
    """Amount-independent scenario key shared across neutral integrations."""

    schema_id: ClassVar[str] = INSTRUMENT_SCENARIO_SCHEMA_ID
    descriptor_schema_id: ClassVar[str] = INSTRUMENT_DESCRIPTOR_SCHEMA_ID
    classification_schema_id: ClassVar[str] = INSTRUMENT_CLASSIFICATION_SCHEMA_ID

    instrument_kind: InstrumentKind
    contract_value_unit: ContractValueUnit
    settlement_asset_relationship: AssetRelationship
    payoff_family: PayoffFamily
    maturity_family: MaturityFamily

    def __post_init__(self) -> None:
        _require_enum(self.instrument_kind, InstrumentKind, "$.instrument_kind")
        _require_enum(self.contract_value_unit, ContractValueUnit, "$.contract_value_unit")
        _require_enum(
            self.settlement_asset_relationship,
            AssetRelationship,
            "$.settlement_asset_relationship",
        )
        _require_enum(self.payoff_family, PayoffFamily, "$.payoff_family")
        _require_enum(self.maturity_family, MaturityFamily, "$.maturity_family")
        if self.settlement_asset_relationship is AssetRelationship.THIRD:
            expected_payoff = PayoffFamily.QUANTO
        elif (
            self.contract_value_unit is ContractValueUnit.BASE
            and self.settlement_asset_relationship is AssetRelationship.QUOTE
        ):
            expected_payoff = PayoffFamily.LINEAR
        elif (
            self.contract_value_unit is ContractValueUnit.QUOTE
            and self.settlement_asset_relationship is AssetRelationship.BASE
        ):
            expected_payoff = PayoffFamily.INVERSE
        else:
            expected_payoff = PayoffFamily.OTHER
        expected_maturity = (
            MaturityFamily.OPEN_ENDED
            if self.instrument_kind is InstrumentKind.PERPETUAL_SWAP
            else MaturityFamily.FIXED_EXPIRY
        )
        if self.payoff_family is not expected_payoff:
            raise ValidationError(
                "inconsistent_classification",
                "$.payoff_family",
                "payoff family does not match the scenario relationships",
            )
        if self.maturity_family is not expected_maturity:
            raise ValidationError(
                "inconsistent_classification",
                "$.maturity_family",
                "maturity family does not match the scenario lifecycle",
            )


@dataclass(frozen=True)
class InstrumentAssessmentV1:
    """Structured outcome of resolving a partial descriptor into a profile."""

    schema_id: ClassVar[str] = INSTRUMENT_ASSESSMENT_SCHEMA_ID

    capability: InstrumentCapability
    state: DescriptorAssessmentState
    issues: Tuple[DescriptorIssueV1, ...]
    profile: Optional[InstrumentProfileV1] = None

    def __post_init__(self) -> None:
        _require_enum(self.capability, InstrumentCapability, "$.capability")
        _require_enum(self.state, DescriptorAssessmentState, "$.state")
        if type(self.issues) is not tuple:
            raise ValidationError("invalid_type", "$.issues", "expected a tuple")
        for index, issue in enumerate(self.issues):
            if not isinstance(issue, DescriptorIssueV1):
                raise ValidationError(
                    "invalid_type", f"$.issues[{index}]", "expected DescriptorIssueV1"
                )
        if self.state is DescriptorAssessmentState.COMPLETE:
            if self.issues:
                raise ValidationError(
                    "inconsistent_assessment",
                    "$",
                    "a complete assessment cannot carry issues",
                )
            if self.capability is InstrumentCapability.COMPLETE_PROFILE:
                if not isinstance(self.profile, InstrumentProfileV1):
                    raise ValidationError(
                        "inconsistent_assessment",
                        "$.profile",
                        "complete-profile assessment requires a resolved profile",
                    )
            elif self.profile is not None:
                raise ValidationError(
                    "inconsistent_assessment",
                    "$.profile",
                    "operation-specific assessment does not produce a full profile",
                )
        elif self.profile is not None or not self.issues:
            raise ValidationError(
                "inconsistent_assessment",
                "$",
                "an incomplete or invalid assessment requires issues and no profile",
            )


@dataclass(frozen=True)
class DataPointRule:
    """Invariant unit and temporal constraints for a canonical datapoint."""

    unit: MeasurementUnit
    temporal_modes: FrozenSet[TemporalMode]
    requires_denomination: bool = False


DATA_POINT_RULES: Mapping[DataPointKind, DataPointRule] = {
    DataPointKind.OPEN_INTEREST_CONTRACT_COUNT: DataPointRule(
        MeasurementUnit.CONTRACT_COUNT,
        frozenset({TemporalMode.CURRENT, TemporalMode.HISTORICAL}),
    ),
    DataPointKind.OPEN_INTEREST_BASE_QUANTITY: DataPointRule(
        MeasurementUnit.BASE_QUANTITY,
        frozenset({TemporalMode.CURRENT, TemporalMode.HISTORICAL}),
    ),
    DataPointKind.OPEN_INTEREST_NOTIONAL: DataPointRule(
        MeasurementUnit.NOTIONAL,
        frozenset({TemporalMode.CURRENT, TemporalMode.HISTORICAL}),
        requires_denomination=True,
    ),
    DataPointKind.FUNDING_INDICATIVE_RATE: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.CURRENT}),
    ),
    DataPointKind.FUNDING_NEXT_RATE: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.NEXT}),
    ),
    DataPointKind.FUNDING_SETTLED_RATE: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.SETTLED, TemporalMode.HISTORICAL}),
    ),
    DataPointKind.FUNDING_INTERVAL: DataPointRule(
        MeasurementUnit.DURATION_SECONDS,
        frozenset({TemporalMode.CURRENT, TemporalMode.HISTORICAL}),
    ),
    DataPointKind.FUNDING_PREMIUM_RATE: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.CURRENT, TemporalMode.HISTORICAL}),
    ),
    DataPointKind.FUNDING_INTEREST_RATE: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.CURRENT, TemporalMode.HISTORICAL}),
    ),
    DataPointKind.FUNDING_RATE_FLOOR: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.CURRENT}),
    ),
    DataPointKind.FUNDING_RATE_CAP: DataPointRule(
        MeasurementUnit.RATE_FRACTION,
        frozenset({TemporalMode.CURRENT}),
    ),
}


@dataclass(frozen=True)
class DataPointDefinitionV1:
    """Canonical meaning, unit, and time semantics of one datapoint."""

    schema_id: ClassVar[str] = DATAPOINT_SCHEMA_ID

    kind: DataPointKind
    temporal_mode: TemporalMode
    unit: MeasurementUnit
    denomination: Optional[NotionalDenomination] = None

    def __post_init__(self) -> None:
        _require_enum(self.kind, DataPointKind, "$.kind")
        _require_enum(self.temporal_mode, TemporalMode, "$.temporal_mode")
        _require_enum(self.unit, MeasurementUnit, "$.unit")
        if self.denomination is not None:
            _require_enum(self.denomination, NotionalDenomination, "$.denomination")

        rule = DATA_POINT_RULES[self.kind]
        if self.unit is not rule.unit:
            raise ValidationError(
                "inconsistent_unit",
                "$.unit",
                f"{self.kind.value} requires {rule.unit.value}",
            )
        if self.temporal_mode not in rule.temporal_modes:
            allowed = ", ".join(sorted(item.value for item in rule.temporal_modes))
            raise ValidationError(
                "inconsistent_temporal_mode",
                "$.temporal_mode",
                f"{self.kind.value} allows: {allowed}",
            )
        if rule.requires_denomination and self.denomination is None:
            raise ValidationError(
                "missing_denomination",
                "$.denomination",
                "a notional datapoint requires an economic denomination",
            )
        if not rule.requires_denomination and self.denomination is not None:
            raise ValidationError(
                "unexpected_denomination",
                "$.denomination",
                "denomination is only valid for a notional datapoint",
            )


def _require_nonnegative_decimal(value: object, path: str) -> None:
    if not isinstance(value, Decimal):
        raise ValidationError("invalid_type", path, "expected Decimal")
    if not value.is_finite() or value < 0:
        raise ValidationError("invalid_value", path, "expected a finite non-negative value")


@dataclass(frozen=True)
class OpenInterestValueV1:
    """An open-interest quantity with explicit measure and denomination."""

    schema_id: ClassVar[str] = OPEN_INTEREST_VALUE_SCHEMA_ID

    amount: Decimal
    measure: OpenInterestMeasure
    denomination: Optional[NotionalDenomination] = None

    def __post_init__(self) -> None:
        _require_nonnegative_decimal(self.amount, "$.amount")
        _require_enum(self.measure, OpenInterestMeasure, "$.measure")
        if self.denomination is not None:
            _require_enum(self.denomination, NotionalDenomination, "$.denomination")
        if self.measure is OpenInterestMeasure.NOTIONAL and self.denomination is None:
            raise ValidationError(
                "missing_denomination",
                "$.denomination",
                "a notional value requires an economic denomination",
            )
        if self.measure is not OpenInterestMeasure.NOTIONAL and self.denomination is not None:
            raise ValidationError(
                "unexpected_denomination",
                "$.denomination",
                "denomination is only valid for a notional value",
            )


@dataclass(frozen=True)
class DerivationStepV1:
    """One ordered step in a measurement lineage."""

    kind: DerivationKind
    method_id: Optional[str] = None

    def __post_init__(self) -> None:
        _require_enum(self.kind, DerivationKind, "$.steps[].kind")
        if self.kind is DerivationKind.NATIVE_REPORTED:
            if self.method_id is not None:
                raise ValidationError(
                    "unexpected_method_id",
                    "$.steps[].method_id",
                    "native reporting does not use a calculation method",
                )
            return
        if not isinstance(self.method_id, str) or not _METHOD_ID_PATTERN.fullmatch(self.method_id):
            raise ValidationError(
                "invalid_method_id",
                "$.steps[].method_id",
                "a calculation step requires a stable lowercase method identifier",
            )


@dataclass(frozen=True)
class MeasurementLineageV1:
    """Ordered derivation history for one canonical datapoint."""

    schema_id: ClassVar[str] = MEASUREMENT_LINEAGE_SCHEMA_ID

    output: DataPointDefinitionV1
    steps: Tuple[DerivationStepV1, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.output, DataPointDefinitionV1):
            raise ValidationError("invalid_type", "$.output", "expected DataPointDefinitionV1")
        if type(self.steps) is not tuple or not self.steps:
            raise ValidationError("invalid_value", "$.steps", "expected a non-empty tuple")
        for index, step in enumerate(self.steps):
            if not isinstance(step, DerivationStepV1):
                raise ValidationError(
                    "invalid_type", f"$.steps[{index}]", "expected DerivationStepV1"
                )
            if index > 0 and step.kind is DerivationKind.NATIVE_REPORTED:
                raise ValidationError(
                    "invalid_lineage_order",
                    f"$.steps[{index}].kind",
                    "native reporting may only be the first lineage step",
                )
        if self.steps[0].kind is DerivationKind.CANONICAL_CONVERSION:
            raise ValidationError(
                "invalid_lineage_order",
                "$.steps[0].kind",
                "a lineage must identify an acquisition or estimation step before conversion",
            )


def _require_utc_datetime(value: object, path: str) -> None:
    if not isinstance(value, datetime):
        raise ValidationError("invalid_type", path, "expected datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValidationError("invalid_value", path, "expected a UTC-aware datetime")


@dataclass(frozen=True)
class FundingIntervalV1:
    """Known interval evidence attached to a funding sample."""

    kind: FundingIntervalKind
    duration_seconds: Optional[int] = None
    window_start: Optional[datetime] = None

    def __post_init__(self) -> None:
        _require_enum(self.kind, FundingIntervalKind, "$.interval.kind")
        if self.duration_seconds is not None and (
            type(self.duration_seconds) is not int or self.duration_seconds <= 0
        ):
            raise ValidationError(
                "invalid_value",
                "$.interval.duration_seconds",
                "a supplied duration must be a positive integer",
            )
        if self.window_start is not None:
            _require_utc_datetime(self.window_start, "$.interval.window_start")

        if self.kind is FundingIntervalKind.EXPLICIT_DURATION:
            if self.duration_seconds is None or self.window_start is not None:
                raise ValidationError(
                    "inconsistent_interval",
                    "$.interval",
                    "explicit duration requires only duration_seconds",
                )
        elif self.kind is FundingIntervalKind.OBSERVED_WINDOW:
            if self.duration_seconds is None or self.window_start is None:
                raise ValidationError(
                    "inconsistent_interval",
                    "$.interval",
                    "an observed window requires a start timestamp and positive duration",
                )
        elif self.duration_seconds is not None or self.window_start is not None:
            raise ValidationError(
                "inconsistent_interval",
                "$.interval",
                "schedule and unspecified intervals do not carry invented bounds",
            )


@dataclass(frozen=True)
class FundingSampleV1:
    """A funding-rate sample with explicit timing and calculation lineage."""

    schema_id: ClassVar[str] = FUNDING_SAMPLE_SCHEMA_ID

    rate: Decimal
    kind: FundingRateKind
    observed_at: Optional[datetime]
    effective_at: Optional[datetime]
    interval: FundingIntervalV1
    lineage: MeasurementLineageV1

    def __post_init__(self) -> None:
        if not isinstance(self.rate, Decimal) or not self.rate.is_finite():
            raise ValidationError("invalid_value", "$.rate", "expected a finite Decimal")
        if self.rate.is_zero() and self.rate.is_signed():
            raise ValidationError("invalid_decimal", "$.rate", "signed zero is not canonical")
        _require_enum(self.kind, FundingRateKind, "$.kind")
        if self.observed_at is not None:
            _require_utc_datetime(self.observed_at, "$.observed_at")
        if self.effective_at is not None:
            _require_utc_datetime(self.effective_at, "$.effective_at")
        if not isinstance(self.interval, FundingIntervalV1):
            raise ValidationError("invalid_type", "$.interval", "expected FundingIntervalV1")
        if not isinstance(self.lineage, MeasurementLineageV1):
            raise ValidationError("invalid_type", "$.lineage", "expected MeasurementLineageV1")
        expected_kind = {
            FundingRateKind.INDICATIVE: DataPointKind.FUNDING_INDICATIVE_RATE,
            FundingRateKind.NEXT: DataPointKind.FUNDING_NEXT_RATE,
            FundingRateKind.SETTLED: DataPointKind.FUNDING_SETTLED_RATE,
        }[self.kind]
        if self.lineage.output.kind is not expected_kind:
            raise ValidationError(
                "inconsistent_lineage",
                "$.lineage.output.kind",
                "lineage output must match the funding sample kind",
            )
        if (
            self.kind in (FundingRateKind.NEXT, FundingRateKind.SETTLED)
            and self.effective_at is None
        ):
            raise ValidationError(
                "missing_effective_at",
                "$.effective_at",
                "next and settled samples require an effective timestamp",
            )


def data_point_rules() -> Dict[DataPointKind, DataPointRule]:
    """Return a copy of the canonical datapoint constraint registry."""

    return dict(DATA_POINT_RULES)
