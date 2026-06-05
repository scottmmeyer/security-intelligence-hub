# CII Methodology Panel — Design Document

## Issue Reference
CII-001: Methodology Awareness Panel

## Objective
Add an information button (ⓘ) to the Portfolio Alignment header that opens a modal explaining the Consensus Intelligence Investing methodology to operators, advisors, or first-time users.

## Design Decisions

### Trigger Placement
**Location:** Inline within the header subtitle, immediately after "Where Analyst Consensus Meets Portfolio Discipline"

**Rationale:** The tagline IS the methodology reference — placing ⓘ directly adjacent creates a natural information hierarchy. An operator reading the subtitle can immediately get more context.

**HTML:**
```html
<p class="subtitle">
  Portfolio Alignment Analysis ·
  Where Analyst Consensus Meets Portfolio Discipline
  <button class="cii-info-btn" onclick="_openCIIModal()" title="About Consensus Intelligence Investing">ⓘ</button>
  · Advisory intelligence only — not trade execution
</p>
```

### Modal Design
**Type:** Fixed-position overlay with backdrop blur  
**Max width:** 560px  
**Max height:** 90vh with scroll  
**Position:** Centered  
**z-index:** 9000 (above all content, below browser chrome)

### Close Mechanisms
1. **× button** (top right) — explicit close
2. **Backdrop click** — clicking outside the modal card closes it
3. **Escape key** — keyboard accessibility

### Content Structure
1. Title: "Consensus Intelligence Investing"
2. Version: "Methodology Version: CII v1.0"
3. Official statement (italicized, left-bordered)
4. Four-Layer Framework (4 cards, each with layer number, title, purpose, source pills)
5. Objective (plain text with bold emphasis)
6. Footer (legal / advisory note)

### Visual Language
- Layer cards: warm background (`#f9f6f0`) matching Company Snapshot cards — consistent visual language
- Source pills: blue pill design matching business model tags — consistent with system-wide badge style
- Statement border: left bar using `--accent` color (brand-consistent)
- Footer: muted, legal-weight text

### Non-Negotiable Constraints
- No links to external sites
- No scoring information in modal
- No price targets, buy/sell recommendations
- Advisory disclaimer in footer
- No code changes to scoring, ranking, or recommendation pipeline

## Files Modified
- `ui/portfolio_alignment/index.html` — CSS, modal HTML, subtitle update, v17 bump
- `ui/portfolio_alignment/app.js` — `_openCIIModal()`, `_closeCIIModal()`, Escape key listener
