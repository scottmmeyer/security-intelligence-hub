from __future__ import annotations

import csv
import json
import socket
import threading
import urllib.request
from datetime import date
from contextlib import ExitStack, closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.run_outcome_ui import (
    _Handler,
    _ThreadingTCPServer,
    _macro_liquidity_context_payload,
    _macro_series_points,
)


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
    assert "symbol=WTI" not in str(wti_row.get("source") or "")
    if wti_row.get("availability") == "UNAVAILABLE":
        assert "SIH does not relabel equity ticker WTI as crude oil" in str(wti_row.get("note") or "")


def test_macro_bno_is_explicit_proxy_not_spot_brent() -> None:
    payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("credit_funding") or []))
    bno_row = next((r for r in rows if str(r.get("name") or "") == "Brent Proxy (BNO)"), None)
    assert bno_row is not None
    assert "proxy_target=Brent crude price movements" in str(bno_row.get("provenance") or "")
    assert "BNO security price/return" in str(bno_row.get("note") or "")


def test_macro_us_2y_uses_dgs2_not_fvx() -> None:
    payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("rates") or []))
    row = next((r for r in rows if str(r.get("name") or "") == "US 2Y Treasury"), None)
    assert row is not None
    assert "^FVX" not in str(row.get("source") or "")
    assert "DGS2" in str(row.get("source") or "")


def test_macro_dxy_is_fail_closed_without_exact_dxy_series() -> None:
    payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("credit_funding") or []))
    row = next((r for r in rows if str(r.get("name") or "") == "DXY"), None)
    assert row is not None
    assert row.get("availability") == "UNAVAILABLE"
    assert "exact DXY canonical series" in str(row.get("note") or "")


def test_macro_missing_series_remains_unavailable_not_zero() -> None:
    with patch("scripts.run_outcome_ui._macro_series_points", return_value=[]):
        payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rates = list(((payload.get("sections") or {}).get("rates") or []))
    row = next((r for r in rates if str(r.get("name") or "") == "US 2Y Treasury"), None)
    assert row is not None
    assert row.get("current_value") == "UNAVAILABLE"
    assert row.get("availability") == "UNAVAILABLE"


