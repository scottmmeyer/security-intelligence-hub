from __future__ import annotations

import csv
import hashlib
import tempfile
from pathlib import Path

import pytest

from scripts import refresh_signals as refresh


_REAL_REPO_ROOT = Path("/Users/scottmmeyer/Projects/security-intelligence-hub").resolve()
_REAL_CURRENT_ROOT = (_REAL_REPO_ROOT / "data" / "current").resolve()
_DEDICATED_FILES = (
    "market_regime_proxy_summary.json",
    "market_regime_proxy_inputs.csv",
    "market_regime_proxy_price_history.csv",
)
_REPLAY_FILES = ("replay_inputs.csv", "replay_performance_series.csv")


def _guard_not_real_current_root(path: Path) -> None:
    resolved = path.resolve()
    if resolved == _REAL_CURRENT_ROOT:
        raise RuntimeError(f"Bridge test attempted to use live current root: {resolved}")
    if _REAL_CURRENT_ROOT in resolved.parents:
        raise RuntimeError(f"Bridge test attempted to write inside live current root: {resolved}")


def _optional_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return _sha256(path)


def _real_current_hashes(root: Path) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in (*_REPLAY_FILES, *_DEDICATED_FILES):
        out[name] = _optional_sha256(root / name)
    return out


@pytest.fixture(scope="module", autouse=True)
def _protect_real_current_artifacts():
    before = _real_current_hashes(_REAL_CURRENT_ROOT)
    yield
    after = _real_current_hashes(_REAL_CURRENT_ROOT)
    assert after == before, (
        "Bridge test isolation violation: live data/current artifacts changed. "
        f"before={before} after={after}"
    )


@pytest.fixture(autouse=True)
def _isolate_bridge_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = (tmp_path / "isolated_repo").resolve()
    data_root = repo_root / "data"
    current_root = data_root / "current"
    history_root = data_root / "history"
    signals_root = data_root / "signals"
    par_root = data_root / "portfolio_ingestion" / "analysis_runs"
    registry_path = history_root / "replay_snapshot_registry.csv"
    report_path = current_root / "last_signal_refresh_report.json"
    stage_dir = (tmp_path / "isolated_tmp").resolve()

    current_root.mkdir(parents=True, exist_ok=True)
    history_root.mkdir(parents=True, exist_ok=True)
    (signals_root / "zacks").mkdir(parents=True, exist_ok=True)
    (signals_root / "danelfin").mkdir(parents=True, exist_ok=True)
    (signals_root / "yahoo").mkdir(parents=True, exist_ok=True)
    (signals_root / "fmp").mkdir(parents=True, exist_ok=True)
    par_root.mkdir(parents=True, exist_ok=True)
    stage_dir.mkdir(parents=True, exist_ok=True)

    _guard_not_real_current_root(current_root)

    # Seed required baseline files for code paths that may read these locations.
    (data_root / "current" / "base_equity_universe.csv").write_text("symbol\nSPY\n", encoding="utf-8")
    registry_path.write_text(
        "replay_id,snapshot_date,start_date,end_date,geography,market_cap_bucket,industry,benchmark_available,"
        "vehicle_available,stock_replay_available,top_n_available,replay_status,replay_mode,generated_at_utc\n",
        encoding="utf-8",
    )
    report_path.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(refresh, "_REPO_ROOT", repo_root)
    monkeypatch.setattr(refresh, "_ZACKS_DIR", signals_root / "zacks")
    monkeypatch.setattr(refresh, "_DANELFIN_DIR", signals_root / "danelfin")
    monkeypatch.setattr(refresh, "_YAHOO_DIR", signals_root / "yahoo")
    monkeypatch.setattr(refresh, "_FMP_DIR", signals_root / "fmp")
    monkeypatch.setattr(refresh, "_BASE_UNIVERSE", data_root / "current" / "base_equity_universe.csv")
    monkeypatch.setattr(refresh, "_PAR_ROOT", par_root)

    # Force bridge staging roots into this test's isolated temp area.
    real_tmpdir = tempfile.TemporaryDirectory
    monkeypatch.setattr(
        refresh.tempfile,
        "TemporaryDirectory",
        lambda prefix="", **kwargs: real_tmpdir(prefix=prefix, dir=str(stage_dir)),
    )

    # Runtime guard for any default publication path usage.
    original_publish = refresh._publish_market_proxy_replay_staging_outputs

    def _guarded_publish(staged_repo_root: Path) -> None:
        target_current_root = refresh._REPO_ROOT / "data" / "current"
        _guard_not_real_current_root(target_current_root)
        original_publish(staged_repo_root)

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", _guarded_publish)


