# PA-006 Dashboard Design — Allocation Drift Trend Visibility

**Date:** 2026-06-15

---

## Placement

A new **"Drift Trends"** section added to the existing PIS dashboard (`/ui/pis_dashboard/`). Positioned after the existing CPV compliance panel. No new route or page.

---

## View 1: CPV Rule Trend Table

**Purpose:** Show every CPV rule with current value, prior value, and trend direction.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Allocation Policy Compliance — Drift Trends                         [Jun 15] │
├────────────────┬────────┬─────────┬─────────┬──────────┬──────────┬──────────┤
│ Rule           │ Policy │ Current │ Prior   │ 7d Delta │ 30d Delta│ Trend    │
├────────────────┼────────┼─────────┼─────────┼──────────┼──────────┼──────────┤
│ CPV-01 Micro   │ ≤5%    │ 8.89% ⚠ │ 9.52% ✖ │ −0.63pp  │ −0.63pp  │ ↓ IMPRV  │
│ CPV-02 Mega    │ ≤50%   │ 18.64%✓ │ 18.66%✓ │ −0.02pp  │ −0.02pp  │ → STABLE │
│ CPV-03 Digital │ ≤8%    │ 0.65% ✓ │ 0.79% ✓ │ −0.14pp  │ −0.14pp  │ → STABLE │
│ CPV-04 Cash    │ ≥2%    │ 10.83%✓ │ 4.24% ✓ │ +6.59pp  │ +6.59pp  │ ↑ IMPRV  │
│ CPV-05 Intl    │ ≥10%   │ 17.52%✓ │ 20.34%✓ │ −2.82pp  │ −2.82pp  │ ↓ WATCH  │
│ CPV-06 EqCls   │ ≤80%   │ 86.72%⚠ │ 94.97%✖ │ −8.25pp  │ −8.25pp  │ ↓ IMPRV  │
│ CPV-07 Equity  │ ≥40%   │ 86.72%✓ │ 94.97%✓ │ −8.25pp  │ −8.25pp  │ → OK     │
│ CPV-08 FI Max  │ ≤40%   │ 1.43% ✓ │ 0.00% ✓ │ +1.43pp  │ +1.43pp  │ → STABLE │
└────────────────┴────────┴─────────┴─────────┴──────────┴──────────┴──────────┘
```

**Trend direction key:**
- `↓ IMPRV` — improving (breach decreasing)
- `↑ WRSE` — worsening (breach increasing)
- `↑ IMPRV` — improving (floor metric increasing toward policy)
- `→ STABLE` — delta < 0.5pp either direction

**Cell styling:**
- Status badges: ✖ FAIL = red pill, ⚠ WARN = amber pill, ADVISORY = yellow pill, ✓ OK = green pill
- Delta cells: negative delta for ceiling rules = green text, positive = red text
- Trend arrows colored to match severity change (red→amber = green arrow)

---

## View 2: CPV Timeline Chart (Inline Sparkline)

**Purpose:** Show movement of the two active violations (CPV-01, CPV-06) over time.

```
  CPV-01 Micro Cap (≤5% policy)                           WARN
  ┌─────────────────────────────────────────────────────────────┐
  │ 9.52  ─────────────────────────── 8.53 ─────────── 8.89    │
  │ FAIL  ○──────────────────────────────○─────────────●       │
  │                              ↑ WARN boundary (9pp)          │
  │ ═══════════════════════════════════════════════════ POLICY  │
  └─────────────────────────────────────────────────────────────┘
    May-21                    May-29                    Jun-15
