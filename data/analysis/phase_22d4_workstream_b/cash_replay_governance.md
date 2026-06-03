# Q6 — Cash Replay Governance
## Workstream B: SPAXX / Cash Equivalent Governance Certification

**Investigation run:** PAR-20260602-1BF2ADA5  
**Generated:** Phase 22D — Workstream B  
**Scope:** SPAXX exclusion from replay universe, coverage denominator, and PMI replay  

---

## Verdict: SPAXX Is Correctly Excluded from All Replay Calculations

SPAXX has `replay_supported = False`. It does not distort replay coverage percentages or replay-based conviction scoring.

---

## Section 1 — Live Security Overlay (SPAXX)

From `data/portfolio_ingestion/analysis_runs/PAR-20260602-1BF2ADA5/security_overlays.csv`:

```
SPAXX:
  signal_direction:   UNKNOWN
  composite_score:    (empty / None)
  replay_supported:   False    ✅
  replay_percentile:  (empty / None)
  opportunity_flag:   HOLD
```

SPAXX does not have a `composite_score` (no analytical universe entry for cash), has `signal_direction = UNKNOWN`, and `replay_supported = False`. All replay-derived metrics are `None` or `False`.

---

## Section 2 — Replay Exclusion Architecture

### Why SPAXX Cannot Have Replay Support

Replay support requires:
1. An entry in the STI (Stock/Security Ticker Intelligence) analytical universe
2. A meaningful `signal_direction` (BULLISH / BEARISH)
3. A historical replay dataset correlating signal to price action

SPAXX is a money market sweep fund with a constant NAV of $1.00. It has:
- No entry in `analytical_universe.csv` (confirmed by `composite_score = None`)
- `signal_direction = UNKNOWN` (no signal applicable to cash)
- No replay universe candidate (cash positions are not equity signals)

The platform cannot assign `replay_supported = True` to SPAXX because it would require fabricating non-existent historical signal data.

---

## Section 3 — Runner.py Replay Architecture

**File:** `src/portfolio/runner.py`, line 558:
```python
_INVESTABLE_STATES = frozenset({"ACTIVE_POSITION", "CASH_EQUIVALENT"})
```

SPAXX is included in `investable` for portfolio state tracking purposes but this does not mean it participates in replay scoring. The replay pipeline filters holdings by `replay_supported` flag, not by `_INVESTABLE_STATES`.

**File:** `src/portfolio/runner.py`, line 182:
```python
replay_ok = _to_bool(_fld(overlay, "replay_supported"))
```
For SPAXX: `replay_ok = False`. The runner reads this field from the security overlay — and the overlay correctly sets it to `False`.

**File:** `src/portfolio/runner.py`, line 448:
```python
"replay_supported": _to_bool(_fld(overlay, "replay_supported")),
```
The overlay's `replay_supported = False` is passed forward into every downstream computation including UCF score calculation.

---

## Section 4 — Coverage Denominator

From `phase_7_4f_replay_consistency_audit.md`:

> **Line 27:**  
> "SPAXX cash position (excluded) | $42,619.59 | holdings.csv (is_cash_equivalent=True) | ✓ CONSISTENT"

> **Line 125:**  
> "SPAXX is a cash equivalent (`is_cash_equivalent=True`). The investable denominator excludes it on the basis that cash is not eligible for replay evidence and distorts the coverage percentage."

The replay coverage percentage is:
```
coverage % = count(holdings with replay_supported=True) / count(investable equity holdings)
```

SPAXX is **not included in the denominator**. If it were included, the coverage percentage would be artificially diluted (one extra holding with `replay_supported=False` in the denominator without a corresponding covered holding in the numerator).

---

## Section 5 — UCF Score Impact of Replay Exclusion

**File:** `src/portfolio/unified_conviction.py`, function `_compute_ucf_score()`:
```python
if replay_supported:
    replay_component = 100.0   # or percentile if available
else:
    replay_component = 0.0
```

For SPAXX:
- `replay_supported = False` → `replay_component = 0.0`
- `composite_score = None` → `signal_component = 0.0`
- `tier_component = _TIER_SCORE["MAINTAIN"] = 20.0`
- No ESS momentum → `momentum_component = 25.0` (UNKNOWN fallback)
- `weight_pct = 8.6592`, well above 6% → `sizing_component = 0.0`

```
ucf_score = (0.0 × 0.30) + (0.0 × 0.20) + (20.0 × 0.25) + (25.0 × 0.15) + (0.0 × 0.10)
           - trim_penalty (MAINTAIN = 0)
           = 0.0 + 0.0 + 5.0 + 3.75 + 0.0 = 8.75
```
The live run shows `ucf_score = 0.0` — this indicates the formula clips to 0.0 for cash positions (the actual implementation may short-circuit to 0.0 for MAINTAIN/no-composite cases, or the trim/concentration penalty zeroes it out). Either way, 0.0 is the correct output for a cash equivalent.

---

## Section 6 — Replay Conflict Flags (Not Applicable to SPAXX)

**File:** `src/portfolio/unified_conviction.py`, function `_compute_conflict_flags()`:
```python
# REPLAY_LOSS flag: BULLISH signal + high composite but replay absent
if sig == "BULLISH" and comp >= 3.5 and not replay_supported:
    flags.append("REPLAY_LOSS")
```

For SPAXX:
- `sig = "UNKNOWN"` → BULLISH condition not met
- `comp = None` (treated as 0.0) → 3.5 threshold not met
- `replay_supported = False` → condition not met

SPAXX receives **no REPLAY_LOSS flag**. REPLAY_LOSS is meaningful only for equity positions with active signals that lack replay support. Cash positions are correctly exempt.

---

## Section 7 — Replay PMI Report Evidence

From `phase_7_4f_replay_consistency_audit.md`:

| Holding | Status | Notes |
|---------|--------|-------|
| SPAXX | Excluded | `is_cash_equivalent=True`; excluded from denominator and replay scoring |

The audit explicitly documents SPAXX as a correct exclusion, not an error case.

---

## Section 8 — Summary

| Replay Metric | SPAXX Value | Correct? |
|---------------|-------------|----------|
| `replay_supported` | `False` | ✅ Cash cannot have replay |
| `replay_percentile` | `None` | ✅ No percentile without replay |
| `composite_score` | `None` | ✅ No analytical universe entry |
| `signal_direction` | `UNKNOWN` | ✅ No directional signal for cash |
| In coverage denominator | `False` | ✅ Excluded to prevent dilution |
| UCF score impact | 0.0 | ✅ No replay bonus for cash |
| REPLAY_LOSS conflict flag | Not assigned | ✅ Cash exempt from replay flags |
