# PRA-IMPL-02 Behavior Delta

## Scope

Forensic comparison of recommendation behavior before and after PRA-IMPL-02.
Evidence from: code inspection, live runtime execution, persisted PAR artifacts.

---

## Q1. Are recommendation targets different?

**No.**

The set of targets (recommendation types, affected symbols, drift percentages,
affected node keys) is identical before and after PRA-IMPL-02. The implementation
is additive to rationale text only for PAP recommendations.

Evidence: comparison of persisted `recommendations.json` in
PAR-CONCENTRATED_ALPHA-3FAFBBBF against code-executed output shows:
- Same 12 recommendations
- Same priority ordering
- Same `affected_symbols` tuples
- Same `recommendation_type` values

The new code does not alter any of the gating conditions, priority logic, severity
thresholds, or recommendation generation control flow in `generate_recommendations(...)`.

---

## Q2. Are funding sources different?

**PAP path: No behavioral change, but enriched rationale.**

The same sources are identified. The same primary source (EXCESS_CASH) is selected.
The ordering is now explicitly scored but the order in the pre-PRA and post-PRA runs
is the same, because the implicit cash-first ordering matched the new deterministic
score ordering (EXCESS_CASH base 100 > TRIM_CANDIDATE base 86 > OVERWEIGHT_REDUCTION base 80).

The delta is in the metadata attached to each source:
- Pre-PRA: `FundingSourceEntry.reduction_reason = ""`, `reduction_score = 0.0`
- Post-PRA: all three fields populated with explicit values

The change in the rationale string is confirmed:
- Pre-PRA: `"Funding source: Excess Cash (SPAXX, ~7.0% available)."`
- Post-PRA: adds Why, Alternatives, Policy clauses (~3 sentences)

**CRA path: Meaningful behavioral change in reduction ordering.**

The CRA reduction ranking NOW applies explicit conviction penalties. The pre-PRA
source builder sorted by category priority and estimated proceeds only. Post-PRA,
`score_reduction_candidates(...)` applies:
- VERY_BEARISH ESS: +12
- BEARISH signal: +8
- Conviction penalties: –2 to –22 based on deployment queue membership

**In the synthetic sample: NVDA's reduction priority was depressed from position 1
to position 4 because it is a CORE_CONVICTION_LEADER in the deployment queue.**
This is a real change in reduction candidate ordering that would be operator-visible.

---

## Q3. Are reduction priorities different?

**Yes, in the CRA path.**

In the capital source builder, all sources were previously sorted only by:
1. Category priority index
2. Estimated proceeds

Post-PRA, `score_reduction_candidates(...)` re-ranks based on:
1. `_CATEGORY_BASE` weight (SIGNAL_DETERIORATION=90 vs OVERWEIGHT_REDUCTION=76 etc.)
2. Priority band bonus (URGENT=+20, HIGH=+12)
3. ESS/signal bonuses
4. Drift bonus (capped at +18)
5. Tax penalty
6. Policy penalty
7. Conviction penalty (queue membership –2 to –22)

The conviction penalty is the most impactful new factor. It can suppress a
SIGNAL_DETERIORATION source that happens to also be in the high-conviction
deployment queue from dominating the reduction list.

**PAP path: No change.** `identify_funding_sources(...)` ranks `FundingSourceEntry`
objects by priority band (fixed 1/2/3) and then by the new score, but since EXCESS_CASH
is always priority=1 and that was already highest priority, the ordering is unchanged
for portfolios with excess cash.

---

## Q4. Does policy scoring actually influence ranking?

**Yes.**

Confirmed by conviction penalty trace:

| Scenario | Pre-PRA Position | Post-PRA Position |
|---|---|---|
| NVDA (OVERWEIGHT_REDUCTION, CCL in queue) | rank 1 by proceeds (~$95k) | rank 4 (score 80.0 vs MSFT 130.0) |
| MSFT (SIGNAL_DETERIORATION, URGENT, VERY_BEARISH) | rank varies | rank 1 (score 130.0) |

The ESS and signal bonuses also materially shift relative rank between candidates
in the same category. A BEARISH signal adds +7–8 points; VERY_BEARISH adds +12.

---

## Q5. Are any outputs unchanged despite new logic?

**PAP recommendation outputs are unchanged.** The text of `REDUCE_OVERWEIGHT` and
`DIVERSIFY_CONCENTRATION` recommendations contains no funding context and receives no
changes from PRA-IMPL-02.

For `INCREASE_UNDERWEIGHT` recommendations:
- Title: unchanged
- affected_symbols: unchanged
- priority/severity/confidence: unchanged
- rationale: expanded with 3 new clauses

The CRA `RotationProposal` payload now carries new fields that were empty before:
- `reduction_score`, `reduction_reason`, `policy_alignment_reason` on every source
- `funding_source_*` fields on every deployment target

All new fields default to `""` / `0.0` and are additive. The pre-PRA fields are
unchanged.

---

## Summary Table

| Dimension | PAP Path | CRA Path |
|---|---|---|
| Recommendation targets | Unchanged | Unchanged |
| Funding source selected | Unchanged | N/A (CRA annotates) |
| Reduction ordering | Unchanged | **Changed** — conviction penalty active |
| Rationale content | **Expanded** with 3 new clauses | Source card fields populated |
| Deployment target annotation | N/A | **New** — primary/alternatives attached |
| Explainability drivers | **New** 3 driver types extracted | N/A |
| Test gate | 126 passed | 126 passed |
