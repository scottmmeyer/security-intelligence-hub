# Recommended Issue Execution Sequence — Phase CII-003

## Prioritization Framework

Issues ranked by: Operator Value × Portfolio Impact × Strategic Importance / Effort

---

## Sequence

### Position 1: ISSUE-07 — Fundamental Conviction Modifier
**GitHub:** #13 | **Labels:** enhancement, fmp, cwdas, priority-high | **Status:** ready (was needs-design)

**Why first:**
- Highest impact on ranking quality (PSX correction)
- Operationalizes the "validates consensus against fundamentals" philosophy
- Design is fully specified — implementation is ready to begin
- Unlocks the CII philosophy's Layer 2 from display-only to consequential

**Effort:** L (5–7 hours including historical validation)

**Gate:** Must include backtest against 6 prior PAR runs and sector calibration

---

### Position 2: ISSUE-08 — Fix analyst_count bug
**GitHub:** Not yet created | **Labels:** bug, provider, data-quality, priority-low, ready

**Why second:**
- 30-minute fix that enables analyst count display in the signal profile grid
- Unlocks the "30 analysts → $484 target" context display (recommended in Phase 8.0B.1C-A)
- No scoring changes — pure data fix
- Can be done as a warmup before or in parallel with ISSUE-07

**Effort:** XS (~30 minutes)

---

### Position 3: ISSUE-05 — Deployment Queue Filter by Thesis Integrity
**GitHub:** #11 | **Labels:** enhancement, ui-ux, priority-medium, ready

**Why third:**
- Labeled `ready` — no design needed
- After ISSUE-07 changes rankings (PSX drops, LRCX rises), being able to filter by INTACT/DETERIORATING thesis becomes immediately useful
- XS effort — can be done in a short session
- Requires ISSUE-07 to be complete first to be fully valuable

**Effort:** XS (1–2 hours)

---

### Position 4: Analyst Target Display Enhancement (new issue)
**GitHub:** Not yet created | **Labels:** enhancement, ui-ux, provider, priority-medium, ready

**Why fourth:**
- After ISSUE-08 fixes analyst_count, displaying `price_target + upside_pct + analyst_count` in the signal profile grid requires only UI wiring
- Recommended in Phase 8.0B.1C-A as high-value display enrichment
- No scoring changes — pure display

**Effort:** S (1–2 hours)

---

### Position 5: ISSUE-04 — Dislocation Watchlist Panel
**GitHub:** #10 | **Labels:** enhancement, ui-ux, fmp, priority-medium, needs-design

**Why fifth:**
- Requires design phase (labeled needs-design)
- After ISSUE-07 changes fundamental modifier, the dislocation classifications may shift for some securities — better to implement this after the scoring stabilizes
- Medium operator value

**Effort:** S–M (2–4 hours)

---

## Deferred (Not in Next 5)

| Issue | Reason for Deferral |
|-------|-------------------|
| CII Modal objective update | Wait for ISSUE-07 certification; update philosophy language then |
| ISSUE-07 analytics monitoring | After 4–6 weeks of production use, assess rank stability |
| Graduated drift penalty | Low urgency (US.SMALL at +3.26% OW — minor) |
| FMP subscription upgrade | Wait for 8.0B.1C findings to confirm what new fields are needed |

---

## Visual Sequence

```
ISSUE-08 (30 min) → ISSUE-07 (5-7 hrs) → ISSUE-05 (1-2 hrs) → Target Display (1-2 hrs) → ISSUE-04 (2-4 hrs)
   ↓                      ↓                    ↓
Fix data bug        Scoring improves      Filters now useful
analyst count       PSX drops             INTACT/DETR filter
visible             LRCX rises            more actionable
```
