# Backlog Disposition Recommendation

Repository: security-intelligence-hub  
Date: 2026-06-09  
Context: Post-PRA-IMPL-03 implementation

## PA-001 Recommendation Stream Overload (#33)

**Current status:** RESOLVED

PRA-IMPL-03 directly and completely addresses PA-001:
- The primary recommendation stream now contains only 3 executable ACTION cards
- All 30 non-action cards are routed to dedicated lanes
- Conviction Anchors, Portfolio Narrative, and Explainability are separated

**Recommendation: Close PA-001 with comment linking PRA-IMPL-03 commit.**

Residual: The conviction anchor section still has usability friction (25 items). This is addressed by the new PRA-IMPL-06 assessment, not by keeping PA-001 open.

---

## PA-002 Recommendation Ordering Defect (#34)

**Current status:** RESOLVED

PRA-IMPL-03 directly addresses PA-002:
- Actions appear at the top of the recommendation panel as the first visible lane
- Blocked/Deferred appear immediately after Actions (also expanded by default)
- Conviction Anchors, Narrative, and Explainability are collapsed below

The prior interleaving defect no longer exists. There is no non-action content visible in the primary view by default.

**Recommendation: Close PA-002 with comment linking PRA-IMPL-03 commit.**

---

## PA-003 Recommendation Count Inflation (#35)

**Current status:** RESOLVED

PRA-IMPL-03 directly addresses PA-003:
- KPI strip now shows typed counts: "3 Actions · 3 Blocked · 25 Anchors · 1 Narratives · 1 Explain"
- Primary KPI is now action count (3), not aggregate count (33)
- "Total cards: 33" remains accessible but is not the primary headline

The inflation problem is eliminated. The 11× overstatement is corrected.

**Recommendation: Close PA-003 with comment linking PRA-IMPL-03 commit.**

---

## Closure Comments Template

For all three issues:

> "Resolved by PRA-IMPL-03 (recommendation surface lane separation and typed counts). 
> Commit: [commit hash]. 
> - PA-001: Actions lane now contains only 3 executable cards; 30 non-action cards routed to dedicated lanes.
> - PA-002: Actions lane is first and always expanded; non-action lanes are collapsed by default.
> - PA-003: KPI strip shows typed counts per lane; primary headline is 3 Actions, not 33 Recommendations.
> 
> Residual conviction anchor usability improvement (25-item flat list) tracked in PRA-IMPL-06 assessment."

---

## Issues That Remain Open After PRA-IMPL-03

| Issue | Status | Reason |
|---|---|---|
| PA-004 Policy Consistency Failure (#36) | OPEN | PAP surface still not normalized — requires separate PAP investigation |
| PA-005 Conviction Explainability Placement (#37) | PARTIALLY ADDRESSED | Cards are now in Conviction Anchors lane, but the lane UX needs further refinement (PRA-IMPL-06 scope) |
| PA-006 Allocation Drift Trend (#38) | OPEN | New capability; no infrastructure yet |
| AI-001 through AI-004 | OPEN | Allocation Intelligence issues; separate scope |
