"""Exact, economically neutral open-interest conversions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from math import gcd
from typing import Callable, List, Mapping, Optional, Sequence, Tuple, Union, cast

from .classification import classify_payoff
from .errors import ValidationError
from .models import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    InstrumentDescriptorV1,
    InstrumentProfileV1,
    NotionalDenomination,
    OpenInterestMeasure,
    OpenInterestValueV1,
    PayoffFamily,
    SettlementDescriptorV1,
)


class ConversionStatus(str, Enum):
    """Outcome of an attempted exact conversion."""

    EXACT = "exact"
    PRECISION_REQUIRED = "precision_required"
    MISSING_INPUT = "missing_input"
    UNMODELED = "unmodeled"


class ConversionIssueCode(str, Enum):
    """Reason an exact decimal conversion was not produced."""

    MISSING_MARK_PRICE = "missing_mark_price"
    MISSING_REPORTING_RATE = "missing_reporting_rate"
    MISSING_ECONOMIC_ATTRIBUTE = "missing_economic_attribute"
    NON_TERMINATING_DECIMAL = "non_terminating_decimal"
    UNMODELED_PAYOFF = "unmodeled_payoff"
    UNRESOLVED_SETTLEMENT = "unresolved_settlement"


class ConversionFormula(str, Enum):
    """Stable identifiers for exact neutral conversion formulas."""

    CONTRACTS_TO_BASE_LINEAR = "open_interest.contracts_to_base.linear.v1"
    BASE_TO_CONTRACTS_LINEAR = "open_interest.base_to_contracts.linear.v1"
    CONTRACTS_TO_QUOTE_INVERSE = "open_interest.contracts_to_quote.inverse.v1"
    QUOTE_TO_CONTRACTS_INVERSE = "open_interest.quote_to_contracts.inverse.v1"
    BASE_TO_QUOTE_AT_MARK = "open_interest.base_to_quote.at_mark.v1"
    QUOTE_TO_BASE_AT_MARK = "open_interest.quote_to_base.at_mark.v1"
    QUOTE_TO_REPORTING = "open_interest.quote_to_reporting.v1"
    REPORTING_TO_QUOTE = "open_interest.reporting_to_quote.v1"


@dataclass(frozen=True)
class ConversionIssueV1:
    """Structured obstacle to an exact decimal conversion."""

    code: ConversionIssueCode
    path: str
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.code, ConversionIssueCode):
            raise ValidationError("invalid_type", "$.issues[].code", "expected ConversionIssueCode")
        if not isinstance(self.path, str) or not self.path.startswith("$."):
            raise ValidationError("invalid_value", "$.issues[].path", "expected a field path")
        if not isinstance(self.message, str) or not self.message:
            raise ValidationError("invalid_value", "$.issues[].message", "expected a message")


@dataclass(frozen=True)
class ExactRatioV1:
    """Reduced rational value whose decimal expansion does not terminate."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if type(self.numerator) is not int:
            raise ValidationError("invalid_type", "$.exact_ratio.numerator", "expected integer")
        if type(self.denominator) is not int or self.denominator <= 0:
            raise ValidationError(
                "invalid_value",
                "$.exact_ratio.denominator",
                "expected a positive integer",
            )
        if gcd(self.numerator, self.denominator) != 1:
            raise ValidationError(
                "invalid_value",
                "$.exact_ratio",
                "expected a reduced rational value",
            )


