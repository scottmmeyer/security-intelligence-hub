# Portfolio Alignment — Trust Assessment

Repository: security-intelligence-hub  
Audit Date: 2026-06-09

## Q4 — Sections a First-Time Operator Would Misunderstand

### "Legacy Alignment 41%"

**Misunderstanding:** A first-time operator will ask: "Legacy compared to what? Is 41% bad? Should I try to get to 100%?"

**Reality:** This is the composite allocation alignment score against the strategic target model. 41% means the portfolio is moderately misaligned from targets. But the label "Legacy" is confusing — it implies this metric is deprecated or superseded.

**Impact:** High. This is the most visible number on the page (KPI strip). If the operator mistrusts or misreads it, all downstream decisions are anchored incorrectly.

### "Intentional Asymmetry: HIGH_CONVICTION_ASYMMETRY 87%"

**Misunderstanding:** "Am I supposed to reduce this? Is asymmetry good or bad? What does 87% mean?"

**Reality:** This score validates that the portfolio's concentration pattern is internally consistent with the CONCENTRATED_ALPHA mandate — it is a positive governance signal. But the word "asymmetry" sounds like a risk flag.

**Impact:** Medium. Operator likely ignores it after initial confusion, which is acceptable. But it adds cognitive load.

### "Reconciliation: FAIL (11/13 checks PASS, 1 WARN, 1 FAIL)"

**Misunderstanding:** "The system failed — can I trust this analysis? What failed? Did it affect my recommendations?"

**Reality:** The failure is a data integrity check (likely SPAXX classification or a specific node mapping). It does not affect the recommendation quality for most use cases. But the operator has no way to know this from the display.

**Impact:** High. Trust-critical. A FAIL badge early in the session undermines confidence in every subsequent output.

### Multi-Dimensional Scorecards with no action path

**Misunderstanding:** "I scored 23/100 on Portfolio Quality. What do I do? How do I improve this?"

**Reality:** These scores are diagnostic summaries. There is no direct action the operator can take that maps to "improve Portfolio Quality score." The scores require the operator to already understand the scoring model.

**Impact:** Medium. Operator will likely skip these after first exposure.

### Replay Alignment 58/100 with coverage/quality breakdown

**Misunderstanding:** "58% replay coverage — is this a problem? What does it mean that quality=27.7/40?"

**Reality:** Replay alignment reflects how much of the portfolio has historical evidence backing. 58/100 is acceptable but could improve. The sub-components (coverage and quality) require understanding of what "replay" means in SIH.

**Impact:** Medium. Domain-specific term barrier.

---

## Q5 — Trust Assessment by Section

### Fully Trusted

| Section | Reason |
|---|---|
| Deployment Queue | Transparent ranking, scores visible, clear tie to actionable deployment |
| PAP Cat 1–5 | Clear categories, policy state visible, FVI overlays added |
| Policy Panel | Direct state reflection; what you set is what you see |
| Allocation Map (drift values) | Mathematically verifiable; actual vs target is objective |
| Tax Position Panel | Reflects actual cost basis data |

### Partially Trusted

| Section | Issue |
|---|---|
| KPI "Legacy Alignment 41%" | "Legacy" label erodes trust |
| Multi-Dim Scorecards | No explanation of calculation methodology visible to operator |
| Recommendations (Actions) | BLOCKED recommendations lack "how to unblock" guidance |
| Reconciliation FAIL | FAIL visible but impact on output not explained |
| CRA Proposal | Auto-generated; operator may not understand what triggered the proposal |

### Difficult to Explain (to investors/banks/clients)

| Section | Problem |
|---|---|
| "Legacy Alignment" | Name is unexplainable in a demo context |
| "Intentional Asymmetry" | Sounds like a risk flag, not a quality signal |
| Replay Alignment 58.2/100 | Requires domain knowledge to interpret |
| Phase labels ("Phase C", "Phase 7.3B") | Developer-internal names visible in output |
| "CONCENTRATED_ALPHA" mandate | Industry term but needs a plain-language label for clients |
