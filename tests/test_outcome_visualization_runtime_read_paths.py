from __future__ import annotations

import json
import re
import socket
import threading
from contextlib import closing, contextmanager
from functools import partial
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from scripts.run_outcome_ui import _Handler, _ThreadingTCPServer


REPO_ROOT = Path(__file__).resolve().parents[1]
CHROME_EXECUTABLE = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _base_refresh_transparency_payload() -> dict:
    return {
        "decision_readiness": {
            "classification": "MEDIUM",
            "core_fresh_pct": 92.6,
            "stale_or_missing": 4,
            "has_provider_failures": False,
        },
        "readiness": {
            "research_universe": {"status": "MEDIUM", "core_fresh": 50, "total": 54, "core_fresh_pct": 92.6},
            "cw_das": {"status": "MEDIUM", "core_fresh": 50, "total": 54, "core_fresh_pct": 92.6},
            "ucf": {"status": "MEDIUM", "core_fresh": 50, "total": 54, "core_fresh_pct": 92.6},
            "recommendations": {"status": "MEDIUM", "core_fresh": 50, "total": 54, "core_fresh_pct": 92.6},
            "cra": {"status": "MEDIUM", "core_fresh": 50, "total": 54, "core_fresh_pct": 92.6},
        },
        "rows": [
            {
                "symbol": "AAPL",
                "zacks": {"state": "fresh", "date": "2026-08-17"},
                "danelfin": {"state": "fresh", "date": "2026-08-15"},
                "yahoo": {"state": "fresh", "date": "2026-08-17"},
                "ess": {"state": "fresh", "date": "2026-08-17"},
                "fmp": {"state": "missing", "date": "NA"},
                "freshness": "FRESH",
            }
        ],
    }


def _base_signal_status_payload() -> dict:
    return {
        "zacks": {
            "sourced_date": "2026-08-17",
            "badge_state": "FRESH",
            "attempted_count": 63,
            "with_data_count": 63,
            "coverage_pct": 100.0,
        },
        "danelfin": {
            "sourced_date": "2026-08-15",
            "badge_state": "STALE",
            "attempted_count": 63,
            "with_data_count": 63,
            "coverage_pct": 100.0,
        },
        "yahoo": {
            "sourced_date": "2026-08-17",
            "badge_state": "FRESH",
            "attempted_count": 63,
            "with_data_count": 63,
            "coverage_pct": 100.0,
        },
        "ess": {
            "sourced_date": "2026-08-17",
            "badge_state": "FRESH",
            "coverage_warning_count": 0,
            "coverage_warning_examples": [],
        },
        "portfolio_holdings_coverage": {
            "run_id": "PAR-20260817-40E00509",
            "active_holdings_baseline": 67,
            "threshold_days": 2,
            "providers": {
                "zacks": {
                    "status": "COMPLIANT",
                    "applicable_holdings": 54,
                    "covered_today": 0,
                    "covered_within_threshold": 54,
                    "stale": 0,
                    "missing": 0,
                    "not_applicable": 13,
                    "failed": 0,
                },
                "danelfin": {
                    "status": "COMPLIANT",
                    "applicable_holdings": 54,
                    "covered_today": 0,
                    "covered_within_threshold": 54,
                    "stale": 0,
                    "missing": 0,
                    "not_applicable": 13,
                    "failed": 0,
                },
                "yahoo": {
                    "status": "COMPLIANT",
                    "applicable_holdings": 54,
                    "covered_today": 0,
                    "covered_within_threshold": 54,
                    "stale": 0,
                    "missing": 0,
                    "not_applicable": 13,
                    "failed": 0,
                },
            },
        },
    }


def _base_refresh_status_payload(running: bool) -> dict:
    return {
        "running": running,
        "provider_progress": {
            "zacks": {
                "completed_count": 0,
                "planned_total_count": 54,
                "progress_pct": 0.0,
                "progress_label": "0/54",
                "is_complete": False,
            },
            "danelfin": {
                "completed_count": 0,
                "planned_total_count": 54,
                "progress_pct": 0.0,
                "progress_label": "0/54",
                "is_complete": False,
            },
            "yahoo": {
                "completed_count": 0,
                "planned_total_count": 54,
                "progress_pct": 0.0,
                "progress_label": "0/54",
                "is_complete": False,
            },
        },
        "scope_summary": {},
    }


