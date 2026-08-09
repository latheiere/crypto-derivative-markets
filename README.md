# Crypto Derivative Markets

`crypto-derivative-markets` is a zero-runtime-dependency Python library for venue-neutral
crypto-derivative economics. Install the distribution from PyPI and import the `cdm` namespace:

```console
python -m pip install crypto-derivative-markets
```

The package supplies:

- versioned JSON Schemas and immutable Python values;
- incomplete instrument descriptors with capability-specific assessment;
- amount-independent instrument scenario keys;
- optional protocol-scoped native identity references with ambiguity-safe selection;
- payoff and maturity classification;
- canonical market-datapoint meanings and ordered calculation lineage;
- context-independent open-interest conversions with exact ratios, structured missing inputs, and
  explicit unmodeled outcomes;
- funding-rate and interval semantics that preserve missing source evidence;
- deterministic JSON codecs and portable conformance vectors.

It intentionally contains no provider adapters, provider-specific identity definitions or mappings,
catalog identifiers, network access, configuration, persistence, scheduling, or service policy.
Opaque native values may be carried through the typed identity-reference contract but are never
interpreted as economic evidence.

## Quick start

```python
from cdm import (
    AssetRelationship,
    ContractValueDescriptorV1,
    ContractValueUnit,
    InstrumentCapability,
    InstrumentDescriptorV1,
    InstrumentKind,
    SettlementDescriptorV1,
    assess_instrument_descriptor,
    instrument_scenario,
)

descriptor = InstrumentDescriptorV1(
    instrument_kind=InstrumentKind.PERPETUAL_SWAP,
    contract_value=ContractValueDescriptorV1(unit=ContractValueUnit.BASE),
    settlement=SettlementDescriptorV1(asset_relationship=AssetRelationship.QUOTE),
)

assessment = assess_instrument_descriptor(
    descriptor,
    InstrumentCapability.CLASSIFICATION,
)
scenario = instrument_scenario(descriptor)
```

Classification succeeds without contract amount, settlement method, margin, or funding metadata
because those attributes do not affect payoff or maturity. A conversion assessment can require a
different minimal set from the same descriptor.

## Contracts and documentation

- [Normative requirements](https://github.com/latheiere/crypto-derivative-markets/blob/main/REQUIREMENTS.md)
- [Antora documentation component](https://github.com/latheiere/crypto-derivative-markets/blob/main/docs/modules/ROOT/pages/index.adoc)
- [Versioned schemas](https://github.com/latheiere/crypto-derivative-markets/tree/main/src/cdm/schemas/v1)
- [Conformance vectors](https://github.com/latheiere/crypto-derivative-markets/tree/main/src/cdm/conformance/v1)
- [Compatibility policy](https://github.com/latheiere/crypto-derivative-markets/blob/main/docs/modules/ROOT/pages/concepts/compatibility.adoc)
- [Contribution guide](https://github.com/latheiere/crypto-derivative-markets/blob/main/CONTRIBUTING.md)

The project is in an initial public-contract release. Schema identifiers are versioned independently
from the Python distribution and are never inferred during decoding.
