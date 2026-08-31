"""Resumable FMP analyst-estimate backfill orchestration.

This module provides controlled, checkpointed annual-estimate accumulation for
research-universe scale runs without changing normal refresh semantics.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from uuid import uuid4

from src.history.pit_observation_manager import append_pit_observations
from src.scoring.fetch_fmp_signals import (
    ANALYST_ESTIMATES_HEADERS,
    _get_api_key,
    fetch_analyst_estimates_with_meta,
)

CHECKPOINT_VERSION = 1
DEFAULT_BATCH_SIZE = 50
DEFAULT_CHECKPOINT_PATH = "data/runtime/checkpoints/fmp_annual_estimate_backfill_checkpoint.json"
DEFAULT_RUNS_ROOT = "data/runtime/fmp_estimate_backfill"
DEFAULT_REQUESTED_PERIODS = ("annual",)
DEFAULT_ESTIMATE_LIMIT = 8
DEFAULT_DELAY_SECONDS = 0.25

CANONICAL_RESULT_KEY_FIELDS = ("provider", "symbol", "request_period", "period_date")
CONFLICT_FAILURE_TYPE = "FMP_DUPLICATE_CONFLICT"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_symbol(value: object) -> str:
    return str(value or "").strip().upper()


def _normalize_periods(periods: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for period in periods:
        p = str(period or "").strip().lower()
        if not p:
            continue
        if p not in {"annual", "quarter"}:
            raise ValueError(f"Invalid requested period: {period}")
        if p not in normalized:
            normalized.append(p)
    if not normalized:
        raise ValueError("At least one requested period is required")
    return normalized


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv_atomic(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=str(path.parent), delete=False) as handle:
        tmp_path = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        tmp_path = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    tmp_path.replace(path)


def _load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _resolve_research_universe_symbols(repo_root: Path) -> list[str]:
    universe_path = repo_root / "data/current/base_equity_universe.csv"
    rows = _read_csv_rows(universe_path)
    resolved: list[str] = []
    seen: set[str] = set()
    for row in rows:
        symbol = _normalize_symbol(row.get("symbol"))
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        resolved.append(symbol)
    return resolved


def _resolve_explicit_symbols(symbols: Sequence[str]) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        symbol = _normalize_symbol(raw)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        resolved.append(symbol)
    return resolved


def _universe_hash(symbols: Sequence[str]) -> str:
    canonical = "\n".join(sorted(_normalize_symbol(sym) for sym in symbols if _normalize_symbol(sym)))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _partition_symbols(symbols: Sequence[str], batch_size: int) -> list[list[str]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    out: list[list[str]] = []
    values = list(symbols)
    for start in range(0, len(values), batch_size):
        out.append(values[start : start + batch_size])
    return out


def _failure_class(failure_type: str) -> str:
    ft = str(failure_type or "").strip().upper()
    if ft == "RATE_LIMIT":
        return "RATE_LIMIT"
    if ft == "PLAN_LIMIT":
        return "PLAN_LIMIT"
    if ft == "PARSE_FAILURE":
        return "PARSE_FAILURE"
    if ft in {"NETWORK_ERROR", "HTTP_ERROR", "UPSTREAM_UNAVAILABLE", "AUTH", "FORBIDDEN", "NOT_FOUND"}:
        return "REQUEST_FAILURE"
    return "OTHER"


def _retry_eligible(failure_class: str) -> bool:
    return failure_class in {"REQUEST_FAILURE", "RATE_LIMIT"}


def _build_pit_observations(
    *,
    rows: Sequence[dict[str, str]],
    symbol: str,
    snapshot_date: str,
    retrieved_at_utc: str,
    run_id: str,
) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for row in rows:
        if _normalize_symbol(row.get("symbol")) != symbol:
            continue
        if str(row.get("fetch_status") or "").strip().upper() != "SUCCESS":
            continue
        period_date = str(row.get("period_date") or "").strip()
        period_label = str(row.get("period_label") or "").strip()
        request_period = str(row.get("request_period") or "").strip().lower()
        sourced_date = str(row.get("sourced_date") or "").strip() or "UNAVAILABLE"
        fiscal_period = str(row.get("fiscal_period") or "").strip() or "UNSPECIFIED"
        forecast_horizon = str(row.get("forecast_horizon") or "").strip() or "UNSPECIFIED"

        source_endpoint = "/stable/analyst-estimates"
        if request_period:
            source_endpoint += f" period={request_period}"
        if period_date:
            source_endpoint += f" period_date={period_date}"
        if period_label:
            source_endpoint += f" period_label={period_label}"

        metrics = (
            ("estimated_eps_avg", "eps_estimate_avg", "NUMBER", "USD", "EPS"),
            ("estimated_eps_high", "eps_estimate_high", "NUMBER", "USD", "EPS"),
            ("estimated_eps_low", "eps_estimate_low", "NUMBER", "USD", "EPS"),
            ("estimated_revenue_avg", "revenue_estimate_avg", "NUMBER", "USD", "REVENUE"),
            ("estimated_revenue_high", "revenue_estimate_high", "NUMBER", "USD", "REVENUE"),
            ("estimated_revenue_low", "revenue_estimate_low", "NUMBER", "USD", "REVENUE"),
            ("analyst_count_eps", "analyst_count_eps", "INTEGER", "COUNT", "ANALYSTS"),
            ("analyst_count_revenue", "analyst_count_revenue", "INTEGER", "COUNT", "ANALYSTS"),
        )
        for field, metric, value_type, unit, currency in metrics:
            value = str(row.get(field) or "").strip()
            if not value:
                continue
            observations.append(
                {
                    "symbol": symbol,
                    "snapshot_date": snapshot_date,
                    "sourced_date": sourced_date,
                    "retrieved_at_utc": retrieved_at_utc,
                    "run_id": run_id,
                    "metric": metric,
                    "value": value,
                    "forecast_horizon": forecast_horizon,
                    "fiscal_period": fiscal_period,
                    "source_provenance": "FMP_ANALYST_ESTIMATES_STABLE",
                    "value_type": value_type,
                    "currency": currency,
                    "unit": unit,
                    "provider_field_name": field,
                    "source_endpoint": source_endpoint,
                }
            )
    return observations


def _symbol_status(rows: Sequence[dict[str, str]]) -> str:
    statuses = {str(row.get("fetch_status") or "").strip().upper() for row in rows}
    if "SUCCESS" in statuses:
        return "SUCCESS"
    if "PROVIDER_NO_DATA" in statuses:
        return "NO_ESTIMATE_COVERAGE"
    if "FETCH_FAILED" in statuses:
        return "FETCH_FAILED"
    return "OTHER"


def _latest_failure_row(rows: Sequence[dict[str, str]]) -> dict[str, str]:
    for row in rows:
        if str(row.get("fetch_status") or "").strip().upper() == "FETCH_FAILED":
            return dict(row)
    return {}


def _symbol_result_path(run_root: Path, symbol: str) -> Path:
    return run_root / "symbol_rows" / f"{symbol}.csv"


def _write_symbol_rows(run_root: Path, symbol: str, rows: list[dict[str, str]]) -> Path:
    path = _symbol_result_path(run_root, symbol)
    _write_csv_atomic(path, ANALYST_ESTIMATES_HEADERS, rows)
    return path


def _read_symbol_rows(run_root: Path, symbol: str) -> list[dict[str, str]]:
    return _read_csv_rows(_symbol_result_path(run_root, symbol))


def _merge_run_rows(run_root: Path, symbols: Sequence[str]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    for symbol in symbols:
        merged.extend(_read_symbol_rows(run_root, symbol))
    return merged


def _canonical_result_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        "FMP",
        _normalize_symbol(row.get("symbol")),
        str(row.get("request_period") or "").strip().lower(),
        str(row.get("period_date") or "").strip(),
    )


def _normalized_row_fingerprint(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(field) or "").strip() for field in ANALYST_ESTIMATES_HEADERS)


def _build_duplicate_conflict_row(
    *,
    key: tuple[str, str, str, str],
    candidate_rows: Sequence[dict[str, str]],
) -> dict[str, str]:
    first = dict(candidate_rows[0]) if candidate_rows else {}
    symbol = key[1]
    request_period = key[2]
    period_date = key[3]
    first["symbol"] = symbol
    first["request_period"] = request_period
    first["period_date"] = period_date
    first["fetch_status"] = "FETCH_FAILED"
    first["failure_type"] = CONFLICT_FAILURE_TYPE
    first["failure_reason"] = (
        "Conflicting provider duplicate rows for canonical key "
        f"symbol={symbol} request_period={request_period} period_date={period_date}"
    )
    for metric_field in (
        "estimated_revenue_avg",
        "estimated_revenue_high",
        "estimated_revenue_low",
        "estimated_eps_avg",
        "estimated_eps_high",
        "estimated_eps_low",
        "analyst_count_revenue",
        "analyst_count_eps",
    ):
        first[metric_field] = ""
    return first


def _canonicalize_rows_for_publication(
    rows: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = _canonical_result_key(row)
        grouped.setdefault(key, []).append(dict(row))

    canonical_rows: list[dict[str, str]] = []
    duplicate_rows_detected = 0
    duplicate_rows_collapsed = 0
    duplicate_conflict_keys: list[dict[str, str]] = []

    for key, candidates in grouped.items():
        if len(candidates) == 1:
            canonical_rows.append(candidates[0])
            continue

        duplicate_rows_detected += len(candidates)
        fingerprints = {_normalized_row_fingerprint(row) for row in candidates}
        if len(fingerprints) == 1:
            canonical_rows.append(candidates[0])
            duplicate_rows_collapsed += len(candidates) - 1
            continue

        duplicate_conflict_keys.append(
            {
                "provider": key[0],
                "symbol": key[1],
                "request_period": key[2],
                "period_date": key[3],
                "multiplicity": str(len(candidates)),
            }
        )
        canonical_rows.append(_build_duplicate_conflict_row(key=key, candidate_rows=candidates))

    metadata: dict[str, object] = {
        "canonical_result_key": list(CANONICAL_RESULT_KEY_FIELDS),
        "provider_duplicate_rows_detected": int(duplicate_rows_detected),
        "provider_duplicate_rows_collapsed": int(duplicate_rows_collapsed),
        "provider_duplicate_conflict_keys": list(duplicate_conflict_keys),
        "provider_duplicate_conflict_key_count": int(len(duplicate_conflict_keys)),
    }
    return canonical_rows, metadata


def _write_final_fmp_artifacts(repo_root: Path, snapshot_date: str, rows: list[dict[str, str]]) -> dict[str, str]:
    fmp_root = repo_root / "data/signals/fmp"
    daily_path = fmp_root / "daily" / f"fmp_analyst_estimates_{snapshot_date}.csv"
    latest_path = fmp_root / "latest" / "latest_fmp_analyst_estimates.csv"
    _write_csv_atomic(daily_path, ANALYST_ESTIMATES_HEADERS, [dict(r) for r in rows])
    _write_csv_atomic(latest_path, ANALYST_ESTIMATES_HEADERS, [dict(r) for r in rows])
    return {
        "daily_path": str(daily_path),
        "latest_path": str(latest_path),
    }


def _build_checkpoint_payload(
    *,
    run_id: str,
    snapshot_date: str,
    requested_periods: Sequence[str],
    universe_count: int,
    universe_hash: str,
    batch_size: int,
    current_batch: int,
    total_batches: int,
    resolved_symbols: Sequence[str],
    completed_symbols: Sequence[str],
    failed_symbols: Sequence[dict[str, object]],
    no_coverage_symbols: Sequence[str],
    symbols_with_data: Sequence[str],
    estimate_rows_fetched: int,
    pit_observations_written: int,
    pit_duplicates_skipped: int,
    rate_limit_events: int,
    retries_performed: int,
    started_at_utc: str,
    status: str,
    completed_at_utc: str | None = None,
) -> dict[str, object]:
    return {
        "version": CHECKPOINT_VERSION,
        "mode": "fmp_estimate_backfill",
        "run_id": run_id,
        "snapshot_date": snapshot_date,
        "requested_periods": list(requested_periods),
        "universe_count": int(universe_count),
        "universe_hash": str(universe_hash),
        "batch_size": int(batch_size),
        "current_batch": int(current_batch),
        "total_batches": int(total_batches),
        "resolved_symbols": list(resolved_symbols),
        "completed_symbols": sorted({_normalize_symbol(s) for s in completed_symbols if _normalize_symbol(s)}),
        "failed_symbols": list(failed_symbols),
        "no_coverage_symbols": sorted({_normalize_symbol(s) for s in no_coverage_symbols if _normalize_symbol(s)}),
        "symbols_with_data": sorted({_normalize_symbol(s) for s in symbols_with_data if _normalize_symbol(s)}),
        "estimate_rows_fetched": int(estimate_rows_fetched),
        "pit_observations_written": int(pit_observations_written),
        "pit_duplicates_skipped": int(pit_duplicates_skipped),
        "rate_limit_events": int(rate_limit_events),
        "retries_performed": int(retries_performed),
        "started_at_utc": started_at_utc,
        "updated_at_utc": _utc_now(),
        "completed_at_utc": completed_at_utc or "",
        "status": str(status),
    }


def _validate_resume_checkpoint(
    *,
    checkpoint: dict[str, Any],
    requested_periods: Sequence[str],
    universe_count: int,
    universe_hash: str,
    batch_size: int,
) -> None:
    if int(checkpoint.get("version") or 0) != CHECKPOINT_VERSION:
        raise ValueError("Checkpoint version mismatch")
    if str(checkpoint.get("mode") or "") != "fmp_estimate_backfill":
        raise ValueError("Checkpoint mode mismatch")

    cp_periods = [str(p).strip().lower() for p in (checkpoint.get("requested_periods") or []) if str(p).strip()]
    if cp_periods != list(requested_periods):
        raise ValueError("Checkpoint requested_periods mismatch")

    if int(checkpoint.get("universe_count") or -1) != int(universe_count):
        raise ValueError("Checkpoint universe_count mismatch")
    if str(checkpoint.get("universe_hash") or "") != str(universe_hash):
        raise ValueError("Checkpoint universe_hash mismatch")

    if int(checkpoint.get("batch_size") or 0) != int(batch_size):
        raise ValueError("Checkpoint batch_size mismatch")


def _pending_symbols_for_fetch(
    *,
    applicable_symbols: Sequence[str],
    terminal_symbols: set[str],
    failed_by_symbol: dict[str, dict[str, object]],
    retry_failed_on_resume: bool,
) -> list[str]:
    pending: list[str] = []
    for symbol in applicable_symbols:
        if symbol in terminal_symbols:
            continue
        failure = failed_by_symbol.get(symbol)
        if failure:
            if not bool(failure.get("retry_eligible")):
                continue
            if not retry_failed_on_resume:
                continue
        pending.append(symbol)
    return pending


def run_fmp_estimate_backfill(
    *,
    repo_root: str | Path = ".",
    research_universe: bool = False,
    symbols: Sequence[str] | None = None,
    requested_periods: Sequence[str] = DEFAULT_REQUESTED_PERIODS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT_PATH,
    resume: bool = False,
    dry_run: bool = False,
    report_path: str | Path | None = None,
    snapshot_date: str | None = None,
    max_batches: int | None = None,
    retry_failed_on_resume: bool = True,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    limit: int = DEFAULT_ESTIMATE_LIMIT,
) -> dict[str, object]:
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    root = Path(repo_root)
    periods = _normalize_periods(requested_periods)

    if research_universe and symbols:
        raise ValueError("Choose either research_universe=True or explicit symbols, not both")
    if not research_universe and not symbols:
        raise ValueError("Explicit symbols are required when research_universe=False")

    if research_universe:
        resolved_symbols = _resolve_research_universe_symbols(root)
        research_universe_symbols_resolved = len(resolved_symbols)
    else:
        resolved_symbols = _resolve_explicit_symbols(symbols or [])
        research_universe_symbols_resolved = 0

    if not resolved_symbols:
        raise ValueError("No applicable symbols resolved for FMP estimate backfill")

    applicable_symbols = list(resolved_symbols)
    universe_count = len(applicable_symbols)
    universe_hash = _universe_hash(applicable_symbols)

    checkpoint_file = Path(checkpoint_path)
    if not checkpoint_file.is_absolute():
        checkpoint_file = root / checkpoint_file

    checkpoint = _load_checkpoint(checkpoint_file) if resume else None
    if resume and checkpoint is None:
        raise ValueError("resume=True requested but checkpoint file was not found")

    run_id = str(uuid4())
    snapshot_date_value = str(snapshot_date).strip() if snapshot_date is not None else ""
    snapshot_date = snapshot_date_value or date.today().isoformat()
    started_at_utc = _utc_now()
    completed_at_utc = ""

    completed_symbols: set[str] = set()
    no_coverage_symbols: set[str] = set()
    symbols_with_data: set[str] = set()
    failed_by_symbol: dict[str, dict[str, object]] = {}

    estimate_rows_fetched = 0
    pit_observations_written = 0
    pit_duplicates_skipped = 0
    rate_limit_events = 0
    retries_performed = 0
    current_batch = 0

    if checkpoint is not None:
        _validate_resume_checkpoint(
            checkpoint=checkpoint,
            requested_periods=periods,
            universe_count=universe_count,
            universe_hash=universe_hash,
            batch_size=batch_size,
        )
        run_id = str(checkpoint.get("run_id") or run_id)
        snapshot_date = str(checkpoint.get("snapshot_date") or snapshot_date)
        started_at_utc = str(checkpoint.get("started_at_utc") or started_at_utc)
        completed_symbols = {_normalize_symbol(s) for s in (checkpoint.get("completed_symbols") or []) if _normalize_symbol(s)}
        no_coverage_symbols = {_normalize_symbol(s) for s in (checkpoint.get("no_coverage_symbols") or []) if _normalize_symbol(s)}
        symbols_with_data = {_normalize_symbol(s) for s in (checkpoint.get("symbols_with_data") or []) if _normalize_symbol(s)}
        estimate_rows_fetched = int(checkpoint.get("estimate_rows_fetched") or 0)
        pit_observations_written = int(checkpoint.get("pit_observations_written") or 0)
        pit_duplicates_skipped = int(checkpoint.get("pit_duplicates_skipped") or 0)
        rate_limit_events = int(checkpoint.get("rate_limit_events") or 0)
        retries_performed = int(checkpoint.get("retries_performed") or 0)
        current_batch = int(checkpoint.get("current_batch") or 0)
        for item in (checkpoint.get("failed_symbols") or []):
            entry = dict(item)
            symbol = _normalize_symbol(entry.get("symbol"))
            if symbol:
                failed_by_symbol[symbol] = entry

    run_root = root / DEFAULT_RUNS_ROOT / f"run_id={run_id}"
    run_root.mkdir(parents=True, exist_ok=True)

    terminal_symbols = set(completed_symbols) | set(no_coverage_symbols)
    remaining_symbols = _pending_symbols_for_fetch(
        applicable_symbols=applicable_symbols,
        terminal_symbols=terminal_symbols,
        failed_by_symbol=failed_by_symbol,
        retry_failed_on_resume=retry_failed_on_resume,
    )

    total_batches = int(math.ceil(len(remaining_symbols) / batch_size)) if remaining_symbols else 0
    provider_calls_avoided_by_resume = max(universe_count - len(remaining_symbols), 0)

    if dry_run:
        payload = {
            "mode": "fmp_estimate_backfill",
            "dry_run": True,
            "run_id": run_id,
            "snapshot_date": snapshot_date,
            "research_universe_symbols_resolved": int(research_universe_symbols_resolved),
            "fmp_estimate_applicable_symbols": int(universe_count),
            "resolved_symbols": list(applicable_symbols),
            "universe_count": int(universe_count),
            "universe_hash": universe_hash,
            "requested_periods": list(periods),
            "batch_size": int(batch_size),
            "checkpoint_path": str(checkpoint_file),
            "resume": bool(resume),
            "already_complete_symbols": sorted(terminal_symbols),
            "already_complete_count": int(len(terminal_symbols)),
            "fetch_required_symbols": list(remaining_symbols),
            "fetch_required_count": int(len(remaining_symbols)),
            "expected_batch_count": int(total_batches),
            "provider_calls": 0,
            "pit_writes": 0,
            "fmp_writes": 0,
            "provider_calls_avoided_by_resume": int(provider_calls_avoided_by_resume),
        }
        if report_path:
            report_file = Path(report_path)
            if not report_file.is_absolute():
                report_file = root / report_file
            _write_json_atomic(report_file, payload)
        return payload

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("FMP_API_KEY not set. Cannot run FMP estimate backfill.")

    processed_batches = 0
    symbol_results: list[dict[str, object]] = []

    for batch_symbols in _partition_symbols(remaining_symbols, batch_size):
        if max_batches is not None and processed_batches >= int(max_batches):
            break

        processed_batches += 1
        current_batch += 1

        for symbol in batch_symbols:
            retrieved_at_utc = _utc_now()
            all_rows: list[dict[str, str]] = []
            symbol_rate_limit_events = 0
            symbol_retries = 0

            for period in periods:
                rows, meta = fetch_analyst_estimates_with_meta(
                    symbol,
                    api_key,
                    snapshot_date,
                    period=period,
                    page=0,
                    limit=limit,
                )
                all_rows.extend(rows)
                symbol_rate_limit_events += int(meta.get("rate_limit_events") or 0)
                symbol_retries += int(meta.get("retries_performed") or 0)

            rate_limit_events += symbol_rate_limit_events
            retries_performed += symbol_retries
            estimate_rows_fetched += sum(
                1 for row in all_rows if str(row.get("fetch_status") or "").strip().upper() == "SUCCESS"
            )

            _write_symbol_rows(run_root, symbol, all_rows)

            status = _symbol_status(all_rows)
            result_entry: dict[str, object] = {
                "symbol": symbol,
                "status": status,
                "rate_limit_events": int(symbol_rate_limit_events),
                "retries_performed": int(symbol_retries),
            }

            if status == "SUCCESS":
                observations = _build_pit_observations(
                    rows=all_rows,
                    symbol=symbol,
                    snapshot_date=snapshot_date,
                    retrieved_at_utc=retrieved_at_utc,
                    run_id=run_id,
                )
                pit_result = append_pit_observations(
                    observations=observations,
                    provider="fmp",
                    snapshot_date=snapshot_date,
                    run_id=run_id,
                    history_root=root / "data/history/pit_observations",
                    index_path=root / "data/history/pit_observation_index.csv",
                )
                pit_observations_written += int(pit_result.written)
                pit_duplicates_skipped += int(pit_result.skipped_duplicate)

                completed_symbols.add(symbol)
                symbols_with_data.add(symbol)
                no_coverage_symbols.discard(symbol)
                failed_by_symbol.pop(symbol, None)
                result_entry.update(
                    {
                        "outcome": "SUCCESS",
                        "pit_written": int(pit_result.written),
                        "pit_duplicates": int(pit_result.skipped_duplicate),
                    }
                )
            elif status == "NO_ESTIMATE_COVERAGE":
                completed_symbols.add(symbol)
                no_coverage_symbols.add(symbol)
                symbols_with_data.discard(symbol)
                failed_by_symbol.pop(symbol, None)
                result_entry.update({"outcome": "NO_ESTIMATE_COVERAGE"})
            else:
                failure_row = _latest_failure_row(all_rows)
                failure_type = str(failure_row.get("failure_type") or "").strip().upper()
                failure_reason = str(failure_row.get("failure_reason") or "").strip()
                failure_class = _failure_class(failure_type)
                prior_attempts = int((failed_by_symbol.get(symbol) or {}).get("attempts") or 0)
                failed_by_symbol[symbol] = {
                    "symbol": symbol,
                    "failure_class": failure_class,
                    "failure_type": failure_type,
                    "failure_reason": failure_reason,
                    "retry_eligible": _retry_eligible(failure_class),
                    "attempts": prior_attempts + 1,
                    "last_seen_at_utc": _utc_now(),
                }
                completed_symbols.discard(symbol)
                no_coverage_symbols.discard(symbol)
                symbols_with_data.discard(symbol)
                result_entry.update(
                    {
                        "outcome": "FAILED",
                        "failure_class": failure_class,
                        "failure_type": failure_type,
                        "failure_reason": failure_reason,
                    }
                )

            symbol_results.append(result_entry)

            checkpoint_payload = _build_checkpoint_payload(
                run_id=run_id,
                snapshot_date=snapshot_date,
                requested_periods=periods,
                universe_count=universe_count,
                universe_hash=universe_hash,
                batch_size=batch_size,
                current_batch=current_batch,
                total_batches=total_batches,
                resolved_symbols=applicable_symbols,
                completed_symbols=sorted(completed_symbols),
                failed_symbols=list(failed_by_symbol.values()),
                no_coverage_symbols=sorted(no_coverage_symbols),
                symbols_with_data=sorted(symbols_with_data),
                estimate_rows_fetched=estimate_rows_fetched,
                pit_observations_written=pit_observations_written,
                pit_duplicates_skipped=pit_duplicates_skipped,
                rate_limit_events=rate_limit_events,
                retries_performed=retries_performed,
                started_at_utc=started_at_utc,
                status="RUNNING",
                completed_at_utc="",
            )
            _write_json_atomic(checkpoint_file, checkpoint_payload)

            if delay_seconds > 0:
                time.sleep(float(delay_seconds))

    terminal_symbols = set(completed_symbols) | set(no_coverage_symbols)
    remaining_after = _pending_symbols_for_fetch(
        applicable_symbols=applicable_symbols,
        terminal_symbols=terminal_symbols,
        failed_by_symbol=failed_by_symbol,
        retry_failed_on_resume=retry_failed_on_resume,
    )

    status = "COMPLETE" if not remaining_after else "IN_PROGRESS"
    if status == "COMPLETE":
        completed_at_utc = _utc_now()

    merged_rows = _merge_run_rows(run_root, sorted(terminal_symbols | set(failed_by_symbol.keys())))
    artifact_paths = {"daily_path": "", "latest_path": ""}
    fmp_writes = 0
    canonicalization_meta: dict[str, object] = {
        "canonical_result_key": list(CANONICAL_RESULT_KEY_FIELDS),
        "provider_duplicate_rows_detected": 0,
        "provider_duplicate_rows_collapsed": 0,
        "provider_duplicate_conflict_keys": [],
        "provider_duplicate_conflict_key_count": 0,
        "rows_before_canonicalization": int(len(merged_rows)),
        "rows_after_canonicalization": int(len(merged_rows)),
    }
    if status == "COMPLETE":
        canonical_rows, dedupe_meta = _canonicalize_rows_for_publication(merged_rows)
        canonicalization_meta.update(dedupe_meta)
        canonicalization_meta["rows_after_canonicalization"] = int(len(canonical_rows))
        artifact_paths = _write_final_fmp_artifacts(root, snapshot_date, canonical_rows)
        fmp_writes = len(canonical_rows)

    final_payload = _build_checkpoint_payload(
        run_id=run_id,
        snapshot_date=snapshot_date,
        requested_periods=periods,
        universe_count=universe_count,
        universe_hash=universe_hash,
        batch_size=batch_size,
        current_batch=current_batch,
        total_batches=total_batches,
        resolved_symbols=applicable_symbols,
        completed_symbols=sorted(completed_symbols),
        failed_symbols=list(failed_by_symbol.values()),
        no_coverage_symbols=sorted(no_coverage_symbols),
        symbols_with_data=sorted(symbols_with_data),
        estimate_rows_fetched=estimate_rows_fetched,
        pit_observations_written=pit_observations_written,
        pit_duplicates_skipped=pit_duplicates_skipped,
        rate_limit_events=rate_limit_events,
        retries_performed=retries_performed,
        started_at_utc=started_at_utc,
        status=status,
        completed_at_utc=completed_at_utc,
    )
    _write_json_atomic(checkpoint_file, final_payload)

    result = {
        "mode": "fmp_estimate_backfill",
        "dry_run": False,
        "run_id": run_id,
        "snapshot_date": snapshot_date,
        "resume": bool(resume),
        "research_universe_symbols_resolved": int(research_universe_symbols_resolved),
        "fmp_estimate_applicable_symbols": int(universe_count),
        "resolved_symbols": list(applicable_symbols),
        "requested_periods": list(periods),
        "universe_count": int(universe_count),
        "universe_hash": universe_hash,
        "batch_size": int(batch_size),
        "checkpoint_path": str(checkpoint_file),
        "total_batches": int(total_batches),
        "current_batch": int(current_batch),
        "processed_batches_this_invocation": int(processed_batches),
        "completed_symbols": sorted(completed_symbols),
        "completed_count": int(len(completed_symbols)),
        "no_coverage_symbols": sorted(no_coverage_symbols),
        "no_coverage_count": int(len(no_coverage_symbols)),
        "symbols_with_data": sorted(symbols_with_data),
        "symbols_with_data_count": int(len(symbols_with_data)),
        "failed_symbols": list(failed_by_symbol.values()),
        "failed_count": int(len(failed_by_symbol)),
        "fetch_required_after_run": list(remaining_after),
        "fetch_required_after_run_count": int(len(remaining_after)),
        "estimate_rows_fetched": int(estimate_rows_fetched),
        "pit_observations_written": int(pit_observations_written),
        "pit_duplicates_skipped": int(pit_duplicates_skipped),
        "rate_limit_events": int(rate_limit_events),
        "retries_performed": int(retries_performed),
        "provider_calls": int(len(symbol_results)),
        "provider_calls_avoided_by_resume": int(provider_calls_avoided_by_resume),
        "checkpoint_write_atomic": True,
        "status": status,
        "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc,
        "symbol_results": symbol_results,
        "daily_artifact_path": artifact_paths["daily_path"],
        "latest_artifact_path": artifact_paths["latest_path"],
        "fmp_writes": int(fmp_writes),
        "pit_writes": int(pit_observations_written + pit_duplicates_skipped),
        "rows_before_canonicalization": int(len(merged_rows)),
        "rows_after_canonicalization": int(canonicalization_meta.get("rows_after_canonicalization") or len(merged_rows)),
        "canonical_result_key": list(canonicalization_meta.get("canonical_result_key") or []),
        "provider_duplicate_rows_detected": int(canonicalization_meta.get("provider_duplicate_rows_detected") or 0),
        "provider_duplicate_rows_collapsed": int(canonicalization_meta.get("provider_duplicate_rows_collapsed") or 0),
        "provider_duplicate_conflict_keys": list(canonicalization_meta.get("provider_duplicate_conflict_keys") or []),
        "provider_duplicate_conflict_key_count": int(canonicalization_meta.get("provider_duplicate_conflict_key_count") or 0),
    }

    if report_path:
        report_file = Path(report_path)
        if not report_file.is_absolute():
            report_file = root / report_file
        _write_json_atomic(report_file, result)

    return result


def parse_symbols_csv(symbols_csv: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in str(symbols_csv or "").split(","):
        symbol = _normalize_symbol(token)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        values.append(symbol)
    return values
