# Phase 23.3 — UI Behavior Review

**Status:** IMPLEMENTED  
**Date:** 2026-06-03

---

## PAP Section Changes

### Category 1: Signal Deterioration — Updated

**Before Phase 23.3:**
- All signal-deteriorated holdings appeared in Cat 1 as `HIGH PRIORITY`
- No distinction between executable and blocked actions
- TSLA would show: `TRIM | HIGH PRIORITY` alongside `DO_NOT_SELL` policy badge

**After Phase 23.3:**

| Column | Before | After |
|--------|--------|-------|
| Symbol | ✓ | ✓ |
| ESS Signal | ✓ | ✓ |
| Flag | ✓ | ✓ (original intelligence flag preserved) |
| Score | ✓ | ✓ |
| % Port | ✓ | ✓ |
| Priority | ✓ | ✓ (DEFERRED items shown at tail) |
| Policy | — | **NEW**: badge (🔒 / ⏸ / ⚓ / ⭐) or `—` |
| Effective Action | — | **NEW**: EXECUTABLE badge or overridden action |
| Rationale | ✓ | ✓ |

**Row behavior by execution_state:**

| State | Row Style | Action Column |
|-------|-----------|---------------|
| `EXECUTABLE` | Normal / `pap-row-high` for HIGH | Original flag (green badge) |
| `DEFERRED_BY_POLICY` | `pap-row-deferred` (muted yellow), sorted to bottom | `TRIM_SELL_LAST` (amber badge) |
| `INFORMATIONAL_ONLY` | `pap-row-info-only` (light blue) | `MONITOR_ONLY` (blue badge) |
| `BLOCKED_BY_POLICY` | **Removed from Cat 1** — moves to Cat 5 | — |

---

### Category 5: Policy-Suppressed Actions — NEW

A new collapsible section added after Cat 4 (Funding Sources).

**Appears when:** One or more positions have `BLOCKED_BY_POLICY` execution state.

**Header:** 🔒 Policy-Suppressed Actions (red accent border)

**Columns:**

| Column | Description |
|--------|-------------|
| Symbol | Affected symbol |
| ESS Signal | Intelligence signal (BEARISH / VERY_BEARISH) |
| Original Action | What intelligence would have recommended (TRIM, REDUCE_CANDIDATE) |
| Policy | Policy badge (🔒 DO NOT SELL) |
| Effective Action | `MONITOR_ONLY` (red badge) |
| Score | Composite score |
| % Port | Portfolio weight |

**Explanatory text displayed above table:**
> These positions have intelligence signals that would normally trigger action,
> but are blocked by operator policy. No execution action should be taken.
> Intelligence is preserved for monitoring purposes only.

---

## Badge Visual Reference

| execution_state | Badge Color | Text |
|----------------|-------------|------|
| `EXECUTABLE` | Green | Original flag text |
| `BLOCKED_BY_POLICY` | Red | `MONITOR_ONLY` |
| `DEFERRED_BY_POLICY` | Amber | `{FLAG}_SELL_LAST` |
| `INFORMATIONAL_ONLY` | Blue | `MONITOR_ONLY` |

---

## Policy Badge Reference (unchanged from 23.2)

| Policy Type | Badge |
|-------------|-------|
| `DO_NOT_SELL` | 🔒 Operator Protected |
| `SELL_LAST` | ⏸ Sell Last |
| `CORE_ANCHOR` | ⚓ Core Anchor |
| `PREFERRED_ACCUMULATION` | ⭐ Preferred Accumulation |

---

## Sort Order — Cat 1

1. `DEFERRED_BY_POLICY` items sorted to bottom of Cat 1
2. Within non-deferred: HIGH priority first
3. Within same priority: composite_score ascending (weakest first)

---

## CSS Classes Added (index.html)

| Class | Usage |
|-------|-------|
| `.pap-row-deferred` | SELL_LAST deferred rows (muted yellow background) |
| `.pap-row-info-only` | CORE_ANCHOR informational rows (light blue) |
| `.pap-row-suppressed` | Cat 5 blocked rows |
| `.pap-cat-suppressed` | Cat 5 category container (red border) |
| `.pap-exec-action` | Base class for effective action badges |
| `.pap-exec-EXECUTABLE` | Green action badge |
| `.pap-exec-BLOCKED_BY_POLICY` | Red action badge |
| `.pap-exec-DEFERRED_BY_POLICY` | Amber action badge |
| `.pap-exec-INFORMATIONAL_ONLY` | Blue action badge |

---

## Cache Version

`app.js?v=9` — incremented from v=8 to force browser cache refresh.
