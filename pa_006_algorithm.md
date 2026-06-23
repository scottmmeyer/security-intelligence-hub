# PA-006 Algorithm — Allocation Drift Computation

**Date:** 2026-06-15

---

## Overview

The drift computation pipeline has three phases:
1. **Select** one canonical PAR run per date
2. **Compute** allocation dimensions per run
3. **Derive** trend, delta, and contributor tables

All computation is read-only. No writes to existing files. Results returned as API JSON.

---

## Phase 1: Canonical PAR Selection Per Date

Multiple PAR runs may exist for the same snapshot date (re-analyses, debug runs, etc.). The canonical selection rule is:

```
For each snapshot_date:
  1. Collect all PAR runs where run_metadata.json.snapshot_date == date
  2. Filter to runs where reconciliation_status != 'HARD_FAIL' (optional, advisory)
  3. Select the latest by created_at_utc
  4. If compliance.json exists for that run, prefer it — otherwise compute from holdings.csv
```

**Implementation:** Read all `run_metadata.json` files, group by `snapshot_date`, pick latest `created_at_utc` per date.

---

## Phase 2: Dimension Computation Per Run

### From `concentration.json` (already computed):
```python
row = {
    'date': snapshot_date,
    'par_id': run_id,
    'top1_pct':   c['top1_pct'],
    'top5_pct':   c['top5_pct'],
    'top10_pct':  c['top10_pct'],
    'mega_pct':   c['mega_subtier_pct'],
    'us_pct':     c['us_pct'],
    'intl_pct':   c['international_pct'],
    'hhi':        c['herfindahl_index'],
}
```

### From `compliance.json` (when available):
```python
cpv = {r['rule_id']: {'actual_pct': r['actual_pct'], 'status': r['status']} 
       for r in c['rules']}
```

### From `holdings.csv` (when compliance.json absent):
```python
# Load active EQUITIES/CASH/FIXED_INCOME rows only
from decimal import Decimal

holdings = [row for row in csv.DictReader(open(holdings_path))
            if row['operational_state'] == 'ACTIVE_POSITION']
total_mv = sum(float(h['market_value']) for h in holdings)

micro_mv  = sum(float(h['market_value']) for h in holdings if h.get('market_cap_bucket') == 'MICRO')
mega_mv   = sum(float(h['market_value']) for h in holdings if h.get('mega_subtier') == 'MEGA')
digital_mv = sum(float(h['market_value']) for h in holdings if h.get('asset_class') == 'DIGITAL')
cash_mv   = sum(float(h['market_value']) for h in holdings if h.get('asset_class') == 'CASH' or h.get('is_cash_equivalent') == 'True')
eq_mv     = sum(float(h['market_value']) for h in holdings if h.get('asset_class') == 'EQUITIES')
fi_mv     = sum(float(h['market_value']) for h in holdings if h.get('asset_class') == 'FIXED_INCOME')
us_mv     = sum(float(h['market_value']) for h in holdings if h.get('geography') == 'US')
intl_mv   = sum(float(h['market_value']) for h in holdings if h.get('geography') not in ('US', 'UNKNOWN', ''))

cpv_values = {
    'CPV-01': micro_mv / total_mv * 100 if total_mv else 0,
    'CPV-02': mega_mv / total_mv * 100 if total_mv else 0,
    'CPV-03': digital_mv / total_mv * 100 if total_mv else 0,
    'CPV-04': cash_mv / total_mv * 100 if total_mv else 0,
    'CPV-05': intl_mv / total_mv * 100 if total_mv else 0,
    'CPV-06': max(eq_mv, fi_mv, digital_mv, cash_mv) / total_mv * 100 if total_mv else 0,
    'CPV-07': eq_mv / total_mv * 100 if total_mv else 0,
    'CPV-08': fi_mv / total_mv * 100 if total_mv else 0,
}
```

### CPV Status Recomputation:
```python
POLICY = {
    'CPV-01': {'type': 'ceiling', 'limit': 5.0,  'advisory': 2.0, 'warn': 4.0},
    'CPV-02': {'type': 'ceiling', 'limit': 50.0, 'advisory': 5.0, 'warn': 10.0},
    'CPV-03': {'type': 'ceiling', 'limit': 8.0,  'advisory': 1.0, 'warn': 2.0},
    'CPV-04': {'type': 'floor',   'limit': 2.0,  'advisory': 1.0, 'warn': 2.0},
    'CPV-05': {'type': 'floor',   'limit': 10.0, 'advisory': 2.0, 'warn': 4.0},
    'CPV-06': {'type': 'ceiling', 'limit': 80.0, 'advisory': 5.0, 'warn': 10.0},
    'CPV-07': {'type': 'floor',   'limit': 40.0, 'advisory': 5.0, 'warn': 10.0},
    'CPV-08': {'type': 'ceiling', 'limit': 40.0, 'advisory': 5.0, 'warn': 10.0},
}

def cpv_status(rule_id, actual_pct):
    p = POLICY[rule_id]
    if p['type'] == 'ceiling':
        breach = actual_pct - p['limit']
    else:
        breach = p['limit'] - actual_pct  # positive = below floor
    if breach <= 0:
        return 'OK', breach
    elif breach <= p['advisory']:
        return 'ADVISORY', breach
    elif breach <= p['warn']:
        return 'WARN', breach
    else:
        return 'FAIL', breach
```

