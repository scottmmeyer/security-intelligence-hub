# ISSUE-05 — Filter Behavior Matrix

**Date:** June 5, 2026

---

## Thesis Filter Behavior

| Filter State | INTACT rows | QUESTIONABLE rows | DETERIORATING rows | Empty/Unknown rows |
|---|---|---|---|---|
| All selected (default) | ✅ visible | ✅ visible | ✅ visible | ✅ visible (pass-through) |
| INTACT only | ✅ visible | ✗ hidden | ✗ hidden | ✅ visible (pass-through) |
| QUESTIONABLE only | ✗ hidden | ✅ visible | ✗ hidden | ✅ visible (pass-through) |
| DETERIORATING only | ✗ hidden | ✗ hidden | ✅ visible | ✅ visible (pass-through) |
| INTACT + QUESTIONABLE | ✅ visible | ✅ visible | ✗ hidden | ✅ visible (pass-through) |
| None selected | All hidden | All hidden | All hidden | ✅ visible (pass-through) |

_Pass-through: candidates with empty or unrecognized thesis_integrity are never hidden by the thesis filter. This preserves backward compatibility with pre-ISSUE-05 artifacts._

---

## Fundamental Consistency Filter Behavior

| Filter State | CONSISTENT | MIXED | CONTRADICTORY | DATA_ANOMALY | Empty/Unknown |
|---|---|---|---|---|---|
| All selected (default) | ✅ | ✅ | ✅ | ✅ | ✅ (pass-through) |
| CONSISTENT only | ✅ | ✗ | ✗ | ✗ | ✅ (pass-through) |
| CONTRADICTORY only | ✗ | ✗ | ✅ | ✗ | ✅ (pass-through) |

---

## Modifier Filter Behavior

| Filter State | modifier > 0 | modifier = 0 | modifier < 0 |
|---|---|---|---|
| All (default) | ✅ visible | ✅ visible | ✅ visible |
| Positive only | ✅ visible | ✗ hidden | ✗ hidden |
| Neutral only | ✗ hidden | ✅ visible | ✗ hidden |
| Negative only | ✗ hidden | ✗ hidden | ✅ visible |

_Modifier polarity is computed from the numeric `score_breakdown.fundamental_modifier` value at filter time. No string field needed._

---

## Combined Filter Logic

Filters are `AND`-joined:
```
show_row = thesis_passes AND consistency_passes AND modifier_passes
```

Each dimension is independent. A row must satisfy all active filter conditions to appear.

---

## Badge Activation

| Condition | Badge State |
|---|---|
| All options selected (default) | No badge (btn shows default style) |
| One or more options deselected | `dq-filter-active` class added (accent color) |
| Modifier = "ALL" | No badge |
| Modifier ≠ "ALL" | `dq-filter-active` class added |

---

## Preserved Values (Never Modified by Filters)

| Field | Preserved |
|---|---|
| `rank` | ✅ unchanged |
| `deployment_score` | ✅ unchanged |
| `score_breakdown.*` | ✅ unchanged |
| `narrative_tier` | ✅ unchanged |
| `replay_supported` | ✅ unchanged |
| `notes` | ✅ unchanged |
| All recommendation logic | ✅ unchanged |
