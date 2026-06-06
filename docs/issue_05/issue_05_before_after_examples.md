# ISSUE-05 — Before / After Examples

**Date:** June 5, 2026

---

## Before ISSUE-05

The Deployment Queue panel header showed:

```
[Capital Deployment Queue]  [CW-DAS-1.1]        Guidance only — not a trade instruction
```

No filtering capability. Operators had to scroll through all 32+ candidates to find INTACT, high-quality opportunities or manually identify which had negative modifiers from the score breakdown.

---

## After ISSUE-05

The panel header now shows:

```
[Capital Deployment Queue]  [CW-DAS-1.1]  [Thesis ▾]  [Consistency ▾]  [Modifier ▾]   Guidance only — not a trade instruction
```

---

## Example 1: Isolate Negative Modifier Names

**Use case:** Operator wants to review which holdings have deteriorating fundamentals hurting their CW-DAS rank.

**Steps:**
1. Click `[Modifier ▾]`
2. Select "Negative (<0)"
3. Panel shows Modifier badge in accent color

**Result:** Table shows only the 6 candidates with `fundamental_modifier < 0`. These are the names where thesis deterioration or earnings miss patterns are suppressing rank. Operator can assess whether to hold, trim, or investigate further.

---

## Example 2: Isolate High-Quality Opportunities

**Use case:** Operator wants INTACT fundamentals with CONSISTENT earnings — the safest deployment targets.

**Steps:**
1. Click `[Thesis ▾]` → uncheck QUESTIONABLE, DETERIORATING
2. Click `[Consistency ▾]` → uncheck MIXED, CONTRADICTORY, DATA ANOMALY
3. Click `[Modifier ▾]` → select "Positive (>0)"

**Result:** Table shows "X of 32" badge. Only candidates with INTACT thesis, CONSISTENT fundamentals, and a positive conviction boost. These represent the highest-quality CII-confirmed deployment targets.

---

## Example 3: View-All with Filters Active

**Use case:** There are more filtered candidates than the 10-row default.

**Steps:**
1. Apply Modifier = Positive (26 match in test queue)
2. View-all button shows "▼ View all 26 candidates" (not 32)
3. Click to expand

**Result:** All 26 positive-modifier candidates shown in original rank order. Ranking is unchanged — the #1 candidate is still #1 regardless of which filter is active.

---

## Example 4: Filter Reset

**Steps:**
1. Apply any filter combination
2. Click `[Thesis ▾]` → check all options back to default
3. Click `[Modifier ▾]` → select "All"

**Result:** Table returns to default 10-row view of all 32 candidates. Count badge disappears. All filter badges revert to default (non-accent) style.

---

## Key Invariants (Before = After)

| Property | Before | After |
|---|---|---|
| CW-DAS scores | Unchanged | Unchanged |
| Rank #1 | DELL (or whatever it is) | DELL — same rank |
| Score values | Unchanged | Unchanged |
| Deployment recommendations | Unchanged | Unchanged |
| All 32 candidates in queue | Present | Present (filtering is view-only) |
