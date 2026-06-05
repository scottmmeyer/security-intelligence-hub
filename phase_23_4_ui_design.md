# Phase 23.4 — BLOCK DIAGNOSTICS UI Design
**Forensic analysis only. No implementation changes.**

Generated: 2026-06-04  
Baseline: PAR-20260603-0487E65C | 853 tests | 0 failures | 1 skip

---

## Design objective

Design a **BLOCK DIAGNOSTICS** section that appears on every `INCREASE_UNDERWEIGHT`
recommendation card where one or more blocker codes are active. The section replaces the
current minimalist badge row + generic banner with a structured, operator-actionable
diagnostic panel.

**Current state**: The optimizer shows badges (`MANDATE_BLOCKED`, `ETF_GATE_FAILED: VOO`,
`CONFLICTS_WITH_MANDATE`, `WORSENS_OVERWEIGHT`) and a single-line banner message.
No evidence fields are shown. No remediation guidance is given. No alternatives are
surfaced in the blocked context.

**Target state**: A dedicated BLOCK DIAGNOSTICS panel that shows:
- What is blocked and why
- What evidence supports the diagnosis
- How to unblock (operator actions)
- What alternatives the system can offer

---

## UI section design: BLOCK DIAGNOSTICS

### Placement

The BLOCK DIAGNOSTICS section appears inside the recommendation card, **below the
existing `blockedWarningHtml` banner** and **above** the optimizer view collapsible block,
when one or more of the following conditions are true:

- `optimizer_decision === "MANDATE_BLOCKED"`
- `candidates.some(c => !String(c.etf_gate || "").startsWith("PASS"))` (any ETF failed)
- `candidates.some(c => c.worsens_overweight)` (any candidate worsens OW)

### Section structure

```
┌──────────────────────────────────────────────────────────────────┐
│  🔍 BLOCK DIAGNOSTICS                                            │
│  ─────────────────────────────────────────────────────────────── │
│  [block row 1]                                                    │
│  [block row 2]                                                    │
│  ...                                                              │
│                                                                   │
│  ▶ Suggested Alternatives  [collapsible]                         │
└──────────────────────────────────────────────────────────────────┘
```

### Block row structure

Each distinct block condition gets one block row:

```
┌───────────────────────────────────────────────────────┐
│  ⛔ [BLOCKER CODE]                                     │
│  Reason:      [human explanation]                     │
│  Evidence:    [field: value] [field: value] ...       │
│  How to unblock: [primary remediation action]         │
└───────────────────────────────────────────────────────┘
```

---

## Block row designs by blocker type

### MANDATE_BLOCKED row

```
⛔ MANDATE BLOCKED
Reason:       Concentrated Alpha mandate classifies this node's underweight as
              intentional portfolio policy. Deployment into [NODE_LABEL] is suppressed.
Evidence:     Mandate: Concentrated Alpha  |  Node: [NODE_KEY]  |
              Drift: [RAW_DRIFT_PCT]pp [DIRECTION]  |  Label: INTENTIONAL_UNDERWEIGHT  |
              Tolerance: 0.90  |  Urgency: INFORMATIONAL
How to unblock: Switch mandate from Concentrated Alpha, or use direct-security
              candidates bypassing the ETF gate.
```

**Data fields needed**:
- `optimizer_metadata.mandate_type`
- `r.affected_node_key`
- `r.affected_node_label` (or label from alignment)
- `r.mandate_drift_label`
- `r.mandate_urgency`
- `r.drift_pct` (raw drift from alignment)
- Mandate `concentration_tolerance` — **not currently in optimizer_metadata** (design gap)

---

### ETF_GATE_FAILED row (one per failed vehicle)

```
⚠ ETF GATE FAILED: [SYMBOL]
Reason:       [SYMBOL] failed the implementation vehicle gate for [NODE_LABEL].
Evidence:     Gate result: FAIL  |  Failures: [etf_gate reason string parsed]  |
              NCS: [ncs]%  |  Suitability: [suitability_tier]
              [if worsens:] Worsens OW: Yes — [OW_NODE] +[overlap_ow]%
How to unblock: Use direct securities in [NODE_LABEL] node, or select an ETF
              with >10% node coverage and no overweight-worsening exposure.
```

**Data fields needed** (all available on candidate dict):
- `c.symbol`
- `c.etf_gate` (full string with reason)
- `c.ncs`
- `c.suitability_tier`
- `c.worsens_overweight`
- `c.conflict_nodes`
- `c.pis` (discounted PIS)