---

## Phase 3: Trend and Contributor Derivation

### 3a: Trend Table (per CPV rule, per date)

```python
# Sort dates ascending
timeline = sorted(rows, key=lambda r: r['date'])

for rule_id in CPV_RULES:
    series = [(r['date'], r['cpv'][rule_id]['actual_pct']) for r in timeline if rule_id in r.get('cpv', {})]
    # 7-day delta: compare today vs 7 calendar days ago (or nearest available)
    # 30-day delta: compare today vs 30 calendar days ago
    # Trend direction: 'IMPROVING' | 'WORSENING' | 'STABLE' based on 7-day delta
```

**Trend direction logic:**
- For ceiling rules: delta > +0.5pp = WORSENING, delta < −0.5pp = IMPROVING, else STABLE
- For floor rules: delta < −0.5pp = WORSENING, delta > +0.5pp = IMPROVING, else STABLE

### 3b: Top Drift Contributors

```python
# Compare current PAR holdings vs prior canonical PAR holdings
# For each symbol in either snapshot:
curr_pct = {h['symbol']: float(h['percent_of_portfolio']) for h in current_holdings}
prior_pct = {h['symbol']: float(h['percent_of_portfolio']) for h in prior_holdings}
all_syms = set(curr_pct) | set(prior_pct)

contributors = []
for sym in all_syms:
    delta = curr_pct.get(sym, 0) - prior_pct.get(sym, 0)
    if abs(delta) >= 0.1:  # filter noise
        contributors.append({'symbol': sym, 'delta_pp': round(delta, 2)})

contributors.sort(key=lambda x: abs(x['delta_pp']), reverse=True)
top_contributors = contributors[:10]
```

---

## Phase 4: API Response Schema

### GET `/api/drift/summary`

```json
{
  "generated_at": "2026-06-15T14:30:00Z",
  "current_date": "2026-06-15",
  "prior_date": "2026-06-11",
  "dates_available": 20,
  "cpv_trend": [
    {
      "rule_id": "CPV-01",
      "name": "Combined Micro Cap",
      "rule_type": "ceiling",
      "policy_limit_pct": 5.0,
      "current_pct": 8.89,
      "prior_pct": 9.52,
      "delta_7d_pp": -0.63,
      "delta_30d_pp": null,
      "current_status": "WARN",
      "prior_status": "FAIL",
      "trend_direction": "IMPROVING",
      "breach_pp": 3.89
    }
  ],
  "concentration_trend": {
    "top5_pct": {"current": 29.88, "prior": 29.67, "delta": 0.21},
    "mega_pct": {"current": 8.83, "prior": 8.88, "delta": -0.05},
    "us_pct": {"current": 69.21, "prior": 68.91, "delta": 0.30},
    "intl_pct": {"current": 16.88, "prior": 17.14, "delta": -0.26}
  },
  "top_contributors": [
    {"symbol": "VRT",  "current_pct": 4.90, "prior_pct": 4.20, "delta_pp": 0.70, "direction": "INCREASED"},
    {"symbol": "ATLC", "current_pct": 1.50, "prior_pct": 0.80, "delta_pp": 0.70, "direction": "NEW"}
  ]
}
```

### GET `/api/drift/timeline`

```json
{
  "rule_id": "CPV-01",
  "timeline": [
    {"date": "2026-05-21", "actual_pct": 9.52, "status": "FAIL", "breach_pp": 4.52},
    {"date": "2026-05-29", "actual_pct": 8.53, "status": "WARN", "breach_pp": 3.53},
    {"date": "2026-06-15", "actual_pct": 8.89, "status": "WARN", "breach_pp": 3.89}
  ]
}
```

---

## Implementation Files

| File | Action | Purpose |
|------|--------|---------|
| `src/portfolio/drift_analyzer.py` | NEW | Core drift computation logic |
| `scripts/run_outcome_ui.py` | ADD endpoints | `GET /api/drift/summary`, `GET /api/drift/timeline` |
| `ui/allocation_intelligence/app.js` | ADD panel | Drift Trends panel in PIS dashboard |
