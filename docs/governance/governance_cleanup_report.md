# Governance Cleanup Report
## June 5, 2026

---

## Issues Closed

### ISSUE-04 — Dislocation Watchlist Panel (GitHub #10)

**Closed:** June 5, 2026  
**Rationale:** Fully implemented through four sub-phases.

| Phase | Description | Artifacts |
|-------|-------------|-----------|
| 04A | Methodology Design | `docs/issue_04a/` — taxonomy, scoring framework, governance |
| 04B | Backend Classifier (Class A1) | `src/portfolio/dislocation.py`, 26 tests |
| 04C | Watchlist Panel UI | `app.js v25`, CSS, `#dislocationWatchlistContainer` |
| 04D | Class Extensions (D1, B2) | `_classify_d1()`, `_classify_b2()`, 34 tests |

Additional tracking phases (12B/12C) also delivered as part of this initiative.

**Final test count at close:** 1,127 passing  
**DISLOCATION_VERSION:** 1.1  
**Governance status:** Informational only — calibration review December 2026

---

### ISSUE-05 — Deployment Queue Filter by Thesis Integrity (GitHub #11)

**Closed:** June 5, 2026  
**Rationale:** Fully implemented and certified.

**Delivered:**
- Three filter dropdowns: Thesis, Consistency, Modifier
- `_dqApplyFilters()`, `_dqRefreshTable()`, `_dqToggleWatch()`
- `thesis_integrity` + `fundamental_consistency` in `CwDasBreakdown` dataclass
- Filter validation: 26 of 32 candidates visible with Modifier=Positive
- Ranking unchanged through all filter combinations

**Version at close:** app.js v23  
**Tests at close:** 1,037 passing

---

### ISSUE-08 — Fix analyst_count Fetch Pipeline (GitHub #15)

**Closed:** June 5, 2026  
**Rationale:** Full data pipeline from yfinance → CSV → model → API → UI implemented.

**Root cause:** `fetch_yahoo_supplemental.py` never called `info.get("numberOfAnalystOpinions")`.

**Delivered:**
- `analyst_count` column added to `_OUTPUT_HEADERS`
- Fetch wired in `fetch_yahoo_supplemental()`
- `_int("analyst_count")` in `load_analyst_consensus()`
- 53 portfolio symbols re-fetched; DELL=23, NVDA=58, MSFT=55 confirmed
- ISSUE-10 ATI block shows "Coverage: N analysts" automatically

**Tests at close:** 1,037 passing

---

## Final Open Issues After Cleanup

| # | Title | Status | Target |
|---|-------|--------|--------|
| 17 | ISSUE-12D: Dislocation Outcome Review Panel | BLOCKED | October 2026 |
| 6 | EPIC: Governance and Tooling | Open (EPIC) | Ongoing |
| 5 | EPIC: Signal Intelligence Evolution | Open (EPIC) | Ongoing |
| 3 | EPIC: Portfolio Action Pipeline (PAP) | Open (EPIC) | Ongoing |
| 2 | EPIC: Capital Rotation Advisor (CRA) | Open (EPIC) | Ongoing |
| 1 | EPIC: FMP Integration | Open (EPIC) | Ongoing |

**Active implementation issues: 0** (only ISSUE-12D, which is blocked until September 2026)

---

## Milestone Created

**Dislocation Calibration Review** (GitHub Milestone #1)  
- Target: December 31, 2026  
- Purpose: Evaluate dislocation predictive value after two complete 90-day cohorts  
- Entry criteria: 50+ detections, tier ordering measurable, 2 full quarters of data  
- ISSUE-12D assigned to this milestone
