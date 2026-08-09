from __future__ import annotations

from decimal import Decimal, localcontext

from cdm import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    ConversionFormula,
    ConversionIssueCode,
    ConversionStatus,
    ExactRatioV1,
    InstrumentDescriptorV1,
    NotionalDenomination,
    OpenInterestMeasure,
    OpenInterestValueV1,
    SettlementDescriptorV1,
    convert_open_interest,
)


def _descriptor(
    unit: ContractValueUnit,
    settlement: AssetRelationship,
    amount: Decimal = Decimal("2"),
) -> InstrumentDescriptorV1:
    return InstrumentDescriptorV1(
        contract_value=ContractValueDescriptorV1(amount=amount, unit=unit),
        settlement=SettlementDescriptorV1(asset_relationship=settlement),
    )


def test_linear_contract_count_to_base_is_exact_without_mark() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(amount=Decimal("3"), measure=OpenInterestMeasure.CONTRACT_COUNT),
        OpenInterestMeasure.BASE_QUANTITY,
        _descriptor(ContractValueUnit.BASE, AssetRelationship.QUOTE),
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output == OpenInterestValueV1(
        amount=Decimal("6"),
        measure=OpenInterestMeasure.BASE_QUANTITY,
    )
    assert result.formula_ids == (ConversionFormula.CONTRACTS_TO_BASE_LINEAR.value,)


def test_linear_contract_count_to_quote_requires_mark() -> None:
    source = OpenInterestValueV1(
        amount=Decimal("3"),
        measure=OpenInterestMeasure.CONTRACT_COUNT,
    )
    instrument = _descriptor(ContractValueUnit.BASE, AssetRelationship.QUOTE)
    missing = convert_open_interest(
        source,
        OpenInterestMeasure.NOTIONAL,
        instrument,
        target_denomination=NotionalDenomination.QUOTE,
    )
    assert missing.status is ConversionStatus.MISSING_INPUT
    assert [issue.code for issue in missing.issues] == [ConversionIssueCode.MISSING_MARK_PRICE]

    exact = convert_open_interest(
        source,
        OpenInterestMeasure.NOTIONAL,
        instrument,
        target_denomination=NotionalDenomination.QUOTE,
        mark_price=Decimal("5"),
    )
    assert exact.status is ConversionStatus.EXACT
    assert exact.output is not None
    assert exact.output.amount == Decimal("30")
    assert exact.formula_ids == (
        ConversionFormula.CONTRACTS_TO_BASE_LINEAR.value,
        ConversionFormula.BASE_TO_QUOTE_AT_MARK.value,
    )


def test_inverse_contract_count_to_quote_does_not_require_mark() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(amount=Decimal("3"), measure=OpenInterestMeasure.CONTRACT_COUNT),
        OpenInterestMeasure.NOTIONAL,
        _descriptor(ContractValueUnit.QUOTE, AssetRelationship.BASE),
        target_denomination=NotionalDenomination.QUOTE,
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output is not None
    assert result.output.amount == Decimal("6")
    assert result.formula_ids == (ConversionFormula.CONTRACTS_TO_QUOTE_INVERSE.value,)


def test_direct_reporting_conversion_does_not_require_mark() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(
            amount=Decimal("10"),
            measure=OpenInterestMeasure.NOTIONAL,
            denomination=NotionalDenomination.QUOTE,
        ),
        OpenInterestMeasure.NOTIONAL,
        InstrumentDescriptorV1(),
        target_denomination=NotionalDenomination.REPORTING,
        mark_price=Decimal("-1"),
        reporting_per_quote=Decimal("1.5"),
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output is not None
    assert result.output.amount == Decimal("15")
    assert result.formula_ids == (ConversionFormula.QUOTE_TO_REPORTING.value,)


def test_unmodeled_payoff_is_not_forced_into_a_contract_formula() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(amount=Decimal("3"), measure=OpenInterestMeasure.CONTRACT_COUNT),
        OpenInterestMeasure.BASE_QUANTITY,
        _descriptor(ContractValueUnit.QUOTE, AssetRelationship.THIRD),
        mark_price=Decimal("5"),
    )
    assert result.status is ConversionStatus.UNMODELED
    assert [issue.code for issue in result.issues] == [ConversionIssueCode.UNMODELED_PAYOFF]