```

**Implementation:** Simple HTML/CSS mini-chart (or sparkline via canvas). Shows:
- Policy limit as a horizontal line
- WARN threshold as a dashed line
- FAIL threshold as a dotted line
- Actual values as circles at each date
- Color: red for FAIL, amber for WARN, green for OK

For the MVP: a CSS-only implementation using a flex-column of dots is sufficient. No charting library needed.

---

## View 3: Top Drift Contributors

**Purpose:** Show which symbols moved the most between the two most recent canonical dates.

```
┌────────────────────────────────────────────────────┐
│  Position Drift: Jun 11 → Jun 15                   │
├──────────┬──────────┬──────────┬────────────────────┤
│ Symbol   │ Jun 11   │ Jun 15   │ Delta              │
├──────────┼──────────┼──────────┼────────────────────┤
│ VRT    ▲ │ 4.62%    │ 4.90%    │ +0.28pp [INCR]     │
│ ATLC   ▲ │ 1.32%    │ 1.50%    │ +0.18pp [INCR]     │
│ SPAXX  ▲ │ 9.91%    │ 10.85%   │ +0.94pp [INCR]     │
│ MU     ▲ │ 6.82%    │ 6.55%    │ −0.27pp [DECR]     │
│ MSFT   ▼ │ 4.23%    │ 3.97%    │ −0.26pp [DECR]     │
└──────────┴──────────┴──────────┴────────────────────┘
```

**Sorted by |delta_pp| descending. Top 10 symbols shown.**

---

## View 4: Drift Summary Banner

**Purpose:** Single-line summary for quick operator orientation. Placed at top of drift section.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  ALLOCATION DRIFT  Jun 15 vs Jun 11 (4 days):  CPV-01 ↓0.63pp  CPV-06 ↓2pp ║
║  2 active violations remain. Overall compliance score: 80/100.               ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## UI Component Specification

### New section in `app.js`

```javascript
async function renderDriftTrends() {
    const resp = await fetch('/api/drift/summary');
    const data = await resp.json();
    
    // Render CPV trend table
    renderCpvTrendTable(data.cpv_trend);
    
    // Render top contributors
    renderDriftContributors(data.top_contributors);
    
    // Render summary banner
    renderDriftBanner(data);
}

function cpvTrendBadge(status, direction) {
    const statusClass = {'FAIL':'badge-fail','WARN':'badge-warn','OK':'badge-ok','ADVISORY':'badge-advisory'};
    const arrow = {'IMPROVING':'↓','WORSENING':'↑','STABLE':'→'};
    return `<span class="${statusClass[status]}">${status}</span> ${arrow[direction]}`;
}
```

### New API endpoints in `run_outcome_ui.py`

```python
@app.route('/api/drift/summary')
def api_drift_summary():
    from src.portfolio.drift_analyzer import compute_drift_summary
    result = compute_drift_summary(repo_root=_REPO_ROOT)
    return jsonify(result)

@app.route('/api/drift/timeline')
def api_drift_timeline():
    rule_id = request.args.get('rule_id', 'CPV-01')
    from src.portfolio.drift_analyzer import compute_drift_timeline
    result = compute_drift_timeline(rule_id=rule_id, repo_root=_REPO_ROOT)
    return jsonify(result)
```

### New module: `src/portfolio/drift_analyzer.py`

```python
"""PA-006: Allocation Drift Analyzer.

Reads existing PAR artifacts (concentration.json, compliance.json, holdings.csv)
to construct allocation drift trends across available history.

No writes. No side effects. Read-only computation.
"""
```

---

## MVP Scope vs Full Implementation

### MVP (Minimum Viable Panel)

1. CPV Trend Table (View 1) — static values from 3 available compliance.json dates
2. Drift Summary Banner (View 4)
3. API endpoint returning static JSON built from 4 compliance files

**Effort:** ~4 hours. No new data collection. No holdings.csv parsing needed for MVP.

### Full Implementation

1. All 4 views
2. `drift_analyzer.py` reading from all 250 PAR runs
3. Per-symbol contributor table
4. Timeline chart (sparkline)
5. Tests for drift computation

**Effort:** ~12-16 hours. Regression tests first.

---

## Regression Test Plan

| Test | Assertion |
|------|-----------|
| `test_drift_canonical_selection` | Latest PAR per date selected correctly |
| `test_cpv_ceiling_status` | Breach >warn_pp → FAIL, between advisory/warn → WARN |
| `test_cpv_floor_status` | Below-floor breach correctly classified |
| `test_trend_direction_ceiling` | Delta +1pp for ceiling rule → WORSENING |
| `test_trend_direction_floor` | Delta −1pp for floor rule → WORSENING |
| `test_contributor_sort` | Top contributors sorted by |delta_pp| desc |
| `test_empty_history` | Returns empty timeline, no crash |
| `test_single_date` | Returns current data, no trend delta |
