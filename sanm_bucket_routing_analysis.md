# SANM Bucket Routing Analysis
**Phase 7.6D.1 — SANM Replay Forensics**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q3: Which Replay Bucket Governs SANM? Why? Would an Alternative Assignment Have Attached SANM to a 365-Day Replay?

---

## Current Governing Bucket

**Bucket:** `US.SMALL` (ALL-industry, CURRENT_RECOMMENDATION, 6-day)

**Replay ID:** `REPLAY-2026-05-20-TO-2026-05-26-US-SMALL-ALL-TOP20-WP05D-20260526-ALL2-US-SMALL-ALL`

**Coverage:** 2026-05-20 to 2026-05-26 (6 days)

SANM's current replay assignment comes from the ALL-industry cross-sector SMALL basket, not from its industry-specific basket. The ALL-basket takes priority in the routing logic (`_load_replay_evidence()` in `src/portfolio/recommendations.py`): when `filter_industry == "ALL"`, the symbol is immediately assigned to `symbol_tier` and any subsequent industry-specific appearances are suppressed.

---

## Why the ALL Basket — Not the TECHNOLOGY Basket?

SANM's classification in `data/current/analytical_universe.csv`:

| Field | Value |
|---|---|
| geography | US |
| market_cap_bucket | SMALL |
| industry | TECHNOLOGY |
| ess_score | 4.277778 (BULLISH) |

SANM is classified as TECHNOLOGY, SMALL, US. There IS a 365-day US-SMALL-TECHNOLOGY basket registered in `replay_matrix.csv`. However, SANM does **not appear in it**.

The SMALL-TECHNOLOGY 365-day basket (snapshot_date=2025-05-14) selected:
```
ARW, AVT, CRUS, DBX, DT, LFUS, VICR, YOU, ALGM, BB, BDC, CGNX, DIOD, GIB, HIMX, LPL, NICE, PAYC, PLXS, QBTS
```

SANM is not in this list. At the 2025-05-14 composite score snapshot, SANM's score was not high enough to place in the top 20 of the SMALL-TECHNOLOGY filter. The TECHNOLOGY basket is a narrower pool (US SMALL-cap TECHNOLOGY only) where SANM competed against 20 other technology-classified holdings.

However, SANM DID rank in the top 20 of the SMALL-ALL basket (all industries combined), appearing at position 10 of 20. This cross-industry basket gave SANM a slot it could not earn within the technology-only filter.

**Why SANM is in the ALL basket but not the TECHNOLOGY basket:**

The composite score filter in the 365-day SMALL-TECHNOLOGY replay was evaluated at 2025-05-14. At that date, SANM's composite score ranked it ~21st or lower among US SMALL-cap TECHNOLOGY holdings. Among ALL industries in the SMALL bucket, SANM's score was high enough to rank 10th overall.

---

## Routing Mechanism: ALL vs. Industry-Specific Priority

The `_load_replay_evidence()` function applies first-seen-wins routing with ALL-basket priority:

```python
if ind == "ALL":
    # Cross-sector ALL replay — highest priority.
    if sym not in symbol_tier:
        symbol_tier[sym] = f"{geo}.{cap}"
        symbol_replay[sym] = replay_id
else:
    # Industry-specific replay — lower priority
    if sym not in symbol_tier and sym not in industry_replay_evidence:
        industry_replay_evidence[sym] = {...}
```

Since the only ALL-industry basket in `replay_inputs.csv` is the 6-day CURRENT_RECOMMENDATION replay, SANM is assigned to it before any industry-specific evidence is evaluated. Even if SANM had been in the SMALL-TECHNOLOGY basket, the ALL-basket would take precedence.

---

## Would an Alternative Assignment Have Attached SANM to a 365-Day Replay?

**Scenario A: If the 365-day SMALL-ALL replay were registered in `replay_inputs.csv`**

The 365-day SMALL-ALL replay exists on disk (`snapshot_date=2025-05-14`, `HISTORICAL_VALIDATION`, SANM at position 10). If it were registered, `_load_replay_evidence()` would encounter it and assign:

```
symbol_tier["SANM"] = "US.SMALL"
replay_id = "REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-ALL-..."
```

Result: `replay_supported=True`, coverage = 365 days (STRONG). No scoring change under the current binary model — SANM still earns 20 pts. Under Model B depth-aware scoring, SANM would earn 20 pts (STRONG tier) rather than 10 pts (THIN tier). Rank would remain 11.

**This is the correct routing. The 365-day evidence exists and SANM legitimately earned a top-10 position in the basket.**

**Scenario B: If SANM were classified as INDUSTRIALS rather than TECHNOLOGY**

Sanmina (SANM) is an electronics manufacturing services (EMS) company. Some classification systems categorize EMS as INDUSTRIALS rather than TECHNOLOGY. If SANM were reclassified as INDUSTRIALS, it would be evaluated for the SMALL-INDUSTRIALS 365-day basket. The SMALL-INDUSTRIALS basket (snapshot_date=2025-05-14) exists in the matrix. Whether SANM would have made the top 20 SMALL-INDUSTRIALS depends on its score rank relative to other SMALL-cap INDUSTRIALS holdings — this is a hypothetical that cannot be determined without re-running the selection logic with the reclassification applied. However, given SANM ranked 10th in the SMALL-ALL cross-industry basket, it is plausible it would also rank in the SMALL-INDUSTRIALS top 20.

**Note:** This scenario is hypothetical and academic. The correct fix is Scenario A, not reclassification.

**Scenario C: Current routing (6-day ALL basket only)**

The 6-day CURRENT_RECOMMENDATION ALL basket is what currently governs SANM. This basket was generated from live signal outputs on 2026-05-20 and represents a 6-day recent window only. SANM earns `replay_supported=True` from this basket, receiving full binary 20-pt replay bonus despite the depth being THIN.

---

## Routing Table Summary

| Scenario | Replay Source | Coverage | Mode | replay_supported | CW-DAS pts | SANM rank (Model A) | SANM rank (Model B) |
|---|---|---|---|---|---|---|---|
| Current (actual) | 6-day SMALL-ALL | 6 days | CURRENT_REC | True | 20 | 11 | 33 |
| Correct routing | 365-day SMALL-ALL | 365 days | HISTORICAL_VAL | True | 20 | 11 | **11** |
| No replay (hypothetical) | None | 0 | N/A | False | 0 | ~40 | ~40 |

The routing fix (Scenario A) changes the depth-aware model rank from 33 back to 11 — identical to the current binary result. Only the THIN → STRONG classification changes; the binary scoring remains unchanged.

---

## Structural Finding: ALL-Industry 365-Day Replays Are Systemically Excluded

The replay matrix and replay_inputs.csv contain **zero** 365-day ALL-industry replays for any cap bucket. All 10 ALL-industry entries in `replay_inputs.csv` are CURRENT_RECOMMENDATION (6-day) replays.

On disk, at `snapshot_date=2025-05-14`, multiple 365-day ALL-industry replays exist (US-SMALL-ALL, US-LARGE-ALL, US-MID-ALL, US-MEGA-ALL, various INTERNATIONAL equivalents — 20+ total). None were registered in the matrix.

This is not a SANM-specific routing error. It is a systemic omission: the 365-day ALL-industry historical validation replays were generated after the matrix was finalized and were never registered. The routing system therefore cannot leverage 365-day ALL-basket evidence for any symbol whose primary basket appearance is in an ALL replay. SANM is the portfolio holding most visibly affected because it appears in the ALL basket but not in its industry-specific (TECHNOLOGY) basket.
