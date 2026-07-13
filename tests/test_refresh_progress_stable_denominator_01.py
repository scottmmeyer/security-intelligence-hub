from __future__ import annotations

import csv
import json
import socket
import threading
import urllib.request
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from scripts import run_outcome_ui as outcome_ui
from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_refresh_progress_uses_stable_denominator(tmp_path, monkeypatch) -> None:
    today = outcome_ui.date.today().isoformat()
    root = tmp_path
    zacks = root / "latest_zacks.csv"
    danelfin = root / "latest_danelfin.csv"
    yahoo = root / "latest_yahoo_supplemental.csv"

    _write_csv(
        zacks,
        ["symbol", "zacks_rank", "zacks_score", "sourced_date"],
        [{"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "sourced_date": today}],
    )
    _write_csv(
        danelfin,
        ["symbol", "danelfin_raw", "danelfin_score", "sourced_date"],
        [{"symbol": "AAPL", "danelfin_raw": "8", "danelfin_score": "4.0", "sourced_date": today}],
    )
    _write_csv(
        yahoo,
        ["symbol", "price_target", "analyst_count", "current_price", "sourced_date"],
        [{"symbol": "AAPL", "price_target": "200", "analyst_count": "12", "current_price": "180", "sourced_date": today}],
    )

    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", root)
    monkeypatch.setattr(outcome_ui, "_SIGNAL_FILES", {"zacks": zacks, "danelfin": danelfin, "yahoo": yahoo})
    monkeypatch.setattr(outcome_ui, "_ESS_SIGNAL_SNAPSHOT", root / "missing_ess.csv")
    monkeypatch.setattr(outcome_ui, "_ESS_COVERAGE_WARNING", root / "missing_ess_warning.json")

    fake_summary = {
        "run_id": "PAR-TEST",
        "active_holdings_baseline": 54,
        "applicable_holdings": 54,
        "covered_today": 21,
        "covered_within_threshold": 21,
        "stale": 33,
        "missing": 0,
        "failed": 0,
        "not_applicable": 0,
        "status": "DEGRADED",
    }

    with patch("src.portfolio.holdings_coverage.summarize_holdings_coverage", return_value=fake_summary):
        status = outcome_ui._signal_status()

    assert status["zacks"]["completed_count"] == 1
    assert status["zacks"]["planned_total_count"] == 54
    assert status["zacks"]["progress_label"] == "1/54"
    assert status["zacks"]["is_complete"] is False


def test_refresh_progress_unknown_total_fallback(tmp_path, monkeypatch) -> None:
    today = outcome_ui.date.today().isoformat()
    root = tmp_path
    zacks = root / "latest_zacks.csv"

    _write_csv(
        zacks,
        ["symbol", "zacks_rank", "zacks_score", "sourced_date"],
        [{"symbol": "AAPL", "zacks_rank": "1", "zacks_score": "5", "sourced_date": today}],
    )

    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", root)
    monkeypatch.setattr(outcome_ui, "_SIGNAL_FILES", {"zacks": zacks, "danelfin": zacks, "yahoo": zacks})
    monkeypatch.setattr(outcome_ui, "_ESS_SIGNAL_SNAPSHOT", root / "missing_ess.csv")
    monkeypatch.setattr(outcome_ui, "_ESS_COVERAGE_WARNING", root / "missing_ess_warning.json")

    fake_summary = {
        "run_id": "PAR-TEST",
        "active_holdings_baseline": 54,
        "applicable_holdings": None,
        "covered_today": 21,
        "covered_within_threshold": 21,
        "stale": 33,
        "missing": 0,
        "failed": 0,
        "not_applicable": 0,
        "status": "DEGRADED",
    }

    with patch("src.portfolio.holdings_coverage.summarize_holdings_coverage", return_value=fake_summary):
        status = outcome_ui._signal_status()

    assert status["zacks"]["planned_total_count"] is None
    assert status["zacks"]["progress_label"] == "1 rows processed"
    assert status["zacks"]["progress_pct"] is None


def test_signal_refresh_status_exposes_provider_progress_contract() -> None:
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = {
            "zacks": {
                "completed_count": 21,
                "planned_total_count": 21,
                "progress_pct": 38.9,
                "progress_label": "21/21",
                "is_complete": False,
            },
            "danelfin": {
                "completed_count": 34,
                "planned_total_count": 34,
                "progress_pct": 63.0,
                "progress_label": "34/34",
                "is_complete": False,
            },
            "yahoo": {
                "completed_count": 54,
                "planned_total_count": 54,
                "progress_pct": 100.0,
                "progress_label": "54/54",
                "is_complete": True,
            },
            "ess": {},
        }
        with patch("scripts.run_outcome_ui._signal_status", return_value=payload), patch(
            "scripts.run_outcome_ui._refresh_provider_planned_totals",
            {"zacks": 54, "danelfin": 54, "yahoo": 54},
        ), patch(
            "scripts.run_outcome_ui._refresh_resolved_intent",
            "holdings_plus_buy_candidates",
        ), patch(
            "scripts.run_outcome_ui._refresh_scope_summary",
            {
                "portfolio_holdings_count": 79,
                "buy_candidate_count": 47,
                "mandatory_dependency_count": 12,
                "market_proxy_count": 7,
                "deduped_symbol_count": 138,
                "full_universe_count": 2473,
            },
        ):
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/signal-refresh/status", timeout=5) as resp:
                assert resp.status == 200
                body = json.loads(resp.read().decode("utf-8"))

        assert "provider_progress" in body
        assert body["provider_progress"]["zacks"]["progress_label"] == "21/54"
        assert body["provider_progress"]["zacks"]["planned_total_count"] == 54
        assert body["provider_progress"]["danelfin"]["progress_label"] == "34/54"
        assert body["provider_progress"]["yahoo"]["is_complete"] is True
        assert "79 holdings + 47 buy candidates + 12 required dependencies + 7 market proxies = 138 symbols" in body["scope_formula"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_provider_health_metrics_preserved() -> None:
    fake_report = {
        "refresh_date": "2026-07-09",
        "providers": {
            "zacks": {
                "submitted_count": 54,
                "written_count": 21,
                "missing_written_count": 33,
                "true_error_count": 2,
                "no_coverage_count": 3,
                "no_score_count": 1,
                "stale_carryover_count": 4,
                "failed": 2,
            },
        },
    }

    with patch("scripts.run_outcome_ui._refresh_last_report", fake_report), patch(
        "scripts.run_outcome_ui._signal_status",
        return_value={"zacks": {}, "danelfin": {}, "yahoo": {}, "ess": {}, "portfolio_holdings_coverage": {"providers": {}}},
    ), patch("scripts.run_outcome_ui._count_research_universe_rows", return_value=54):
        payload = outcome_ui._refresh_transparency_payload()

    metrics = payload["provider_counts"]["zacks"]
    assert metrics["written"] == 21
    assert metrics["missing_written"] == 33
    assert metrics["true_error"] == 2
    assert metrics["no_coverage"] == 3
    assert metrics["no_score"] == 1
    assert metrics["stale_carryover"] == 4
    assert metrics["failed"] == 2
