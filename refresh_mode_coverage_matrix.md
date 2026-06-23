# Refresh Mode Coverage Matrix

## Findings

| Mode | Target universe | Providers targeted | Expected symbols | Actual latest observed counts | What it means for candidate freshness |
| --- | --- | --- | --- | --- | --- |
| Refresh Stale Only | Stale or missing applicable holdings, plus repair targets; may skip entirely if the latest file is within the 2-day tolerance | Zacks, Danelfin, Yahoo, and any downstream repair path already wired in the refresh engine | Variable; depends on current staleness and repair targets | Not observed as a completed run in this audit | This is a repair mode, not a candidate-freshness guarantee. If the latest file is considered fresh, the mode can skip. |
| Refresh Portfolio Signals | Provider-applicable active holdings | Zacks, Danelfin, Yahoo; FMP daily branch also runs in the bundled orchestration | 56 applicable holdings per core provider in the latest run | 56 submitted / 56 refreshed for Zacks, 56 / 56 for Danelfin, 56 / 56 for Yahoo, FMP 0 / 0 | Holdings-first. It validated the owned portfolio, not the broader candidate universe. |
| Rebuild Research Universe | Full base research universe | Research-universe providers used by the analytical-universe rebuild | 2,473 symbols in the current analytical universe export | Not observed as a completed run in this audit | This is the mode that actually guarantees a full candidate-universe rebuild. |
| Prepare Portfolio Review | Portfolio Signals plus derived PIS artifacts | Same provider set as portfolio signals, then refreshes the derived PIS artifacts | Same 56-applicable-holdings provider refresh plus derived-artifact refresh | Same 56 / 56 core provider counts as `Refresh Portfolio Signals`, plus derived PIS refresh | Good for owned-portfolio readiness, but still not a candidate-universe freshness guarantee. |

## Bottom Line

Candidate freshness depends on a different refresh path than holdings freshness. `Refresh Portfolio Signals` is enough for the existing portfolio, but `rebuild_research_universe` is the mode that can guarantee the candidate universe is rebuilt.
