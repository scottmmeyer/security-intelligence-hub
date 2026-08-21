from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_JS = REPO_ROOT / "ui" / "portfolio_alignment" / "app.js"
INDEX_HTML = REPO_ROOT / "ui" / "portfolio_alignment" / "index.html"
RUN_ROOT = REPO_ROOT / "data" / "portfolio_ingestion" / "analysis_runs" / "PAR-20260820-2DF39E29"


@contextmanager
def browser_page():
    playwright = sync_playwright().start()
    browser = None
    try:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://127.0.0.1:8765/ui/portfolio_alignment/", wait_until="networkidle")
        yield page
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser/runtime unavailable: {exc}")
    finally:
        if browser is not None:
            browser.close()
        playwright.stop()


@pytest.mark.parametrize(
    "payload",
    [
        {
            "analysis_preflight": {"status": "DEGRADED", "reason_codes": ["PF-GEO-001", "PF-FMP-001"]},
            "deployment_queue": {
                "candidate_count": 0,
                "queue": [],
                "suppressed_by_preflight": False,
                "preflight_reason_codes": ["PF-GEO-001", "PF-FMP-001"],
            },
            "deployment_plan": {
                "recommendations": [],
                "suppressed_by_preflight": False,
                "preflight_reason_codes": ["PF-GEO-001", "PF-FMP-001"],
            },
        }
    ],
)
def test_empty_state_keeps_top_trades_panel_visible(payload):
    with browser_page() as page:
        page.evaluate(
            """
            (data) => renderDeploymentQueue(data)
            """,
            payload,
        )

        container = page.locator("#deploymentQueueContainer")
        assert container.is_visible()
        assert container.locator(".dq-empty-state").count() == 1
        assert container.locator(".dq-table tbody tr").count() == 0

        text = container.inner_text()
        assert "Top Trades to Consider" in text
        assert "No canonical deployment candidates today." in text
        assert "Queue candidates" in text and "0" in text
        assert "Queue rows" in text and "0" in text
        assert "Planned recommendations" in text and "0" in text
        assert "Preflight" in text and "DEGRADED" in text
        assert "PF-GEO-001" in text
        assert "PF-FMP-001" in text
        assert "Portfolio Action Pipeline contains broader HOLD / WATCH / TRIM / allocation guidance and is separate from the ranked deployment queue." in text
        assert container.locator('a[href="#portfolioActionPipelineSection"]').count() == 1


