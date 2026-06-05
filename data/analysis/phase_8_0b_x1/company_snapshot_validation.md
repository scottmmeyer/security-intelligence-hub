# Company Snapshot Validation — Phase 8.0B.X.1

## Validation Symbols

| Symbol | Company | HQ | Business Desc | Cap Tier | Status |
|--------|---------|-----|---------------|----------|--------|
| VRT | Vertiv Holdings Co | Westerville, OH, United States | ✓ | LARGE | PASS |
| DELL | Dell Technologies Inc. | Round Rock, TX, United States | ✓ | LARGE | PASS |
| ARW | Arrow Electronics, Inc. | Centennial, CO, United States | ✓ | MID | PASS |
| PSX | Phillips 66 | Houston, TX, United States | ✓ | LARGE | PASS |
| CAH | Cardinal Health, Inc. | Dublin, OH, United States | ✓ | LARGE | PASS |
| SNX | TD SYNNEX Corporation | Fremont, CA, United States | ✓ | MID | PASS |
| TSM | Taiwan Semiconductor Manufacturing Co. | Hsinchu City, Taiwan | ✓ | MEGA | PASS |
| ASML | ASML Holding N.V. | Veldhoven, Netherlands | ✓ | MEGA | PASS |
| CVE | Cenovus Energy Inc. | Calgary, AB, Canada | ✓ | MID | PASS |

**9/9 symbols PASS**

## Side-Effect Validation

| Check | Method | Result |
|-------|--------|--------|
| Composite score unchanged | pytest test suite | ✓ PASS |
| Signal rankings unchanged | pytest test suite | ✓ PASS |
| Recommendations unchanged | pytest test suite | ✓ PASS |
| CCL thresholds unchanged | pytest test suite | ✓ PASS |
| CRA proposal unchanged | pytest test suite | ✓ PASS |
| Test count | pytest -q | 1,004 passed |

## Display Validation

- Company names populated for all 9 symbols
- HQ city + state + country renders correctly
- Business descriptions truncated to ≤250 characters
- Section title changed from "Company Context" to "Company Snapshot"
- Cap Tier badge appears only when available
- Section does not suppress when profile data missing (shows "Unknown")

## Regression Notes

No changes to:
- Composite score calculation
- CCL thresholds
- Signal authority weights
- Deployment queue ranking
- CRA rotation proposal logic
- Any scoring pipeline code
