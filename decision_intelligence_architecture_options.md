# Decision Intelligence Layer — Architecture Options

**Date:** 2026-06-10

---

## Option A: Static Synthesis (Deterministic Rules on Existing Data)

**Approach:** Compute operator posture and commentary entirely from signals already in `_lastAnalysisData`. No new data sources.

**Implementation:**
- A `computeDIL(symbol, ac, fs, fmp, ucf, ov)` function runs deterministic rules
- Outputs: `posture_label`, `posture_color`, `key_points[]`, `rationale_text`
- Runs client-side in JS at profile-expand time (no API call)

**Inputs available today:**
- ESS + Fidelity StarMine rating
- Consensus Matrix (ESS/Yahoo/Zacks alignment classification)
- ABR, price target, upside %
- FMP EPS surprise, beat rate, revenue growth, analyst counts
- UCF label and score

**Example output for PRIM:**
```
INVESTIGATE BEFORE ACTING

Key Points:
• PARTIAL ALIGNMENT: ESS BEARISH, but Street is BUY (14 analysts)
• Last EPS surprise was a -30.6% miss (Q1 YoY EPS growth: +51% — prior quarters strong)
• Beat rate over 8 quarters: 85.7% — historically strong executor
• ABR: 1.86 → strong buy consensus with 18% upside to target

Assessment: The BEARISH ESS may reflect a single-quarter EPS miss against a strong
historical track record. Analyst targets may not reflect post-Q1 revisions.
Upside to target ($143.79) is substantial. Investigate before reducing.
```

**Pros:** No new infrastructure, fully deterministic, fast, works offline  
**Cons:** Cannot explain price-action events (no 1D return data), no "what changed today" capability

**Complexity:** Low — 1–2 days implementation  
**Governance burden:** Low — no external calls

---

## Option B: Price + Earnings Context Layer (yfinance)

**Approach:** Add lightweight yfinance calls for: current price, 1D/5D return, 52-week range, next earnings date.

**yfinance is already installed** (`data.signals` pipeline uses it). The existing `_build_signal_source_metadata()` function already uses yfinance indirectly. Adding a new `_build_price_context(symbols)` function would fetch:
- `info['currentPrice']`, `info['52WeekHigh']`, `info['52WeekLow']`
- `history(period='5d')` → 1D and 5D returns
- `info['earningsDate']` (next quarterly earnings)
- `info['forwardPE']`, `info['priceToBook']`

**Governance:** Already approved via existing yfinance usage. Display-only. No scoring impact.

**Example output added to PRIM:**
```
INVESTIGATE BEFORE ACTING

Market Context:
• Price today: $121.84  (−15.2% today)
• 5D return: −16.8%
• 52W range: $94.20 – $152.40 (currently at 18th percentile)
• Next earnings: 2026-08-06 (est.)

Interpretation: Stock is at 1-year lows following a sharp move today.
ESS BEARISH + Street BUY + recent price collapse = high-priority investigate case.
```

**Pros:** Enables the "what happened today" answer that matters most  
**Cons:** Requires live network call at render time; adds 0.5–2s latency; yfinance can fail/timeout

**Complexity:** Medium — 2–3 days  
**Governance burden:** Low — same as existing yfinance usage

---

## Option C: Cached Price Context (nightly background fetch)

**Approach:** Fetch price context nightly (or at PAR generation time) and persist to `data/current/price_context.csv`. DIL reads from this cached file — no live calls at render time.

**Fields to cache:** symbol, date, current_price, return_1d, return_5d, return_1m, high_52w, low_52w, pct_from_52w_high, next_earnings_date

**Integration point:** Add to `run_analysis()` or as a standalone script callable before analysis.

**Pros:** Fast render, works offline after nightly refresh, no render-time latency  
**Cons:** Price data is one day stale; doesn't capture intraday events; adds build complexity

**Complexity:** Medium — 2–3 days  
**Governance burden:** Low — data stored locally, same as other signals

---

## Option D: Real-Time News Integration (External API)

**Approach:** Integrate a news headline API (NewsAPI, Benzinga, Polygon.io) to fetch 3–5 recent headlines per symbol on demand.

**Pros:** Enables catalyst investigation ("earnings miss", "CEO departure", "contract win")  
**Cons:** Requires API key + cost; content moderation burden; rate limits; latency; governance complexity; inconsistent coverage

**Complexity:** High — 1–2 weeks  
**Governance burden:** HIGH — financial news content policy, third-party dependency, cost management

**Recommendation:** Defer to Phase 3. Address after Option A+B are validated.

---

## Recommended Implementation Path

### Phase 1 (NOW): Option A — Static Synthesis

Implement `computeDIL()` as a pure JS function. No new data sources, no API calls. Delivers 70% of the operator value with minimal risk.

Target postures:
- `HIGH_CONFIDENCE_REDUCTION` — ESS bearish + Street bearish + EPS miss + divergence confirmed
- `ACTIONABLE` — ESS bearish + reasonable analyst consensus + no conflicting signals
- `INVESTIGATE_BEFORE_ACTING` — PARTIAL_ALIGNMENT with EPS miss OR recent price volatility suspected
- `MONITOR` — single weak signal, no corroboration
- `WAIT_ADDITIONAL_DATA` — signals available but consensus refresh stale > 14 days
- `CONFLICTING_EVIDENCE` — MAJOR_DIVERGENCE between ESS and Street

### Phase 2 (NEXT SPRINT): Option B — yfinance Price Context

Add `_build_price_context()` to the server-side signal pipeline. Include in analysis result payload. DIL reads `price_context_by_symbol` and adds market context layer.

### Phase 3 (BACKLOG): Option D — News Integration

Design separate news ingestion pipeline with governance framework. Keep DIL display-only regardless.
