# Action Ranking Architecture: Final Recommendation

**Date:** 2026-06-09  
**Context:** PAP/CRA Action Ranking Architecture Audit

---

## The Core Problem

The "Recommended Actions — Top 10" is a **"Top 10 Buys" list** presented under a name that implies comprehensive portfolio action prioritization. Sell, trim, reduce, and rotate actions — however urgent — cannot appear in it under any current code path.

This is not a bug in the policy engine or scoring system. Those components are working correctly. It is a **product surface gap**: the primary operator action view is structurally incomplete.

---

## Options

### Option A: Keep Buy-Only Queue, Rename UI

**Description:** Rename "Recommended Actions — Top 10" to "Top Deployment Candidates" or "Capital Deployment Priority." Add a note that the list shows buy/accumulate opportunities only.

**Pros:**
- No architectural change required
- Honest about scope
- Very low implementation risk

**Cons:**
- The operator still has no unified priority view of all portfolio actions
- The most urgent portfolio action (TSLA TRIM at RPS=85 when unblocked) remains invisible in the primary surface
- Does not address the underlying rotational blind spot

**Implementation effort:** Minimal — 1 label change

---

### Option B: Create Separate Buy and Sell Queues

**Description:** Add a "Reduction Queue" panel alongside the Deployment Queue. The Reduction Queue ranks reduction actions by RPS, showing the operator the top 10 reduction priorities independently. Both queues are shown side-by-side on the page.

**Pros:**
- Operator gets full visibility into both dimensions
- No scoring normalization required — each queue uses its native metric
- Clean separation of intent (deploy cash vs. free capital)
- Low risk — no cross-system score comparison needed
- Consistent with how portfolio managers actually think (buy list + sell list)

**Cons:**
- Does not answer "what is the single most important thing I can do to this portfolio right now?"
- Two lists require more cognitive load than one unified view

**Implementation effort:** Medium — requires CRA/RPS data surfacing in a new DQ-style panel

---

### Option C: Unified Portfolio Action Queue

**Description:** Create a single ranked list where all portfolio actions — buys, trims, sells, rotations — compete on a single priority score. Requires defining a cross-system normalization (e.g., CW-DAS and RPS → normalized 0–100 portfolio impact score).

**Pros:**
- Answers "what is the single most important portfolio action right now?"
- Most operator-aligned design
- Forces explicit thinking about relative urgency (buy VRT vs. trim TSLA)

**Cons:**
- Requires defining a cross-system normalization that doesn't currently exist
- CW-DAS and RPS are measuring different things; naive normalization risks misleading comparisons
- High risk if normalization is wrong: operator could be told "trim TSLA" when the marginal allocation improvement from trimming is smaller than the marginal improvement from buying VRT
- Significant implementation and governance complexity

**Implementation effort:** High — requires new scoring architecture

---

## Recommendation: Option B (Separate Buy and Sell Queues)

**Recommended architecture: Two purpose-specific queues, each using its native ranking metric, presented as a parallel operator view.**

### Rationale

1. **Option A is technically accurate but trust-damaging.** Renaming the list without fixing the surface leaves the operator without reduction action visibility. The problem of "invisible urgent actions" persists.

2. **Option C is architecturally correct but premature.** The normalization required to merge CW-DAS and RPS into a single scale is non-trivial and carries meaningful risk of misleading the operator. The two scores are not directly comparable without a validated weighting model. Building that model requires more empirical validation than is currently available.

3. **Option B is the pragmatic correct answer.** 
   - The DQ already exists as a well-designed buy-side queue
   - The CRA capital sources already produce a well-designed sell-side ranked list
   - What's missing is operator-facing visibility of the sell-side list in the primary surface
   - Option B closes this gap without merging incommensurable metrics

### Concrete Design

**Deployment Queue (Buy Queue):** existing CW-DAS ranked list  
**Reduction Queue (Sell Queue):** new panel showing top 10 reduction candidates from CRA capital sources, ranked by estimated_proceeds × priority weight

Side-by-side or tabbed presentation in the primary surface.

### What Option B Does NOT Do (left for future consideration)

- Does not create a unified "what's the #1 action" answer (requires Option C)
- Does not normalize buy vs. sell urgency into a single score
- Does not replace the PAP recommendation structure

### Label Change (immediate, complementary to Option B)

In parallel with Option B implementation, rename "Recommended Actions — Top 10" to "**Deployment Candidates — Top 10**" to accurately scope the current surface.

---

## Implementation Backlog Items

1. **ARCH-01 (HIGH):** Rename "Recommended Actions — Top 10" → "Deployment Candidates — Top 10" (trivial label fix)
2. **ARCH-02 (MEDIUM):** Surface CRA capital pool as a "Reduction Queue" panel with top 10 reduction candidates, ranked by source_priority + estimated_proceeds
3. **ARCH-03 (LOW, future):** Design and prototype a unified portfolio action scoring model that normalizes CW-DAS and RPS onto a shared impact scale
4. **ARCH-04 (MEDIUM):** Fix KGC DEFERRED propagation artifact — KGC is DEFERRED because DODFX (SELL_LAST) is in the same multi-symbol rec; consider per-symbol execution state in multi-symbol sell recs
