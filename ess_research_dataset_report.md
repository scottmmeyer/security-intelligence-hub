# ESS Historical Research Dataset — Final Report
**Phase 7.6F-R — Deliverable Q7 (Final)**
**Generated:** 2026-06-01
**Run:** PAR-20260601-9CFD7C63

---

## 1. Phase Summary

Phase 7.6F-R transformed 50 preserved ESS archive files (from Phase 7.6E) into a governed historical research dataset consisting of 3 CSV outputs and 4 analytical reports. The following deliverables are complete:

| # | Deliverable | Status | Records / Scope |
|---|-------------|--------|-----------------|
| Q1 | `ess_history_master.csv` | ✅ WRITTEN | 54,566 records, 2,918 symbols, 36 dates |
| Q2 | `ess_symbol_history_inventory.csv` | ✅ WRITTEN | 2,918 symbol rows |
| Q3 | `ess_coverage_tiers.csv` | ✅ WRITTEN | 2,918 symbols in 4 tiers |
| Q4 | `ess_stability_preview.md` | ✅ WRITTEN | Upgrade/downgrade/stable analysis |
| Q5 | `ess_research_readiness.md` | ✅ WRITTEN | Study-type eligibility by threshold |
| Q6 | `authentic_replay_readiness.md` | ✅ WRITTEN | Replay date coverage and classification |
| Q7 | `ess_research_dataset_report.md` | ✅ THIS FILE | Final recommendation |

---

## 2. Dataset Key Facts

| Metric | Value |
|--------|-------|
| Total records | 54,566 |
| Unique symbols | 2,918 |
| Observation date range | 2025-08-18 → 2026-06-01 |
| Span | 287 days |
| Unique observation dates | 36 |
| TIER_A symbols (10+ obs) | 2,504 (85.8%) |
| TIER_B symbols (5–9 obs) | 43 (1.5%) |
| TIER_C symbols (2–4 obs) | 322 (11.0%) |
| TIER_D symbols (1 obs) | 49 (1.7%) |
| Multi-obs symbols (2+) | 2,869 (98.3%) |
| Average ESS delta (first→last) | −0.519 (slight net downgrade over period) |
| Most stable symbol | APO — 0.0 std dev, 26 obs, 287 days |
| Largest upgrade | HELE, NIQ, OSCR — +4 (VERY_BEARISH → VERY_BULLISH) |
| Largest downgrade | AB, APTV, BIDU, CCJ — −4 (VERY_BULLISH → VERY_BEARISH) |
| Files without ESS column (excluded) | 2 (May 1 2026, May 8 2026 large file) |

---

## 3. Schema Resolution Summary

Two ESS data formats were found across the archive. Both were successfully normalized:

| Period | Column Name | Format | Normalization |
|--------|-------------|--------|---------------|
| Aug 2025 – Mar 2026 (portfolio) | `ESS from LSEG StarMine` | Numeric 1-10 | Bucketed to VERY_BULLISH/BULLISH/NEUTRAL/BEARISH/VERY_BEARISH, then 1-5 |
| Mar 2026 – Jun 2026 (full universe) | `Equity Summary Score (ESS) from LSEG StarMine` | Text category | Mapped directly to 1-5 |

Outputs use:
- `ess_raw` — exact string from source file
- `ess_category` — normalized enum (VERY_BULLISH ... VERY_BEARISH)
- `ess_5pt` — integer 1–5 for cross-period comparison

---

## 4. Final Recommendation

### **A. READY_FOR_ESS_EFFECTIVENESS_STUDY**

The ESS historical research dataset is ready for a formal signal effectiveness study under the following conditions:

**Condition 1 — Scope-Aware Analysis Required**
All analyses must account for the portfolio-vs-full-universe scope boundary at 2026-03-10. Pre-boundary observations carry portfolio selection bias; post-boundary observations are representationally complete.

**Condition 2 — Return Data Not Yet In Archive**
The `ess_history_master.csv` contains ESS signal data only. A price return dataset must be joined for effectiveness analysis. This is readily available from the existing data pipeline but is a prerequisite for executing the effectiveness study.

**Condition 3 — 12-Month Full-Universe Study Requires Until Mar 2027**
The 12-month effectiveness study for the full-universe cohort (Mar 10, 2026 baseline) requires forward return data through Mar 10, 2027. The 12-month portfolio-level study (Aug 2025 baseline) becomes available in August 2026.

**Immediately actionable studies (no additional data needed beyond price data):**
1. **ESS Transition Matrix** — probability that ESS changes from X to Y over 7/30/90 days (2,869 symbols)
2. **Persistence Study** — average ESS category half-life (2,542 symbols, 5+ obs, 30+ days)
3. **30-day Effectiveness Pilot** — ESS vs 30-day forward returns, full-universe baseline 2026-03-10 (2,539 symbols)
4. **90-day Effectiveness Study** — available ~Jun 8, 2026 (7 days from reference date)

---

## 5. ESS Archive and Dataset Provenance Chain

```
Source Files (PM repo, live):
  processed_inputs/*.csv   (2026-03-10 → 2026-06-01)
  archive/<timestamp>/*.csv (2025-08-18 → 2026-03-10)

↓ Phase 7.6E: ESS Archive Preservation
data/history/ess_archive/
  pm_archive/              (20 files, timestamped)
  pm_processed_inputs/     (30 files)

↓ Phase 7.6F-R: Dataset Construction
ess_archive_inventory.csv  → 50-row canonical inventory
_build_ess_research.py     → construction script

↓ Outputs:
ess_history_master.csv             (54,566 records, research dataset)
ess_symbol_history_inventory.csv   (2,918 symbol stats)
ess_coverage_tiers.csv             (2,918 tier classifications)
ess_stability_preview.md           (movement analysis)
ess_research_readiness.md          (study eligibility)
authentic_replay_readiness.md      (replay date coverage)
ess_research_dataset_report.md     (this document)
```

---

## 6. Next-Phase Recommendations

| Priority | Action | Phase |
|----------|--------|-------|
| HIGH | Join price return data to `ess_history_master.csv` for effectiveness study | 7.6G |
| HIGH | Rebuild replay matrix classification using authentic ESS dates | 7.6D.3 |
| MEDIUM | Run transition matrix analysis on multi-obs subset | 7.6G |
| MEDIUM | Begin daily full-universe ESS capture in SIH to extend baseline | Operational |
| LOW | Implement automated archive append process for ongoing ESS preservation | Operational |

---

## 7. Governance

- `ess_history_master.csv` is a **derived artifact** — treat as append-only, not editable
- Source archive files in `data/history/ess_archive/` remain read-only per Phase 7.6E governance
- `_build_ess_research.py` is a reproducible construction script — delete after Phase 7.6F-R is closed if cleanup is desired, or retain as rebuild capability
- Dataset version: `v1.0.0`, constructed from archive snapshot as of 2026-06-01
