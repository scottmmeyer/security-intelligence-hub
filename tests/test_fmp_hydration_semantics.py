from __future__ import annotations

import csv
import importlib.util
from datetime import date
from pathlib import Path

from src.scoring.fmp_universe_enrichment import (
    ATTEMPT_PROVENANCE_LEDGER,
    ATTEMPT_PROVENANCE_LEGACY,
    ATTEMPT_PROVENANCE_UNKNOWN,
    COVERAGE_FETCH_FAILED,
    COVERAGE_FULL,
    COVERAGE_NOT_FETCHED,
    COVERAGE_PARTIAL,
    COVERAGE_PROVIDER_NO_DATA,
    build_fmp_enriched_universe,
)
from src.validation.analysis_preflight import run_analysis_preflight


_FETCH_STATUS_HEADERS = [
    "symbol",
    "product",
    "status",
    "attempted_at_utc",
    "source_date",
    "failure_type",
    "failure_reason",
]


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _seed_preflight_repo(tmp_path: Path) -> Path:
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
        ["symbol", "snapshot_date", "geography", "asset_class", "security_type"],
        [
            {"symbol": "AAA", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES", "security_type": "COMMON STOCK"},
            {"symbol": "BBB", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES", "security_type": "COMMON STOCK"},
            {"symbol": "CCC", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES", "security_type": "COMMON STOCK"},
            {"symbol": "DDD", "snapshot_date": "2026-08-13", "geography": "US", "asset_class": "EQUITIES", "security_type": "COMMON STOCK"},
        ],
    )

    today = date.today().isoformat()
    _write_csv(
        repo / "data/current/signal_snapshot.csv",
        ["symbol", "snapshot_date", "coverage_domain", "starmine_ess_text"],
        [
            {"symbol": "AAA", "snapshot_date": today, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"},
            {"symbol": "BBB", "snapshot_date": today, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"},
            {"symbol": "CCC", "snapshot_date": today, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"},
            {"symbol": "DDD", "snapshot_date": today, "coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"},
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

    _write_csv(repo / "data/current/replay_availability.csv", ["replay_generated"], [{"replay_generated": "true"}])

    _write_csv(
        repo / "data/signals/zacks/latest_zacks.csv",
        ["symbol", "sourced_date", "zacks_score"],
        [{"symbol": "AAA", "sourced_date": today, "zacks_score": "4.0"}],
    )
    _write_csv(
        repo / "data/signals/danelfin/latest_danelfin.csv",
        ["symbol", "sourced_date", "danelfin_score"],
        [{"symbol": "AAA", "sourced_date": today, "danelfin_score": "8"}],
    )
    _write_csv(
        repo / "data/signals/yahoo/latest_yahoo_supplemental.csv",
        ["symbol", "sourced_date", "current_price"],
        [{"symbol": "AAA", "sourced_date": today, "current_price": "100.0"}],
    )

    _write_csv(repo / "data/history/pis/canonical/canonical_daily_snapshots.csv", ["snapshot_date"], [{"snapshot_date": "2026-08-13"}])
    (repo / "data/portfolio_ingestion").mkdir(parents=True, exist_ok=True)
    (repo / "data/portfolio_ingestion/manifest.json").write_text(
        '{"portfolios": [{"status": "COMPLETE"}]}', encoding="utf-8"
    )

    _write_csv(
        repo / "data/portfolio_ingestion/analysis_runs/PAR-TEST/holdings.csv",
        ["symbol", "market_value", "asset_class", "operational_state"],
        [
            {"symbol": "AAA", "market_value": "400", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "BBB", "market_value": "250", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "CCC", "market_value": "200", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
            {"symbol": "DDD", "market_value": "150", "asset_class": "EQUITIES", "operational_state": "ACTIVE_POSITION"},
        ],
    )
    return repo


def test_interrupt_safe_enrichment_keeps_statuses_distinct(tmp_path: Path) -> None:
    repo = _seed_preflight_repo(tmp_path)

    fmp_latest = repo / "data/signals/fmp/latest"
    _write_csv(
        fmp_latest / "latest_fmp_key_metrics.csv",
        ["symbol", "sourced_date", "fetch_status", "failure_type", "failure_reason", "ev_ebitda_ttm", "roe_ttm", "roic_ttm"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "ev_ebitda_ttm": "12.3", "roe_ttm": "0.15", "roic_ttm": "0.12"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "ev_ebitda_ttm": "7.1", "roe_ttm": "0.08", "roic_ttm": "0.06"},
            {"symbol": "CCC", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_grades_consensus.csv",
        ["symbol", "sourced_date", "fetch_status", "failure_type", "failure_reason", "consensus_label", "net_buy_score"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "consensus_label": "BUY", "net_buy_score": "3"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "consensus_label": "HOLD", "net_buy_score": "0"},
            {"symbol": "CCC", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_earnings_surprises.csv",
        ["symbol", "sourced_date", "fetch_status", "failure_type", "failure_reason", "beat_rate_8q", "latest_eps_surprise_pct"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "beat_rate_8q": "0.75", "latest_eps_surprise_pct": "4.2"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "beat_rate_8q": "0.50", "latest_eps_surprise_pct": "-2.1"},
            {"symbol": "CCC", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_income_growth.csv",
        ["symbol", "sourced_date", "fetch_status", "failure_type", "failure_reason", "revenue_growth_q1_yoy", "eps_growth_q1_yoy"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "fetch_status": "SUCCESS", "revenue_growth_q1_yoy": "0.1", "eps_growth_q1_yoy": "0.12"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "FETCH_FAILED", "failure_type": "NETWORK_ERROR", "failure_reason": "timeout"},
            {"symbol": "CCC", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_fetch_status.csv",
        _FETCH_STATUS_HEADERS,
        [
            {"symbol": "AAA", "product": "key_metrics", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "grades_consensus", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "earnings", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "income_growth", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:03+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "key_metrics", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:01:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "grades_consensus", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:01:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "earnings", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:01:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "income_growth", "status": "FETCH_FAILED", "attempted_at_utc": "2026-08-13T10:01:03+00:00", "source_date": "2026-08-13", "failure_type": "NETWORK_ERROR", "failure_reason": "timeout"},
            {"symbol": "CCC", "product": "key_metrics", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:02:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "CCC", "product": "grades_consensus", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:02:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "CCC", "product": "earnings", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:02:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "CCC", "product": "income_growth", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:02:03+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
        ],
    )

    records = build_fmp_enriched_universe(
        fmp_latest_dir=fmp_latest,
        universe_path=repo / "data/current/analytical_universe.csv",
        output_path=fmp_latest / "latest_fmp_enriched_universe.csv",
    )

    assert records["AAA"].fmp_coverage_status == COVERAGE_FULL
    assert records["BBB"].fmp_coverage_status == COVERAGE_FETCH_FAILED
    assert records["CCC"].fmp_coverage_status == COVERAGE_PROVIDER_NO_DATA
    assert records["DDD"].fmp_coverage_status == COVERAGE_NOT_FETCHED
    assert records["BBB"].fmp_attempted == "1"
    assert records["CCC"].fmp_attempted == "1"
    assert records["DDD"].fmp_attempted == "0"
    assert records["AAA"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_LEDGER
    assert records["BBB"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_LEDGER
    assert records["CCC"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_LEDGER
    assert records["DDD"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_UNKNOWN


def test_attempted_and_completed_hydration_are_distinct(tmp_path: Path) -> None:
    repo = _seed_preflight_repo(tmp_path)
    fmp_latest = repo / "data/signals/fmp/latest"

    _write_csv(
        fmp_latest / "latest_fmp_key_metrics.csv",
        ["symbol", "sourced_date", "ev_ebitda_ttm", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "ev_ebitda_ttm": "9.1", "fetch_status": "SUCCESS"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "ev_ebitda_ttm": "8.2", "fetch_status": "SUCCESS"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "ev_ebitda_ttm": "10.4", "fetch_status": "SUCCESS"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_grades_consensus.csv",
        ["symbol", "sourced_date", "consensus_label", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "consensus_label": "BUY", "fetch_status": "SUCCESS"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "consensus_label": "BUY", "fetch_status": "SUCCESS"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_earnings_surprises.csv",
        ["symbol", "sourced_date", "beat_rate_8q", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "beat_rate_8q": "0.75", "fetch_status": "SUCCESS"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "beat_rate_8q": "0.50", "fetch_status": "SUCCESS"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_income_growth.csv",
        ["symbol", "sourced_date", "revenue_growth_q1_yoy", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "revenue_growth_q1_yoy": "0.1", "fetch_status": "SUCCESS"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "revenue_growth_q1_yoy": "0.2", "fetch_status": "SUCCESS"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_fetch_status.csv",
        _FETCH_STATUS_HEADERS,
        [
            {"symbol": "AAA", "product": "key_metrics", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "grades_consensus", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "earnings", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "income_growth", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:03+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "key_metrics", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:01:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "CCC", "product": "key_metrics", "status": "FETCH_FAILED", "attempted_at_utc": "2026-08-13T10:02:00+00:00", "source_date": "2026-08-13", "failure_type": "NETWORK_ERROR", "failure_reason": "timeout"},
            {"symbol": "DDD", "product": "key_metrics", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:03:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "DDD", "product": "grades_consensus", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:03:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "DDD", "product": "earnings", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:03:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "DDD", "product": "income_growth", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:03:03+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
        ],
    )

    records = build_fmp_enriched_universe(
        fmp_latest_dir=fmp_latest,
        universe_path=repo / "data/current/analytical_universe.csv",
        output_path=fmp_latest / "latest_fmp_enriched_universe.csv",
    )

    # AAA: completed hydration across all products.
    assert records["AAA"].fmp_attempted == "1"
    assert records["AAA"].fmp_coverage_status == COVERAGE_FULL

    # BBB: attempted but only 1/4 products attempted.
    assert records["BBB"].fmp_attempted == "1"
    assert records["BBB"].fmp_coverage_status == COVERAGE_PARTIAL

    # CCC: attempted but explicit technical failure.
    assert records["CCC"].fmp_attempted == "1"
    assert records["CCC"].fmp_coverage_status == COVERAGE_FETCH_FAILED

    # DDD: attempted with provider-no-data for one product remains completed hydration.
    assert records["DDD"].fmp_attempted == "1"
    assert records["DDD"].fmp_coverage_status == COVERAGE_FULL


def test_ledger_override_and_legacy_provenance_contract(tmp_path: Path) -> None:
    repo = _seed_preflight_repo(tmp_path)
    fmp_latest = repo / "data/signals/fmp/latest"

    # Stale existing enriched artifact must not drive rebuild semantics.
    _write_csv(
        fmp_latest / "latest_fmp_enriched_universe.csv",
        ["symbol", "fmp_coverage_status", "fmp_attempted"],
        [
            {"symbol": "AAA", "fmp_coverage_status": "NOT_FETCHED", "fmp_attempted": "0"},
            {"symbol": "BBB", "fmp_coverage_status": "NOT_FETCHED", "fmp_attempted": "0"},
            {"symbol": "CCC", "fmp_coverage_status": "NOT_FETCHED", "fmp_attempted": "0"},
            {"symbol": "DDD", "fmp_coverage_status": "NOT_FETCHED", "fmp_attempted": "0"},
        ],
    )

    _write_csv(
        fmp_latest / "latest_fmp_key_metrics.csv",
        ["symbol", "sourced_date", "ev_ebitda_ttm", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "ev_ebitda_ttm": "9.0", "fetch_status": "SUCCESS"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "ev_ebitda_ttm": "11.0"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_grades_consensus.csv",
        ["symbol", "sourced_date", "consensus_label", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "consensus_label": "BUY", "fetch_status": "SUCCESS"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "consensus_label": "BUY"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_earnings_surprises.csv",
        ["symbol", "sourced_date", "beat_rate_8q", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "beat_rate_8q": "0.8", "fetch_status": "SUCCESS"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "beat_rate_8q": "0.6"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_income_growth.csv",
        ["symbol", "sourced_date", "revenue_growth_q1_yoy", "fetch_status"],
        [
            {"symbol": "AAA", "sourced_date": "2026-08-13", "revenue_growth_q1_yoy": "0.1", "fetch_status": "SUCCESS"},
            {"symbol": "BBB", "sourced_date": "2026-08-13", "fetch_status": "PROVIDER_NO_DATA"},
            {"symbol": "DDD", "sourced_date": "2026-08-13", "revenue_growth_q1_yoy": "0.2"},
        ],
    )
    _write_csv(
        fmp_latest / "latest_fmp_fetch_status.csv",
        _FETCH_STATUS_HEADERS,
        [
            {"symbol": "AAA", "product": "key_metrics", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "grades_consensus", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "earnings", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "AAA", "product": "income_growth", "status": "SUCCESS", "attempted_at_utc": "2026-08-13T10:00:03+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "key_metrics", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:01:00+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "grades_consensus", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:01:01+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "earnings", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:01:02+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
            {"symbol": "BBB", "product": "income_growth", "status": "PROVIDER_NO_DATA", "attempted_at_utc": "2026-08-13T10:01:03+00:00", "source_date": "2026-08-13", "failure_type": "", "failure_reason": ""},
        ],
    )

    records = build_fmp_enriched_universe(
        fmp_latest_dir=fmp_latest,
        universe_path=repo / "data/current/analytical_universe.csv",
        output_path=fmp_latest / "latest_fmp_enriched_universe.csv",
    )

    # AAA: stale attempted=0 overridden by ledger-confirmed success.
    assert records["AAA"].fmp_attempted == "1"
    assert records["AAA"].fmp_coverage_status == COVERAGE_FULL
    assert records["AAA"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_LEDGER

    # BBB: ledger-confirmed provider no-data remains attempted.
    assert records["BBB"].fmp_attempted == "1"
    assert records["BBB"].fmp_coverage_status == COVERAGE_PROVIDER_NO_DATA
    assert records["BBB"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_LEDGER

    # CCC: no evidence remains not fetched.
    assert records["CCC"].fmp_attempted == "0"
    assert records["CCC"].fmp_coverage_status == COVERAGE_NOT_FETCHED
    assert records["CCC"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_UNKNOWN

    # DDD: legacy payload evidence without ledger remains attempted by compatibility.
    assert records["DDD"].fmp_attempted == "1"
    assert records["DDD"].fmp_coverage_status == COVERAGE_FULL
    assert records["DDD"].fmp_attempt_provenance == ATTEMPT_PROVENANCE_LEGACY


def test_preflight_reports_hydration_vs_data_coverage(tmp_path: Path) -> None:
    repo = _seed_preflight_repo(tmp_path)

    _write_csv(
        repo / "data/signals/fmp/latest/latest_fmp_enriched_universe.csv",
        ["symbol", "fmp_coverage_status"],
        [
            {"symbol": "AAA", "fmp_coverage_status": "FULL"},
            {"symbol": "BBB", "fmp_coverage_status": "FETCH_FAILED"},
            {"symbol": "CCC", "fmp_coverage_status": "PROVIDER_NO_DATA"},
            {"symbol": "DDD", "fmp_coverage_status": "NOT_FETCHED"},
        ],
    )

    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    fmp = result.components["fmp"]

    assert result.status == "DEGRADED"
    assert "PF-FMP-003" in result.reason_codes
    assert "PF-FMP-004" in result.reason_codes
    assert "PF-FMP-005" in result.reason_codes
    assert fmp.metrics["applicable_symbols"] == 4
    assert fmp.metrics["attempted_symbols"] == 3
    assert fmp.metrics["completed_hydration_symbols"] == 2
    assert fmp.metrics["usable_data_symbols"] == 1
    assert fmp.metrics["provider_no_data_symbols"] == 1
    assert fmp.metrics["fetch_failed_symbols"] == 1
    assert fmp.metrics["not_fetched_symbols"] == 1
    assert fmp.metrics["hydration_pct"] == 50.0
    assert fmp.metrics["usable_data_pct"] == 25.0


def test_preflight_reports_attempt_provenance_breakdown(tmp_path: Path) -> None:
    repo = _seed_preflight_repo(tmp_path)

    _write_csv(
        repo / "data/signals/fmp/latest/latest_fmp_enriched_universe.csv",
        ["symbol", "fmp_coverage_status", "fmp_attempt_provenance"],
        [
            {"symbol": "AAA", "fmp_coverage_status": "FULL", "fmp_attempt_provenance": "LEDGER_CONFIRMED"},
            {"symbol": "BBB", "fmp_coverage_status": "PARTIAL", "fmp_attempt_provenance": "LEGACY_PAYLOAD_CONFIRMED"},
            {"symbol": "CCC", "fmp_coverage_status": "PROVIDER_NO_DATA", "fmp_attempt_provenance": "LEDGER_CONFIRMED"},
            {"symbol": "DDD", "fmp_coverage_status": "NOT_FETCHED", "fmp_attempt_provenance": "UNKNOWN"},
        ],
    )

    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    fmp = result.components["fmp"]

    assert fmp.metrics["attempted_symbols"] == 3
    assert fmp.metrics["ledger_confirmed_attempted_symbols"] == 2
    assert fmp.metrics["legacy_confirmed_attempted_symbols"] == 1
    assert fmp.metrics["coverage_inferred_attempted_symbols"] == 0


def test_preflight_uses_not_fetched_reason_code_and_metrics(tmp_path: Path) -> None:
    repo = _seed_preflight_repo(tmp_path)

    _write_csv(
        repo / "data/signals/fmp/latest/latest_fmp_enriched_universe.csv",
        ["symbol", "fmp_coverage_status"],
        [
            {"symbol": "AAA", "fmp_coverage_status": "FULL"},
            {"symbol": "BBB", "fmp_coverage_status": "NOT_FETCHED"},
            {"symbol": "CCC", "fmp_coverage_status": "NOT_FETCHED"},
            {"symbol": "DDD", "fmp_coverage_status": "NOT_FETCHED"},
        ],
    )

    result = run_analysis_preflight(repo_root=repo, require_active_ess=True)
    fmp = result.components["fmp"]

    assert result.status == "DEGRADED"
    assert "PF-FMP-005" in result.reason_codes
    assert "PF-FMP-003" not in result.reason_codes
    assert fmp.metrics["applicable_symbols"] == 4
    assert fmp.metrics["attempted_symbols"] == 1
    assert fmp.metrics["not_fetched_symbols"] == 3
    assert fmp.metrics["completed_hydration_symbols"] == 1
    assert fmp.metrics["hydration_pct"] == 25.0
    assert fmp.metrics["provider_no_data_symbols"] == 0


def test_bulk_resume_status_driven_completion_cases_a_to_e(tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "fmp_bulk_fetch_universe.py"
    spec = importlib.util.spec_from_file_location("fmp_bulk_fetch_universe", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    status_rows = {
        ("AAA", "key_metrics"): {"status": "SUCCESS"},
        ("AAA", "grades_consensus"): {"status": "SUCCESS"},
        ("AAA", "earnings"): {"status": "SUCCESS"},
        ("AAA", "income_growth"): {"status": "SUCCESS"},
        ("BBB", "key_metrics"): {"status": "SUCCESS"},
        ("BBB", "grades_consensus"): {"status": "PROVIDER_NO_DATA"},
        ("BBB", "earnings"): {"status": "SUCCESS"},
        ("BBB", "income_growth"): {"status": "SUCCESS"},
        ("CCC", "key_metrics"): {"status": "SUCCESS"},
        ("CCC", "grades_consensus"): {"status": "FETCH_FAILED"},
        ("CCC", "earnings"): {"status": "SUCCESS"},
        ("CCC", "income_growth"): {"status": "SUCCESS"},
        ("EEE", "key_metrics"): {"status": "PROVIDER_NO_DATA"},
        ("EEE", "grades_consensus"): {"status": "PROVIDER_NO_DATA"},
        ("EEE", "earnings"): {"status": "PROVIDER_NO_DATA"},
        ("EEE", "income_growth"): {"status": "PROVIDER_NO_DATA"},
    }

    km_rows = {
        "AAA": {"symbol": "AAA"},
        "BBB": {"symbol": "BBB"},
        "CCC": {"symbol": "CCC"},
        "EEE": {"symbol": "EEE"},
    }
    gr_rows = {
        "AAA": {"symbol": "AAA"},
        "BBB": {"symbol": "BBB"},
        "CCC": {"symbol": "CCC"},
        "EEE": {"symbol": "EEE"},
    }
    es_rows = {
        "AAA": {"symbol": "AAA"},
        "BBB": {"symbol": "BBB"},
        "CCC": {"symbol": "CCC"},
        "EEE": {"symbol": "EEE"},
    }
    ig_rows = {
        "AAA": {"symbol": "AAA"},
        "BBB": {"symbol": "BBB"},
        "CCC": {"symbol": "CCC"},
        "EEE": {"symbol": "EEE"},
    }

    assert module._symbol_completed(
        symbol="AAA",
        status_rows=status_rows,
        km_rows=km_rows,
        gr_rows=gr_rows,
        es_rows=es_rows,
        ig_rows=ig_rows,
    )
    assert module._symbol_completed(
        symbol="BBB",
        status_rows=status_rows,
        km_rows=km_rows,
        gr_rows=gr_rows,
        es_rows=es_rows,
        ig_rows=ig_rows,
    )
    assert not module._symbol_completed(
        symbol="CCC",
        status_rows=status_rows,
        km_rows=km_rows,
        gr_rows=gr_rows,
        es_rows=es_rows,
        ig_rows=ig_rows,
    )
    assert not module._symbol_completed(
        symbol="DDD",
        status_rows=status_rows,
        km_rows=km_rows,
        gr_rows=gr_rows,
        es_rows=es_rows,
        ig_rows=ig_rows,
    )
    assert module._symbol_completed(
        symbol="EEE",
        status_rows=status_rows,
        km_rows=km_rows,
        gr_rows=gr_rows,
        es_rows=es_rows,
        ig_rows=ig_rows,
    )
