from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from contextlib import closing
from unittest.mock import patch

import scripts.run_outcome_ui as run_outcome_ui
from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer


class _DummyProc:
    def poll(self):
        return 0


def _reset_refresh_state() -> None:
    run_outcome_ui._refresh_proc = None
    run_outcome_ui._refresh_last_report = None
    run_outcome_ui._refresh_last_exit_code = None
    run_outcome_ui._refresh_requested_intent = None
    run_outcome_ui._refresh_resolved_intent = None
    run_outcome_ui._refresh_scope_summary = None
    run_outcome_ui._refresh_scope_samples = None
    run_outcome_ui._refresh_provider_planned_totals = {}
    run_outcome_ui._refresh_started_at_utc = None
    run_outcome_ui._refresh_completed_at_utc = None


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _post_signal_refresh(payload: dict, patchers: list | None = None) -> tuple[int, dict, list[str]]:
    _reset_refresh_state()
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    captured: list[str] = []

    def _fake_popen(cmd, **_kwargs):
        captured.extend(cmd)
        return _DummyProc()

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/signal-refresh",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with patch("scripts.run_outcome_ui.subprocess.Popen", side_effect=_fake_popen):
            for p in patchers or []:
                p.start()
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status, json.loads(resp.read().decode("utf-8")), captured
            finally:
                for p in reversed(patchers or []):
                    p.stop()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        _reset_refresh_state()


def _post_signal_refresh_error(payload: dict) -> tuple[int, dict]:
    _reset_refresh_state()
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/signal-refresh",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as _resp:
            raise AssertionError("expected HTTP error")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        _reset_refresh_state()


def test_refresh_intent_holdings_plus_buy_candidates_supported() -> None:
    fake_scope = {
        "scope_summary": {
            "portfolio_holdings_count": 79,
            "buy_candidate_count": 47,
            "mandatory_dependency_count": 12,
            "deduped_symbol_count": 138,
            "full_universe_count": 2473,
        },
        "planned_symbol_samples": {
            "portfolio_holdings": ["MU", "VRT", "DELL"],
            "buy_candidates": ["ARW", "LRCX", "CAH"],
            "mandatory_dependencies": ["SPY", "QQQ"],
        },
        "planned_symbols": {
            "provider_symbols": {
                "zacks": ["MU", "VRT"],
                "danelfin": ["MU", "VRT"],
                "yahoo": ["MU", "VRT"],
            }
        },
    }

    status, body, cmd = _post_signal_refresh(
        {"intent": "holdings_plus_buy_candidates"},
        patchers=[patch("scripts.run_outcome_ui._refresh_scope_plan", return_value=fake_scope)],
    )

    assert status == 200
    assert body["accepted"] is True
    assert body["resolved_intent"] == "holdings_plus_buy_candidates"
    assert body["scope_summary"]["deduped_symbol_count"] == 138
    assert "79 holdings + 47 buy candidates + 12 required dependencies = 138 symbols" in body["scope_formula"]
    assert "refresh_signals.py" in " ".join(cmd)
    assert "--refresh-mode" in cmd
    assert "holdings_plus_buy_candidates" in cmd


def test_holdings_plus_buy_candidates_scope_dedupes_symbols() -> None:
    fake_scope = {
        "scope_summary": {
            "portfolio_holdings_count": 3,
            "buy_candidate_count": 3,
            "mandatory_dependency_count": 1,
            "deduped_symbol_count": 4,
            "full_universe_count": 2473,
        },
        "planned_symbol_samples": {
            "portfolio_holdings": ["MU", "VRT", "DELL"],
            "buy_candidates": ["VRT", "ARW", "MU"],
            "mandatory_dependencies": ["SPY"],
        },
        "planned_symbols": {"provider_symbols": {"zacks": ["MU", "VRT", "DELL", "SPY"], "danelfin": [], "yahoo": []}},
    }

    status, body, _cmd = _post_signal_refresh(
        {"intent": "holdings_plus_buy_candidates"},
        patchers=[patch("scripts.run_outcome_ui._refresh_scope_plan", return_value=fake_scope)],
    )

    assert status == 200
    assert body["scope_summary"]["deduped_symbol_count"] == 4


def test_holdings_plus_buy_candidates_does_not_use_full_universe() -> None:
    fake_scope = {
        "scope_summary": {
            "portfolio_holdings_count": 79,
            "buy_candidate_count": 47,
            "mandatory_dependency_count": 12,
            "deduped_symbol_count": 138,
            "full_universe_count": 2473,
        },
        "planned_symbol_samples": {"portfolio_holdings": [], "buy_candidates": [], "mandatory_dependencies": []},
        "planned_symbols": {"provider_symbols": {"zacks": ["AAPL"], "danelfin": ["AAPL"], "yahoo": ["AAPL"]}},
    }

    status, _body, cmd = _post_signal_refresh(
        {"intent": "holdings_plus_buy_candidates"},
        patchers=[patch("scripts.run_outcome_ui._refresh_scope_plan", return_value=fake_scope)],
    )

    assert status == 200
    assert "rebuild_research_universe" not in cmd


def test_existing_refresh_modes_still_supported() -> None:
    for intent in ("stale_only", "portfolio_signals", "rebuild_research_universe", "prepare_portfolio_review"):
        status, body, _cmd = _post_signal_refresh({"intent": intent})
        assert status == 200
        assert body["accepted"] is True
        assert body["resolved_intent"] == intent


def test_unknown_refresh_intent_rejected() -> None:
    status, body = _post_signal_refresh_error({"intent": "not_real"})

    assert status == 400
    assert body["accepted"] is False
    assert body["error"] == "unknown refresh intent"
    assert "holdings_plus_buy_candidates" in body["allowed_intents"]
