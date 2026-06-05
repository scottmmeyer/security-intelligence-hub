# Phase 23.4A — Q5: UI Design
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. BLOCK DIAGNOSTICS Card — Redesign

### 1.1 Current Section Order (Phase 23.3)

```
[MANDATE_BLOCKED banner]
[ETF_GATE_FAILED badge]
[WORSENS_OVERWEIGHT badge]
[CONFLICTS_WITH_MANDATE badge]

↓ No further operator guidance
```

### 1.2 Target Section Order (Phase 23.5)

```
1. NEXT BEST ACTION      ← New — actionable first
2. Suggested Alternatives ← New — scannable alternatives table
3. Why Blocked            ← Was first — moved to third
4. Evidence               ← Existing — preserved
5. How To Unblock         ← Existing — preserved
```

---

## 2. Panel Mockup

### 2.1 Full BLOCK DIAGNOSTICS Card

```
┌──────────────────────────────────────────────────────────────────┐
│  BLOCK DIAGNOSTICS                                               │
│  EQUITIES.US.LARGE / INCREASE_UNDERWEIGHT                        │
│  ──────────────────────────────────────────────────────────────  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ NEXT BEST ACTION                            [HIGH]         │  │
│  │                                                            │  │
│  │  Instead of adding VOO/IVV/SPY to EQUITIES.US.LARGE:       │  │
│  │                                                            │  │
│  │  → ACCUMULATE direct securities ranked by conviction       │  │
│  │                                                            │  │
│  │  CONCENTRATED_ALPHA mandate suppresses ETF allocation;     │  │
│  │  direct securities are the preferred deployment path.      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ SUGGESTED ALTERNATIVES                                     │  │
│  │                                                            │  │
│  │  #  Symbol   Score   Tier                   Headroom       │  │
│  │  1  VRT      94.97   CORE_CONVICTION_LEADER  33%          │  │
│  │  2  ARW      93.93   HIGH_CONVICTION_ANCHOR  82%          │  │
│  │  3  PSX      93.53   HIGH_CONVICTION_ANCHOR  86%          │  │
│  │  4  DELL     92.45   HIGH_CONVICTION_ANCHOR  77%          │  │
│  │  5  AVT      91.96   HIGH_CONVICTION_ANCHOR  83%          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ▶ WHY BLOCKED  [collapsed by default]                           │
│  ▶ EVIDENCE     [collapsed by default]                           │
│  ▶ HOW TO UNBLOCK [collapsed by default]                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 NBA Panel — MONITOR_ONLY State (TSLA DO_NOT_SELL)

```
┌──────────────────────────────────────────────────────────────────┐
│  BLOCK DIAGNOSTICS                                               │
│  TSLA / TRIM                                                     │
│  ──────────────────────────────────────────────────────────────  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ NEXT BEST ACTION                       [INFORMATIONAL]     │  │
│  │                                                            │  │
│  │  Instead of reducing TSLA:                                 │  │
│  │                                                            │  │
│  │  → MONITOR ONLY — no action available                      │  │
│  │                                                            │  │
│  │  DO_NOT_SELL policy in effect. Hold current position.      │  │
│  │  Monitor for signal reversal before re-evaluating.         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ▶ WHY BLOCKED  [collapsed]                                      │
│  ▶ EVIDENCE     [collapsed]                                      │
│  ▶ HOW TO UNBLOCK [collapsed]                                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. HTML Structure

### 3.1 BLOCK DIAGNOSTICS Wrapper

