# Phase 8.0B.0A — FMP Rate Limit Analysis

**Date:** 2026-06-04  
**Type:** Architecture review — no implementation

---

## CRITICAL FINDING: Current API Key is FREE Plan

The live probe confirmed all fundamental endpoints (income statements, key metrics, earnings, analyst estimates) return **HTTP 402 Payment Required**. The current API key `7OjmiAAsVH4gor067gCkGeqDJzBUg0Je` is on the **FREE** plan.

Only the `profile` endpoint returned data (profile is included in Free).

The v3/v4 legacy API is completely blocked with "Legacy Endpoint" messages, confirming FMP has migrated fully to the `/stable/` API.

---

## Plan Comparison Matrix

| Plan | Price | Calls/Minute | Calls/Day | Fundamental Data | Bulk/Batch | Coverage |
|------|-------|-------------|----------|-----------------|-----------|---------|
| **FREE** (current) | $0 | — | **250/day** | Sample only (~87 symbols) | No | ~87 symbols |
| **Starter** | $19/mo | **300/min** | ~432,000/day | Yes — Annual only, 5yr history | No | US only |
| **Premium** | $49/mo | **750/min** | ~1,080,000/day | Yes — Full, 30yr history | No | US + UK + Canada |
| **Ultimate** | $99/mo | **3,000/min** | ~4,320,000/day | Yes — Full, 30yr history | **Yes** | Global |

---

## Scale Analysis: Can All Data Be Refreshed Daily?

### Current Universe: 689 Symbols

**Priority endpoints (per-symbol calls needed):**

| Endpoint | Frequency Needed | Calls per Universe |
|----------|-----------------|-------------------|
| `/earnings?symbol=X&limit=8` | Quarterly (after earnings) | 689 calls/quarter |
| `/income-statement-growth` | Quarterly | 689 calls/quarter |
| `/key-metrics-ttm?symbol=X` | Daily | **689 calls/day** |
| `/grades?symbol=X` | Weekly | 689 calls/week |
| **Total daily per-symbol calls** | | **~689 to 1,400 calls/day** |

**With bulk endpoints (Ultimate plan):**
| Endpoint | Calls | Returns |
|----------|-------|--------|
| `/key-metrics-ttm-bulk` | **1 call** | All symbols |
| `/earnings-surprises-bulk?year=2026` | **1 call** | All symbols |
| `/income-statement-growth-bulk` | **1 call/quarter** | All symbols |
| `/upgrades-downgrades-consensus-bulk` | **1 call** | All symbols |
| **Total with bulk** | **~4–6 calls/day** | Full universe |

---

## Plan Feasibility by Scale

### 689 Symbols (Current)

| Plan | Per-Symbol Approach | Bulk Approach | Verdict |
|------|--------------------|----|---------|
| FREE | ❌ 250/day limit; only 87 symbols covered | ❌ No bulk access | **NOT VIABLE** |
| Starter ($19/mo) | ✅ 689 calls << 432K/day; quarterly earnings = 2,756 calls/quarter | ❌ No bulk | **VIABLE — per-symbol** |
| Premium ($49/mo) | ✅ Same + 30yr history + 750/min (faster refresh) | ❌ No bulk | **VIABLE — per-symbol, faster** |
| Ultimate ($99/mo) | ✅ Best | ✅ 4–6 bulk calls for full universe | **OPTIMAL** |

### 2,500 Symbols

| Plan | Per-Symbol Daily | Calls Budget | Verdict |
|------|-----------------|-------------|---------|
| Starter | ~2,500/day | 432K/day | ✅ Viable |
| Premium | ~2,500/day | 1M+/day | ✅ Viable |
| Ultimate with bulk | 4–6 calls/day | — | ✅ Optimal |

### 5,000 Symbols

| Plan | Per-Symbol Daily | Calls Budget | Verdict |
|------|-----------------|-------------|---------|
| Starter | ~5,000/day + earnings refresh | 432K/day | ✅ Viable (but tight on earnings refresh cycle) |
| Ultimate with bulk | 4–6 calls/day | — | ✅ Optimal |

---

## Refresh Timing Analysis

**Starter plan — 300 calls/minute:**

| Scenario | Time Required |
|----------|-------------|
| 689 symbols, key_metrics_ttm (1 call each) | 689/300 = **2.3 minutes** |
| 689 symbols, earnings_surprises (1 call each) | 2.3 minutes |
| 689 symbols, income_statement_growth (1 call each) | 2.3 minutes |
| **Full daily refresh (689 symbols, 4 endpoints)** | ~10 minutes total |

**Ultimate plan — bulk endpoints:**

| Scenario | Time Required |
|----------|-------------|
| key_metrics_ttm_bulk (all symbols) | **< 5 seconds** |
| earnings_surprises_bulk | < 5 seconds |
| income_statement_growth_bulk | < 5 seconds |
| **Full daily refresh (any scale)** | **< 2 minutes** |

---

## Recommended Plan

**For current scale (689 symbols): Starter plan ($19/mo)**
- 300 calls/minute is more than sufficient
- Per-symbol approach completes in < 15 minutes
- Full fundamentals + annual data (5yr history sufficient for growth trends)
- US coverage covers ~85% of SIH universe (non-US securities degrade gracefully)

**For scale ≥ 2,500 or if bulk efficiency is needed: Ultimate plan ($99/mo)**
- Bulk endpoints reduce 689 per-symbol calls to 4–6 calls total
- 5,000 symbols feasible in < 2 minutes
- Required for production-scale operations

**Minimum viable: Starter plan ($19/mo)**  
**Recommended: Starter for now; upgrade to Ultimate at 2,500+ symbols**

---

## Rate Limit Safety Design

For per-symbol refreshes on Starter (300/min):
- SIH already throttles Danelfin at ~5/second (consistent pattern)
- Recommended: 250ms sleep between calls = 240 calls/minute (20% below limit)
- This matches the existing `refresh_signals.py` pattern

For pre-market readiness (target: 04:00–04:30 window):
- 689 symbols × 4 endpoints = 2,756 calls
- At 240/min: ~11.5 minutes → **completes well within 30-minute window** ✅
