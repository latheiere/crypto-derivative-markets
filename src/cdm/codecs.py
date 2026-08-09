"""Strict JSON-compatible codecs for versioned CDM values."""

from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Optional, Set, Type, TypeVar, Union, cast

from .errors import DecodeError, UnknownSchemaError, ValidationError
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
    NATIVE_IDENTITY_NAMESPACE_PATTERN,
    NATIVE_IDENTITY_SELECTOR_SCHEMA_ID,
    OPEN_INTEREST_VALUE_SCHEMA_ID,
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    ContractValueV1,
    DataPointDefinitionV1,
    DataPointKind,
    DerivationKind,
    DerivationStepV1,
    DescriptorAssessmentState,
    DescriptorIssueCode,
    DescriptorIssueV1,
    FundingDescriptorV1,
    FundingIntervalKind,
    FundingIntervalV1,
    FundingMechanism,
    FundingRateKind,
    FundingSampleV1,
    FundingTermsV1,
    InstrumentAssessmentV1,
    InstrumentCapability,
    InstrumentClassificationV1,
    InstrumentDescriptorV1,
    InstrumentKind,
    InstrumentProfileV1,
    InstrumentReferenceV1,
    InstrumentScenarioV1,
    MarginAssetRelationship,
    MaturityFamily,
    MeasurementLineageV1,
    MeasurementUnit,
    NativeIdentityNamespace,
    NativeIdentityRole,
    NativeIdentitySelectorV1,
    NativeIdentityV1,
    NotionalDenomination,
    OpenInterestMeasure,
    OpenInterestValueV1,
    PayoffFamily,
    SettlementDescriptorV1,
    SettlementMethod,
    SettlementTermsV1,
    TemporalMode,
)

CDMValue = Union[
    InstrumentDescriptorV1,
    InstrumentProfileV1,
    InstrumentClassificationV1,
    InstrumentAssessmentV1,
    InstrumentScenarioV1,
    InstrumentReferenceV1,
    NativeIdentitySelectorV1,
    DataPointDefinitionV1,
    MeasurementLineageV1,
    OpenInterestValueV1,
    FundingSampleV1,
]

E = TypeVar("E", bound=Enum)
_DECIMAL_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?$")
_NATIVE_IDENTITY_NAMESPACE_PATTERN = re.compile(NATIVE_IDENTITY_NAMESPACE_PATTERN)


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ValidationError("invalid_value", "$", "cannot serialize a non-finite Decimal")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):
        return "0"
    return text


