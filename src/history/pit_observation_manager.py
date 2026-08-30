"""Append-only point-in-time provider observation storage manager."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

PIT_OBSERVATION_HEADERS = [
    "provider",
    "symbol",
    "snapshot_date",
    "sourced_date",
    "retrieved_at_utc",
    "run_id",
    "metric",
    "value",
    "forecast_horizon",
    "fiscal_period",
    "source_provenance",
    "value_type",
    "currency",
    "unit",
    "provider_field_name",
    "source_endpoint",
    "observation_id",
]

PIT_INDEX_HEADERS = [
    "snapshot_date",
    "run_id",
    "provider",
    "created_at_utc",
    "partition_path",
    "observations_path",
    "row_count",
    "symbol_count",
]


@dataclass(frozen=True)
class PitStoragePaths:
    partition_dir: Path
    observations_path: Path
    index_path: Path


@dataclass(frozen=True)
class PitAppendResult:
    attempted: int
    written: int
    skipped_duplicate: int


def _ensure_file_with_headers(path: Path, headers: List[str]) -> None:
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            existing_headers = next(reader, [])
        if existing_headers and existing_headers != headers:
            raise ValueError(
                f"PIT contract header mismatch for {path}: expected {headers}, observed {existing_headers}."
            )
        if existing_headers:
            return

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()


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


def build_pit_storage_paths(
    *,
    snapshot_date: str,
    run_id: str,
    provider: str,
    history_root: str | Path = "data/history/pit_observations",
    index_path: str | Path = "data/history/pit_observation_index.csv",
) -> PitStoragePaths:
    history_root_path = Path(history_root)
    partition_dir = (
        history_root_path
        / f"snapshot_date={snapshot_date}"
        / f"run_id={run_id}"
        / f"provider={provider}"
    )
    return PitStoragePaths(
        partition_dir=partition_dir,
        observations_path=partition_dir / "observations.csv",
        index_path=Path(index_path),
    )


def ensure_pit_observation_contracts(
    *,
    index_path: str | Path = "data/history/pit_observation_index.csv",
) -> None:
    _ensure_file_with_headers(Path(index_path), PIT_INDEX_HEADERS)


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _observation_identity(record: Dict[str, object]) -> tuple[str, ...]:
    return (
        _normalize_text(record.get("provider")).upper(),
        _normalize_text(record.get("symbol")).upper(),
        _normalize_text(record.get("snapshot_date")),
        _normalize_text(record.get("run_id")),
        _normalize_text(record.get("metric")),
        _normalize_text(record.get("forecast_horizon")),
        _normalize_text(record.get("fiscal_period")),
        _normalize_text(record.get("source_provenance")),
    )


def _observation_id(record: Dict[str, object]) -> str:
    parts = _observation_identity(record)
    return "|".join(parts)


def _assert_required_fields(record: Dict[str, object], row_number: int) -> None:
    required = ("provider", "symbol", "snapshot_date", "retrieved_at_utc", "run_id", "metric")
    missing = [f for f in required if not _normalize_text(record.get(f))]
    if missing:
        raise ValueError(
            f"PIT observation validation failed at row {row_number}: missing fields {', '.join(sorted(missing))}."
        )


def append_pit_observations(
    *,
    observations: Iterable[Dict[str, object]],
    provider: str,
    snapshot_date: str,
    run_id: str,
    history_root: str | Path = "data/history/pit_observations",
    index_path: str | Path = "data/history/pit_observation_index.csv",
) -> PitAppendResult:
    rows = [dict(item) for item in observations]
    if not rows:
        return PitAppendResult(attempted=0, written=0, skipped_duplicate=0)

    provider_name = _normalize_text(provider).upper()
    if not provider_name:
        raise ValueError("PIT append blocked: provider is required.")

    normalized: List[Dict[str, object]] = []
    seen_in_batch: set[tuple[str, ...]] = set()

    for row_number, row in enumerate(rows, start=1):
        record = {
            "provider": provider_name,
            "symbol": _normalize_text(row.get("symbol")).upper(),
            "snapshot_date": _normalize_text(row.get("snapshot_date") or snapshot_date),
            "sourced_date": _normalize_text(row.get("sourced_date")) or "UNAVAILABLE",
            "retrieved_at_utc": _normalize_text(row.get("retrieved_at_utc")),
            "run_id": _normalize_text(row.get("run_id") or run_id),
            "metric": _normalize_text(row.get("metric")),
            "value": _normalize_text(row.get("value")),
            "forecast_horizon": _normalize_text(row.get("forecast_horizon")) or "UNSPECIFIED",
            "fiscal_period": _normalize_text(row.get("fiscal_period")) or "UNSPECIFIED",
            "source_provenance": _normalize_text(row.get("source_provenance")) or "UNSPECIFIED",
            "value_type": _normalize_text(row.get("value_type")) or "UNSPECIFIED",
            "currency": _normalize_text(row.get("currency")) or "UNSPECIFIED",
            "unit": _normalize_text(row.get("unit")) or "UNSPECIFIED",
            "provider_field_name": _normalize_text(row.get("provider_field_name")) or "UNSPECIFIED",
            "source_endpoint": _normalize_text(row.get("source_endpoint")) or "UNSPECIFIED",
        }
        _assert_required_fields(record, row_number=row_number)

        identity = _observation_identity(record)
        if identity in seen_in_batch:
            continue
        seen_in_batch.add(identity)
        record["observation_id"] = _observation_id(record)
        normalized.append(record)

    if not normalized:
        return PitAppendResult(attempted=len(rows), written=0, skipped_duplicate=len(rows))

    for record in normalized:
        if record["snapshot_date"] != snapshot_date:
            raise ValueError(
                "PIT append blocked: mixed snapshot_date values are not allowed "
                f"within one provider append (expected {snapshot_date}, found {record['snapshot_date']})."
            )
        if record["run_id"] != run_id:
            raise ValueError(
                "PIT append blocked: mixed run_id values are not allowed "
                f"within one provider append (expected {run_id}, found {record['run_id']})."
            )
        if record["provider"] != provider_name:
            raise ValueError(
                "PIT append blocked: mixed provider values are not allowed "
                f"within one provider append (expected {provider_name}, found {record['provider']})."
            )

    ensure_pit_observation_contracts(index_path=index_path)
    paths = build_pit_storage_paths(
        snapshot_date=snapshot_date,
        run_id=run_id,
        provider=provider_name,
        history_root=history_root,
        index_path=index_path,
    )

    existing_index_rows = _read_csv_rows(paths.index_path)
    has_index_entry = any(
        _normalize_text(r.get("snapshot_date")) == snapshot_date
        and _normalize_text(r.get("run_id")) == run_id
        and _normalize_text(r.get("provider")).upper() == provider_name
        for r in existing_index_rows
    )

    if paths.partition_dir.exists() and has_index_entry:
        existing_rows = _read_csv_rows(paths.observations_path)
        existing_ids = {_normalize_text(r.get("observation_id")) for r in existing_rows}
        new_ids = {_normalize_text(r.get("observation_id")) for r in normalized}
        missing = [r for r in normalized if _normalize_text(r.get("observation_id")) not in existing_ids]
        if missing:
            raise ValueError(
                "Immutable PIT partition protection triggered: existing partition is incomplete for "
                f"provider={provider_name}, run_id={run_id}, snapshot_date={snapshot_date}."
            )
        return PitAppendResult(attempted=len(rows), written=0, skipped_duplicate=len(new_ids))

    if paths.partition_dir.exists() != has_index_entry:
        raise ValueError(
            "PIT index/partition consistency error: partition presence does not match index entry for "
            f"provider={provider_name}, run_id={run_id}, snapshot_date={snapshot_date}."
        )

    paths.partition_dir.mkdir(parents=True, exist_ok=False)
    _write_csv_rows(paths.observations_path, PIT_OBSERVATION_HEADERS, normalized)

    index_entry = {
        "snapshot_date": snapshot_date,
        "run_id": run_id,
        "provider": provider_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "partition_path": str(paths.partition_dir),
        "observations_path": str(paths.observations_path),
        "row_count": str(len(normalized)),
        "symbol_count": str(_count_unique(normalized, "symbol")),
    }

    with paths.index_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PIT_INDEX_HEADERS)
        writer.writerow(index_entry)

    return PitAppendResult(attempted=len(rows), written=len(normalized), skipped_duplicate=0)


def _parse_iso_utc(value: str) -> datetime | None:
    raw = _normalize_text(value)
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def query_pit_observations(
    *,
    symbol: str,
    cutoff_retrieved_at_utc: str,
    provider: str | None = None,
    metric: str | None = None,
    latest_only: bool = False,
    history_root: str | Path = "data/history/pit_observations",
) -> List[Dict[str, str]]:
    symbol_key = _normalize_text(symbol).upper()
    if not symbol_key:
        raise ValueError("PIT query requires a symbol.")

    cutoff_dt = _parse_iso_utc(cutoff_retrieved_at_utc)
    if cutoff_dt is None:
        raise ValueError("PIT query requires a valid cutoff_retrieved_at_utc ISO timestamp.")

    provider_key = _normalize_text(provider).upper() if provider else ""
    metric_key = _normalize_text(metric)

    rows: List[Dict[str, str]] = []
    root = Path(history_root)
    if not root.exists():
        return []

    for observations_path in sorted(root.glob("snapshot_date=*/run_id=*/provider=*/observations.csv")):
        for row in _read_csv_rows(observations_path):
            if _normalize_text(row.get("symbol")).upper() != symbol_key:
                continue
            if provider_key and _normalize_text(row.get("provider")).upper() != provider_key:
                continue
            if metric_key and _normalize_text(row.get("metric")) != metric_key:
                continue
            retrieved_dt = _parse_iso_utc(_normalize_text(row.get("retrieved_at_utc")))
            if retrieved_dt is None:
                continue
            if retrieved_dt <= cutoff_dt:
                rows.append(row)

    rows.sort(key=lambda r: _normalize_text(r.get("retrieved_at_utc")))

    if not latest_only:
        return rows

    latest_by_key: Dict[tuple[str, str, str], Dict[str, str]] = {}
    for row in rows:
        key = (
            _normalize_text(row.get("provider")).upper(),
            _normalize_text(row.get("metric")),
            _normalize_text(row.get("forecast_horizon")) + "|" + _normalize_text(row.get("fiscal_period")),
        )
        latest_by_key[key] = row

    return sorted(latest_by_key.values(), key=lambda r: _normalize_text(r.get("retrieved_at_utc")))
