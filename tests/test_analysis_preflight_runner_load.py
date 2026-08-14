from __future__ import annotations

import json
from pathlib import Path

from src.portfolio import runner


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_minimal_run(base: Path, run_id: str, *, metadata_preflight: dict | None = None) -> Path:
    run_dir = base / "analysis_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "run_metadata.json",
        {
            "run_id": run_id,
            "snapshot_date": "2026-08-13",
            "analysis_preflight": metadata_preflight,
        },
    )
    _write_json(run_dir / "snapshot.json", {"snapshot_date": "2026-08-13"})
    _write_json(run_dir / "concentration.json", {"concentration_tier": "LOW"})
    _write_json(run_dir / "recommendations.json", [])
    return run_dir


def test_load_analysis_run_prefers_persisted_preflight_artifact(tmp_path: Path, monkeypatch) -> None:
    ingestion_root = tmp_path / "data" / "portfolio_ingestion"
    run_id = "PAR-ARTIFACT"
    run_dir = _seed_minimal_run(ingestion_root, run_id, metadata_preflight={"status": "READY"})
    _write_json(run_dir / "preflight.json", {"status": "DEGRADED", "reason_codes": ["PF-GEO-001"]})

    monkeypatch.setattr(runner, "_INGESTION_ROOT", ingestion_root)
    monkeypatch.setattr(runner, "_build_consensus_payload", lambda: {})
    monkeypatch.setattr(runner, "_build_fidelity_payload", lambda: {})
    monkeypatch.setattr(runner, "_build_signal_source_metadata", lambda: {})
    monkeypatch.setattr(runner, "_build_fmp_payload", lambda _symbols: {})
    monkeypatch.setattr(runner, "_build_price_context_payload", lambda _symbols: {})
    monkeypatch.setattr(runner, "_build_market_context_payload", lambda **_kwargs: {})

    loaded = runner.load_analysis_run(run_id)
    assert loaded is not None
    assert loaded["analysis_preflight"]["status"] == "DEGRADED"
    assert loaded["analysis_preflight_provenance"] == "persisted_preflight_artifact"


def test_load_analysis_run_falls_back_to_metadata_preflight(tmp_path: Path, monkeypatch) -> None:
    ingestion_root = tmp_path / "data" / "portfolio_ingestion"
    run_id = "PAR-META"
    _seed_minimal_run(ingestion_root, run_id, metadata_preflight={"status": "READY", "reason_codes": []})

    monkeypatch.setattr(runner, "_INGESTION_ROOT", ingestion_root)
    monkeypatch.setattr(runner, "_build_consensus_payload", lambda: {})
    monkeypatch.setattr(runner, "_build_fidelity_payload", lambda: {})
    monkeypatch.setattr(runner, "_build_signal_source_metadata", lambda: {})
    monkeypatch.setattr(runner, "_build_fmp_payload", lambda _symbols: {})
    monkeypatch.setattr(runner, "_build_price_context_payload", lambda _symbols: {})
    monkeypatch.setattr(runner, "_build_market_context_payload", lambda **_kwargs: {})

    loaded = runner.load_analysis_run(run_id)
    assert loaded is not None
    assert loaded["analysis_preflight"]["status"] == "READY"
    assert loaded["analysis_preflight_provenance"] == "persisted_run_metadata"


def test_load_analysis_run_marks_computed_fallback_as_non_historical(tmp_path: Path, monkeypatch) -> None:
    ingestion_root = tmp_path / "data" / "portfolio_ingestion"
    run_id = "PAR-FALLBACK"
    _seed_minimal_run(ingestion_root, run_id, metadata_preflight=None)

    class _StubResult:
        def to_dict(self):
            return {"status": "BLOCKED", "reason_codes": ["PF-AU-001"]}

    monkeypatch.setattr(runner, "_INGESTION_ROOT", ingestion_root)
    monkeypatch.setattr(runner, "run_analysis_preflight", lambda **_kwargs: _StubResult())
    monkeypatch.setattr(runner, "_build_consensus_payload", lambda: {})
    monkeypatch.setattr(runner, "_build_fidelity_payload", lambda: {})
    monkeypatch.setattr(runner, "_build_signal_source_metadata", lambda: {})
    monkeypatch.setattr(runner, "_build_fmp_payload", lambda _symbols: {})
    monkeypatch.setattr(runner, "_build_price_context_payload", lambda _symbols: {})
    monkeypatch.setattr(runner, "_build_market_context_payload", lambda **_kwargs: {})

    loaded = runner.load_analysis_run(run_id)
    assert loaded is not None
    assert loaded["analysis_preflight"]["status"] == "BLOCKED"
    assert loaded["analysis_preflight"]["computed_at_load_time"] is True
    assert loaded["analysis_preflight_provenance"] == "computed_load_time_fallback"