def _seed_stage_with_required_outputs(
    staged_repo_root: Path,
    *,
    industries: tuple[str, ...] = refresh._MARKET_PROXY_REPLAY_INDUSTRIES,
) -> Path:
    staged_current_root = staged_repo_root / "data" / "current"
    _guard_not_real_current_root(staged_current_root)
    staged_current_root.mkdir(parents=True, exist_ok=True)

    with (staged_current_root / "replay_inputs.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "replay_id",
                "filter_geography",
                "filter_market_cap_bucket",
                "filter_industry",
                "selected_symbols",
            ],
        )
        writer.writeheader()
        for industry in industries:
            writer.writerow(
                {
                    "replay_id": f"RID-{industry}",
                    "filter_geography": "US",
                    "filter_market_cap_bucket": "LARGE",
                    "filter_industry": industry,
                    "selected_symbols": "AAA|BBB",
                }
            )

    with (staged_current_root / "replay_performance_series.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["replay_id", "series_type", "date", "value"],
        )
        writer.writeheader()
        for industry in industries:
            writer.writerow(
                {
                    "replay_id": f"RID-{industry}",
                    "series_type": "FULL_UNIVERSE",
                    "date": "2026-07-15",
                    "value": "100.0",
                }
            )

    return staged_current_root


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_dedicated_refresh_report_disables_replay_publish_for_market_regime_proxy_only(monkeypatch) -> None:
    replay_bridge_called = {"value": False}

    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.fetch_market_regime_proxy_history",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "published": True,
            "symbols": ["XLK", "XLE", "XLB", "XLI"],
            "observations_by_symbol": {"XLK": 70, "XLE": 70, "XLB": 70, "XLI": 70},
            "earliest_date": "2026-03-01",
            "latest_common_date": "2026-07-15",
            "missing_symbols": [],
            "insufficient_symbols": [],
            "warnings": [],
            "transaction_id": "MRG-HISTORY-test",
        },
    )
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.build_market_regime_proxy_artifacts",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "reason": "completed",
            "published": True,
            "input_source": "dedicated_market_regime_price_history",
            "latest_proxy_date_before": "2026-07-14",
            "latest_proxy_date_after": "2026-07-15",
            "missing_inputs": [],
            "warnings": [],
            "transaction_id": "MRG-DEDICATED-test",
        },
    )
    monkeypatch.setattr(
        refresh,
        "_publish_market_proxy_replay_artifacts",
        lambda **kwargs: replay_bridge_called.__setitem__("value", True),
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_MARKET_REGIME_PROXY_ONLY,
    )

    assert replay_bridge_called["value"] is False
    assert report["market_proxy_replay_publish"]["status"] == "disabled"
    assert report["market_proxy_replay_publish"]["reason"] == "dedicated_proxy_artifact_architecture"
    assert report["market_regime_proxy_history_fetch"]["published"] is True
    assert report["market_regime_proxy_artifact_build"]["published"] is True
    assert report["market_regime_proxy_artifact_build"]["input_source"] == "dedicated_market_regime_price_history"