def test_curve_requires_same_observation_date() -> None:
    def _points(series_id: str):
        if series_id == "DGS2":
            return [("2026-08-20", 3.8, {"series_id": "DGS2", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"})]
        if series_id == "DGS10":
            return [("2026-08-19", 4.2, {"series_id": "DGS10", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-19", "provenance": "p"})]
        if series_id == "DGS30":
            return [("2026-08-19", 4.6, {"series_id": "DGS30", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-19", "provenance": "p"})]
        return []

    with patch("scripts.run_outcome_ui._macro_series_points", side_effect=_points):
        payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("rates") or []))
    curve = next((r for r in rows if str(r.get("name") or "") == "2s10s Curve"), None)
    assert curve is not None
    assert curve.get("availability") == "UNAVAILABLE"


def test_hy_ig_oas_differential_derives_from_same_date_series() -> None:
    def _points(series_id: str):
        if series_id == "BAMLH0A0HYM2":
            return [("2026-08-20", 3.0, {"series_id": "BAMLH0A0HYM2", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"})]
        if series_id == "BAMLC0A0CM":
            return [("2026-08-20", 1.2, {"series_id": "BAMLC0A0CM", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"})]
        return []

    with patch("scripts.run_outcome_ui._macro_series_points", side_effect=_points):
        payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rows = list(((payload.get("sections") or {}).get("credit_funding") or []))
    diff = next((r for r in rows if str(r.get("name") or "") == "HY-IG OAS Differential"), None)
    assert diff is not None
    assert diff.get("availability") == "AVAILABLE"
    assert "bp" in str(diff.get("current_value") or "")


def test_rate_like_series_changes_render_in_basis_points() -> None:
    def _points(series_id: str):
        if series_id == "DGS10":
            return [
                ("2026-08-19", 4.65, {"series_id": "DGS10", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-19", "provenance": "p"}),
                ("2026-08-20", 4.69, {"series_id": "DGS10", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"}),
            ]
        if series_id == "SOFR":
            return [
                ("2026-08-19", 3.62, {"series_id": "SOFR", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-19", "provenance": "p"}),
                ("2026-08-20", 3.63, {"series_id": "SOFR", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"}),
            ]
        return []

    with patch("scripts.run_outcome_ui._macro_series_points", side_effect=_points):
        payload, status = _macro_liquidity_context_payload()

    assert status == 200
    rates = list(((payload.get("sections") or {}).get("rates") or []))
    ten_year = next((r for r in rates if str(r.get("name") or "") == "US 10Y Treasury"), None)
    assert ten_year is not None
    assert str(ten_year.get("change_1d") or "") == "+4 bp"

    liquidity = list(((payload.get("sections") or {}).get("liquidity") or []))
    sofr = next((r for r in liquidity if str(r.get("name") or "") == "SOFR"), None)
    assert sofr is not None
    assert str(sofr.get("change_1d") or "") == "+1 bp"


def test_non_rate_series_changes_remain_percent() -> None:
    payload, status = _macro_liquidity_context_payload()
    assert status == 200
    rows = list(((payload.get("sections") or {}).get("credit_funding") or []))
    vix = next((r for r in rows if str(r.get("name") or "") == "VIX"), None)
    if vix and vix.get("availability") == "AVAILABLE":
        assert "%" in str(vix.get("change_1d") or "") or str(vix.get("change_1d") or "") == "UNAVAILABLE"


def test_iorb_uses_runtime_cutoff_and_common_date_for_sofr_relationship() -> None:
    def _points(series_id: str):
        if series_id == "SOFR":
            return [
                ("2026-08-19", 3.62, {"series_id": "SOFR", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-19", "provenance": "p"}),
                ("2026-08-20", 3.63, {"series_id": "SOFR", "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"}),
            ]
        if series_id == "IORB":
            return [
                ("2026-08-19", 3.65, {"series_id": "IORB", "source_provider": "FRED", "units": "Percent", "frequency": "Daily, 7-Day", "expected_update_frequency": "daily_7_day_administered_rate", "observation_date": "2026-08-19", "provenance": "p"}),
                ("2026-08-20", 3.65, {"series_id": "IORB", "source_provider": "FRED", "units": "Percent", "frequency": "Daily, 7-Day", "expected_update_frequency": "daily_7_day_administered_rate", "observation_date": "2026-08-20", "provenance": "p"}),
                ("2026-08-21", 3.65, {"series_id": "IORB", "source_provider": "FRED", "units": "Percent", "frequency": "Daily, 7-Day", "expected_update_frequency": "daily_7_day_administered_rate", "observation_date": "2026-08-21", "provenance": "p"}),
                ("2026-08-22", 3.65, {"series_id": "IORB", "source_provider": "FRED", "units": "Percent", "frequency": "Daily, 7-Day", "expected_update_frequency": "daily_7_day_administered_rate", "observation_date": "2026-08-22", "provenance": "p"}),
                ("2026-08-24", 3.65, {"series_id": "IORB", "source_provider": "FRED", "units": "Percent", "frequency": "Daily, 7-Day", "expected_update_frequency": "daily_7_day_administered_rate", "observation_date": "2026-08-24", "provenance": "p"}),
            ]
        # Keep other required series available so payload builds normally.
        if series_id in {"DGS2", "DGS10", "DGS30", "BAMLC0A0CM", "BAMLH0A0HYM2", "VIXCLS", "DCOILWTICO", "DCOILBRENTEU", "WTREGEN", "WRESBAL", "RRPONTSYD", "DTWEXBGS"}:
            return [("2026-08-20", 1.0, {"series_id": series_id, "source_provider": "FRED", "units": "Percent", "frequency": "Business Daily", "expected_update_frequency": "business_daily", "observation_date": "2026-08-20", "provenance": "p"})]
        return []

    with patch("scripts.run_outcome_ui._macro_series_points", side_effect=_points):
        payload, status = _macro_liquidity_context_payload()

    assert status == 200
    liquidity = list(((payload.get("sections") or {}).get("liquidity") or []))
    iorb = next((r for r in liquidity if str(r.get("name") or "") == "IORB"), None)
    rel = next((r for r in liquidity if str(r.get("name") or "") == "IORB-SOFR Relationship"), None)

    assert iorb is not None
    assert iorb.get("availability") == "AVAILABLE"
    assert str(iorb.get("as_of") or "") == date.today().isoformat()
    assert "Daily, 7-Day" in str(iorb.get("note") or "") or "daily_7_day_administered_rate" in str(iorb.get("note") or "")
    assert "IORB" in str(iorb.get("source") or "")

    assert rel is not None
    assert rel.get("availability") == "AVAILABLE"
    assert str(rel.get("as_of") or "") == "2026-08-20"
    assert "bp" in str(rel.get("current_value") or "")
    assert "+2" in str(rel.get("current_value") or "") or "2.0" in str(rel.get("current_value") or "")


def test_iorb_metadata_semantics_are_not_business_day_only() -> None:
    with (ROOT / "data" / "current" / "macro_liquidity_series.csv").open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    iorb = next(row for row in rows if row.get("series_id") == "IORB")
    assert iorb["frequency"] == "Daily, 7-Day"
    assert iorb["expected_update_frequency"] == "daily_7_day_administered_rate"
    assert "business" not in iorb["frequency"].lower()
    assert "business_daily" not in iorb["expected_update_frequency"].lower()


def test_macro_series_points_cache_invalidates_on_mtime_change() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        series_dir = root / "series_id=DGS2"
        series_dir.mkdir(parents=True, exist_ok=True)
        path = series_dir / "observations.csv"
        path.write_text(
            "series_id,display_name,source_provider,source_agency,units,frequency,expected_update_frequency,observation_date,value,materialized_at_utc,availability,freshness_state,age_days,source_url,series_url,artifact_path,provenance\n"
            "DGS2,US 2Y Treasury,FRED,Federal Reserve,Percent,Business Daily,business_daily,2026-08-19,4.10,ts,AVAILABLE,FRESH,0,u,s,a,p\n",
            encoding="utf-8",
        )

        with patch("scripts.run_outcome_ui._MACRO_HISTORY_ROOT", root):
            p1 = _macro_series_points("DGS2")
            p2 = _macro_series_points("DGS2")
            assert p1[-1][0] == "2026-08-19"
            assert p2[-1][0] == "2026-08-19"

            # Update file and ensure cache invalidates via mtime/size token.
            path.write_text(
                "series_id,display_name,source_provider,source_agency,units,frequency,expected_update_frequency,observation_date,value,materialized_at_utc,availability,freshness_state,age_days,source_url,series_url,artifact_path,provenance\n"
                "DGS2,US 2Y Treasury,FRED,Federal Reserve,Percent,Business Daily,business_daily,2026-08-19,4.10,ts,AVAILABLE,FRESH,0,u,s,a,p\n"
                "DGS2,US 2Y Treasury,FRED,Federal Reserve,Percent,Business Daily,business_daily,2026-08-20,4.19,ts,AVAILABLE,FRESH,0,u,s,a,p\n",
                encoding="utf-8",
            )
            p3 = _macro_series_points("DGS2")
            assert p3[-1][0] == "2026-08-20"


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


def test_ui_restore_normalizes_backend_run_wrapper() -> None:
    app_js = (ROOT / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")
    assert "function _normalizeRestoredRunData" in app_js
    assert "holdings_count" in app_js
    assert "holding_count" in app_js
    assert "snapshot_date = pickFirst" in app_js
    assert "recommendation_count = pickFirst" in app_js
    assert "concentration_tier = pickFirst" in app_js
    assert "mandate_type = pickFirst" in app_js
    assert "_analysisResult = _normalizeRestoredRunData(data);" in app_js
    assert "const backendRun = _normalizeRestoredRunData(await _loadLatestRunFromBackend());" in app_js


def test_ui_boot_has_no_removed_debug_helper_dependency() -> None:
    app_js = (ROOT / "ui" / "portfolio_alignment" / "app.js").read_text(encoding="utf-8")

    assert "_addDebugMsg" not in app_js
    assert "const saved = _normalizeRestoredRunData(_loadSavedResult());" in app_js
    assert "const backendRun = _normalizeRestoredRunData(await _loadLatestRunFromBackend());" in app_js


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