def _timestamp_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _object(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise DecodeError("invalid_type", path, "expected an object with string keys")
    return cast(Mapping[str, object], value)


def _fields(
    value: Mapping[str, object],
    *,
    required: Set[str],
    optional: Set[str],
    path: str,
) -> None:
    missing = sorted(required.difference(value))
    if missing:
        raise DecodeError("missing_field", f"{path}.{missing[0]}", "required field is missing")
    unknown = sorted(set(value).difference(required | optional))
    if unknown:
        raise DecodeError("unknown_field", f"{path}.{unknown[0]}", "field is not defined")


def _enum(enum_type: Type[E], value: object, path: str) -> E:
    if not isinstance(value, str):
        raise DecodeError("invalid_type", path, "expected a string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise DecodeError("invalid_enum", path, f"unsupported value {value!r}") from error


def _native_identity_namespace(value: object, path: str) -> NativeIdentityNamespace:
    if not isinstance(value, str):
        raise DecodeError("invalid_type", path, "expected a string")
    if not _NATIVE_IDENTITY_NAMESPACE_PATTERN.fullmatch(value):
        raise DecodeError(
            "invalid_value",
            path,
            "expected a supported protocol identity namespace",
        )
    return NativeIdentityNamespace(value)


def _decimal(value: object, path: str) -> Decimal:
    if not isinstance(value, str) or not _DECIMAL_PATTERN.fullmatch(value):
        raise DecodeError("invalid_decimal", path, "expected a canonical decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:  # pragma: no cover - guarded by the pattern
        raise DecodeError("invalid_decimal", path, "expected a decimal string") from error
    if _decimal_text(parsed) != value:
        raise DecodeError("invalid_decimal", path, "expected canonical decimal formatting")
    return parsed


def _positive_integer(value: object, path: str) -> int:
    if type(value) is not int or value <= 0:
        raise DecodeError("invalid_value", path, "expected a positive integer")
    return value


def _timestamp(value: object, path: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DecodeError("invalid_timestamp", path, "expected an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise DecodeError(
            "invalid_timestamp", path, "expected an RFC 3339 UTC timestamp"
        ) from error
    if _timestamp_text(parsed) != value:
        raise DecodeError("invalid_timestamp", path, "expected canonical UTC formatting")
    return parsed


def _profile_data(value: InstrumentProfileV1) -> Dict[str, object]:
    data: Dict[str, object] = {
        "instrument_kind": value.instrument_kind.value,
        "contract_value": {
            "amount": _decimal_text(value.contract_value.amount),
            "unit": value.contract_value.unit.value,
        },
        "settlement": {
            "method": value.settlement.method.value,
            "asset_relationship": value.settlement.asset_relationship.value,
        },
        "margin_asset_relationship": value.margin_asset_relationship.value,
        "funding": {"mechanism": value.funding.mechanism.value},
    }
    data["schema_id"] = value.schema_id
    if value.funding.interval_seconds is not None:
        cast(Dict[str, object], data["funding"])["interval_seconds"] = (
            value.funding.interval_seconds
        )
    return data


def _decode_profile(value: object, path: str) -> InstrumentProfileV1:
    data = _object(value, path)
    required = {
        "instrument_kind",
        "contract_value",
        "settlement",
        "margin_asset_relationship",
        "funding",
    }
    required.add("schema_id")
    _fields(data, required=required, optional=set(), path=path)
    if data["schema_id"] != INSTRUMENT_PROFILE_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")

    contract = _object(data["contract_value"], f"{path}.contract_value")
    _fields(
        contract,
        required={"amount", "unit"},
        optional=set(),
        path=f"{path}.contract_value",
    )
    settlement = _object(data["settlement"], f"{path}.settlement")
    _fields(
        settlement,
        required={"method", "asset_relationship"},
        optional=set(),
        path=f"{path}.settlement",
    )
    funding = _object(data["funding"], f"{path}.funding")
    _fields(
        funding,
        required={"mechanism"},
        optional={"interval_seconds"},
        path=f"{path}.funding",
    )
    try:
        return InstrumentProfileV1(
            instrument_kind=_enum(
                InstrumentKind, data["instrument_kind"], f"{path}.instrument_kind"
            ),
            contract_value=ContractValueV1(
                amount=_decimal(contract["amount"], f"{path}.contract_value.amount"),
                unit=_enum(
                    ContractValueUnit,
                    contract["unit"],
                    f"{path}.contract_value.unit",
                ),
            ),
            settlement=SettlementTermsV1(
                method=_enum(
                    SettlementMethod,
                    settlement["method"],
                    f"{path}.settlement.method",
                ),
                asset_relationship=_enum(
                    AssetRelationship,
                    settlement["asset_relationship"],
                    f"{path}.settlement.asset_relationship",
                ),
            ),
            margin_asset_relationship=_enum(
                MarginAssetRelationship,
                data["margin_asset_relationship"],
                f"{path}.margin_asset_relationship",
            ),
            funding=FundingTermsV1(
                mechanism=_enum(
                    FundingMechanism,
                    funding["mechanism"],
                    f"{path}.funding.mechanism",
                ),
                interval_seconds=(
                    _positive_integer(
                        funding["interval_seconds"], f"{path}.funding.interval_seconds"
                    )
                    if "interval_seconds" in funding
                    else None
                ),
            ),
        )
    except ValidationError as error:
        if isinstance(error, DecodeError):
            raise
        raise DecodeError(error.code, error.path, error.message) from error


def _descriptor_data(value: InstrumentDescriptorV1) -> Dict[str, object]:
    data: Dict[str, object] = {"schema_id": value.schema_id}
    if value.instrument_kind is not None:
        data["instrument_kind"] = value.instrument_kind.value
    if value.contract_value is not None:
        contract: Dict[str, object] = {}
        if value.contract_value.amount is not None:
            contract["amount"] = _decimal_text(value.contract_value.amount)
        if value.contract_value.unit is not None:
            contract["unit"] = value.contract_value.unit.value
        data["contract_value"] = contract
    if value.settlement is not None:
        settlement: Dict[str, object] = {}
        if value.settlement.method is not None:
            settlement["method"] = value.settlement.method.value
        if value.settlement.asset_relationship is not None:
            settlement["asset_relationship"] = value.settlement.asset_relationship.value
        data["settlement"] = settlement
    if value.margin_asset_relationship is not None:
        data["margin_asset_relationship"] = value.margin_asset_relationship.value
    if value.funding is not None:
        funding: Dict[str, object] = {}
        if value.funding.mechanism is not None:
            funding["mechanism"] = value.funding.mechanism.value
        if value.funding.interval_seconds is not None:
            funding["interval_seconds"] = value.funding.interval_seconds
        data["funding"] = funding
    return data


def _decode_descriptor(value: object, path: str) -> InstrumentDescriptorV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id"},
        optional={
            "instrument_kind",
            "contract_value",
            "settlement",
            "margin_asset_relationship",
            "funding",
        },
        path=path,
    )
    if data["schema_id"] != INSTRUMENT_DESCRIPTOR_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")

    contract: Optional[Mapping[str, object]] = None
    if "contract_value" in data:
        contract = _object(data["contract_value"], f"{path}.contract_value")
        _fields(
            contract,
            required=set(),
            optional={"amount", "unit"},
            path=f"{path}.contract_value",
        )
    settlement: Optional[Mapping[str, object]] = None
    if "settlement" in data:
        settlement = _object(data["settlement"], f"{path}.settlement")
        _fields(
            settlement,
            required=set(),
            optional={"method", "asset_relationship"},
            path=f"{path}.settlement",
        )
    funding: Optional[Mapping[str, object]] = None
    if "funding" in data:
        funding = _object(data["funding"], f"{path}.funding")
        _fields(
            funding,
            required=set(),
            optional={"mechanism", "interval_seconds"},
            path=f"{path}.funding",
        )
    return InstrumentDescriptorV1(
        instrument_kind=(
            _enum(InstrumentKind, data["instrument_kind"], f"{path}.instrument_kind")
            if "instrument_kind" in data
            else None
        ),
        contract_value=(
            ContractValueDescriptorV1(
                amount=(
                    _decimal(contract["amount"], f"{path}.contract_value.amount")
                    if contract is not None and "amount" in contract
                    else None
                ),
                unit=(
                    _enum(
                        ContractValueUnit,
                        contract["unit"],
                        f"{path}.contract_value.unit",
                    )
                    if contract is not None and "unit" in contract
                    else None
                ),
            )
            if contract is not None
            else None
        ),
        settlement=(
            SettlementDescriptorV1(
                method=(
                    _enum(
                        SettlementMethod,
                        settlement["method"],
                        f"{path}.settlement.method",
                    )
                    if settlement is not None and "method" in settlement
                    else None
                ),
                asset_relationship=(
                    _enum(
                        AssetRelationship,
                        settlement["asset_relationship"],
                        f"{path}.settlement.asset_relationship",
                    )
                    if settlement is not None and "asset_relationship" in settlement
                    else None
                ),
            )
            if settlement is not None
            else None
        ),
        margin_asset_relationship=(
            _enum(
                MarginAssetRelationship,
                data["margin_asset_relationship"],
                f"{path}.margin_asset_relationship",
            )
            if "margin_asset_relationship" in data
            else None
        ),
        funding=(
            FundingDescriptorV1(
                mechanism=(
                    _enum(
                        FundingMechanism,
                        funding["mechanism"],
                        f"{path}.funding.mechanism",
                    )
                    if funding is not None and "mechanism" in funding
                    else None
                ),
                interval_seconds=(
                    _positive_integer(
                        funding["interval_seconds"], f"{path}.funding.interval_seconds"
                    )
                    if funding is not None and "interval_seconds" in funding
                    else None
                ),
            )
            if funding is not None
            else None
        ),
    )


def _native_identity_data(value: NativeIdentityV1) -> Dict[str, object]:
    return {
        "role": value.role.value,
        "namespace": str(value.namespace),
        "value": value.value,
    }


def _decode_native_identity(value: object, path: str) -> NativeIdentityV1:
    data = _object(value, path)
    _fields(
        data,
        required={"role", "namespace", "value"},
        optional=set(),
        path=path,
    )
    native_value = data["value"]
    if not isinstance(native_value, str):
        raise DecodeError("invalid_type", f"{path}.value", "expected a string")
    if not native_value:
        raise DecodeError("invalid_value", f"{path}.value", "expected a non-empty value")
    return NativeIdentityV1(
        role=_enum(NativeIdentityRole, data["role"], f"{path}.role"),
        namespace=_native_identity_namespace(data["namespace"], f"{path}.namespace"),
        value=native_value,
    )


def _reference_data(value: InstrumentReferenceV1) -> Dict[str, object]:
    data: Dict[str, object] = {
        "schema_id": value.schema_id,
        "descriptor": _descriptor_data(value.descriptor),
    }
    if value.native_identities:
        data["native_identities"] = [
            _native_identity_data(identity) for identity in value.native_identities
        ]
    return data


def _decode_reference(value: object, path: str) -> InstrumentReferenceV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id", "descriptor"},
        optional={"native_identities"},
        path=path,
    )
    if data["schema_id"] != INSTRUMENT_REFERENCE_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    identities = data.get("native_identities")
    if identities is not None:
        if not isinstance(identities, list):
            raise DecodeError(
                "invalid_type",
                f"{path}.native_identities",
                "expected an array",
            )
        if not identities:
            raise DecodeError(
                "invalid_value",
                f"{path}.native_identities",
                "an explicit identity array must not be empty",
            )
    return InstrumentReferenceV1(
        descriptor=_decode_descriptor(data["descriptor"], f"{path}.descriptor"),
        native_identities=tuple(
            _decode_native_identity(identity, f"{path}.native_identities[{index}]")
            for index, identity in enumerate(identities or [])
        ),
    )


def _selector_data(value: NativeIdentitySelectorV1) -> Dict[str, object]:
    return {
        "schema_id": value.schema_id,
        "role": value.role.value,
        "namespace": str(value.namespace),
    }


def _decode_selector(value: object, path: str) -> NativeIdentitySelectorV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id", "role", "namespace"},
        optional=set(),
        path=path,
    )
    if data["schema_id"] != NATIVE_IDENTITY_SELECTOR_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    return NativeIdentitySelectorV1(
        role=_enum(NativeIdentityRole, data["role"], f"{path}.role"),
        namespace=_native_identity_namespace(data["namespace"], f"{path}.namespace"),
    )


def _datapoint_data(value: DataPointDefinitionV1) -> Dict[str, object]:
    data: Dict[str, object] = {
        "kind": value.kind.value,
        "temporal_mode": value.temporal_mode.value,
        "unit": value.unit.value,
    }
    data["schema_id"] = value.schema_id
    if value.denomination is not None:
        data["denomination"] = value.denomination.value
    return data


def _decode_datapoint(value: object, path: str) -> DataPointDefinitionV1:
    data = _object(value, path)
    required = {"kind", "temporal_mode", "unit"}
    required.add("schema_id")
    _fields(data, required=required, optional={"denomination"}, path=path)
    if data["schema_id"] != DATAPOINT_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    return DataPointDefinitionV1(
        kind=_enum(DataPointKind, data["kind"], f"{path}.kind"),
        temporal_mode=_enum(TemporalMode, data["temporal_mode"], f"{path}.temporal_mode"),
        unit=_enum(MeasurementUnit, data["unit"], f"{path}.unit"),
        denomination=(
            _enum(NotionalDenomination, data["denomination"], f"{path}.denomination")
            if "denomination" in data
            else None
        ),
    )


def _lineage_data(value: MeasurementLineageV1) -> Dict[str, object]:
    data: Dict[str, object] = {
        "output": _datapoint_data(value.output),
        "steps": [
            {
                "kind": step.kind.value,
                **({"method_id": step.method_id} if step.method_id is not None else {}),
            }
            for step in value.steps
        ],
    }
    data["schema_id"] = value.schema_id
    return data


def _decode_lineage(value: object, path: str) -> MeasurementLineageV1:
    data = _object(value, path)
    required = {"output", "steps"}
    required.add("schema_id")
    _fields(data, required=required, optional=set(), path=path)
    if data["schema_id"] != MEASUREMENT_LINEAGE_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    steps_value = data["steps"]
    if not isinstance(steps_value, list) or not steps_value:
        raise DecodeError("invalid_value", f"{path}.steps", "expected a non-empty array")
    steps = []
    for index, raw_step in enumerate(steps_value):
        step_path = f"{path}.steps[{index}]"
        step = _object(raw_step, step_path)
        _fields(step, required={"kind"}, optional={"method_id"}, path=step_path)
        method_id = step.get("method_id")
        if method_id is not None and not isinstance(method_id, str):
            raise DecodeError("invalid_type", f"{step_path}.method_id", "expected a string")
        steps.append(
            DerivationStepV1(
                kind=_enum(DerivationKind, step["kind"], f"{step_path}.kind"),
                method_id=method_id,
            )
        )
    return MeasurementLineageV1(
        output=_decode_datapoint(data["output"], f"{path}.output"),
        steps=tuple(steps),
    )


def _assessment_data(value: InstrumentAssessmentV1) -> Dict[str, object]:
    data: Dict[str, object] = {
        "schema_id": value.schema_id,
        "capability": value.capability.value,
        "state": value.state.value,
        "issues": [
            {"code": issue.code.value, "path": issue.path, "message": issue.message}
            for issue in value.issues
        ],
    }
    if value.profile is not None:
        data["profile"] = _profile_data(value.profile)
    return data


def _decode_assessment(value: object, path: str) -> InstrumentAssessmentV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id", "capability", "state", "issues"},
        optional={"profile"},
        path=path,
    )
    if data["schema_id"] != INSTRUMENT_ASSESSMENT_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    raw_issues = data["issues"]
    if not isinstance(raw_issues, list):
        raise DecodeError("invalid_type", f"{path}.issues", "expected an array")
    issues = []
    for index, raw_issue in enumerate(raw_issues):
        issue_path = f"{path}.issues[{index}]"
        issue = _object(raw_issue, issue_path)
        _fields(
            issue,
            required={"code", "path", "message"},
            optional=set(),
            path=issue_path,
        )
        if not isinstance(issue["path"], str) or not isinstance(issue["message"], str):
            raise DecodeError("invalid_type", issue_path, "issue path and message must be strings")
        issues.append(
            DescriptorIssueV1(
                code=_enum(DescriptorIssueCode, issue["code"], f"{issue_path}.code"),
                path=issue["path"],
                message=issue["message"],
            )
        )
    return InstrumentAssessmentV1(
        capability=_enum(InstrumentCapability, data["capability"], f"{path}.capability"),
        state=_enum(DescriptorAssessmentState, data["state"], f"{path}.state"),
        issues=tuple(issues),
        profile=(
            _decode_profile(data["profile"], f"{path}.profile") if "profile" in data else None
        ),
    )


