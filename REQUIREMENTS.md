# Crypto Derivative Markets requirements

Status: normative for schema major version 1 and Python API major version 0.

The terms **must**, **must not**, **should**, and **may** express requirement strength.

## Boundary

- **CDM-BND-001:** The distribution must be a leaf library with no runtime dependencies.
- **CDM-BND-002:** The library must describe provider-independent economic meaning. It must
  not contain provider adapters, provider-specific identity definitions or mappings, catalog
  identifiers, service identifiers, network clients, configuration loading, persistence,
  scheduling, or deployment policy.
- **CDM-BND-003:** Concrete systems may map their native vocabulary into CDM values, but those
  mappings and their coverage declarations must remain owned by the integrating system.
- **CDM-BND-004:** The library must not infer missing economic metadata from a provider name,
  native product label, listing identifier, or consumer policy.
- **CDM-BND-005:** The library may carry an integrating system's opaque native identity values
  through a protocol-domain vocabulary. It must not interpret those values or use them as economic
  evidence.

## Versioned contracts

- **CDM-SCH-001:** Every top-level wire value must carry an exact `schema_id` URN.
- **CDM-SCH-002:** Each schema major must use closed objects and closed enumerations. Unknown
  fields or values must fail decoding rather than being ignored.
- **CDM-SCH-003:** Exact decimal values must use canonical decimal strings. Floating-point JSON
  numbers must not be accepted for economic quantities or rates.
- **CDM-SCH-004:** Timestamps must be canonical RFC 3339 UTC values.
- **CDM-SCH-005:** The Python distribution must ship all supported JSON Schemas and expose them
  through `schema_ids()`, `load_schema()`, and `load_schemas()` without requiring a validator.
- **CDM-SCH-006:** Python codecs and JSON Schemas must accept and reject every portable conformance
  vector identically. Local invariants outside JSON Schema's vocabulary must not weaken a portable
  wire contract.

## Python values and codecs

- **CDM-PY-001:** Public economic values must be immutable typed values.
- **CDM-PY-002:** Constructors must validate local invariants and must not coerce strings,
  integers, booleans, or floating-point values into economic types.
- **CDM-PY-003:** `to_data()` and `to_json()` must produce deterministic canonical values.
- **CDM-PY-004:** `from_data()` and `from_json()` must reject missing required fields, unknown
  fields, unknown schema versions, invalid enumerations, and non-canonical scalar encodings with
  structured `DecodeError` details.
- **CDM-PY-005:** The installed distribution must include the `py.typed` marker.

## Instrument descriptors and classification

- **CDM-INS-001:** `InstrumentDescriptorV1` must represent incomplete neutral metadata without
  substituting defaults. Missing nested fields must remain distinguishable.
- **CDM-INS-002:** `assess_instrument_descriptor()` must return an `InstrumentAssessmentV1`
  containing a capability, state, and ordered structured issues. Issue codes and canonical field
  paths must be suitable for programmatic handling; prose messages must not be the contract.
- **CDM-INS-003:** Metadata requirements must be capability-specific:

  | Capability | Required descriptor fields |
  |---|---|
  | `classification` | `instrument_kind`, `contract_value.unit`, `settlement.asset_relationship` |
  | `open_interest_conversion` | `contract_value.amount`, `contract_value.unit`, `settlement.asset_relationship` |
  | `funding_mechanism` | `instrument_kind`, `funding.mechanism` |
  | `funding_interval` | funding-mechanism fields, plus `funding.interval_seconds` only when periodic |
  | `complete_profile` | all fields needed to construct `InstrumentProfileV1` |

- **CDM-INS-004:** Payoff classification must depend only on the fixed contract-value unit and
  settlement-asset relationship. Maturity classification must depend only on instrument lifecycle
  kind. Margin and funding attributes must not gate either classification.
- **CDM-INS-005:** Classification must distinguish `linear`, `inverse`, `quanto`, and `other`.
  A profile outside the modeled linear and inverse relationships must never be forced into either
  family.
- **CDM-INS-006:** `InstrumentClassificationV1` must contain payoff and maturity classification;
  it must not mix independent funding or margin attributes into those results.
- **CDM-INS-007:** `InstrumentScenarioV1` must provide the amount-independent join key shared by
  catalog projections and acquisition capability declarations. It must contain the descriptor and
  classification schema identifiers, lifecycle kind, contract-value unit, settlement-asset
  relationship, payoff family, and maturity family. It must not contain provider, catalog,
  coverage, exact amount, settlement method, margin, or funding concerns.

## Native identity references

- **CDM-ID-001:** `NativeIdentityV1` must qualify an opaque non-empty value by a semantic role and
  a protocol identity namespace. Roles must distinguish instrument, pair, underlying, index,
  settlement asset, product family, and an explicitly unmodeled other role.
- **CDM-ID-002:** `NativeIdentityNamespace` must accept only `rest`, `websocket`, `fix`, or `rpc`
  protocol roots with optional lowercase neutral scope segments. Scope segments must name an
  identity domain or payload context and must not name a concrete provider, listing, catalog
  instance, or service.
- **CDM-ID-003:** `InstrumentReferenceV1` must keep an `InstrumentDescriptorV1` separate from an
  optional ordered native-identity collection. The collection must reject exact duplicates. Its
  order must not select one value over another.
