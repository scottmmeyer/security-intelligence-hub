# AI-001 Option B — Actual Portfolio Compliance Validator Design

Repository: security-intelligence-hub  
Date: 2026-06-09  
Status: Design only. No implementation.

## Context

AI-001 Option D (commit c09565e) delivered the Current Portfolio Compliance UI section. That section shows actual allocation bars vs policy ceilings, but produces no formal validator signal — it is a display-only feature. AI-001 Option B formalises the governance check: should actual portfolio positions exceeding a policy ceiling produce an observable, traceable validator result?

---

## Design Objective

Add a `CURRENT_PORTFOLIO_COMPLIANCE` validator group to the SIH governance framework. This validator reads actual portfolio allocation data from the most recent PAR and compares each node against the structural policy ceilings defined in `config/allocation_policy.yaml`.

The validator is **informational governance only**. It does not:
- Mutate allocation targets
- Mutate scores, rankings, or recommendations
- Trigger automatic rebalancing
- Block or modify CW-DAS, STI, ESS, CRA, or PAP outputs

---

## Q1 — Which Ceilings Should Be Monitored?

Based on `config/allocation_policy.yaml` `structural_policy` block:

| Rule ID | Metric | Policy Value | Source Field | Evaluation |
|---|---|---|---|---|
| CPV-01 | Combined Micro Cap (US + Intl) | max 5% | EQUITIES.US.MICRO + EQUITIES.INTERNATIONAL.MICRO | Combined actual > 5% |
| CPV-02 | Mega Cap concentration | max 50% | EQUITIES.US.MEGA | Actual > 50% |
| CPV-03 | Digital Assets | max 8% | DIGITAL | Actual > 8% |
| CPV-04 | Cash floor | min 2% | CASH | Actual < 2% |
| CPV-05 | International minimum | min 10% | EQUITIES.INTERNATIONAL + EQUITIES.EMERGING_MARKETS | Combined actual < 10% |
| CPV-06 | Single asset class max | max 80% | Any L1 node | Actual > 80% |
| CPV-07 | Equities minimum | min 40% | EQUITIES | Actual < 40% |
| CPV-08 | Fixed Income maximum | max 40% | FIXED_INCOME | Actual > 40% |

Note: `max_single_sector_pct` (20%) is not included in v1 because sector classification is not reliably available at the PAR alignment level. Include in v2 when sector data is stable.

---

## Q2 — What Tolerance Bands Are Appropriate?

Tolerance bands serve two purposes:
1. Account for normal portfolio drift between rebalancing events.
2. Distinguish between advisory awareness, actionable governance, and hard violations.

Recommended three-tier model:

| Band | Name | Definition | Operator Action |
|---|---|---|---|
| T0 | OK | actual ≤ ceiling (or ≥ floor) | None required |
| T1 | ADVISORY | excess within tolerance_advisory_pp | Note; no action required |
| T2 | WARN | excess > tolerance_advisory_pp but ≤ tolerance_warn_pp | Review recommended |
| T3 | FAIL | excess > tolerance_warn_pp | Rebalancing or governance review required |

Default threshold proposal (configurable per rule):

| Rule | tolerance_advisory_pp | tolerance_warn_pp |
|---|---|---|
| CPV-01 Micro Cap | 2pp | 4pp |
| CPV-02 Mega Cap | 5pp | 10pp |
| CPV-03 Digital | 1pp | 2pp |
| CPV-04 Cash floor | 1pp (below) | 2pp (below) |
| CPV-05 International min | 2pp (below) | 4pp (below) |
| CPV-06 Asset Class max | 5pp | 10pp |
| CPV-07 Equities min | 5pp (below) | 10pp (below) |
| CPV-08 FI max | 5pp | 10pp |

Example (CPV-01 Micro Cap today: actual = 8.33% + 0% = 8.33% vs 5.0% ceiling):
- excess = +3.33pp
- advisory threshold = 2pp → T1 passed
- warn threshold = 4pp → T2 not reached
- Result: **WARN** (excess 3.33pp > 2pp advisory, ≤ 4pp warn threshold)

