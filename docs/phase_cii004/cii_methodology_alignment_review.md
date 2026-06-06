# CII Methodology Alignment Review — Phase CII-004

## Context
ISSUE-07 (Fundamental Conviction Modifier) was certified complete on June 5, 2026.
CW-DAS version advanced from 1.0 to 1.1.
Layer 2 (Fundamental Validation) now influences ranking through a bounded modifier.

---

## Review Scope

### 1. CII Modal

**Location:** `ui/portfolio_alignment/index.html`

| Section | Current State | Post-ISSUE-07 Accuracy | Action Required |
|---------|--------------|----------------------|-----------------|
| Version badge | "CII v1.0" | ❌ CW-DAS is v1.1 | UPDATE: "CII v1.1" |
| Statement | "validates that consensus against business fundamentals... scores opportunities using an internal conviction framework" | ⚠️ Partially accurate — "scores" is vague; doesn't say validation influences ranking | UPDATE: explicitly state validation adjusts ranking |
| Layer 2 purpose | "Validate whether business fundamentals support the consensus." | ⚠️ Understates — implies display-only; now actively adjusts conviction | UPDATE: "Validate and adjust conviction based on business fundamentals." |
| Layer 2 sources | ESS pill absent; "Revenue Growth, ROIC, Beat Rate, FCF Yield, Revisions" | ✅ Accurate | No change needed |
| Objective | "...where analyst consensus, business fundamentals, historical evidence, and portfolio discipline align most favorably..." | ⚠️ Missing error-reduction language; missing "validation-adjusted ranking" | UPDATE |
| Fundamental Confirmation alpha | "reduces exposure to deteriorating theses" | ✅ Accurate; ISSUE-07 operationalizes this | MINOR: can add "now actively adjusts conviction" |
| Why CII Exists | General statement | ✅ Accurate | No change needed |

### 2. Methodology Documentation

**Location:** `docs/methodology/`

| Document | Status |
|---------|--------|
| `02_consensus_intelligence_framework.md` | Layer 2 described as display-only → NEEDS UPDATE post-ISSUE-07 |
| `03_core_beliefs.md` | Belief 3, 5 still accurate; Belief 2 (error reduction) now operationalized → ADD note |
| `09_final_verdict.md` | States "display-only enrichment" for fundamentals → OUTDATED |
| Others | Accurate; no changes needed |

### 3. Company Context Screens

The Fundamental Snapshot panel (Phase 8.0B.1B.5) already shows Thesis Integrity and Fundamental Consistency labels. These are display-accurate.

The "Why SIH Likes It" section now includes fundamental modifier bullets ("Fundamental bonus +X.X" / "Fundamental penalty −X.X") — these are post-ISSUE-07 additions and are accurate.

**Assessment: Company context screens are accurate post-ISSUE-07.** No UI changes needed here.

### 4. Portfolio Alignment Header Subtitle

Current: "Where Analyst Consensus Meets Portfolio Discipline"

**Assessment: Still accurate.** This tagline describes the relationship between inputs and outputs; it does not imply fundamentals are absent. No change required.

### 5. CW-DAS Score Breakdown Grid

The breakdown grid now shows "Fund. Mod" when `fundamental_modifier ≠ 0`. This is correct and transparent. No changes needed.

---

## Summary: What Requires Updating

| Item | Priority | Change Type |
|------|---------|-------------|
| Version badge: v1.0 → v1.1 | HIGH | Minor text |
| Modal statement: add validation-adjusts-ranking language | HIGH | Language update |
| Layer 2 purpose text | HIGH | Purpose description update |
| Objective statement | MEDIUM | Language enhancement |
| `docs/methodology/02_consensus_intelligence_framework.md` Layer 2 section | MEDIUM | Documentation update |
| Fundamental Confirmation alpha description | LOW | Minor enhancement |

---

## Q1: Does current methodology language remain accurate?

**PARTIALLY.** The language is not wrong, but it is now incomplete. "Validates that consensus against business fundamentals" (in docs) and "Validate whether business fundamentals support the consensus" (in modal) imply a passive check. ISSUE-07 made this active — fundamentals now influence the ranking score.

The statement "scores opportunities using an internal conviction framework" is vague — it doesn't convey that the conviction framework now incorporates fundamental quality.

## Q2: What wording should be updated?

1. "validates" → "validates and adjusts conviction based on"
2. Layer 2 purpose: add "and adjust conviction accordingly"
3. Statement: add "with fundamental quality influencing conviction adjustments"
4. Version: v1.0 → v1.1

## Q3: Should CII explicitly reference error reduction?

**YES** — and it partially already does via the "Fundamental Confirmation" alpha source ("reduces exposure to deteriorating theses"). After ISSUE-07 this should be updated to note this is now operationalized, not just conceptual.

## Q4: Should CII explicitly reference validation-adjusted ranking?

**YES** — the modal statement and Layer 2 purpose should make clear that fundamental validation now influences the deployment queue ranking, not just provides a display label.

## Q5: Does ISSUE-07 change the source of alpha?

**NO.** Consensus (Layer 1) remains the primary alpha source. ISSUE-07 adds an error-reduction mechanism that improves decision quality by downweighting deteriorating-thesis candidates. It does not create a new independent alpha source — it validates and refines the consensus signal.

## Q6: Does ISSUE-07 change portfolio construction philosophy?

**NO.** The philosophy is unchanged:
- Consensus first
- Fundamental validation
- Historical validation
- Portfolio discipline

ISSUE-07 operationalizes step 2 (validation) into step 4 (portfolio discipline via CW-DAS scoring). It is a completion of the intended architecture, not a change to it.

## Q7: What exact wording should replace the current objective statement?

See `cii_objective_statement_recommendation.md`.

## Q8: Should any UI text be updated?

**YES:** Modal version badge, modal statement, Layer 2 purpose text. See `cii_modal_update_proposal.md`.
