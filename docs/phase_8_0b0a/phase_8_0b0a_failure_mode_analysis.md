# Phase 8.0B.0A — Failure Mode Analysis

**Date:** 2026-06-04  

---

## Failure Mode Taxonomy

### Failure 1: Provider Outage

**Description:** FMP API is unreachable or returning 5xx errors.

**Current SIH behavior (existing pattern):** `refresh_signals.py` catches exceptions and falls back to the last known-good CSV file. Stale data is surfaced but not blocking.

**FMP behavior should mirror this exactly:**
```
If FMP refresh fails:
  - Log: "[fmp_refresh] FAILED — using stale data from {last_date}"
  - Continue with last successfully fetched CSV (latest_fmp_*.csv)
  - Do NOT block PAR run
  - Surface staleness warning in run_metadata.json warnings[]
```

**Governance:** The system must be **fail-closed on refresh** (no partial writes that corrupt the latest file) but **fail-open on consumption** (stale data is better than no PAR run).

**Recovery path:** On next scheduled refresh, retry automatically. No manual intervention needed for transient outages.

---

### Failure 2: Partial Universe Refresh

**Description:** FMP refresh completes for 600 of 689 symbols; 89 fail due to rate limit or network errors.

**Mitigation:**
1. Refresher writes output only after full universe completes (not per-symbol)
2. Per-symbol errors are logged individually
3. Partial refresh is discarded; `latest_fmp_*.csv` is not updated
4. Retry logic: re-attempt failed symbols in a second pass (match existing Danelfin retry pattern)

**Implementation note:** `refresh_signals.py` currently retries at the symbol level. FMP should use the same retry wrapper.

---

### Failure 3: Rate-Limit Exhaustion

**Description:** Requests are throttled (HTTP 429) mid-refresh.

**Mitigation:**
- Starter plan: 300 calls/minute. Current design uses 240/min (80% of limit) with 250ms sleep.
- On HTTP 429: back off 60 seconds, retry up to 3 times
- If 3 retries fail: log exhaustion event, stop refresh, retain last good data
- Alert operator via run_metadata warning

**Never:** reduce sleep delay during throttle response. Always increase or maintain.

---

### Failure 4: Corrupt or Malformed Payload

**Description:** FMP returns valid HTTP 200 but JSON has unexpected structure, missing fields, or null values.

**Current risk:** FMP changed its API (v3/v4 → /stable/). This can happen again.

**Mitigation:**
1. Field validation on every parsed row: required fields must be present
2. Null values treated as missing (not zero) — stored as empty in CSV
3. Schema version recorded in file header (e.g., `# fmp_schema_version: 1.0`)
4. If >10% of rows have missing required fields: treat as corrupt; don't update latest

**Required fields (fail if absent):**
- `symbol` (always required)
- At least 3 of the 5 key_metrics fields (avoid total failure on one missing field)

---

### Failure 5: Symbol Coverage Gaps

**Description:** FMP returns no data for a symbol (international, small-cap, or missing from FMP universe).

**Expected gap analysis:**
- SIH universe: ~689 symbols including international (TSM, ASML, CVE, SBS, etc.)
- FMP Starter coverage: US exchanges only
- FMP Premium: US + UK + Canada
- FMP Ultimate/Global: broader but not 100%

**Expected coverage gaps with Starter plan:**
- Non-US symbols (~15% of SIH universe): no data returned
- Micro-cap symbols not in FMP database: no data returned
- Coverage gap estimate: ~20% of symbols may return empty

**Mitigation:**
- Treat missing as `null` in output CSV (not an error)
- `latest_fmp_key_metrics.csv` has null/empty for uncovered symbols
- Analytical universe scoring uses null = "no FMP data" (degrades gracefully to current behavior)
- Over time, as SIH universe grows, coverage gap should decrease

**Governance rule:** A symbol with no FMP data receives no FMP scoring boost or penalty. It is treated as if FMP data is unavailable.

---

### Failure 6: API Plan Downgrade or Key Revocation

**Description:** FMP key becomes invalid (payment failure, plan change, key rotation).

**Detection:** All endpoints return HTTP 401 or HTTP 402.

**Impact:** Complete FMP data loss until new key is configured.

**Mitigation:**
1. On consecutive 401/402 responses: log "FMP key may be invalid or plan insufficient"
2. Do NOT mark existing latest files as stale
3. Surface key validation failure in health check
4. Operator must rotate key in `.env` and restart refresh

---

## Fail-Closed vs Fail-Open Decision

| Scenario | SIH Behavior |
|----------|-------------|
| FMP refresh fails | **Fail-open on PAR** — use last good FMP data; run PAR normally |
| FMP refresh succeeds with coverage gaps | **Fail-open per symbol** — nulls for uncovered symbols |
| Corrupt payload | **Fail-closed on write** — don't update `latest_fmp_*.csv` |
| Partial refresh | **Fail-closed on write** — require full universe before updating |
| First-time setup (no FMP data yet) | **Fail-open completely** — FMP columns are null; PAR runs without them |

**Core principle:** FMP data enriches intelligence; it never blocks operations. SIH ran correctly before FMP and must continue to run correctly if FMP data is unavailable.

---

## Governance Requirements

1. All FMP CSV files carry a `sourced_date` field per row
2. `run_metadata.json` records FMP data freshness in the `warnings` array when stale
3. `latest_fmp_*.csv` is only updated on full successful refresh (atomic write via temp file + rename)
4. FMP refresh failures are non-blocking to PAR runs
5. Historical FMP files are immutable once written (append-only index pattern matches ESS history)
