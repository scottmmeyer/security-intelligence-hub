from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import scripts.run_outcome_ui as outcome_ui
import scripts.refresh_signals as refresh


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _setup_refresh_scope_fixture(tmp_path: Path) -> tuple[Path, Path]:
    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    danelfin_dir = tmp_path / "data" / "signals" / "danelfin"

    _write_csv(
        base_universe,
        ["symbol", "company_name", "security_type"],
        [
            {"symbol": "A", "company_name": "A", "security_type": "Common Stock"},
            {"symbol": "B", "company_name": "B", "security_type": "Common Stock"},
            {"symbol": "C", "company_name": "C", "security_type": "Common Stock"},
            {"symbol": "D", "company_name": "D", "security_type": "Common Stock"},
        ],
    )

    _write_csv(
        danelfin_dir / "latest_danelfin.csv",
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [
            {"symbol": "A", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": date.today().isoformat()},
        ],
    )

    _write_csv(
        danelfin_dir / f"{date.today().isoformat()}_danelfin_attempts.csv",
        [
            "symbol",
            "attempt_date",
            "direct_status",
            "http_status",
            "detail",
            "browser_fallback_requested",
            "browser_fallback_completed",
            "final_status",
            "promoted_to_latest",
            "latest_sourced_date",
            "latest_danelfin_raw",
            "latest_danelfin_score",
        ],
        [
            {
                "symbol": "B",
                "attempt_date": date.today().isoformat(),
                "direct_status": "NO_PRIMARY_FIELDS",
                "http_status": "200",
                "detail": "",
                "browser_fallback_requested": "1",
                "browser_fallback_completed": "1",
                "final_status": "UNAVAILABLE_FAILED",
                "promoted_to_latest": "0",
                "latest_sourced_date": "",
                "latest_danelfin_raw": "",
                "latest_danelfin_score": "",
            },
            {
                "symbol": "D",
                "attempt_date": date.today().isoformat(),
                "direct_status": "BLOCKED_403_OR_CHALLENGE",
                "http_status": "403",
                "detail": "",
                "browser_fallback_requested": "1",
                "browser_fallback_completed": "1",
                "final_status": "UNAVAILABLE_FAILED",
                "promoted_to_latest": "0",
                "latest_sourced_date": "",
                "latest_danelfin_raw": "",
                "latest_danelfin_score": "",
            },
        ],
    )

    return base_universe, danelfin_dir


def test_danelfin_applicability_not_coverage_scope_counts(tmp_path, monkeypatch):
    base_universe, danelfin_dir = _setup_refresh_scope_fixture(tmp_path)

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "1")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    summary = scope["scope_summary"]

    assert summary["full_universe_count"] == 4
    assert summary["danelfin_known_covered_count"] == 1
    assert summary["danelfin_known_no_coverage_count"] == 1
    assert summary["danelfin_unknown_count"] == 2
    assert summary["danelfin_discovery_count"] == 1


def test_danelfin_known_covered_refresh_and_bounded_discovery(tmp_path, monkeypatch):
    base_universe, danelfin_dir = _setup_refresh_scope_fixture(tmp_path)

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "1")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    danelfin_symbols = scope["planned_symbols"]["provider_symbols"]["danelfin"]

    assert danelfin_symbols[0] == "A"
    assert len(danelfin_symbols) == 2
    assert scope["scope_summary"]["danelfin_rebuild_target_count"] == 2


def test_danelfin_discovery_success_promotion(tmp_path, monkeypatch):
    base_universe, danelfin_dir = _setup_refresh_scope_fixture(tmp_path)
    latest = danelfin_dir / "latest_danelfin.csv"

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "1")

    _write_csv(
        latest,
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [
            {"symbol": "A", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": date.today().isoformat()},
            {"symbol": "C", "danelfin_raw": "6", "danelfin_score": "3.0000", "sourced_date": date.today().isoformat()},
        ],
    )

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    summary = scope["scope_summary"]
    known_covered = set(scope["planned_symbols"]["danelfin_known_covered"])

    assert "C" in known_covered
    assert summary["danelfin_known_covered_count"] == 2


def test_danelfin_operational_failure_not_no_coverage(tmp_path, monkeypatch):
    base_universe, danelfin_dir = _setup_refresh_scope_fixture(tmp_path)

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "1")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    known_no_coverage = set(scope["planned_symbols"]["danelfin_known_no_coverage"])

    assert "B" in known_no_coverage
    assert "D" not in known_no_coverage


