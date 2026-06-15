# Initial Issue Backlog — Phase 8.0B.1D

## Program Closure Update — 2026-06-12

### Closed Issues

| ID | Title | Status | Closure Basis |
|---|---|---|---|
| SIGNAL-COVERAGE-04 | Coverage Governance Denominator Separation | CLOSED | Denominator drift identified and governance concepts separated |
| SIGNAL-COVERAGE-05 | Operational Mandatory Holdings Coverage Enforcement | CLOSED | Canonical baseline, applicability model, and holdings coverage model implemented |
| SIGNAL-COVERAGE-06 | Coverage-Aware Refresh Enforcement | CLOSED | coverage-aware eligibility, coverage_repair mode, report/API/UI truthfulness validated |
| SIGNAL-COVERAGE-07 | Coverage Repair Failed Checkpoint Retry | CLOSED | failed same-day checkpoint retries implemented and live repair validated |

### Final Validated State (Portfolio Holdings Coverage)

| Provider | Status | Applicable | Within Threshold | Stale | Missing | Failed | Not Applicable |
|---|---|---:|---:|---:|---:|---:|---:|
| Zacks | COMPLIANT | 58 | 58 | 0 | 0 | 0 | 16 |
| Danelfin | COMPLIANT | 58 | 58 | 0 | 0 | 0 | 16 |
| Yahoo | COMPLIANT | 58 | 58 | 0 | 0 | 0 | 16 |

### Governance Closure Verdict

Mandatory Holdings Coverage is operationally complete. Refresh engine behavior, holdings coverage model, applicability classification, UI reporting, and retry semantics were validated in live execution.

### Post-Closure Priority Order

1. PRA-IMPL-02 — Policy-Aware Funding Sources
2. AI-003 — Allocation Philosophy Explainability
3. PERFORMANCE-ATTRIBUTION-01
4. PIS Phase 2 — Change Detection

## Top 10 Issues (Priority Ordered)

---

### ISSUE-01: FMP Bulk Fetch — Full Universe Coverage
**Labels:** `enhancement` `fmp` `provider` `priority-high` `ready`  
**Epic:** EPIC-01: FMP Integration  
**Milestone:** FMP Integration Track

**Description:**  
FMP data has been fetched for 12 validation symbols only. The full analytical universe (2,473 symbols) requires a bulk fetch. FMP Starter plan provides bulk endpoints that can cover the entire universe in 4 API calls vs. 2,473 per-symbol calls.

**Acceptance Criteria:**
- [ ] `scripts/refresh_signals.py` includes `fmp` as a provider with bulk endpoints
- [ ] `data/signals/fmp/latest/latest_fmp_key_metrics.csv` — all 2,473 symbols
- [ ] `data/signals/fmp/latest/latest_fmp_grades_consensus.csv` — all symbols
- [ ] `data/signals/fmp/latest/latest_fmp_earnings_surprises.csv` — all symbols
- [ ] Coverage report shows ≥75% FULL for equity universe
- [ ] Fundamental Snapshot renders for all deployment queue candidates
- [ ] 0 scoring changes; regression suite passes

**Estimated Effort:** M

---

### ISSUE-02: CRA Draft Persistence + Export (Phase 23.6C)
**Labels:** `enhancement` `cra` `ui-ux` `priority-high` `ready`  
**Epic:** EPIC-02: CRA  
**Milestone:** CRA Track v2

**Description:**  
Three UX items scoped in Phase 23.6C: (1) Save CRA proposal draft to server, (2) Export proposal as CSV, (3) Clipboard copy button. The data model is already ready.

**Acceptance Criteria:**
- [ ] `POST /api/cra/proposal/draft` saves current proposal to `data/operator/cra_draft.json`
- [ ] `GET /api/cra/proposal/export` returns downloadable CSV of proposal
- [ ] Clipboard copy button copies proposal summary text
- [ ] Draft loads automatically on page reload
- [ ] All three buttons render in CRA panel with correct state management
- [ ] 0 scoring changes; regression suite passes

**Estimated Effort:** M

---