```html
<div class="block-diagnostics-panel" data-symbol="${r.symbol}" data-node="${r.affected_node_key || ''}">

  <div class="diagnostics-header">
    <span class="diagnostics-title">BLOCK DIAGNOSTICS</span>
    <span class="diagnostics-context">${r.affected_node_key || r.symbol} / ${r.recommendation_type || r.opportunity_flag}</span>
  </div>

  <!-- SECTION 1: NEXT BEST ACTION -->
  <div class="nba-panel nba-priority-${nba.action_priority.toLowerCase()}">
    <div class="nba-header">
      <span class="nba-label">NEXT BEST ACTION</span>
      <span class="nba-priority-badge priority-${nba.action_priority.toLowerCase()}">${nba.action_priority}</span>
    </div>
    <div class="nba-body">
      <div class="nba-instead-of">Instead of ${_buildBlockedDescription(r)}:</div>
      <div class="nba-action-directive">→ ${_buildActionDirective(nba)}</div>
      <div class="nba-rationale">${nba.rationale}</div>
    </div>
  </div>

  <!-- SECTION 2: SUGGESTED ALTERNATIVES (only if candidates exist) -->
  ${nba.candidate_symbols.length > 0 ? `
  <div class="alternatives-panel">
    <div class="alternatives-header">SUGGESTED ALTERNATIVES</div>
    <table class="alternatives-table">
      <thead>
        <tr>
          <th>#</th><th>Symbol</th><th>Score</th><th>Tier</th><th>Headroom</th>
        </tr>
      </thead>
      <tbody>
        ${nba.candidate_symbols.map((sym, i) => `
        <tr class="alternative-row" data-symbol="${sym}">
          <td>${i + 1}</td>
          <td class="alt-symbol">${sym}</td>
          <td class="alt-score">${nba.deployment_scores[i]?.toFixed(2) || '—'}</td>
          <td class="alt-tier">${_formatTier(nba.narrative_tiers[i])}</td>
          <td class="alt-headroom">${_extractHeadroom(sym, deploymentQueue)}</td>
        </tr>`).join('')}
      </tbody>
    </table>
  </div>` : ''}

  <!-- SECTION 3: WHY BLOCKED (collapsible) -->
  <details class="diagnostics-section">
    <summary class="diagnostics-section-header">WHY BLOCKED</summary>
    <div class="diagnostics-section-body">
      ${_buildWhyBlocked(r)}
    </div>
  </details>

  <!-- SECTION 4: EVIDENCE (collapsible) -->
  <details class="diagnostics-section">
    <summary class="diagnostics-section-header">EVIDENCE</summary>
    <div class="diagnostics-section-body">
      ${_buildEvidence(r)}
    </div>
  </details>

  <!-- SECTION 5: HOW TO UNBLOCK (collapsible) -->
  <details class="diagnostics-section">
    <summary class="diagnostics-section-header">HOW TO UNBLOCK</summary>
    <div class="diagnostics-section-body">
      ${_buildHowToUnblock(r)}
    </div>
  </details>

</div>
```

---

## 4. CSS Additions

```css
/* ── BLOCK DIAGNOSTICS PANEL ── */
.block-diagnostics-panel {
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 16px;
  margin-top: 12px;
  background: var(--surface-secondary);
}

.diagnostics-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.diagnostics-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.diagnostics-context {
  font-size: 11px;
  color: var(--text-secondary);
}

/* ── NBA PANEL ── */
.nba-panel {
  border-radius: 4px;
  padding: 12px 14px;
  margin-bottom: 10px;
}

.nba-panel.nba-priority-high {
  background: color-mix(in srgb, var(--accent-amber) 8%, transparent);
  border-left: 3px solid var(--accent-amber);
}

.nba-panel.nba-priority-medium {
  background: color-mix(in srgb, var(--accent-blue) 8%, transparent);
  border-left: 3px solid var(--accent-blue);
}

.nba-panel.nba-priority-low {
  background: color-mix(in srgb, var(--text-muted) 6%, transparent);
  border-left: 3px solid var(--border-subtle);
}

.nba-panel.nba-priority-informational {
  background: color-mix(in srgb, var(--text-muted) 4%, transparent);
  border-left: 3px solid var(--border-subtle);
}

.nba-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.nba-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.nba-priority-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.priority-high { background: var(--accent-amber); color: var(--surface-primary); }
.priority-medium { background: var(--accent-blue); color: white; }
.priority-low { background: var(--border-subtle); color: var(--text-muted); }
.priority-informational { color: var(--text-muted); border: 1px solid var(--border-subtle); }

.nba-instead-of {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.nba-action-directive {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.nba-rationale {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

/* ── ALTERNATIVES TABLE ── */
.alternatives-panel {
  margin-bottom: 10px;
}

.alternatives-header {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.alternatives-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.alternatives-table th {
  text-align: left;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 4px 6px;
  border-bottom: 1px solid var(--border-subtle);
}

.alternatives-table td {
  padding: 5px 6px;
  border-bottom: 1px solid var(--border-lightest);
  color: var(--text-primary);
}

.alt-symbol {
  font-weight: 600;
  font-family: var(--font-mono);
}

.alt-score {
  font-variant-numeric: tabular-nums;
  color: var(--accent-green);
  font-weight: 500;
}

.alt-tier {
  font-size: 11px;
  color: var(--text-secondary);
}

.alt-headroom {
  font-size: 11px;
  color: var(--text-secondary);
}

/* ── COLLAPSIBLE SECTIONS ── */
.diagnostics-section {
  margin-top: 6px;
}

.diagnostics-section-header {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px 0;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.diagnostics-section-header::before {
  content: '▶';
  font-size: 9px;
  transition: transform 0.15s;
}

details[open] > .diagnostics-section-header::before {
  transform: rotate(90deg);
}

.diagnostics-section-body {
  padding: 8px 0 4px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}
```

