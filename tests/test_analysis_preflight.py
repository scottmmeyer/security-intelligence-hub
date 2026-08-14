from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from src.validation.analysis_preflight import run_analysis_preflight


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _seed_ready_repo(tmp_path: Path) -> Path:
    repo = tmp_path
    (repo / "config").mkdir(parents=True, exist_ok=True)
    (repo / "config" / "preflight_policy.yaml").write_text(
        "analysis_preflight:\n"
        "  max_active_ess_age_days: 14\n"
        "  l1_recognized_mv_coverage_block_threshold_pct: 90.0\n",
        encoding="utf-8",
    )

    _write_csv(
        repo / "data/current/analytical_universe.csv",
        ["symbol", "snapshot_date", "geography", "asset_class"],
        [
            {"symbol": "AAPL", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES"},
            {"symbol": "MSFT", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES"},
        ],
    )

    today = date.today().isoformat()
    _write_csv(
        repo / "data/current/signal_snapshot.csv",
        ["symbol", "snapshot_date", "coverage_domain", "starmine_ess_text"],
        [
            {"symbol": "AAPL", "snapshot_date": today, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"},
            {"symbol": "MSFT", "snapshot_date": today, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "NEUTRAL"},
        ],
    )

    _write_csv(
        repo / "data/current/benchmark_returns.csv",
        ["benchmark_id", "date", "adjusted_close"],
        [
            {"benchmark_id": "BM_US_LARGE", "date": "2026-08-12", "adjusted_close": "100.0"},
            {"benchmark_id": "BM_US_LARGE", "date": "2026-08-13", "adjusted_close": "101.0"},
        ],
    )

    _write_csv(
        repo / "data/current/replay_availability.csv",
        ["replay_generated"],
        [{"replay_generated": "true"}],
    )

    _write_csv(
        repo / "data/signals/fmp/latest/latest_fmp_enriched_universe.csv",
        ["symbol", "fmp_coverage_status"],
        [
            {"symbol": "AAPL", "fmp_coverage_status": "FULL"},
            {"symbol": "MSFT", "fmp_coverage_status": "FULL"},
        ],
    )

    _write_csv(
        repo / "data/signals/zacks/latest_zacks.csv",
        ["symbol", "sourced_date", "zacks_score"],
        [{"symbol": "AAPL", "sourced_date": today, "zacks_score": "4.0"}],
    )
    _write_csv(
        repo / "data/signals/danelfin/latest_danelfin.csv",
        ["symbol", "sourced_date", "danelfin_score"],
        [{"symbol": "AAPL", "sourced_date": today, "danelfin_score": "8"}],
    )
    _write_csv(
        repo / "data/signals/yahoo/latest_yahoo_supplemental.csv",
        ["symbol", "sourced_date", "current_price"],
        [{"symbol": "AAPL", "sourced_date": today, "current_price": "100.0"}],
    )

    _write_csv(
        repo / "data/history/pis/canonical/canonical_daily_snapshots.csv",
        ["snapshot_date"],
        [{"snapshot_date": "2026-08-13"}],
    )
    (repo / "data/portfolio_ingestion").mkdir(parents=True, exist_ok=True)
    (repo / "data/portfolio_ingestion/manifest.json").write_text(
        '{"portfolios": [{"status": "COMPLETE"}]}', encoding="utf-8"
    )

    _write_csv(
        repo / "data/portfolio_ingestion/analysis_runs/PAR-TEST/holdings.csv",
        ["symbol", "market_value", "asset_class", "operational_state"],
        [
            {"symbol": "AAPL", "market_value": "700", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "MSFT", "market_value": "300", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    return repo


def test_ready_preflight(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "READY"
    assert result.suppression_flags["suppress_action_recommendation_cards"] is False


def test_degraded_geography_optional_provider_fmp_partial_and_replay_unavailable(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    _write_csv(
        repo / "data/current/analytical_universe.csv",
        ["symbol", "snapshot_date", "geography", "asset_class"],
        [
            {"symbol": "AAPL", "snapshot_date": "2026-08-13", "geography": "UNKNOWN", "asset_class": "EQUITIES"},
            {"symbol": "MSFT", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES"},
        ],
    )
    _write_csv(
        repo / "data/signals/fmp/latest/latest_fmp_enriched_universe.csv",
        ["symbol", "fmp_coverage_status"],
        [
            {"symbol": "AAPL", "fmp_coverage_status": "PARTIAL"},
            {"symbol": "MSFT", "fmp_coverage_status": "NO_DATA"},
        ],
    )
    (repo / "data/current/replay_availability.csv").unlink(missing_ok=True)
    (repo / "data/signals/danelfin/latest_danelfin.csv").unlink(missing_ok=True)

    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "DEGRADED"
    assert "PF-GEO-001" in result.reason_codes
    assert "PF-FMP-001" in result.reason_codes
    assert "PF-REPLAY-001" in result.reason_codes
    assert result.components["replay"].metrics["replay_unavailable_not_score_zero"] is True


def test_blocked_when_analytical_universe_missing(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    (repo / "data/current/analytical_universe.csv").unlink()
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-AU-001" in result.reason_codes
    assert result.suppression_flags["suppress_deployment_queue"] is True


def test_blocked_when_analytical_universe_empty(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    _write_csv(repo / "data/current/analytical_universe.csv", ["symbol", "snapshot_date", "geography", "asset_class"], [])
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-AU-003" in result.reason_codes


def test_blocked_when_analytical_universe_unreadable(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    (repo / "data/current/analytical_universe.csv").unlink()
    (repo / "data/current/analytical_universe.csv").mkdir(parents=True, exist_ok=True)
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-AU-003" in result.reason_codes


def test_blocked_when_l1_coverage_below_threshold(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    _write_csv(
        repo / "data/portfolio_ingestion/analysis_runs/PAR-TEST/holdings.csv",
        ["symbol", "market_value", "asset_class", "operational_state"],
        [
            {"symbol": "AAPL", "market_value": "800", "asset_class": "UNKNOWN", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "MSFT", "market_value": "200", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-AU-002" in result.reason_codes


def test_blocked_when_ess_stale_for_required_mode(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    stale_date = (date.today() - timedelta(days=21)).isoformat()
    _write_csv(
        repo / "data/current/signal_snapshot.csv",
        ["symbol", "snapshot_date", "coverage_domain", "starmine_ess_text"],
        [{"symbol": "AAPL", "snapshot_date": stale_date, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"}],
    )
    (repo / "ess_history_master.csv").write_text(
        "symbol,capture_date,ess_category\nAAPL,2099-01-01,VERY_BULLISH\n",
        encoding="utf-8",
    )
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-ESS-001" in result.reason_codes


def test_blocked_when_ess_freshness_unknown_for_required_mode(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    _write_csv(
        repo / "data/current/signal_snapshot.csv",
        ["symbol", "snapshot_date", "coverage_domain", "starmine_ess_text"],
        [{"symbol": "AAPL", "snapshot_date": "not-a-date", "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"}],
    )
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-ESS-002" in result.reason_codes


def test_runtime_incompleteness_missing_au_and_signal_snapshot(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    (repo / "data/current/analytical_universe.csv").unlink(missing_ok=True)
    (repo / "data/current/signal_snapshot.csv").unlink(missing_ok=True)
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.status == "BLOCKED"
    assert "PF-AU-001" in result.reason_codes
    assert "PF-ESS-003" in result.reason_codes


def test_suppression_flags_set_when_blocked(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    (repo / "data/current/analytical_universe.csv").unlink(missing_ok=True)
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.suppression_flags["suppress_action_recommendation_cards"] is True
    assert result.suppression_flags["suppress_deployment_queue"] is True
    assert result.suppression_flags["suppress_deployment_plan"] is True
    assert result.suppression_flags["suppress_capital_allocation_guidance"] is True
    assert result.suppression_flags["suppress_actionable_adds_trims"] is True


def test_top_level_reason_codes_are_unique(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    (repo / "data/signals/zacks/latest_zacks.csv").unlink(missing_ok=True)
    (repo / "data/signals/danelfin/latest_danelfin.csv").unlink(missing_ok=True)
    (repo / "data/signals/yahoo/latest_yahoo_supplemental.csv").unlink(missing_ok=True)
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.reason_codes.count("PF-PROVIDER-001") == 1


def test_invalid_policy_values_fall_back_to_safe_defaults(tmp_path: Path) -> None:
    repo = _seed_ready_repo(tmp_path)
    (repo / "config" / "preflight_policy.yaml").write_text(
        "analysis_preflight:\n"
        "  max_active_ess_age_days: not-a-number\n"
        "  l1_recognized_mv_coverage_block_threshold_pct: bad\n",
        encoding="utf-8",
    )
    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result.metrics["policy"]["max_active_ess_age_days"] == 14
    assert result.metrics["policy"]["l1_recognized_mv_coverage_block_threshold_pct"] == 90.0


def test_reason_codes_are_deterministic_and_no_scoring_invoked(tmp_path: Path, monkeypatch) -> None:
    repo = _seed_ready_repo(tmp_path)

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("scoring should not be invoked during preflight")

    monkeypatch.setattr(
        "src.portfolio.recommendations.generate_recommendations_with_phase_e_warnings",
        _raise_if_called,
        raising=True,
    )

    result_a = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    result_b = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    assert result_a.reason_codes == result_b.reason_codes
