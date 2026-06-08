# Portfolio Reconciliation Audit

Repository: security-intelligence-hub  
PAR: PAR-20260529-7482D734  
Portfolio Date: 2026-05-29  
Audit Date: 2026-06-08  
Source of Truth: incoming/portfolio/Portfolio_Positions_May-29-2026.csv

## Q3 — Portfolio Identity Validation

### Account Snapshot

| Field | Value |
|---|---|
| Source file | Portfolio_Positions_May-29-2026.csv |
| Download date | May-29-2026 10:38 a.m. ET |
| Account identities | X20548022 (General Brokerage), Z26346415 (Joint WROS-TOD), Z35123695 (Individual TOD) |
| Holdings in CSV | ~79 rows (excluding disclaimer footer) |
| SIH holdings after exclusions | 81 enriched holdings |
| PAR run ID | PAR-20260529-7482D734 |
| Snapshot ID | PSNAP-20260529-5E2353DEC9FB |
| Total market value (SIH) | $472,219.90 |
| Concentration tier | DIVERSIFIED |
| Overall alignment score | 0.4138 (41.38%) |

### Exclusion Notes

- M26CNT069 (CYBERARK SOFTWA F CONTRA, Account Z26346415): zero market value; excluded as ZERO_VALUE_LEGACY_POSITION.
- Fidelity disclaimer footer rows: excluded from analysis.

### Reconciliation Status

- 11/13 checks PASS
- 1 WARN
- 1 FAIL
- Reconciliation certification: 11/13 checks PASS, 1 WARN, 1 FAIL

VERDICT: This is the correct portfolio for the audit. The May-29 Fidelity export from account Z35123695 (Individual TOD) plus associated accounts is the intended source.

## Q1 — Cash Reconciliation Summary

### Fidelity CSV Cash-Type Entries

| Symbol | Description | Market Value | Classification |
|---|---|---|---|
| SPAXX | Held in Money Market (Z35123695) | $42,619.59 | Cash |

### SIH Cash Classification

| Field | Value |
|---|---|
| cash_mv (SIH) | $42,619.59 |
| cash_pct | 9.0254% |
| mandate_cash_target_pct | 7.0% |
| effective_floor_pct | 7.0% |
| floor_mv | $33,055.39 |
| excess_mv | $9,564.20 |
| excess_pct | 2.0254% |
| deployable_mv | $9,564.20 |
| settlement_adjustment | $0 |
| adjusted_deployable_mv | $9,564.20 |

### Reconciliation Finding

SIH reads SPAXX as $42,619.59 and classifies it entirely as CASH. This agrees with the Fidelity CSV value.

Note: There is a discrepancy between the question premise ($54,257.49) and the portfolio CSV ($42,619.59). This is fully explained in cash_reconciliation_report.md.

## Q4 — Recommendation Summary (Current Portfolio)

### Action Recommendations (True Executable)

| Type | Title | Drift | Severity |
|---|---|---|---|
| REDUCE_OVERWEIGHT | Reduce EQUITIES.US.MEGA.ULTRA_MEGA (+4.4%) | +4.45pp | MODERATE |
| REDUCE_OVERWEIGHT | Reduce EQUITIES.INTERNATIONAL.LARGE (+4.2%) | +4.25pp | MODERATE |
| REDUCE_OVERWEIGHT | Reduce EQUITIES.INTERNATIONAL (+6.1%) | +6.08pp | MODERATE |
| INCREASE_UNDERWEIGHT | Build EQUITIES.US.LARGE (-6.2%) | -6.17pp | MODERATE |
| INCREASE_UNDERWEIGHT | Build EQUITIES.US.MEGA.EXTENDED_MEGA (-4.1%) | -4.15pp | MODERATE |
| IMPROVE_REPLAY_ALIGNMENT | Replay opportunity in EQUITIES.US.LARGE | — | MODERATE |

True executable actions: 6

### Non-Action Intelligence

- 2 OBSERVATION (STRATEGIC_RETAIN_SIGNAL: DELL, MSFT)
- 3 NARRATIVE (retain narratives: MU, VRT, CVE)
- 22 EXPLAINABILITY (conviction cards, replay context)

Total cards displayed: 33

### Policy Suppressed

- TSLA: BLOCKED_BY_POLICY (DO_NOT_SELL active)

## Q5 — Policy Interaction Summary

| Symbol | Policy | Surface Impact |
|---|---|---|
| TSLA | DO_NOT_SELL | Blocked in deployment queue; BLOCKED_BY_POLICY state |
| DODFX | SELL_LAST | Appears in INTERNATIONAL reduction candidate list; should be tail-ranked (DEFERRED_BY_POLICY — pending PRA-IMPL-02) |

See recommendation_change_assessment.md for full Q4 impact and policy_engine_interaction in report section.
