# CII Modal Update Proposal — Phase CII-004

## Changes Recommended

### Change 1: Version Badge

**Current:** `Methodology Version: CII v1.0`  
**Proposed:** `Methodology Version: CII v1.1`  
**Rationale:** CW-DAS advanced from v1.0 to v1.1 (ISSUE-07). The modal should reflect the current certified architecture version.

---

### Change 2: Main Statement

**Current:**
> "Consensus Intelligence Investing (CII) is a portfolio construction methodology that begins with professional analyst consensus, validates that consensus against business fundamentals and historical evidence, scores opportunities using an internal conviction framework, and deploys capital through a risk-managed model designed to maximize long-term portfolio growth."

**Proposed:**
> "Consensus Intelligence Investing (CII) is a portfolio construction methodology that begins with professional analyst consensus, validates that consensus against business fundamentals and historical evidence — with fundamental quality actively adjusting conviction scores — and deploys capital through a risk-managed framework designed to generate superior long-term risk-adjusted returns."

**Changes:**
- "scores opportunities using an internal conviction framework" → "with fundamental quality actively adjusting conviction scores" (more accurate post-ISSUE-07)
- "maximize long-term portfolio growth" → "generate superior long-term risk-adjusted returns" (matches the established Objective language; risk-adjusted is more precise)

---

### Change 3: Layer 2 Purpose Text

**Current:** `Validate whether business fundamentals support the consensus.`  
**Proposed:** `Validate whether business fundamentals support the consensus, and adjust conviction scores accordingly.`  
**Rationale:** Pre-ISSUE-07, Layer 2 was informational only. Post-ISSUE-07, it actively adjusts the CW-DAS score via the fundamental modifier (±3/−5 range). The word "accordingly" conveys consequence without specifying the mechanism.

---

### Change 4: Objective Section

**Current:**
> "Identify and allocate capital toward opportunities where analyst consensus, business fundamentals, historical evidence, and portfolio discipline align most favorably in pursuit of superior long-term risk-adjusted returns."

**Proposed:**
> "Identify and allocate capital toward high-conviction opportunities where analyst consensus, business fundamentals, historical evidence, and portfolio discipline align most favorably — while systematically reducing allocation errors where consensus has outrun business reality — in pursuit of superior long-term risk-adjusted returns."

**Changes:** Added error-reduction clause; added "high-conviction" qualifier.

---

### Change 5: Fundamental Confirmation Alpha Description

**Current:** `"Validates whether business performance supports the prevailing market narrative, reducing exposure to deteriorating theses."`

**Proposed:** `"Validates whether business performance supports the prevailing market narrative, and actively reduces conviction in deteriorating theses through the Fundamental Modifier."`

**Rationale:** The current text says "reducing exposure" which implies a soft display-only reduction. Post-ISSUE-07 this is operationalized via the fundamental modifier (up to −5.0 pts for DETERIORATING + CONTRADICTORY). Adding "actively reduces conviction" and naming the mechanism makes this accurate and transparent.

---

## Not Changed

| Element | Reason |
|---------|--------|
| Header subtitle: "Where Analyst Consensus Meets Portfolio Discipline" | Still accurate; no change needed |
| Layer 1, 3, 4 descriptions | Unchanged architecture; no update needed |
| "Why CII Exists" box | Accurate; no update needed |
| Source pills | Unchanged; no update needed |
| Advisory footer | Unchanged |

---

## Implementation Note

All proposed changes are text-only updates to `ui/portfolio_alignment/index.html`. No new CSS, no new JS, no scoring changes. A single version bump of the HTML file is sufficient.

Recommended to implement in a single commit with message:
`docs: CII modal v1.1 — update Layer 2, statement, and objective for ISSUE-07 architecture`
