from __future__ import annotations

import json
import socket
import sys
import threading
import urllib.error
import socketserver
import urllib.request
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_outcome_ui as run_outcome_ui


def _server_class():
    return getattr(run_outcome_ui, "_ThreadingTCPServer", socketserver.TCPServer)


class _DummyProc:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def poll(self):
        return None


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _reset_refresh_globals() -> None:
    run_outcome_ui._refresh_proc = None
    run_outcome_ui._refresh_last_report = None
    run_outcome_ui._refresh_last_exit_code = None
    run_outcome_ui._refresh_requested_intent = None
    run_outcome_ui._refresh_resolved_intent = None
    run_outcome_ui._refresh_universe_scope = None
    run_outcome_ui._refresh_estimated_symbol_count = None
    run_outcome_ui._refresh_updates = []
    run_outcome_ui._refresh_does_not_update = []
    run_outcome_ui._refresh_research_universe_expected = False
    run_outcome_ui._refresh_candidate_readiness_expected = False
    run_outcome_ui._refresh_started_at_utc = None
    run_outcome_ui._refresh_completed_at_utc = None


def _post_signal_refresh(payload: dict) -> tuple[int, dict, list[str]]:
    _reset_refresh_globals()
    port = _free_port()
    server = _server_class()(("127.0.0.1", port), run_outcome_ui._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    captured_cmd: list[str] = []

    def _fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _DummyProc(cmd, kwargs)

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/signal-refresh",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with patch("scripts.run_outcome_ui.subprocess.Popen", side_effect=_fake_popen):
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8")), captured_cmd
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        _reset_refresh_globals()


def _post_signal_refresh_error(payload: dict) -> tuple[int, dict]:
    _reset_refresh_globals()
    port = _free_port()
    server = _server_class()(("127.0.0.1", port), run_outcome_ui._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/signal-refresh",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as _resp:
            raise AssertionError("Expected HTTP error")
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8"))
        return exc.code, body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        _reset_refresh_globals()


def _get_json(path: str) -> tuple[int, dict]:
    _reset_refresh_globals()
    port = _free_port()
    server = _server_class()(("127.0.0.1", port), run_outcome_ui._Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        _reset_refresh_globals()


def test_signal_refresh_defaults_to_portfolio_signals_when_intent_omitted():
    status, body, cmd = _post_signal_refresh({})

    assert status == 200
    assert body["accepted"] is True
    assert body["started"] is True
    assert body["requested_intent"] == "portfolio_signals"
    assert body["resolved_intent"] == "portfolio_signals"
    assert body["mode"] == "portfolio_signals"
    assert body["universe_scope"] == "portfolio_holdings"
    assert "research_universe_freshness" in body["does_not_update"]
    assert "holdings_readiness" in body["updates"]
    assert "refresh_signals.py" in " ".join(cmd)
    assert "portfolio_signals" in cmd


def test_signal_refresh_honors_rebuild_research_universe_without_silent_downgrade():
    status, body, cmd = _post_signal_refresh({"intent": "rebuild_research_universe"})

    assert status == 200
    assert body["accepted"] is True
    assert body["requested_intent"] == "rebuild_research_universe"
    assert body["resolved_intent"] == "rebuild_research_universe"
    assert body["mode"] == "rebuild_research_universe"
    assert body["universe_scope"] == "research_universe"
    assert body["candidate_readiness_expected"] is True
    assert body["research_universe_freshness_expected"] is True
    assert body["does_not_update"] == []
    assert "refresh_signals.py" in " ".join(cmd)
    assert "rebuild_research_universe" in cmd
    assert "--smart" not in cmd


def test_signal_refresh_rejects_unknown_intent():
    status, body = _post_signal_refresh_error({"intent": "not_a_real_intent"})

    assert status == 400
    assert body["accepted"] is False
    assert body["error"] == "unknown refresh intent"
    assert body["requested_intent"] == "not_a_real_intent"
    assert "portfolio_signals" in body["allowed_intents"]
    assert "rebuild_research_universe" in body["allowed_intents"]


def test_signal_refresh_prepare_portfolio_review_reports_expected_updates():
    status, body, cmd = _post_signal_refresh({"intent": "prepare_portfolio_review"})

    assert status == 200
    assert body["accepted"] is True
    assert body["resolved_intent"] == "prepare_portfolio_review"
    assert body["mode"] == "prepare_portfolio_review"
    assert body["universe_scope"] == "portfolio_review_bundle"
    assert "portfolio_review_artifacts" in body["updates"]
    assert "research_universe_freshness_guarantee" in body["does_not_update"]
    assert "prepare_portfolio_review.py" in " ".join(cmd)


def test_refresh_transparency_endpoint_contract_compatibility():
    status, body = _get_json("/api/refresh-transparency")

    assert status == 200
    assert "status" in body
    assert "latest_refresh_date" in body
    assert "provider_counts" in body
    assert "decision_readiness" in body
    assert "warnings" in body
    assert "artifacts" in body
    assert "readiness" in body
    assert "rows" in body
    assert "manual_sources" in body
    assert "compatibility" in body
    assert body["compatibility"]["endpoint"] == "/api/refresh-transparency"
    assert "ess_lseg" in body["manual_sources"]
    assert "manual_source" in body["manual_sources"]["ess_lseg"]
    assert body["manual_sources"]["ess_lseg"]["manual_source"] is True

    readiness = body["readiness"]
    for key in ("research_universe", "cw_das", "ucf", "recommendations", "cra"):
        assert key in readiness
        metric = readiness[key]
        assert "core_fresh_pct" in metric
        assert "core_fresh" in metric
        assert "total" in metric
        assert "stale_or_missing" in metric
        assert "status" in metric

    signal_status_code, signal_status_body = _get_json("/api/signal-status")
    refresh_status_code, refresh_status_body = _get_json("/api/signal-refresh/status")
    assert signal_status_code == 200
    assert refresh_status_code == 200
    assert "_running" in signal_status_body
    assert "running" in refresh_status_body


def test_signal_status_exposes_ess_and_holdings_coverage_contract():
    status, body = _get_json("/api/signal-status")

    assert status == 200
    assert "ess" in body
    assert "badge_state" in body["ess"]
    assert "sourced_date" in body["ess"]
    assert "portfolio_holdings_coverage" in body
    coverage = body["portfolio_holdings_coverage"]
    assert "providers" in coverage
    providers = coverage["providers"]
    for key in ("zacks", "danelfin", "yahoo"):
        assert key in providers
        assert "applicable_holdings" in providers[key]
