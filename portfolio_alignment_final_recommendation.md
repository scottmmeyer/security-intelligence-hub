# Portfolio Alignment — UX Final Recommendation

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

---

## Final Questions

### 1. Is Portfolio Alignment Operator-Ready?

**Partially.** The core decision machinery is complete and trustworthy:
- PAP with 5 categories is excellent (especially with FVI overlays from PRA-IMPL-05)
- CRA is well-structured
- Deployment Queue is clear
- Policy integration (BLOCKED/DEFERRED) is correct
- Conviction Anchors are rationalized (PRA-IMPL-06)

However, three trust-critical issues prevent "fully ready" status:
1. **"Legacy Alignment"** — the top KPI carries a confusing label
2. **Reconciliation FAIL** — visible with no explanation; undermines trust
3. **Page order** — PAP and CRA are buried after 12 sections; operators miss execution guidance

For internal use: yes, operator-ready.  
For investor/bank demo: not quite — UX-PA-01, 02, 03 must be resolved first.

---

### 2. What Are the Highest-Value UX Improvements?

**Sprint 1 (1–2 days total, all S complexity):**

1. Rename "Legacy Alignment" → "Allocation Alignment" (UX-PA-01)
2. Reorder page: PAP and CRA before Security Intelligence Overlay (UX-PA-03)
3. Add deployable cash context tooltip (UX-PA-07)
4. Add BLOCKED action "what would unblock" note (UX-PA-06)
5. Add Multi-Dim score navigation links (UX-PA-04)

**Sprint 2:**

6. Reconciliation FAIL explainability (UX-PA-02)
7. Allocation Map Top-3 summary view (UX-PA-05)
8. Remove Phase labels from visible UI text (UX-PA-10)
9. Add INCREASE+REDUCE coexistence explanation (UX-PA-09)

---

### 3. Which Issues Should Become GitHub Backlog Items?

All 13 UX-PA issues should be tracked. Priority grouping:

**Create immediately (P0 — trust-critical):**
- UX-PA-01: Rename "Legacy Alignment"
- UX-PA-02: Reconciliation FAIL explainability
- UX-PA-03: Move PAP/CRA before Security Overlay

**Create for next sprint (P1):**
- UX-PA-04, UX-PA-05, UX-PA-06, UX-PA-07

**Backlog for future (P2–P3):**
- UX-PA-08 through UX-PA-13

---

### 4. Should AI-001 Option B Still Be the Next Implementation Target?

**No — the UX P0 sprint should precede AI-001 Option B.**

Rationale:
- AI-001 Option B adds portfolio compliance validators (M complexity, new Python code)
- UX-PA-01/02/03 are all S complexity and directly address the three highest-trust-impact issues
- The page currently tells an investor/demo audience "Legacy Alignment 41%" and "FAIL" before showing any actionable output — this must be fixed before new validator outputs are added

**Recommended sequence:**
1. UX Sprint 1: PA-01, PA-03, PA-07, PA-06, PA-04 (one session)
2. UX Sprint 2: PA-02, PA-05, PA-10, PA-09
3. AI-001 Option B: Actual Portfolio Compliance Validator
4. PRA-IMPL-06: Conviction Anchor rationalization (if not yet done)
5. AI-003: Allocation Philosophy Narrative

---

### 5. Recommended Roadmap After This Audit

| Phase | Items | Theme | Duration |
|---|---|---|---|
| 1 — UX Trust Sprint | UX-PA-01, 03, 07, 06, 04 | Remove confusion; fix page order | 1 session |
| 2 — UX Clarity Sprint | UX-PA-02, 05, 10, 09, 08 | Deepen explainability | 1–2 sessions |
| 3 — AI-001 Option B | #40 — CPV compliance validator | Governance depth | M |
| 4 — AI-003 | #31 — Allocation philosophy | Explainability content | Needs content |
| 5 — AI-004 | #32 — Policy version diff | Governance enhancement | M |
| 6 — PA-006 | #38 — Drift trend history | Capability expansion | L |

---

## Summary Verdict

The Portfolio Alignment page has **excellent intelligence depth** and **good policy governance** but suffers from **unclear labeling, trust-undermining failure display, and buried execution surfaces**. The three P0 issues can be resolved in a single focused session. After that, the page will be demo-ready and fully operator-ready.

The architecture investments (PRA-IMPL-01 through 05, PA-004, AI-001 Option D) are sound. The remaining work is presentation, not substance.
