# Refresh Completion Confidence

This defines objective evidence the operator should see when Rebuild Research Universe finishes.

## Required Completion Evidence

1. Job completion proof

- /api/signal-refresh/status.running = false
- /api/signal-refresh/status.exit_code = 0
- /api/signal-refresh/status.last_report.refresh_mode = rebuild_research_universe

2. Provider refresh proof

- last_report.providers.zacks submitted and refreshed counts near rebuild denominator.
- Equivalent submitted and refreshed counts for Danelfin and Yahoo.

3. Candidate freshness improvement proof

- Research universe core freshness percent before versus after.
- Candidate-set freshness deltas for CW-DAS, UCF, recommendation candidates, CRA deployments.

4. Input quality improvement proof

- Higher with_data_count and attempted_count today rows on provider cards.
- Reduced stale or missing counts in candidate freshness panel.

5. Ranking confidence proof

- Timestamped statement that current rankings are based on refreshed provider files dated today or within threshold.

## Suggested Completion Indicators in UI

1. Rebuild complete banner

- Rebuild Research Universe complete at time with runtime and exit code.

2. Before and after deltas

- Candidate freshness delta cards, such as CW-DAS +X%, UCF +Y%, Research +Z%.

3. Data provenance summary

- Ranked on provider snapshots: Zacks date, Danelfin date, Yahoo date, ESS date, FMP date.

4. Confidence label

- Candidate Confidence HIGH, MEDIUM, LOW from candidate-readiness prototype metrics.
