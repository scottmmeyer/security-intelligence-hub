"""Allocation data storage manager — append-only snapshots, current targets, manifest."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.allocation.models import (
    AllocationEvidence,
    AllocationRecommendation,
    AllocationRecalculationSnapshot,
    StrategicAllocationTarget,
    TacticalMomentumOverlay,
)

# ─── CSV Header Contracts ───────────────────────────────────────────────────

STRATEGIC_ALLOCATION_HEADERS = [
    "target_id", "snapshot_date", "recalculation_id", "node_key", "node_label",
    "parent_key", "asset_class", "geography", "market_structure", "mega_subtier",
    "hierarchy_depth", "target_pct_of_parent", "target_pct_of_total",
    "prior_target_pct_of_total", "delta_pct", "confidence_score", "evidence_summary",
    "evidence_ids", "methodology_basis_ref", "policy_bounded",
]

TACTICAL_OVERLAY_HEADERS = [
    "overlay_id", "effective_date", "expiry_date", "dimension_type", "dimension_value",
    "overlay_pct", "max_overlay_pct", "persistence_score", "momentum_signal",
    "replay_support_ids", "notes", "status",
]

ALLOCATION_RECOMMENDATION_HEADERS = [
    "recommendation_id", "snapshot_date", "policy_id", "recalculation_id", "node_key",
    "asset_class", "strategic_target_pct", "tactical_overlay_pct", "effective_target_pct",
    "is_policy_capped", "policy_ceiling", "drift_from_prior",
]

EVIDENCE_HEADERS = [
    "evidence_id", "evidence_date", "evidence_type", "node_key", "asset_class",
    "metric_name", "metric_value", "benchmark_comparison", "significance", "replay_id",
    "human_readable",
]

SNAPSHOT_HEADERS = [
    "recalculation_id", "recalculation_date", "prior_recalculation_id", "triggered_by",
    "policy_version", "evidence_ids", "change_summary", "unchanged_summary",
    "total_allocation_valid", "notes",
]


class AllocationStoragePaths:
    """All paths used by the allocation intelligence system."""

    def __init__(self, base_dir: Path | str = Path("data")):
        root = Path(base_dir)
        self.alloc_dir = root / "allocation"
        self.snapshots_dir = self.alloc_dir / "recalculation_snapshots"
        self.evidence_dir = self.alloc_dir / "evidence_history"
        self.proposed_dir = self.alloc_dir / "proposed"
        self.overlay_history_dir = self.alloc_dir / "overlay_history"
        self.current_dir = root / "current"
        self.manifest_path = self.alloc_dir / "manifest.json"

        # Current published files
        self.current_targets = self.current_dir / "strategic_allocation_targets.csv"
        self.current_overlays = self.current_dir / "tactical_overlays.csv"
        self.current_recommendation = self.current_dir / "allocation_recommendation.csv"

        # Proposed (pre-commit)
        self.proposed_targets = self.proposed_dir / "proposed_strategic_targets.csv"
        self.proposed_recommendation = self.proposed_dir / "proposed_allocation_recommendation.csv"
        self.proposed_snapshot = self.proposed_dir / "proposed_snapshot.json"

    def ensure_dirs(self) -> None:
        for d in [
            self.alloc_dir, self.snapshots_dir, self.evidence_dir,
            self.proposed_dir, self.overlay_history_dir, self.current_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


def _ensure_csv_with_headers(path: Path, headers: list[str]) -> None:
    """Create CSV with headers if it doesn't exist. No-op if it already has correct headers."""
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()


def _write_csv_rows(path: Path, headers: list[str], rows: list[dict]) -> None:
    """Overwrite a CSV file with given rows."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _append_csv_rows(path: Path, headers: list[str], rows: list[dict]) -> None:
    """Append rows to a CSV, creating with header if necessary."""
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        if not exists or path.stat().st_size == 0:
            writer.writeheader()
        writer.writerows(rows)


def _read_csv_rows(path: Path) -> list[dict]:
    """Read CSV rows as list of dicts. Returns empty list if file doesn't exist."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _target_to_row(t: StrategicAllocationTarget) -> dict:
    return {
        "target_id": t.target_id,
        "snapshot_date": t.snapshot_date,
        "recalculation_id": t.recalculation_id,
        "node_key": t.node_key,
        "node_label": t.node_label,
        "parent_key": t.parent_key or "",
        "asset_class": t.asset_class,
        "geography": t.geography or "",
        "market_structure": t.market_structure or "",
        "mega_subtier": t.mega_subtier or "",
        "hierarchy_depth": t.hierarchy_depth,
        "target_pct_of_parent": t.target_pct_of_parent,
        "target_pct_of_total": t.target_pct_of_total,
        "prior_target_pct_of_total": t.prior_target_pct_of_total or "",
        "delta_pct": t.delta_pct if t.delta_pct is not None else "",
        "confidence_score": t.confidence_score,
        "evidence_summary": t.evidence_summary,
        "evidence_ids": "|".join(t.evidence_ids),
        "methodology_basis_ref": t.methodology_basis_ref,
        "policy_bounded": str(t.policy_bounded),
    }


