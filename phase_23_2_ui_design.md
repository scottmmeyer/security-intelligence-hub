# Phase 23.2 — UI Design

**Date:** 2026-06-03
**Status:** APPROVED

---

## 1. UI Design Principles

- Policies are additive — they annotate existing intelligence, never replace it
- Intelligence data must remain fully visible regardless of policy
- Policy badges are visually distinct from intelligence flags
- Policy management requires explicit operator action (no implicit policies)
- Policy panel is accessible without triggering a new analysis run

---

## 2. Policy Badge System

Policy annotations appear in the Security Overlay panel and Deployment Queue alongside existing intelligence flags.

### Badge Definitions

| Policy Type | Badge | Color | Location |
|-------------|-------|-------|----------|
| DO_NOT_SELL | `🔒 Operator Protected` | Deep blue border | Overlay card header |
| SELL_LAST | `⏸ Sell Last` | Amber border | Overlay card header |
| CORE_ANCHOR | `⚓ Core Anchor` | Green border | Overlay card header |
| PREFERRED_ACCUMULATION | `⭐ Preferred` | Gold border | Overlay card + queue entry |

Badges appear **alongside** the existing `opportunity_flag` badge, never replacing it.

Example rendering for TSLA:
```
[🔒 Operator Protected] [TRIM]   TSLA   ESS: VERY_BEARISH   Composite: 1.33
```

The intelligence TRIM flag is always shown, even when DO_NOT_SELL is active. This provides governance transparency: the operator can see when their policy diverges from intelligence.

---

## 3. Operator Policy Panel

### Location
A new collapsible panel in the Portfolio Alignment upload section, below the existing Tax Position Panel.

```
[Portfolio Upload]
[Tax Position Panel ▼]
[Operator Policy Panel ▼]   ← NEW (Phase 23.2)
[Analyze]
```

### Panel Header
```
⚙ Operator Portfolio Policies
[Active policies: 2]  [Manage Policies]
```

### Policy List View (collapsed default)

```
Symbol    Policy Type           Rationale              Action
──────────────────────────────────────────────────────────────
TSLA      🔒 DO NOT SELL       Strategic hold         [Edit] [Revoke]
DODFX     ⏸ SELL LAST         Legacy holding         [Edit] [Revoke]
```

### Add Policy Form

```
Add Operator Policy
───────────────────────────────
Symbol:       [TSLA        ▼]   (or text input)
Policy Type:  [DO_NOT_SELL ▼]
  • DO_NOT_SELL — Never appears in sell queue
  • SELL_LAST — Always ranked last in sell queue
  • CORE_ANCHOR — Confirm required before trim
  • PREFERRED_ACCUMULATION — Priority in buy queue
Rationale:    [Long-term strategic position     ]
Expires:      [ ] Set expiration date
              [  date picker  ] (if checked)

[Add Policy]   [Cancel]
```

### Validation Feedback (inline)

- Symbol not in current portfolio: ⚠️ "Symbol not in current portfolio — policy will apply on next upload if symbol present"
- Conflict detected: ❌ "Cannot add SELL_LAST — DO_NOT_SELL policy already active for TSLA"
- Semantic warning: ⚠️ "SELL_LAST and PREFERRED_ACCUMULATION on same symbol — unusual combination"

---

## 4. Security Overlay Card Updates

Each holding card in the Security Overlay panel gains a policy badge row when a policy is active.

### Before (current):
```
┌─────────────────────────────────────────────────┐
│ TSLA                              [TRIM]         │
│ ESS: VERY_BEARISH  Composite: 1.33  Replay: 6.2% │
│ TRIM: weak signal in overweight tier             │
└─────────────────────────────────────────────────┘
```

### After (with DO_NOT_SELL policy):
```
┌─────────────────────────────────────────────────┐
│ TSLA    [🔒 OPERATOR PROTECTED]   [TRIM]         │
│ ESS: VERY_BEARISH  Composite: 1.33  Replay: 6.2% │
│ TRIM: weak signal in overweight tier             │
│ Policy: "Long-term strategic position"           │
│ ⚠ Intelligence recommends TRIM — policy active  │
└─────────────────────────────────────────────────┘
```

The `⚠ Intelligence recommends TRIM — policy active` line appears when the operator's policy diverges from the intelligence recommendation. This is the governance transparency line — it ensures the operator is never passively ignoring a signal.

