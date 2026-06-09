# FVI Config Validation

Repository: security-intelligence-hub  
Date: 2026-06-09

## Validation: config/fvi_peer_groups.yaml

### Load Test

Config loads successfully via `load_fvi_registry()` with all 15 fund vehicles.

### Entry Completeness

| Symbol | peer_group | fvi_tier | retain_advisory | confidence | data_source |
|---|---|---|---|---|---|
| VOO | US Large Blend ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| VB | US Small Blend ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| VO | US Mid Blend ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| VEA | Foreign Large Blend ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| VWO | Diversified EM ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| FXAIX | US Large Blend Index Fund | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| BND | US Core Bond ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| BNDX | World Bond ETF | ELITE | True | HIGH | MANUAL_ADVISORY_ESTIMATE |
| DODFX | Foreign Large Value | HIGH | True | MEDIUM | MANUAL_ADVISORY_ESTIMATE |
| FBTC | Bitcoin Spot ETF | HIGH | True | MEDIUM | MANUAL_ADVISORY_ESTIMATE |
| FETH | Ethereum Spot ETF | HIGH | True | MEDIUM | MANUAL_ADVISORY_ESTIMATE |
| FIGFX | Foreign Large Growth | MEDIUM | False | LOW | MANUAL_ADVISORY_ESTIMATE |
| FMCSX | US Mid Cap Active Fund | MEDIUM | False | LOW | MANUAL_ADVISORY_ESTIMATE |
| FCPGX | US Small Growth Active Fund | MEDIUM | False | LOW | MANUAL_ADVISORY_ESTIMATE |
| XRP | XRP/Altcoin Digital Asset ETF | MEDIUM | False | LOW | MANUAL_ADVISORY_ESTIMATE |
| FSOL | Solana/Altcoin Digital Asset ETF | LOW | False | LOW | MANUAL_ADVISORY_ESTIMATE |

### Graceful Degradation Tests

- Missing config file: returns {} (no error)
- Malformed YAML: returns {} (no error)
- Empty funds section: returns {} (no error)
- Symbol not in registry: get_fvi_record returns None (no error)
- Empty portfolio holdings: build_fvi_data_for_holdings returns {} (no error)

### Advisory Disclaimer Compliance

All 15 entries carry `data_source: MANUAL_ADVISORY_ESTIMATE`. No entry claims provider-validated data. Scores are clearly labelled as estimated.