def test_dedicated_refresh_report_exposes_separate_dedicated_status_blocks(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.fetch_market_regime_proxy_history",
        lambda repo_root: {
            "attempted": True,
            "status": "failed",
            "published": False,
            "symbols": ["XLK", "XLE", "XLB", "XLI"],
            "observations_by_symbol": {"XLK": 60, "XLE": 60, "XLB": 60, "XLI": 60},
            "earliest_date": "2026-03-01",
            "latest_common_date": "2026-07-15",
            "missing_symbols": [],
            "insufficient_symbols": ["XLK", "XLE", "XLB", "XLI"],
            "warnings": ["insufficient_observations"],
            "transaction_id": "MRG-HISTORY-test",
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_MARKET_REGIME_PROXY_ONLY,
    )

    assert report["market_proxy_replay_publish"]["status"] == "disabled"
    assert report["market_regime_proxy_history_fetch"]["status"] == "failed"
    assert report["market_regime_proxy_artifact_build"]["status"] == "failed"
    assert report["market_regime_proxy_artifact_build"]["reason"] == "history_fetch_failed"


def test_non_targeted_refresh_report_keeps_replay_publish_disabled(monkeypatch) -> None:
    replay_bridge_called = {"value": False}
    monkeypatch.setattr(
        refresh,
        "_build_refresh_scope",
        lambda *, refresh_mode: {
            "scope_summary": {"market_proxy_count": 7},
            "planned_symbol_samples": {},
            "buy_candidate_cap": 50,
            "planned_symbols": {"provider_symbols": {"zacks": [], "danelfin": [], "yahoo": []}},
        },
    )
    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (False, {"provider": "zacks", "state": "RESEARCH_FRESH_COMPLIANT"}))
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.build_market_regime_proxy_artifacts",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "reason": "completed",
            "published": True,
            "input_source": "dedicated_market_regime_price_history",
            "latest_proxy_date_before": "2026-07-14",
            "latest_proxy_date_after": "2026-07-15",
            "missing_inputs": [],
            "warnings": [],
            "transaction_id": "MRG-DEDICATED-test",
        },
    )
    monkeypatch.setattr(
        refresh,
        "_publish_market_proxy_replay_artifacts",
        lambda **kwargs: replay_bridge_called.__setitem__("value", True),
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks",),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_HOLDINGS_PLUS_BUY_CANDIDATES,
    )

    assert report["providers"]["zacks"]["state"] == "RESEARCH_FRESH_COMPLIANT"
    assert report["providers"]["zacks"]["triggered"] is False
    assert replay_bridge_called["value"] is False
    assert report["market_proxy_replay_publish"]["status"] == "disabled"
    assert report["market_regime_proxy_artifact_build"]["published"] is True


def test_market_regime_proxy_only_never_calls_provider_refresh(monkeypatch) -> None:
    called = {"z": False, "d": False, "y": False}

    monkeypatch.setattr(refresh, "_refresh_zacks", lambda **kwargs: (called.__setitem__("z", True), {}) and (False, {}))
    monkeypatch.setattr(refresh, "_refresh_danelfin", lambda **kwargs: (called.__setitem__("d", True), {}) and (False, {}))
    monkeypatch.setattr(refresh, "_refresh_yahoo", lambda **kwargs: (called.__setitem__("y", True), {}) and (False, {}))
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.fetch_market_regime_proxy_history",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "published": True,
            "symbols": ["XLK", "XLE", "XLB", "XLI"],
            "observations_by_symbol": {"XLK": 70, "XLE": 70, "XLB": 70, "XLI": 70},
            "earliest_date": "2026-03-01",
            "latest_common_date": "2026-07-15",
            "missing_symbols": [],
            "insufficient_symbols": [],
            "warnings": [],
            "transaction_id": "MRG-HISTORY-test",
        },
    )
    monkeypatch.setattr(
        "src.portfolio.regime.market_regime_proxy_artifacts.build_market_regime_proxy_artifacts",
        lambda repo_root: {
            "attempted": True,
            "status": "completed",
            "reason": "completed",
            "published": True,
            "input_source": "dedicated_market_regime_price_history",
            "latest_proxy_date_before": "2026-07-14",
            "latest_proxy_date_after": "2026-07-15",
            "missing_inputs": [],
            "warnings": [],
            "transaction_id": "MRG-DEDICATED-test",
        },
    )

    report = refresh.ensure_signals_fresh_with_report(
        providers=("zacks", "danelfin", "yahoo"),
        dry_run=False,
        verbose=False,
        refresh_mode=refresh.REFRESH_MODE_MARKET_REGIME_PROXY_ONLY,
    )

    assert called == {"z": False, "d": False, "y": False}
    assert report["market_proxy_replay_publish"]["status"] == "disabled"
    assert report["market_regime_proxy_history_fetch"]["published"] is True
    assert report["market_regime_proxy_artifact_build"]["published"] is True


def test_market_regime_proxy_freshness_uses_regenerated_replay_artifact(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260714-TEST", "snapshot_date": "2026-07-14"},
    )

    calls: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)

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
    assert all(str(item[1]).startswith("MRG-PROXY-BRIDGE-20260714-") for item in calls)
    assert all(item[2] == "2026-07-14" for item in calls)
    assert all(item[3] == "2026-07-14" for item in calls)
    assert status["status"] == "completed"
    assert status["latest_proxy_date"] == "2026-07-14"


