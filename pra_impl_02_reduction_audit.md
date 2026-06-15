# PRA-IMPL-02 Reduction Ranking Audit

## Scope

Independent inspection of `score_reduction_candidates(...)` in
`src/portfolio/cra/funding_policy.py`. Evidence from code inspection and
live runtime execution.

---

## Scoring Formula (from code)

```
score = _CATEGORY_BASE[category]           # SIGNAL_DETERIORATION=90, STRATEGIC_EXIT=84,
                                            # OVERWEIGHT_REDUCTION=76, TAX_AWARE_EXIT=62,
                                            # LOW_CONVICTION_REDUCTION=55, other=40

      + _PRIORITY_BONUS[priority]           # URGENT=+20, HIGH=+12, MODERATE=+6, LOW=+2, DEFER=-10

      + _ess_bonus(ess_score_text)          # VERY_BEARISH=+12, BEARISH=+7, BULLISH=-8, else 0

      + _signal_bonus(signal_direction)     # BEARISH=+8, BULLISH=-7, else 0

      + min(18.0, max(0.0, drift_pct))      # drift capped at +18

      + _tax_penalty(tax_bucket)            # bucket A=+4, D=-10, E=-7, else 0

      + _policy_penalty(policy_type)        # SELL_LAST=-5, CORE_ANCHOR=-8, DO_NOT_SELL=-100

      + _conviction_penalty(sym, queue)     # CORE_CONVICTION_LEADER=-22,
                                            # HIGH_CONVICTION_ANCHOR=-13,
                                            # rank<=5=-8, else=-2
```

Blocked sources (`blocked_by_policy=True`) are zeroed and remain at score 0.0.

---

## Representative Sample — Ranked Output

Inputs tested against live scoring engine:

| Rank | Symbol | Category | Priority | ESS | Signal | Drift | Score | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | MSFT | SIGNAL_DETERIORATION | URGENT | VERY_BEARISH | BEARISH | — | **130.0** | 90+20+12+8 = 130 |
| 2 | AAPL | SIGNAL_DETERIORATION | HIGH | BEARISH | BEARISH | — | 117.0 | 90+12+7+8 = 117 |
| 3 | AMZN | STRATEGIC_EXIT | HIGH | — | — | — | 96.0 | 84+12 = 96 |
| 4 | NVDA | OVERWEIGHT_REDUCTION | HIGH | — | — | 14pp | **80.0** | 76+12+min(18,14)+0 –22(CCL) = 80 |
| 5 | META | LOW_CONVICTION_REDUCTION | MODERATE | — | — | — | 61.0 | 55+6 = 61 |

**NVDA conviction penalty confirmed:** Without the –22 CCL penalty, NVDA would score
76+12+14 = 102, ranking #2. The penalty correctly suppresses a high-conviction
deployment candidate from topping the reduction list.

---

## Q6. Is ranking deterministic?

**Yes.**

Sort keys in `score_reduction_candidates(...)`:
```python
scored.sort(
    key=lambda s: (
        -float(s.reduction_score),   # primary: descending score
        -float(s.estimated_proceeds), # secondary: descending proceeds
        str(s.symbol),               # tie-break: ascending symbol (lexicographic)
    )
)
```

All three sort keys are deterministic. Given identical inputs, the output is
always identical. No random state, timestamps, or external calls involved.

Tie-break test (from test suite, `test_reduction_tie_breaks_by_symbol`):
- AAA and ZZZ both LOW_CONVICTION_REDUCTION, LOW priority, same proceeds → AAA ranked first
- Confirmed by test passage.

---

## Q7. Is ranking explainable?

**Yes.**

Each ranked source carries:
- `reduction_reason`: human-readable sentence per category (e.g.,
  "Weak signal posture and deterioration evidence justify reducing this holding first.")
- `policy_alignment_reason`: single standard sentence about philosophy alignment
- `reduction_score`: numeric score allowing operator to reproduce manually

Operators can:
1. Read the category
2. Read the score
3. See the rationale sentence
4. Understand whether conviction penalty or ESS bonus drove rank

One gap: the score components are not individually surfaced. Operators see the
final score but not the additive breakdown (e.g., "90 base + 20 URGENT + 12 VERY_BEARISH").
This is an explainability surface gap, not a correctness gap.

---

## Q8. Can operators reproduce rankings manually?

**Partially.**

An operator with the category, priority, ESS, signal, drift, and deployment queue
membership can manually compute the score using the formula above. All inputs are
sourced from persisted overlay data and the deployment queue — both visible in the UI.

**Limitation:** The `_conviction_penalty` lookup requires knowing a symbol's position
in the deployment queue AND its narrative_tier. Both are visible in the UI Deployment
Queue section, but are not surfaced in the reduction card itself. Operators cannot
reproduce the penalty without opening the deployment queue to cross-reference.

---

## Overweight Preference Validation

`_CATEGORY_BASE[OVERWEIGHT_REDUCTION] = 76`

An OVERWEIGHT_REDUCTION with HIGH priority and 14pp drift scores:
`76 + 12 + min(18, 14) = 102`

An OVERWEIGHT_REDUCTION with HIGH priority, 14pp drift, **and BEARISH ESS** scores:
`76 + 12 + 7 (ESS) + 8 (signal) + 14 = 117`

This correctly blends overweight-repair intent with signal quality confirmation.

---

## Weak-Signal Preference Validation

SIGNAL_DETERIORATION base (90) > OVERWEIGHT_REDUCTION base (76).

A SIGNAL_DETERIORATION with BEARISH ESS and HIGH priority scores:
`90 + 12 + 7 + 8 = 117`

This outranks an OVERWEIGHT_REDUCTION with equivalent attributes:
`76 + 12 + 7 + 8 = 103`

Weak-signal preference is structurally embedded in base scores.

---

## Conflict Penalty Validation

Conviction penalties:
- CORE_CONVICTION_LEADER: –22 (most aggressive protection)
- HIGH_CONVICTION_ANCHOR: –13
- Rank ≤ 5 (no tier): –8
- Rank > 5 (any queue member): –2
- Not in queue: 0

A VERY_BEARISH SIGNAL_DETERIORATION URGENT source in the CCL tier still scores:
`90 + 20 + 12 = 122 – 22 = 100`

It retains reduction priority over low-quality candidates but is correctly
penalized relative to non-CCL names. The system does NOT block CCL sources from
reduction entirely — it only depresses their ranking.

This is correct behavior: operator should still see the conflict and choose,
but the system doesn't silently allow a CCL name to be the top reduction candidate.