def _recommendation_to_row(r: AllocationRecommendation) -> dict:
    return {
        "recommendation_id": r.recommendation_id,
        "snapshot_date": r.snapshot_date,
        "policy_id": r.policy_id,
        "recalculation_id": r.recalculation_id,
        "node_key": r.node_key,
        "asset_class": r.asset_class,
        "strategic_target_pct": r.strategic_target_pct,
        "tactical_overlay_pct": r.tactical_overlay_pct,
        "effective_target_pct": r.effective_target_pct,
        "is_policy_capped": str(r.is_policy_capped),
        "policy_ceiling": r.policy_ceiling if r.policy_ceiling is not None else "",
        "drift_from_prior": r.drift_from_prior if r.drift_from_prior is not None else "",
    }


def _evidence_to_row(e: AllocationEvidence) -> dict:
    return {
        "evidence_id": e.evidence_id,
        "evidence_date": e.evidence_date,
        "evidence_type": e.evidence_type,
        "node_key": e.node_key,
        "asset_class": e.asset_class,
        "metric_name": e.metric_name,
        "metric_value": e.metric_value,
        "benchmark_comparison": e.benchmark_comparison or "",
        "significance": e.significance,
        "replay_id": e.replay_id or "",
        "human_readable": e.human_readable,
    }


def _canonical_target_rows(targets: list[StrategicAllocationTarget]) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for t in targets:
        pct = float(getattr(t, "target_pct_of_total", 0.0) or 0.0)
        if math.isnan(pct) or math.isinf(pct):
            pct = 0.0
        rows.append((str(getattr(t, "node_key", "")), pct))
    rows.sort(key=lambda x: x[0])
    return rows


def _fnv1a_32(text: str) -> str:
    h = 0x811C9DC5
    for b in text.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def _target_model_fingerprint(targets: list[StrategicAllocationTarget]) -> str:
    canonical = "|".join(f"{k}={v:.6f}" for k, v in _canonical_target_rows(targets))
    return _fnv1a_32(canonical)


def _format_validator_results(validation_results: dict[str, list[str]] | None) -> dict[str, dict[str, object]]:
    """Normalize validator output to an object schema the UI already supports."""
    if not validation_results:
        return {}

    payload: dict[str, dict[str, object]] = {}
    for name, errors in validation_results.items():
        err_list = list(errors or [])
        if err_list:
            payload[name] = {
                "status": "FAIL",
                "message": " | ".join(str(e) for e in err_list),
                "errors": [str(e) for e in err_list],
            }
        else:
            payload[name] = {
                "status": "PASS",
                "message": "",
                "errors": [],
            }
    return payload


def _snapshot_to_dict(
    s: AllocationRecalculationSnapshot,
    validation_results: dict[str, list[str]] | None = None,
    target_model_fingerprint: str | None = None,
    target_model_scope: str | None = None,
) -> dict:
    payload = {
        "recalculation_id": s.recalculation_id,
        "recalculation_date": s.recalculation_date,
        "prior_recalculation_id": s.prior_recalculation_id or "",
        "triggered_by": s.triggered_by,
        "policy_version": s.policy_version,
        "evidence_ids": list(s.evidence_ids),
        "change_summary": list(s.change_summary),
        "unchanged_summary": s.unchanged_summary,
        "confidence_summary": s.confidence_summary,
        "total_allocation_valid": s.total_allocation_valid,
        "notes": s.notes,
    }
    formatted = _format_validator_results(validation_results)
    if formatted:
        payload["validator_results"] = formatted
    if target_model_fingerprint:
        payload["target_model_fingerprint"] = target_model_fingerprint
    if target_model_scope:
        payload["target_model_scope"] = target_model_scope
    return payload


# ─── Public API ──────────────────────────────────────────────────────────────

def save_proposed_targets(
    targets: list[StrategicAllocationTarget],
    snapshot: AllocationRecalculationSnapshot,
    recommendations: list[AllocationRecommendation],
    validation_results: dict[str, list[str]] | None = None,
    paths: AllocationStoragePaths | None = None,
) -> None:
    """Write proposed targets, recommendation, and snapshot JSON to proposed/ dir."""
    if paths is None:
        paths = AllocationStoragePaths()
    paths.ensure_dirs()

    _write_csv_rows(paths.proposed_targets, STRATEGIC_ALLOCATION_HEADERS,
                    [_target_to_row(t) for t in targets])
    _write_csv_rows(paths.proposed_recommendation, ALLOCATION_RECOMMENDATION_HEADERS,
                    [_recommendation_to_row(r) for r in recommendations])
    target_fingerprint = _target_model_fingerprint(targets)
    with paths.proposed_snapshot.open("w", encoding="utf-8") as fh:
        json.dump(
            _snapshot_to_dict(
                snapshot,
                validation_results=validation_results,
                target_model_fingerprint=target_fingerprint,
                target_model_scope="PROPOSED_NON_COMMIT",
            ),
            fh,
            indent=2,
        )


