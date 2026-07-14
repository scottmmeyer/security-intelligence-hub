from __future__ import annotations

from scripts import refresh_signals as refresh


def test_refresh_with_market_proxies_invokes_replay_publish(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 7},
            "planned_symbol_samples": {"market_proxies": ["SPY", "QQQ", "XLK", "XLF", "XLI", "XLV", "SOXX"]},
            "buy_candidate_cap": 50,
        },
    )
    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (True, {"provider": "zacks"}))

    seen: dict[str, object] = {}

    def _publish(*, verbose: bool) -> dict[str, object]:
        seen["verbose"] = verbose
        return {
            "attempted": True,
            "status": "completed",
            "artifacts": ["replay_inputs.csv", "replay_performance_series.csv"],
            "latest_proxy_date": "2026-07-14",
            "warnings": [],
        }

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_artifacts", _publish)

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
    )

    assert seen == {"verbose": False}
    assert report["market_proxy_replay_publish"]["attempted"] is True
    assert report["market_proxy_replay_publish"]["status"] == "completed"
    assert report["market_proxy_replay_publish"]["latest_proxy_date"] == "2026-07-14"


def test_refresh_without_market_proxies_does_not_invoke_replay_publish(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 0},
            "planned_symbol_samples": {},
            "buy_candidate_cap": 50,
        },
    )
    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (True, {"provider": "zacks"}))

    called = {"value": False}

    def _publish(*, verbose: bool) -> dict[str, object]:
        called["value"] = True
        return {}

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_artifacts", _publish)

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
    )

    assert called["value"] is False
    assert report["market_proxy_replay_publish"]["attempted"] is False
    assert report["market_proxy_replay_publish"]["status"] == "skipped"


def test_replay_publish_status_is_reported(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 7},
            "planned_symbol_samples": {},
            "buy_candidate_cap": 50,
        },
    )
    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (False, {"provider": "zacks"}))
    monkeypatch.setattr(
        refresh,
        "_publish_market_proxy_replay_artifacts",
        lambda *, verbose: {
            "attempted": True,
            "status": "completed",
            "artifacts": ["replay_inputs.csv", "replay_performance_series.csv"],
            "latest_proxy_date": "2026-07-14",
            "warnings": [],
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
    )

    publish = report["market_proxy_replay_publish"]
    assert publish["artifacts"] == ["replay_inputs.csv", "replay_performance_series.csv"]
    assert publish["latest_proxy_date"] == "2026-07-14"


def test_replay_publish_failure_reports_warning_without_changing_scores(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 7},
            "planned_symbol_samples": {},
            "buy_candidate_cap": 50,
        },
    )
    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (True, {"provider": "zacks", "state": "RESEARCH_FRESH_COMPLIANT"}))
    monkeypatch.setattr(
        refresh,
        "_publish_market_proxy_replay_artifacts",
        lambda *, verbose: {
            "attempted": True,
            "status": "warning",
            "artifacts": ["replay_inputs.csv", "replay_performance_series.csv"],
            "latest_proxy_date": None,
            "warnings": [
                "Market proxy provider refresh completed, but replay/rotation artifacts were not regenerated; Market Regime Guardrail may remain stale."
            ],
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
    )

    assert report["providers"]["zacks"]["state"] == "RESEARCH_FRESH_COMPLIANT"
    assert report["market_proxy_replay_publish"]["status"] == "warning"
    assert report["market_proxy_replay_publish"]["warnings"]


def test_market_regime_proxy_freshness_uses_regenerated_replay_artifact(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260714-TEST", "snapshot_date": "2026-07-14"},
    )

    calls: list[tuple[str, str, str, str]] = []

    def _builder(**kwargs):
        calls.append(
            (
                kwargs["filter_industry"],
                kwargs["run_id"],
                kwargs["snapshot_date"],
                kwargs["end_date"],
            )
        )
        return {"matrix_row_count": 10, "availability_row_count": 10}

    monkeypatch.setattr("src.replay.foundation_service.build_wp05b_replay_matrix", _builder)
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {"proxy_returns": {"latest_proxy_date": "2026-07-14"}},
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert [item[0] for item in calls] == list(refresh._MARKET_PROXY_REPLAY_INDUSTRIES)
    assert all(item[1] == "PAR-20260714-TEST" for item in calls)
    assert all(item[2] == "2026-07-14" for item in calls)
    assert all(item[3] == "2026-07-14" for item in calls)
    assert status["status"] == "completed"
    assert status["latest_proxy_date"] == "2026-07-14"