def test_danelfin_full_universe_scope_denominator_bounded(tmp_path, monkeypatch):
    base_universe, danelfin_dir = _setup_refresh_scope_fixture(tmp_path)

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "1")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    danelfin_symbols = scope["planned_symbols"]["provider_symbols"]["danelfin"]

    assert len(danelfin_symbols) == 2  # known covered (1) + discovery cap (1)
    assert scope["scope_summary"]["full_universe_count"] == 4


def test_danelfin_full_universe_scope_uses_known_covered_plus_cap_2640_fixture(tmp_path, monkeypatch):
    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    danelfin_dir = tmp_path / "data" / "signals" / "danelfin"
    symbols = [f"S{i:04d}" for i in range(2640)]

    _write_csv(
        base_universe,
        ["symbol", "company_name", "security_type"],
        [{"symbol": sym, "company_name": sym, "security_type": "Common Stock"} for sym in symbols],
    )

    known_covered = set(symbols[:57])
    _write_csv(
        danelfin_dir / "latest_danelfin.csv",
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [
            {"symbol": sym, "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": date.today().isoformat()}
            for sym in sorted(known_covered)
        ],
    )

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "8")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    danelfin_symbols = scope["planned_symbols"]["provider_symbols"]["danelfin"]

    assert scope["scope_summary"]["full_universe_count"] == 2640
    assert scope["scope_summary"]["danelfin_known_covered_count"] == 57
    assert scope["scope_summary"]["danelfin_discovery_count"] == 8
    assert len(danelfin_symbols) == 65


def test_danelfin_known_coverage_durability_from_attempts_history(tmp_path, monkeypatch):
    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    danelfin_dir = tmp_path / "data" / "signals" / "danelfin"
    today = date.today()

    _write_csv(
        base_universe,
        ["symbol", "company_name", "security_type"],
        [
            {"symbol": "A", "company_name": "A", "security_type": "Common Stock"},
            {"symbol": "B", "company_name": "B", "security_type": "Common Stock"},
            {"symbol": "C", "company_name": "C", "security_type": "Common Stock"},
        ],
    )

    # Latest materialization currently contains only A.
    _write_csv(
        danelfin_dir / "latest_danelfin.csv",
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [
            {"symbol": "A", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": today.isoformat()},
        ],
    )

    # B had a prior successful acquisition and should remain durable known-covered.
    _write_csv(
        danelfin_dir / f"{(today.replace(day=max(today.day - 1, 1))).isoformat()}_danelfin_attempts.csv",
        [
            "symbol",
            "attempt_date",
            "direct_status",
            "http_status",
            "detail",
            "browser_fallback_requested",
            "browser_fallback_completed",
            "final_status",
            "promoted_to_latest",
            "latest_sourced_date",
            "latest_danelfin_raw",
            "latest_danelfin_score",
        ],
        [
            {
                "symbol": "B",
                "attempt_date": today.isoformat(),
                "direct_status": "BLOCKED_403_OR_CHALLENGE",
                "http_status": "403",
                "detail": "",
                "browser_fallback_requested": "1",
                "browser_fallback_completed": "1",
                "final_status": "VALID_BROWSER_FALLBACK",
                "promoted_to_latest": "1",
                "latest_sourced_date": today.isoformat(),
                "latest_danelfin_raw": "7",
                "latest_danelfin_score": "3.5000",
            }
        ],
    )

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "1")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    known_covered = set(scope["planned_symbols"]["danelfin_known_covered"])

    assert "A" in known_covered
    assert "B" in known_covered