---

### WORSENS_OVERWEIGHT advisory row

```
⚠ WORSENS OVERWEIGHT (advisory)
Reason:       One or more vehicles would deepen an existing overweight allocation node.
              This is an advisory signal; the ETF gate handles the hard block.
Evidence:     Affected vehicles: [list symbols where worsens_overweight=true]  |
              Conflict type: T1 (build-vehicle worsens reduce-target node)
How to unblock: Rebalance [OW_NODE] first, or use direct securities
              that do not expose the overweight tier.
```

**Data fields needed**:
- `candidates.filter(c => c.worsens_overweight).map(c => c.symbol)`
- `c.conflict_nodes` (contains "OVERWEIGHT_NODE_WORSENED")

---

### CONFLICTS_WITH_MANDATE advisory row

```
ℹ CONFLICTS WITH MANDATE (advisory)
Reason:       The legacy vehicle(s) referenced in this recommendation sit in a
              mandate-blocked allocation node. These vehicles are not viable
              implementation paths under the current mandate.
Evidence:     Legacy vehicles: [legacy_vehicles list]  |
              Mandate: [mandate_type]  |  Node: [affected_node_key]
How to unblock: Same as MANDATE BLOCKED — change mandate or use direct securities.
```

**Data fields needed**:
- `optimizer_metadata.legacy_vehicles`
- `optimizer_metadata.mandate_type`
- `r.affected_node_key`

---

## Suggested Alternatives panel

When MANDATE_BLOCKED or V3 ETF_GATE_FAILED fires, a collapsible "Suggested Alternatives"
panel provides direct-security candidates that could address the deployment gap:

```
▶ Suggested Alternatives — Direct Security Candidates for [NODE_LABEL]

  These holdings are in your portfolio and positioned for deployment in this
  allocation tier. They are not ETF vehicles and are not subject to the
  mandate block on ETF gate.

  ┌────────────────────────────────────────────────────────────────────┐
  │ Symbol │ Tier    │ ESS Score     │ Deploy Score │ Note             │
  │ VRT    │ CCL     │ VERY_BULLISH  │ 78.4         │ CCL tier | 42% hrm │
  │ DELL   │ HCA     │ BULLISH       │ 63.1         │ HCA tier | 68% hrm │
  │ LRCX   │ HCA     │ BULLISH       │ 61.8         │ HCA tier | 55% hrm │
  │ ARW    │ HCA     │ BULLISH       │ 58.2         │ HCA tier | 71% hrm │
  │ CAH    │ TGC     │ BULLISH       │ 44.0         │ TGC tier | 88% hrm │
  └────────────────────────────────────────────────────────────────────┘

  Note: These are guidance signals — not trade instructions. Deployment
  decisions remain with the operator.
```

**Data source**: The deployment queue (`deployment_queue.json`) filtered to candidates
whose `target_node` matches the blocked rec's `affected_node_key`.

**Columns**:
- Symbol
- Narrative tier (CCL / HCA / TGC)
- ESS score text
- CW-DAS deployment_score
- Notes (from `DeploymentCandidate.notes`)

**Sort**: By `deployment_score` descending. Show top 5.

---

## Full block diagnostics panel mockup (composite example)

