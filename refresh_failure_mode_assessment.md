# Refresh Failure Mode Assessment

Repository: security-intelligence-hub  
Date: 2026-06-09

## Identified Failure Modes

### 1. Provider Returns No Data (Silent Null)

**Location:** `fetch_zacks_data()` in `src/scoring/fetch_zacks_scores.py`  
**Behavior:** If the HTTP response is 200 but the page contains no parseable rank/score, returns `(None, None, ...)`. The row is still written with `sourced_date=today` and empty score fields.

**Evidence today:** 31 Zacks symbols had `sourced_date=2026-06-09` but empty `zacks_rank` and `zacks_score`.

**Badge result: FRESH** — false positive for affected symbols.

**Severity:** LOW for individual symbols (illiquid/unlisted symbols expected); HIGH if widespread.

---

### 2. HTTP Error (Non-200 Response)

**Location:** `fetch_zacks_data()` line ~70, `fetch_danelfin_score()` line ~88  
**Behavior:**
- Zacks: `except HTTPError` → returns `(None, None, ...)` → row written with empty fields + today date
- Danelfin: `except requests.RequestException` → returns `(None, None)` → row written with empty fields + today date

**Badge result: FRESH** — false positive if this happens for all symbols.

**Severity:** MEDIUM — HTTP errors are silently absorbed; batch continues.

---

### 3. Timeout

**Location:** `fetch_danelfin_score()` with `timeout=_REQUEST_TIMEOUT`  
**Behavior:** `requests.RequestException` catches timeout. Row written with empty score + today date.

**Badge result: FRESH** — false positive.

**Severity:** LOW individually; HIGH if systematic timeout affects most symbols.

---

### 4. Rate Limit

**Behavior:** Would manifest as 429 HTTP status → caught by HTTPError handler → empty row written → `sourced_date=today`.

**Badge result: FRESH** — false positive.

**Severity:** MEDIUM.

---

### 5. Partial Field Failure

**Evidence today (Yahoo):** `eps_growth_5yr` = 0/697 rows. All other Yahoo fields populated. The scraping logic for this specific field may have failed silently (e.g., the HTML element it parses was changed by the provider).

**Badge result: FRESH** — no way to detect this from the badge. Operator has no visibility that a key field is universally missing.

**Severity:** HIGH — invisible data quality degradation, badge shows FRESH.

---

### 6. Stale Provider Response (Cached/Outdated)

**Behavior:** Provider HTML returns stale cached content with old data. Row written with old values and `sourced_date=today`. No mechanism in the current code to detect stale provider-side caching.

**Badge result: FRESH** — data is today but content is stale.

**Severity:** MEDIUM — data quality issue invisible to operator.

---

### 7. Authentication Failure

**Not applicable** to current providers. Zacks and Danelfin use no-auth HTML scraping. Yahoo uses no-auth API. No API key authentication for these three.

---

### 8. Process Crash After Partial Write

**Behavior:** If the refresh process crashes mid-batch, some symbols will have today's date and some won't. The badge will show FRESH if any row has today's date.

**Badge result: FRESH** — partial refresh presented as complete.

**Severity:** LOW for first-party (crash would be logged), MEDIUM for operator.

---

## Can Any Failure Path Incorrectly Produce a FRESH Badge?

**YES.** Every failure mode that still results in a row being written with `sourced_date=today` produces a FRESH badge regardless of data quality.

The following failures produce FRESH with no valid data:
- Provider returns no data (null parsing)
- HTTP error (non-200)
- Timeout
- Rate limit
- Partial field failure (other fields populated)

Only a **complete process crash** before any file writes, or a provider being **entirely unavailable**, would result in a STALE badge.

---

## Recommended Detection Improvements

1. Add a `data_coverage_pct` metric to `_signal_status()` — what percentage of symbols have non-empty scores today?
2. Add per-field coverage to the status response for Yahoo (since partial-field failure is real today with eps_growth_5yr).
3. Badge should show FRESH_PARTIAL when coverage < 95% of expected symbols.
4. Log parse failures per symbol with reason code for operator audit trail.