def test_danelfin_discovery_rotation_advances_across_days(monkeypatch):
    universe = [f"S{i:02d}" for i in range(1, 13)]

    class _Day1(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 1)

    class _Day2(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 2)

    monkeypatch.setattr(refresh, "_danelfin_attempted_symbols_for_date", lambda _d: set())

    monkeypatch.setattr(refresh, "date", _Day1)
    day1 = refresh._select_danelfin_discovery_symbols(
        universe_symbols=universe,
        known_covered=set(),
        known_no_coverage=set(),
        priority_symbols=[],
        cap=4,
    )

    monkeypatch.setattr(refresh, "date", _Day2)
    day2 = refresh._select_danelfin_discovery_symbols(
        universe_symbols=universe,
        known_covered=set(),
        known_no_coverage=set(),
        priority_symbols=[],
        cap=4,
    )

    assert len(day1) == 4
    assert len(day2) == 4
    assert day1 != day2


def test_danelfin_discovery_skips_same_day_attempts(tmp_path, monkeypatch):
    base_universe = tmp_path / "data" / "current" / "base_equity_universe.csv"
    danelfin_dir = tmp_path / "data" / "signals" / "danelfin"
    today = date.today().isoformat()

    _write_csv(
        base_universe,
        ["symbol", "company_name", "security_type"],
        [
            {"symbol": "A", "company_name": "A", "security_type": "Common Stock"},
            {"symbol": "B", "company_name": "B", "security_type": "Common Stock"},
            {"symbol": "C", "company_name": "C", "security_type": "Common Stock"},
            {"symbol": "D", "company_name": "D", "security_type": "Common Stock"},
            {"symbol": "E", "company_name": "E", "security_type": "Common Stock"},
        ],
    )

    _write_csv(
        danelfin_dir / f"{today}_danelfin_attempts.csv",
        [
            "symbol",
            "attempt_date",
            "direct_status",
            "http_status",
            "detail",
            "browser_fallback_requested",
            "browser_fallback_completed",
            "final_status",
            "promoted_to_latest",
            "latest_sourced_date",
            "latest_danelfin_raw",
            "latest_danelfin_score",
        ],
        [
            {
                "symbol": "C",
                "attempt_date": today,
                "direct_status": "BLOCKED_403_OR_CHALLENGE",
                "http_status": "403",
                "detail": "",
                "browser_fallback_requested": "1",
                "browser_fallback_completed": "1",
                "final_status": "UNAVAILABLE_FAILED",
                "promoted_to_latest": "0",
                "latest_sourced_date": "",
                "latest_danelfin_raw": "",
                "latest_danelfin_score": "",
            }
        ],
    )

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: set())
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: set())
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setenv("DANELFIN_DISCOVERY_CAP", "2")

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_REBUILD_RESEARCH_UNIVERSE)
    discovery = set(scope["planned_symbols"]["danelfin_discovery"])

    assert "C" not in discovery


def test_danelfin_portfolio_mode_regression_scope(tmp_path, monkeypatch):
    base_universe, danelfin_dir = _setup_refresh_scope_fixture(tmp_path)

    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", base_universe)
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", danelfin_dir)
    monkeypatch.setattr(refresh, "_load_portfolio_equity_holdings", lambda: {"A", "B"})
    monkeypatch.setattr(refresh, "_load_portfolio_provider_holdings", lambda provider: {"A", "B"})
    monkeypatch.setattr(refresh, "_load_buy_candidate_symbols", lambda cap=50: [])
    monkeypatch.setattr(refresh, "_market_proxy_symbols", lambda: ["SPY", "QQQ"])

    scope = refresh._build_refresh_scope(refresh_mode=refresh.REFRESH_MODE_PORTFOLIO_SIGNALS)
    danelfin_symbols = scope["planned_symbols"]["provider_symbols"]["danelfin"]

    assert danelfin_symbols == ["A", "B"]


