from __future__ import annotations

import json
from pathlib import Path

import pytest

import src.pis.current_intelligence as current_intelligence


PORTFOLIO_MANIFEST = {
    "version": 1,
    "portfolios": [
        {
            "run_id": "PAR-TEST-0904",
            "portfolio_snapshot_id": "PSNAP-TEST-0904",
            "snapshot_date": "2026-09-04",
            "created_at_utc": "2026-09-04T12:00:00+00:00",
            "status": "COMPLETE",
        }
    ],
}


def _write_manifest(root: Path) -> None:
    path = root / "data" / "portfolio_ingestion" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(PORTFOLIO_MANIFEST), encoding="utf-8")


def _payloads() -> tuple[dict, dict]:
    momentum = {
        "snapshot_date": "2026-09-04",
        "market_momentum": {"market_absolute_momentum": {"state": "STRONG"}},
        "sector_rotation": [],
        "industry_rotation": [],
        "portfolio_momentum_map": {"holdings": []},
        "coverage": {"portfolio_coverage_state": "PARTIALLY_EVALUATED"},
    }
    dri = {
        "as_of_date": "2026-09-04",
        "coverage_summary": {"industry_count": 141},
        "industries": [],
    }
    return momentum, dri


def test_materialization_publishes_atomic_current_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_manifest(tmp_path)
    momentum, dri = _payloads()
    monkeypatch.setattr(current_intelligence, "_atomic_write_json", current_intelligence._atomic_write_json)
    monkeypatch.setattr("src.pis.momentum_intelligence.pis_momentum_summary", lambda repo_root: momentum)
    monkeypatch.setattr("src.pis.dislocation_recovery_intelligence.pis_dri_industry_map", lambda repo_root, as_of_date: dri)

    result = current_intelligence.materialize_current_intelligence(repo_root=tmp_path, snapshot_date="2026-09-04")
    pointer = json.loads((tmp_path / "data/current/current_intelligence/current_pointer.json").read_text(encoding="utf-8"))

    assert result["portfolio_run_id"] == "PAR-TEST-0904"
    assert pointer["snapshot_date"] == "2026-09-04"
    assert pointer["source_portfolio_snapshot_id"] == "PSNAP-TEST-0904"
    assert (tmp_path / "data/current/current_intelligence/momentum_summary.json").exists()
    assert (tmp_path / "data/current/current_intelligence/dri_industry_map.json").exists()
    assert not list((tmp_path / "data/current/current_intelligence").glob("*.tmp"))


def test_valid_current_reads_do_not_call_compute_functions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_manifest(tmp_path)
    momentum, dri = _payloads()
    monkeypatch.setattr("src.pis.momentum_intelligence.pis_momentum_summary", lambda repo_root: momentum)
    monkeypatch.setattr("src.pis.dislocation_recovery_intelligence.pis_dri_industry_map", lambda repo_root, as_of_date: dri)
    current_intelligence.materialize_current_intelligence(repo_root=tmp_path, snapshot_date="2026-09-04")

    def fail(*args, **kwargs):
        raise AssertionError("compute must not run during a valid current read")

    monkeypatch.setattr("src.pis.momentum_intelligence.pis_momentum_summary", fail)
    monkeypatch.setattr("src.pis.dislocation_recovery_intelligence.pis_dri_industry_map", fail)
    assert current_intelligence.load_current_intelligence(kind="momentum", repo_root=tmp_path)["snapshot_date"] == "2026-09-04"
    assert current_intelligence.load_current_intelligence(kind="dri", repo_root=tmp_path)["as_of_date"] == "2026-09-04"


