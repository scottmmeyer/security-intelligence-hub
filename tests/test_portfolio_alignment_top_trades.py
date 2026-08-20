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
