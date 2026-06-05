# 09 — Consensus Intelligence Methodology Final Verdict

## Verdict

**APPROVED**

---

## Final Question Answers

### Q1: What investment methodology does SIH represent?

**Consensus Intelligence Investing (CII)** — a distinct, four-layer methodology that uses professional analyst consensus as its primary input, validates that consensus against business fundamentals and historical performance, and disciplines capital deployment through systematic portfolio construction.

SIH does not fit neatly into growth, value, momentum, quality, quantitative, or consensus-following as defined by traditional investment categories. It borrows elements from each but is defined by the combination of all four layers operating as a coherent system.

---

### Q2: Is "Consensus Intelligence Investing" an accurate description?

**Yes — with one important precision.**

"Consensus" is accurate because the primary signal layer (Layer 1) aggregates professional analyst consensus across ESS, Zacks, and Danelfin.

"Intelligence" is the critical modifier — it distinguishes SIH from passive consensus-following. SIH does not follow consensus; it interrogates it. The intelligence is in the validation (Layer 2), the empirical gate (Layer 3), and the portfolio discipline (Layer 4).

"Investing" positions this as a methodology, not just a tool.

**Official name adopted:** Consensus Intelligence Investing (CII)  
**Short form:** Consensus Intelligence  
**Product name:** Security Intelligence Hub (SIH)

---

### Q3: What differentiates SIH from traditional analyst-following?

Three structural differences:

1. **Validation:** SIH checks whether business fundamentals support the consensus before deploying capital. A persistently BULLISH rating on a deteriorating business is flagged, not followed.

2. **Historical Gate:** The Replay requirement means every deployment candidate must have a historical precedent. Narrative without history does not enter the deployment queue.

3. **Portfolio Discipline:** Traditional analyst-following provides no portfolio construction framework. SIH enforces position sizing limits, allocation target alignment, concentration controls, and capital rotation intelligence.

---

### Q4: What differentiates SIH from purely quantitative investing?

Three structural differences:

1. **Explainability:** Every SIH score is decomposed into components that the operator can understand and evaluate. No black box.

2. **Human Authority:** The operator is the final decision-maker. Policies, overrides, and manual exclusions encode operator judgment directly into the system. Autonomy is advisory, not autonomous.

3. **Consensus as Primary:** Traditional quant investing uses mathematical factor models derived from historical return data. SIH uses professional human analyst consensus as its primary evidence layer — acknowledging that human expert judgment contains information that price history alone cannot capture.

---

### Q5: What name should be adopted officially?

**Consensus Intelligence Investing (CII)**

- Primary documentation name
- Institutional/advisor-facing description
- Abbreviation: CII

Short form for UI use: **Consensus Intelligence**

Product name remains: **Security Intelligence Hub (SIH)**

---

### Q6: What tagline should appear in the UI?

**Primary:** `Where Analyst Consensus Meets Portfolio Discipline`

**Full subtitle (recommended for header):**  
`Portfolio Alignment Analysis · Where Analyst Consensus Meets Portfolio Discipline · Advisory intelligence only — not trade execution`

**Alternate for shorter contexts:** `Consensus Validated. Conviction Built. Capital Deployed.`

---

### Q7: Should this philosophy become a governed document?

**Yes — emphatically.**

The methodology documents in `docs/methodology/` should be treated as governance anchors. Proposed changes to the system should be evaluated against the core beliefs and framework layers documented here.

Specifically:
- Any change to Layer 1 (consensus composition) requires justification against Core Belief 1
- Any removal of the Replay gate (Layer 3) requires explicit override of Core Belief 4
- Any change to portfolio discipline (Layer 4) requires CW-DAS trace update
- Any addition of autonomous execution capability violates Core Belief 9 and requires explicit authorization

The `docs/methodology/` directory is the canonical reference. Phase documents, phase deliverables, and GitHub Issues should link to it.

---

## Methodology Summary Card

```
╔══════════════════════════════════════════════════════════════╗
║         CONSENSUS INTELLIGENCE INVESTING (CII)               ║
║         Security Intelligence Hub                            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Layer 1   ANALYST CONSENSUS                                 ║
║            ESS · Zacks · Danelfin · Yahoo ABR                ║
║            What the professional community believes          ║
║                                                              ║
║  Layer 2   FUNDAMENTAL VALIDATION                            ║
║            Revenue · ROIC · Beat Rate · Revisions            ║
║            Whether the business supports the consensus       ║
║                                                              ║
║  Layer 3   HISTORICAL VALIDATION (Replay)                    ║
║            Empirical evidence from historical portfolios     ║
║                                                              ║
║  Layer 4   PORTFOLIO DISCIPLINE                              ║
║            CW-DAS · Allocation Targets · CRA                 ║
║            Capital deployed intelligently                    ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  "Where Analyst Consensus Meets Portfolio Discipline"        ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Classification

**APPROVED**

Phase 8.0B.1E is complete. The Consensus Intelligence Investing methodology is formally documented. No code changes. No scoring changes. Governance documentation only.

Next authorized action: Implement the tagline update (ISSUE: "[UI] Add methodology tagline to Portfolio Alignment header subtitle") as a quick follow-on.