def _base_routes(*, replay_series_status: int, refresh_running: bool, refresh_completed_count: int = 0) -> list[tuple[str, object, int, str]]:
    refresh_status = _base_refresh_status_payload(refresh_running)
    for provider in ("zacks", "danelfin", "yahoo"):
        refresh_status["provider_progress"][provider]["completed_count"] = refresh_completed_count
        refresh_status["provider_progress"][provider]["progress_label"] = f"{refresh_completed_count}/54"
        refresh_status["provider_progress"][provider]["progress_pct"] = round((refresh_completed_count / 54) * 100.0, 1)

    return [
        (r".*/data/current/replay_performance_series\.csv$", "", replay_series_status, "text/csv"),
        (r".*/data/current/replay_inputs\.csv$", "replay_id,filter_geography,filter_market_cap_bucket,filter_industry,top_n,selected_symbols\nR1,US,LARGE,ALL,20,AAPL|MSFT\n", 200, "text/csv"),
        (r".*/data/current/replay_availability\.csv$", "geography,market_cap_bucket,industry,replay_generated,replay_status,benchmark_available,vehicle_available,stock_replay_available,top_n_available,missing_dependencies\nUS,LARGE,ALL,true,READY,true,true,true,true,\n", 200, "text/csv"),
        (r".*/data/current/replay_matrix\.csv$", "replay_id,geography,market_cap_bucket,industry,replay_metadata_path,replay_evidence_summary_path\nR1,US,LARGE,ALL,,\n", 200, "text/csv"),
        (r".*/data/current/analytical_universe\.csv$", "symbol,filter_industry,filter_geography,filter_market_cap_bucket,top_n\nAAPL,ALL,US,LARGE,20\n", 200, "text/csv"),
        (r".*/config/benchmark_category_registry\.yaml$", "benchmarks:\n  - benchmark_id: BM1\n    name: Benchmark One\n", 200, "text/yaml"),
        (r".*/config/investable_vehicle_registry\.yaml$", "vehicles:\n  - vehicle_id: V1\n    name: Vehicle One\n", 200, "text/yaml"),
        (r".*/data/current/current_snapshot_metadata\.json$", json.dumps({"snapshot_date": "2026-08-17", "generated_at_utc": "2026-08-17T00:00:00Z", "freshness_status": "FRESH", "run_id": "PAR-20260817-40E00509"}), 200, "application/json"),
        (r".*/api/signal-status$", _base_signal_status_payload(), 200, "application/json"),
        (r".*/api/signal-refresh/status$", refresh_status, 200, "application/json"),
        (r".*/api/refresh-transparency$", _base_refresh_transparency_payload(), 200, "application/json"),
        (r".*/api/portfolio/runs$", {"portfolios": [{"run_id": "PAR-20260817-40E00509", "status": "COMPLETE", "snapshot_date": "2026-08-17", "holding_count": 77}]}, 200, "application/json"),
        (r".*/data/portfolio_ingestion/analysis_runs/PAR-20260817-40E00509/deployment_plan\.json$", {"run_id": "PAR-20260817-40E00509", "deployable_cash": 6898, "recommendations": []}, 200, "application/json"),
        (r".*/data/portfolio_ingestion/analysis_runs/PAR-20260817-40E00509/deployment_queue\.json$", {"run_id": "PAR-20260817-40E00509", "queue": [], "cash_context": {"deployable_mv": 6898}}, 200, "application/json"),
        (r".*/data/portfolio_ingestion/analysis_runs/PAR-20260817-40E00509/alignment\.csv$", "node_key,target_pct,actual_pct\nCOMMODITIES,2.0,1.1\nCOMMODITIES.GOLD,1.0,0.5\nCOMMODITIES.ENERGY,0.7,0.4\nCOMMODITIES.BROAD_BASKET,0.3,0.2\n", 200, "text/csv"),
        (r".*/data/portfolio_ingestion/analysis_runs/PAR-20260817-40E00509/run_metadata\.json$", {"run_id": "PAR-20260817-40E00509", "snapshot_date": "2026-08-17"}, 200, "application/json"),
    ]