This example reflects the canonical Phase 23.4 scenario:
- Mandate: CONCENTRATED_ALPHA
- Blocked node: EQUITIES.US.MEGA (−4.2pp underweight, INTENTIONAL)
- Legacy vehicles: VOO, IVV, SPY (all worsening EQUITIES.US.MEGA overweight in sub-positions)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  🔍 BLOCK DIAGNOSTICS                                                        │
│                                                                              │
│  ⛔ MANDATE BLOCKED                                                           │
│  Reason:      Concentrated Alpha mandate classifies US Mega Cap underweight  │
│               as intentional. Node EQUITIES.US.MEGA deployment is suppressed.│
│  Evidence:    Mandate: Concentrated Alpha  |  Tolerance: 0.90  |             │
│               Drift: −4.2pp Underweight  |  Label: INTENTIONAL_UNDERWEIGHT  │
│               Urgency: INFORMATIONAL                                         │
│  How to unblock: Switch mandate to Growth or Balanced, or deploy via          │
│               direct-security candidates listed in Suggested Alternatives.   │
│                                                                              │
│  ⚠ ETF GATE FAILED: VOO                                                       │
│  Reason:      VOO fails the vehicle gate for US Mega Cap.                    │
│  Evidence:    Gate: FAIL  |  NCS: 31.4%  |  Suitability: MEDIUM  |           │
│               Worsens OW: Yes — EQUITIES.US.MEGA +18.3%                     │
│  How to unblock: Use direct securities that don't expose existing OW nodes.  │
│                                                                              │
│  ⚠ ETF GATE FAILED: IVV                                                       │
│  Reason:      IVV fails the vehicle gate for US Mega Cap.                    │
│  Evidence:    Gate: FAIL  |  NCS: 30.1%  |  Suitability: MEDIUM  |           │
│               Worsens OW: Yes — EQUITIES.US.MEGA +17.2%                     │
│  How to unblock: Use direct securities instead.                              │
│                                                                              │
│  ⚠ WORSENS OVERWEIGHT (advisory)                                              │
│  Reason:      VOO, IVV, SPY all worsen overweight in EQUITIES.US.MEGA.       │
│  Evidence:    Vehicles: VOO, IVV, SPY  |  Conflict type: T1                 │
│  How to unblock: Rebalance EQUITIES.US.MEGA first, then reassess.            │
│                                                                              │
│  ▶ Suggested Alternatives — Direct Security Candidates for US Mega Cap       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Symbol │ Tier │ ESS           │ Deploy Score │ Notes                  │  │
│  │ VRT    │ CCL  │ VERY_BULLISH  │ 78.4         │ CCL tier | 42% headrm │  │
│  │ DELL   │ HCA  │ BULLISH       │ 63.1         │ HCA tier | 68% headrm │  │
│  │ LRCX   │ HCA  │ BULLISH       │ 61.8         │ HCA tier | 55% headrm │  │
│  │ ARW    │ HCA  │ BULLISH       │ 58.2         │ HCA tier | 71% headrm │  │
│  │ CAH    │ TGC  │ BULLISH       │ 44.0         │ TGC tier | 88% headrm │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## CSS class design

```css
/* BLOCK DIAGNOSTICS section */
.block-diagnostics-section {
    margin-top: 8px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: #fafafa;
    padding: 10px 14px;
}

.block-diagnostics-title {
    font-size: 0.7rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #374151;
    margin-bottom: 8px;
}

/* Individual blocker row */
.block-row {
    border-left: 3px solid #e5e7eb;
    padding: 6px 10px;
    margin-bottom: 8px;
    background: white;
    border-radius: 0 4px 4px 0;
}

.block-row.block-row-mandate { border-left-color: #dc2626; }   /* red */
.block-row.block-row-etf     { border-left-color: #d97706; }   /* amber */
.block-row.block-row-advisory{ border-left-color: #2563eb; }   /* blue */

.block-row-code {
    font-size: 0.65rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}
.block-row-code.code-mandate  { color: #dc2626; }
.block-row-code.code-etf      { color: #d97706; }
.block-row-code.code-advisory { color: #2563eb; }

.block-row-reason,
.block-row-evidence,
.block-row-remediation {
    font-size: 0.72rem;
    line-height: 1.5;
    color: #374151;
    margin-bottom: 2px;
}

.block-row-label {
    display: inline-block;
    min-width: 90px;
    font-weight: 700;
    color: #6b7280;
    font-size: 0.65rem;
    text-transform: uppercase;
}

/* Evidence chips */
.block-evidence-chip {
    display: inline-block;
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 0.65rem;
    font-family: monospace;
    margin-right: 4px;
    margin-bottom: 2px;
    color: #374151;
}

/* Suggested alternatives table */
.block-alternatives-panel {
    margin-top: 10px;
    border-top: 1px solid #e5e7eb;
    padding-top: 8px;
}

.block-alternatives-title {
    font-size: 0.65rem;
    font-weight: 700;
    color: #1a5c8a;
    margin-bottom: 6px;
    cursor: pointer;
}

.block-alternatives-table {
    width: 100%;
    font-size: 0.68rem;
    border-collapse: collapse;
}

.block-alternatives-table th {
    text-align: left;
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
    border-bottom: 1px solid #e5e7eb;
    padding: 3px 6px;
}

.block-alternatives-table td {
    padding: 3px 6px;
    color: #374151;
    border-bottom: 1px solid #f3f4f6;
}

.alt-tier-CCL  { color: #059669; font-weight: 700; }
.alt-tier-HCA  { color: #2563eb; font-weight: 700; }
.alt-tier-TGC  { color: #7c3aed; font-weight: 600; }
```

