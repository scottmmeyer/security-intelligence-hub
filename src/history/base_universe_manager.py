"""Partitioned immutable base universe storage manager."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

BASE_UNIVERSE_HEADERS = [
    "symbol",
    "company_name",
    "security_type",
    "geography",
    "market_cap_raw_usd",
    "market_cap_bucket",
    "coverage_domain",
    "starmine_ess_text",
    "provider",
    "source_file",
    "snapshot_date",
    "created_at_utc",
    "run_id",
]

UNIVERSE_LINEAGE_HEADERS = [
    "lineage_id",
    "snapshot_date",
    "created_at_utc",
    "run_id",
    "provider",
    "source_file",
    "symbol",
    "coverage_domain",
    "provider_schema_version",
    "mapped_columns",
    "unmapped_columns",
    "lineage_notes",
]

UNIVERSE_INDEX_HEADERS = [
    "snapshot_date",
    "run_id",
    "created_at_utc",
    "partition_path",
    "base_equity_universe_path",
    "universe_lineage_registry_path",
    "row_count",
    "provider_count",
    "source_file_count",
]


@dataclass(frozen=True)
class BaseUniverseStoragePaths:
    current_base_universe_path: Path
    partition_dir: Path
    partition_base_universe_path: Path
    partition_lineage_registry_path: Path
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
                f"Base universe contract header mismatch for {path}: "
                f"expected {headers}, observed {existing_headers}."
            )
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()


def build_base_universe_storage_paths(
    *,
    snapshot_date: str,
    run_id: str,
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/universe",
    index_path: str | Path = "data/history/universe_index.csv",
) -> BaseUniverseStoragePaths:
    current_root_path = Path(current_root)
    history_root_path = Path(history_root)
    partition_dir = history_root_path / f"snapshot_date={snapshot_date}" / f"run_id={run_id}"

    return BaseUniverseStoragePaths(
        current_base_universe_path=current_root_path / "base_equity_universe.csv",
        partition_dir=partition_dir,
        partition_base_universe_path=partition_dir / "base_equity_universe.csv",
        partition_lineage_registry_path=partition_dir / "universe_lineage_registry.csv",
        index_path=Path(index_path),
    )


def ensure_base_universe_contracts(
    *,
    current_root: str | Path = "data/current",
    index_path: str | Path = "data/history/universe_index.csv",
) -> None:
    """Ensure current output and index contracts exist with deterministic headers."""

    current_root_path = Path(current_root)
    _ensure_file_with_headers(current_root_path / "base_equity_universe.csv", BASE_UNIVERSE_HEADERS)
    _ensure_file_with_headers(Path(index_path), UNIVERSE_INDEX_HEADERS)


def _assert_required_partition_fields(record: Dict[str, object], row_number: int) -> None:
    required_fields = (
        "snapshot_date",
        "provider",
        "source_file",
        "symbol",
        "coverage_domain",
    )
    missing = [field for field in required_fields if not str(record.get(field, "")).strip()]
    if missing:
        raise ValueError(
            "Canonical base-universe partition validation failed at row "
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


def append_base_universe_rows(
    *,
    base_rows: Iterable[Dict[str, object]],
    run_id: str,
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/universe",
    index_path: str | Path = "data/history/universe_index.csv",
) -> int:
    """Persist base universe rows to current and immutable run partition storage."""

    records = [dict(record) for record in base_rows]
    if not records:
        return 0

    snapshot_dates = {str(record.get("snapshot_date", "")).strip() for record in records}
    if "" in snapshot_dates:
        raise ValueError("Base universe partition write blocked: snapshot_date is required for every row.")
    if len(snapshot_dates) != 1:
        raise ValueError(
            "Base universe partition write blocked: mixed snapshot_date values are not allowed "
            f"within a single run partition: {sorted(snapshot_dates)}."
        )
    snapshot_date = next(iter(snapshot_dates))

    ensure_base_universe_contracts(current_root=current_root, index_path=index_path)
    storage_paths = build_base_universe_storage_paths(
        snapshot_date=snapshot_date,
        run_id=run_id,
        current_root=current_root,
        history_root=history_root,
        index_path=index_path,
    )

    if storage_paths.partition_dir.exists():
        raise ValueError(
            "Immutable base-universe partition protection triggered: partition already exists for "
            f"run_id={run_id} at {storage_paths.partition_dir}."
        )

    existing_index_rows = _read_csv_rows(storage_paths.index_path)
    if any(str(row.get("run_id", "")) == run_id for row in existing_index_rows):
        raise ValueError(
            "Base universe index append blocked: run_id already registered in universe_index.csv "
            f"for run_id={run_id}."
        )

    now_ts = datetime.now(timezone.utc).isoformat()
    seen_keys: set[tuple[str, str, str, str, str, str]] = set()
    universe_rows: List[Dict[str, object]] = []
    lineage_rows: List[Dict[str, object]] = []

    for index, record in enumerate(records, start=1):
        _assert_required_partition_fields(record, row_number=index)

        partition_key = (
            str(record.get("snapshot_date", "")).strip(),
            str(run_id),
            str(record.get("provider", "")).strip(),
            str(record.get("source_file", "")).strip(),
            str(record.get("symbol", "")).strip(),
            str(record.get("coverage_domain", "")).strip(),
        )
        if partition_key in seen_keys:
            raise ValueError(
                "Immutable base-universe partition protection triggered: duplicate run-scoped key for "
                f"symbol={partition_key[4]} coverage_domain={partition_key[5]}."
            )
        seen_keys.add(partition_key)

        universe_row = {
            "symbol": record.get("symbol"),
            "company_name": record.get("company_name"),
            "security_type": record.get("security_type"),
            "geography": record.get("geography"),
            "market_cap_raw_usd": record.get("market_cap_raw_usd"),
            "market_cap_bucket": record.get("market_cap_bucket"),
            "coverage_domain": record.get("coverage_domain"),
            "starmine_ess_text": record.get("starmine_ess_text"),
            "provider": record.get("provider"),
            "source_file": record.get("source_file"),
            "snapshot_date": record.get("snapshot_date"),
            "created_at_utc": now_ts,
            "run_id": run_id,
        }
        universe_rows.append(universe_row)

        column_lineage = record.get("provider_column_lineage")
        mapped_columns = ""
        if isinstance(column_lineage, dict):
            mapped_columns = "|".join(sorted(str(column_key) for column_key in column_lineage.keys()))

        unmapped_columns_raw = record.get("unmapped_provider_columns")
        unmapped_columns = ""
        if isinstance(unmapped_columns_raw, list):
            unmapped_columns = "|".join(sorted(str(item) for item in unmapped_columns_raw))

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
                "provider_schema_version": record.get("provider_schema_version", "UNKNOWN"),
                "mapped_columns": mapped_columns,
                "unmapped_columns": unmapped_columns,
                "lineage_notes": "Provider-native Fidelity columns mapped to canonical base universe fields.",
            }
        )

    storage_paths.partition_dir.mkdir(parents=True, exist_ok=False)
    _write_csv_rows(storage_paths.partition_base_universe_path, BASE_UNIVERSE_HEADERS, universe_rows)
    _write_csv_rows(storage_paths.partition_lineage_registry_path, UNIVERSE_LINEAGE_HEADERS, lineage_rows)
    _write_csv_rows(storage_paths.current_base_universe_path, BASE_UNIVERSE_HEADERS, universe_rows)

    index_entry = {
        "snapshot_date": snapshot_date,
        "run_id": run_id,
        "created_at_utc": now_ts,
        "partition_path": str(storage_paths.partition_dir),
        "base_equity_universe_path": str(storage_paths.partition_base_universe_path),
        "universe_lineage_registry_path": str(storage_paths.partition_lineage_registry_path),
        "row_count": str(len(universe_rows)),
        "provider_count": str(_count_unique(universe_rows, "provider")),
        "source_file_count": str(_count_unique(universe_rows, "source_file")),
    }

    with storage_paths.index_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=UNIVERSE_INDEX_HEADERS)
        writer.writerow(index_entry)

    return len(universe_rows)
