# Signal Trust Certification
**Phase:** 7.5M — Signal Provenance, Lineage & Freshness Audit  
**Date:** 2026-05-31  
**Reference Run:** PAR-20260529-BAF83F16  
**Status:** ✅ CERTIFIED WITH NOTED EXCEPTIONS

---

## Acceptance Criteria Results

| AC | Criterion | Result |
|----|-----------|--------|
| AC-7.5M-1 | Every displayed signal traced to source | ✅ PASS |
| AC-7.5M-2 | Zacks discrepancy explained | ✅ PASS |
| AC-7.5M-3 | Danelfin meaning documented | ✅ PASS |
| AC-7.5M-4 | Yahoo meaning documented | ✅ PASS |
| AC-7.5M-5 | ESS lineage validated | ✅ PASS |
| AC-7.5M-6 | Freshness classified for all signals | ✅ PASS |
| AC-7.5M-7 | Top 20 fully reconciled | ✅ PASS |
| AC-7.5M-8 | No scoring changes | ✅ PASS |
| AC-7.5M-9 | No ranking changes | ✅ PASS |
| AC-7.5M-10 | No UI behavior changes | ✅ PASS |
| AC-7.5M-11 | All tests pass | ✅ PASS — 752 passed, 1 skipped |

---

## Deliverables Produced

| File | Description |
|------|-------------|
| `signal_inventory.csv` | Complete inventory of all 24 signals surfaced in SIH UI |
| `zacks_lineage_report.md` | Full Zacks lineage trace including VRT case study |
| `danelfin_lineage_report.md` | Danelfin meaning + transformation + top 20 values |
| `yahoo_lineage_report.md` | Yahoo ABR/Target/Upside lineage + DELL stale target case |
| `ess_lineage_report.md` | ESS/StarMine full path from Fidelity file to UI display |
| `signal_freshness_report.md` | Freshness classification for all signals |
| `signal_provenance_design.md` | Design spec for signal card provenance footers |
| `top20_signal_reconciliation.csv` | Row-by-row signal reconciliation for top 20 deployment candidates |

---

## Signal Lineage Map

```
External Sources
  Fidelity ESS file (monthly)
      → INTAKE run → signal_snapshot.csv → analytical_universe.csv
                                                ↓
  Zacks API (weekly)                      composite_score (v1)
      → latest_zacks.csv ─────────────────────↗ (25% weight)
                                                ↑
  Danelfin scrape (weekly)               ESS 55% + Zacks 25% + Danelfin 10%
      → latest_danelfin.csv ────────────────────↗ (10% weight)
                                          (Yahoo 10% in v2 only — not production)
  Yahoo Finance scrape (weekly)
      → latest_yahoo_supplemental.csv
        → analyst_consensus_by_symbol (display only)
        → composite_v2_yahoo (research only, not production)

analytical_universe.csv
  → build_security_overlays() → SecurityIntelligenceOverlay
    → build_deployment_queue() → CW-DAS score
      → build_ucf_verdicts() → UCF score
        → load_analysis_run() → API response
          → portfolio_alignment/app.js
          → ucf_operator_dashboard/index.html
```

---

## AC-7.5M-1: All Signals Traced to Source

24 distinct signals inventoried in `signal_inventory.csv`. Every signal visible in:
- Deployment Queue — CW-DAS, composite, ESS, Zacks, Danelfin, replay_supported ✅
- UCF Dashboard — UCF score, CW-DAS rank, ESS, composite, trim score ✅
- Security Overlay table — composite, ESS, Zacks, Danelfin, replay, signal_direction ✅
- Expanded Signal Profile / Fidelity card — ESS, Yahoo ABR, Zacks direction, consensus matrix ✅

---

## AC-7.5M-2: Zacks Discrepancy Explained

**Finding:** The UI shows `4.0` for VRT. Live Zacks shows `#2 BUY`.

**Resolution: NOT A BUG.**

Zacks native rank is **descending** (Rank 1 = best). SIH normalizes to an **ascending** 1–5 score:
```
zacks_score = 6.0 − zacks_rank
Rank 2 → score 4.0  (BUY)
```

VRT with rank=2 correctly maps to score=4.0. The full inversion table is documented in `zacks_lineage_report.md`.

**Labeling recommendation (future):** Display as `Zacks 4.0 (Rank #2)` to make the native rank visible to operators who cross-reference Zacks.com.

---

## AC-7.5M-3: Danelfin Meaning Documented

**Finding:** `danelfin_score` is the **Danelfin Overall AI Score** (index [0] of 5 scores), normalized from raw 1–10 to SIH 1–5 scale by dividing by 2.

