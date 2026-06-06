# ISSUE-04B — API Payload Validation Report

**Date:** June 5, 2026  
**Run tested:** PAR-20260605-BC438F9E

---

## Payload Structure Validation

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `dislocation_by_symbol` key present | True | True | ✅ |
| Total symbols classified | 78 | 78 | ✅ |
| All entries have `tier` field | True | True | ✅ |
| All entries have `evidence` field (list) | True | True | ✅ |
| All entries have `version` field | "1.0" | "1.0" | ✅ |
| All entries have `dislocation_class` field | True | True | ✅ |

---

## Tier Distribution (PAR-20260605-BC438F9E)

| Tier | Count | Pct |
|------|-------|-----|
| NONE | 56 | 71.8% |
| WATCH | 17 | 21.8% |
| MODERATE | 5 | 6.4% |
| HIGH_CONVICTION | 0 | 0% |
| **Total** | **78** | **100%** |

Note: HIGH_CONVICTION requires beat_rate ≥ 87.5% + ESS BEARISH/VERY_BEARISH +
Danelfin < 2.0. In this portfolio, the bearish ESS names typically do not have
the required beat rate, and the high-beat-rate names currently have neutral-to-
bullish ESS. This is the expected behavior: no true dislocation in a portfolio
that is currently performing well on signal alignment.

---

## Governance Validation Per Named Symbol

### PSX — Expected NONE (DETERIORATING thesis)

```json
{
  "tier": "NONE",
  "dislocation_class": "NONE",
  "evidence": []
}
```
✅ CORRECT — PSX has DETERIORATING thesis (revenue −27.6%, per ISSUE-07 analysis).
A DETERIORATING thesis is explicitly excluded from dislocation classification.
This is the most important governance test: "signal weakness + deteriorating
fundamentals" must never be labelled as dislocation.

### NVDA — Expected NONE (signals agree with fundamentals)

```json
{ "tier": "NONE", "dislocation_class": "NONE", "evidence": [] }
```
✅ CORRECT — NVDA has strong ESS and high Danelfin. No signal divergence.

### VRT — Expected NONE (signals agree with fundamentals)

```json
{ "tier": "NONE", "dislocation_class": "NONE", "evidence": [] }
```
✅ CORRECT — VRT is VERY_BULLISH on ESS. No divergence.

### DELL — WATCH tier

```json
{
  "tier": "WATCH",
  "dislocation_class": "A1_FUNDAMENTAL_BEAT_DIVERGENCE",
  "evidence": [
    "Beat rate 86% — fundamentals consistently exceeded expectations",
    "Thesis: INTACT",
    "Danelfin: 2.5 — AI model diverging from fundamentals",
    "Revenue growth: +18.8% (confirming)"
  ]
}
```
✅ Beat rate 86% (just below 87.5% HIGH CONVICTION threshold).
Danelfin 2.5 (moderate divergence). ESS is not bearish (not in evidence),
so HIGH CONVICTION cannot fire. WATCH is the correct tier.

### LRCX — WATCH tier

```json
{
  "tier": "WATCH",
  "dislocation_class": "A1_FUNDAMENTAL_BEAT_DIVERGENCE",
  "evidence": [
    "Beat rate 100% — fundamentals consistently exceeded expectations",
    "Thesis: INTACT",
    "Danelfin: 3.0 — AI model diverging from fundamentals",
    "Revenue growth: +23.7% (confirming)"
  ]
}
```
✅ 100% beat rate + INTACT thesis + Danelfin exactly at 3.0 (boundary for MODERATE).
MODERATE requires Danelfin < 3.0 strictly; LRCX at 3.0 correctly falls to WATCH.

### AEIS — WATCH tier

```json
{
  "tier": "WATCH",
  "dislocation_class": "A1_FUNDAMENTAL_BEAT_DIVERGENCE",
  "evidence": [
    "Beat rate 100% — fundamentals consistently exceeded expectations",
    "Thesis: INTACT",
    "ESS: NEUTRAL — signal neutral/absent",
    "Danelfin: 4.0 — AI model diverging from fundamentals"
  ]
}
```
✅ 100% beat rate, INTACT thesis, but Danelfin 4.0 (above MODERATE threshold).
ESS NEUTRAL provides mild divergence. WATCH is correct.

---

## Evidence Quality Checks

All non-NONE entries include:
- Beat rate with percentage and interpretation ✅
- Thesis statement ("Thesis: INTACT") ✅
- ESS or Danelfin divergence explanation ✅
- Revenue growth confirming signal when positive ✅

Maximum evidence items per entry: 4 ✅  
Minimum evidence items for non-NONE: 2 ✅

---

## No Scoring Contamination Verified

After payload inspection, confirmed that for all 78 classified symbols:
- `deployment_score` in `deployment_queue.queue` entries: unchanged
- `composite_score` in `security_overlays`: unchanged
- `rank` in deployment queue: unchanged
- `fundamental_modifier` in `score_breakdown`: unchanged
- CRA source/destination classification: unchanged
