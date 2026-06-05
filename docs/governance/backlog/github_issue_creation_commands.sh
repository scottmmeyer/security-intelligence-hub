# GitHub Backlog Activation — Issue Creation Commands
# Repository: scottmmeyer/security-intelligence-hub
# Generated: June 5, 2026

# ══════════════════════════════════════════════════════════════
# PREREQUISITE: Install and authenticate gh CLI
# ══════════════════════════════════════════════════════════════
# 
# Install:
#   brew install gh
#
# Authenticate:
#   gh auth login
#   (select GitHub.com → HTTPS → authenticate via browser)
#
# Verify:
#   gh auth status
#   gh repo view scottmmeyer/security-intelligence-hub

REPO="scottmmeyer/security-intelligence-hub"

# ══════════════════════════════════════════════════════════════
# TASK 2 — CREATE LABELS
# ══════════════════════════════════════════════════════════════

# Type labels
gh label create "enhancement"     --color "3B82F6" --description "New feature or capability"                         --repo $REPO
gh label create "bug"             --color "EF4444" --description "Defect or incorrect behavior"                      --repo $REPO
gh label create "governance"      --color "6B7280" --description "Process, documentation, standards"                 --repo $REPO
gh label create "technical-debt"  --color "F97316" --description "Known cleanup with no behavioral change"           --repo $REPO
gh label create "research"        --color "14B8A6" --description "Investigation, audit, validation"                  --repo $REPO
gh label create "ui-ux"           --color "EC4899" --description "Frontend/display work"                             --repo $REPO
gh label create "epic"            --color "8B5CF6" --description "Top-level initiative grouping multiple issues"     --repo $REPO

# Component labels
gh label create "fmp"             --color "0EA5E9" --description "Financial Modeling Prep integration"               --repo $REPO
gh label create "cra"             --color "7C3AED" --description "Capital Rotation Advisor"                          --repo $REPO
gh label create "pap"             --color "1D4ED8" --description "Portfolio Action Pipeline"                         --repo $REPO
gh label create "cwdas"           --color "065F46" --description "CW-DAS scoring formula"                            --repo $REPO
gh label create "sti"             --color "92400E" --description "Strategic Intelligence (STI/UCF)"                  --repo $REPO
gh label create "ess"             --color "BE185D" --description "ESS signal pipeline"                               --repo $REPO
gh label create "replay"          --color "115E59" --description "Replay scoring system"                             --repo $REPO
gh label create "provider"        --color "1E3A5F" --description "External data provider"                            --repo $REPO
gh label create "data-quality"    --color "FBBF24" --description "Data validation, null handling, coverage"          --repo $REPO

# Priority labels
gh label create "priority-critical" --color "DC2626" --description "Blocking — immediate action"                    --repo $REPO
gh label create "priority-high"     --color "EA580C" --description "High value — next 1-2 sessions"                 --repo $REPO
gh label create "priority-medium"   --color "D97706" --description "Meaningful improvement — not urgent"            --repo $REPO
gh label create "priority-low"      --color "4B5563" --description "Nice-to-have — deferred"                        --repo $REPO

# Status labels
gh label create "ready"           --color "16A34A" --description "Fully scoped, ready to implement"                  --repo $REPO
gh label create "needs-design"    --color "9333EA" --description "Requires design phase before implementation"       --repo $REPO
gh label create "blocked"         --color "DC2626" --description "Blocked by dependency or authorization gate"       --repo $REPO
gh label create "deferred"        --color "6B7280" --description "Explicitly deferred to future milestone"           --repo $REPO
gh label create "in-progress"     --color "3B82F6" --description "Currently being worked"                            --repo $REPO

echo "Labels created: 26 total"

# ══════════════════════════════════════════════════════════════
# TASK 3 — CREATE EPIC ISSUES
# ══════════════════════════════════════════════════════════════

gh issue create \
  --repo $REPO \
  --title "EPIC: FMP Integration" \
  --label "epic,fmp,provider" \
  --body "## FMP Integration Epic

**Objective:** Make Financial Modeling Prep fundamental data fully available and progressively integrated across SIH signals, scoring, and display.

**Phase Track:**
- [x] 8.0B.0 — FMP Capability Audit
- [x] 8.0B.0A — FMP Integration Philosophy
- [x] 8.0B.1A — FMP Signal Intake Pipeline
- [x] 8.0B.1A.1 — FMP API Corrections
- [x] 8.0B.1B — FMP Analytical Universe Enrichment
- [x] 8.0B.1B.5 — FMP Diagnostic Overlay
- [x] ISSUE-01 — FMP Bulk Fetch (98.7% FULL coverage achieved)
- [ ] ISSUE-03 — FMP Score Integration Assessment (8.0B.1C)
- [ ] 8.0B.2 — Dislocation Framework (post-8.0B.1C)