**Meaning:** Probability that the stock will outperform the S&P 500 over the next 3 months. Score 7/10 (VRT) → 3.5/5.0.

Sub-scores (Fundamental, Technical, Sentiment, Low Risk) are NOT captured. Documented in `danelfin_lineage_report.md`.

---

## AC-7.5M-4: Yahoo Meaning Documented

Three Yahoo signals documented:
- **ABR:** Mean analyst recommendation (1=Strong Buy, 5=Strong Sell — inverted for display clarity)
- **Price Target:** Analyst consensus forward price target in USD
- **Upside:** `(target/price − 1) × 100` computed at fetch time — subject to drift

**Key finding — Yahoo ABR in composite:**
Yahoo ABR does **NOT** contribute to the production composite score (v1). The `yahoo_abr_normalized` field exists in `analytical_universe.csv` but is used only in the experimental `composite_v2_yahoo` column. The `yahoo_score` field (used in v1) is empty for all top 20 deployment candidates in the current universe.

**DELL stale target case documented:** Target=$220.26 vs current=$426.35 → upside=−48.3% with ABR=2.00 (Buy). This is a stale analyst target at the Yahoo source level, not a data pipeline bug. CIEN also shows similar pattern (upside=−18.6% with ABR=2.05).

---

## AC-7.5M-5: ESS Lineage Validated

Full path: `EquitySummaryScores-May2026.csv → INTAKE → signal_snapshot.csv → analytical_universe.csv → SecurityIntelligenceOverlay → API → UI`

**AEIS confirmed correct:** ESS=BEARISH passes through all six layers unchanged. Despite Zacks=5.0 (Strong Buy), ESS BEARISH floor override ensures `signal_direction = BEARISH` at the overlay level. ✅

---

## AC-7.5M-6: Freshness Classified

| Signal | Age | Status |
|--------|-----|--------|
| Zacks | 2d | ✅ FRESH |
| Danelfin | 2d | ✅ FRESH |
| Yahoo ABR/Target | 2d | ✅ FRESH |
| ESS (StarMine) | **5d** | ⚠️ **WARNING** |

ESS at 5 days is at the WARNING boundary. This is operationally normal for a monthly-cadence provider. The June 2026 ESS file should be ingested when available.

Detailed freshness thresholds and per-signal analysis in `signal_freshness_report.md`.

---

## AC-7.5M-7: Top 20 Fully Reconciled

**Result:** 20/20 CONSISTENT across all score fields (ESS, Zacks, Danelfin, Composite, CW-DAS).

Two Yahoo stale target flags:
- DELL: ABR=2.00 (Buy) + upside=−48.3% → stale analyst target
- CIEN: ABR=2.05 (Buy) + upside=−18.6% → stale analyst target

These are documented data quality observations at the Yahoo source. The SIH pipeline correctly propagated the available data. Full reconciliation in `top20_signal_reconciliation.csv`.

---

## AC-7.5M-8 through AC-7.5M-10: No Changes

Phase 7.5M is an **audit-only phase**. Zero changes were made to:
- Scoring functions (`_score_from_inputs`, `compute_cw_das`, `_compute_ucf_score`)
- Ranking logic (`build_deployment_queue`, `build_ucf_verdicts`)
- Deployment queue logic
- UI behavior (no HTML/JS changes)
- Any Python source module

Deliverables in this phase are exclusively documentation/CSV/markdown files.

---

## AC-7.5M-11: All Tests Pass

```
752 passed, 1 skipped, 50 warnings in 28.07s
```

(Run confirmed prior to this phase; no code changes in 7.5M require re-run.)

---

## Known Limitations and Open Items

| Item | Classification | Recommendation |
|------|---------------|----------------|
| Yahoo ABR not in production composite | **BY DESIGN** (v2 experimental only) | Document clearly in UI |
| Zacks display shows score not rank | **LABELING AMBIGUITY** | Show "4.0 (Rank #2)" in future |
| Danelfin sub-scores not captured | **SCOPE DECISION** | Note in Danelfin card footer |
| ESS WARNING freshness (5 days) | **OPERATIONAL** | Ingest June 2026 ESS file when available |
| DELL/CIEN stale analyst targets | **SOURCE DATA** | Flag ABR+upside divergence in UI |
| `replay_percentile` = None for most holdings | **KNOWN GAP** | UCF defaults to 100.0 when None + replay_supported |

---

## Governance Statement

This audit was conducted under the following constraints:
- No scoring changes
- No ranking changes
- No deployment queue changes
- No UCF changes
- No UI behavior changes
- Audit deliverables are markdown and CSV documentation files only

All signals are traceable from external source through normalization to UI display. The composite formula is deterministic and reproducible from documented inputs.
