from __future__ import annotations

import json
import socket
import threading
import urllib.request
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer


ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _fetch_json(path: str, patchers: list | None = None) -> dict:
    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with ExitStack() as stack:
            for p in patchers or []:
                stack.enter_context(p)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as resp:
                assert resp.status == 200
                return json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_market_regime_guardrail_endpoint_returns_display_only_contract() -> None:
    payload = {
        "regime": "DEFENSIVE_ROTATION",
        "severity": "MODERATE",
        "deployment_posture": "ONLY_NON_STRESSED_SECTORS",
        "trim_posture": "REVIEW_OVERWEIGHTS",
        "cash_posture": "HOLD_EXCESS",
        "operator_summary": "Display-only test payload.",
        "evidence": ["test evidence"],
        "affected_symbols": ["NVDA"],
        "stressed_sectors": ["SEMI"],
        "safe_to_deploy": False,
        "confidence": "MEDIUM",
        "data_freshness": {"market_proxies_ts": "2026-06-24", "portfolio_snapshot_ts": "2026-06-25"},
        "guardrail_version": "MRG-1.0",
        "recommended_operator_checks": ["check 1"],
        "scoring_impact": "none",
    }

    result = _fetch_json(
        "/api/market-regime-guardrail/latest",
        patchers=[
            patch("scripts.run_outcome_ui._market_regime_guardrail_payload", return_value=(payload, 200)),
        ],
    )

    assert result["regime"] == "DEFENSIVE_ROTATION"
    assert result["scoring_impact"] == "none"
    assert result["deployment_posture"] == "ONLY_NON_STRESSED_SECTORS"


def test_market_regime_guardrail_ui_hooks_are_present() -> None:
    app_js = (ROOT / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "loadMarketRegimeGuardrail(data);" in app_js
    assert "fetch(url)" in app_js
    assert "/api/market-regime-guardrail/latest" in app_js
    assert "Market Regime Guardrail" in app_js
    assert "No automatic scoring, ranking, allocation, sizing, or execution changes" in app_js
    assert "Freshness Status:" in app_js
    assert "Lag: ${lagDays} day(s)" in app_js
    assert "Operator Action:" in app_js
    assert "REFRESH_MARKET_PROXIES" in app_js or "operator_action" in app_js


def test_market_regime_guardrail_container_exists() -> None:
    html = (ROOT / "ui" / "portfolio_alignment" / "index.html").read_text(encoding="utf-8")

    assert 'id="marketContextContainer"' in html
