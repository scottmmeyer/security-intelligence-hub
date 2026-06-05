# Phase 23.6B.4 — Circular Conflict Remediation

**Date:** 2026-06-04  

---

## Problem

Five symbols (CVE, GTX, TSM, ASML, SBS) appeared in both the CRA capital sources (sell) and deployment targets (buy) in the same proposal, creating contradictory guidance. The worst cases had net BUY direction:

- CVE: sell $3,120 → buy $10,473 = net +$7,353 BUY
- GTX: sell $2,263 → buy $12,675 = net +$10,412 BUY

---

## Decision: Option A

Remove from capital sources when:
1. Source category is OVERWEIGHT_REDUCTION or LOW_CONVICTION_REDUCTION (exposure-only reason — no thesis break)
2. Conviction signal is BULLISH or VERY_BULLISH

Rationale: an overweight allocation node with a BULLISH security means the portfolio has too much of a good thing — you reduce the allocation node, not the security. The conviction signal wins.

Securities with signal deterioration (BEARISH ESS) that also appear in the deployment queue retain their source record — the system correctly surfaces a conflict because deterioration + buy is genuinely contradictory and deserves operator review.

---

## Implementation

**File:** `src/portfolio/cra/rotation_proposal_builder.py`

Added after deployments are computed, before proposal assembly:

```python
_OW_ONLY_CATEGORIES = frozenset({"OVERWEIGHT_REDUCTION", "LOW_CONVICTION_REDUCTION"})
_BULLISH_SIGNALS    = frozenset({"BULLISH", "VERY_BULLISH"})

for src in all_sources:
    if src.symbol in deploy_syms:
        sig = overlay[src.symbol].get("signal_direction")
        ess = overlay[src.symbol].get("ess_score_text")
        conviction_bullish = sig in _BULLISH_SIGNALS or ess in _BULLISH_SIGNALS
        if src.category in _OW_ONLY_CATEGORIES and conviction_bullish:
            # Option A: remove from sources — conviction wins
            circular_resolved.append(src.symbol)
        else:
            filtered_sources.append(src)  # keep + surface in review_flags
```

Remaining circular conflicts (e.g. AVGO TAX_AWARE_EXIT + in queue) are flagged in `review_flags` for operator visibility.

---

## Live Validation

```
OW_REDUCTION sources also in deploy targets: []  ✅ PASS
Remaining circular (any category): ['AVGO', 'UHS'] — flagged in review_flags ✅
Review flag: "Signal conflict: AVGO, UHS appear in both capital sources and deployment targets"
```

CVE, GTX, TSM, ASML, SBS: removed from sources — no longer contradictory ✅
