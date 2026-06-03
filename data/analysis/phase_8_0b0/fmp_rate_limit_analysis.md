# FMP Rate Limit Analysis
**Phase**: 8.0B.0 — FMP Capability Audit  
**Probe Date**: 2025-01-30  
**Key Tier**: Free (unregistered / starter)  

---

## Rate Limit Test Results

### Test Methodology
10 rapid sequential requests fired against `GET /stable/quote?symbol=AAPL` with no inter-request delay.

### Observed Results
```
10 requests fired
0 OK (all blocked by plan restriction — 402 Payment Required / 403 Legacy)
0 rate-limit errors (no HTTP 429 observed)
Elapsed: 2.81 seconds for 10 requests
```

### Interpretation

The test did not surface any rate-limiting behavior because **all requests were rejected at the plan authorization layer before reaching rate limiting logic**. Rate limiting is enforced after plan authorization, so the free tier's plan restriction short-circuits before the rate limiter is reached.

**No meaningful rate limit data could be collected from the free tier.**

---

## FMP Published Rate Limits (From Documentation)

*The following is from FMP's published documentation as of early 2025.*

### Free Tier
| Metric | Limit |
|---|---|
| API calls / day | ~250 (undocumented; observed to be near-zero for fundamental endpoints) |
| Calls / minute | Not specified |
| Concurrent connections | 1 |
| Endpoints accessible | Price quotes (stable), company profile (basic), public company list |

### Starter Tier ($0–$14/month range)
| Metric | Limit |
|---|---|
| API calls / month | 50,000 |
| Endpoints accessible | Basic financials (annual only), quotes, profiles |
| Historical depth | 5 years |
| Real-time data | Delayed (15 min) |

### Basic Tier (~$19/month)
| Metric | Limit |
|---|---|
| API calls / month | 250,000 |
| Endpoints accessible | Full financials, growth, key metrics, analyst estimates, earnings |
| Historical depth | 10+ years |
| Real-time data | Real-time |
| Rate limit | ~300 req/min |

### Premium Tier (~$49/month+)
| Metric | Limit |
|---|---|
| API calls / month | 750,000+ |
| Additional endpoints | DCF, earnings call transcripts, insider transactions |
| Rate limit | ~1,000 req/min |

---

## Operational Rate Limit Analysis for FMI

Assuming the **Basic tier (~$19/month, 250,000 calls/month)**:

### Calls Per Symbol (Full FMS Refresh)

For each symbol requiring a full FMS score update:

| Endpoint | Calls | Notes |
|---|---|---|
| `stable/income-statement?period=annual` | 1 | Revenue/EPS history |
| `stable/income-statement?period=quarter` | 1 | Quarterly detail |
| `stable/cash-flow-statement?period=annual` | 1 | FCF history |
| `stable/financial-growth` | 1 | Pre-computed growth rates |
| `stable/key-metrics-ttm` | 1 | PEG, PE ratios |
| `stable/analyst-estimates` | 1 | Forward estimates + analyst count |
| `stable/earnings-surprises` | 1 | EPS surprise history |
| `stable/ratios-ttm` | 1 | Forward PE, PEG cross-check |
| **Total per symbol** | **8** | |

### Monthly Call Budget Scenarios

| Universe Size | Full Refresh Freq | Calls/Month | % of 250K Budget | Feasible? |
|---|---|---|---|---|
| Top 25 symbols | Weekly | 25 × 8 × 4 = 800 | 0.3% | YES |
| Top 100 symbols | Weekly | 100 × 8 × 4 = 3,200 | 1.3% | YES |
| Full universe (2,586) | Weekly | 2,586 × 8 × 4 = 82,752 | 33% | YES |
| Full universe (2,586) | Daily | 2,586 × 8 × 22 = 455,136 | 182% | NO — exceeds budget |
| Full universe (2,586) | Twice/week | 2,586 × 8 × 8 = 165,504 | 66% | YES |

### Practical Rate Limiting Strategy

Assuming 300 req/min on Basic tier:
- Sequential batch at 0.2s delay: 300 calls/min × 60 = 18,000 calls/hour
- Full universe (2,586 symbols × 8 calls) = 20,688 calls ≈ **~1.15 hours per full sweep**
- Practical approach: batch overnight run, not real-time

### Recommended Operational Approach

1. **Batch frequency**: Weekly FMS refresh (not daily) — keeps well within call budget
2. **Per-call delay**: 200ms between calls to avoid burst violations
3. **Priority queue**: Score top 25 symbols on every run; top 100 weekly; full universe monthly
4. **Caching**: Cache responses with TTL of 7 days to avoid redundant calls within a week
5. **Error handling**: Implement exponential backoff with max 3 retries on 429 responses

---

## Rate Limit Risk Summary

| Risk | Severity | Mitigation |
|---|---|---|
| Exceeding 250K calls/month on full daily universe | HIGH | Weekly batching only; daily updates for top-N only |
| Rate throttling (429) on burst requests | MEDIUM | 200ms inter-call delay |
| Plan restriction cutting off mid-run | LOW | Monitor remaining call quota; alert at 80% |
| API key exposure | MEDIUM | Keep in `.env`, never commit; rotate quarterly |

---

## Note on Current Key Status

The current API key (`7OjmiAAsVH4gor067gCkGeqDJzBUg0Je`) returns Legacy/402 errors on all fundamental endpoints. **This key must be upgraded to a paid plan before any FMS data collection is possible.** The rate limit analysis above applies to the paid tier post-upgrade.
