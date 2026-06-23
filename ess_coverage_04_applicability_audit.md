# ESS-COVERAGE-04 Applicability Classification Audit

Date: 2026-06-17
Scope: Forensic audit only (no fixes implemented)

## Part A - Symbol-Level Applicability Inventory

Generated artifact:
- provider_applicability_inventory.csv (48 symbols total; union of ESS warning symbols + Danelfin stale + Yahoo stale)

Key totals:
- ESS warning symbols: 16
- Danelfin stale symbols: 32
- Yahoo stale symbols: 32
- Danelfin/Yahoo stale intersection: 32 (exact match)

Critical ESS applicability result:
- Under current applicability engine, only 1 of 16 ESS warning symbols is provider-applicable: SIMO
- Remaining 15 of 16 are classified not applicable with reason: not_in_base_equity_universe

ESS non-applicable symbols:
- BSVN, DODFX, FCPGX, FMCSX, FXAIX, MCB, SBS, SMR, SPCX, STNG, TTNDY, VB, VO, VOO, VWO

## Part B - Deep Dive on VOO, VB, SBS

From provider_applicability_inventory.csv:
- VOO: in_ess_absent_warning=1, ess_applicable=0, reason=not_in_base_equity_universe
- VB: in_ess_absent_warning=1, ess_applicable=0, reason=not_in_base_equity_universe
- SBS: in_ess_absent_warning=1, ess_applicable=0, reason=not_in_base_equity_universe

Root-cause path (code):
1. ESS warning assembly uses latest EQUITIES holdings directly, without provider-applicability filtering.
2. Applicability logic exists centrally and returns not_in_base_equity_universe for these symbols.
3. Because ESS warning path does not apply this filter, non-applicable symbols can still appear as TRUE_MISSING.

Evidence in current warning artifact:
- example_symbols includes SBS, VB, VOO
- each appears as gap_type=TRUE_MISSING

## Part C - Shared Degradation Pattern (Danelfin/Yahoo)

Current holdings-coverage computation indicates:
- applicable_holdings=55 for both Danelfin and Yahoo
- covered_today=22
- covered_within_threshold=23
- stale=32
- status=DEGRADED

Cross-provider alignment:
- Danelfin stale set and Yahoo stale set are identical (32/32 overlap)
- Both providers have one covered_within_threshold-only symbol: CAH

Interpretation:
- This is a shared classification/dependency pattern, not provider-specific drift.
- Applicability and stale classification are driven by a shared engine path.

## Part D - Governance Conclusions and Design-Only Remediation

Q1. Is VOO inclusion in ESS warning correct?
- No. Under current applicability criteria, VOO is not applicable (not_in_base_equity_universe) but still appears in ESS warning.

Q2. Is VB inclusion in ESS warning correct?
- No. VB is not applicable (not_in_base_equity_universe) but is included as TRUE_MISSING.

Q3. Is SBS inclusion in ESS warning correct?
- No. SBS is not applicable (not_in_base_equity_universe) but is included as TRUE_MISSING.

Q4. Of the 16 ESS warning symbols, how many are truly ESS-applicable?
- 1 symbol (SIMO) under the current engine.

Q5. Is the Danelfin/Yahoo degradation claim (Applicable 55, Covered today 22, Stale 32) accurate?
- Yes, for current holdings-coverage computation.
- Note: this differs from data/current/last_signal_refresh_report.json, which reflects an earlier 24-applicable context.

Q6. Is there a shared applicability defect?
- Yes. A shared defect exists at the integration boundary: ESS warning generation uses EQUITIES holdings without applying the shared provider-applicability filter, while holdings coverage does apply that filter.

Q7. Smallest safe remediation (design only, not implemented)?
- Introduce a single applicability gate in ESS warning build path using the same classify_provider_applicability criteria used by holdings coverage.
- Keep warning semantics unchanged after filtering (TRUE_MISSING/STALE_ESS/NO_FRESH_STARMINE).
- Add regression assertions for non-applicable ETFs/ADRs/funds to prevent reintroduction.

Q8. Should a new GitHub issue be created?
- Yes.
- Recommended issue scope: ESS-COVERAGE-04 Applicability Alignment
- Recommended acceptance criteria:
  - ESS warning excludes symbols classified not applicable by shared applicability logic.
  - SBS/VB/VOO are excluded from ESS warning when not applicable.
  - ESS warning counts reconcile with holdings coverage applicable universe.
  - Regression tests cover base-universe exclusions and provider parity.

## Evidence References

- src/portfolio/holdings_coverage.py
  - classify_provider_applicability and provider-agnostic behavior (provider argument discarded)
  - summarize_holdings_coverage stale/threshold classification path

- src/portfolio/ess_coverage.py
  - ESS warning built from latest EQUITIES holdings
  - TRUE_MISSING / STALE_ESS gap assignment path

- data/current/ess_coverage_warning.json
  - warning_count=16
  - example_symbols: SBS, VB, VOO

- provider_applicability_inventory.csv
  - Symbol-level applicability verdicts for ESS warning + Danelfin stale + Yahoo stale universe

- data/current/last_signal_refresh_report.json
  - Historical report context showing earlier 24-applicable scope
