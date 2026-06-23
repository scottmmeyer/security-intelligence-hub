# SIMO Warning Analysis

## Observed Warning

The current ESS coverage warning artifact reports exactly one warning symbol:

- SIMO

Artifact details:

- `warning_count = 1`
- `true_missing_count = 0`
- `stale_coverage_count = 1`
- `no_fresh_starmine_count = 0`

## Exact Stale Condition

From `data/current/ess_coverage_warning.json`:

- symbol: `SIMO`
- company_name: `SILICON MOTION TECHNO ADR REP 4 ORD`
- last_ess_date: `2026-05-20`
- current_ess_posture: `BULLISH`
- days_stale: `29`
- gap_type: `STALE_ESS`

## Why SIMO Is Still The Only Warning

The current signal snapshot row for SIMO shows:

- `source_file = non-ess1.csv`
- `coverage_domain = NON_STARMINE_ANALYST`
- `signal_coverage_status = NON_COVERED`
- `starmine_ess_text = ''`

That means the current non-StarMine row does not supply fresh ESS coverage for SIMO.

## Can The Current ESS Process Refresh It?

Yes, but only if a fresh StarMine ESS export is placed in `incoming/ess/starmine/` and the ESS intake is rerun.

The signal refresh button does not fix this condition because this is an ESS intake gap, not a live-provider signal refresh gap.

## Is Operator Action Required?

Yes.

Operator action is required to provide a new StarMine ESS file for SIMO.

## Conclusion

SIMO is stale because its last ESS data point is 29 days old, not because the portfolio refresh modes failed to target it. It is an upstream ESS freshness issue, and the correct remediation path is a new StarMine intake file.

After the completed Portfolio Signals refresh, SIMO still remains the only ESS warning because the refresh path does not replace missing upstream StarMine ESS history for that symbol.