**Success Definition:** FMP fundamental data influences at least one scored component in CW-DAS or UCF, validated against historical queue quality.

**Governance:** docs/governance/backlog/epic_structure.md"

gh issue create \
  --repo $REPO \
  --title "EPIC: Capital Rotation Advisor (CRA)" \
  --label "epic,cra" \
  --body "## Capital Rotation Advisor Epic

**Objective:** Provide an operator-facing capital rotation recommendation engine that identifies optimal sources and targets for portfolio rebalancing.

**Phase Track:**
- [x] 23.6A — CRA Design & Architecture
- [x] 23.6B.0 — CRA Backend Implementation
- [x] 23.6B.1 — CRA UI Implementation
- [x] 23.6B.2 — Tier-Aware Allocation
- [x] 23.6B.3 — CRA Forensics
- [x] 23.6B.4 — Trust Remediation
- [x] 23.6B.5 — FIS Strategic Exit Retirement
- [ ] ISSUE-02 — CRA Draft Persistence + Export (Phase 23.6C)
- [ ] 23.6D — TBD post-23.6C

**Success Definition:** Operator can save, export, and share a CRA proposal with a single action.

**Governance:** docs/governance/backlog/epic_structure.md"

gh issue create \
  --repo $REPO \
  --title "EPIC: Portfolio Action Pipeline (PAP)" \
  --label "epic,pap" \
  --body "## Portfolio Action Pipeline Epic

**Objective:** Provide a complete operator workflow from signal ingestion through portfolio analysis, deployment queue, and action tracking.

**Phase Track:**
- [x] 23.0A — Tax Position Panel
- [x] 23.1 — Operator Policy Registry
- [x] 23.2 — Policy Annotations
- [x] 23.3 — Deployment Planner
- [x] 23.4 — NBA/OW-node Filtering
- [x] 23.5 — Allocation Node Tracking
- [ ] 23.0B — Portfolio Action Pipeline v2 (future)

**Success Definition:** Full operator workflow from CSV upload to deployment action is traceable, auditable, and policy-aware.

**Governance:** docs/governance/backlog/epic_structure.md"

gh issue create \
  --repo $REPO \
  --title "EPIC: Company Context & Methodology" \
  --label "epic,ui-ux" \
  --body "## Company Context & Methodology Epic

**Objective:** Provide rich operator-facing company context (identity, business, thesis, methodology) directly in the deployment queue card and application UI.

**Phase Track:**
- [x] 8.0B.X — Company Context Enrichment
- [x] 8.0B.X.1 — Company Business Snapshot
- [x] 8.0B.X.2 — What They Do / Why It Matters / Tags
- [x] 8.0B.X.3 — Why SIH Likes It
- [x] 8.0B.X.4 — CW-DAS Allocation Drift Audit
- [x] 8.0B.1E — Consensus Intelligence Methodology
- [x] CII-001 — Methodology Awareness Panel
- [ ] ISSUE-05 — Dislocation Watchlist Panel
- [ ] ISSUE-06 — Queue Filter by Thesis Integrity
- [ ] 8.0B.X.5 — Theme Concentration Analysis

**Success Definition:** An operator reviewing any deployment queue candidate can fully understand the company, thesis, and SIH rationale without leaving the card.

**Governance:** docs/governance/backlog/epic_structure.md"

gh issue create \
  --repo $REPO \
  --title "EPIC: Signal Intelligence Evolution" \
  --label "epic,cwdas,sti,ess" \
  --body "## Signal Intelligence Evolution Epic

**Objective:** Evolve the composite signal model to incorporate additional evidence sources and improve conviction differentiation.

**Phase Track:**
- [x] 7.5 — UCF / CW-DAS baseline
- [x] 8.0B.1B.5 — FMP Diagnostic Overlay (display-only)
- [ ] ISSUE-03 — FMP Score Integration Assessment (8.0B.1C)
- [ ] ISSUE-04 — Graduated Allocation Drift Penalty
- [ ] TBD — Analyst Consensus Integration into UCF
- [ ] 8.0D — CW-DAS FMS Integration (requires empirical validation)

**Success Definition:** Composite score more accurately reflects true investment opportunity quality, validated against deployment outcomes.

**Governance:** docs/governance/backlog/epic_structure.md"

gh issue create \
  --repo $REPO \
  --title "EPIC: Governance & Tooling" \
  --label "epic,governance" \
  --body "## Governance & Tooling Epic

**Objective:** Establish durable engineering practices for SIH: backlog management, test standards, CI, documentation, and technical debt.

