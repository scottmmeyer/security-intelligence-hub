# Phase 22D.1 — Portfolio Intelligence UI Consistency Audit
## Final Verdict Report

**Reference Date:** 2026-06-01  
**Audit Type:** Read-Only Evidence Gathering — No Code Changes Made  
**Deliverables:** 4 evidence files (see below)

---

## Audit Deliverables

| Deliverable | File | Status |
|-------------|------|--------|
| Replay Alignment Gap Analysis | `replay_alignment_gap_analysis.md` | ✅ Complete |
| Signal Coverage Audit | `signal_coverage_audit.csv` | ✅ Complete |
| Recommendation Narrative Audit | `recommendation_narrative_audit.md` | ✅ Complete |
| Freshness Governance Validation | `freshness_governance_validation.md` | ✅ Complete |

---

## Issue Classification Summary

### ISSUE 1 — Replay Alignment KPI Quality Component Permanently Zero
**Severity: HIGH**

The Replay Alignment KPI shows 31.7/100 with Quality component = 0.0/40 on every portfolio run, regardless of actual replay performance. This is a 3-layer pipeline gap:

1. **Data layer:** No per-symbol percentile rank exists anywhere in the replay data pipeline. `replay_performance_series.csv` contains only aggregate series data. The concept of "how did this symbol rank among its replay cohort" is entirely uncomputed.
2. **Loader layer:** `_load_replay_evidence()` (recommendations.py line 49) reads only symbol membership from `replay_inputs.csv`. The code comment promising `percentile_approx` is a dead reference to an unimplemented field.
3. **Overlay layer:** `build_security_overlays()` line 212 hardcodes `replay_percentile=None` unconditionally.

**Result:** `_compute_replay_alignment()` always receives an empty percentiles list → Quality always = 0.0. The KPI maximum is permanently capped at 60/100 across all runs.

**Recommended Fix:** Compute per-symbol percentile rank at replay completion time; store in replay artifacts; thread through loader → overlay → scorer.

---

### ISSUE 2 — ESS Signal Missing for 5 Portfolio Holdings (SBS, STNG, SIMO, MCB, BSVN)
**Severity: HIGH**

All 5 holdings show ESS = "—" in the UI despite recent ESS data existing in `ess_history_master.csv`. Root causes vary by symbol:

**Root Cause B (ESS archive disconnected from signal ingestion) — SBS, STNG, SIMO, MCB, BSVN:**
- `ess_history_master.csv` contains valid recent ESS data for all 5 symbols (most recent: 2026-05-20 for STNG/SIMO/BSVN; 2026-04-18 for MCB; 2026-04-04 for SBS)
- `analytical_universe_manager.py` uses only `signal_snapshot.csv` to populate `ess_score_text`
- SBS and MCB are absent from `signal_snapshot.csv` entirely
- STNG, SIMO, and BSVN are present but with `signal_coverage_status=NON_STARMINE_ANALYST` — the universe manager only uses rows with `STARMINE_COVERED` status

**Root Cause A (Provider coverage gap) — MCB Zacks only:**
- `latest_zacks.csv` has an MCB row but with blank rank/score fields — genuine absence of Zacks coverage on the 2026-06-01 capture date

**Impact on composite score:** ESS term (55% weight) is zero for all 5 symbols. Composite scores are computed from Zacks (25%) and Danelfin (10%) only. This understates conviction for symbols with genuine ESS coverage in the archive.

**Danelfin:** All 5 covered and flowing correctly — no issue.

**Recommended Fix:** Route `ess_history_master.csv` as a fallback in the universe rebuild when `signal_snapshot.csv` has no COVERED row for a symbol. For NON_STARMINE_ANALYST symbols, consider populating with a lower-confidence ESS value rather than silent suppression.

---

### ISSUE 3 — INCREASE_UNDERWEIGHT Narrative Does Not Surface Blocked Vehicle State
**Severity: HIGH**

When the optimizer finds `optimizer_decision = "NO_CANDIDATES"` or `"MANDATE_BLOCKED"` for an `INCREASE_UNDERWEIGHT` recommendation, the main recommendation card still shows:
- **Title:** "Build {node_label} allocation..."
- **Rationale:** Prescriptive ETF vehicle recommendations (hardcoded, unconditional)

The blocked status is only visible inside a **collapsible "Optimizer View" panel** that is hidden by default. Operators reading the main card receive an active increase directive with vehicle names even when the optimizer has determined no actionable path exists.

**Code gaps confirmed:**
- `recommendations.py`: `_PRESCRIPTIVE_RATIONALE` dict returns vehicle text unconditionally regardless of gate status
- `mandate.py`: `_build_recommendation_narrative()` has no branch for all-vehicles-blocked scenario
- `app.js` lines 1308–1429: `renderRecommendations()` renders `r.title` and `r.rationale` directly; never checks `optimizer_decision`
- `app.js` line 1820: ETF gate failures are in a secondary collapsed panel, not the primary card

**Recommended Fix:** When `optimizer_decision` is `NO_CANDIDATES` or `MANDATE_BLOCKED`, surface a visible indicator in the main card (e.g., badge, title suffix "— No Vehicles Available", or rationale prefix). Do not require the operator to expand a secondary panel to discover the recommendation is unactionable.

---

### ISSUE 4 — Danelfin and Yahoo Signal Freshness (3 Days Stale)
**Severity: MEDIUM**

Current state (2026-06-01):
- Danelfin `sourced_date` = 2026-05-29 → 3 days stale → UI shows **WARNING**
- Yahoo `sourced_date` = 2026-05-29 → 3 days stale → UI shows **WARNING**
- ESS and Zacks are current (2026-06-01 → FRESH)

This is an operational gap (signals need refresh), not a code bug. The UI freshness system is working correctly — it is accurately reporting WARNING state for the 3-day gap.

**Secondary code issues (LOW severity):**
- Server `_sourced_date()` reads the first CSV row rather than the latest date — latent correctness risk
- ESS is not included in the `/api/signal-status` endpoint
- Danelfin/Yahoo universe coverage is 954 rows vs 2,601 for Zacks and 2,831 for ESS — indicates these providers cover a subset of the analytical universe

**Recommended Fix:** Trigger `scripts/refresh_signals.py` to refresh Danelfin and Yahoo. No code change required for the operational staleness.

---

## Go/No-Go Recommendation for Phase 7.8A

### Assessment

| Issue | Severity | Blocks Phase 7.8A? |
|-------|----------|-------------------|
| Replay percentile permanently zero (Issue 1) | HIGH | Yes — KPI is structurally broken; 40% of score category is always 0 |
| ESS missing for 5 holdings (Issue 2) | HIGH | Yes — composite scores for affected holdings are systematically understated |
| Blocked vehicles not surfaced in narratives (Issue 3) | HIGH | Yes — operators may execute recommendations the system has already gated |
| Danelfin/Yahoo freshness (Issue 4) | MEDIUM | No — operational; refresh signals and it resolves |

### Verdict: **Resolve HIGH Issues Before Phase 7.8A**

All three HIGH-severity issues represent **silent failures** — the system produces output that looks valid but contains structural gaps invisible to the operator. Proceeding to Phase 7.8A under these conditions means:

1. The Replay Alignment KPI will always show ≤60% of its possible score, making portfolio quality assessments systematically biased
2. ~5 holdings show materially understated conviction scores due to the ESS archive disconnect
3. Operators may act on "Build allocation" directives that the optimizer has already determined are unactionable

The fixes for Issues 1 and 2 require pipeline changes (not UI-only). Issue 3 can be addressed with a targeted UI card update. Recommend completing these before advancing to Phase 7.8A.
