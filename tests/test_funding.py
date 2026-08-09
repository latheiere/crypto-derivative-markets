from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from cdm import (
    DataPointDefinitionV1,
    DataPointKind,
    DerivationKind,
    DerivationStepV1,
    FundingIntervalKind,
    FundingIntervalV1,
    FundingRateKind,
    FundingSampleV1,
    MeasurementLineageV1,
    MeasurementUnit,
    TemporalMode,
    ValidationError,
)

UTC_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _lineage(kind: DataPointKind, temporal_mode: TemporalMode) -> MeasurementLineageV1:
    return MeasurementLineageV1(
        output=DataPointDefinitionV1(
            kind=kind,
            temporal_mode=temporal_mode,
            unit=MeasurementUnit.RATE_FRACTION,
        ),
        steps=(DerivationStepV1(kind=DerivationKind.NATIVE_REPORTED),),
    )


def test_unspecified_interval_does_not_invent_duration() -> None:
    sample = FundingSampleV1(
        rate=Decimal("0"),
        kind=FundingRateKind.INDICATIVE,
        observed_at=UTC_TIME,
        effective_at=None,
        interval=FundingIntervalV1(kind=FundingIntervalKind.UNSPECIFIED),
        lineage=_lineage(DataPointKind.FUNDING_INDICATIVE_RATE, TemporalMode.CURRENT),
    )
    assert sample.interval.duration_seconds is None


def test_missing_source_observation_time_remains_missing() -> None:
    sample = FundingSampleV1(
        rate=Decimal("0"),
        kind=FundingRateKind.INDICATIVE,
        observed_at=None,
        effective_at=None,
        interval=FundingIntervalV1(kind=FundingIntervalKind.UNSPECIFIED),
        lineage=_lineage(DataPointKind.FUNDING_INDICATIVE_RATE, TemporalMode.CURRENT),
    )
    assert sample.observed_at is None


def test_settled_sample_requires_effective_time() -> None:
    with pytest.raises(ValidationError) as error:
        FundingSampleV1(
            rate=Decimal("0"),
            kind=FundingRateKind.SETTLED,
            observed_at=UTC_TIME,
            effective_at=None,
            interval=FundingIntervalV1(kind=FundingIntervalKind.PROTOCOL_SCHEDULE),
            lineage=_lineage(DataPointKind.FUNDING_SETTLED_RATE, TemporalMode.SETTLED),
        )
    assert error.value.code == "missing_effective_at"


def test_sample_lineage_must_match_sample_kind() -> None:
    with pytest.raises(ValidationError) as error:
        FundingSampleV1(
            rate=Decimal("0"),
            kind=FundingRateKind.NEXT,
            observed_at=UTC_TIME,
            effective_at=UTC_TIME,
            interval=FundingIntervalV1(kind=FundingIntervalKind.PROTOCOL_SCHEDULE),
            lineage=_lineage(DataPointKind.FUNDING_INDICATIVE_RATE, TemporalMode.CURRENT),
        )
    assert error.value.code == "inconsistent_lineage"


def test_observed_window_requires_start_and_positive_duration() -> None:
    with pytest.raises(ValidationError) as error:
        FundingIntervalV1(
            kind=FundingIntervalKind.OBSERVED_WINDOW,
            window_start=UTC_TIME,
        )
    assert error.value.code == "inconsistent_interval"