**Phase Track:**
- [x] 8.0B.1D — GitHub Backlog Establishment
- [x] 8.0B.1E — Consensus Intelligence Methodology
- [ ] GitHub Actions CI (automated test run on push)
- [ ] Signal Freshness Monitoring
- [ ] Technical Debt Cleanup Sprint (ISSUE-08: YAML cleanup)

**Success Definition:** All SIH development work is tracked in GitHub Issues with acceptance criteria. No untracked deferred work.

**Execution Standard:** docs/governance/backlog/copilot_execution_standard.md"

echo "Epics created: 6"

# ══════════════════════════════════════════════════════════════
# TASK 4 — CREATE IMPLEMENTATION ISSUES
# ══════════════════════════════════════════════════════════════

# ISSUE-01: FMP Bulk Fetch (CLOSED — already complete)
gh issue create \
  --repo $REPO \
  --title "ISSUE-01: FMP Bulk Fetch — Full Universe Coverage" \
  --label "enhancement,fmp,provider,priority-high,ready" \
  --body "## Summary
Expand FMP enrichment from 12 validation symbols to full analytical universe (~2,465 symbols).

## Context
Phase 8.0B.1B established FMP data infrastructure but only fetched 12 validation symbols.
Full coverage unlocks Fundamental Snapshot, Thesis Integrity, and Dislocation Detection for every deployment queue candidate.

**Epic:** EPIC: FMP Integration
**Design docs:** docs/governance/backlog/initial_issue_backlog.md