### ISSUE-03: FMP Score Integration Assessment (Phase 8.0B.1C)
**Labels:** `research` `fmp` `cwdas` `priority-high` `needs-design`  
**Epic:** EPIC-01: FMP Integration  
**Milestone:** Scoring Evolution

**Description:**  
Formal assessment of whether FMP fundamental data should be integrated into CW-DAS scoring (Momentum component) or UCF. This is a research and design phase — not implementation. Requires: (a) assessing which fields have signal value, (b) determining impact on queue ranking, (c) designing the integration, (d) governance approval before any scoring change.

**Acceptance Criteria:**
- [ ] Design document identifying candidate integration points
- [ ] Counterfactual simulation: what queue would look like with FMP-influenced scores
- [ ] Risk assessment: what could break
- [ ] Governance verdict: APPROVED / APPROVED WITH ADVISORIES / BLOCKED
- [ ] No scoring changes in this phase

**Estimated Effort:** L

---

### ISSUE-04: Graduated Allocation Drift Penalty
**Labels:** `enhancement` `cwdas` `priority-medium` `needs-design`  
**Epic:** EPIC-05: Signal Intelligence Evolution  
**Milestone:** Scoring Evolution

**Description:**  
Current CW-DAS Redundancy Penalty is binary: −15 for MODERATE+ OW nodes, 0 for LOW OW. This creates a cliff at the MODERATE threshold. US.SMALL (+3.26% OW) and US.MICRO (+2.00% OW) receive zero penalty despite meaningful drift. A graduated response would more accurately signal allocation pressure.

**Acceptance Criteria:**
- [ ] Design doc specifying graduated penalty formula (e.g., LINEAR: drift_pct × scale_factor)
- [ ] Simulation against current queue — show rank impact
- [ ] Validation that top 2 positions (DELL, VRT) remain stable
- [ ] MODERATE threshold behavior preserved (no regression for current penalty)
- [ ] Governance sign-off
- [ ] Regression suite passes

**Estimated Effort:** M

---

### ISSUE-05: Dislocation Watchlist Panel
**Labels:** `enhancement` `ui-ux` `fmp` `priority-medium` `needs-design`  
**Epic:** EPIC-04: Company Context Track  
**Milestone:** UI Enhancement Track

**Description:**  
Add a dedicated "Dislocation Watchlist" section to the Portfolio Alignment UI. Shows all symbols with `dislocation_status = POTENTIAL or HIGH CONVICTION` across the deployment queue and holdings. Allows the operator to see at a glance where fundamental thesis is intact but signal/price weakness may create an entry opportunity.

**Acceptance Criteria:**
- [ ] New panel "Potential Dislocations" renders when at least 1 symbol qualifies
- [ ] Shows: symbol, rank, thesis integrity, dislocation label, key evidence
- [ ] Filters out symbols with NO_DATA coverage
- [ ] No scoring changes
- [ ] Regression suite passes

**Estimated Effort:** S

---

### ISSUE-06: Deployment Queue Filter by Thesis Integrity
**Labels:** `enhancement` `ui-ux` `priority-medium` `ready`  
**Epic:** EPIC-04: Company Context Track  
**Milestone:** UI Enhancement Track

**Description:**  
Add a filter control to the deployment queue table that lets the operator filter by Thesis Integrity status (INTACT / QUESTIONABLE / DETERIORATING / INSUFFICIENT_DATA). Useful for quickly identifying candidates where fundamentals support or challenge the signal-driven ranking.

**Acceptance Criteria:**
- [ ] Filter dropdown/toggle appears above deployment queue table
- [ ] Filters are applied client-side (no API change)
- [ ] "All" option resets filter
- [ ] Filter state persists during session
- [ ] 0 scoring changes

**Estimated Effort:** XS

---

### ISSUE-07: FMP Consistency Monitor (Automated Stale Signal Detection)
**Labels:** `enhancement` `fmp` `data-quality` `priority-medium` `needs-design`  
**Epic:** EPIC-01: FMP Integration  
**Milestone:** FMP Integration Track

**Description:**  
Build a monitoring check that flags symbols where ESS/Danelfin signal direction is CONTRADICTORY relative to FMP fundamental data for more than 2 consecutive refresh cycles. Surfaces as a governance alert — not a scoring change.