---

## Data flow design

The BLOCK DIAGNOSTICS section is rendered entirely in JavaScript from existing
`optimizer_metadata` fields. **No new Python endpoints are required.**

### Required data available today

| Field | Where it lives | Status |
|-------|---------------|--------|
| `optimizer_decision` | `rec.optimizer_metadata.optimizer_decision` | ✅ Available |
| `mandate_blocked` | `rec.optimizer_metadata.mandate_blocked` | ✅ Available |
| `candidates` | `rec.optimizer_metadata.candidates` | ✅ Available |
| `etf_gate` (per candidate) | `candidate.etf_gate` | ✅ Available |
| `ncs` | `candidate.ncs` | ✅ Available |
| `worsens_overweight` | `candidate.worsens_overweight` | ✅ Available |
| `suitability_tier` | `candidate.suitability_tier` | ✅ Available |
| `legacy_vehicles` | `rec.optimizer_metadata.legacy_vehicles` | ✅ Available |
| `mandate_drift_label` | `rec.mandate_drift_label` | ✅ Available |
| `mandate_urgency` | `rec.mandate_urgency` | ✅ Available |

### Data NOT available today (design gaps)

| Missing field | Needed for | Where to add |
|--------------|-----------|-------------|
| `mandate_type` on optimizer_metadata | Mandate row: "Mandate: Concentrated Alpha" | Add to `_build_result()` in optimizer.py |
| `concentration_tolerance` | Mandate row evidence | Add to `_build_result()` — sourced from `PortfolioMandate` |
| Deployment queue candidates for target node | Suggested Alternatives panel | New endpoint or field in optimizer result |
| `raw_drift_pct` on optimizer_metadata | Mandate row evidence | Available on rec alignment data; add to build_result |

### Suggested Alternatives data flow

Two implementation options (both design-only here):

**Option A — Embed in optimizer result**: During `run_parallel_optimizer()`, for
MANDATE_BLOCKED nodes, look up matching deployment queue entries and embed top-N
as `suggested_alternatives` in the OptimizerResult dict.

**Option B — Separate API call**: The UI issues a second request to `/api/portfolio/deploy-queue`
filtered by `target_node`, and renders alternatives client-side without modifying the
optimizer output.

Option A is preferred for data coherence. Option B is simpler to implement without
touching the optimizer.

---

## Component specification summary

### `_buildBlockDiagnostics(r)` function

```javascript
/**
 * Build the BLOCK DIAGNOSTICS section for a recommendation card.
 * @param {Object} r - recommendation object with optimizer_metadata
 * @returns {string} HTML string for the diagnostics section, or "" if no blocks
 */
function _buildBlockDiagnostics(r) {
    const om = r.optimizer_metadata;
    if (!om) return "";

    const candidates  = om.candidates || [];
    const decision    = om.optimizer_decision || "";
    const rows        = [];

    // Row 1: MANDATE_BLOCKED
    if (decision === "MANDATE_BLOCKED") {
        rows.push(_buildMandateBlockedRow(r, om));
    }

    // Row 2+: ETF_GATE_FAILED (one per failed vehicle)
    const etfFailed = candidates.filter(
        c => c.candidate_type === "ETF" && !String(c.etf_gate || "").startsWith("PASS")
    );
    for (const c of etfFailed) {
        rows.push(_buildEtfGateFailedRow(c, r));
    }

    // Row 3: WORSENS_OVERWEIGHT advisory
    const ow = candidates.filter(c => c.worsens_overweight);
    if (ow.length > 0) {
        rows.push(_buildWorsensOWRow(ow));
    }

    // Row 4: CONFLICTS_WITH_MANDATE advisory
    if (om.mandate_blocked && decision !== "MANDATE_BLOCKED") {
        rows.push(_buildConflictsWithMandateRow(r, om));
    }

    if (rows.length === 0) return "";

    const alternativesHtml = _buildSuggestedAlternativesPanel(r, om);

    return `<div class="block-diagnostics-section">
        <div class="block-diagnostics-title">🔍 Block Diagnostics</div>
        ${rows.join("")}
        ${alternativesHtml}
    </div>`;
}
```

---

*Phase 23.4 — Design document 4 of 5.*