def _classification_data(value: InstrumentClassificationV1) -> Dict[str, object]:
    return {
        "schema_id": value.schema_id,
        "payoff_family": value.payoff_family.value,
        "maturity_family": value.maturity_family.value,
    }


def _decode_classification(value: object, path: str) -> InstrumentClassificationV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id", "payoff_family", "maturity_family"},
        optional=set(),
        path=path,
    )
    if data["schema_id"] != INSTRUMENT_CLASSIFICATION_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    return InstrumentClassificationV1(
        payoff_family=_enum(PayoffFamily, data["payoff_family"], f"{path}.payoff_family"),
        maturity_family=_enum(MaturityFamily, data["maturity_family"], f"{path}.maturity_family"),
    )


def _scenario_data(value: InstrumentScenarioV1) -> Dict[str, object]:
    return {
        "schema_id": value.schema_id,
        "descriptor_schema_id": value.descriptor_schema_id,
        "classification_schema_id": value.classification_schema_id,
        "instrument_kind": value.instrument_kind.value,
        "contract_value_unit": value.contract_value_unit.value,
        "settlement_asset_relationship": value.settlement_asset_relationship.value,
        "payoff_family": value.payoff_family.value,
        "maturity_family": value.maturity_family.value,
    }


def _decode_scenario(value: object, path: str) -> InstrumentScenarioV1:
    data = _object(value, path)
    _fields(
        data,
        required={
            "schema_id",
            "descriptor_schema_id",
            "classification_schema_id",
            "instrument_kind",
            "contract_value_unit",
            "settlement_asset_relationship",
            "payoff_family",
            "maturity_family",
        },
        optional=set(),
        path=path,
    )
    if data["schema_id"] != INSTRUMENT_SCENARIO_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    if data["descriptor_schema_id"] != INSTRUMENT_DESCRIPTOR_SCHEMA_ID:
        raise UnknownSchemaError(
            data["descriptor_schema_id"],
            f"{path}.descriptor_schema_id",
        )
    if data["classification_schema_id"] != INSTRUMENT_CLASSIFICATION_SCHEMA_ID:
        raise UnknownSchemaError(
            data["classification_schema_id"],
            f"{path}.classification_schema_id",
        )
    return InstrumentScenarioV1(
        instrument_kind=_enum(
            InstrumentKind,
            data["instrument_kind"],
            f"{path}.instrument_kind",
        ),
        contract_value_unit=_enum(
            ContractValueUnit,
            data["contract_value_unit"],
            f"{path}.contract_value_unit",
        ),
        settlement_asset_relationship=_enum(
            AssetRelationship,
            data["settlement_asset_relationship"],
            f"{path}.settlement_asset_relationship",
        ),
        payoff_family=_enum(PayoffFamily, data["payoff_family"], f"{path}.payoff_family"),
        maturity_family=_enum(
            MaturityFamily,
            data["maturity_family"],
            f"{path}.maturity_family",
        ),
    )