Wait — re-evaluating: with advisory=2pp and warn=4pp, 3.33pp > 2pp but < 4pp → this is ADVISORY, not WARN. WARN requires excess > tolerance_warn_pp. Clarification in thresholds document.

---

## Q3 — Should WARN and FAIL Be Configurable?

**Yes.** Thresholds should be defined in `config/allocation_policy.yaml` under a new `compliance_tolerance` section. This:
- Allows policy adjustments without code changes
- Creates a governed, versioned record of tolerance decisions
- Permits different thresholds per rule

Proposed YAML extension:

```yaml
compliance_tolerance:
  CPV-01_micro_cap:
    advisory_pp: 2.0
    warn_pp: 4.0
  CPV-02_mega_cap:
    advisory_pp: 5.0
    warn_pp: 10.0
  CPV-03_digital:
    advisory_pp: 1.0
    warn_pp: 2.0
  CPV-04_cash_floor:
    advisory_pp: 1.0
    warn_pp: 2.0
  CPV-05_international_min:
    advisory_pp: 2.0
    warn_pp: 4.0
  CPV-06_asset_class_max:
    advisory_pp: 5.0
    warn_pp: 10.0
  CPV-07_equities_min:
    advisory_pp: 5.0
    warn_pp: 10.0
  CPV-08_fi_max:
    advisory_pp: 5.0
    warn_pp: 10.0
```

---

## Q4 — How Should Results Appear in Allocation Intelligence?

Recommended UI integration in three places:

### 1. Current Portfolio Compliance section (already exists from Option D)

Existing compliance bars get severity badges alongside the existing OVER indicator:
- Replace plain "OVER" badge with: ADVISORY (yellow) / WARN (orange) / FAIL (red)
- Add exceedance amount: "+3.33pp"

### 2. New Governance Signal Banner at top of Allocation Intelligence page

If any CPV check is WARN or FAIL, show a pinned banner:
- "Portfolio compliance: 1 WARN (Micro Cap +3.33pp) — rebalancing review recommended"

### 3. Validator Grid (Recalculation Status section)

Current grid shows strategic target recalculation validators. Add a clearly separated group:
- Header: "Current Portfolio Compliance"
- One row per CPV rule with OK / ADVISORY / WARN / FAIL status

---

## Q5 — Should Any Validator Affect Recommendation Generation?

**No.** The validator is informational governance only. It must not:
- Filter or suppress allocation recommendations
- Alter recommendation severity or urgency
- Change deployment queue ranking
- Influence any scoring computation

Rationale: Recommendation generation is driven by drift from strategic targets, not by absolute policy ceiling violations. These are separate decision domains. Conflating them would reduce operator clarity.

The validator provides context for human operator decisions; it does not automate them.

---

## Q6 — Governance Model

Recommended governance model: **Graded Advisory with Hard Stop threshold**.

- ADVISORY: informational, logged, displayed. No required action.
- WARN: displayed prominently. Operator review recommended before next portfolio change. No blocking.
- FAIL: displayed as hard governance signal. Operator must acknowledge before proceeding with any rebalancing that worsens the breach. System does not block autonomously.

This model follows the SIH governance principle:
> "SIH produces allocation intelligence recommendations only. Portfolio consumers own execution."

---

## Implementation Dependency Map

```
config/allocation_policy.yaml
    └── add compliance_tolerance section

src/allocation/validators.py
    └── add validate_portfolio_compliance(alignment_results, policy) function

src/portfolio/runner.py
    └── call validate_portfolio_compliance after alignment
    └── add portfolio_compliance_results to run output

ui/allocation_intelligence/app.js
    └── renderPortfolioCompliance() (already exists from Option D)
    └── extend to read portfolio_compliance_results from latest PAR

ui/allocation_intelligence/index.html
    └── extend compliance section with severity badges
    └── add governance banner if WARN/FAIL present
```

All changes are additive. No existing outputs are modified.
