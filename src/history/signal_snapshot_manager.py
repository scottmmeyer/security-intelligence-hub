"""Partitioned immutable signal snapshot storage manager."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

SNAPSHOT_HEADERS = [
    "snapshot_date",
    "created_at_utc",
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

LINEAGE_HEADERS = [
    "lineage_id",
    "snapshot_date",
    "created_at_utc",
    "run_id",
    "provider",
    "source_file",
    "symbol",
    "coverage_domain",
    "normalization_version",
    "lineage_notes",
]

SIGNAL_INDEX_HEADERS = [
    "snapshot_date",
    "run_id",
    "created_at_utc",
    "partition_path",
    "signal_snapshots_path",
    "signal_lineage_registry_path",
    "row_count",
    "provider_count",
    "source_file_count",
]


@dataclass(frozen=True)
class SignalStoragePaths:
    current_signal_snapshot_path: Path
    partition_dir: Path
    partition_signal_snapshots_path: Path
    partition_signal_lineage_path: Path
    index_path: Path


def _ensure_file_with_headers(path: Path, headers: List[str]) -> None:
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            existing_headers = next(reader, [])

        if not existing_headers:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
            return

        if existing_headers != headers:
            raise ValueError(
                f"Signal contract header mismatch for {path}: "
                f"expected {headers}, observed {existing_headers}."
            )
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()


def build_signal_storage_paths(
    *,
    snapshot_date: str,
    run_id: str,
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/signals",
    index_path: str | Path = "data/history/signal_index.csv",
) -> SignalStoragePaths:
    current_root_path = Path(current_root)
    history_root_path = Path(history_root)
    partition_dir = history_root_path / f"snapshot_date={snapshot_date}" / f"run_id={run_id}"

    return SignalStoragePaths(
        current_signal_snapshot_path=current_root_path / "signal_snapshot.csv",
        partition_dir=partition_dir,
        partition_signal_snapshots_path=partition_dir / "signal_snapshots.csv",
        partition_signal_lineage_path=partition_dir / "signal_lineage_registry.csv",
        index_path=Path(index_path),
    )


def ensure_signal_history_contracts(
    *,
    current_root: str | Path = "data/current",
    index_path: str | Path = "data/history/signal_index.csv",
) -> None:
    """Ensure current output and index contracts exist with deterministic headers."""

    current_root_path = Path(current_root)
    _ensure_file_with_headers(current_root_path / "signal_snapshot.csv", SNAPSHOT_HEADERS)
    _ensure_file_with_headers(Path(index_path), SIGNAL_INDEX_HEADERS)


def _assert_required_snapshot_fields(record: Dict[str, object], row_number: int) -> None:
    required_fields = ("snapshot_date", "provider", "source_file", "symbol", "coverage_domain")
    missing = [field for field in required_fields if not str(record.get(field, "")).strip()]
    if missing:
        raise ValueError(
            "Canonical signal partition validation failed at row "
            f"{row_number}: missing fields {', '.join(sorted(missing))}."
        )


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv_rows(path: Path, headers: List[str], rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _count_unique(rows: List[Dict[str, object]], key: str) -> int:
    values = {str(row.get(key, "")).strip() for row in rows if str(row.get(key, "")).strip()}
    return len(values)


def _coverage_rank(row: Dict[str, object]) -> int:
    """Higher number = preferred.  STARMINE_COVERED with ESS text ranks highest."""
    domain = str(row.get("coverage_domain") or "").strip()
    ess = str(row.get("starmine_ess_text") or "").strip()
    if domain == "STARMINE_COVERED" and ess:
        return 2
    if ess:
        return 1
    return 0


def _build_merged_snapshot(
    *,
    snapshot_date: str,
    history_root: Path,
    extra_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    """Return a merged, provider-order-independent signal snapshot for *snapshot_date*.

    Collects all persisted partition rows for *snapshot_date* plus *extra_rows*
    (the rows being appended in the current call, whose partition file may not
    yet be readable).  For each symbol keeps the best-quality row (STARMINE_COVERED
    with ESS text > any ESS text > no ESS text), breaking ties by latest
    ``created_at_utc``.
    """
    all_rows: List[Dict[str, object]] = list(extra_rows)

    # Collect rows from all existing partitions for this snapshot_date
    date_dir = history_root / f"snapshot_date={snapshot_date}"
    if date_dir.exists():
        for run_dir in sorted(date_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            snap_file = run_dir / "signal_snapshots.csv"
            if snap_file.exists():
                all_rows.extend(_read_csv_rows(snap_file))

    # Pick best row per symbol
    best: Dict[str, Dict[str, object]] = {}
    for row in all_rows:
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym:
            continue
        existing = best.get(sym)
        if existing is None:
            best[sym] = row
        else:
            r_rank = _coverage_rank(row)
            e_rank = _coverage_rank(existing)
            if r_rank > e_rank:
                best[sym] = row
            elif r_rank == e_rank:
                # Tiebreak: later created_at_utc wins
                if str(row.get("created_at_utc") or "") > str(existing.get("created_at_utc") or ""):
                    best[sym] = row

    return sorted(best.values(), key=lambda r: str(r.get("symbol") or ""))


def append_signal_snapshots(
    *,
    normalized_records: Iterable[Dict[str, object]],
    run_id: str,
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/signals",
    index_path: str | Path = "data/history/signal_index.csv",
) -> int:
    """Persist signal snapshots to current and immutable run partition storage."""

    records = [dict(record) for record in normalized_records]
    if not records:
        return 0

    snapshot_dates = {str(record.get("snapshot_date", "")).strip() for record in records}
    if "" in snapshot_dates:
        raise ValueError("Signal partition write blocked: snapshot_date is required for every row.")
    if len(snapshot_dates) != 1:
        raise ValueError(
            "Signal partition write blocked: mixed snapshot_date values are not allowed "
            f"within a single run partition: {sorted(snapshot_dates)}."
        )
    snapshot_date = next(iter(snapshot_dates))

    ensure_signal_history_contracts(current_root=current_root, index_path=index_path)
    storage_paths = build_signal_storage_paths(
        snapshot_date=snapshot_date,
        run_id=run_id,
        current_root=current_root,
        history_root=history_root,
        index_path=index_path,
    )

    if storage_paths.partition_dir.exists():
        raise ValueError(
            "Immutable signal partition protection triggered: partition already exists for "
            f"run_id={run_id} at {storage_paths.partition_dir}."
        )

    existing_index_rows = _read_csv_rows(storage_paths.index_path)
    if any(str(row.get("run_id", "")) == run_id for row in existing_index_rows):
        raise ValueError(
            "Signal index append blocked: run_id already registered in signal_index.csv "
            f"for run_id={run_id}."
        )

    now_ts = datetime.now(timezone.utc).isoformat()
    seen_keys: set[tuple[str, str, str, str, str, str]] = set()
    snapshot_rows: List[Dict[str, object]] = []
    lineage_rows: List[Dict[str, object]] = []

    for index, record in enumerate(records, start=1):
        _assert_required_snapshot_fields(record, row_number=index)

        snapshot_key = (
            str(record.get("snapshot_date", "")).strip(),
            str(run_id),
            str(record.get("provider", "")).strip(),
            str(record.get("source_file", "")).strip(),
            str(record.get("symbol", "")).strip(),
            str(record.get("coverage_domain", "")).strip(),
        )
        if snapshot_key in seen_keys:
            raise ValueError(
                "Immutable signal partition protection triggered: duplicate run-scoped key for "
                f"symbol={snapshot_key[4]} coverage_domain={snapshot_key[5]}."
            )
        seen_keys.add(snapshot_key)

        snapshot_rows.append(
            {
                "snapshot_date": record.get("snapshot_date"),
                "created_at_utc": now_ts,
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
        )

        lineage_notes = str(
            record.get("lineage_notes")
            or "Immutable partition append from ESS normalization output; numeric provenance preserved."
        )
        normalization_version = str(record.get("normalization_version") or "2")

        lineage_rows.append(
            {
                "lineage_id": (
                    f"{run_id}:{record.get('snapshot_date')}:{record.get('symbol')}:{record.get('coverage_domain')}"
                ),
                "snapshot_date": record.get("snapshot_date"),
                "created_at_utc": now_ts,
                "run_id": run_id,
                "provider": record.get("provider"),
                "source_file": record.get("source_file"),
                "symbol": record.get("symbol"),
                "coverage_domain": record.get("coverage_domain"),
                "normalization_version": normalization_version,
                "lineage_notes": lineage_notes,
            }
        )

    storage_paths.partition_dir.mkdir(parents=True, exist_ok=False)
    _write_csv_rows(storage_paths.partition_signal_snapshots_path, SNAPSHOT_HEADERS, snapshot_rows)
    _write_csv_rows(storage_paths.partition_signal_lineage_path, LINEAGE_HEADERS, lineage_rows)

    # ── Option-A merge: rebuild signal_snapshot.csv from ALL partitions for this
    # snapshot_date so that provider execution order cannot affect coverage results.
    # Rules:
    #   1. Include every partition for the current snapshot_date.
    #   2. For each symbol keep the row whose coverage_domain is STARMINE_COVERED
    #      (with a non-empty ess_text) over any NON_STARMINE_ANALYST row.
    #   3. Among equal-quality rows, keep the one from the most recently created
    #      partition (latest created_at_utc).
    # This produces a deterministic merged view regardless of intake order.
    merged = _build_merged_snapshot(
        snapshot_date=snapshot_date,
        history_root=Path(history_root),
        extra_rows=snapshot_rows,
    )
    _write_csv_rows(storage_paths.current_signal_snapshot_path, SNAPSHOT_HEADERS, merged)

    index_entry = {
        "snapshot_date": snapshot_date,
        "run_id": run_id,
        "created_at_utc": now_ts,
        "partition_path": str(storage_paths.partition_dir),
        "signal_snapshots_path": str(storage_paths.partition_signal_snapshots_path),
        "signal_lineage_registry_path": str(storage_paths.partition_signal_lineage_path),
        "row_count": str(len(snapshot_rows)),
        "provider_count": str(_count_unique(snapshot_rows, "provider")),
        "source_file_count": str(_count_unique(snapshot_rows, "source_file")),
    }

    with storage_paths.index_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SIGNAL_INDEX_HEADERS)
        writer.writerow(index_entry)

    return len(snapshot_rows)