def _open_interest_data(value: OpenInterestValueV1) -> Dict[str, object]:
    data: Dict[str, object] = {
        "schema_id": value.schema_id,
        "amount": _decimal_text(value.amount),
        "measure": value.measure.value,
    }
    if value.denomination is not None:
        data["denomination"] = value.denomination.value
    return data


def _decode_open_interest(value: object, path: str) -> OpenInterestValueV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id", "amount", "measure"},
        optional={"denomination"},
        path=path,
    )
    if data["schema_id"] != OPEN_INTEREST_VALUE_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    return OpenInterestValueV1(
        amount=_decimal(data["amount"], f"{path}.amount"),
        measure=_enum(OpenInterestMeasure, data["measure"], f"{path}.measure"),
        denomination=(
            _enum(NotionalDenomination, data["denomination"], f"{path}.denomination")
            if "denomination" in data
            else None
        ),
    )


def _funding_sample_data(value: FundingSampleV1) -> Dict[str, object]:
    interval: Dict[str, object] = {"kind": value.interval.kind.value}
    if value.interval.duration_seconds is not None:
        interval["duration_seconds"] = value.interval.duration_seconds
    if value.interval.window_start is not None:
        interval["window_start"] = _timestamp_text(value.interval.window_start)
    data: Dict[str, object] = {
        "schema_id": value.schema_id,
        "rate": _decimal_text(value.rate),
        "kind": value.kind.value,
        "interval": interval,
        "lineage": _lineage_data(value.lineage),
    }
    if value.observed_at is not None:
        data["observed_at"] = _timestamp_text(value.observed_at)
    if value.effective_at is not None:
        data["effective_at"] = _timestamp_text(value.effective_at)
    return data


