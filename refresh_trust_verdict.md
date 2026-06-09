# Refresh Trust Verdict

Repository: security-intelligence-hub  
Date: 2026-06-09

---

## 1. Are the Current Freshness Badges Trustworthy?

**Partially.** The badge correctly indicates that a refresh was **attempted** today. It does not guarantee that the refresh produced valid data.

Specifically:
- The badge reflects `max(sourced_date in file) == today`
- A row is written with `sourced_date=today` **whether or not data was returned**
- The badge cannot distinguish between "refreshed with valid data" and "refreshed but got null"

For routine operations where provider success rates are high (as today: Zacks 95.6%, Danelfin 100%, Yahoo 99.9%), the badge is a reliable indicator.

**The badge is NOT reliable when:**
- Provider scraping changes break field parsing (Yahoo `eps_growth_5yr` = 0/697 today)
- Systematic null returns for a symbol class (Zacks 31/702 no-data rows)
- Silent partial failures (any field goes to 0% coverage without operator alert)

---

## 2. Did the Latest Refresh Actually Update Provider Data?

**Yes, substantially.** All three providers ran today and updated data for the majority of the universe:

| Provider | Symbols Updated | Coverage | Data Quality |
|---|---|---|---|
| Zacks | 702 symbols with today's date | 702/700+ eligible | 671/702 (95.6%) with score data |
| Danelfin | 497 symbols | High-conviction universe | 497/497 (100%) with score |
| Yahoo | 697 symbols | Broad universe | 696/697 (99.9%) with at least one field; eps_growth_5yr = 0% |

**Concern:** Yahoo `eps_growth_5yr` was empty for all 697 symbols today. This is a real data quality event. The badge shows FRESH but this field is silently degraded.

---

## 3. Can Any Failure Path Incorrectly Produce a FRESH Status?

**Yes.** The following failure paths produce an incorrect FRESH badge:

| Failure | FRESH Badge? | Operator Sees |
|---|---|---|
| Provider returns null for symbol | Yes | FRESH — no indication of partial failure |
| HTTP 4xx/5xx error per symbol | Yes | FRESH — error absorbed silently |
| Request timeout | Yes | FRESH — timeout absorbed silently |
| Field-level parsing failure (all symbols) | Yes | FRESH — field is empty across board, badge is still FRESH |
| Partial batch completion | Yes (if any symbol wrote today) | FRESH — badge does not indicate batch completeness |

The most significant confirmed case today: **Yahoo `eps_growth_5yr` = 0/697** — a systematic field failure that produces FRESH despite that specific data dimension being completely absent.

---

## 4. Recommended Improvements

### Priority 1 (High — trust-critical)

**Add data coverage check to `_signal_status()`.**

For each provider, compute:
```python
today_rows = sum(1 for r in rows if r['sourced_date'] == today)
data_rows  = sum(1 for r in rows if r['sourced_date'] == today and r.get(primary_score_field))
coverage_pct = data_rows / today_rows if today_rows else 0
```

Expose `coverage_pct` in the API response and render it alongside the badge.

### Priority 2 (High — trust-critical)

**Introduce FRESH_PARTIAL badge state.**

If `coverage_pct < 0.95` or any primary field has 0% coverage today, show:
- FRESH (≥95% data coverage)
- FRESH_PARTIAL (<95% data coverage — some symbols have no data)
- STALE (file has no today entries)

This would have caught the Yahoo `eps_growth_5yr` failure and the 31 Zacks null returns.

### Priority 3 (Medium)

**Log null returns separately from successful fetches.** Currently "no data" and "HTTP error" produce identical output (empty row + today date). A per-symbol result code would enable audit.

### Priority 4 (Low)

**Reconcile `_is_stale()` vs `_sourced_date()`** — refresh_signals.py uses first-row date; run_outcome_ui.py uses max date. Standardize to max for consistency.

---

## Summary Verdict

The freshness badges accurately reflect refresh execution for today's run. Zacks and Yahoo completed with high success rates. Danelfin was 100% successful. However:

1. The badge architecture is **completion-based**, not **data-quality-based**.
2. The Yahoo `eps_growth_5yr` field degradation (0/697 today) is invisible to the operator from the badge alone.
3. 31 Zacks symbols with `sourced_date=today` but empty scores represent a known expected condition (illiquid/unlisted symbols) but are indistinguishable from scraping failures.
4. Any systematic provider failure that still allows rows to be written will produce FRESH badges.

Recommended action: implement `coverage_pct` field in signal status and FRESH_PARTIAL badge state before the next investor or bank demonstration.
