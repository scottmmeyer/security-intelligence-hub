from __future__ import annotations

import json
import socket
import threading
import urllib.request
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer, _macro_liquidity_context_payload


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


def test_macro_liquidity_context_endpoint_returns_display_only_contract() -> None:
    payload = {
        "status": "ok",
        "reporting_only": True,
        "title": "Macro & Liquidity Context",
        "subtitle": "Display-only confirmation of rates, credit, liquidity, volatility, breadth, and known event risk.",
        "sections": {
            "rates": [],
            "credit_funding": [],
            "liquidity": [],
            "market_confirmation": {"availability": "UNAVAILABLE"},
            "event_window": {"events": []},
        },
        "guardrails": {
            "scoring_impact": "none",
            "macro_panel_affects_scoring": "NO",
            "macro_panel_affects_recommendations": "NO",
            "macro_panel_affects_cw_das": "NO",
            "macro_panel_affects_deployment": "NO",
            "macro_panel_affects_allocation": "NO",
            "macro_panel_affects_execution": "NO",
        },
    }

    result = _fetch_json(
        "/api/portfolio/macro-liquidity-context",
        patchers=[
            patch("scripts.run_outcome_ui._macro_liquidity_context_payload", return_value=(payload, 200)),
        ],
    )

    assert result["title"] == "Macro & Liquidity Context"
    assert result["reporting_only"] is True
    assert result["guardrails"]["scoring_impact"] == "none"
    assert "macro_score" not in result
    assert "liquidity_score" not in result
    assert "risk_score" not in result


def test_macro_liquidity_context_endpoint_fails_closed_on_error() -> None:
    result = _fetch_json(
        "/api/portfolio/macro-liquidity-context",
        patchers=[
            patch("scripts.run_outcome_ui._macro_liquidity_context_payload", side_effect=RuntimeError("boom")),
        ],
    )

    assert result["status"] == "degraded"
    assert result["reporting_only"] is True
    assert result["title"] == "Macro & Liquidity Context"
    assert result["guardrails"]["scoring_impact"] == "none"


def test_market_regime_guardrail_ui_hooks_are_present() -> None:
    app_js = (ROOT / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "loadMarketRegimeGuardrail(data);" in app_js
    assert "fetch(url)" in app_js
    assert "/api/market-regime-guardrail/latest" in app_js
    assert "Market Regime Guardrail" in app_js
    assert "No automatic scoring, ranking, allocation, sizing, or execution changes" in app_js
    assert "Freshness Status:" in app_js
    assert "Lag: ${lagDays} day(s)" in app_js
    assert "Input Source" in app_js
    assert "Dedicated Market Regime Proxy" in app_js
    assert "Operator Action:" in app_js
    assert "Action Guidance:" in app_js
    assert "market_proxies_ts || \"unavailable\"" in app_js
    assert "Run Refresh Current Holdings + Buy Candidates" in app_js
    assert "REFRESH_MARKET_PROXIES" in app_js or "operator_action" in app_js
    assert "/api/portfolio/macro-liquidity-context" in app_js
    assert "Macro & Liquidity Context" in app_js
    assert "How to Read Macro Stress" in app_js
    assert "No automatic scoring, recommendation, CW-DAS, deployment, allocation, or execution changes" in app_js


def test_market_regime_guardrail_container_exists() -> None:
    html = (ROOT / "ui" / "portfolio_alignment" / "index.html").read_text(encoding="utf-8")

    assert 'id="marketContextContainer"' in html


def test_macro_wti_crude_fails_closed_on_equity_identity_collision() -> None:
    payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("credit_funding") or []))
    names = {str(r.get("name") or "") for r in rows}
    assert "WTI" not in names

    wti_row = next((r for r in rows if str(r.get("name") or "") == "WTI Crude"), None)
    assert wti_row is not None
    assert wti_row.get("availability") == "UNAVAILABLE"
    assert "No canonical current WTI crude series/proxy is available." in str(wti_row.get("note") or "")
    assert "W&T Offshore" in str(wti_row.get("note") or "")


def test_macro_bno_is_explicit_proxy_not_spot_brent() -> None:
    payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("credit_funding") or []))
    bno_row = next((r for r in rows if str(r.get("name") or "") == "Brent Proxy (BNO)"), None)
    assert bno_row is not None
    assert "proxy_target=Brent crude price movements" in str(bno_row.get("provenance") or "")
    assert "BNO security price/return" in str(bno_row.get("note") or "")