def test_bridge_does_not_report_completed_when_target_industry_zero_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)

    published = {"value": False}

    def _publish_outputs(staged_repo_root: Path) -> None:
        published["value"] = True

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", _publish_outputs)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 0,
            "availability_row_count": 10,
            "status_counts": {"BLOCKED": 0},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": ""},
            "data_quality": {"missing_inputs": ["TECHNOLOGY benchmark proxy", "hard-asset benchmark proxies"]},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["status"] == "warning"
    assert status["published"] is False
    assert published["value"] is False
    assert status["reason"] == "blocked_or_zero_row_generation"


def test_bridge_does_not_report_completed_when_target_industry_blocked(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)
    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", lambda staged_repo_root: None)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 10,
            "availability_row_count": 10,
            "status_counts": {"BLOCKED": 2},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": "2026-07-15"},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["status"] == "warning"
    assert status["published"] is False
    assert status["reason"] == "blocked_or_zero_row_generation"
    assert status["details"]["blocked_industries"] == sorted(list(refresh._MARKET_PROXY_REPLAY_INDUSTRIES))


def test_bridge_preserves_current_artifacts_on_zero_row_generation(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)

    published = {"value": False}

    def _publish_outputs(staged_repo_root: Path) -> None:
        published["value"] = True

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", _publish_outputs)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 0,
            "availability_row_count": 10,
            "status_counts": {},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": ""},
            "data_quality": {"missing_inputs": ["TECHNOLOGY benchmark proxy"]},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert published["value"] is False
    assert status["published"] is False


def test_bridge_status_exposes_zero_row_and_blocked_industries(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)
    statuses = {
        "TECHNOLOGY": {"matrix_row_count": 0, "status_counts": {"BLOCKED": 1}},
        "ENERGY": {"matrix_row_count": 0, "status_counts": {}},
        "BASIC MATERIALS": {"matrix_row_count": 5, "status_counts": {}},
        "INDUSTRIALS": {"matrix_row_count": 5, "status_counts": {}},
    }

    def _builder(**kwargs):
        industry = kwargs["filter_industry"]
        payload = statuses[industry]
        return {
            "run_id": kwargs["run_id"],
            "matrix_row_count": payload["matrix_row_count"],
            "availability_row_count": 10,
            "status_counts": payload["status_counts"],
        }

    monkeypatch.setattr("src.replay.foundation_service.build_wp05b_replay_matrix", _builder)
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": ""},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["details"]["blocked_industries"] == ["TECHNOLOGY"]
    assert status["details"]["zero_row_industries"] == ["ENERGY", "TECHNOLOGY"]


def test_bridge_requires_non_empty_latest_proxy_date_after_for_completed(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)
    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", lambda staged_repo_root: None)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 10,
            "availability_row_count": 10,
            "status_counts": {},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": ""},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["status"] == "warning"
    assert status["published"] is False
    assert status["reason"] == "latest_proxy_date_missing_after_generation"


def test_bridge_does_not_publish_when_any_industry_generation_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)

    published = {"value": False}

    def _publish_outputs(staged_repo_root: Path) -> None:
        published["value"] = True

    def _builder(**kwargs):
        if kwargs["filter_industry"] == "ENERGY":
            raise RuntimeError("immutable partition collision")
        return {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 10,
            "availability_row_count": 10,
            "status_counts": {},
        }

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", _publish_outputs)
    monkeypatch.setattr("src.replay.foundation_service.build_wp05b_replay_matrix", _builder)
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": "2026-07-15"},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["published"] is False
    assert status["status"] == "warning"
    assert status["reason"] == "industry_generation_failed"
    assert published["value"] is False
    assert "ENERGY" in status["details"]["failed_industries"]


def test_one_invalid_industry_invalidates_entire_bridge_attempt(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)

    published = {"value": False}

    def _publish_outputs(staged_repo_root: Path) -> None:
        published["value"] = True

    def _builder(**kwargs):
        industry = kwargs["filter_industry"]
        return {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 0 if industry == "TECHNOLOGY" else 10,
            "availability_row_count": 10,
            "status_counts": {},
        }

    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", _publish_outputs)
    monkeypatch.setattr("src.replay.foundation_service.build_wp05b_replay_matrix", _builder)
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": "2026-07-15"},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["published"] is False
    assert status["status"] == "warning"
    assert status["reason"] == "blocked_or_zero_row_generation"
    assert published["value"] is False