@contextmanager
def _serve_outcome_page(route_specs: list[tuple[str, object, int, str]]):
    if not CHROME_EXECUTABLE.exists():
        pytest.skip("Google Chrome is not installed at the expected path for browser validation")

    port = _free_port()
    server = _ThreadingTCPServer(("127.0.0.1", port), partial(_Handler, directory=str(REPO_ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=str(CHROME_EXECUTABLE),
                args=["--disable-dev-shm-usage"],
            )
            context = browser.new_context()
            try:
                page = context.new_page()

                for pattern, payload, status, content_type in route_specs:
                    def _handler(route, request, _payload=payload, _status=status, _content_type=content_type):
                        body = _payload
                        if isinstance(_payload, (dict, list)):
                            body = json.dumps(_payload)
                        route.fulfill(status=_status, content_type=_content_type, body=body)

                    page.route(re.compile(pattern), _handler)

                page.goto(
                    f"http://127.0.0.1:{port}/ui/outcome_visualization/index.html?validation=outcome-runtime-readpath-fix",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function(
                    """
                    () => {
                      const readiness = document.getElementById('decisionReadinessSummary');
                      const holdings = document.getElementById('holdingsCoverageSummary');
                      const recBody = document.getElementById('recommendationFreshnessBody');
                      return readiness && !readiness.innerText.includes('Loading')
                        && holdings && !holdings.innerText.includes('Loading')
                        && recBody && !recBody.innerText.includes('Loading');
                    }
                    """,
                    timeout=20000,
                )
                page.wait_for_function(
                    """
                    () => {
                      const op = document.getElementById('portfolioActionPanel');
                      return op && !op.innerText.includes('Loading latest portfolio action plan...');
                    }
                    """,
                    timeout=20000,
                )
                yield page
            finally:
                context.close()
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_replay_series_404_does_not_trigger_page_wide_failure() -> None:
    with _serve_outcome_page(_base_routes(replay_series_status=404, refresh_running=False)) as page:
        status_text = page.locator("#statusBox").inner_text()
        replay_meta = page.locator("#replayMeta").inner_text()
        body = page.locator("body").inner_text()

        assert "replay_performance_series.csv is missing (HTTP 404)" in status_text
        assert "replay_panel_status" in replay_meta
        assert "UNAVAILABLE" in replay_meta
        assert "Failed to load UI data inputs" not in body
        assert "Classification:" in page.locator("#decisionReadinessSummary").inner_text()
        assert "Candidate readiness unavailable" not in page.locator("#candidateReadinessGrid").inner_text()
        assert "No recommendation freshness rows available" not in page.locator("#recommendationFreshnessBody").inner_text()
        assert "Loading latest portfolio action plan" not in page.locator("#portfolioActionPanel").inner_text()
        assert "with 0 points" not in status_text


def test_provider_cards_keep_canonical_coverage_when_refresh_not_running() -> None:
    with _serve_outcome_page(_base_routes(replay_series_status=404, refresh_running=False, refresh_completed_count=0)) as page:
        signal_text = page.locator("#signalStatusPills").inner_text()
        assert "Current holdings: 54/54 within threshold" in signal_text
        assert "Active refresh progress:" not in signal_text


def test_danelfin_uses_canonical_holdings_coverage_not_refresh_progress() -> None:
    with _serve_outcome_page(_base_routes(replay_series_status=404, refresh_running=False, refresh_completed_count=0)) as page:
        signal_text = page.locator("#signalStatusPills").inner_text()
        holdings_text = page.locator("#holdingsCoveragePills").inner_text()

        assert "Danelfin" in signal_text
        assert "Current holdings: 54/54 within threshold" in signal_text
        assert "stale 0" in signal_text
        assert "missing 0" in signal_text
        assert "failed 0" in signal_text
        assert "Active refresh progress:" not in signal_text

        assert "Applicable: 54" in holdings_text
        assert "Within threshold: 54" in holdings_text
        assert "Stale: 0" in holdings_text
        assert "Missing: 0" in holdings_text
        assert "Failed: 0" in holdings_text


def test_active_refresh_progress_displays_separately_from_canonical_coverage() -> None:
    with _serve_outcome_page(_base_routes(replay_series_status=404, refresh_running=True, refresh_completed_count=10)) as page:
        signal_text = page.locator("#signalStatusPills").inner_text()
        assert "Current holdings: 54/54 within threshold" in signal_text
        assert "Active refresh progress: 10/54 rows" in signal_text


def test_refresh_observability_shows_current_stage_queue_and_fmp_visibility() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=True)
    refresh_payload = {
        "running": True,
        "resolved_intent": "holdings_plus_buy_candidates",
        "scope_summary": {
            "portfolio_holdings_count": 67,
            "buy_candidate_count": 0,
            "mandatory_dependency_count": 0,
            "market_proxy_count": 9,
            "deduped_symbol_count": 76,
        },
        "scope_formula": "Planned refresh scope: 67 holdings + 0 buy candidates + 0 required dependencies + 9 market proxies = 76 symbols",
        "provider_progress": {
            "zacks": {
                "completed_count": 63,
                "planned_total_count": 63,
                "progress_pct": 100.0,
                "progress_label": "63/63",
                "is_complete": True,
            },
            "yahoo": {
                "completed_count": 43,
                "planned_total_count": 63,
                "progress_pct": 68.3,
                "progress_label": "43/63",
                "is_complete": False,
            },
            "danelfin": {
                "completed_count": 0,
                "planned_total_count": 63,
                "progress_pct": 0.0,
                "progress_label": "0/63",
                "is_complete": False,
            },
        },
        "provider_execution": {
            "zacks": {
                "provider": "zacks",
                "planned_count": 63,
                "attempted_count": 63,
                "success_count": 63,
                "failed_count": 0,
                "state": "COMPLETE",
            },
            "yahoo": {
                "provider": "yahoo",
                "planned_count": 63,
                "attempted_count": 43,
                "success_count": 43,
                "failed_count": 0,
                "state": "RUNNING",
            },
            "danelfin": {
                "provider": "danelfin",
                "planned_count": 63,
                "attempted_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "state": "QUEUED",
            },
            "fmp": {
                "provider": "fmp",
                "planned_count": None,
                "attempted_count": None,
                "success_count": None,
                "failed_count": None,
                "state": "QUEUED",
            },
        },
        "current_stage": "provider_refresh_yahoo",
        "current_stage_provider": "yahoo",
        "started_at_utc": "2026-08-18T15:35:55.000000+00:00",
        "completed_at_utc": None,
    }

    routes = [
        (r".*/api/signal-refresh/status$", refresh_payload, 200, "application/json")
        if pattern == r".*/api/signal-refresh/status$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]

    with _serve_outcome_page(routes) as page:
        runtime_summary = page.locator("#refreshActiveStateSummary").inner_text()
        runtime_details = page.locator("#refreshActiveStateDetails").inner_text()
        signal_text = page.locator("#signalStatusPills").inner_text()
        refresh_msg = page.locator("#signalRefreshMsg").inner_text()

        assert "Current stage: YAHOO (RUNNING)" in runtime_summary
        assert "ZACKSCOMPLETE 63/63" in runtime_details
        assert "YAHOORUNNING 43/63" in runtime_details
        assert "DANELFINQUEUED 0/63" in runtime_details
        assert "FMPQUEUED —/—" in runtime_details
        assert "success 63" in runtime_details
        assert "success 43" in runtime_details

        assert "Refresh state: COMPLETE" in signal_text
        assert "Refresh state: RUNNING" in signal_text
        assert "Refresh state: QUEUED" in signal_text
        assert "current stage: YAHOO" in refresh_msg
        assert "Execution: attempted 63 · success 63 · failed 0" in signal_text


def test_refresh_observability_marks_terminal_danelfin_and_fmp_running() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=True)
    refresh_payload = {
        "running": True,
        "resolved_intent": "holdings_plus_buy_candidates",
        "scope_summary": {
            "portfolio_holdings_count": 67,
            "buy_candidate_count": 0,
            "mandatory_dependency_count": 0,
            "market_proxy_count": 9,
            "deduped_symbol_count": 76,
        },
        "provider_progress": {
            "zacks": {
                "completed_count": 63,
                "planned_total_count": 63,
                "progress_pct": 100.0,
                "progress_label": "63/63",
                "is_complete": True,
            },
            "yahoo": {
                "completed_count": 63,
                "planned_total_count": 63,
                "progress_pct": 100.0,
                "progress_label": "63/63",
                "is_complete": True,
            },
            "danelfin": {
                "completed_count": 0,
                "planned_total_count": 63,
                "progress_pct": 0.0,
                "progress_label": "0/63",
                "is_complete": False,
            },
        },
        "provider_execution": {
            "zacks": {
                "provider": "zacks",
                "planned_count": 63,
                "attempted_count": 63,
                "success_count": 63,
                "failed_count": 0,
                "state": "COMPLETE",
            },
            "yahoo": {
                "provider": "yahoo",
                "planned_count": 63,
                "attempted_count": 63,
                "success_count": 63,
                "failed_count": 0,
                "state": "COMPLETE",
            },
            "danelfin": {
                "provider": "danelfin",
                "planned_count": 63,
                "attempted_count": 63,
                "success_count": 0,
                "failed_count": 63,
                "state": "COMPLETE_WITH_ERRORS",
            },
            "fmp": {
                "provider": "fmp",
                "planned_count": None,
                "attempted_count": None,
                "success_count": None,
                "failed_count": None,
                "state": "RUNNING",
            },
        },
        "current_stage": "provider_refresh_fmp",
        "current_stage_provider": "fmp",
        "started_at_utc": "2026-08-18T15:35:55.000000+00:00",
        "completed_at_utc": None,
    }

    routes = [
        (r".*/api/signal-refresh/status$", refresh_payload, 200, "application/json")
        if pattern == r".*/api/signal-refresh/status$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]

    with _serve_outcome_page(routes) as page:
        runtime_summary = page.locator("#refreshActiveStateSummary").inner_text()
        runtime_details = page.locator("#refreshActiveStateDetails").inner_text()
        signal_text = page.locator("#signalStatusPills").inner_text()

        assert "Current stage: FMP (RUNNING)" in runtime_summary
        assert "DANELFINCOMPLETE_WITH_ERRORS 63/63" in runtime_details
        assert "FMPRUNNING —/—" in runtime_details
        assert "Active refresh progress: 0/63 rows" in signal_text
        assert "Refresh state: COMPLETE_WITH_ERRORS" in signal_text
        assert "Execution: attempted 63 · success 0 · failed 63" in signal_text


def test_refresh_observability_no_active_refresh_state() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=False)
    refresh_payload = {
        "running": False,
        "resolved_intent": "holdings_plus_buy_candidates",
        "scope_summary": {
            "portfolio_holdings_count": 67,
            "buy_candidate_count": 0,
            "mandatory_dependency_count": 0,
            "market_proxy_count": 9,
            "deduped_symbol_count": 76,
        },
        "provider_progress": {
            "zacks": {
                "completed_count": 63,
                "planned_total_count": 63,
                "progress_pct": 100.0,
                "progress_label": "63/63",
                "is_complete": True,
            },
            "yahoo": {
                "completed_count": 63,
                "planned_total_count": 63,
                "progress_pct": 100.0,
                "progress_label": "63/63",
                "is_complete": True,
            },
            "danelfin": {
                "completed_count": 63,
                "planned_total_count": 63,
                "progress_pct": 100.0,
                "progress_label": "63/63",
                "is_complete": True,
            },
        },
        "started_at_utc": "2026-08-18T15:35:55.000000+00:00",
        "completed_at_utc": "2026-08-18T16:35:55.000000+00:00",
    }

    routes = [
        (r".*/api/signal-refresh/status$", refresh_payload, 200, "application/json")
        if pattern == r".*/api/signal-refresh/status$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]

    with _serve_outcome_page(routes) as page:
        runtime_summary = page.locator("#refreshActiveStateSummary").inner_text()
        assert runtime_summary == "No active refresh job."


def test_recommendation_freshness_ess_labels_distinguish_no_score_and_missing() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=False)
    updated_payload = _base_refresh_transparency_payload()
    updated_payload["rows"] = [
        {
            "symbol": "SIMO",
            "zacks": {"state": "fresh", "date": "2026-08-18"},
            "danelfin": {"state": "fresh", "date": "2026-08-18"},
            "yahoo": {"state": "fresh", "date": "2026-08-18"},
            "ess": {"state": "no_starmine_score", "date": "2026-08-18"},
            "fmp": {"state": "missing", "date": "NA"},
            "freshness": "FRESH",
        },
        {
            "symbol": "MISSING1",
            "zacks": {"state": "fresh", "date": "2026-08-18"},
            "danelfin": {"state": "fresh", "date": "2026-08-18"},
            "yahoo": {"state": "fresh", "date": "2026-08-18"},
            "ess": {"state": "missing", "date": "2026-08-18"},
            "fmp": {"state": "missing", "date": "NA"},
            "freshness": "FRESH",
        },
    ]

    routes = [
        (r".*/api/refresh-transparency$", updated_payload, 200, "application/json")
        if pattern == r".*/api/refresh-transparency$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]

    with _serve_outcome_page(routes) as page:
        body_text = page.locator("#recommendationFreshnessBody").inner_text()
        assert "SIMO" in body_text
        assert "NO STARMINE ESS SCORE (2026-08-18)" in body_text
        assert "MISSING1" in body_text
        assert "HOLDING ABSENT (2026-08-18)" in body_text


def test_ess_summary_wording_uses_coverage_gap_language() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=False)
    signal_payload = _base_signal_status_payload()
    signal_payload["ess"]["coverage_warning_count"] = 2
    signal_payload["ess"]["coverage_warning_examples"] = ["SIMO", "MISSING1"]

    routes = [
        (r".*/api/signal-status$", signal_payload, 200, "application/json")
        if pattern == r".*/api/signal-status$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]

    with _serve_outcome_page(routes) as page:
        signal_text = page.locator("#signalStatusPills").inner_text()
        assert "ESS coverage warning: 2 holdings with ESS coverage gaps" in signal_text
        assert "holdings absent" not in signal_text


def test_holdings_summary_label_is_explicit_about_equity_scope() -> None:
    with _serve_outcome_page(_base_routes(replay_series_status=404, refresh_running=False)) as page:
        summary = page.locator("#holdingsCoverageSummary").inner_text()
        assert "Active equity holdings: 67" in summary
        assert "Provider-applicable holdings: 54" in summary


def test_operator_panel_renders_success_payload_on_initialization() -> None:
    with _serve_outcome_page(_base_routes(replay_series_status=404, refresh_running=False)) as page:
        panel = page.locator("#portfolioActionPanel").inner_text()
        assert "Loading latest portfolio action plan" not in panel
        assert "WHAT MATTERS RIGHT NOW" in panel


def test_operator_panel_renders_explicit_empty_state_when_no_runs_exist() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=False)
    routes = [
        (r".*/api/portfolio/runs$", {"portfolios": []}, 200, "application/json")
        if pattern == r".*/api/portfolio/runs$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]
    with _serve_outcome_page(routes) as page:
        panel = page.locator("#portfolioActionPanel").inner_text()
        assert "Loading latest portfolio action plan" not in panel
        assert "No completed portfolio analysis runs available." in panel


def test_operator_panel_renders_explicit_unavailable_state_when_artifacts_incomplete() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=False)
    routes = [
        (
            r".*/data/portfolio_ingestion/analysis_runs/PAR-20260817-40E00509/alignment\.csv$",
            "node_key,target_pct,actual_pct\n",
            200,
            "text/csv",
        )
        if pattern == r".*/data/portfolio_ingestion/analysis_runs/PAR-20260817-40E00509/alignment\.csv$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]
    with _serve_outcome_page(routes) as page:
        panel = page.locator("#portfolioActionPanel").inner_text()
        assert "Loading latest portfolio action plan" not in panel
        assert "Operator action plan unavailable" in panel
        assert "persisted operator artifacts are incomplete" in panel


def test_operator_panel_renders_explicit_error_state_when_runs_endpoint_fails() -> None:
    routes = _base_routes(replay_series_status=404, refresh_running=False)
    routes = [
        (r".*/api/portfolio/runs$", {"error": "unavailable"}, 503, "application/json")
        if pattern == r".*/api/portfolio/runs$"
        else (pattern, payload, status, content_type)
        for pattern, payload, status, content_type in routes
    ]
    with _serve_outcome_page(routes) as page:
        panel = page.locator("#portfolioActionPanel").inner_text()
        assert "Loading latest portfolio action plan" not in panel
        assert "Operator action plan unavailable" in panel
        assert "HTTP 503" in panel
