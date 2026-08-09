from __future__ import annotations

import pytest

from cdm import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    InstrumentDescriptorV1,
    InstrumentKind,
    InstrumentScenarioV1,
    MaturityFamily,
    PayoffFamily,
    SettlementDescriptorV1,
    ValidationError,
    instrument_scenario,
    to_data,
)


def test_scenario_is_amount_independent_and_versioned() -> None:
    scenario = instrument_scenario(
        InstrumentDescriptorV1(
            instrument_kind=InstrumentKind.PERPETUAL_SWAP,
            contract_value=ContractValueDescriptorV1(unit=ContractValueUnit.BASE),
            settlement=SettlementDescriptorV1(asset_relationship=AssetRelationship.QUOTE),
        )
    )
    assert to_data(scenario) == {
        "schema_id": "urn:cdm:schema:instrument-scenario:1",
        "descriptor_schema_id": "urn:cdm:schema:instrument-descriptor:1",
        "classification_schema_id": "urn:cdm:schema:instrument-classification:1",
        "instrument_kind": "perpetual_swap",
        "contract_value_unit": "base",
        "settlement_asset_relationship": "quote",
        "payoff_family": "linear",
        "maturity_family": "open_ended",
    }


def test_scenario_rejects_inconsistent_derived_fields() -> None:
    with pytest.raises(ValidationError) as error:
        InstrumentScenarioV1(
            instrument_kind=InstrumentKind.FUTURE,
            contract_value_unit=ContractValueUnit.QUOTE,
            settlement_asset_relationship=AssetRelationship.BASE,
            payoff_family=PayoffFamily.LINEAR,
            maturity_family=MaturityFamily.FIXED_EXPIRY,
        )
    assert error.value.code == "inconsistent_classification"
