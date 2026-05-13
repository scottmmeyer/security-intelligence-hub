# ESS Schema Contracts

## WP-03.2 Addendum: Fidelity Provider-Native Adapter Boundary

- Fidelity raw exports are provider-native and authoritative.
- Fidelity raw files are no longer expected to include canonical fields like
  `snapshot_date`, `provider`, or `source_file`.
- Canonical fields are populated by adapter and normalization layers after
  provider-native parsing.
- Unmapped provider-native columns are surfaced explicitly in validation and
  lineage outputs.

## Deterministic Contract Scope

This document defines expected CSV schema contracts for:

- Universe A: STARMINE covered intake
- Universe B: non-StarMine analyst intake

All malformed records are fail-closed with explicit validation errors.

## Universe A: STARMINE Covered

Landing zone: incoming/ess/starmine/

### Required Columns

- Symbol
- Company Name
- Security Type
- Equity Summary Score (ESS) from LSEG StarMine
- Market Capitalization

### Optional Columns

- Security Price
- Forward EPS Long Term Growth (3-5 Yrs)
- Jefferson Research
- Zacks Investment Research
- McLean Capital Management
- Geography

### Normalization Expectations

- Provider-native rows are adapted into canonical rows before strict
  validation and persistence checks.
- symbol is normalized to an uppercase trimmed token.
- coverage_domain is assigned as STARMINE_COVERED.
- ESS categorical text is normalized to canonical token values.
- Unknown provider columns are surfaced as explicit unmapped-column warnings.

## Universe B: NON_STARMINE_ANALYST

Landing zone: incoming/ess/non_starmine_zacks/

### Required Columns

- Symbol
- Company Name
- Security Type
- Zacks Investment Research
- Market Capitalization

### Optional Columns

- Security Price
- Forward EPS Long Term Growth (3-5 Yrs)
- Jefferson Research
- McLean Capital Management
- Geography

### Normalization Expectations

- Provider-native rows are adapted into canonical rows before strict
  validation and persistence checks.
- symbol is normalized to an uppercase trimmed token.
- coverage_domain is assigned as NON_STARMINE_ANALYST.
- analyst_rating preserves provider provenance lineage.

## Lineage Requirements

Each canonical row produced by provider adaptation must preserve:

- snapshot_date
- provider
- source_file
- coverage_domain
- run_id (assigned at ingestion stage)
- created_at_utc (assigned at persistence time)

## Malformed Row Handling Philosophy

- malformed rows fail validation with row-specific errors.
- duplicate symbols within the same intake file fail validation.
- empty files fail validation.
- invalid coverage domains or unsupported provider mappings fail validation.
- no silent row drops or silent correction.