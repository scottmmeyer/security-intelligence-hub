"""Governed materialization and fail-fast serving for current intelligence."""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"
CURRENT_ROOT_NAME = "current_intelligence"
POINTER_NAME = "current_pointer.json"
MOMENTUM_ARTIFACT_NAME = "momentum_summary.json"
DRI_ARTIFACT_NAME = "dri_industry_map.json"


class CurrentIntelligenceError(RuntimeError):
    """Raised when current intelligence is missing, stale, or invalid."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _current_root(root: Path) -> Path:
    return root / "data" / "current" / CURRENT_ROOT_NAME


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_NOT_MATERIALIZED", f"Missing artifact: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_INVALID", f"Unreadable artifact: {path}") from exc
    if not isinstance(value, dict):
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_INVALID", f"Artifact must contain an object: {path}")
    return value


def _latest_portfolio_identity(root: Path, expected_date: str | None = None) -> dict[str, str]:
    manifest_path = root / "data" / "portfolio_ingestion" / "manifest.json"
    manifest = _read_json(manifest_path)
    portfolios = manifest.get("portfolios")
    if not isinstance(portfolios, list):
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_NOT_MATERIALIZED", "No portfolio run manifest is available.")
    candidates = [row for row in portfolios if isinstance(row, dict) and str(row.get("status") or "").upper() == "COMPLETE"]
    if expected_date:
        candidates = [row for row in candidates if str(row.get("snapshot_date") or "")[:10] == expected_date[:10]]
    if not candidates:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", "No complete current portfolio snapshot matches the requested date.")
    row = max(candidates, key=lambda item: str(item.get("created_at_utc") or ""))
    identity = {
        "portfolio_run_id": str(row.get("run_id") or ""),
        "portfolio_snapshot_id": str(row.get("portfolio_snapshot_id") or ""),
        "snapshot_date": str(row.get("snapshot_date") or "")[:10],
    }
    if not all(identity.values()):
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_INVALID", "Current portfolio identity is incomplete.")
    return identity


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _artifact_payload(
    *,
    artifact_type: str,
    artifact_path: Path,
    identity: dict[str, str],
    payload: dict[str, Any],
    generated_at_utc: str,
) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "schema_version": SCHEMA_VERSION,
        "snapshot_date": identity["snapshot_date"],
        "as_of_date": identity["snapshot_date"],
        "generated_at_utc": generated_at_utc,
        "source_portfolio_run_id": identity["portfolio_run_id"],
        "source_portfolio_snapshot_id": identity["portfolio_snapshot_id"],
        "analysis_as_of": identity["snapshot_date"],
        "provenance": {
            "source": "governed_current_intelligence_materialization",
            "generation_mode": "explicit_materialization",
        },
        "payload": payload,
        "artifact_path": str(artifact_path),
    }


def materialize_current_intelligence(
    *,
    repo_root: str | Path = ".",
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    identity = _latest_portfolio_identity(root, expected_date=snapshot_date)
    from src.pis.dislocation_recovery_intelligence import pis_dri_industry_map
    from src.pis.momentum_intelligence import pis_momentum_summary

    momentum = pis_momentum_summary(repo_root=root)
    dri = pis_dri_industry_map(repo_root=root, as_of_date=identity["snapshot_date"])
    if str(momentum.get("snapshot_date") or "")[:10] != identity["snapshot_date"]:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", "Momentum output does not match current portfolio date.")
    if str(dri.get("as_of_date") or "")[:10] != identity["snapshot_date"]:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", "DRI output does not match current portfolio date.")

    output_root = _current_root(root)
    generated_at = datetime.now(timezone.utc).isoformat()
    momentum_path = output_root / MOMENTUM_ARTIFACT_NAME
    dri_path = output_root / DRI_ARTIFACT_NAME
    momentum_artifact = _artifact_payload(
        artifact_type="CURRENT_MOMENTUM_SUMMARY",
        artifact_path=momentum_path,
        identity=identity,
        payload=momentum,
        generated_at_utc=generated_at,
    )
    dri_artifact = _artifact_payload(
        artifact_type="CURRENT_DRI_INDUSTRY_MAP",
        artifact_path=dri_path,
        identity=identity,
        payload=dri,
        generated_at_utc=generated_at,
    )
    _atomic_write_json(momentum_path, momentum_artifact)
    _atomic_write_json(dri_path, dri_artifact)
    pointer = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at,
        "snapshot_date": identity["snapshot_date"],
        "analysis_as_of": identity["snapshot_date"],
        "source_portfolio_run_id": identity["portfolio_run_id"],
        "source_portfolio_snapshot_id": identity["portfolio_snapshot_id"],
        "provenance": "governed_current_intelligence_materialization",
        "momentum": str(momentum_path.relative_to(root)),
        "dri": str(dri_path.relative_to(root)),
    }
    _atomic_write_json(output_root / POINTER_NAME, pointer)
    return {
        "snapshot_date": identity["snapshot_date"],
        "portfolio_run_id": identity["portfolio_run_id"],
        "portfolio_snapshot_id": identity["portfolio_snapshot_id"],
        "momentum_artifact": str(momentum_path),
        "dri_artifact": str(dri_path),
        "pointer": str(output_root / POINTER_NAME),
    }


def _validate_artifact(
    *,
    root: Path,
    artifact_path: Path,
    artifact_type: str,
    identity: dict[str, str],
    required_payload_keys: tuple[str, ...],
) -> dict[str, Any]:
    artifact = _read_json(artifact_path)
    if artifact.get("artifact_type") != artifact_type or artifact.get("schema_version") != SCHEMA_VERSION:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_INVALID", f"Artifact identity/schema mismatch: {artifact_path}")
    for key in ("snapshot_date", "as_of_date", "analysis_as_of"):
        if str(artifact.get(key) or "")[:10] != identity["snapshot_date"]:
            raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", f"Artifact date mismatch: {artifact_path}")
    if artifact.get("source_portfolio_run_id") != identity["portfolio_run_id"] or artifact.get("source_portfolio_snapshot_id") != identity["portfolio_snapshot_id"]:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", f"Artifact portfolio identity mismatch: {artifact_path}")
    payload = artifact.get("payload")
    if not isinstance(payload, dict) or any(key not in payload for key in required_payload_keys):
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_INVALID", f"Artifact payload is incomplete: {artifact_path}")
    return payload


def load_current_intelligence(
    *,
    kind: str,
    repo_root: str | Path = ".",
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    identity = _latest_portfolio_identity(root, expected_date=snapshot_date)
    pointer = _read_json(_current_root(root) / POINTER_NAME)
    if pointer.get("schema_version") != SCHEMA_VERSION or str(pointer.get("snapshot_date") or "")[:10] != identity["snapshot_date"]:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", "Current intelligence pointer does not match the portfolio snapshot.")
    if pointer.get("source_portfolio_run_id") != identity["portfolio_run_id"] or pointer.get("source_portfolio_snapshot_id") != identity["portfolio_snapshot_id"]:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_STALE", "Current intelligence pointer has the wrong portfolio identity.")
    relative_path = pointer.get(kind)
    if not isinstance(relative_path, str) or not relative_path:
        raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_NOT_MATERIALIZED", f"No current {kind} artifact is published.")
    artifact_path = root / relative_path
    if kind == "momentum":
        return copy.deepcopy(_validate_artifact(
            root=root,
            artifact_path=artifact_path,
            artifact_type="CURRENT_MOMENTUM_SUMMARY",
            identity=identity,
            required_payload_keys=("snapshot_date", "market_momentum", "sector_rotation", "industry_rotation", "portfolio_momentum_map", "coverage"),
        ))
    if kind == "dri":
        return copy.deepcopy(_validate_artifact(
            root=root,
            artifact_path=artifact_path,
            artifact_type="CURRENT_DRI_INDUSTRY_MAP",
            identity=identity,
            required_payload_keys=("as_of_date", "coverage_summary", "industries"),
        ))
    raise CurrentIntelligenceError("CURRENT_INTELLIGENCE_INVALID", f"Unknown current intelligence kind: {kind}")
