# Header Usability Assessment — Phase CII-002

## Problem Statement

The CII methodology ⓘ icon is effectively invisible on the current UI theme.

### Root Cause

```css
/* Previous implementation */
.cii-info-btn {
  background: rgba(255,255,255,0.25);   /* 25% white = nearly transparent */
  color: rgba(255,255,255,0.9);         /* white text */
  border: 1px solid rgba(255,255,255,0.4); /* 40% white border */
}
```

The button was styled for a **dark background** (likely copied from a dark-header pattern). The actual page header uses `--bg: #f3efe6` (warm cream/beige). On this background:
- 25% white overlay → invisible
- White text → barely visible
- White border → invisible

**Contrast ratio: < 2:1 — fails WCAG AA (requires 4.5:1 for text)**

## Options Evaluated

### Option A — Visible Circular Button
Solid circle with accent color background.

**Pros:** Clean, compact  
**Cons:** Small target area (~16px), still may not attract attention

### Option B — Question Mark Pill
`[?]` pill with a distinct color.

**Pros:** Standard UX pattern for "help"  
**Cons:** "?" implies help/documentation rather than methodology identity

### Option C — Text Link: "About CII"
Plain text link with accent color underline.

**Pros:** Maximum discoverability  
**Cons:** Breaks the visual hierarchy of the subtitle; too much text

### Option D — Methodology Pill (SELECTED)
`ⓘ About CII` as a small solid pill button using `--accent` background.

**Pros:**
- Immediately visible — solid teal (#0d5c63) against cream background
- Text label explains purpose ("About CII") — zero ambiguity
- ⓘ icon provides visual cue for information/methodology
- Compact but readable
- Keyboard accessible (button element)
- ARIA label provided

**Cons:** Slightly larger than the previous ⓘ icon (acceptable)

## Recommendation: Option D

The "About CII" pill provides the best balance of visibility, discoverability, and purpose clarity. It satisfies the first-time user requirement: they can immediately see there is methodology context available.