def test_canonical_event_calendar_has_correct_sep_fomc_window_and_tax_event() -> None:
    calendar_path = ROOT / "data" / "mei" / "event_calendar.json"
    events = json.loads(calendar_path.read_text(encoding="utf-8"))

    assert not any(
        "FOMC" in str(ev.get("event_name") or "").upper() and str(ev.get("event_date") or "") == "2026-09-17"
        for ev in events
    )

    fomc_sep = next(
        (
            ev
            for ev in events
            if "FOMC" in str(ev.get("event_name") or "").upper()
            and str(ev.get("start_date") or "") == "2026-09-15"
            and str(ev.get("end_date") or "") == "2026-09-16"
        ),
        None,
    )
    assert fomc_sep is not None
    assert str(fomc_sep.get("source") or "") == "Federal Reserve"
    assert str(fomc_sep.get("source_reference") or "")
    assert str(fomc_sep.get("provenance") or "")
    assert str(fomc_sep.get("verified_as_of") or "")

    tax_sep = next(
        (
            ev
            for ev in events
            if str(ev.get("event_date") or "") == "2026-09-15"
            and "TAX" in str(ev.get("event_type") or "").upper()
        ),
        None,
    )
    assert tax_sep is not None
    assert str(tax_sep.get("source") or "") == "Internal Revenue Service"
    assert "estimated-tax" in str(tax_sep.get("description") or "").lower()
    assert "recommendation" not in tax_sep
    assert "action" not in tax_sep


def test_signal_refresh_status_returns_market_proxy_replay_publish() -> None:
    fake_report = {
        "market_proxy_replay_publish": {
            "attempted": True,
            "status": "completed",
            "reason": "market_regime_replay_artifacts_stale",
            "published": True,
            "latest_proxy_date_before": "2026-05-14",
            "latest_proxy_date_after": "2026-07-14",
            "artifacts": [
                "data/current/replay_inputs.csv",
                "data/current/replay_performance_series.csv",
            ],
            "warnings": [],
            "details": {},
        }
    }
    result = _fetch_json(
        "/api/signal-refresh/status",
        patchers=[
            patch("scripts.run_outcome_ui._refresh_last_report", fake_report),
            patch("scripts.run_outcome_ui._refresh_last_exit_code", 0),
            patch("scripts.run_outcome_ui._refresh_scope_summary", {}),
            patch("scripts.run_outcome_ui._refresh_resolved_intent", "portfolio_signals"),
            patch("scripts.run_outcome_ui._refresh_proc", None),
            patch("scripts.run_outcome_ui._signal_status", return_value={}),
        ],
    )

    publish = result.get("market_proxy_replay_publish") or {}
    assert publish.get("status") == "completed"
    assert publish.get("latest_proxy_date_after") == "2026-07-14"


def test_signal_refresh_status_preserves_bridge_reason_fields() -> None:
    fake_report = {
        "market_proxy_replay_publish": {
            "attempted": True,
            "status": "warning",
            "reason": "blocked_or_zero_row_generation",
            "published": False,
            "latest_proxy_date_before": "2026-05-14",
            "latest_proxy_date_after": None,
            "warnings": [
                "Replay bridge did not publish because TECHNOLOGY generation returned zero rows.",
            ],
            "details": {
                "blocked_industries": ["ENERGY"],
                "zero_row_industries": ["TECHNOLOGY"],
                "failed_industries": [],
                "missing_required_cohorts": [],
                "target_industries": ["TECHNOLOGY", "ENERGY", "BASIC MATERIALS", "INDUSTRIALS"],
            },
        }
    }
    result = _fetch_json(
        "/api/signal-refresh/status",
        patchers=[
            patch("scripts.run_outcome_ui._refresh_last_report", fake_report),
            patch("scripts.run_outcome_ui._refresh_last_exit_code", 0),
            patch("scripts.run_outcome_ui._refresh_scope_summary", {}),
            patch("scripts.run_outcome_ui._refresh_resolved_intent", "portfolio_signals"),
            patch("scripts.run_outcome_ui._refresh_proc", None),
            patch("scripts.run_outcome_ui._signal_status", return_value={}),
        ],
    )

    publish = result.get("market_proxy_replay_publish") or {}
    details = publish.get("details") or {}
    assert publish.get("attempted") is True
    assert publish.get("status") == "warning"
    assert publish.get("reason") == "blocked_or_zero_row_generation"
    assert publish.get("published") is False
    assert details.get("blocked_industries") == ["ENERGY"]
    assert details.get("zero_row_industries") == ["TECHNOLOGY"]
    assert details.get("failed_industries") == []
    assert details.get("missing_required_cohorts") == []
    assert details.get("target_industries") == ["TECHNOLOGY", "ENERGY", "BASIC MATERIALS", "INDUSTRIALS"]


def test_ui_renders_market_proxy_replay_publish_completed() -> None:
    app_js = (ROOT / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "Market proxy replay publish: completed" in app_js
    assert "Latest proxy date:" in app_js


def test_ui_renders_market_proxy_replay_publish_warning() -> None:
    app_js = (ROOT / "ui" / "outcome_visualization" / "app.js").read_text(encoding="utf-8")

    assert "Market proxy replay publish: warning - ${reason || \"replay artifacts were not regenerated\"}" in app_js
    assert "Replay artifacts were not regenerated; Market Regime Guardrail may remain stale." in app_js
    assert "publish.published === false" in app_js
