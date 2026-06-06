# Dislocation Benchmark Assessment
## ISSUE-12 Assessment — June 5, 2026

---

## 1. The Benchmark Problem

The purpose of a benchmark is to answer: "Did the dislocation detection add
informational value relative to what a passive investor would have earned
without it?"

A useful benchmark must be:
1. **Investable** — reflects a real, executable alternative
2. **Comparable** — has similar risk characteristics to the detection universe
3. **Consistently available** — price history accessible without bespoke sourcing
4. **Honest** — not trivially easy to beat due to selection bias

---

## 2. Option A — SPY (S&P 500 Total Return)

**Pros:**
- Universally available, liquid, low-cost investable proxy
- Standard academic and practitioner benchmark
- No ambiguity in construction
- Historical prices freely available via yfinance

**Cons:**
- SIH detects dislocations in a concentrated portfolio of large-cap US equities
  heavily overlapping with S&P 500 — this makes SPY comparison a near-apple-to-
  apple in many cases but not all (international ADRs, small-caps, etc.)
- SPY includes sector exposure that may not match a given detection cohort
- A pure-beta portfolio manager would be compared against SPY; SIH operators
  are running a concentrated alpha mandate, so a higher bar may be appropriate

**Verdict:** Use as the primary benchmark. Its universality and availability
justify its use even with the limitations.

---

## 3. Option B — Market-Cap Matched Benchmark

**Description:** For each detected symbol, compare to an index of securities
with similar market cap (e.g., large-cap: SPY / mid-cap: MDY / small-cap: IJR).

**Pros:**
- More precise size-adjusted comparison
- Removes size premium as a confound

**Cons:**
- Requires cap-bucket data per detection (available in SIH holdings enrichment)
- Three separate benchmarks to track and compute
- Complicates comparison across detection cohorts

**Verdict:** Use as a secondary benchmark for sensitivity analysis. Add after
primary SPY analysis is established.

---

## 4. Option C — Sector Benchmark

**Description:** Compare each detection to its GICS sector ETF (XLK, XLE, etc.).

**Pros:**
- Controls for sector momentum — if tech is rallying broadly, a tech dislocation
  "outperforming" SPY may simply be sector beta
- Sector benchmarking is the standard in factor research

**Cons:**
- SIH does not currently fetch sector ETF price data
- Sector classifications in the holding universe are not uniformly available
- Adds significant infrastructure overhead for initial outcome measurement

**Verdict:** Defer to Phase 12D or later. Note as a potential refinement once
primary and secondary benchmarks are established.

---

## 5. Option D — Multiple Benchmarks

**Description:** Track excess return vs. SPY, vs. cap-matched, and vs. sector
simultaneously.

**Pros:**
- Most rigorous — prevents benchmark selection bias
- Standard practice in quantitative research

**Cons:**
- High complexity for initial implementation
- Report becomes harder to interpret when three excess-return series diverge

**Verdict:** The correct long-term design, but premature for the first 90-day
cohort. Adopt in phases: SPY first, cap-matched second, sector third.

---

## 6. Recommended Benchmark Approach

### Primary: SPY Total Return

Use SPY daily adjusted close prices fetched via yfinance for outcome comparison.

For every detection with a 30/60/90/180/365-day outcome:
```
excess_return = symbol_total_return - SPY_total_return
```
over the same holding period window.

### Secondary (deferred): Cap-Matched Benchmark

Large-cap (≥$10B market cap): compare to SPY  
Mid-cap ($2B–$10B): compare to MDY  
Small-cap (<$2B): compare to IJR  

Available once cap-bucket data flows reliably through the detection snapshot.

### What NOT to Use

- QQQ or sector ETFs as primary benchmarks — introduces selection bias
- Portfolio NAV as benchmark — circular (the portfolio already holds these)
- Equal-weighted custom index — requires bespoke construction

---

## 7. Equal-Weighted Detection Portfolio Alternative

A secondary analysis can construct a hypothetical equal-weighted portfolio of
all non-NONE detections as of each detection date, held for 90 days, and compare
that portfolio's return to SPY. This is the standard "long-only paper portfolio"
evaluation used in quantitative signal research.

This approach:
- Eliminates position-size differences between detections
- Provides a single portfolio-level return vs. SPY comparison
- Separates the question "does dislocation detection add alpha?" from "does
  position sizing optimize the alpha?"

**Recommendation:** Include this as a secondary analysis metric alongside
individual detection outcomes.