def test_non_empty_queue_preserves_order_and_shows_blocked_rows():
    payload = {
        "analysis_preflight": {"status": "PASS", "reason_codes": []},
        "deployment_queue": {
            "candidate_count": 2,
            "queue": [
                {
                    "rank": 1,
                    "symbol": "AAA",
                    "deployment_score": 91.2,
                    "current_weight_pct": 1.0,
                    "narrative_tier": "CORE_CONVICTION_LEADER",
                    "replay_supported": True,
                    "trim_score": 10.0,
                    "score_breakdown": {"redundancy_pen": 0, "conc_pen": 0},
                    "notes": "stable",
                },
                {
                    "rank": 2,
                    "symbol": "BBB",
                    "deployment_score": 80.0,
                    "current_weight_pct": 7.0,
                    "narrative_tier": "HIGH_CONVICTION_ANCHOR",
                    "replay_supported": True,
                    "trim_score": 15.0,
                    "score_breakdown": {"redundancy_pen": 15, "conc_pen": 1},
                    "notes": "blocked",
                },
            ],
            "cash_context": {
                "cash_pct": 8.0,
                "mandate_cash_target_pct": 7.0,
                "excess_pct": 1.0,
                "excess_mv": 1000,
                "deployable_mv": 1000,
            },
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
        "deployment_plan": {
            "recommendations": [
                {
                    "rank": 1,
                    "symbol": "AAA",
                    "deployment_tier": "TIER_1",
                    "suggested_add": 5000,
                    "current_weight_pct": 1.0,
                    "projected_weight_pct": 2.0,
                    "current_market_value": 10000,
                    "projected_market_value": 15000,
                    "headroom_to_warn": 7000,
                    "constraint_status": "DEPLOYABLE",
                },
                {
                    "rank": 2,
                    "symbol": "BBB",
                    "deployment_tier": "TIER_2",
                    "suggested_add": 2500,
                    "current_weight_pct": 7.0,
                    "projected_weight_pct": 7.5,
                    "current_market_value": 12000,
                    "projected_market_value": 14500,
                    "headroom_to_warn": 0,
                    "constraint_status": "BLOCKED",
                },
            ],
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
    }

    with browser_page() as page:
        page.evaluate("""(data) => renderDeploymentQueue(data)""", payload)

        container = page.locator("#deploymentQueueContainer")
        rows = container.locator("#dq-queue-table-body tr.dq-data-row")
        assert rows.count() == 2
        assert "AAA" in rows.nth(0).inner_text()
        assert "BBB" in rows.nth(1).inner_text()
        assert "BLOCKED" in rows.nth(1).inner_text()
        assert container.locator(".dq-empty-state").count() == 0


def test_current_run_remains_canonical_queue_empty_and_pap_separate():
    run_metadata = json.loads((RUN_ROOT / "run_metadata.json").read_text(encoding="utf-8"))
    deployment_queue = json.loads((RUN_ROOT / "deployment_queue.json").read_text(encoding="utf-8"))
    deployment_plan = json.loads((RUN_ROOT / "deployment_plan.json").read_text(encoding="utf-8"))

    assert run_metadata["recommendation_count"] == 26
    assert deployment_queue["candidate_count"] == 0
    assert deployment_queue["queue"] == []
    assert deployment_plan["recommendations"] == []
    assert deployment_queue["suppressed_by_preflight"] is False
    assert deployment_plan["suppressed_by_preflight"] is False
    assert APP_JS.read_text(encoding="utf-8").count("Portfolio Action Pipeline contains broader HOLD / WATCH / TRIM / allocation guidance and is separate from the ranked deployment queue.") == 1
    assert "portfolioActionPipelineSection" in INDEX_HTML.read_text(encoding="utf-8")


def _momentum_payload(snapshot_date: str = "2026-08-20") -> dict:
    return {
        "run_id": "PAR-TEST-0001",
        "snapshot_date": snapshot_date,
        "analysis_preflight": {"status": "PASS", "reason_codes": []},
        "deployment_queue": {
            "candidate_count": 2,
            "queue": [
                {
                    "rank": 1,
                    "symbol": "AAA",
                    "deployment_score": 91.2,
                    "current_weight_pct": 1.0,
                    "narrative_tier": "CORE_CONVICTION_LEADER",
                    "replay_supported": True,
                    "trim_score": 10.0,
                    "composite_score": 4.1,
                    "score_breakdown": {"redundancy_pen": 0, "conc_pen": 0},
                    "notes": "stable",
                },
                {
                    "rank": 2,
                    "symbol": "BBB",
                    "deployment_score": 80.0,
                    "current_weight_pct": 2.0,
                    "narrative_tier": "HIGH_CONVICTION_ANCHOR",
                    "replay_supported": True,
                    "trim_score": 15.0,
                    "composite_score": 3.7,
                    "score_breakdown": {"redundancy_pen": 0, "conc_pen": 0},
                    "notes": "stable",
                },
            ],
            "cash_context": {
                "cash_pct": 8.0,
                "mandate_cash_target_pct": 7.0,
                "excess_pct": 1.0,
                "excess_mv": 1000,
                "deployable_mv": 1000,
            },
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
        "deployment_plan": {
            "recommendations": [
                {
                    "rank": 1,
                    "symbol": "AAA",
                    "deployment_tier": "TIER_1",
                    "suggested_add": 5000,
                    "current_weight_pct": 1.0,
                    "projected_weight_pct": 2.0,
                    "current_market_value": 10000,
                    "projected_market_value": 15000,
                    "headroom_to_warn": 7000,
                    "constraint_status": "DEPLOYABLE",
                },
                {
                    "rank": 2,
                    "symbol": "BBB",
                    "deployment_tier": "TIER_2",
                    "suggested_add": 2500,
                    "current_weight_pct": 2.0,
                    "projected_weight_pct": 2.5,
                    "current_market_value": 12000,
                    "projected_market_value": 14500,
                    "headroom_to_warn": 0,
                    "constraint_status": "DEPLOYABLE",
                },
            ],
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
    }


def _momentum_summary(
    snapshot_date: str = "2026-08-20",
    include_bbb: bool = True,
    aaa_change: str = "FADING",
    bbb_change: str = "ACCELERATING",
) -> dict:
    holdings = [
        {
            "symbol": "AAA",
            "relative_momentum_change": aaa_change,
            "absolute_security_momentum": {
                "state": "STRONG",
                "horizons": {"1M": {"confidence": "HIGH", "as_of_date": snapshot_date}},
            },
            "confirmation_state": "CONFIRMED_MOMENTUM",
            "extension_state": "NORMAL",
            "history_label": "RECONSTRUCTED_DERIVED",
            "evaluation_status": "FULLY_EVALUATED",
        }
    ]
    if include_bbb:
        holdings.append(
            {
                "symbol": "BBB",
                "relative_momentum_change": bbb_change,
                "absolute_security_momentum": {
                    "state": "WEAK",
                    "horizons": {"1M": {"confidence": "HIGH", "as_of_date": snapshot_date}},
                },
                "confirmation_state": "MOMENTUM_DIVERGENCE",
                "extension_state": "EXTENDED",
                "history_label": "RECONSTRUCTED_DERIVED",
                "evaluation_status": "FULLY_EVALUATED",
            }
        )
    return {
        "status": "ok",
        "reporting_only": True,
        "snapshot_date": snapshot_date,
        "generated_at_utc": "2026-08-20T23:13:29.367822+00:00",
        "portfolio_momentum_map": {"holdings": holdings},
    }


def test_momentum_loading_then_ready_renders_level_and_change():
    payload = _momentum_payload("2026-08-20")
    summary = _momentum_summary("2026-08-20", include_bbb=True, aaa_change="FADING", bbb_change="ACCELERATING")

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return new Promise((resolve) => {
                    setTimeout(() => {
                      resolve({ ok: true, json: () => Promise.resolve(summary) });
                    }, 60);
                  });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        pending_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert pending_cells.nth(0).inner_text().strip() == "…"
        assert pending_cells.nth(1).inner_text().strip() == "…"

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'STRONG · FADING'
            """
        )

        rows = page.locator("#dq-queue-table-body tr.dq-data-row")
        assert rows.count() == 2
        assert "AAA" in rows.nth(0).inner_text()
        assert "BBB" in rows.nth(1).inner_text()

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "STRONG · FADING"
        assert momentum_cells.nth(1).inner_text().strip() == "WEAK · ACCELERATING"

        header = page.locator(".dq-table thead tr th").nth(6).inner_text()
        assert "Momentum" in header
        assert "State / Change" in header


def test_partial_momentum_fields_render_level_with_dash_and_raw_unavailable_tooltip():
    payload = {
        "run_id": "PAR-TEST-PARTIAL",
        "snapshot_date": "2026-08-20",
        "analysis_preflight": {"status": "PASS", "reason_codes": []},
        "deployment_queue": {
            "candidate_count": 2,
            "queue": [
                {
                    "rank": 1,
                    "symbol": "DELL",
                    "deployment_score": 91.2,
                    "current_weight_pct": 1.0,
                    "narrative_tier": "CORE_CONVICTION_LEADER",
                    "replay_supported": True,
                    "trim_score": 10.0,
                    "composite_score": 4.1,
                    "score_breakdown": {"redundancy_pen": 0, "conc_pen": 0},
                    "notes": "stable",
                },
                {
                    "rank": 2,
                    "symbol": "SBS",
                    "deployment_score": 80.0,
                    "current_weight_pct": 2.0,
                    "narrative_tier": "HIGH_CONVICTION_ANCHOR",
                    "replay_supported": True,
                    "trim_score": 15.0,
                    "composite_score": 3.7,
                    "score_breakdown": {"redundancy_pen": 0, "conc_pen": 0},
                    "notes": "stable",
                },
            ],
            "cash_context": {
                "cash_pct": 8.0,
                "mandate_cash_target_pct": 7.0,
                "excess_pct": 1.0,
                "excess_mv": 1000,
                "deployable_mv": 1000,
            },
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
        "deployment_plan": {
            "recommendations": [
                {
                    "rank": 1,
                    "symbol": "DELL",
                    "deployment_tier": "TIER_1",
                    "suggested_add": 5000,
                    "current_weight_pct": 1.0,
                    "projected_weight_pct": 2.0,
                    "current_market_value": 10000,
                    "projected_market_value": 15000,
                    "headroom_to_warn": 7000,
                    "constraint_status": "DEPLOYABLE",
                },
                {
                    "rank": 2,
                    "symbol": "SBS",
                    "deployment_tier": "TIER_2",
                    "suggested_add": 2500,
                    "current_weight_pct": 2.0,
                    "projected_weight_pct": 2.5,
                    "current_market_value": 12000,
                    "projected_market_value": 14500,
                    "headroom_to_warn": 0,
                    "constraint_status": "DEPLOYABLE",
                },
            ],
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
    }
    summary = {
        "status": "ok",
        "reporting_only": True,
        "snapshot_date": "2026-08-20",
        "generated_at_utc": "2026-08-20T23:13:29.367822+00:00",
        "portfolio_momentum_map": {
            "holdings": [
                {
                    "symbol": "DELL",
                    "relative_momentum_change": "UNAVAILABLE",
                    "absolute_security_momentum": {
                        "state": "STRONG",
                        "horizons": {"1M": {"confidence": "HIGH", "as_of_date": "2026-08-20"}},
                    },
                    "confirmation_state": "CONFIRMED_MOMENTUM",
                    "extension_state": "ELEVATED",
                    "history_label": "RECONSTRUCTED_DERIVED",
                    "evaluation_status": "FULLY_EVALUATED",
                },
                {
                    "symbol": "SBS",
                    "relative_momentum_change": "UNAVAILABLE",
                    "absolute_security_momentum": {
                        "state": "WEAK",
                        "horizons": {"1M": {"confidence": "HIGH", "as_of_date": "2026-08-20"}},
                    },
                    "confirmation_state": "UNAVAILABLE",
                    "extension_state": "NORMAL",
                    "history_label": "RECONSTRUCTED_DERIVED",
                    "evaluation_status": "FULLY_EVALUATED",
                },
            ]
        },
    }

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'STRONG · —'
            """
        )

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "STRONG · —"
        assert momentum_cells.nth(1).inner_text().strip() == "WEAK · —"

        dell_tooltip = momentum_cells.nth(0).get_attribute("title") or ""
        sbs_tooltip = momentum_cells.nth(1).get_attribute("title") or ""
        assert "Momentum Change: UNAVAILABLE" in dell_tooltip
        assert "Momentum Change: UNAVAILABLE" in sbs_tooltip


def test_mu_can_show_strong_level_and_fading_change_with_extension_in_tooltip():
    payload = {
        "run_id": "PAR-TEST-MU",
        "snapshot_date": "2026-08-20",
        "analysis_preflight": {"status": "PASS", "reason_codes": []},
        "deployment_queue": {
            "candidate_count": 1,
            "queue": [
                {
                    "rank": 1,
                    "symbol": "MU",
                    "deployment_score": 70.0,
                    "current_weight_pct": 1.0,
                    "narrative_tier": "HIGH_CONVICTION_ANCHOR",
                    "replay_supported": True,
                    "trim_score": 10.0,
                    "composite_score": 3.6,
                    "score_breakdown": {"redundancy_pen": 0, "conc_pen": 0},
                    "notes": "stable",
                }
            ],
            "cash_context": {
                "cash_pct": 8.0,
                "mandate_cash_target_pct": 7.0,
                "excess_pct": 1.0,
                "excess_mv": 1000,
                "deployable_mv": 1000,
            },
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
        "deployment_plan": {
            "recommendations": [
                {
                    "rank": 1,
                    "symbol": "MU",
                    "deployment_tier": "TIER_2",
                    "suggested_add": 1000,
                    "current_weight_pct": 1.0,
                    "projected_weight_pct": 1.5,
                    "current_market_value": 10000,
                    "projected_market_value": 11000,
                    "headroom_to_warn": 7000,
                    "constraint_status": "DEPLOYABLE",
                }
            ],
            "suppressed_by_preflight": False,
            "preflight_reason_codes": [],
        },
    }
    summary = {
        "status": "ok",
        "reporting_only": True,
        "snapshot_date": "2026-08-20",
        "generated_at_utc": "2026-08-20T23:13:29.367822+00:00",
        "portfolio_momentum_map": {
            "holdings": [
                {
                    "symbol": "MU",
                    "relative_momentum_change": "FADING",
                    "absolute_security_momentum": {
                        "state": "STRONG",
                        "horizons": {"1M": {"confidence": "HIGH", "as_of_date": "2026-08-20"}},
                    },
                    "confirmation_state": "MOMENTUM_DIVERGENCE",
                    "extension_state": "EXTENDED",
                    "history_label": "RECONSTRUCTED_DERIVED",
                    "evaluation_status": "FULLY_EVALUATED",
                }
            ]
        },
    }

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'STRONG · FADING'
            """
        )

        cell = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span").nth(0)
        assert cell.inner_text().strip() == "STRONG · FADING"
        tooltip = cell.get_attribute("title") or ""
        assert "Momentum State: STRONG" in tooltip
        assert "Momentum Change: FADING" in tooltip
        assert "Extension: EXTENDED" in tooltip
        assert "Confirmation: MOMENTUM_DIVERGENCE" in tooltip


def test_static_buy_timing_guide_exists_and_is_non_executable_guidance():
    payload = _momentum_payload("2026-08-20")
    summary = _momentum_summary("2026-08-20", include_bbb=True)

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        page.wait_for_function(
            """
            () => document.querySelector('#deploymentQueueContainer details summary')?.textContent?.includes('How to Read Momentum')
            """
        )

        text = page.locator("#deploymentQueueContainer").inner_text()
        assert "How to Read Momentum (Buy-Timing Context)" in text
        assert "State / Change field contract:" in text
        assert "Momentum should influence timing/aggressiveness, not underlying conviction." in text
        assert "STRONG + IMPROVING" in text
        assert "WEAK + FADING/WEAKENING" in text
        assert "EXTENDED" in text

        app_text = APP_JS.read_text(encoding="utf-8")
        forbidden = ["BUY_NOW", "TIMING_SCORE", "MOMENTUM_BUY_SCORE", "BUY\n", "WAIT", "AVOID", "CHASE"]
        for token in forbidden:
            assert token not in app_text


def test_same_run_rerender_retains_loaded_momentum_map():
    payload = _momentum_payload("2026-08-20")
    summary = _momentum_summary("2026-08-20", include_bbb=True)

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.__momFetchCalls = 0;
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  window.__momFetchCalls += 1;
                  return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'STRONG · FADING'
            """
        )

        page.evaluate("(payload) => renderDeploymentQueue(payload)", payload)

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "STRONG · FADING"
        assert momentum_cells.nth(1).inner_text().strip() == "WEAK · ACCELERATING"
        assert page.evaluate("() => window.__momFetchCalls") == 1


def test_missing_momentum_symbol_renders_unavailable():
    payload = _momentum_payload("2026-08-20")
    summary = _momentum_summary("2026-08-20", include_bbb=False)

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        page.wait_for_function(
            """
            () => document.querySelectorAll('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span').length === 2
            """
        )

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "STRONG · FADING"
        assert momentum_cells.nth(1).inner_text().strip() == "UNAVAILABLE"


def test_momentum_provenance_mismatch_displays_unavailable_with_guard():
    payload = _momentum_payload("2026-08-19")
    summary = _momentum_summary("2026-08-20", include_bbb=True)

    with browser_page() as page:
        page.evaluate(
            """
            ({ payload, summary }) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            {"payload": payload, "summary": summary},
        )

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'UNAVAILABLE'
            """
        )

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "UNAVAILABLE"
        assert momentum_cells.nth(1).inner_text().strip() == "UNAVAILABLE"
        assert "provenance mismatch" in (momentum_cells.nth(0).get_attribute("title") or "").lower()


def test_momentum_fetch_failure_resolves_loading_to_unavailable_and_keeps_order():
    payload = _momentum_payload("2026-08-20")

    with browser_page() as page:
        page.evaluate(
            """
            (payload) => {
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  return new Promise((_, reject) => {
                    setTimeout(() => reject(new Error('momentum endpoint unavailable')), 50);
                  });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payload);
            }
            """,
            payload,
        )

        pending_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert pending_cells.nth(0).inner_text().strip() == "…"
        assert pending_cells.nth(1).inner_text().strip() == "…"

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'UNAVAILABLE'
            """
        )

        rows = page.locator("#dq-queue-table-body tr.dq-data-row")
        assert rows.count() == 2
        assert "AAA" in rows.nth(0).inner_text()
        assert "BBB" in rows.nth(1).inner_text()

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "UNAVAILABLE"
        assert momentum_cells.nth(1).inner_text().strip() == "UNAVAILABLE"


def test_context_change_clears_prior_map_shows_loading_then_unavailable():
    payload_compatible = _momentum_payload("2026-08-20")
    payload_historical = _momentum_payload("2026-08-19")
    summary = _momentum_summary("2026-08-20", include_bbb=True)

    with browser_page() as page:
        page.evaluate(
            """
            ({ payloadCompatible, payloadHistorical, summary }) => {
              window.__momFetchCalls = 0;
              window.fetch = (url) => {
                if (String(url).includes('/api/pis/momentum/summary')) {
                  window.__momFetchCalls += 1;
                  if (window.__momFetchCalls === 1) {
                    return Promise.resolve({ ok: true, json: () => Promise.resolve(summary) });
                  }
                  return new Promise((resolve) => {
                    setTimeout(() => {
                      resolve({ ok: true, json: () => Promise.resolve(summary) });
                    }, 60);
                  });
                }
                return Promise.reject(new Error(`unexpected url: ${url}`));
              };
              renderDeploymentQueue(payloadCompatible);
              setTimeout(() => renderDeploymentQueue(payloadHistorical), 20);
            }
            """,
            {
                "payloadCompatible": payload_compatible,
                "payloadHistorical": payload_historical,
                "summary": summary,
            },
        )

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'STRONG · FADING'
            """
        )

        page.wait_for_function(
            """
            () => {
              const first = document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span');
              return !!first && first.textContent.trim() === '…';
            }
            """
        )

        page.wait_for_function(
            """
            () => document.querySelector('#dq-queue-table-body tr.dq-data-row td:nth-child(7) span')?.textContent?.trim() === 'UNAVAILABLE'
            """
        )

        momentum_cells = page.locator("#dq-queue-table-body tr.dq-data-row td:nth-child(7) span")
        assert momentum_cells.nth(0).inner_text().strip() == "UNAVAILABLE"
        assert momentum_cells.nth(1).inner_text().strip() == "UNAVAILABLE"
        assert page.evaluate("() => window.__momFetchCalls") == 2
