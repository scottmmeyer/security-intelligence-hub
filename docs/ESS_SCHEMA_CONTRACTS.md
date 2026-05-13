# ESS Schema Contracts

## Deterministic Contract Scope

This document defines expected CSV schema contracts for:

- Universe A: STARMINE covered intake
- Universe B: non-StarMine analyst intake

All malformed records are fail-closed with explicit validation errors.

## Universe A: STARMINE Covered

Landing zone: incoming/ess/starmine/

### Required Columns

- snapshot_date
- symbol
- provider
- source_file
- starmine_ess_text

### Optional Columns

- starmine_ess_numeric
- starmine_ess_numeric_estimated
- starmine_ess_source_type
- analyst_rating
- notes

### Normalization Expectations

- symbol normalized to uppercase trimmed token.
- coverage_domain assigned as STARMINE_COVERED unless explicit override policy
  is introduced later.
- starmine_ess_text preserved as-source (normalized to uppercase token form).
- starmine_ess_numeric only treated as authoritative when source_type is
  DIRECT_NUMERIC.

## Universe B: NON_STARMINE_ANALYST

Landing zone: incoming/ess/non_starmine_zacks/

### Required Columns

- snapshot_date
- symbol
- provider
- source_file
- analyst_rating

### Optional Columns

- starmine_ess_text
- starmine_ess_numeric
- starmine_ess_numeric_estimated
- starmine_ess_source_type
- notes

### Normalization Expectations

- symbol normalized to uppercase trimmed token.
- coverage_domain assigned as NON_STARMINE_ANALYST.
- if ESS text/numeric exists, provenance fields must remain explicit.

## Lineage Requirements

Each normalized row must preserve:

- snapshot_date
- provider
- source_file
- coverage_domain
- run_id (assigned at ingestion stage)

## Malformed Row Handling Philosophy

- malformed rows fail validation with row-specific errors.
- duplicate symbols within the same intake file fail validation.
- empty files fail validation.
- invalid coverage domains or source types fail validation.
- no silent row drops or silent correction.