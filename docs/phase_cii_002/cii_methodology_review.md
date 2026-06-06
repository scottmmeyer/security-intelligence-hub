# CII Methodology Review — Phase CII-002

## Review of Previous Modal Content (CII-001)

### What Was Present
- Title: Consensus Intelligence Investing / Methodology Version: CII v1.0
- Statement (italic): definition paragraph
- Four-Layer Framework (4 cards)
- Objective: "Identify opportunities where... align most favorably."
- Footer: advisory disclaimer

### Identified Gaps

| Gap | Severity | Notes |
|-----|---------|-------|
| No explanation of WHERE alpha comes from | MEDIUM | Modal explains HOW but not WHY it generates returns |
| Objective text does not mention risk-adjusted returns | LOW | Misses the ultimate investment purpose |
| No "Why CII Exists" philosophy section | MEDIUM | First-time users lack context for the system's purpose |
| ⓘ button nearly invisible on light theme | HIGH | Button used rgba(255,255,255,0.25) background on --bg: #f3efe6 — effectively invisible |

### Previous Header Button
```css
.cii-info-btn {
  background: rgba(255,255,255,0.25);  /* invisible on light background */
  color: rgba(255,255,255,0.9);        /* white text on light bg = invisible */
  border: 1px solid rgba(255,255,255,0.4); /* invisible border */
}
```
This was designed for a dark navbar. On the actual cream/warm beige background it was effectively transparent.

## Changes Applied in CII-002

1. **Expected Sources of Alpha** — new section with 4 alpha sources
2. **Objective** — enhanced to include "superior long-term risk-adjusted returns"
3. **Why CII Exists** — new philosophy box with 2-paragraph rationale
4. **About CII pill** — replaced invisible ⓘ with a teal solid pill button