---

## 5. Deployment Queue UI Updates

The deployment queue table gains a `Policy` column:

### Current Deployment Queue Table
```
Rank  Symbol  Score   Tier              Notes
1     VRT     94.96   CORE_CONVICTION   CCL tier | 33% headroom
2     ARW     88.40   CORE_CONVICTION   ...
```

### Updated Deployment Queue Table
```
Rank  Symbol  Score   Tier              Policy      Notes
1     VRT     94.96   CORE_CONVICTION   ⭐ Preferred  CCL tier | 33% headroom
2     ARW     88.40   CORE_CONVICTION   ⭐ Preferred  ...
...
34    DODFX   —       —                 ⏸ Sell Last  Sell only after others
```

If a symbol has DO_NOT_SELL and would have appeared in a sell/reduction portion, it shows in a separate "Policy-Suppressed" section below the main queue:

```
── Policy-Suppressed (Execution Blocked) ──
TSLA   [🔒 OPERATOR PROTECTED]   Intelligence: TRIM   Policy: DO_NOT_SELL
```

---

## 6. CORE_ANCHOR Confirmation Gate

When the operator clicks to execute a trim recommendation on a CORE_ANCHOR symbol, a modal confirmation dialog appears:

```
⚓ Core Anchor Position — Confirm Trim

SYMBOL: MU
Current policy: CORE ANCHOR
Rationale: "Core anchor — protect from trims"

Intelligence says: MONITOR (RPS 42)
Trim recommendation: Reduce by ~1.5% of portfolio

Are you sure you want to trim this anchor position?

[Cancel — Keep Anchor]   [Confirm Trim]
```

This is a UI-layer gate only — it does not block the operator, it requires acknowledgment.

---

## 7. Policy Divergence Indicator (Global)

A policy divergence indicator appears in the Portfolio Alignment summary header when active policies conflict with intelligence recommendations:

```
Analysis Summary: 34 holdings | 12/13 reconciliation checks PASS
⚠ 1 policy divergence: TSLA (DO_NOT_SELL but intelligence says TRIM)
```

This gives the operator a persistent reminder that active policies are suppressing actions the intelligence engine has recommended.

---

## 8. API Integration (UI → Server)

| Action | HTTP | Endpoint | Payload |
|--------|------|----------|---------|
| Load policies | GET | `/api/operator/policies` | — |
| Add/update policy | POST | `/api/operator/policies` | `{symbol, policy_type, rationale, expires_at?}` |
| Revoke policy | POST | `/api/operator/policies/revoke` | `{symbol}` |
| Load policy for symbol | GET | `/api/operator/policies/{symbol}` | — |

All endpoints follow the existing `portfolio_alignment_state.json` read-merge-write pattern.

---

## 9. Persistence Behavior

- Policies persist across browser refreshes (stored server-side in `portfolio_alignment_state.json`)
- Policies persist across portfolio uploads (symbol-keyed, independent of upload)
- If the symbol is not present in a new upload, the policy is dormant (shown as "inactive" in panel but not deleted)
- Policy panel initializes by calling `GET /api/operator/policies` on page load
- Policy panel renders independently of analysis run results — no run required to view or manage policies

---

## 10. Style Guide for Policy Badges

```css
/* Policy badge base */
.policy-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  margin-right: 4px;
}

/* DO_NOT_SELL */
.policy-badge.do-not-sell {
  background: #1a3a5c;
  color: #a8c7e8;
  border: 1px solid #2c5282;
}

/* SELL_LAST */
.policy-badge.sell-last {
  background: #3d2f00;
  color: #f6d860;
  border: 1px solid #7d5a00;
}

/* CORE_ANCHOR */
.policy-badge.core-anchor {
  background: #1a3d1a;
  color: #74c574;
  border: 1px solid #2d6e2d;
}

/* PREFERRED_ACCUMULATION */
.policy-badge.preferred-accumulation {
  background: #3d3000;
  color: #ffd700;
  border: 1px solid #7a6000;
}

/* Divergence warning row */
.policy-divergence-row {
  color: #f6ad55;
  font-size: 11px;
  margin-top: 4px;
  padding: 3px 6px;
  border-left: 2px solid #f6ad55;
}
```