- **CDM-ID-004:** `NativeIdentitySelectorV1` must match an identity by exact role and exact
  namespace without wildcards. Selection must return `unique`, `missing`, or `ambiguous` from match
  cardinality and must never choose the first of multiple matches.
- **CDM-ID-005:** Native identities and selectors must not alter descriptor assessment, payoff or
  maturity classification, scenario keys, datapoint meaning, or open-interest formulas.
- **CDM-ID-006:** Native identity discovery, native-value interpretation, provider mappings, and
  endpoint routing remain responsibilities of integrating libraries and services.

## Datapoints and lineage

- **CDM-DAT-001:** Open-interest meanings must distinguish contract count, base quantity, and
  explicitly denominated notional.
- **CDM-DAT-002:** Funding meanings must distinguish indicative rate, next rate, settled rate,
  interval, premium-rate component, interest-rate component, rate floor, and rate cap where those
  meanings are available.
- **CDM-DAT-003:** Every `DataPointDefinitionV1` must validate its unit, temporal mode, and
  denomination against the selected canonical meaning.
- **CDM-DAT-004:** `MeasurementLineageV1` must contain an ordered, non-empty derivation chain.
  It must distinguish native reporting, provider-defined formulas, canonical conversions, and
  estimates.
- **CDM-DAT-005:** Native reporting may only begin a lineage. Every formula, conversion, or
  estimate must carry a stable method identifier.

## Open-interest conversion

- **CDM-OI-001:** `convert_open_interest()` must accept either a complete profile or an incomplete
  descriptor and must return a structured result rather than inventing missing metadata.
- **CDM-OI-002:** Exact neutral conversion may use contract value, mark price, and a
  reporting-per-quote rate only when required by the selected conversion path.
- **CDM-OI-002A:** Runtime path selection must precede metadata assessment. Identity conversion must
  complete before instrument assessment, including identity in an unresolved settlement
  denomination. Base, quote, and reporting conversions must not require contract terms.
- **CDM-OI-003:** Successful conversion must expose an ordered list of stable formula identifiers.
- **CDM-OI-004:** Missing observations or instrument attributes must produce `missing_input` with
  structured issues. Economically unsupported paths must produce `unmodeled`.
- **CDM-OI-005:** Contract-count conversion for `quanto` and `other` payoff families must remain
  unmodeled until a future schema explicitly represents sufficient multiplier economics.
- **CDM-OI-006:** Identity and same-denomination conversions must not require an unrelated mark
  price or reporting rate.
- **CDM-OI-007:** Decimal arithmetic must not depend on the process-wide decimal context. `exact`
  means the mathematically exact rational result has a finite base-ten representation and is
  returned without rounding.
- **CDM-OI-008:** A mathematically exact result with a non-terminating base-ten representation must
  produce `precision_required` with its reduced integer ratio and formula identifiers. The caller
  owns any subsequent precision, rounding mode, and rounded-value lineage.

## Funding samples

- **CDM-FND-001:** `FundingSampleV1` must distinguish indicative, next, and settled rates and must
  validate that its lineage output has the same meaning.
- **CDM-FND-002:** Next and settled samples must carry an effective timestamp. A sample may carry
  a source-declared observation timestamp; its absence must remain explicit. Acquisition or
  retrieval timestamps belong to the acquiring library's source envelope and must not be
  substituted for missing source time.
- **CDM-FND-003:** Funding interval evidence must distinguish explicit duration, observed window,
  protocol schedule, and unspecified interval.
- **CDM-FND-003A:** An observed window must carry a canonical UTC start timestamp and a positive
  integer duration. Its end is defined as start plus duration, making ordering schema-validatable.
- **CDM-FND-004:** An unspecified or protocol-scheduled interval must not carry invented duration
  or window values.
- **CDM-FND-005:** Calculation origin must be represented by ordered lineage, not by a single
  ambiguous native-or-inferred flag.

## Compatibility and distribution

- **CDM-CMP-001:** Distribution releases must follow Semantic Versioning independently of schema
  major versions.
- **CDM-CMP-002:** Removing or renaming a field, changing a field meaning or requirement, adding any
  field to a closed object even when optional, or changing a closed enumeration requires a new
  schema major.
- **CDM-CMP-003:** Consumers must select supported schema identifiers explicitly. The library must
  not silently reinterpret an unsupported schema major.
- **CDM-CMP-004:** Every supported schema must have exactly one portable valid-and-invalid
  conformance vector set, and every vector set must identify one supported schema. Vectors must ship
  in both source and wheel distributions.
- **CDM-DST-001:** Source distributions and wheels must be reproducibly buildable from the public
  repository and installable under the distribution name `crypto-derivative-markets` with import
  namespace `cdm`.
- **CDM-DST-002:** Release automation must use PyPI trusted publishing and must not store a long-lived
  package-registry credential in repository configuration.
- **CDM-DST-003:** Release automation must repeat the complete lint, type, test, generated-document,
  build, and metadata-verification gate before publishing. Third-party actions must be referenced by
  immutable commit identifiers.
- **CDM-DOC-001:** Module documentation must be publishable as an Antora component and must keep
  generated vocabulary tables synchronized with every public closed enumeration, schema identifier,
  classification mapping, datapoint constraint, and formula identifier.
