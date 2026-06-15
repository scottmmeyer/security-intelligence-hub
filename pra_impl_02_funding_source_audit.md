# PRA-IMPL-02 Funding Source Audit

## Scope

Independent audit of `identify_funding_sources(...)` in `src/portfolio/recommendations.py`.
Evidence from code inspection and live runtime execution against real portfolio data.

---

## Q9. Is excess cash used first when policy permits?

**Yes, confirmed.**

Live trace with real portfolio data (SPAXX = 9.0% of portfolio):
- Cash reserve floor: 2.0% (`_CASH_RESERVE_FLOOR_PCT = 2.0`)
- Deployable cash: 9.0% – 2.0% = 7.0%
- EXCESS_CASH base score: 100.0
- Available % bonus: min(20, 7.03) = +7.03
- Final EXCESS_CASH score: **107.03**

TRIM_CANDIDATE scored 93.1. OVERWEIGHT_REDUCTION scored 90.25–92.83.

EXCESS_CASH won as expected. The scoring model correctly enforces cash-first when
excess cash exists.

**Mechanism:** The base score for EXCESS_CASH (100.0) is 14 points higher than
TRIM_CANDIDATE (86.0) and 20 points higher than OVERWEIGHT_REDUCTION (80.0), and
the available-% bonus only adds to this gap. Cash-first is structurally guaranteed
unless bearish signal bonuses on TRIM_CANDIDATE are extreme AND cash is minimal.

**Edge case to note:** If excess cash is 0.1% (just above threshold) and a TRIM_CANDIDATE
has VERY_BEARISH bearish signals AND high available pct, TRIM_CANDIDATE could theoretically
score higher than EXCESS_CASH. This is expected behavior — a tiny excess cash position
should not dominate a large bearish reduction opportunity.

---

## Q10. Is reserve protection functioning?

**Yes, confirmed.**

Code path:
```python
deployable_cash = max(0.0, total_cash_pct - _CASH_RESERVE_FLOOR_PCT)
if deployable_cash > 0.1:
    # create EXCESS_CASH source
```

With SPAXX at 9.0%, reserve floor at 2.0%:
- `deployable_cash = max(0.0, 9.0 - 2.0) = 7.0`
- Condition: 7.0 > 0.1 → EXCESS_CASH source created

Test `test_no_cash_scenario_uses_non_cash_sources` validates the boundary:
- SPAXX = 1.0% (below floor by implication since floor is 2%)
- `deployable_cash = max(0.0, 1.0 - 2.0) = 0.0` → NOT > 0.1
- No EXCESS_CASH source created
- Test confirms: `funding.sources[0].source_type != "EXCESS_CASH"`

The 0.1 minimum threshold prevents creating a trivial excess-cash source that
would rank first but deliver negligible capital.

---

## Q11. Are alternatives ranked correctly?

**Yes, confirmed.**

Observed ranking from live trace:
1. EXCESS_CASH (score 107.03)
2. TRIM_CANDIDATE (score 93.1)
3. OVERWEIGHT_REDUCTION INTERNATIONAL (score 92.83)
4. OVERWEIGHT_REDUCTION INTERNATIONAL.LARGE (score 90.25)

Two OVERWEIGHT_REDUCTION sources exist because two distinct allocation nodes
(EQUITIES.INTERNATIONAL and EQUITIES.INTERNATIONAL.LARGE) are independently
flagged as overweight. This is correct — the same underlying holdings (SBS, DODFX)
participate in both reductions but at different granularity levels.

The summary correctly identifies top 2 alternatives:
`"Alternatives considered: Trim Candidate, Overweight Reduction."`

Alternatives are sourced from `funding.sources[1:3]` — the next two entries after
primary. This is correct for the typical 3-4 source scenario. If there are fewer
than 2 alternatives, the clause is omitted (conditional check confirmed in code).

---

## Q12. Are tie-breakers stable?

**Yes, in tests. One gap in production scenarios.**

For `FundingSourceEntry` objects within the same `source_type`, the sort key in
`identify_funding_sources(...)` is:

```python
ranked_sources.sort(
    key=lambda s: (
        -float(s.reduction_score),
        int(s.priority),
        str(s.source_type),
    )
)
```

Note: there is no symbol-level tie-break for `FundingSourceEntry` objects (unlike
`CapitalSourceRecord` which has explicit symbol lexicographic ordering). If two
`FundingSourceEntry` objects have identical score, priority, and source_type, their
relative order is determined by Python's stable sort (insertion order from the
`sources` list construction).

In practice this is stable because the construction order is deterministic
(cash first, then trim, then overweight by node key order from alignment CSV).
But this is an implicit rather than explicit determinism guarantee.

**Mitigation:** The test suite does not expose this gap because the test fixture
creates sources with distinct scores. A minor hardening would be to add
`str(s.symbols[0] if s.symbols else "")` as a final tie-break.

---

## Source Construction Code Review

### EXCESS_CASH (priority=1)
- Built from `is_cash_equivalent=True` or `asset_class="CASH"` holdings
- Available pct = total cash pct – 2% floor
- Created only when deployable_cash > 0.1

### TRIM_CANDIDATE (priority=2)
- Built from overlays with `opportunity_flag="TRIM"`
- Available pct = sum of trim holding pct (up to 5 symbols)
- Created only when trim_holdings exist
- Bearish signal bonus applied in scoring

### OVERWEIGHT_REDUCTION (priority=3+)
- Built from alignment results with OVERWEIGHT drift and HIGH/MODERATE severity
- Available pct = node drift pct (approximate)
- One entry per overweight alignment node
- Created only when overweight nodes exist

### Policy on Ranking Order

Original `sources` list is built in order: cash → trim → overweight (by alignment iteration).
After `_funding_policy_score()` + `replace()` + sort, the list is re-ordered by score.
Re-ordering only matters when TRIM scores higher than OVERWEIGHT or vice versa; in
the live trace TRIM (93.1) > OVERWEIGHT (92.83), consistent with signal-quality preference.
