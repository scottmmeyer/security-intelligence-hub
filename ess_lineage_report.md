# ESS / StarMine Lineage Audit Report
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date:** 2026-05-31  
**Status:** COMPLETE

---

## Summary

The ESS (Equity Summary Score) is the primary signal in SIH, carrying 55% weight in the production composite. It originates from Fidelity's StarMine-derived scoring system, passes through three distinct persistence layers (raw file → signal_snapshot → analytical_universe), and is displayed verbatim at every UI layer with no additional transformation beyond the text label itself.

---

## What ESS Means

The **Equity Summary Score (ESS)** is a StarMine model score published by Fidelity Investments. It aggregates multiple sell-side analyst research signals into a single directional conviction label using quantitative factor models.

**Scale:**
| ESS Text | ESS Numeric | Analyst Language | SIH Score |
|----------|------------|-----------------|-----------|
| VERY_BULLISH | 5.0 | STRONG_BUY | 5.0 |
| BULLISH | 4.0 | BUY | 4.0 |
| NEUTRAL | 3.0 | HOLD | 3.0 |
| BEARISH | 2.0 | SELL | 2.0 |
| VERY_BEARISH | 1.0 | STRONG_SELL | 1.0 |

**Numeric source note:** The `starmine_ess_numeric` field is `TEXT_MAPPED` — it is not a raw numeric from StarMine but is derived from the text label at intake via a fixed mapping. The `starmine_ess_numeric_estimated = True` flag marks this clearly.

---

## Complete Lineage Path

```
Fidelity EquitySummaryScores-May2026.csv   (provider-provided monthly file)
  → src/scoring/ess_normalizer.py           (validates + normalizes ESS rows)
    → src/history/base_universe_manager.py  (merges into base_universe)
      → signal_snapshot append (INTAKE-20260526-001)
        → data/current/signal_snapshot.csv
          fields: snapshot_date, provider, source_file, symbol, coverage_domain,
                  signal_coverage_status, starmine_ess_text, starmine_ess_numeric,
                  starmine_ess_numeric_estimated, starmine_ess_source_type
            → analytical_universe build (REBUILD-20260531-FIX)
              → data/current/analytical_universe.csv
                fields used: ess_score_text (= starmine_ess_text), composite_score
                  → SecurityIntelligenceOverlay.ess_score_text (via enrichment.py)
                    → API: security_overlays[].ess_score_text
                      → UI: overlay table, signal profile, consensus matrix

```

---

## Normalization Rules at Intake

`src/scoring/ess_normalizer.py` validates incoming ESS text against the allowed vocabulary:

- Valid values: `VERY_BULLISH`, `BULLISH`, `NEUTRAL`, `BEARISH`, `VERY_BEARISH`
- Coverage domain: `STARMINE_COVERED` (preferred) vs `NON_STARMINE_ANALYST` (fallback)
- When multiple rows exist for the same symbol, `load_fidelity_signals()` prefers the `STARMINE_COVERED` row with a non-empty `ess_text`

---

## Fidelity Transparency Panel Derivation

The Fidelity card displayed in the expanded signal profile and UCF dashboard adds **two derived display fields** on top of the raw ESS text:

| Display Field | Source | Transformation |
|--------------|--------|---------------|
| `fidelity_rating` | `starmine_ess_text` | `ess_text_to_rating()` maps to analyst language (STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL) |
| `fidelity_direction` | `starmine_ess_text` | `ess_text_to_direction()` maps to directional (BULLISH / NEUTRAL / BEARISH) |

Both transformations are defined in `src/portfolio/fidelity_signal.py`. Neither changes any score or ranking — they are display aliases for the operator's benefit.

---

## ESS in the Production Composite Score

```python
# src/history/analytical_universe_manager._ESS_TEXT_SCORE_MAP
VERY_BULLISH → 5.0
BULLISH      → 4.0
NEUTRAL      → 3.0
BEARISH      → 2.0
VERY_BEARISH → 1.0

# Weight in composite v1
composite = (ess_score × 0.55 + zacks_score × 0.25 + yahoo × 0.10 + danelfin × 0.10)
            / total_available_weight
```

ESS is the dominant signal at 55%. When ESS is absent (not in `_ESS_TEXT_SCORE_MAP`), the full weight is renormalized to remaining signals.

---

## Signal Direction Priority (Overlay Builder)

`src/portfolio/recommendations.build_security_overlays()` uses ESS as the **primary** signal direction determinant:

```python
# ESS BEARISH floor override: if composite ≥ 3.5 (BULLISH) but ESS is BEARISH,
# ESS wins → direction = BEARISH
# ESS NEUTRAL/absent: composite score determines direction
```

This ensures that even if the composite score is elevated by Zacks/Danelfin, a BEARISH ESS cannot result in a BULLISH direction signal.

---

## AEIS Validation

**AEIS (Advanced Energy Industries) — correct display confirmed:**

| Layer | Field | Value |
|-------|-------|-------|
| signal_snapshot.csv | `starmine_ess_text` | `BEARISH` |
| signal_snapshot.csv | `starmine_ess_numeric` | `2.0` |
| analytical_universe.csv | `ess_score_text` | `BEARISH` |
| analytical_universe.csv | `composite_score` | `3.055556` |
| analytical_universe.csv | `zacks_rating` | `5.0` (Zacks Strong Buy) |
| security_overlays (API) | `ess_score_text` | `BEARISH` |
| Fidelity card (UI) | `fidelity_rating` | `SELL` |
| Fidelity card (UI) | `fidelity_direction` | `BEARISH` |
| Signal direction | `signal_direction` | `BEARISH` (ESS override) |

**Verdict: ✅ AEIS correctly displays BEARISH.** Despite Zacks=5.0 (Strong Buy), the ESS=BEARISH floor override ensures the signal direction is BEARISH. The composite of 3.055556 reflects Zacks diluting the bearish ESS but cannot override the direction label.

---

## Freshness

| Field | Latest snapshot_date | Age (2026-05-31) | Status |
|-------|--------------------|----|--------|
| `starmine_ess_text` in `signal_snapshot.csv` | 2026-05-26 | **5 days** | ⚠️ **WARNING** |
| `ess_score_text` in `analytical_universe.csv` | Rebuilt 2026-05-31 | 0 days | **FRESH** (carries 2026-05-26 ESS data) |

**Note:** The ESS refresh date of 2026-05-26 is at the WARNING threshold (≤5 days = WARNING, per proposed thresholds). The next Fidelity ESS file (June 2026) should be ingested when available. Fidelity publishes ESS data monthly, so a 5-day delay from the latest monthly snapshot is normal. The universe rebuild on 2026-05-31 propagates the existing ESS data forward — it does not constitute a new ESS refresh.