def test_bridge_does_not_publish_when_required_cohorts_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(
        refresh,
        "_seed_market_proxy_replay_staging_root",
        lambda staged_repo_root: _seed_stage_with_required_outputs(
            staged_repo_root,
            industries=("TECHNOLOGY", "ENERGY", "INDUSTRIALS"),
        ),
    )
    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", lambda staged_repo_root: None)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 10,
            "availability_row_count": 10,
            "status_counts": {},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": "2026-07-15"},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["published"] is False
    assert status["status"] == "warning"
    assert status["reason"] == "required_cohorts_missing_after_generation"
    assert status["details"]["missing_required_cohorts"]


def test_completed_requires_published_true(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 10,
            "availability_row_count": 10,
            "status_counts": {},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": "2026-07-15"},
            "data_quality": {"missing_inputs": []},
        },
    )
    monkeypatch.setattr(
        refresh,
        "_publish_market_proxy_replay_staging_outputs",
        lambda staged_repo_root: (_ for _ in ()).throw(RuntimeError("copy failed")),
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["published"] is False
    assert status["status"] == "warning"
    assert status["reason"] != "completed"


def test_bridge_failure_preserves_current_artifacts_byte_for_byte(monkeypatch, tmp_path) -> None:
    current_root = tmp_path / "data" / "current"
    current_root.mkdir(parents=True, exist_ok=True)
    replay_inputs = current_root / "replay_inputs.csv"
    replay_series = current_root / "replay_performance_series.csv"
    replay_inputs.write_text(
        "replay_id,filter_geography,filter_market_cap_bucket,filter_industry,selected_symbols\n"
        "RID0,US,LARGE,TECHNOLOGY,AAA|BBB\n",
        encoding="utf-8",
    )
    replay_series.write_text(
        "replay_id,series_type,date,value\nRID0,FULL_UNIVERSE,2026-07-15,100\n",
        encoding="utf-8",
    )

    before_inputs_hash = _sha256(replay_inputs)
    before_series_hash = _sha256(replay_series)

    monkeypatch.setattr(refresh, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr("src.replay.foundation_service.build_wp05b_replay_matrix", lambda **kwargs: {
        "run_id": kwargs["run_id"],
        "matrix_row_count": 0,
        "availability_row_count": 10,
        "status_counts": {},
    })
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": ""},
            "data_quality": {"missing_inputs": ["TECHNOLOGY benchmark proxy"]},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["published"] is False
    assert _sha256(replay_inputs) == before_inputs_hash
    assert _sha256(replay_series) == before_series_hash


def test_bridge_success_requires_every_target_industry_and_required_cohort(monkeypatch) -> None:
    monkeypatch.setattr(
        refresh,
        "_latest_completed_portfolio_context",
        lambda: {"run_id": "PAR-20260715-TEST", "snapshot_date": "2026-07-15"},
    )
    monkeypatch.setattr(refresh, "_seed_market_proxy_replay_staging_root", _seed_stage_with_required_outputs)
    monkeypatch.setattr(refresh, "_publish_market_proxy_replay_staging_outputs", lambda staged_repo_root: None)
    monkeypatch.setattr(
        "src.replay.foundation_service.build_wp05b_replay_matrix",
        lambda **kwargs: {
            "run_id": kwargs["run_id"],
            "matrix_row_count": 10,
            "availability_row_count": 10,
            "status_counts": {},
        },
    )
    monkeypatch.setattr(
        "src.sih.rotation_risk_monitor.rotation_risk_summary",
        lambda repo_root: {
            "proxy_returns": {"latest_proxy_date": "2026-07-15"},
            "data_quality": {"missing_inputs": []},
        },
    )

    status = refresh._publish_market_proxy_replay_artifacts(verbose=False)

    assert status["status"] == "completed"
    assert status["published"] is True
    assert sorted(status["details"]["target_industries"]) == sorted(list(refresh._MARKET_PROXY_REPLAY_INDUSTRIES))
    assert status["details"]["missing_required_cohorts"] == []