---

## 5. JavaScript Function Spec: `_buildNextBestAction(r, deploymentQueue, overlays)`

### 5.1 Signature

```javascript
/**
 * Generates a NextBestAction object for a blocked recommendation.
 *
 * @param {Object} r - recommendation object (from recommendations.json)
 * @param {Array}  deploymentQueue - array of DeploymentCandidate objects
 * @param {Object} overlaysBySymbol - map of symbol → security_overlay row
 * @returns {NextBestAction|null} - null if no block detected
 */
function _buildNextBestAction(r, deploymentQueue, overlaysBySymbol) { ... }
```

### 5.2 Input Contract

`r` (recommendation): `{ affected_node_key, optimizer_metadata: { mandate_blocked, optimizer_decision, candidates[] }, recommendation_type }`

`r` (security overlay): `{ symbol, opportunity_flag, execution_state, effective_action, signal_direction }`

`deploymentQueue`: `[ { rank, symbol, deployment_score, narrative_tier, notes } ]`

`overlaysBySymbol`: `{ "VRT": { execution_state: "EXECUTABLE", signal_direction: "BULLISH", ... } }`

### 5.3 Output Contract

Returns `NextBestAction` as defined in Q2 data contract, or `null` if no block is present.

### 5.4 Rendering Function: `_renderBlockDiagnosticsPanel(r, nba, deploymentQueue)`

```javascript
/**
 * Renders the full BLOCK DIAGNOSTICS card.
 * Sections: NBA → Alternatives → Why Blocked (collapsed) → Evidence (collapsed) → Unblock (collapsed)
 *
 * @param {Object} r - recommendation/security overlay
 * @param {NextBestAction} nba - pre-built NBA object
 * @param {Array} deploymentQueue - for headroom extraction
 * @returns {string} HTML string
 */
function _renderBlockDiagnosticsPanel(r, nba, deploymentQueue) { ... }
```

---

## 6. Placement Rules

### 6.1 When to Render BLOCK DIAGNOSTICS Panel

Render the panel when ANY of the following are true:
- `r.optimizer_metadata?.mandate_blocked == true`
- `r.optimizer_metadata?.optimizer_decision == "MANDATE_BLOCKED"`
- Any candidate has `optimizer_status in {"MANDATE_BLOCKED", "ETF_GATED"}`
- `r.execution_state == "BLOCKED_BY_POLICY"`
- Any candidate has `worsens_overweight == true`

### 6.2 When NOT to Render

- `execution_state == "EXECUTABLE"` with no gated candidates
- `opportunity_flag in {"HOLD", "WATCH"}` with no block conditions
- Recommendation type is `NOT_APPLICABLE`

### 6.3 Panel Placement in Card

The BLOCK DIAGNOSTICS panel appends below the standard opportunity card content. It does not replace the existing card layout.

```
[Existing card: header, signal badges, stats, opportunity flag]
[BLOCK DIAGNOSTICS panel — new, appended below]
```

---

## 7. Summary

| Element | Design Decision |
|---|---|
| Section order | NBA → Alternatives → Why Blocked → Evidence → Unblock |
| Why Blocked / Evidence / Unblock | Collapsible (`<details>`) — closed by default |
| NBA panel color coding | Amber (HIGH), Blue (MEDIUM), Gray (LOW/INFORMATIONAL) |
| Alternatives table | Max 5 rows, sortable by deployment_score |
| No alternatives state | Explicit "no action available" message — never blank |
| CSS approach | New utility classes, no existing class changes |
| JS function | `_buildNextBestAction()` + `_renderBlockDiagnosticsPanel()` |

**Status: Q5 COMPLETE — UI DESIGN CERTIFIED**