def _decode_funding_sample(value: object, path: str) -> FundingSampleV1:
    data = _object(value, path)
    _fields(
        data,
        required={"schema_id", "rate", "kind", "interval", "lineage"},
        optional={"observed_at", "effective_at"},
        path=path,
    )
    if data["schema_id"] != FUNDING_SAMPLE_SCHEMA_ID:
        raise UnknownSchemaError(data["schema_id"], f"{path}.schema_id")
    interval = _object(data["interval"], f"{path}.interval")
    _fields(
        interval,
        required={"kind"},
        optional={"duration_seconds", "window_start"},
        path=f"{path}.interval",
    )
    return FundingSampleV1(
        rate=_decimal(data["rate"], f"{path}.rate"),
        kind=_enum(FundingRateKind, data["kind"], f"{path}.kind"),
        observed_at=(
            _timestamp(data["observed_at"], f"{path}.observed_at")
            if "observed_at" in data
            else None
        ),
        effective_at=(
            _timestamp(data["effective_at"], f"{path}.effective_at")
            if "effective_at" in data
            else None
        ),
        interval=FundingIntervalV1(
            kind=_enum(FundingIntervalKind, interval["kind"], f"{path}.interval.kind"),
            duration_seconds=(
                _positive_integer(interval["duration_seconds"], f"{path}.interval.duration_seconds")
                if "duration_seconds" in interval
                else None
            ),
            window_start=(
                _timestamp(interval["window_start"], f"{path}.interval.window_start")
                if "window_start" in interval
                else None
            ),
        ),
        lineage=_decode_lineage(data["lineage"], f"{path}.lineage"),
    )