## Acceptance Criteria
- [x] \`scripts/fmp_bulk_fetch_universe.py\` — resumable bulk fetcher with smart-resume
- [x] \`data/signals/fmp/latest/latest_fmp_key_metrics.csv\` — 2,467 symbols cached
- [x] \`data/signals/fmp/latest/latest_fmp_grades_consensus.csv\` — all symbols
- [x] \`data/signals/fmp/latest/latest_fmp_earnings_surprises.csv\` — all symbols
- [x] \`data/signals/fmp/latest/latest_fmp_income_growth.csv\` — all symbols
- [x] Coverage report: 98.7% FULL (target was ≥75%)
- [x] Fundamental Snapshot renders for all 32 deployment queue candidates
- [x] 0 scoring changes — 1,004 tests passing

## Result
**COMPLETE — 98.7% FULL coverage (2,442/2,475 symbols)**

ADR support: ✅ TSM, ASML, CVE, SBS confirmed FULL
International support: ✅ Taiwan, Netherlands, Canada, Brazil, Switzerland
ETF handling: ✅ Unit Trust Funds → ETF_NOT_APPLICABLE
Null handling: pe_ratio_ttm null (FMP Starter plan limitation — documented)

## Non-Negotiables
- NO CW-DAS changes ✅
- NO UCF changes ✅
- NO Deployment Queue changes ✅
- NO Recommendation changes ✅

## Closes
This issue closes upon merge. Certification: data/analysis/issue_01_fmp_bulk/"

# Close ISSUE-01 immediately since it's already done
# gh issue close <number> --repo $REPO

echo "Note: After creating ISSUE-01, close it with: gh issue close <number> --repo $REPO"

gh issue create \
  --repo $REPO \
  --title "ISSUE-02: CRA Draft Persistence + Export (Phase 23.6C)" \
  --label "enhancement,cra,ui-ux,priority-high,ready" \
  --body "## Summary
Add save/export/clipboard capabilities to the Capital Rotation Advisor panel.

## Context
The CRA panel produces rotation proposals but operators cannot save, export, or share them outside the session. Phase 23.6C adds three additive UX actions with no scoring impact.

**Epic:** EPIC: Capital Rotation Advisor (CRA)
**Design docs:** docs/governance/backlog/initial_issue_backlog.md

## Acceptance Criteria
- [ ] \`POST /api/cra/proposal/draft\` saves current proposal to \`data/operator/cra_draft.json\`
- [ ] \`GET /api/cra/proposal/export\` returns downloadable CSV of the proposal
- [ ] Clipboard copy button copies proposal summary text to clipboard
- [ ] Draft loads automatically on page reload (persist last proposal)
- [ ] All three buttons render in CRA panel with correct enabled/disabled state
- [ ] 0 scoring changes; 1,004 tests passing

## Non-Negotiables
- NO CW-DAS changes
- NO scoring changes
- NO ranking changes

## Estimated Effort
M (3–4 hours)"

gh issue create \
  --repo $REPO \
  --title "ISSUE-03: FMP Score Integration Assessment (Phase 8.0B.1C)" \
  --label "research,fmp,cwdas,priority-high,needs-design" \
  --body "## Summary
Formal assessment of whether FMP fundamental data should be integrated into CW-DAS scoring or UCF. Research and design phase only — no scoring changes in this issue.

## Context
Phase 8.0B.1B.5 established FMP data as display-only. Full-universe FMP coverage (ISSUE-01, 98.7% FULL) is now available. The next question: do FMP fundamentals have enough signal value to inform scoring decisions?

**Epic:** EPIC: Signal Intelligence Evolution
**Prerequisite:** ISSUE-01 complete ✅
**Design docs:** docs/governance/backlog/initial_issue_backlog.md, docs/governance/fmp_integration_philosophy.md

## Acceptance Criteria
- [ ] Design document: candidate FMP fields for CW-DAS Momentum component integration
- [ ] Counterfactual simulation: what the deployment queue would look like with FMP-influenced scores
- [ ] Fundamental Consistency classifier calibration against known outcomes
- [ ] Risk assessment: what could break, what signals could be degraded
- [ ] Governance verdict document: APPROVED / APPROVED WITH ADVISORIES / BLOCKED
- [ ] NO scoring changes in this phase

## Non-Negotiables
- NO CW-DAS changes in this phase (assessment only)
- NO UCF changes
- Scoring change requires separate authorized issue

## Estimated Effort
L (5–7 hours)"

gh issue create \
  --repo $REPO \
  --title "ISSUE-04: Dislocation Watchlist Panel" \
  --label "enhancement,ui-ux,fmp,priority-medium,needs-design" \
  --body "## Summary
Add a dedicated Dislocation Watchlist section to the Portfolio Alignment UI showing all symbols flagged as POTENTIAL or HIGH CONVICTION dislocation by the FMP Diagnostic Overlay.

## Context
Phase 8.0B.1B.5 implemented per-card dislocation detection. Operators currently must expand each card individually to see dislocation status. A watchlist panel surfaces all dislocations at a glance.

**Epic:** EPIC: Company Context & Methodology
**Prerequisite:** ISSUE-01 complete ✅ (needs full-universe FMP data)
**Design docs:** docs/governance/backlog/initial_issue_backlog.md

## Acceptance Criteria
- [ ] New panel 'Potential Dislocations' renders below deployment queue when ≥1 symbol qualifies
- [ ] Displays: symbol, CW-DAS rank, Thesis Integrity, Dislocation label, key evidence
- [ ] Filters out symbols with NO_DATA or ETF_NOT_APPLICABLE FMP coverage
- [ ] Panel collapses/expands like other sections
- [ ] No scoring changes; regression suite passes

## Non-Negotiables
- NO scoring changes
- NO ranking changes
- Display-only

## Estimated Effort
S (2–3 hours)"

gh issue create \
  --repo $REPO \
  --title "ISSUE-05: Deployment Queue Filter by Thesis Integrity" \
  --label "enhancement,ui-ux,priority-medium,ready" \
  --body "## Summary
Add a filter control above the deployment queue table allowing operators to filter candidates by FMP Thesis Integrity status (INTACT / QUESTIONABLE / DETERIORATING / INSUFFICIENT_DATA).

## Context
With full-universe FMP coverage (98.7% FULL after ISSUE-01), every deployment queue candidate now has Thesis Integrity data. Filtering by this field helps operators quickly focus on candidates with confirmed or concerning fundamental profiles.

**Epic:** EPIC: Company Context & Methodology
**Prerequisite:** ISSUE-01 complete ✅
**Design docs:** docs/governance/backlog/initial_issue_backlog.md

## Acceptance Criteria
- [ ] Filter dropdown/toggle appears above deployment queue table
- [ ] Options: All, INTACT, QUESTIONABLE, DETERIORATING, INSUFFICIENT_DATA
- [ ] Filter applied client-side — no API change required
- [ ] 'All' option resets filter to show full queue
- [ ] Filter state persists during session
- [ ] 0 scoring changes; regression suite passes

## Non-Negotiables
- NO scoring changes
- NO ranking changes
- Client-side only

## Estimated Effort
XS (1–2 hours)"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "SUMMARY"
echo "══════════════════════════════════════════════════════════"
echo "Labels created: 26"
echo "Epic issues created: 6"
echo "Implementation issues created: 5 (ISSUE-01 through ISSUE-05)"
echo ""
echo "After creating ISSUE-01, close it immediately:"
echo "  gh issue close 1 --repo $REPO  (replace 1 with actual issue number)"
echo ""
echo "View all issues:"
echo "  gh issue list --repo $REPO"
echo ""
echo "Open in browser:"
echo "  gh repo view $REPO --web"
