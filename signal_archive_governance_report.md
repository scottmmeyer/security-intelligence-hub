# Signal Archive Governance Report
**Phase 7.7B — Final Deliverable**
**Generated:** 2026-06-01
**Next Review Date:** 2026-07-15 (Phase 8.1 readiness check)

---

## 1. Verdict

**A. ARCHIVE_GOVERNANCE_ESTABLISHED**

As of 2026-06-01, the Security Intelligence Hub has a governed process to build Zacks and Danelfin signal history archives. All Phase 7.7B deliverables are complete. Systematic archive capture begins today.

---

## 2. Executive Summary

Phase 7.7A returned verdict **E. INSUFFICIENT_COMPARATIVE_EVIDENCE** because:
- ESS: 10.5 months of archive, 32,805 usable 30-day return pairs
- Zacks: 15 days of archive, **0 usable 30-day return pairs**
- Danelfin: 15 days of archive, **0 usable 30-day return pairs**

The question "Is ESS genuinely stronger than Zacks and Danelfin?" could not be answered.

Phase 7.7B establishes the governance infrastructure to answer that question in Phase 8.3 (target: 2026-12-01). It defines:
1. What archives exist today (baseline inventory)
2. What schemas are required (canonical archive format)
3. How to build normalized history tables (master CSVs)
4. How often to capture (cadence plan)
5. What quality gates protect the archive (fail-closed gates)
6. How operators run captures (runbook)
7. When studies become credible (readiness roadmap)

**No composite weights change. No UCF changes. No scoring changes. No deployment changes.**

---

## 3. Current State (as of 2026-06-01)

### 3.1 Zacks Archive

| Metric | Value |
|--------|-------|
| Files | 5 dated (+ 1 alias) |
| Earliest date | 2026-05-14 |
| Latest date | 2026-05-29 |
| Archive span | 15 days |
| Full-universe captures | 1 (2026-05-26, 2,568 rows) |
| Total observations | 3,373 |
| Unique symbols | 2,601 |
| Coverage rate | 95.7% (105 blank ranks) |
| Data quality issues | Blank rank (4.1%), scaffold columns always empty |
| Normalized master | `data/history/signals/zacks_history_master.csv` (3,373 rows, 3,228 COVERED) |

### 3.2 Danelfin Archive

| Metric | Value |
|--------|-------|
| Files | 5 dated (+ 1 alias) |
| Earliest date | 2026-05-14 |
| Latest date | 2026-05-29 |
| Archive span | 15 days |
| Full-universe captures | 0 (max was 782 on 2026-05-20) |
| Total observations | 2,266 |
| Unique symbols | 954 |
| Coverage rate | 99.6% (8 blank or out-of-range scores) |
| Data quality issues | 2 out-of-range scores (0.5, below 1.0 floor) in 2026-05-21 partial |
| Normalized master | `data/history/signals/danelfin_history_master.csv` (2,266 rows, 2,256 COVERED) |

### 3.3 Composite State Before Governance

| Question | Status |
|----------|--------|
| Can Zacks 30d effectiveness be measured? | NO — price data gap |
| Can Danelfin 30d effectiveness be measured? | NO — price data gap |
| Is ESS confirmed dominant? | PARTIALLY — Phase 7.6G: median/win rate/vol confirmed, avg inverted |
| Can Phase 7.7A comparison be completed? | NO — archive asymmetry too large |
| Are composite weights evidence-based? | ESS 55% is defensible but unproven vs. alternatives |

---

## 4. Schema

Two canonical schemas govern all archive activity. Full specification in [signal_archive_schema.md](signal_archive_schema.md).

**Zacks archive source schema:** `capture_date, symbol, zacks_rank, zacks_score, zacks_label, source_file, sourced_date, coverage_status`

**Danelfin archive source schema:** `capture_date, symbol, danelfin_raw, danelfin_score, danelfin_label, source_file, sourced_date, coverage_status`

**Normalized history master schema (both):** `capture_date, symbol, normalized_5pt_score, raw_value, source_file, provider, coverage_status`

**Normalization rules:**
- Zacks: `normalized_5pt = 6 - zacks_rank` (rank 1=Strong Buy → 5pt=5)
- Danelfin: `normalized_5pt = round(danelfin_score)` clamped [1,5] (half-point rounding: 1.5→2, 2.5→3, etc.)

---

## 5. Process

The full operator workflow is defined in [signal_capture_operator_runbook.md](signal_capture_operator_runbook.md).

**8-step process summary:**

| Step | Action |
|------|--------|
| 1 | Download Zacks export (Zacks Premium, full US equity universe) |
| 2 | Download Danelfin export (Danelfin platform, full coverage universe) |
| 3 | Place files in `data/signals/zacks/YYYY-MM-DD_zacks.csv` and `data/signals/danelfin/YYYY-MM-DD_danelfin.csv` |
| 4 | Run quality gate validation script |
| 5 | Normalize and append to history masters |
| 6 | Generate capture report |
| 7 | Update `latest_*.csv` aliases |
| 8 | Commit archive artifacts to git |

**Session time estimate:** 15–20 minutes per twice-weekly session.

---

## 6. Capture Cadence

Full specification in [signal_capture_cadence_plan.md](signal_capture_cadence_plan.md).

| Parameter | Value |
|-----------|-------|
| Minimum cadence | Weekly |
| Recommended cadence | **Twice-weekly** |
| Capture days | Tuesday + Friday |
| Maximum gap | ≤ 14 calendar days |
| Holiday handling | Capture next trading day; do not skip |

**Projected archive growth (twice-weekly):**

