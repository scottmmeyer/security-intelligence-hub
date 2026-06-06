# ISSUE-08 — UI Validation Report

**Date:** June 5, 2026  
**Run:** PAR-20260605-BC438F9E  
**Symbol tested:** DELL (rank #1 in deployment queue)

---

## ATI Block — Before and After

### Before ISSUE-08

```
┌──────────────────────────────────────────────────────┐
│ ANALYST TARGET INTELLIGENCE                          │
│ Target       Upside        Sourced                   │
│ $483.83      +20.6%        2026-06-05                │
│ ⚠ Guidance only — not a price forecast              │
└──────────────────────────────────────────────────────┘
```
(Coverage row absent — analyst_count = null)

### After ISSUE-08

```
┌──────────────────────────────────────────────────────┐
│ ANALYST TARGET INTELLIGENCE                          │
│ Target       Upside        Coverage      Sourced     │
│ $483.83      +22.7%        23 analysts   2026-06-05  │
│ ⚠ Guidance only — not a price forecast              │
└──────────────────────────────────────────────────────┘
```
(Coverage row appears — analyst_count = 23)

---

## Browser Validation Checks

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `analyst_consensus_by_symbol['DELL']['analyst_count']` in API | 23 | 23 | ✅ |
| ATI block renders | ✅ | ✅ | ✅ |
| "Coverage" label visible | ✅ | ✅ | ✅ |
| Coverage value | "23 analysts" | "23 analysts" | ✅ |
| Target | "$483.83" | "$483.83" | ✅ |
| Upside | "+22.7%" | "+22.7%" | ✅ |
| Sourced date | "2026-06-05" | "2026-06-05" | ✅ |
| Advisory text | "⚠ Guidance only..." | Exact match | ✅ |
| All 4 items in ATI block | Target + Upside + Coverage + Sourced | 4 items | ✅ |

---

## Recommendation Panel

The `_consensusPanelHtml` function renders the Analyst Consensus section in recommendation card expansions. It receives `ac` (the `analyst_consensus_by_symbol` entry). After ISSUE-08:

- `ac.analyst_count = 23` for DELL
- The panel already references `ac.analyst_count` (pre-wired in prior phases)

**Status:** ✅ analyst_count flows to both the ATI block and the recommendation panel.

---

## Symbols Without Coverage

Symbols where `analyst_count` was not available (no `numberOfAnalystOpinions` in yfinance):

These will continue to have `analyst_count = null`. The ATI block hides the Coverage row gracefully — no "—" placeholder, no empty row. The block still shows Target + Upside + Sourced.

**Verified:** `_dqAnalystTargetHtml({ ..., analyst_count: null })` → no Coverage row rendered.

---

## No Scoring Changes

| System | Status |
|--------|--------|
| Composite score | Unchanged |
| Fundamental Modifier | Unchanged |
| CW-DAS | Unchanged (`CW_DAS_VERSION = "1.1"`) |
| CRA | Unchanged |
| Deployment queue ranking | Unchanged |