def publish_proposed_targets(
    targets: list[StrategicAllocationTarget],
    snapshot: AllocationRecalculationSnapshot,
    recommendations: list[AllocationRecommendation],
    evidence_records: list[AllocationEvidence],
    validation_results: dict[str, list[str]] | None = None,
    paths: AllocationStoragePaths | None = None,
) -> None:
    """Commit proposed targets to data/current/ and append to historical archives."""
    if paths is None:
        paths = AllocationStoragePaths()
    paths.ensure_dirs()

    # Publish to current/
    _write_csv_rows(paths.current_targets, STRATEGIC_ALLOCATION_HEADERS,
                    [_target_to_row(t) for t in targets])
    _write_csv_rows(paths.current_recommendation, ALLOCATION_RECOMMENDATION_HEADERS,
                    [_recommendation_to_row(r) for r in recommendations])
    _ensure_csv_with_headers(paths.current_overlays, TACTICAL_OVERLAY_HEADERS)

    # Append to historical snapshots archive
    snapshot_archive = paths.snapshots_dir / f"{snapshot.recalculation_id}.json"
    target_fingerprint = _target_model_fingerprint(targets)
    with snapshot_archive.open("w", encoding="utf-8") as fh:
        json.dump(
            _snapshot_to_dict(
                snapshot,
                validation_results=validation_results,
                target_model_fingerprint=target_fingerprint,
                target_model_scope="ACTIVE_PUBLISHED",
            ),
            fh,
            indent=2,
        )

    # Append evidence to historical evidence archive
    evidence_archive = paths.evidence_dir / f"{snapshot.recalculation_id}_evidence.csv"
    _write_csv_rows(evidence_archive, EVIDENCE_HEADERS,
                    [_evidence_to_row(e) for e in evidence_records])

    update_manifest(snapshot, paths)


def load_latest_targets(
    paths: AllocationStoragePaths | None = None,
) -> list[dict]:
    """Load current strategic allocation targets as raw CSV rows."""
    if paths is None:
        paths = AllocationStoragePaths()
    return _read_csv_rows(paths.current_targets)


def load_all_snapshots(
    paths: AllocationStoragePaths | None = None,
) -> list[dict]:
    """Load all historical snapshot JSON files as a list of dicts."""
    if paths is None:
        paths = AllocationStoragePaths()
    if not paths.snapshots_dir.exists():
        return []
    snapshots = []
    for f in sorted(paths.snapshots_dir.glob("*.json")):
        with f.open("r", encoding="utf-8") as fh:
            snapshots.append(json.load(fh))
    return snapshots


def load_active_overlays_from_csv(
    paths: AllocationStoragePaths | None = None,
) -> list[dict]:
    """Load active tactical overlays from data/current/tactical_overlays.csv."""
    if paths is None:
        paths = AllocationStoragePaths()
    rows = _read_csv_rows(paths.current_overlays)
    return [r for r in rows if r.get("status", "").upper() == "ACTIVE"]


def update_manifest(
    snapshot: AllocationRecalculationSnapshot,
    paths: AllocationStoragePaths | None = None,
) -> None:
    """Update (or cold-start create) manifest.json with latest recalculation metadata."""
    if paths is None:
        paths = AllocationStoragePaths()
    paths.ensure_dirs()

    manifest: dict[str, Any] = {}
    if paths.manifest_path.exists():
        with paths.manifest_path.open("r", encoding="utf-8") as fh:
            try:
                manifest = json.load(fh)
            except json.JSONDecodeError:
                manifest = {}

    manifest.setdefault("history", [])
    manifest["latest_recalculation_id"] = snapshot.recalculation_id
    manifest["latest_recalculation_date"] = snapshot.recalculation_date
    manifest["total_snapshots"] = len(manifest["history"]) + 1
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

    # Append lightweight history entry
    manifest["history"].append({
        "recalculation_id": snapshot.recalculation_id,
        "recalculation_date": snapshot.recalculation_date,
        "triggered_by": snapshot.triggered_by,
        "total_allocation_valid": snapshot.total_allocation_valid,
        "change_count": len([c for c in snapshot.change_summary if c != "No changes proposed."]),
    })

    with paths.manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