**Acceptance Criteria:**
- [ ] `src/scoring/fmp_consistency_monitor.py` runs as part of `refresh_signals.py`
- [ ] Writes `data/signals/fmp/latest/fmp_consistency_alerts.csv`
- [ ] Alert conditions: CONTRADICTORY classification for 2+ cycles
- [ ] No scoring changes
- [ ] Regression suite passes

**Estimated Effort:** M

---

### ISSUE-08: YAML Registry Cleanup (SPAXX / VMFXX / FZFXX)
**Labels:** `technical-debt` `pap` `priority-low` `ready`  
**Epic:** EPIC-06: Governance & Tooling  
**Milestone:** Technical Debt Cleanup

**Description:**  
`etf_exposure_decomposition.yaml` contains entries for SPAXX, VMFXX, and FZFXX with `decomposition_source: REGISTRY` which produces stale metadata warnings. These should be changed to `decomposition_source: DIRECT_CLASSIFICATION`. Zero behavioral impact — pure cleanup.

**Acceptance Criteria:**
- [ ] SPAXX, VMFXX, FZFXX entries updated in `etf_exposure_decomposition.yaml`
- [ ] No stale metadata warnings for these symbols in pipeline output
- [ ] Regression suite passes (no change in scores, classifications, or deployment queue)

**Estimated Effort:** XS

---

### ISSUE-09: Portfolio Theme Exposure Dashboard
**Labels:** `enhancement` `ui-ux` `priority-medium` `needs-design`  
**Epic:** EPIC-04: Company Context Track  
**Milestone:** UI Enhancement Track

**Description:**  
Using the business model tags implemented in Phase 8.0B.X.2 (AI, DATA CENTER, SEMICONDUCTOR, etc.), build a Portfolio Theme Exposure view showing what percentage of the portfolio is exposed to each thematic category. Helps operators understand concentration by investment theme, not just sector.

**Acceptance Criteria:**
- [ ] New "Theme Exposure" panel in Portfolio Alignment UI
- [ ] Shows tag → % portfolio weight breakdown
- [ ] Tags derived from existing `_TAGS_PRIMARY` + keyword boost logic (no new data)
- [ ] Visual: simple bar or sorted list
- [ ] 0 scoring changes

**Estimated Effort:** S

---

### ISSUE-10: FMP Subscription Upgrade Evaluation
**Labels:** `research` `fmp` `provider` `governance` `priority-medium` `needs-design`  
**Epic:** EPIC-01: FMP Integration  
**Milestone:** FMP Integration Track

**Description:**  
Evaluate whether upgrading from FMP Starter ($19/mo) to a higher tier unlocks material data improvements: (1) `pe_ratio_ttm` return, (2) quarterly income growth granularity, (3) higher rate limits for faster bulk refresh. Document cost vs. capability matrix and make a recommendation.

**Acceptance Criteria:**
- [ ] Document listing what each tier unlocks
- [ ] Estimate of SIH impact (which null fields would fill)
- [ ] Cost/benefit analysis
- [ ] Recommendation: upgrade or defer
- [ ] No implementation changes in this phase

**Estimated Effort:** S

---

## Additional Backlog (Issues 11–20)

| # | Title | Labels | Priority |
|---|-------|--------|----------|
| 11 | Historical Fundamental Trends mini-chart | ui-ux, fmp | medium |
| 12 | Strategic Exit Automation (PAR strategic_profiles.json) | cra, pap | medium |
| 13 | Replay Curve Full-Universe Expansion | replay, research | low |
| 14 | FMP Quarterly Income Growth (Premium+) | fmp, provider | low |
| 15 | AI-Assisted Company Summary Refinement | ui-ux | low |
| 16 | GitHub Actions CI Setup | governance | medium |
| 17 | Signal Freshness Monitoring | data-quality, governance | medium |
| 18 | CRA Phase 23.6D (post-23.6C TBD) | cra | low |
| 19 | FMS Predictive Value Empirical Validation | research, ess | high |
| 20 | Dislocation Framework (Phase 8.0B.2) | fmp, cwdas | medium |
