# Phase 23.2 — Execution Ranking Design

**Date:** 2026-06-03
**Status:** APPROVED

---

## 1. Principles

1. Intelligence scores are never modified by policy
2. Policy modifies only **queue position** and **output annotations**
3. All policy effects are reversible — revoking a policy restores original ranks
4. The original (pre-policy) rank is preserved in `original_rank` for transparency
5. Reconciliation inputs are pre-policy data — policies do not affect any reconciliation check

---

## 2. Deployment Queue Architecture

### Current Flow (Phase 23.1)
```
holdings → enrichment → alignment → CW-DAS scoring → deployment_queue.build_deployment_queue()
  → CandidateEntry list ordered by deployment_score DESC
```

### Updated Flow (Phase 23.2)
```
holdings → enrichment → alignment → CW-DAS scoring → deployment_queue.build_deployment_queue()
  → CandidateEntry list (pre-policy, intelligence scores only)
  → OperatorPolicyRegistry.load()
  → apply_policy_to_queue(queue, registry)
    ├── annotate all entries
    ├── extract DO_NOT_SELL entries → policy_suppressed_entries list
    ├── boost PREFERRED_ACCUMULATION entries to front of buy cohort
    ├── push SELL_LAST entries to tail of sell cohort
    └── renumber ranks
  → annotated CandidateEntry list (output)
```

---

## 3. Queue Partitioning

The deployment queue contains two logical cohorts:

**Buy Cohort:** Entries with positive deployment context (accumulation candidates)
**Sell/Reduction Cohort:** Entries with reduction context (trim/exit candidates, overweight contributors)

Policy affects each cohort differently.

### Current queue structure (flat, ranked by deployment_score):
```
Rank 1: VRT  (deployment_score=94.96, buy context)
Rank 2: ARW  (deployment_score=88.40, buy context)
...
Rank N: TSLA (deployment_score=X, TRIM context — overweight, weak signal)
```

### Policy modifications:

#### DO_NOT_SELL applied to TSLA (sell context):
```
Rank 1: VRT   (unchanged)
Rank 2: ARW   (unchanged)
...
[TSLA removed from execution queue]
[TSLA preserved in policy_suppressed_entries with annotation]
```

#### PREFERRED_ACCUMULATION applied to ARW:
```
Before: VRT(1), ARW(2), PSX(3)
After:  ARW(1, policy_rank_boost=True, original_rank=2), VRT(2), PSX(3)
Scores: VRT=94.96, ARW=88.40 — UNCHANGED
```

#### SELL_LAST applied to DODFX (sell context):
```
Before: ... MSFT(30, sell), DODFX(31, sell), VZ(32, sell)
After:  ... MSFT(30, sell), VZ(31, sell), DODFX(32, sell, policy_annotation="⏸ Sell Last")
```

---

## 4. Rank Adjustment Algorithm

### `apply_policy_to_queue(queue, registry)` pseudocode

```python
def apply_policy_to_queue(
    queue: list[CandidateEntry],
    registry: OperatorPolicyRegistry,
) -> tuple[list[CandidateEntry], list[CandidateEntry]]:
    """
    Returns:
      (annotated_active_queue, policy_suppressed_entries)
    """
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).isoformat()

    # Step 1: Annotate all entries with policy metadata
    for entry in queue:
        pt = registry.active_policy_type(entry.symbol)
        entry.policy_type = pt
        entry.original_rank = entry.rank
        entry.policy_rank_boost = False
        if pt == "DO_NOT_SELL":
            entry.policy_annotation = "🔒 Operator Protected"
            entry.policy_protected = True
        elif pt == "SELL_LAST":
            entry.policy_annotation = "⏸ Sell Last"
        elif pt == "CORE_ANCHOR":
            entry.policy_annotation = "⚓ Core Anchor"
        elif pt == "PREFERRED_ACCUMULATION":
            entry.policy_annotation = "⭐ Preferred Accumulation"
            entry.policy_rank_boost = True
        else:
            entry.policy_annotation = None

    # Step 2: Extract DO_NOT_SELL entries from execution (only sell-context entries)
    #   "Sell context" = entry is a trim/reduction candidate (negative deployment context)
    #   Buy-context entries with DO_NOT_SELL are retained (no conflict — operator can buy more)
    suppressed = []
    active = []
    for entry in queue:
        is_sell_context = _is_sell_context(entry)  # see below
        if entry.policy_type == "DO_NOT_SELL" and is_sell_context:
            suppressed.append(entry)
        else:
            active.append(entry)

    # Step 3: Boost PREFERRED_ACCUMULATION within buy cohort
    buy_cohort = [e for e in active if not _is_sell_context(e)]
    sell_cohort = [e for e in active if _is_sell_context(e)]

    # Sort buy cohort: preferred first (stable sort preserves relative order)
    buy_preferred = [e for e in buy_cohort if e.policy_rank_boost]
    buy_normal = [e for e in buy_cohort if not e.policy_rank_boost]
    buy_cohort_sorted = buy_preferred + buy_normal

    # Step 4: Push SELL_LAST to tail of sell cohort
    sell_normal = [e for e in sell_cohort if e.policy_type != "SELL_LAST"]
    sell_last = [e for e in sell_cohort if e.policy_type == "SELL_LAST"]
    # Within sell_last cohort, preserve intelligence-rank order
    sell_last_sorted = sorted(sell_last, key=lambda e: e.original_rank)
    sell_cohort_sorted = sell_normal + sell_last_sorted

    # Step 5: Reassemble and renumber
    final_queue = buy_cohort_sorted + sell_cohort_sorted
    for i, entry in enumerate(final_queue, start=1):
        entry.rank = i

    return final_queue, suppressed


def _is_sell_context(entry: CandidateEntry) -> bool:
    """True if this entry represents a reduction/sell recommendation context."""
    # Heuristic: trim_score > 0 OR opportunity_flag in reduction flags
    return (
        entry.trim_score > 0
        or getattr(entry, "opportunity_flag", "") in ("TRIM", "REDUCE_CANDIDATE")
    )
```