def test_identity_conversion_works_for_unmodeled_payoff() -> None:
    source = OpenInterestValueV1(
        amount=Decimal("3"),
        measure=OpenInterestMeasure.CONTRACT_COUNT,
    )
    result = convert_open_interest(
        source,
        OpenInterestMeasure.CONTRACT_COUNT,
        _descriptor(ContractValueUnit.QUOTE, AssetRelationship.THIRD),
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output == source
    assert result.formula_ids == ()


def test_identity_precedes_descriptor_and_unused_observation_assessment() -> None:
    source = OpenInterestValueV1(
        amount=Decimal("3"),
        measure=OpenInterestMeasure.NOTIONAL,
        denomination=NotionalDenomination.SETTLEMENT,
    )
    result = convert_open_interest(
        source,
        OpenInterestMeasure.NOTIONAL,
        InstrumentDescriptorV1(),
        target_denomination=NotionalDenomination.SETTLEMENT,
        mark_price=1,  # type: ignore[arg-type]
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output == source


def test_base_quote_path_does_not_require_instrument_metadata() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(
            amount=Decimal("3"),
            measure=OpenInterestMeasure.BASE_QUANTITY,
        ),
        OpenInterestMeasure.NOTIONAL,
        InstrumentDescriptorV1(),
        target_denomination=NotionalDenomination.QUOTE,
        mark_price=Decimal("5"),
        reporting_per_quote=Decimal("-1"),
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output is not None
    assert result.output.amount == Decimal("15")


def test_reporting_to_base_path_uses_only_selected_observations() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(
            amount=Decimal("1"),
            measure=OpenInterestMeasure.NOTIONAL,
            denomination=NotionalDenomination.REPORTING,
        ),
        OpenInterestMeasure.BASE_QUANTITY,
        InstrumentDescriptorV1(),
        mark_price=Decimal("4"),
        reporting_per_quote=Decimal("2"),
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output is not None
    assert result.output.amount == Decimal("0.125")


def test_settlement_mapping_requires_only_settlement_relationship() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(
            amount=Decimal("3"),
            measure=OpenInterestMeasure.NOTIONAL,
            denomination=NotionalDenomination.SETTLEMENT,
        ),
        OpenInterestMeasure.NOTIONAL,
        InstrumentDescriptorV1(
            settlement=SettlementDescriptorV1(asset_relationship=AssetRelationship.QUOTE)
        ),
        target_denomination=NotionalDenomination.QUOTE,
    )
    assert result.status is ConversionStatus.EXACT
    assert result.output == OpenInterestValueV1(
        amount=Decimal("3"),
        measure=OpenInterestMeasure.NOTIONAL,
        denomination=NotionalDenomination.QUOTE,
    )


def test_missing_settlement_mapping_does_not_request_contract_terms() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(
            amount=Decimal("3"),
            measure=OpenInterestMeasure.BASE_QUANTITY,
        ),
        OpenInterestMeasure.NOTIONAL,
        InstrumentDescriptorV1(),
        target_denomination=NotionalDenomination.SETTLEMENT,
    )
    assert result.status is ConversionStatus.MISSING_INPUT
    assert [(issue.code, issue.path) for issue in result.issues] == [
        (
            ConversionIssueCode.MISSING_ECONOMIC_ATTRIBUTE,
            "$.settlement.asset_relationship",
        )
    ]


def test_exact_decimal_result_is_independent_of_ambient_context() -> None:
    with localcontext() as context:
        context.prec = 2
        result = convert_open_interest(
            OpenInterestValueV1(
                amount=Decimal("1"),
                measure=OpenInterestMeasure.NOTIONAL,
                denomination=NotionalDenomination.QUOTE,
            ),
            OpenInterestMeasure.BASE_QUANTITY,
            InstrumentDescriptorV1(),
            mark_price=Decimal("8"),
        )
    assert result.status is ConversionStatus.EXACT
    assert result.output is not None
    assert result.output.amount == Decimal("0.125")


def test_nonterminating_decimal_returns_exact_ratio_for_caller_rounding() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(
            amount=Decimal("1"),
            measure=OpenInterestMeasure.NOTIONAL,
            denomination=NotionalDenomination.QUOTE,
        ),
        OpenInterestMeasure.BASE_QUANTITY,
        InstrumentDescriptorV1(),
        mark_price=Decimal("3"),
    )
    assert result.status is ConversionStatus.PRECISION_REQUIRED
    assert result.output is None
    assert result.exact_ratio == ExactRatioV1(numerator=1, denominator=3)
    assert [issue.code for issue in result.issues] == [ConversionIssueCode.NON_TERMINATING_DECIMAL]


def test_missing_descriptor_metadata_is_structured() -> None:
    result = convert_open_interest(
        OpenInterestValueV1(amount=Decimal("3"), measure=OpenInterestMeasure.CONTRACT_COUNT),
        OpenInterestMeasure.BASE_QUANTITY,
        InstrumentDescriptorV1(
            contract_value=ContractValueDescriptorV1(unit=ContractValueUnit.BASE),
            settlement=SettlementDescriptorV1(asset_relationship=AssetRelationship.QUOTE),
        ),
    )
    assert result.status is ConversionStatus.MISSING_INPUT
    assert [(issue.code, issue.path) for issue in result.issues] == [
        (ConversionIssueCode.MISSING_ECONOMIC_ATTRIBUTE, "$.contract_value.amount")
    ]
