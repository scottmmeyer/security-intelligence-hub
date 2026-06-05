# Phase 23.0A.1 — Q6: Future Tax Data Acquisition Options

**Scope**: Research only. No implementation. Options for how SIH could acquire or receive tax context data from sources beyond manual operator entry.

---

## Current State: Manual Operator Entry

All tax context (YTD realized gain/loss, potential losses, carryforward, tax year) is entered manually by the operator in the Tax Context Panel. This is the MVP baseline.

- **Complexity**: None — text fields.
- **Reliability**: Operator-dependent. Values are only as accurate as what the operator knows and enters.
- **Operator burden**: Moderate — requires periodic re-entry as YTD position changes throughout the year.
- **Frequency of updates**: Likely quarterly or after significant trading activity.
- **Data staleness risk**: High if operator forgets to update.

---

## Option A — Structured CSV Import

Operator uploads a structured CSV containing their tax summary data (manually exported from brokerage or tax software).

### Description
SIH accepts a tax context CSV file alongside the portfolio CSV, or via a dedicated upload in the Tax Context Panel. A defined schema (similar to how portfolio CSVs are accepted today) maps to the four tax fields.

### Estimated Schema
```
tax_year, net_realized_ytd, potential_additional_losses, capital_loss_carryforward
2025, -24730.00, 14236.00, 0.00
```

### Complexity: LOW–MODERATE
- New import endpoint: `POST /api/operator/tax-state/import` (similar to portfolio upload).
- CSV parsing: ~20 lines, existing `csv.DictReader` pattern from the codebase.
- UI: add a "Browse CSV" button to Tax Panel.

### Reliability: MODERATE–HIGH
- As reliable as the source CSV. If exported from brokerage, data reflects account records.
- No browser-to-brokerage integration required.
- Operator still controls when to export and import.

### Operator Burden: LOW
- One-click export from brokerage → import into SIH.
- No manual transcription of dollar amounts.

### Risk: LOW
- Same security profile as current manual entry (local only).
- No credentials or account data transmitted.

### Recommendation Priority: **HIGH** — most practical near-term upgrade.

---

## Option B — Tax Software Report Integration

Import a tax summary report exported from commercial tax preparation software (TurboTax, H&R Block, TaxAct, Drake, etc.).

### Description
Map fields from a tax software summary export (typically PDF or structured export) to SIH's four tax fields. Realistically, a TurboTax "Tax Summary" or "Capital Gains Worksheet" PDF export would be the primary format.

### Formats Available
| Software | Export Format | Machine-Readable? |
|---|---|---|
| TurboTax | PDF, tax return XML (.tax) | XML possible via `.tax` file; PDF requires parsing |
| H&R Block | PDF | Not machine-readable without PDF extraction |
| TaxAct | XML, PDF | XML possible |
| Drake Tax | PDF | Not machine-readable |

### Complexity: MODERATE–HIGH
- PDF extraction requires `pdfplumber` or `pdfminer.six` — adds dependency.
- XML formats differ by software and version — fragile parsing.
- Field mapping is not standardized across vendors.

### Reliability: HIGH (for prior-year data)
- Prior-year carryforward is very accurate from tax return data.
- YTD figures from mid-year tax software reports are uncommon.

### Operator Burden: MODERATE
- Requires locating and exporting the right report from tax software.
- Many operators won't have mid-year tax exports.

### Best Use Case
Carryforward import only — prior-year carryforward from completed tax return is stable, accurate, and doesn't require mid-year updates. This is a narrower but more reliable use case than full YTD import.

### Recommendation Priority: **MEDIUM** — useful for carryforward field only; full YTD coverage is impractical.

---

## Option C — Brokerage 1099 / Gain-Loss Report Import

Import a brokerage-generated gain/loss report or year-to-date realized gain/loss statement (typically CSV or PDF).

### Description
Most brokerages (Schwab, Fidelity, TD Ameritrade, Interactive Brokers, etc.) offer downloadable realized gain/loss reports in CSV format. These contain per-position detail as well as totals that map to SIH's `net_realized_ytd` field.

