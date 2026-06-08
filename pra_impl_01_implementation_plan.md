# PRA-IMPL-01 Implementation Plan

Project: Security Intelligence Hub (SIH)  
Issue: PRA-IMPL-01 Typed Recommendation Contract and Card Schema  
Date: 2026-06-08

## Scope

Additive fields only. No scores, ranking, generation logic, UI, or policy behavior changes.

## Affected Files

### 1. src/portfolio/models.py

Add five new fields with safe defaults to `PortfolioRecommendation` frozen dataclass:

| Field | Default | Notes |
|---|---|---|
| `card_type` | `"DIAGNOSTIC"` | Safe fallback for unclassified cards |
| `execution_state` | `"EXECUTABLE"` | Existing recommendations default to executable |
| `effective_action` | `""` | Empty string = not yet resolved |
| `evidence_link` | `""` | Empty string = no linked artifact |
| `card_lifecycle_state` | `"OBSERVED"` | Starting lifecycle state |

### 2. src/portfolio/recommendations.py

Set `card_type` at construction time in `generate_recommendations()` and `_generate_strategic_trim_recs()`.

Mapping: see pra_impl_01_schema_mapping.md.

### 3. src/portfolio/phase_e_synthesis.py

Set `card_type` at construction time for Phase E recommendation types.

### 4. tests/test_pra_impl_01_card_schema.py (new)

New test file covering:
- card_type present on all PortfolioRecommendation instances
- ACTION card types carry non-empty execution_state
- Defaults are safe for every construction site
- No existing field values changed

## Non-Changes

- `runner.py` — no changes required; `dataclasses.asdict()` auto-serialises new fields
- CW-DAS scoring — untouched
- alignment.py — untouched
- operator_policy.py — untouched
- CRA models — untouched

## Serialisation Note

`runner.py` uses `dataclasses.asdict(rec)` to write `recommendations.json`. New fields on the dataclass are automatically included in serialisation output. No runner changes required.

## Risk

Low. All new fields have safe defaults. Frozen dataclass pattern requires explicit values at all call sites — the compiler will surface any missed sites at test time.
