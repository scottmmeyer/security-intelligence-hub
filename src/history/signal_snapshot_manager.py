"""Immutable signal snapshot append scaffolding."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SNAPSHOT_HEADERS = [
    "snapshot_date",
    "run_id",
    "provider",
    "source_file",
    "symbol",
    "coverage_domain",
    "signal_coverage_status",
    "starmine_ess_text",
    "starmine_ess_numeric",
    "starmine_ess_numeric_estimated",
    "starmine_ess_source_type",
]

HISTORY_HEADERS = [
    "history_event_id",
    "snapshot_date",
    "run_id",
    "provider",
    "source_file",
    "coverage_domain",
    "event_type",
    "event_ts_utc",
]

LINEAGE_HEADERS = [
    "lineage_id",
    "snapshot_date",
    "run_id",
    "provider",
    "source_file",
    "symbol",
    "coverage_domain",
    "normalization_version",
    "lineage_notes",
]


def _ensure_file_with_headers(path: Path, headers: List[str]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()


def ensure_signal_history_contracts(history_root: str | Path = "data/history/signals") -> None:
    """Ensure signal history contract files exist with deterministic headers."""

    root = Path(history_root)
    _ensure_file_with_headers(root / "signal_snapshots.csv", SNAPSHOT_HEADERS)
    _ensure_file_with_headers(root / "signal_snapshot_history.csv", HISTORY_HEADERS)
    _ensure_file_with_headers(root / "signal_lineage_registry.csv", LINEAGE_HEADERS)


def _existing_snapshot_keys(snapshot_path: Path) -> set[Tuple[str, str, str, str, str, str]]:
    if not snapshot_path.exists():
        return set()

    keys: set[Tuple[str, str, str, str, str, str]] = set()
    with snapshot_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            keys.add(
                (
                    row.get("snapshot_date", ""),
                    row.get("run_id", ""),
                    row.get("provider", ""),
                    row.get("source_file", ""),
                    row.get("symbol", ""),
                    row.get("coverage_domain", ""),
                )
            )
    return keys


def append_signal_snapshots(
    *,
    normalized_records: Iterable[Dict[str, object]],
    run_id: str,
    history_root: str | Path = "data/history/signals",
) -> int:
    """Append normalized snapshots to immutable history contracts."""

    ensure_signal_history_contracts(history_root=history_root)
    root = Path(history_root)
    snapshots_path = root / "signal_snapshots.csv"
    history_path = root / "signal_snapshot_history.csv"
    lineage_path = root / "signal_lineage_registry.csv"

    records = [dict(record) for record in normalized_records]
    if not records:
        return 0

    existing = _existing_snapshot_keys(snapshot_path=snapshots_path)
    now_ts = datetime.now(timezone.utc).isoformat()

    snapshot_rows: List[Dict[str, object]] = []
    history_rows: List[Dict[str, object]] = []
    lineage_rows: List[Dict[str, object]] = []

    for index, record in enumerate(records, start=1):
        snapshot_key = (
            str(record.get("snapshot_date", "")),
            str(run_id),
            str(record.get("provider", "")),
            str(record.get("source_file", "")),
            str(record.get("symbol", "")),
            str(record.get("coverage_domain", "")),
        )
        if snapshot_key in existing:
            raise ValueError(
                "Immutable snapshot protection triggered: duplicate snapshot key detected "
                f"for symbol {record.get('symbol')} in run {run_id}."
            )

        snapshot_row = {
            "snapshot_date": record.get("snapshot_date"),
            "run_id": run_id,
            "provider": record.get("provider"),
            "source_file": record.get("source_file"),
            "symbol": record.get("symbol"),
            "coverage_domain": record.get("coverage_domain"),
            "signal_coverage_status": record.get("signal_coverage_status"),
            "starmine_ess_text": record.get("starmine_ess_text"),
            "starmine_ess_numeric": record.get("starmine_ess_numeric"),
            "starmine_ess_numeric_estimated": record.get("starmine_ess_numeric_estimated"),
            "starmine_ess_source_type": record.get("starmine_ess_source_type"),
        }
        snapshot_rows.append(snapshot_row)

        history_rows.append(
            {
                "history_event_id": f"{run_id}:APPEND:{index}",
                "snapshot_date": record.get("snapshot_date"),
                "run_id": run_id,
                "provider": record.get("provider"),
                "source_file": record.get("source_file"),
                "coverage_domain": record.get("coverage_domain"),
                "event_type": "APPEND",
                "event_ts_utc": now_ts,
            }
        )

        lineage_rows.append(
            {
                "lineage_id": (
                    f"{run_id}:{record.get('snapshot_date')}:{record.get('symbol')}:{record.get('coverage_domain')}"
                ),
                "snapshot_date": record.get("snapshot_date"),
                "run_id": run_id,
                "provider": record.get("provider"),
                "source_file": record.get("source_file"),
                "symbol": record.get("symbol"),
                "coverage_domain": record.get("coverage_domain"),
                "normalization_version": "1",
                "lineage_notes": (
                    "Immutable append from ESS normalization output; numeric provenance preserved."
                ),
            }
        )

    with snapshots_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SNAPSHOT_HEADERS)
        writer.writerows(snapshot_rows)

    with history_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HISTORY_HEADERS)
        writer.writerows(history_rows)

    with lineage_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LINEAGE_HEADERS)
        writer.writerows(lineage_rows)

    return len(snapshot_rows)
