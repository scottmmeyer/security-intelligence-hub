# Roadmap Recommendation — Phase 8.0B.1D

## Governance Update — Signal Coverage Program Closed (2026-06-12)

SIGNAL-COVERAGE-04 through SIGNAL-COVERAGE-07 are closed based on live operational validation.

Validated closure state:

- Zacks holdings coverage: COMPLIANT (58/58 within threshold; stale=0, missing=0, failed=0)
- Danelfin holdings coverage: COMPLIANT (58/58 within threshold; stale=0, missing=0, failed=0)
- Yahoo holdings coverage: COMPLIANT (58/58 within threshold; stale=0, missing=0, failed=0)

Mandatory Holdings Coverage is operationally complete.

## Updated Next Priorities (Post-Closure)

1. PRA-IMPL-02 — Policy-Aware Funding Sources
2. AI-003 — Allocation Philosophy Explainability
3. PERFORMANCE-ATTRIBUTION-01
4. PIS Phase 2 — Change Detection

## Evaluation Criteria

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Operator Value | 30% | Directly improves operator decision quality |
| Portfolio Impact | 25% | Measurable effect on portfolio outcomes |
| Implementation Effort | 20% | Inverse: low effort = higher score |
| Strategic Importance | 25% | Enables future capabilities, builds foundation |

---

## Top 5 Recommended Next Initiatives

### Rank 1: FMP Bulk Fetch — Full Universe Coverage
**Phase:** ISSUE-01  
**Operator Value:** HIGH — Every deployment candidate will show Fundamental Snapshot  
**Portfolio Impact:** MEDIUM-HIGH — Operators see thesis integrity for all queue entries  
**Effort:** M (3–4 hours)  
**Strategic Importance:** HIGH — Unlocks all downstream FMP features  

**Rationale:** Without bulk fetch, the Fundamental Snapshot only renders for 12 symbols. After bulk fetch, every deployment queue candidate has FMP data. This single task activates everything built in 8.0B.1B and 8.0B.1B.5 for real use. It's high-value, well-defined, and relatively straightforward.

**Prerequisite:** None. Execute immediately.

---

### Rank 2: CRA Draft Persistence + Export (Phase 23.6C)
**Phase:** ISSUE-02  
**Operator Value:** HIGH — Operators can save and share rotation proposals  
**Portfolio Impact:** MEDIUM — Makes CRA output actionable beyond the screen  
**Effort:** M (3–4 hours)  
**Strategic Importance:** HIGH — Completes the CRA action loop  

**Rationale:** The CRA panel is already fully functional. Adding save/export/clipboard closes the last gap between insight and action. The data model is ready; only the API endpoints and UI wiring remain. This makes the CRA useful in practice, not just in-session.

**Prerequisite:** None. Can run immediately or in parallel with ISSUE-01.

---

### Rank 3: FMP Score Integration Assessment (Phase 8.0B.1C)
**Phase:** ISSUE-03  
**Operator Value:** MEDIUM (research phase)  
**Portfolio Impact:** VERY HIGH — Could materially improve signal quality  
**Effort:** L (5–7 hours)  
**Strategic Importance:** VERY HIGH — Defines whether FMP becomes a scoring input  

**Rationale:** The most strategically significant item in the backlog. If FMP fundamentals can be validated as improving CW-DAS accuracy, every deployment decision improves. However, this is a research phase, not implementation — governance must confirm the integration design before any scoring changes. Do this after ISSUE-01 provides full-universe data.

**Prerequisite:** ISSUE-01 (full-universe FMP data needed for meaningful analysis).

---

### Rank 4: Deployment Queue Filter by Thesis Integrity
**Phase:** ISSUE-06  
**Operator Value:** HIGH — Operators can focus on INTACT thesis candidates  
**Portfolio Impact:** LOW (display only)  
**Effort:** XS (1–2 hours)  
**Strategic Importance:** MEDIUM  

**Rationale:** Extremely low effort, high immediate operator utility. Once Fundamental Snapshot renders for all candidates (post-ISSUE-01), filtering by thesis integrity is an obvious next step. An operator can immediately scan "show me only INTACT thesis candidates in the top 20."

**Prerequisite:** ISSUE-01 (needs populated FMP data to be useful).

---

### Rank 5: YAML Registry Cleanup
**Phase:** ISSUE-08  
**Operator Value:** LOW (zero visible change)  
**Portfolio Impact:** ZERO  
**Effort:** XS (30 minutes)  
**Strategic Importance:** LOW  

**Rationale:** Known technical debt with zero behavioral impact. Eliminates stale metadata warnings for SPAXX/VMFXX/FZFXX. Small effort, removes a documented debt item, and sets a pattern for technical debt management. Do this as a warmup or parallel task during a longer session.

**Prerequisite:** None.

---

## Recommended Session Sequence

```
Session N+1:  ISSUE-01 (FMP Bulk Fetch) + ISSUE-08 (YAML cleanup)
Session N+2:  ISSUE-02 (CRA Draft Persistence + Export) 
Session N+3:  ISSUE-06 (Queue Filter by Thesis Integrity) + ISSUE-05 (Dislocation Watchlist)
Session N+4:  ISSUE-03 (FMP Score Integration Assessment — design phase)
Session N+5:  FMP 8.0B.1C implementation (if assessment APPROVED)
```

---

## Deferred (Do Not Start Yet)

| Issue | Reason for Deferral |
|-------|-------------------|
| ISSUE-04: Graduated Drift Penalty | Needs simulation data; LOW OW nodes are currently minor |
| ISSUE-10: FMP Subscription Upgrade | Not needed until 8.0B.1C defines what's missing |
| ISSUE-09: Theme Exposure Dashboard | Nice-to-have; deprioritize relative to scoring improvements |
| EPIC-05: Signal Evolution (scoring) | Requires Phase 8.0B.1C assessment first |
| ARCH-02: GitHub Actions CI | Infrastructure work; deprioritize vs. feature value |
| RES-01: FMS Empirical Validation | Requires historical data that doesn't yet exist |

---

## Risk-Adjusted View

If only one session is available: **ISSUE-01** (FMP Bulk Fetch)  
If two sessions: **ISSUE-01 + ISSUE-02** (FMP + CRA Export)  
If scoring improvement is the priority: Skip to **ISSUE-03** after ISSUE-01
