# 07 — UI Integration Recommendation

## Where the Methodology Should Appear

### 1. Application Header Subtitle

**Location:** `ui/portfolio_alignment/index.html` — the `<p class="subtitle">` below the main heading

**Current text:**  
`Portfolio Alignment Analysis · Advisory intelligence only — not trade execution`

**Proposed text:**  
`Portfolio Alignment Analysis · Where Analyst Consensus Meets Portfolio Discipline · Advisory intelligence only — not trade execution`

**Alternative (shorter):**  
`Consensus Intelligence · Portfolio Alignment Analysis · Advisory intelligence only`

**Rationale:** The subtitle is the first text an operator reads after the product name. Adding a methodology reference immediately positions the system's intent.

---

### 2. Portfolio Analysis Page Subheading

**Location:** `ui/portfolio_alignment/index.html` — below the "Portfolio Upload" section header

**Proposed addition (small text, muted):**  
`Consensus Validated · Conviction Built · Capital Deployed`

---

### 3. Report Footer (Exported Reports)

**When export is implemented (Phase 23.6C):**

**Footer line:**  
`Security Intelligence Hub · Consensus Intelligence Investing · Advisory intelligence only — not financial advice`

---

### 4. Methodology Modal / About Dialog

**New UI element (low effort):** A small `?` or `ⓘ` icon in the header that opens a brief methodology reference panel.

**Proposed panel content:**

```
CONSENSUS INTELLIGENCE INVESTING

SIH uses a four-layer investment framework:

1. Analyst Consensus — What professionals believe (ESS, Zacks, Danelfin)
2. Fundamental Validation — Whether the business supports the consensus (FMP)
3. Historical Validation — Whether similar configurations have worked before (Replay)
4. Portfolio Discipline — How to deploy capital intelligently (CW-DAS, CRA)

Signals tell you what. Fundamentals tell you why.

All recommendations are advisory only — not trade execution instructions.
```

---

### 5. Deployment Queue Card Expansion

**Location:** Below the "Company Snapshot" section, above the signal grid

**Not as a full section** — as a small badge at the top of the expanded card:

```html
<span class="cii-badge">Consensus Intelligence</span>
```

This subtly reinforces the methodology context each time a card is expanded. Implementation is optional and low-priority.

---

### 6. Documentation Header

**All methodology documents in `docs/methodology/`** should include a consistent header:

```markdown
> **Security Intelligence Hub — Consensus Intelligence Investing (CII)**  
> This document is part of the official SIH investment methodology.
```

---

## Exact Proposed UI Text (Immediately Actionable)

### Option A — Minimal Change (Recommended for Now)

In `index.html`, replace the subtitle paragraph:

```html
<p class="subtitle">
  Portfolio Alignment Analysis &nbsp;·&nbsp;
  Where Analyst Consensus Meets Portfolio Discipline &nbsp;·&nbsp;
  Advisory intelligence only — not trade execution
</p>
```

This is a single-line change. No functional impact. Immediately communicates the methodology to every user who opens the application.

### Option B — Full Implementation (Phase 8.0B.1E.1)

When the About dialog is built:

1. Add `ⓘ` icon to header (right side)
2. Add modal with 4-layer framework description (text above)
3. Add footer methodology reference

**Effort estimate:** S (2–3 hours)

---

## Non-Negotiables for UI Integration

- No scoring changes
- No ranking changes
- No functional changes to any analytical pipeline
- Tagline changes are purely display text
- About dialog is informational only — no links to recommendations