@dataclass(frozen=True)
class OpenInterestConversionV1:
    """Result of an exact open-interest conversion attempt."""

    status: ConversionStatus
    output: Optional[OpenInterestValueV1]
    formula_ids: Tuple[str, ...]
    issues: Tuple[ConversionIssueV1, ...]
    exact_ratio: Optional[ExactRatioV1] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, ConversionStatus):
            raise ValidationError("invalid_type", "$.status", "expected ConversionStatus")
        if type(self.formula_ids) is not tuple or not all(
            isinstance(item, str) and item for item in self.formula_ids
        ):
            raise ValidationError("invalid_type", "$.formula_ids", "expected a string tuple")
        if type(self.issues) is not tuple or not all(
            isinstance(item, ConversionIssueV1) for item in self.issues
        ):
            raise ValidationError("invalid_type", "$.issues", "expected an issue tuple")

        if self.status is ConversionStatus.EXACT:
            if (
                not isinstance(self.output, OpenInterestValueV1)
                or self.issues
                or self.exact_ratio is not None
            ):
                raise ValidationError(
                    "inconsistent_conversion",
                    "$",
                    "an exact result requires decimal output and no issue or ratio",
                )
        elif self.status is ConversionStatus.PRECISION_REQUIRED:
            if (
                self.output is not None
                or not self.formula_ids
                or len(self.issues) != 1
                or self.issues[0].code is not ConversionIssueCode.NON_TERMINATING_DECIMAL
                or not isinstance(self.exact_ratio, ExactRatioV1)
            ):
                raise ValidationError(
                    "inconsistent_conversion",
                    "$",
                    "a precision-required result needs formulas, one issue, and an exact ratio",
                )
        elif (
            self.output is not None
            or not self.issues
            or self.formula_ids
            or self.exact_ratio is not None
        ):
            raise ValidationError(
                "inconsistent_conversion",
                "$",
                "a missing or unmodeled result requires only structured issues",
            )


class _Node(str, Enum):
    CONTRACTS = "contracts"
    BASE = "base"
    QUOTE = "quote"
    REPORTING = "reporting"


class _Factor(str, Enum):
    CONTRACT_VALUE = "contract_value"
    MARK_PRICE = "mark_price"
    REPORTING_RATE = "reporting_rate"


@dataclass(frozen=True)
class _Edge:
    source: _Node
    target: _Node
    formula: ConversionFormula
    factor: _Factor
    transform: Callable[[Fraction, Fraction], Fraction]


def _multiply(value: Fraction, factor: Fraction) -> Fraction:
    return value * factor


def _divide(value: Fraction, factor: Fraction) -> Fraction:
    return value / factor