def test_danelfin_known_covered_readiness_and_transparency(tmp_path, monkeypatch):
    root = tmp_path
    today = date.today().isoformat()

    _write_csv(
        root / "data" / "current" / "analytical_universe.csv",
        ["symbol"],
        [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}],
    )

    _write_csv(
        root / "data" / "signals" / "zacks" / "latest_zacks.csv",
        ["symbol", "zacks_rank", "zacks_score", "sourced_date"],
        [
            {"symbol": "A", "zacks_rank": "1", "zacks_score": "5", "sourced_date": today},
            {"symbol": "B", "zacks_rank": "1", "zacks_score": "5", "sourced_date": today},
            {"symbol": "C", "zacks_rank": "1", "zacks_score": "5", "sourced_date": today},
        ],
    )

    _write_csv(
        root / "data" / "signals" / "yahoo" / "latest_yahoo_supplemental.csv",
        ["symbol", "price_target", "analyst_count", "current_price", "sourced_date"],
        [
            {"symbol": "A", "price_target": "10", "analyst_count": "3", "current_price": "9", "sourced_date": today},
            {"symbol": "B", "price_target": "11", "analyst_count": "3", "current_price": "9", "sourced_date": today},
            {"symbol": "C", "price_target": "12", "analyst_count": "4", "current_price": "9", "sourced_date": today},
        ],
    )

    _write_csv(
        root / "data" / "signals" / "danelfin" / "latest_danelfin.csv",
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [
            {"symbol": "A", "danelfin_raw": "8", "danelfin_score": "4.0000", "sourced_date": today},
        ],
    )

    _write_csv(
        root / "data" / "signals" / "danelfin" / f"{today}_danelfin_attempts.csv",
        [
            "symbol",
            "attempt_date",
            "direct_status",
            "http_status",
            "detail",
            "browser_fallback_requested",
            "browser_fallback_completed",
            "final_status",
            "promoted_to_latest",
            "latest_sourced_date",
            "latest_danelfin_raw",
            "latest_danelfin_score",
        ],
        [
            {
                "symbol": "B",
                "attempt_date": today,
                "direct_status": "NO_PRIMARY_FIELDS",
                "http_status": "200",
                "detail": "",
                "browser_fallback_requested": "1",
                "browser_fallback_completed": "1",
                "final_status": "UNAVAILABLE_FAILED",
                "promoted_to_latest": "0",
                "latest_sourced_date": "",
                "latest_danelfin_raw": "",
                "latest_danelfin_score": "",
            }
        ],
    )

    fake_signal_status = {
        "zacks": {"with_data_count": 3, "attempted_count": 3, "sourced_date": today},
        "danelfin": {"with_data_count": 1, "attempted_count": 1, "sourced_date": today},
        "yahoo": {"with_data_count": 3, "attempted_count": 3, "sourced_date": today},
        "ess": {"sourced_date": today, "badge_state": "FRESH"},
        "portfolio_holdings_coverage": {"providers": {}},
    }

    fake_report = {
        "providers": {
            "danelfin": {
                "submitted_count": 2,
                "primary_data_count": 1,
                "failed": 1,
            }
        }
    }

    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", root)
    monkeypatch.setattr(
        outcome_ui,
        "_SIGNAL_FILES",
        {
            "zacks": root / "data" / "signals" / "zacks" / "latest_zacks.csv",
            "danelfin": root / "data" / "signals" / "danelfin" / "latest_danelfin.csv",
            "yahoo": root / "data" / "signals" / "yahoo" / "latest_yahoo_supplemental.csv",
        },
    )
    monkeypatch.setattr(outcome_ui, "_ESS_SIGNAL_SNAPSHOT", root / "data" / "current" / "signal_snapshot.csv")
    monkeypatch.setattr(outcome_ui, "_ESS_COVERAGE_WARNING", root / "data" / "current" / "ess_coverage_warning.json")

    monkeypatch.setattr(outcome_ui, "_signal_status", lambda: fake_signal_status)
    monkeypatch.setattr(outcome_ui, "_refresh_last_report", fake_report)

    payload = outcome_ui._refresh_transparency_payload()

    assert payload["readiness"]["research_universe"]["core_fresh"] == 3
    assert payload["decision_readiness"]["core_fresh_pct"] == 100.0

    coverage = payload["coverage_transparency"]
    assert coverage["known_covered_count"] == 1
    assert coverage["known_no_coverage_count"] == 1
    assert coverage["unknown_count"] == 1
    assert coverage["fresh_known_covered_count"] == 1
    assert coverage["attempted_count"] == 2
    assert coverage["succeeded_count"] == 1
    assert coverage["operational_failure_count"] == 1