| Date | Zacks Captures | Zacks Observations | Danelfin Observations |
|------|---------------|--------------------|-----------------------|
| 2026-07-01 | ~9 | ~25,000 | ~7,600 |
| 2026-09-01 | ~26 | ~71,000 | ~21,600 |
| 2026-12-01 | ~52 | ~137,000 | ~41,600 |
| 2027-06-01 | ~104 | ~270,000 | ~82,000 |

---

## 7. Quality Gates

20 quality gates are defined (10 per provider) across 6 categories. Full specification in [signal_archive_quality_gates.md](signal_archive_quality_gates.md).

**Gate categories:**

| Category | Description | Gates |
|----------|-------------|-------|
| STRUCTURAL | File existence, required columns | Z-01, Z-02, D-01, D-02 |
| COVERAGE | Row count thresholds | Z-03, D-03 |
| DELTA | Symbol count vs. prior capture | Z-04, D-04 |
| FRESHNESS | Date validation, no future-dating | Z-05, Z-06, D-05, D-06 |
| CONTENT | Range checks, parse rates, format | Z-07, Z-10, D-07, D-10 |
| INTEGRITY | Checksum, duplicate detection | Z-08, Z-09, D-08, D-09 |

**Gate behavior:**
- BLOCK: append is stopped; requires operator resolution
- WARN: anomaly logged; operator decides to proceed or stop
- ROLLBACK: append reversal if post-append integrity check fails

**Row count thresholds:**
- Zacks minimum: 500 rows (threshold for meaningful full-universe capture)
- Danelfin minimum: 400 rows

---

## 8. Phase 8.x Readiness Roadmap

Full specification in [comparative_signal_readiness_roadmap.md](comparative_signal_readiness_roadmap.md).

| Milestone | Phase | Target | Purpose | Weight Change Eligible? |
|-----------|-------|--------|---------|------------------------|
| 30-Day Pilot | 8.1 | 2026-07-15 | First return pairs | NO |
| 90-Day Pilot | 8.2 | 2026-09-01 | Multi-horizon comparison | NO |
| 6-Month Comparative | **8.3** | **2026-12-01** | **Primary Phase 7.7A re-run** | **YES** |
| 12-Month Full-Cycle | 8.4 | 2027-06-01 | Multi-regime validation | YES |

**Current readiness (2026-06-01): NOT READY for any Phase 8.x comparative study.** Archive capture begins today.

**Blocking dependency:** Price history data must be extended past 2026-05-26. Without this, no forward-return study is possible regardless of signal archive depth. This is a separate action item outside Phase 7.7B scope.

---

## 9. Deliverable Index

All Phase 7.7B deliverables:

| # | Deliverable | Status | Location |
|---|-------------|--------|----------|
| Q1 | Archive Inventory | ✅ | [zacks_danelfin_archive_inventory.md](zacks_danelfin_archive_inventory.md) |
| Q2 | Canonical Schema | ✅ | [signal_archive_schema.md](signal_archive_schema.md) |
| Q3 | Normalized History Masters | ✅ | `data/history/signals/zacks_history_master.csv` (3,373 rows) |
| Q3 | Normalized History Masters | ✅ | `data/history/signals/danelfin_history_master.csv` (2,266 rows) |
| Q4 | Capture Cadence Plan | ✅ | [signal_capture_cadence_plan.md](signal_capture_cadence_plan.md) |
| Q5 | Quality Gates | ✅ | [signal_archive_quality_gates.md](signal_archive_quality_gates.md) |
| Q6 | Operator Runbook | ✅ | [signal_capture_operator_runbook.md](signal_capture_operator_runbook.md) |
| Q7 | Readiness Roadmap | ✅ | [comparative_signal_readiness_roadmap.md](comparative_signal_readiness_roadmap.md) |
| Final | Governance Report (this file) | ✅ | `signal_archive_governance_report.md` |

**Temp scripts to delete after review:**
- `_77b_inventory.py`
- `_77b_build_masters.py`

---

## 10. Open Items and Known Limitations

| Item | Status | Priority |
|------|--------|----------|
| Price history extension past 2026-05-26 | **NOT STARTED** | CRITICAL — blocks all Phase 8.x studies |
| Quality gate scripts (code implementation) | **NOT STARTED** | HIGH — runbook references scripts that don't exist yet |
| Capture automation / scheduled job | NOT STARTED | MEDIUM — currently manual |
| Danelfin full-universe baseline unclear | KNOWN ISSUE | MEDIUM — 782 vs. 725 row discrepancy unresolved |
| Zacks scaffold columns (abr, price_target, eps_growth) always empty | KNOWN ISSUE | LOW — may populate in future exports |

---

## 11. Review Schedule

| Review | Date | Trigger |
|--------|------|---------|
| Phase 8.1 readiness check | 2026-07-15 | 45 days after governance start |
| Phase 8.2 readiness check | 2026-09-01 | 90-day pilot target |
| Cadence threshold review | 2026-09-01 | After first 90 days of capture |
| Phase 8.3 study execution | 2026-12-01 | 6-month comparative authority |
| Phase 8.4 study execution | 2027-06-01 | 12-month full-cycle |

---

## 12. Governance Verdict

**A. ARCHIVE_GOVERNANCE_ESTABLISHED**

The SIH now has:
- A documented baseline of the current Zacks and Danelfin archives
- A canonical schema for all future archive files
- Normalized history master tables built from existing data
- A cadence plan defining capture frequency and gap tolerances
- 20 quality gates protecting archive integrity
- An operator runbook for executing captures
- A phased readiness roadmap with explicit go/no-go criteria for each Phase 8.x study

The system is ready to begin systematic archive capture. Phase 8.3 (2026-12-01) is the first date at which "Is ESS genuinely stronger than Zacks and Danelfin?" can be answered with evidence sufficient to justify composite weight changes.
