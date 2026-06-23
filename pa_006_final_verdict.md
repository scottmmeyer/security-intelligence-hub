# PA-006 Final Verdict — Allocation Drift Trend Visibility

**Date:** 2026-06-15  
**Review Status:** COMPLETE  
**Recommendation:** IMPLEMENT — High value, low risk, fully evidenced

---

## Executive Summary

PA-006 proposes adding historical allocation drift visibility to the existing PIS dashboard. Investigation confirms that all required data already exists on disk across 250 PAR runs (20 dates, May 21 – Jun 15). No new data collection, no model changes, no governance changes required.

The system currently shows only current-state CPV compliance. Two active violations (CPV-01 WARN, CPV-06 WARN) are visible but their trajectory is not. This gap is real: CPV-06 has improved −8.25pp since May 21 (FAIL → WARN), which is meaningful information the operator cannot currently see.

---

## Required Final Answers

### Q1: Can drift be reconstructed from existing data?

**Yes, completely.** All 250 PAR runs contain `concentration.json` (pre-computed concentration metrics) and `holdings.csv` (per-symbol classification data). CPV values can be computed deterministically from holdings.csv for any run. No new ingestion required.

### Q2: What dimensions should be tracked?

All 8 CPV rule dimensions (policy-bound) + top1/5/10 concentration + US/international split. Prioritized:

| Priority | Dimension | Reason |
|----------|-----------|--------|
| 1 | CPV-01 Micro Cap | Active WARN, 3.89pp from FAIL threshold |
| 2 | CPV-06 Single Asset Class | Active WARN, improving trend |
| 3 | Top 5% / Top 10% | Concentration risk monitor |
| 4 | CPV-05 International | Declining trend (−3.3pp since May 21) |
| 5 | CPV-04 Cash | Floor monitor — cash deployment visibility |

### Q3: Which dimensions provide highest operator value?

**CPV-01 and CPV-06 trend** — because they currently have violations and the operator needs to know if actions are working. **Top 5% trend** — because concentration increased +4.82pp since May 21, which is a meaningful risk signal. **International %** — declined −3.3pp since May, approaching the 10% floor (currently 17.52% but direction is concerning).

### Q4: Should drift be snapshot-based or recomputed?

**Recomputed on demand from existing PAR artifacts.** Storing a separate drift CSV would duplicate data. The compute time for one date is ~50ms (CSV parse + arithmetic). For 20 dates at API load time: ~1 second. Acceptable for a dashboard.

**No new persistent storage needed.**

### Q5: What dashboard design is recommended?

Four views in a new "Drift Trends" section of the existing PIS dashboard:
1. **CPV Rule Trend Table** — all 8 rules with current, prior, 7d/30d delta, trend direction
2. **Sparkline Timeline** — for CPV-01 and CPV-06 showing movement over available history
3. **Top Drift Contributors** — top 10 symbols by |delta_pp| between last two canonical dates
4. **Drift Summary Banner** — single-line summary of active violations + trend

### Q6: What implementation approach is recommended?

**Two-phase approach:**

**Phase 1 (MVP — ~4 hours):**
- New `GET /api/drift/summary` endpoint reading from the 4 existing compliance.json files
- New `GET /api/drift/timeline` endpoint
- CPV Trend Table (View 1) + Drift Summary Banner (View 4) in `app.js`
- No holdings.csv parsing needed — uses pre-computed compliance values
- Full regression test coverage before merge

**Phase 2 (Full — ~12 hours):**
- `src/portfolio/drift_analyzer.py` parsing holdings.csv across all 250 PAR runs
- Per-symbol contributor table
- Timeline sparklines for all CPV rules
- 8 regression tests as specified in dashboard design

### Q7: Estimated implementation effort?

| Phase | Scope | Effort |
|-------|-------|--------|
| Phase 1 (MVP) | 2 endpoints + CPV table + banner | 4 hours |
| Phase 2 (Full) | drift_analyzer.py + contributors + sparklines + 8 tests | 12-16 hours |
| Total | Full implementation | ~20 hours |

### Q8: Is PA-006 justified as the next workstream?

**Yes.** Evidence-based justification:
1. **Active governance violations exist** (CPV-01 WARN, CPV-06 WARN) — operators need trend visibility to act intelligently
2. **Data is already available** — zero new collection risk, zero schema changes
3. **The system is already showing CPV status** — drift trend is a natural extension that doubles the information value of the existing CPV panel
4. **Concrete signals already visible** — CPV-06 improved −8.25pp (the operator doesn't know this), Top 5% drifted +4.82pp (the operator doesn't know this), International drifted −3.3pp toward the floor (the operator doesn't know this)
5. **Visibility only** — no risk of breaking existing functionality

---

## Historical Drift Facts Summary

| Metric | May 21 | Jun 15 | Change | Interpretation |
|--------|--------|--------|--------|---------------|
| CPV-01 Micro | 9.52% FAIL | 8.89% WARN | −0.63pp | Improved — deployment into non-micro positions |
| CPV-06 Equities | 94.97% FAIL | 86.72% WARN | −8.25pp | Significant improvement — asset diversification |
| Top 5% | 25.06% | 29.88% | +4.82pp | More concentrated — conviction positions growing |
| Top 10% | 42.22% | 45.46% | +3.24pp | More concentrated |
| International | 20.18% | 16.88% | −3.30pp | Declining — watch for floor approach |
| Mega Cap | 10.05% | 8.83% | −1.22pp | Slight decline |
| US | 72.97% | 69.21% | −3.76pp | Declined — partially explains intl also declining (cash drag) |
| HHI | 0.0272 | 0.0331 | +0.0059 | Higher concentration, still DIVERSIFIED tier |

---

## Governance Log

| Date | Action | Outcome |
|------|--------|--------|
| 2026-06-15 | PA-006 investigation | 250 PAR runs verified; all drift dimensions reconstructible |
| 2026-06-15 | Historical drift computed | 20 dates, CPV trend documented |
| 2026-06-15 | Design and algorithm defined | Ready for Phase 1 implementation |

---

## Next Actions

| Priority | Action | Phase |
|----------|--------|-------|
| HIGH | Implement `GET /api/drift/summary` and `GET /api/drift/timeline` | Phase 1 |
| HIGH | Add CPV Trend Table to PIS dashboard `app.js` | Phase 1 |
| HIGH | Write regression tests for CPV status recomputation | Phase 1 |
| MEDIUM | Implement `src/portfolio/drift_analyzer.py` with full holdings.csv parsing | Phase 2 |
| MEDIUM | Add per-symbol contributor table to dashboard | Phase 2 |
| LOW | Add sparkline timeline charts | Phase 2 |