### Format Examples
| Brokerage | Export Format | YTD GL Column |
|---|---|---|
| Schwab | CSV ("Realized Gain/Loss") | `Net Gain/Loss` |
| Fidelity | CSV | `Net Gain/Loss` |
| TD Ameritrade / Schwab | CSV | `Total Gain/Loss` |
| Interactive Brokers | CSV, FLEX Report | `Realized P&L` |
| eTrade | CSV | `Net Gain or Loss` |

### Complexity: MODERATE
- Each brokerage uses a slightly different CSV format and column naming.
- A format detection + normalization layer is needed (similar to how the portfolio ingestion pipeline handles format variations today).
- Could start with one brokerage format and expand.
- No API integration required — file upload only.

### Reliability: HIGH
- Brokerage records are authoritative for realized gains/losses.
- YTD data is current as of the export date.
- Per-position data also available — could enable per-holding cost basis enrichment (future feature).

### Operator Burden: LOW–MODERATE
- Requires periodic brokerage report downloads.
- Some brokerages offer automatic email delivery of monthly statements.
- Operator still controls upload timing.

### Recommendation Priority: **MEDIUM-HIGH** — high reliability, moderate complexity. Best option if operator is comfortable with brokerage CSV exports (which they likely already are, given portfolio CSV workflow).

---

## Option D — Direct Brokerage API Integration

Connect to a brokerage API (Schwab API, Fidelity Wealth Management API, IBKR API, or Plaid as an aggregator) to pull real-time or near-real-time realized gain/loss data.

### Description
SIH authenticates with a brokerage API using OAuth2 and requests account-level gain/loss summary. Tax state is updated automatically without operator action.

### APIs Available
| Provider | API | Notes |
|---|---|---|
| Schwab Developer | OAuth2, REST | Public API available; requires developer registration |
| Interactive Brokers | IBKR Web API / TWS API | Comprehensive; complex setup |
| Plaid | `/investments/transactions` | Aggregator; normalizes across brokerages; subscription cost |
| Alpaca | REST + OAuth | Limited tax data |
| Fidelity | Wealth Management APIs | Restricted to institutional partners |

### Complexity: HIGH
- OAuth2 flows require secure credential storage.
- Token refresh, rate limiting, error handling.
- API terms vary; some restrict non-institutional access.
- Plaid adds a subscription cost layer.

### Reliability: VERY HIGH
- Real-time authoritative data.
- No manual re-entry or staleness risk.

### Operator Burden: LOW (after setup)
- One-time OAuth authorization.
- Automated refresh thereafter.

### Recommendation Priority: **LOW for current phase** — out of scope for local advisory tool. Introduces significant complexity, credential management, and external dependency. Revisit if SIH evolves toward a hosted or multi-user platform.

---

## Comparison Matrix

| Option | Complexity | Reliability | Operator Burden | Data Freshness | Priority |
|---|---|---|---|---|---|
| A — Manual Entry (current) | None | Operator-dependent | Moderate | Manual | N/A (deployed) |
| B — CSV Import | Low | Moderate-High | Low | Export-date | HIGH |
| C — Tax Software Report | Moderate-High | High (carryforward only) | Moderate | Prior-year only | MEDIUM |
| D — Brokerage Gain/Loss CSV | Moderate | High | Low-Moderate | Export-date | MEDIUM-HIGH |
| E — Brokerage API | High | Very High | Low (post-setup) | Real-time | LOW |

---

## Recommended Roadmap

| Phase | Enhancement | Effort |
|---|---|---|
| Near-term | Option B: CSV import (`POST /api/operator/tax-state/import`) | ~1 day |
| Near-term | Option D: Schwab gain/loss CSV parser (single format first) | ~1 day |
| Mid-term | Option C: Carryforward import from tax return XML (TurboTax/TaxAct) | ~2 days |
| Long-term | Option E: Brokerage API integration (if platform evolves) | 2+ weeks |

The CSV import path (Option B) pairs well with the existing portfolio CSV workflow — operators who are already comfortable uploading portfolio CSVs will understand uploading a tax summary CSV. This is the most natural next step.

---

## Verdict: Q6

Current manual entry is appropriate for MVP. The clearest upgrade path is brokerage gain/loss CSV import (Option D) or a generic tax context CSV import schema (Option B). Direct API integration (Option E) is out of scope for the current local advisory tool architecture.

**No implementation recommended in Phase 23.0A.1 — documentation only.**
