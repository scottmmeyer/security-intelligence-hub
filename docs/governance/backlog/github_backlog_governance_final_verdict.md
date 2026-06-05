# GitHub Backlog Governance Final Verdict — Phase 8.0B.1D

## Verdict

**APPROVED**

---

## Q1: Is GitHub Issues recommended as the primary backlog system?

**YES.**

Current tracking (session memory files, deliverable documents, ChatGPT history) is insufficient as SIH grows. The codebase now has 46 tracked backlog items across 8 categories, spanning 6 epics. Issues will be lost without a structured system.

GitHub Issues provides:
- Persistent, searchable backlog
- Label-based filtering and prioritization
- Acceptance criteria per item
- Cross-reference to commits and PRs
- Milestone-based roadmap grouping
- Native integration with the GitHub repository where code lives

**Recommendation:** Establish GitHub Issues as the authoritative backlog system immediately.

---

## Q2: What labels should be established?

**Minimum viable label set (create these first):**

**Type:** `enhancement` `bug` `governance` `technical-debt` `research` `ui-ux` `epic`  
**Component:** `fmp` `cra` `pap` `cwdas` `sti` `ess` `replay` `provider` `data-quality`  
**Priority:** `priority-critical` `priority-high` `priority-medium` `priority-low`  
**Status:** `ready` `needs-design` `blocked` `deferred` `in-progress`

Full label taxonomy: `docs/governance/backlog/github_issue_taxonomy.md`

---

## Q3: What epics should exist?

Six epics recommended:

| Epic | Focus |
|------|-------|
| EPIC-01: FMP Integration | FMP 8.0B track — fundamental data |
| EPIC-02: CRA | Capital Rotation Advisor 23.6 track |
| EPIC-03: PAP | Portfolio Action Pipeline 23.x track |
| EPIC-04: Company Context | 8.0B.X track — company identity/context |
| EPIC-05: Signal Evolution | Scoring improvements, CW-DAS evolution |
| EPIC-06: Governance & Tooling | CI, standards, backlog, technical debt |

Full epic structure: `docs/governance/backlog/epic_structure.md`

---

## Q4: What are the top 10 backlog items?

| Rank | Title | Priority | Effort |
|------|-------|----------|--------|
| 1 | FMP Bulk Fetch — Full Universe Coverage | HIGH | M |
| 2 | CRA Draft Persistence + CSV Export (23.6C) | HIGH | M |
| 3 | FMP Score Integration Assessment (8.0B.1C) | HIGH | L |
| 4 | Graduated Allocation Drift Penalty | MEDIUM | M |
| 5 | Dislocation Watchlist Panel | MEDIUM | S |
| 6 | Queue Filter by Thesis Integrity | MEDIUM | XS |
| 7 | FMP Consistency Monitor | MEDIUM | M |
| 8 | YAML Registry Cleanup | LOW | XS |
| 9 | Portfolio Theme Exposure Dashboard | MEDIUM | S |
| 10 | FMP Subscription Upgrade Evaluation | MEDIUM | S |

Full issue backlog: `docs/governance/backlog/initial_issue_backlog.md`

---

## Q5: What should be worked next?

**Immediate (Session N+1):**
- **ISSUE-01: FMP Bulk Fetch** — Activates the Fundamental Snapshot for all deployment candidates. Highest single-task operator value.
- **ISSUE-08: YAML Registry Cleanup** — 30-minute debt item; clear it as warmup.

**Session N+2:**
- **ISSUE-02: CRA Draft Persistence** — Completes the CRA action loop.

**Session N+3:**
- **ISSUE-06: Queue Filter by Thesis Integrity** + **ISSUE-05: Dislocation Watchlist**

**Session N+4:**
- **ISSUE-03: FMP Score Integration Assessment** — Research phase, most strategic.

---

## Q6: What should be deferred?

| Item | Reason |
|------|--------|
| Graduated Drift Penalty | LOW OW nodes are minor; no urgency |
| FMP Premium+ features (P/E, quarterly growth) | Wait for 8.0B.1C assessment to confirm need |
| GitHub Actions CI | Infrastructure; not operator-facing |
| FMS Empirical Validation | Requires historical data not yet available |
| AI-assisted company summaries | Low priority; current summaries are adequate |
| CRA Phase 23.6D | Not yet scoped; wait for 23.6C completion |

---

## Recommended Initial GitHub Backlog

**Ready to create immediately (copy titles directly into GitHub):**

```
[ISSUE-01] FMP Bulk Fetch — Full Universe Coverage
[ISSUE-02] CRA Draft Persistence + CSV Export (Phase 23.6C)
[ISSUE-03] FMP Score Integration Assessment (Phase 8.0B.1C)
[ISSUE-04] Graduated Allocation Drift Penalty
[ISSUE-05] Dislocation Watchlist Panel
[ISSUE-06] Deployment Queue Filter by Thesis Integrity
[ISSUE-07] FMP Consistency Monitor
[ISSUE-08] YAML Registry Cleanup (SPAXX/VMFXX/FZFXX)
[ISSUE-09] Portfolio Theme Exposure Dashboard
[ISSUE-10] FMP Subscription Upgrade Evaluation
[ISSUE-11] Historical Fundamental Trends Mini-Chart
[ISSUE-12] Strategic Exit Automation (PAR strategic_profiles.json)
[ISSUE-13] Signal Freshness Monitoring
[ISSUE-14] FMS Predictive Value Empirical Validation
[ISSUE-15] GitHub Actions CI Setup
```

---

## Governance Documents Created

| Document | Path |
|---------|------|
| Backlog Inventory | `docs/governance/backlog/backlog_inventory.md` |
| Issue Taxonomy | `docs/governance/backlog/github_issue_taxonomy.md` |
| Epic Structure | `docs/governance/backlog/epic_structure.md` |
| Initial Issue Backlog | `docs/governance/backlog/initial_issue_backlog.md` |
| Copilot Execution Standard | `docs/governance/backlog/copilot_execution_standard.md` |
| Roadmap Recommendation | `docs/governance/backlog/roadmap_recommendation.md` |
| Final Verdict (this doc) | `docs/governance/backlog/github_backlog_governance_final_verdict.md` |

---

## Implementation Status

No code changes in Phase 8.0B.1D. Governance documentation only.  
All 46 backlog items cataloged. Execution standard defined. Roadmap sequenced.

**Phase 8.0B.1D: COMPLETE.**

Next recommended action: Create GitHub Issues for top 10 items using the titles and acceptance criteria in `initial_issue_backlog.md`.