def test_portfolio_run_enrichment_uses_current_artifact_without_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.run_outcome_ui as outcome_ui

    summary, _ = _payloads()
    summary["entry_timing_context"] = {"holdings": []}
    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", Path("."))
    monkeypatch.setattr(current_intelligence, "load_current_intelligence", lambda **kwargs: summary)
    monkeypatch.setattr(outcome_ui, "_pis_momentum_summary_cached", lambda: (_ for _ in ()).throw(AssertionError("compute must not run")))

    result = outcome_ui._enrich_top_trades_entry_timing_context({
        "snapshot_date": "2026-09-04",
        "deployment_queue": {"queue": [{"symbol": "DELL"}]},
    })

    assert result["deployment_queue"]["queue"][0]["entry_timing_context"]["history_status"] == "UNAVAILABLE"


def test_market_confirmation_uses_current_artifact_without_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.run_outcome_ui as outcome_ui

    summary, _ = _payloads()
    summary.update({
        "snapshot_date": "2026-09-04",
        "market_momentum": {"market_absolute_momentum": {"state": "STRONG"}},
        "sector_rotation": [],
        "portfolio_momentum_map": {"holdings": []},
        "coverage": {"portfolio_coverage_state": "PARTIALLY_EVALUATED"},
    })
    monkeypatch.setattr(outcome_ui, "_MACRO_MOMENTUM_CACHE", {"signature": None, "payload": None})
    monkeypatch.setattr(outcome_ui, "_REPO_ROOT", Path("."))
    monkeypatch.setattr(current_intelligence, "load_current_intelligence", lambda **kwargs: summary)
    monkeypatch.setattr(outcome_ui, "_pis_momentum_summary_cached", lambda: (_ for _ in ()).throw(AssertionError("compute must not run")))

    payload = outcome_ui._macro_market_confirmation_payload()

    assert payload["as_of"] == "2026-09-04"
    assert payload["market_state"] == "STRONG"


def test_missing_and_stale_current_artifacts_fail_fast(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    with pytest.raises(current_intelligence.CurrentIntelligenceError, match="Missing artifact"):
        current_intelligence.load_current_intelligence(kind="momentum", repo_root=tmp_path)

    root = tmp_path / "data/current/current_intelligence"
    root.mkdir(parents=True, exist_ok=True)
    pointer = {
        "schema_version": "1",
        "snapshot_date": "2026-09-03",
        "source_portfolio_run_id": "PAR-TEST-0904",
        "source_portfolio_snapshot_id": "PSNAP-TEST-0904",
        "momentum": "data/current/current_intelligence/momentum_summary.json",
    }
    (root / "current_pointer.json").write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(current_intelligence.CurrentIntelligenceError, match="does not match"):
        current_intelligence.load_current_intelligence(kind="momentum", repo_root=tmp_path)


def test_artifact_identity_and_payload_schema_are_validated(tmp_path: Path) -> None:
    _write_manifest(tmp_path)
    root = tmp_path / "data/current/current_intelligence"
    root.mkdir(parents=True, exist_ok=True)
    (root / "current_pointer.json").write_text(json.dumps({
        "schema_version": "1",
        "snapshot_date": "2026-09-04",
        "source_portfolio_run_id": "PAR-TEST-0904",
        "source_portfolio_snapshot_id": "PSNAP-TEST-0904",
        "momentum": "data/current/current_intelligence/momentum_summary.json",
    }), encoding="utf-8")
    (root / "momentum_summary.json").write_text(json.dumps({
        "artifact_type": "CURRENT_MOMENTUM_SUMMARY",
        "schema_version": "1",
        "snapshot_date": "2026-09-04",
        "as_of_date": "2026-09-04",
        "analysis_as_of": "2026-09-04",
        "source_portfolio_run_id": "PAR-TEST-0904",
        "source_portfolio_snapshot_id": "PSNAP-TEST-0904",
        "payload": {"snapshot_date": "2026-09-04"},
    }), encoding="utf-8")
    with pytest.raises(current_intelligence.CurrentIntelligenceError, match="incomplete"):
        current_intelligence.load_current_intelligence(kind="momentum", repo_root=tmp_path)
