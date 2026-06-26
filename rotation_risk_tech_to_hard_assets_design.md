# ROTATION-RISK-01: Tech-to-hard-assets rotation monitor

## Objective
Create a display-only diagnostic to detect possible market regime rotation from Technology into hard-asset cohorts (Energy, Basic Materials, Industrials) without changing allocation scores, recommendation ranking, CRA, PAP, replay logic, or execution behavior.

## Scope and Guardrails
- Scope: informational summary only, surfaced in Portfolio Alignment UI and via API.
- Non-goals: no mutation of ESS, CW-DAS, UCF, CRA, PAP, recommendation generation, or trade execution.
- Contract: endpoint must fail-open to DATA_UNAVAILABLE with explicit missing inputs.

## Data Audit
Available now:
- data/current/replay_inputs.csv: replay metadata across industries/caps.
- data/current/replay_performance_series.csv: benchmark time series for replay cohorts.
- data/current/signal_snapshot.csv: latest ESS posture for breadth confirmation.
- data/portfolio_ingestion/analysis_runs/<run_id>/holdings.csv: current portfolio exposure map.
- data/mei/event_calendar.json: macro event context for forward monitoring.

Known gaps:
- data/current/security_prices.csv often empty in current environment.
- Therefore proxy computation uses replay benchmark series (industry cohorts) as primary source.

## Proxy Construction
- Tech proxy: US TECHNOLOGY benchmark replay series (preferred cap bucket selected from LARGE, MEGA, MID, SMALL, MICRO by availability).
- Hard-asset proxy: average of available benchmark replay series for:
  - ENERGY
  - BASIC MATERIALS
  - INDUSTRIALS
- Windows: 5d, 20d, 60d.
- Rotation spread: hard_asset_return - tech_return for each window.

## Confirmation Rules (Display-only)
Signal confirmation uses portfolio-held symbol ESS breadth:
- tech_bearish_share = share of Technology holdings with ESS <= 2.0
- hard_assets_bullish_share = share of hard-asset holdings with ESS >= 4.0
- confirmation_passed when:
  - tech_bearish_share >= 35%
  - hard_assets_bullish_share >= 45%
  - at least 2 covered symbols in each cohort

## Diagnostic Classification
- ELEVATED_ROTATION_RISK:
  - 20d spread >= +3.0pp
  - 5d spread >= +1.0pp
  - confirmation passed OR 60d spread >= +5.0pp
- WATCHLIST_ROTATION:
  - 20d spread >= +1.5pp and elevated criteria not fully met
- TECH_LEADERSHIP:
  - 20d spread <= -1.5pp
- NO_CLEAR_SIGNAL:
  - none of the above
- DATA_UNAVAILABLE:
  - missing replay inputs/performance or insufficient proxies

## API
- Endpoint: GET /api/rotation-risk/summary
- Module: src/sih/rotation_risk_monitor.py
- Response includes:
  - status, signal, headline, risk_score
  - portfolio_exposure
  - proxy_returns (tech, hard-assets, spreads)
  - confirmation metrics
  - data_quality diagnostics
  - upcoming high-impact MEI events

## UI
- New panel in Portfolio Alignment results: Rotation Risk Monitor
- Placement: directly below Market Context for operator timing awareness continuity.
- Elements:
  - signal badges
  - 5d/20d/60d proxy table
  - portfolio tech vs hard-asset exposure
  - confirmation breadth metrics
  - high-impact event list
  - governance disclaimer

## Safety Assertions
- Read-only filesystem behavior for monitor logic.
- No write-paths invoked.
- No changes to existing scoring and action engines.
- Endpoint error path returns DATA_UNAVAILABLE (200) for resilience.

## Validation
- Added tests:
  - elevated/watchlist path when proxies + confirmation are present.
  - DATA_UNAVAILABLE path when replay artifacts are missing.