def to_data(value: CDMValue) -> Dict[str, object]:
    """Encode a typed value into a JSON-compatible object."""

    if isinstance(value, InstrumentDescriptorV1):
        return _descriptor_data(value)
    if isinstance(value, InstrumentReferenceV1):
        return _reference_data(value)
    if isinstance(value, NativeIdentitySelectorV1):
        return _selector_data(value)
    if isinstance(value, InstrumentProfileV1):
        return _profile_data(value)
    if isinstance(value, InstrumentClassificationV1):
        return _classification_data(value)
    if isinstance(value, InstrumentScenarioV1):
        return _scenario_data(value)
    if isinstance(value, InstrumentAssessmentV1):
        return _assessment_data(value)
    if isinstance(value, DataPointDefinitionV1):
        return _datapoint_data(value)
    if isinstance(value, MeasurementLineageV1):
        return _lineage_data(value)
    if isinstance(value, OpenInterestValueV1):
        return _open_interest_data(value)
    if isinstance(value, FundingSampleV1):
        return _funding_sample_data(value)
    raise ValidationError("unsupported_type", "$", f"cannot encode {type(value).__name__}")


def from_data(value: object) -> CDMValue:
    """Decode a JSON-compatible object selected by its schema identifier."""

    data = _object(value, "$")
    if "schema_id" not in data:
        raise DecodeError("missing_field", "$.schema_id", "required field is missing")
    schema_id = data["schema_id"]
    if not isinstance(schema_id, str):
        raise DecodeError("invalid_type", "$.schema_id", "expected a string")
    decoders: Mapping[str, Callable[[object, str], CDMValue]] = {
        INSTRUMENT_DESCRIPTOR_SCHEMA_ID: _decode_descriptor,
        INSTRUMENT_REFERENCE_SCHEMA_ID: _decode_reference,
        NATIVE_IDENTITY_SELECTOR_SCHEMA_ID: _decode_selector,
        INSTRUMENT_PROFILE_SCHEMA_ID: _decode_profile,
        INSTRUMENT_CLASSIFICATION_SCHEMA_ID: _decode_classification,
        INSTRUMENT_SCENARIO_SCHEMA_ID: _decode_scenario,
        INSTRUMENT_ASSESSMENT_SCHEMA_ID: _decode_assessment,
        DATAPOINT_SCHEMA_ID: _decode_datapoint,
        MEASUREMENT_LINEAGE_SCHEMA_ID: _decode_lineage,
        OPEN_INTEREST_VALUE_SCHEMA_ID: _decode_open_interest,
        FUNDING_SAMPLE_SCHEMA_ID: _decode_funding_sample,
    }
    decoder = decoders.get(schema_id)
    if decoder is None:
        raise UnknownSchemaError(schema_id)
    try:
        return decoder(data, "$")
    except DecodeError:
        raise
    except ValidationError as error:
        raise DecodeError(error.code, error.path, error.message) from error


def to_json(value: CDMValue) -> str:
    """Encode a typed value as deterministic compact JSON."""

    return json.dumps(to_data(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def from_json(value: Union[str, bytes, bytearray]) -> CDMValue:
    """Decode JSON into a typed CDM value."""

    try:
        data: Any = json.loads(value)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DecodeError("invalid_json", "$", "input is not valid JSON") from error
    return from_data(data)
