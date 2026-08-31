"""Operational daily wrapper for annual FMP estimate PIT snapshots."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

import fcntl

from src.history.fmp_estimate_backfill import DEFAULT_BATCH_SIZE, run_fmp_estimate_backfill


DEFAULT_CHECKPOINT_TEMPLATE = "data/runtime/checkpoints/fmp_annual_estimate_{snapshot_date}.json"
DEFAULT_REPORT_TEMPLATE = "data/runtime/reports/fmp_annual_estimate_{snapshot_date}.json"
DEFAULT_LOCK_TEMPLATE = "data/runtime/locks/fmp_annual_estimate_{snapshot_date}.lock"
DEFAULT_DISCOVERY_INDEX = "data/runtime/reports/fmp_annual_estimate_snapshot_index.json"
DEFAULT_PERIODS = ("annual",)


@dataclass(frozen=True)
class SnapshotPaths:
    checkpoint_path: Path
    report_path: Path
    lock_path: Path
    discovery_index_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot_date(value: str | None) -> str:
    if value:
        return str(value).strip()
    return date.today().isoformat()


def _is_weekday(snapshot_date: str) -> bool:
    dt = date.fromisoformat(snapshot_date)
    return dt.weekday() < 5


def _resolve_paths(repo_root: Path, snapshot_date: str) -> SnapshotPaths:
    checkpoint = repo_root / DEFAULT_CHECKPOINT_TEMPLATE.format(snapshot_date=snapshot_date)
    report = repo_root / DEFAULT_REPORT_TEMPLATE.format(snapshot_date=snapshot_date)
    lock = repo_root / DEFAULT_LOCK_TEMPLATE.format(snapshot_date=snapshot_date)
    discovery = repo_root / DEFAULT_DISCOVERY_INDEX
    return SnapshotPaths(
        checkpoint_path=checkpoint,
        report_path=report,
        lock_path=lock,
        discovery_index_path=discovery,
    )


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        tmp_path = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


def _determine_action(
    *,
    checkpoint: dict[str, Any] | None,
    report: dict[str, Any] | None,
    force: bool,
) -> str:
    report_status = str((report or {}).get("status") or "").upper()
    checkpoint_status = str((checkpoint or {}).get("status") or "").upper()

    if not force and report_status == "COMPLETE":
        return "SKIP_ALREADY_COMPLETE"
    if not force and checkpoint_status == "COMPLETE":
        return "SKIP_ALREADY_COMPLETE"

    if checkpoint is not None:
        return "RESUME"
    return "START_NEW"


@contextmanager
def _file_lock(lock_path: Path, *, blocking: bool = False) -> Iterator[bool]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), flags)
            acquired = True
        except BlockingIOError:
            acquired = False
        try:
            yield acquired
        finally:
            if acquired:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _build_health(
    *,
    snapshot_date: str,
    action: str,
    status: str,
    run_result: dict[str, Any] | None,
    checkpoint: dict[str, Any] | None,
    report: dict[str, Any] | None,
    paths: SnapshotPaths,
) -> dict[str, Any]:
    source = run_result or report or checkpoint or {}

    def _coerce_count(value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, (list, tuple, set, dict)):
            return len(value)
        text = str(value).strip()
        if not text:
            return 0
        try:
            return int(float(text))
        except Exception:
            return 0

    symbols_with_data = _coerce_count(
        source.get("symbols_with_data_count")
        if source.get("symbols_with_data_count") is not None
        else source.get("symbols_with_data")
    )
    symbols_no_coverage = _coerce_count(
        source.get("no_coverage_count")
        if source.get("no_coverage_count") is not None
        else source.get("symbols_no_coverage")
        if source.get("symbols_no_coverage") is not None
        else source.get("no_coverage_symbols")
    )
    symbols_failed = _coerce_count(
        source.get("failed_count")
        if source.get("failed_count") is not None
        else source.get("symbols_failed")
        if source.get("symbols_failed") is not None
        else source.get("failed_symbols")
    )
    universe_count = int(source.get("universe_count") or 0)
    total_accounted = symbols_with_data + symbols_no_coverage + symbols_failed
    unaccounted = max(universe_count - total_accounted, 0) if universe_count else 0

    completed_at = str(source.get("completed_at_utc") or "")
    started_at = str(source.get("started_at_utc") or "")

    return {
        "snapshot_date": snapshot_date,
        "status": status,
        "action": action,
        "run_id": str(source.get("run_id") or ""),
        "requested_periods": list(source.get("requested_periods") or []),
        "checkpoint_path": str(paths.checkpoint_path),
        "report_path": str(paths.report_path),
        "universe_count": universe_count,
        "universe_hash": str(source.get("universe_hash") or ""),
        "symbols_with_data": symbols_with_data,
        "symbols_no_coverage": symbols_no_coverage,
        "symbols_failed": symbols_failed,
        "total_accounted": total_accounted,
        "unaccounted_symbols": unaccounted,
        "batches_total": int(source.get("total_batches") or 0),
        "batches_completed": int(source.get("current_batch") or source.get("completed_batches") or 0),
        "estimate_rows_fetched": int(source.get("estimate_rows_fetched") or 0),
        "pit_observations_written": int(source.get("pit_observations_written") or 0),
        "pit_duplicates_skipped": int(source.get("pit_duplicates_skipped") or 0),
        "provider_duplicate_rows_detected": int(source.get("provider_duplicate_rows_detected") or 0),
        "provider_duplicate_rows_collapsed": int(source.get("provider_duplicate_rows_collapsed") or 0),
        "provider_duplicate_conflict_key_count": int(source.get("provider_duplicate_conflict_key_count") or 0),
        "rate_limit_events": int(source.get("rate_limit_events") or 0),
        "retries_performed": int(source.get("retries_performed") or 0),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "updated_at_utc": _utc_now(),
    }


def _update_discovery_index(index_path: Path, entry: dict[str, Any], *, max_entries: int = 30) -> None:
    payload = _read_json(index_path) or {}
    items = list(payload.get("captures") or [])
    snapshot_date = str(entry.get("snapshot_date") or "")
    items = [x for x in items if str((x or {}).get("snapshot_date") or "") != snapshot_date]
    items.insert(0, dict(entry))
    payload = {
        "captures": items[:max_entries],
        "updated_at_utc": _utc_now(),
    }
    _write_json_atomic(index_path, payload)


def discover_recent_captures(
    *,
    repo_root: str | Path = ".",
    limit: int = 10,
) -> dict[str, object]:
    root = Path(repo_root)
    index_path = root / DEFAULT_DISCOVERY_INDEX
    payload = _read_json(index_path) or {"captures": [], "updated_at_utc": ""}
    captures = list(payload.get("captures") or [])[: max(int(limit), 0)]
    return {
        "captures": captures,
        "updated_at_utc": str(payload.get("updated_at_utc") or ""),
        "index_path": str(index_path),
    }


def run_daily_fmp_annual_snapshot(
    *,
    repo_root: str | Path = ".",
    snapshot_date: str | None = None,
    symbols: Sequence[str] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    force: bool = False,
    allow_non_trading_day: bool = False,
    dry_run: bool = False,
    max_batches: int | None = None,
    run_backfill: Callable[..., dict[str, object]] = run_fmp_estimate_backfill,
) -> dict[str, object]:
    root = Path(repo_root)
    as_of = _snapshot_date(snapshot_date)
    paths = _resolve_paths(root, as_of)

    if not allow_non_trading_day and not _is_weekday(as_of):
        health = {
            "snapshot_date": as_of,
            "status": "SKIPPED_NON_TRADING_DAY",
            "action": "SKIP_NON_TRADING_DAY",
            "run_id": "",
            "requested_periods": list(DEFAULT_PERIODS),
            "checkpoint_path": str(paths.checkpoint_path),
            "report_path": str(paths.report_path),
            "universe_count": 0,
            "universe_hash": "",
            "symbols_with_data": 0,
            "symbols_no_coverage": 0,
            "symbols_failed": 0,
            "total_accounted": 0,
            "unaccounted_symbols": 0,
            "batches_total": 0,
            "batches_completed": 0,
            "estimate_rows_fetched": 0,
            "pit_observations_written": 0,
            "pit_duplicates_skipped": 0,
            "provider_duplicate_rows_detected": 0,
            "provider_duplicate_rows_collapsed": 0,
            "provider_duplicate_conflict_key_count": 0,
            "rate_limit_events": 0,
            "retries_performed": 0,
            "started_at_utc": "",
            "completed_at_utc": "",
            "updated_at_utc": _utc_now(),
        }
        _write_json_atomic(paths.report_path, health)
        _update_discovery_index(paths.discovery_index_path, health)
        return health

    with _file_lock(paths.lock_path, blocking=False) as acquired:
        if not acquired:
            health = {
                "snapshot_date": as_of,
                "status": "BLOCKED_ACTIVE_RUN",
                "action": "BLOCKED_ACTIVE_RUN",
                "run_id": "",
                "requested_periods": list(DEFAULT_PERIODS),
                "checkpoint_path": str(paths.checkpoint_path),
                "report_path": str(paths.report_path),
                "universe_count": 0,
                "universe_hash": "",
                "symbols_with_data": 0,
                "symbols_no_coverage": 0,
                "symbols_failed": 0,
                "total_accounted": 0,
                "unaccounted_symbols": 0,
                "batches_total": 0,
                "batches_completed": 0,
                "estimate_rows_fetched": 0,
                "pit_observations_written": 0,
                "pit_duplicates_skipped": 0,
                "provider_duplicate_rows_detected": 0,
                "provider_duplicate_rows_collapsed": 0,
                "provider_duplicate_conflict_key_count": 0,
                "rate_limit_events": 0,
                "retries_performed": 0,
                "started_at_utc": "",
                "completed_at_utc": "",
                "updated_at_utc": _utc_now(),
            }
            _write_json_atomic(paths.report_path, health)
            _update_discovery_index(paths.discovery_index_path, health)
            return health

        checkpoint = _read_json(paths.checkpoint_path)
        report = _read_json(paths.report_path)
        action = _determine_action(checkpoint=checkpoint, report=report, force=force)

        if action == "SKIP_ALREADY_COMPLETE":
            health = _build_health(
                snapshot_date=as_of,
                action=action,
                status="ALREADY_COMPLETE",
                run_result=None,
                checkpoint=checkpoint,
                report=report,
                paths=paths,
            )
            _write_json_atomic(paths.report_path, health)
            _update_discovery_index(paths.discovery_index_path, health)
            return health

        run_result = run_backfill(
            repo_root=root,
            research_universe=not bool(symbols),
            symbols=list(symbols) if symbols else None,
            requested_periods=list(DEFAULT_PERIODS),
            batch_size=int(batch_size),
            checkpoint_path=paths.checkpoint_path,
            resume=(action == "RESUME"),
            dry_run=bool(dry_run),
            report_path=paths.report_path,
            snapshot_date=as_of,
            max_batches=max_batches,
        )
        checkpoint_after = _read_json(paths.checkpoint_path)
        report_after = _read_json(paths.report_path)

        run_status = str(run_result.get("status") or "").upper()
        status = "IN_PROGRESS"
        if run_status == "COMPLETE":
            status = "COMPLETE"
        elif run_status == "IN_PROGRESS":
            status = "IN_PROGRESS"
        elif run_status:
            status = run_status

        health = _build_health(
            snapshot_date=as_of,
            action=action,
            status=status,
            run_result=run_result,
            checkpoint=checkpoint_after,
            report=report_after,
            paths=paths,
        )

        if health["status"] == "COMPLETE" and int(health.get("unaccounted_symbols") or 0) > 0:
            health["status"] = "FAILED_ACCOUNTING"

        _write_json_atomic(paths.report_path, health)
        _update_discovery_index(paths.discovery_index_path, health)
        return health