def _require_positive_decimal(value: object, path: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ValidationError("invalid_value", path, "expected a positive finite Decimal")
    return value


def _terminating_decimal(value: Fraction) -> Optional[Decimal]:
    """Return an exact finite Decimal without consulting the ambient context."""

    if value.numerator == 0:
        return Decimal("0")
    denominator = value.denominator
    powers_of_two = 0
    powers_of_five = 0
    while denominator % 2 == 0:
        denominator //= 2
        powers_of_two += 1
    while denominator % 5 == 0:
        denominator //= 5
        powers_of_five += 1
    if denominator != 1:
        return None

    scale = max(powers_of_two, powers_of_five)
    coefficient = abs(value.numerator)
    coefficient *= 2 ** (scale - powers_of_two)
    coefficient *= 5 ** (scale - powers_of_five)
    digits = tuple(int(character) for character in str(coefficient))
    sign = 1 if value.numerator < 0 else 0
    return Decimal((sign, digits, -scale))


def _same_semantic_value(
    source: OpenInterestValueV1,
    target_measure: OpenInterestMeasure,
    target_denomination: Optional[NotionalDenomination],
) -> bool:
    if source.measure is not target_measure:
        return False
    if source.measure is OpenInterestMeasure.NOTIONAL:
        return source.denomination is target_denomination
    return True


def _settlement_relationship(
    instrument: Union[InstrumentProfileV1, InstrumentDescriptorV1],
) -> Optional[AssetRelationship]:
    if isinstance(instrument, InstrumentProfileV1):
        return instrument.settlement.asset_relationship
    settlement = instrument.settlement
    if settlement is None:
        return None
    return settlement.asset_relationship


def _contract_terms(
    instrument: Union[InstrumentProfileV1, InstrumentDescriptorV1],
) -> Tuple[
    Optional[Decimal],
    Optional[ContractValueUnit],
    Optional[AssetRelationship],
    Tuple[ConversionIssueV1, ...],
]:
    if isinstance(instrument, InstrumentProfileV1):
        return (
            instrument.contract_value.amount,
            instrument.contract_value.unit,
            instrument.settlement.asset_relationship,
            (),
        )

    contract_value: Optional[ContractValueDescriptorV1] = instrument.contract_value
    settlement: Optional[SettlementDescriptorV1] = instrument.settlement
    amount = contract_value.amount if contract_value is not None else None
    unit = contract_value.unit if contract_value is not None else None
    relationship = settlement.asset_relationship if settlement is not None else None
    missing = []
    if amount is None:
        missing.append(_missing_attribute("$.contract_value.amount"))
    if unit is None:
        missing.append(_missing_attribute("$.contract_value.unit"))
    if relationship is None:
        missing.append(_missing_attribute("$.settlement.asset_relationship"))
    return amount, unit, relationship, tuple(missing)


def _node_for_denomination(
    denomination: NotionalDenomination,
    settlement_relationship: Optional[AssetRelationship],
) -> Optional[_Node]:
    if denomination is NotionalDenomination.BASE:
        return _Node.BASE
    if denomination is NotionalDenomination.QUOTE:
        return _Node.QUOTE
    if denomination is NotionalDenomination.REPORTING:
        return _Node.REPORTING
    if settlement_relationship is AssetRelationship.BASE:
        return _Node.BASE
    if settlement_relationship is AssetRelationship.QUOTE:
        return _Node.QUOTE
    return None


def _value_node(
    value: OpenInterestValueV1,
    settlement_relationship: Optional[AssetRelationship],
) -> Optional[_Node]:
    if value.measure is OpenInterestMeasure.CONTRACT_COUNT:
        return _Node.CONTRACTS
    if value.measure is OpenInterestMeasure.BASE_QUANTITY:
        return _Node.BASE
    denomination = cast(NotionalDenomination, value.denomination)
    return _node_for_denomination(denomination, settlement_relationship)


def _target_node(
    measure: OpenInterestMeasure,
    denomination: Optional[NotionalDenomination],
    settlement_relationship: Optional[AssetRelationship],
) -> Optional[_Node]:
    if measure is OpenInterestMeasure.CONTRACT_COUNT:
        return _Node.CONTRACTS
    if measure is OpenInterestMeasure.BASE_QUANTITY:
        return _Node.BASE
    return _node_for_denomination(
        cast(NotionalDenomination, denomination),
        settlement_relationship,
    )


def _conversion_edges(payoff: Optional[PayoffFamily]) -> Sequence[_Edge]:
    edges: List[_Edge] = [
        _Edge(
            _Node.BASE,
            _Node.QUOTE,
            ConversionFormula.BASE_TO_QUOTE_AT_MARK,
            _Factor.MARK_PRICE,
            _multiply,
        ),
        _Edge(
            _Node.QUOTE,
            _Node.BASE,
            ConversionFormula.QUOTE_TO_BASE_AT_MARK,
            _Factor.MARK_PRICE,
            _divide,
        ),
        _Edge(
            _Node.QUOTE,
            _Node.REPORTING,
            ConversionFormula.QUOTE_TO_REPORTING,
            _Factor.REPORTING_RATE,
            _multiply,
        ),
        _Edge(
            _Node.REPORTING,
            _Node.QUOTE,
            ConversionFormula.REPORTING_TO_QUOTE,
            _Factor.REPORTING_RATE,
            _divide,
        ),
    ]
    if payoff is PayoffFamily.LINEAR:
        edges.extend(
            (
                _Edge(
                    _Node.CONTRACTS,
                    _Node.BASE,
                    ConversionFormula.CONTRACTS_TO_BASE_LINEAR,
                    _Factor.CONTRACT_VALUE,
                    _multiply,
                ),
                _Edge(
                    _Node.BASE,
                    _Node.CONTRACTS,
                    ConversionFormula.BASE_TO_CONTRACTS_LINEAR,
                    _Factor.CONTRACT_VALUE,
                    _divide,
                ),
            )
        )
    elif payoff is PayoffFamily.INVERSE:
        edges.extend(
            (
                _Edge(
                    _Node.CONTRACTS,
                    _Node.QUOTE,
                    ConversionFormula.CONTRACTS_TO_QUOTE_INVERSE,
                    _Factor.CONTRACT_VALUE,
                    _multiply,
                ),
                _Edge(
                    _Node.QUOTE,
                    _Node.CONTRACTS,
                    ConversionFormula.QUOTE_TO_CONTRACTS_INVERSE,
                    _Factor.CONTRACT_VALUE,
                    _divide,
                ),
            )
        )
    return edges


def _find_path(edges: Sequence[_Edge], source: _Node, target: _Node) -> Optional[List[_Edge]]:
    queue: deque[Tuple[_Node, List[_Edge]]] = deque([(source, [])])
    visited = {source}
    while queue:
        node, path = queue.popleft()
        if node is target:
            return path
        for edge in edges:
            if edge.source is node and edge.target not in visited:
                visited.add(edge.target)
                queue.append((edge.target, [*path, edge]))
    return None


def _missing_attribute(path: str) -> ConversionIssueV1:
    return ConversionIssueV1(
        code=ConversionIssueCode.MISSING_ECONOMIC_ATTRIBUTE,
        path=path,
        message="required neutral instrument metadata is missing",
    )


def _issue(code: ConversionIssueCode) -> ConversionIssueV1:
    details: Mapping[ConversionIssueCode, Tuple[str, str]] = {
        ConversionIssueCode.MISSING_MARK_PRICE: (
            "$.mark_price",
            "an exact conversion path requires a positive mark price",
        ),
        ConversionIssueCode.MISSING_REPORTING_RATE: (
            "$.reporting_per_quote",
            "an exact conversion path requires a positive reporting-per-quote rate",
        ),
        ConversionIssueCode.MISSING_ECONOMIC_ATTRIBUTE: (
            "$.instrument",
            "required neutral instrument metadata is missing",
        ),
        ConversionIssueCode.NON_TERMINATING_DECIMAL: (
            "$.output.amount",
            "the exact rational result requires caller-owned decimal precision",
        ),
        ConversionIssueCode.UNMODELED_PAYOFF: (
            "$.instrument",
            "contract-count conversion is not modeled for this payoff family",
        ),
        ConversionIssueCode.UNRESOLVED_SETTLEMENT: (
            "$.denomination",
            "the settlement denomination is distinct from base and quote",
        ),
    }
    path, message = details[code]
    return ConversionIssueV1(code=code, path=path, message=message)


def convert_open_interest(
    source: OpenInterestValueV1,
    target_measure: OpenInterestMeasure,
    instrument: Union[InstrumentProfileV1, InstrumentDescriptorV1],
    *,
    target_denomination: Optional[NotionalDenomination] = None,
    mark_price: Optional[Decimal] = None,
    reporting_per_quote: Optional[Decimal] = None,
) -> OpenInterestConversionV1:
    """Convert using only metadata and observations selected by the runtime path."""

    if not isinstance(source, OpenInterestValueV1):
        raise ValidationError("invalid_type", "$.source", "expected OpenInterestValueV1")
    if not isinstance(target_measure, OpenInterestMeasure):
        raise ValidationError("invalid_type", "$.target_measure", "expected OpenInterestMeasure")
    if not isinstance(instrument, (InstrumentProfileV1, InstrumentDescriptorV1)):
        raise ValidationError(
            "invalid_type",
            "$.instrument",
            "expected InstrumentProfileV1 or InstrumentDescriptorV1",
        )
    if target_measure is OpenInterestMeasure.NOTIONAL:
        if not isinstance(target_denomination, NotionalDenomination):
            raise ValidationError(
                "missing_denomination",
                "$.target_denomination",
                "a notional target requires an economic denomination",
            )
    elif target_denomination is not None:
        raise ValidationError(
            "unexpected_denomination",
            "$.target_denomination",
            "denomination is only valid for a notional target",
        )

    if _same_semantic_value(source, target_measure, target_denomination):
        return OpenInterestConversionV1(
            status=ConversionStatus.EXACT,
            output=source,
            formula_ids=(),
            issues=(),
        )

    settlement_needed = (
        source.measure is OpenInterestMeasure.NOTIONAL
        and source.denomination is NotionalDenomination.SETTLEMENT
    ) or (
        target_measure is OpenInterestMeasure.NOTIONAL
        and target_denomination is NotionalDenomination.SETTLEMENT
    )
    settlement_relationship = _settlement_relationship(instrument) if settlement_needed else None
    if settlement_needed and settlement_relationship is None:
        return OpenInterestConversionV1(
            status=ConversionStatus.MISSING_INPUT,
            output=None,
            formula_ids=(),
            issues=(_missing_attribute("$.settlement.asset_relationship"),),
        )

    source_node = _value_node(source, settlement_relationship)
    target_node = _target_node(
        target_measure,
        target_denomination,
        settlement_relationship,
    )
    if source_node is None or target_node is None:
        return OpenInterestConversionV1(
            status=ConversionStatus.UNMODELED,
            output=None,
            formula_ids=(),
            issues=(_issue(ConversionIssueCode.UNRESOLVED_SETTLEMENT),),
        )

    contract_amount: Optional[Decimal] = None
    payoff: Optional[PayoffFamily] = None
    if source_node is _Node.CONTRACTS or target_node is _Node.CONTRACTS:
        contract_amount, contract_unit, contract_settlement, issues = _contract_terms(instrument)
        if issues:
            return OpenInterestConversionV1(
                status=ConversionStatus.MISSING_INPUT,
                output=None,
                formula_ids=(),
                issues=issues,
            )
        payoff = classify_payoff(
            cast(ContractValueUnit, contract_unit),
            cast(AssetRelationship, contract_settlement),
        )

    edges = _conversion_edges(payoff)
    path = _find_path(edges, source_node, target_node)
    if path is None:
        return OpenInterestConversionV1(
            status=ConversionStatus.UNMODELED,
            output=None,
            formula_ids=(),
            issues=(_issue(ConversionIssueCode.UNMODELED_PAYOFF),),
        )

    factors: Mapping[_Factor, Optional[Decimal]] = {
        _Factor.CONTRACT_VALUE: contract_amount,
        _Factor.MARK_PRICE: mark_price,
        _Factor.REPORTING_RATE: reporting_per_quote,
    }
    missing_codes = []
    for edge in path:
        if factors[edge.factor] is None:
            missing_codes.append(
                ConversionIssueCode.MISSING_MARK_PRICE
                if edge.factor is _Factor.MARK_PRICE
                else ConversionIssueCode.MISSING_REPORTING_RATE
            )
    if missing_codes:
        unique_missing = tuple(dict.fromkeys(missing_codes))
        return OpenInterestConversionV1(
            status=ConversionStatus.MISSING_INPUT,
            output=None,
            formula_ids=(),
            issues=tuple(_issue(code) for code in unique_missing),
        )

    amount = Fraction(source.amount)
    formula_ids = []
    for edge in path:
        factor_path = {
            _Factor.CONTRACT_VALUE: "$.instrument.contract_value.amount",
            _Factor.MARK_PRICE: "$.mark_price",
            _Factor.REPORTING_RATE: "$.reporting_per_quote",
        }[edge.factor]
        factor = _require_positive_decimal(factors[edge.factor], factor_path)
        amount = edge.transform(amount, Fraction(factor))
        formula_ids.append(edge.formula.value)

    decimal_amount = _terminating_decimal(amount)
    if decimal_amount is None:
        return OpenInterestConversionV1(
            status=ConversionStatus.PRECISION_REQUIRED,
            output=None,
            formula_ids=tuple(formula_ids),
            issues=(_issue(ConversionIssueCode.NON_TERMINATING_DECIMAL),),
            exact_ratio=ExactRatioV1(
                numerator=amount.numerator,
                denominator=amount.denominator,
            ),
        )

    return OpenInterestConversionV1(
        status=ConversionStatus.EXACT,
        output=OpenInterestValueV1(
            amount=decimal_amount,
            measure=target_measure,
            denomination=target_denomination,
        ),
        formula_ids=tuple(formula_ids),
        issues=(),
    )