---

## 5. CORE_ANCHOR: No Rank Change

`CORE_ANCHOR` does **not** modify queue rank. It only adds an annotation flag. The trim confirmation gate is a UI-layer concern, not a queue-ordering concern.

```python
# CORE_ANCHOR: annotation only — no rank change
if entry.policy_type == "CORE_ANCHOR":
    entry.policy_annotation = "⚓ Core Anchor"
    # rank: unchanged
    # scores: unchanged
    # queue position: unchanged
```

---

## 6. Multiple PREFERRED_ACCUMULATION Symbols

When multiple symbols have `PREFERRED_ACCUMULATION`, they are sorted among themselves by their original intelligence rank (i.e., deployment_score descending — highest score still leads):

```
Before: VRT(1, score=94.96), ARW(2, score=88.40), PSX(3, score=75.12), SNX(4, score=70.0)
PREFERRED on VRT and ARW:

After: VRT(1, ⭐, original=1), ARW(2, ⭐, original=2), PSX(3), SNX(4)
# In this case no reorder needed — they were already top 2
```

If PSX had PREFERRED_ACCUMULATION:
```
Before: VRT(1), ARW(2), PSX(3), SNX(4)
After: VRT(1, ⭐, o=1), ARW(2), PSX(2→1 PREFERRED, o=3), SNX(3)
# Actually: preferred {VRT, PSX} sorted by original_rank → VRT(1, ⭐), PSX(2, ⭐), ARW(3), SNX(4)
```

---

## 7. Tax-Aware Interaction with SELL_LAST

When tax-aware ranking is active, SELL_LAST symbols are sorted among themselves using tax context (holding_days, cost_basis) before being appended to the sell cohort tail:

```
Unprotected sell candidates (ordered by tax-aware rank):
  [28] MSFT (ST gain — last to exit from tax perspective)
  [29] VZ   (LT loss — harvest candidate)

SELL_LAST candidates (ordered by tax-aware rank within cohort):
  [30] DODFX (LT gain — least favorable tax profile)
  [31] SPXL  (ST loss — more favorable, but still SELL_LAST)

Final sell queue: MSFT(28), VZ(29), DODFX(30), SPXL(31)
```

Tax rank is computed before policy, then preserved within each cohort. Policy ordering is the outer sort.

---

## 8. Output Fields in `CandidateEntry`

New fields added to the `CandidateEntry` dataclass:

```python
@dataclass
class CandidateEntry:
    # ... existing fields ...
    rank: int
    symbol: str
    deployment_score: float
    # ... other existing fields ...

    # Phase 23.2 — Policy annotation fields (never affect scoring)
    policy_type: Optional[str] = None
    policy_annotation: Optional[str] = None
    policy_protected: bool = False
    policy_rank_boost: bool = False
    original_rank: Optional[int] = None
```

---

## 9. PAR Output: Policy-Suppressed Section

`deployment_queue.json` gains a new top-level key alongside `queue`:

```json
{
  "queue": [...],
  "policy_suppressed": [
    {
      "rank": null,
      "symbol": "TSLA",
      "policy_type": "DO_NOT_SELL",
      "policy_annotation": "🔒 Operator Protected",
      "original_rank": 28,
      "deployment_score": 15.3,
      "intelligence_flag": "TRIM",
      "note": "Excluded from execution by operator policy"
    }
  ],
  "policy_active_count": 2
}
```

This preserves complete transparency: the output records not only what will execute, but what was suppressed and why.

---

## 10. Rank Stability Guarantee

The implementation provides a **stability guarantee**: reverting all policies returns the queue to its pre-policy rank order (by restoring from `original_rank`). This is enforced by:

1. Always computing intelligence scores first (pre-policy)
2. Storing `original_rank` on every entry before policy application
3. Policy application is a pure transformation on a copy — original queue object is not mutated

This means policy changes are instantly reversible by revoking the policy and regenerating the PAR.
