# ESS-COVERAGE-05 Non-Scored Security Applicability Audit

Date: 2026-06-17
Scope: Forensic audit only. No fixes implemented.

## Part A - Symbol Lineage

### SBS lineage (current state)

1. Incoming ESS source
- Not present in current non-StarMine intake file: incoming/ess/non_starmine_zacks/non-ess.csv.
- There is no current 2026-06-17 signal snapshot row for SBS in merged current signal state.

2. Parsed ESS output
- No current parsed signal row in data/current/signal_snapshot.csv for SBS.
- No 2026-06-17 historical signal partition row for SBS.

3. Merged signal state
- Absent from data/current/signal_snapshot.csv.

4. Overlay generation
- SBS appears in latest holdings and overlays with ESS text BULLISH:
  - holdings: data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/holdings.csv line 59
  - overlay: data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/security_overlays.csv line 5
- Overlay ESS can be backfilled from archive fallback when holding ESS is empty:
  - src/portfolio/recommendations.py lines 173-200

5. Warning generation
- Under current ESS-COVERAGE-04 warning builder logic, SBS is not in recomputed warning gaps.
- If SBS appears in data/current/ess_coverage_warning.json, that reflects stale artifact content prior to regeneration.

### SIMO lineage (current state)

1. Incoming ESS source
- Present in current non-StarMine intake file:
  - incoming/ess/non_starmine_zacks/non-ess.csv line 141

2. Parsed ESS output
- Non-StarMine parsed row carries no ESS text or numeric and is marked NON_COVERED:
  - data/current/signal_snapshot.csv line 2094
  - src/normalize/ess_normalizer.py lines 126-127

3. Signal snapshot generation and merged current state
- SIMO is in merged current snapshot as NON_STARMINE_ANALYST / NON_COVERED with blank ESS fields:
  - data/current/signal_snapshot.csv line 2094
- SIMO is in base universe as NON_STARMINE_ANALYST with blank StarMine ESS text:
  - data/current/base_equity_universe.csv line 2633

4. Overlay generation
- Latest holding has blank ESS and blank composite fields:
  - data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/holdings.csv line 60
- Overlay still shows ESS BULLISH due archive fallback:
  - data/portfolio_ingestion/analysis_runs/PAR-20260617-001280E0/security_overlays.csv line 62
  - src/portfolio/recommendations.py lines 173-200

5. Warning generation
- Warning builder loads current scored ESS via load_fidelity_signals plus historical fallback:
  - src/portfolio/ess_coverage.py lines 96-98 and 115
- load_fidelity_signals skips symbols with empty ESS text in current snapshot:
  - src/portfolio/fidelity_signal.py lines 102-103
- Historical partition contains prior STARMINE_COVERED SIMO row (BULLISH, 4.0):
  - data/history/signals/snapshot_date=2026-05-20/run_id=RUN-REAL-ESS-20260520-001/signal_snapshots.csv line 2465
- Because current has no fresh scored StarMine for SIMO but prior exists, SIMO is classified as STALE_ESS:
  - src/portfolio/ess_coverage.py lines 117-127

## Part B - Scoring Eligibility Findings

### SBS
1. Present in ESS source now: No (not in current non-ess source).
2. Receives ESS score now from current signal path: No.
3. Receives ESS direction now: Yes in overlay (archive/fallback path), not from current signal snapshot.
4. Receives ESS rating text now: Yes in overlays/holdings output (BULLISH), sourced from upstream/archival context.
5. Intentionally excluded from scoring: Not explicitly excluded by policy in the inspected paths; currently absent from current ESS signal intake rows.

### SIMO
1. Present in ESS source now: Yes, in non-ess.csv.
2. Receives ESS score now: No (blank ESS fields in current signal snapshot/base universe row).
3. Receives ESS direction now: Yes in overlays (BULLISH), via archive fallback behavior.
4. Receives ESS rating text now: Yes in overlays (BULLISH), not from current scored StarMine row.
5. Intentionally excluded from scoring: It is classified as NON_STARMINE_ANALYST/NON_COVERED in normalization, i.e., not StarMine-scored for the current intake.

## Part C - Applicability Semantics Assessment

Current warning semantics effectively conflate two states:
- truly missing unsupported/no-history symbols
- symbols that are currently unscored but have historical scored ESS

A cleaner model for ESS warning diagnostics would separate:
1. SCORED_APPLICABLE
- current STARMINE_COVERED with non-empty ESS text

2. UNSCORED_CURRENTLY
- current NON_STARMINE_ANALYST or blank ESS for symbol that may still exist in universe/holdings

3. UNSUPPORTED_FOR_ESS
- symbols that never receive StarMine ESS (or not in supported StarMine set)

Under this model, only SCORED_APPLICABLE should drive "missing/stale ESS coverage" warnings. UNSCORED_CURRENTLY should be diagnostic telemetry, not equivalent to missing scored coverage.

## Part D - Why SIMO Remains in Warning Set

SIMO remains because warning logic uses historical ESS continuity:
- Current row for SIMO is NON_STARMINE_ANALYST with no ESS text.
- Historical ESS exists (latest observed 2026-05-20, BULLISH).
- Builder interprets this as stale loss of fresh scored coverage, producing STALE_ESS.

Recomputed warning (current code semantics) returns:
- warning_count: 1
- example_symbols: [SIMO]
- SIMO gap_type: STALE_ESS

## Required Questions (Q1-Q8)

Q1: Does SBS receive an ESS score?
- Not from current ESS signal snapshot intake path.

Q2: Does SIMO receive an ESS score?
- Not from current intake path (blank ESS text/numeric in current signal snapshot).

Q3: Is SIMO truly missing coverage?
- Not strictly missing symbol coverage in snapshot terms; it is present but unscored currently.

Q4: Is SIMO merely unscored?
- In current intake, yes. It is present as NON_STARMINE_ANALYST/NON_COVERED with no ESS score.

Q5: Should unscored securities generate ESS warnings?
- For strict ESS coverage quality, they should be tracked separately from missing/stale scored coverage. They are a different diagnostic state.

Q6: If not, what would the true warning count be?
- Zero under the current observed set, because the sole remaining warning symbol (SIMO) is currently unscored rather than freshly scored-and-missing.

Q7: Would warning count become zero?
- Yes, if unscored-currently symbols are excluded from missing/stale scored-warning counts.

Q8: Is a new applicability category required?
- Yes. At minimum, introduce UNSCORED_CURRENTLY (or equivalent) separate from true missing/stale scored coverage.

## Final Determination

SIMO currently behaves as a non-scored security in intake outputs, while warning logic treats it as stale because of historical scored continuity. That indicates a semantic boundary issue, not a parsing failure.

Interpretation against success criteria:
- SIMO is better characterized as currently unscored than as genuinely missing symbol coverage.
- If warning intent is strictly "missing scored ESS coverage," SIMO should move to a separate diagnostic category rather than remain in primary warning count.
