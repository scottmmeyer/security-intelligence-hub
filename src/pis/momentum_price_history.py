"""Momentum price-history coverage and restoration utilities (reporting-only).

This module uses existing repo-supported market-data providers and persistence
contracts to inventory and restore price history for current portfolio momentum
analytics without changing scoring or recommendation behavior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from src.history.market_data_manager import persist_benchmark_returns, persist_security_prices
from src.models.market_data_models import BenchmarkReturnRow
from src.replay.history_providers import YahooHistoricalPriceProvider


APPLICABLE_SECURITY_TYPES = {
    "EQUITY",
    "EQUITIES",
    "STOCK",
    "COMMON STOCK",
    "COMMON_STOCK",
    "ADR",
    "ETF",
}

NON_INDUSTRY_VALUES = {"", "UNAVAILABLE", "UNKNOWN", "N/A", "NA", "NONE", "ALL"}

DEFAULT_RESEARCH_HISTORY_START = "2021-01-01"
DEFAULT_BACKFILL_BATCH_SIZE = 50
DEFAULT_CHECKPOINT_PATH = "data/runtime/checkpoints/research_universe_price_backfill_checkpoint.json"
DEFAULT_BENCHMARK_ID = "BM_US_LARGE_SP500"
DEFAULT_BENCHMARK_SYMBOL = "^GSPC"

SECTOR_PARENT_ETF_MAP = {
    "TECHNOLOGY": "XLK",
    "ENERGY": "XLE",
    "BASIC MATERIALS": "XLB",
    "INDUSTRIALS": "XLI",
    "HEALTHCARE": "XLV",
    "FINANCIAL SERVICES": "XLF",
    "FINANCIALS": "XLF",
    "CONSUMER CYCLICAL": "XLY",
    "CONSUMER DEFENSIVE": "XLP",
    "CONSUMER STAPLES": "XLP",
    "UTILITIES": "XLU",
    "REAL ESTATE": "XLRE",
    "COMMUNICATION SERVICES": "XLC",
}


@dataclass(frozen=True)
class PriceCoverageRow:
    symbol: str
    asset_type: str
    sector: str
    industry: str
    first_price_date: str | None
    last_price_date: str | None
    trading_days_available: int
    source: str | None
    freshness_days: int | None
    coverage_status: str


@dataclass(frozen=True)
class CoverageInventory:
    snapshot_date: str
    applicable_count: int
    not_applicable_count: int
    present_count: int
    missing_count: int
    partial_count: int
    coverage_pct: float
    rows: tuple[PriceCoverageRow, ...]
    not_applicable_symbols: tuple[str, ...]


@dataclass(frozen=True)
class SectorParentCoverageRow:
    sector: str
    current_holdings_count: int
    parent_series: str | None
    parent_source: str | None
    history_available: bool
    first_date: str | None
    last_date: str | None
    trading_days_available: int


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _to_float(value: object) -> float | None:
    try:
        text = str(value or "").strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_date(value: object) -> str:
    raw = str(value or "").strip()
    return raw[:10] if len(raw) >= 10 else ""


def _freshness_days(last_date: str | None) -> int | None:
    if not last_date:
        return None
    try:
        d = date.fromisoformat(last_date)
    except ValueError:
        return None
    return (date.today() - d).days


def _latest_positions_file(repo_root: Path) -> tuple[str, Path | None]:
    rows = _read_csv_rows(repo_root / "data/history/pis/pis_snapshot_index.csv")
    if not rows:
        return "", None
    best = max(rows, key=lambda row: str(row.get("snapshot_date", "")))
    positions_path = str(best.get("positions_path", "")).strip()
    if not positions_path:
        return str(best.get("snapshot_date", "")), None
    p = Path(positions_path)
    if not p.is_absolute():
        p = repo_root / p
    return str(best.get("snapshot_date", "")), p


def _load_universe_metadata(repo_root: Path) -> dict[str, dict[str, str]]:
    """Load security metadata from authoritative sources.
    
    Priority:
    1. Portfolio analysis holdings.csv (has enriched sector/industry for current portfolio)
    2. Analytical universe CSV (has ESS/Zacks/Yahoo data for broader universe)
    """
    out: dict[str, dict[str, str]] = {}

    # First: check portfolio ingestion for current holdings metadata
    portfolio_runs_dir = repo_root / "data/portfolio_ingestion/analysis_runs"
    if portfolio_runs_dir.exists():
        # Find latest portfolio analysis run
        latest_run = max(
            (d for d in portfolio_runs_dir.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            default=None,
        )
        if latest_run:
            holdings_path = latest_run / "holdings.csv"
            if holdings_path.exists():
                for row in _read_csv_rows(holdings_path):
                    symbol = str(row.get("symbol", "")).strip().upper()
                    if not symbol:
                        continue
                    out[symbol] = {
                        "sector": str(row.get("sector", "")).strip(),
                        "industry": str(row.get("industry", "")).strip(),
                        "security_type": str(row.get("security_type", "")).strip(),
                    }

    # Second: load analytical_universe for securities not in portfolio analysis
    universe_rows = _read_csv_rows(repo_root / "data/current/analytical_universe.csv")
    for row in universe_rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in out:
            continue
        out[symbol] = {
            "sector": str(row.get("sector", "")).strip(),
            "industry": str(row.get("industry", "")).strip(),
            "security_type": str(row.get("security_type", "")).strip(),
        }
    return out


def load_current_holdings(repo_root: Path) -> tuple[str, list[dict[str, object]]]:
    snapshot_date, positions_path = _latest_positions_file(repo_root)
    if positions_path is None or not positions_path.exists():
        return snapshot_date, []

    universe = _load_universe_metadata(repo_root)
    out: list[dict[str, object]] = []
    for row in _read_csv_rows(positions_path):
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in {"CASH", "PENDING"}:
            continue
        sec_type = str(row.get("security_type", "")).strip().upper()
        metadata = universe.get(symbol, {})
        sector = str(metadata.get("sector", "")).strip()
        industry = str(metadata.get("industry", "")).strip()
        weight = _to_float(row.get("percent_of_account")) or 0.0
        out.append(
            {
                "symbol": symbol,
                "asset_type": sec_type,
                "sector": sector,
                "industry": industry,
                "portfolio_weight": float(weight),
            }
        )
    return snapshot_date, out


def _price_series_stats(repo_root: Path, symbol: str) -> tuple[str | None, str | None, int, str | None]:
    price_file = repo_root / "data/history/prices" / f"symbol={symbol}" / "prices.csv"
    if not price_file.exists():
        return None, None, 0, None
    rows = _read_csv_rows(price_file)
    if not rows:
        return None, None, 0, None
    dates = sorted([_normalize_date(r.get("date", "")) for r in rows if _normalize_date(r.get("date", ""))])
    if not dates:
        return None, None, 0, None
    source = str(rows[-1].get("source_provider", "")).strip() or None
    return dates[0], dates[-1], len(dates), source


def _benchmark_series_stats(
    repo_root: Path,
    benchmark_id: str = DEFAULT_BENCHMARK_ID,
) -> tuple[str | None, str | None, int]:
    benchmark_file = repo_root / "data/history/benchmarks" / f"benchmark_id={benchmark_id}" / "benchmark_returns.csv"
    if not benchmark_file.exists():
        return None, None, 0
    rows = _read_csv_rows(benchmark_file)
    if not rows:
        return None, None, 0
    dates = sorted([_normalize_date(r.get("date", "")) for r in rows if _normalize_date(r.get("date", ""))])
    if not dates:
        return None, None, 0
    return dates[0], dates[-1], len(dates)


def _latest_existing_benchmark_endpoint(repo_root: Path, requested_end_date: str) -> str:
    benchmark_file = (
        repo_root
        / "data/history/benchmarks"
        / f"benchmark_id={DEFAULT_BENCHMARK_ID}"
        / "benchmark_returns.csv"
    )
    if not benchmark_file.exists():
        return requested_end_date

    rows = _read_csv_rows(benchmark_file)
    candidates: list[str] = []
    for row in rows:
        value = _normalize_date(row.get("date", ""))
        if value and value <= requested_end_date:
            candidates.append(value)
    if not candidates:
        return requested_end_date
    return max(candidates)


def _start_requirement_met(
    *,
    first_date: str | None,
    requested_start_date: str,
    max_start_gap_days: int = 7,
) -> bool:
    if not first_date:
        return False
    if first_date <= requested_start_date:
        return True
    try:
        first_dt = date.fromisoformat(first_date)
        requested_dt = date.fromisoformat(requested_start_date)
    except ValueError:
        return False
    return 0 <= (first_dt - requested_dt).days <= int(max_start_gap_days)


def _is_already_complete(
    *,
    first_date: str | None,
    last_date: str | None,
    required_start_date: str,
    required_latest_endpoint: str,
) -> bool:
    if not first_date or not last_date:
        return False
    return _start_requirement_met(
        first_date=first_date,
        requested_start_date=required_start_date,
    ) and last_date >= required_latest_endpoint


def _parse_symbols_csv(symbols_csv: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in str(symbols_csv or "").split(","):
        symbol = token.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        values.append(symbol)
    return values


def resolve_research_universe_applicable_equities(repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    rows = _read_csv_rows(root / "data/current/analytical_universe.csv")
    research_symbols: list[str] = []
    seen_research: set[str] = set()

    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        if symbol not in seen_research:
            seen_research.add(symbol)
            research_symbols.append(symbol)

    # Reuse canonical DRI applicability contract so all DRI-eligible equities are included.
    from src.pis.dislocation_recovery_intelligence import (
        _NON_INDUSTRY_VALUES,
        _canonical_research_symbols,
        _is_equity_like,
        _normalized_taxonomy_value,
    )
    from src.pis.momentum_intelligence import _load_security_type_taxonomy, _load_universe_metadata

    universe = _load_universe_metadata(root)
    canonical_research_symbols, research_security_types = _canonical_research_symbols(root)
    security_types = _load_security_type_taxonomy(root)

    research_considered = set(canonical_research_symbols)
    if not research_considered:
        research_considered = set(universe.keys())

    applicable_equities: list[str] = []
    for symbol in sorted(research_considered):
        meta = universe.get(symbol, {})
        industry = _normalized_taxonomy_value(
            str(meta.get("industry") or ""),
            unknown_values=_NON_INDUSTRY_VALUES,
            fallback="UNAVAILABLE",
        )
        if industry == "UNAVAILABLE":
            continue

        sec_type = security_types.get(symbol) or research_security_types.get(symbol) or ""
        if sec_type and not _is_equity_like(sec_type):
            continue

        applicable_equities.append(symbol)

    return {
        "research_universe_symbols": sorted(research_symbols),
        "applicable_equities": sorted(applicable_equities),
    }


def _build_backfill_checkpoint_payload(
    *,
    run_id: str,
    mode: str,
    requested_start_date: str,
    requested_end_date: str,
    batch_size: int,
    resolved_symbols: Sequence[str],
    completed_symbols: Sequence[str],
    failed_symbols: Sequence[dict[str, object]],
    current_batch: int,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "mode": mode,
        "requested_start_date": requested_start_date,
        "requested_end_date": requested_end_date,
        "batch_size": int(batch_size),
        "resolved_symbols": list(resolved_symbols),
        "resolved_symbol_count": len(resolved_symbols),
        "completed_symbols": sorted(set(str(s) for s in completed_symbols if str(s))),
        "failed_symbols": list(failed_symbols),
        "current_batch": int(current_batch),
        "last_completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _load_checkpoint(checkpoint_path: Path) -> dict[str, object] | None:
    if not checkpoint_path.exists():
        return None
    try:
        return json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def backfill_research_universe_price_history(
    *,
    repo_root: str | Path = ".",
    symbols: Sequence[str] | None = None,
    research_universe_mode: bool = False,
    start_date: str = DEFAULT_RESEARCH_HISTORY_START,
    end_date: str | None = None,
    batch_size: int = DEFAULT_BACKFILL_BATCH_SIZE,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT_PATH,
    resume: bool = False,
    include_benchmark: bool = True,
    dry_run: bool = False,
) -> dict[str, object]:
    """Backfill canonical historical prices for explicit symbols or research universe.

    This orchestration reuses existing Yahoo provider and existing partitioned
    persistence contracts. It is reporting/runtime oriented and does not alter
    scoring or recommendation logic.
    """

    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    root = Path(repo_root)
    requested_end_date = str(end_date or date.today().isoformat())
    requested_start_date = str(start_date)

    if research_universe_mode and symbols:
        raise ValueError("Choose either research_universe_mode or explicit symbols, not both.")
    if not research_universe_mode and not symbols:
        raise ValueError(
            "Explicit scope is required: pass symbols or set research_universe_mode=True."
        )

    mode = "research_universe" if research_universe_mode else "explicit_symbols"
    if research_universe_mode:
        resolved = resolve_research_universe_applicable_equities(root)
        research_universe_symbols = list(resolved["research_universe_symbols"])
        resolved_symbols = list(resolved["applicable_equities"])
    else:
        research_universe_symbols = []
        resolved_symbols = sorted(
            {
                str(symbol).strip().upper()
                for symbol in (symbols or [])
                if str(symbol).strip()
            }
        )

    required_start_endpoint = requested_start_date
    required_latest_endpoint = _latest_existing_benchmark_endpoint(root, requested_end_date)

    symbol_before: dict[str, dict[str, object]] = {}
    already_complete_symbols: list[str] = []
    fetch_required_symbols: list[str] = []
    for symbol in resolved_symbols:
        first_date, last_date, row_count, _source = _price_series_stats(root, symbol)
        symbol_before[symbol] = {
            "first_date": first_date,
            "last_date": last_date,
            "row_count": row_count,
        }
        if _is_already_complete(
            first_date=first_date,
            last_date=last_date,
            required_start_date=required_start_endpoint,
            required_latest_endpoint=required_latest_endpoint,
        ):
            already_complete_symbols.append(symbol)
        else:
            fetch_required_symbols.append(symbol)

    checkpoint_file = Path(checkpoint_path)
    if not checkpoint_file.is_absolute():
        checkpoint_file = root / checkpoint_file

    checkpoint = _load_checkpoint(checkpoint_file) if resume else None
    run_id = str(uuid4())
    completed_symbols: set[str] = set(already_complete_symbols)
    failed_symbols: list[dict[str, object]] = []
    checkpoint_batch = 0

    if checkpoint is not None:
        if str(checkpoint.get("mode")) != mode:
            raise ValueError("Checkpoint mode does not match requested run mode.")
        if str(checkpoint.get("requested_start_date")) != requested_start_date:
            raise ValueError("Checkpoint requested_start_date does not match.")
        if str(checkpoint.get("requested_end_date")) != requested_end_date:
            raise ValueError("Checkpoint requested_end_date does not match.")
        if int(checkpoint.get("batch_size") or 0) != int(batch_size):
            raise ValueError("Checkpoint batch_size does not match.")

        checkpoint_symbols = [str(s) for s in (checkpoint.get("resolved_symbols") or [])]
        if checkpoint_symbols != list(resolved_symbols):
            raise ValueError("Checkpoint resolved_symbols does not match current resolution.")

        run_id = str(checkpoint.get("run_id") or run_id)
        completed_symbols.update(str(s) for s in (checkpoint.get("completed_symbols") or []) if str(s))
        failed_symbols = [dict(item) for item in (checkpoint.get("failed_symbols") or [])]
        checkpoint_batch = int(checkpoint.get("current_batch") or 0)

    benchmark_first_before, benchmark_last_before, benchmark_rows_before = _benchmark_series_stats(root)
    benchmark_already_complete = _is_already_complete(
        first_date=benchmark_first_before,
        last_date=benchmark_last_before,
        required_start_date=required_start_endpoint,
        required_latest_endpoint=required_latest_endpoint,
    )
    benchmark_required = bool(include_benchmark and not benchmark_already_complete)

    remaining_symbols = [symbol for symbol in fetch_required_symbols if symbol not in completed_symbols]
    batch_count = (len(remaining_symbols) + batch_size - 1) // batch_size if remaining_symbols else 0

    if dry_run:
        return {
            "run_id": run_id,
            "mode": mode,
            "dry_run": True,
            "checkpoint_path": str(checkpoint_file),
            "requested_start_date": requested_start_date,
            "requested_end_date": requested_end_date,
            "required_start_endpoint": required_start_endpoint,
            "required_latest_endpoint": required_latest_endpoint,
            "batch_size": int(batch_size),
            "expected_batch_count": int(batch_count),
            "research_universe_symbols_resolved": len(research_universe_symbols),
            "applicable_equities_resolved": len(resolved_symbols),
            "already_complete_count": len(already_complete_symbols),
            "fetch_required_count": len(fetch_required_symbols),
            "remaining_fetch_required_count": len(remaining_symbols),
            "benchmark_backfill_required": benchmark_required,
            "provider_calls": 0,
            "canonical_writes": 0,
            "data_mutated": False,
            "sample_status_by_symbol": {
                symbol: (
                    "ALREADY_COMPLETE" if symbol in set(already_complete_symbols) else "FETCH_REQUIRED"
                )
                for symbol in resolved_symbols[:50]
            },
            "crm_backfill_status": (
                "ALREADY_COMPLETE"
                if "CRM" in set(already_complete_symbols)
                else ("FETCH_REQUIRED" if "CRM" in set(resolved_symbols) else "NOT_IN_SCOPE")
            ),
        }

    provider = YahooHistoricalPriceProvider()
    symbol_results: list[dict[str, object]] = []
    for symbol in already_complete_symbols:
        before = symbol_before[symbol]
        symbol_results.append(
            {
                "symbol": symbol,
                "status": "ALREADY_COMPLETE",
                "rows_before": int(before["row_count"]),
                "rows_fetched": 0,
                "rows_added": 0,
                "rows_after": int(before["row_count"]),
                "first_date_before": before["first_date"],
                "first_date_after": before["first_date"],
                "last_date_before": before["last_date"],
                "last_date_after": before["last_date"],
                "requested_start": requested_start_date,
                "requested_end": requested_end_date,
                "error_type": "",
                "error_message": "",
            }
        )

    batch_reports: list[dict[str, object]] = []
    total_rows_fetched = 0
    total_rows_added = 0
    all_failures = list(failed_symbols)

    for batch_index in range(batch_count):
        offset = batch_index * batch_size
        batch_symbols = remaining_symbols[offset : offset + batch_size]
        batch_started = datetime.now(timezone.utc).isoformat()
        batch_price_rows = []
        batch_symbol_meta: list[dict[str, object]] = []
        batch_failures: list[dict[str, object]] = []
        batch_rows_fetched = 0

        for symbol in batch_symbols:
            before_first, before_last, before_count, _source = _price_series_stats(root, symbol)
            status = "SUCCESS"
            error_type = ""
            error_message = ""
            fetched_rows = []
            try:
                fetched_rows = provider.get_historical_prices(
                    security_id=f"YF:{symbol}",
                    symbol=symbol,
                    security_type="EQUITY",
                    start_date=requested_start_date,
                    end_date=requested_end_date,
                )
            except Exception as exc:
                status = "OTHER"
                error_type = "OTHER"
                error_message = str(exc)
                fetched_rows = []

            if status == "SUCCESS" and not fetched_rows:
                if before_first and before_first > requested_start_date:
                    status = "IPO_LIMITATION"
                    error_type = "IPO_LIMITATION"
                else:
                    status = "NO_DATA"
                    error_type = "NO_DATA"

            batch_rows_fetched += len(fetched_rows)
            batch_price_rows.extend(fetched_rows)
            batch_symbol_meta.append(
                {
                    "symbol": symbol,
                    "before_first": before_first,
                    "before_last": before_last,
                    "before_count": before_count,
                    "status": status,
                    "error_type": error_type,
                    "error_message": error_message,
                    "rows_fetched": len(fetched_rows),
                }
            )
            if status != "SUCCESS":
                failure = {
                    "symbol": symbol,
                    "status": status,
                    "error_type": error_type,
                    "error_message": error_message,
                }
                batch_failures.append(failure)
                all_failures.append(failure)

        history_rows_added = 0
        persistence_error = ""
        if batch_price_rows:
            try:
                persist_result = persist_security_prices(
                    rows=batch_price_rows,
                    current_root=root / "data/runtime/research_universe_price_backfill_current",
                    history_root=root / "data/history/prices",
                )
                history_rows_added = int(persist_result.get("history_rows_appended") or 0)
            except Exception as exc:
                persistence_error = str(exc)

        for item in batch_symbol_meta:
            symbol = str(item["symbol"])
            after_first, after_last, after_count, _source = _price_series_stats(root, symbol)
            rows_added = max(0, after_count - int(item["before_count"]))
            status = str(item["status"])
            error_type = str(item["error_type"])
            error_message = str(item["error_message"])
            if persistence_error and status == "SUCCESS":
                status = "PERSISTENCE_FAILURE"
                error_type = "PERSISTENCE_FAILURE"
                error_message = persistence_error

            if status == "SUCCESS":
                completed_symbols.add(symbol)

            symbol_results.append(
                {
                    "symbol": symbol,
                    "status": status,
                    "rows_before": int(item["before_count"]),
                    "rows_fetched": int(item["rows_fetched"]),
                    "rows_added": int(rows_added),
                    "rows_after": int(after_count),
                    "first_date_before": item["before_first"],
                    "first_date_after": after_first,
                    "last_date_before": item["before_last"],
                    "last_date_after": after_last,
                    "requested_start": requested_start_date,
                    "requested_end": requested_end_date,
                    "error_type": error_type,
                    "error_message": error_message,
                }
            )

        total_rows_fetched += int(batch_rows_fetched)
        total_rows_added += int(history_rows_added)
        batch_completed = datetime.now(timezone.utc).isoformat()
        batch_reports.append(
            {
                "batch_number": int(batch_index + 1),
                "symbols_requested": len(batch_symbols),
                "symbols_succeeded": sum(1 for item in batch_symbol_meta if item["status"] == "SUCCESS"),
                "symbols_failed": len(batch_failures),
                "symbols_skipped_already_complete": 0,
                "rows_fetched": int(batch_rows_fetched),
                "rows_added": int(history_rows_added),
                "batch_started_at_utc": batch_started,
                "batch_completed_at_utc": batch_completed,
            }
        )

        checkpoint_payload = _build_backfill_checkpoint_payload(
            run_id=run_id,
            mode=mode,
            requested_start_date=requested_start_date,
            requested_end_date=requested_end_date,
            batch_size=batch_size,
            resolved_symbols=resolved_symbols,
            completed_symbols=sorted(completed_symbols),
            failed_symbols=all_failures,
            current_batch=checkpoint_batch + batch_index + 1,
        )
        _write_json_atomic(checkpoint_file, checkpoint_payload)

    benchmark_result: dict[str, object] = {
        "requested": bool(include_benchmark),
        "backfill_required": bool(benchmark_required),
        "status": "SKIPPED",
        "rows_before": int(benchmark_rows_before),
        "rows_fetched": 0,
        "rows_added": 0,
        "rows_after": int(benchmark_rows_before),
        "first_date_before": benchmark_first_before,
        "first_date_after": benchmark_first_before,
        "last_date_before": benchmark_last_before,
        "last_date_after": benchmark_last_before,
        "requested_start": requested_start_date,
        "requested_end": requested_end_date,
    }

    if include_benchmark and benchmark_required:
        try:
            bm_prices = provider.get_historical_prices(
                security_id=f"BENCH:{DEFAULT_BENCHMARK_ID}",
                symbol=DEFAULT_BENCHMARK_SYMBOL,
                security_type="BENCHMARK_INDEX",
                start_date=requested_start_date,
                end_date=requested_end_date,
            )
            bm_points = sorted(
                [(row.date, float(row.adjusted_close)) for row in bm_prices if row.adjusted_close > 0],
                key=lambda item: item[0],
            )
            bm_rows = []
            if bm_points:
                base = bm_points[0][1]
                if base > 0:
                    bm_rows = [
                        BenchmarkReturnRow(
                            benchmark_id=DEFAULT_BENCHMARK_ID,
                            symbol_or_index=DEFAULT_BENCHMARK_SYMBOL,
                            date=d,
                            adjusted_close=round(value, 8),
                            cumulative_return=round((value / base) - 1.0, 8),
                            source_provider="YAHOO_FINANCE",
                        )
                        for d, value in bm_points
                    ]

            benchmark_rows_added = 0
            if bm_rows:
                persist_result = persist_benchmark_returns(
                    rows=bm_rows,
                    current_root=root / "data/runtime/research_universe_price_backfill_current",
                    history_root=root / "data/history/benchmarks",
                )
                benchmark_rows_added = int(persist_result.get("history_rows_appended") or 0)

            benchmark_first_after, benchmark_last_after, benchmark_rows_after = _benchmark_series_stats(root)
            benchmark_result = {
                "requested": True,
                "backfill_required": True,
                "status": "SUCCESS",
                "rows_before": int(benchmark_rows_before),
                "rows_fetched": len(bm_rows),
                "rows_added": int(benchmark_rows_added),
                "rows_after": int(benchmark_rows_after),
                "first_date_before": benchmark_first_before,
                "first_date_after": benchmark_first_after,
                "last_date_before": benchmark_last_before,
                "last_date_after": benchmark_last_after,
                "requested_start": requested_start_date,
                "requested_end": requested_end_date,
            }
        except Exception as exc:
            benchmark_result["status"] = "OTHER"
            benchmark_result["error_type"] = "OTHER"
            benchmark_result["error_message"] = str(exc)

    final_checkpoint = _build_backfill_checkpoint_payload(
        run_id=run_id,
        mode=mode,
        requested_start_date=requested_start_date,
        requested_end_date=requested_end_date,
        batch_size=batch_size,
        resolved_symbols=resolved_symbols,
        completed_symbols=sorted(completed_symbols),
        failed_symbols=all_failures,
        current_batch=checkpoint_batch + batch_count,
    )
    final_checkpoint["status"] = "COMPLETE"
    _write_json_atomic(checkpoint_file, final_checkpoint)

    return {
        "run_id": run_id,
        "mode": mode,
        "dry_run": False,
        "checkpoint_path": str(checkpoint_file),
        "requested_start_date": requested_start_date,
        "requested_end_date": requested_end_date,
        "required_start_endpoint": required_start_endpoint,
        "required_latest_endpoint": required_latest_endpoint,
        "batch_size": int(batch_size),
        "batch_count": int(batch_count),
        "research_universe_symbols_resolved": len(research_universe_symbols),
        "applicable_equities_resolved": len(resolved_symbols),
        "already_complete_count": len(already_complete_symbols),
        "fetch_required_count": len(fetch_required_symbols),
        "symbol_results": symbol_results,
        "batch_reports": batch_reports,
        "failed_symbols": all_failures,
        "rows_fetched_total": int(total_rows_fetched),
        "rows_added_total": int(total_rows_added),
        "benchmark": benchmark_result,
        "resume_used": bool(resume),
    }


def parse_symbols_csv(symbols_csv: str) -> list[str]:
    """Public helper for CLI parsing of comma-delimited symbol lists."""
    return _parse_symbols_csv(symbols_csv)


def _coverage_status(trading_days: int, freshness: int | None) -> str:
    if trading_days <= 0:
        return "MISSING"
    if trading_days < 253:
        return "PARTIAL"
    if freshness is None:
        return "PARTIAL"
    if freshness > 5:
        return "PARTIAL"
    return "PRESENT"


def inventory_current_price_coverage(repo_root: str | Path = ".") -> CoverageInventory:
    root = Path(repo_root)
    snapshot_date, holdings = load_current_holdings(root)

    rows: list[PriceCoverageRow] = []
    not_applicable_symbols: list[str] = []

    applicable_count = 0
    present_count = 0
    missing_count = 0
    partial_count = 0

    for holding in holdings:
        symbol = str(holding["symbol"])
        asset_type = str(holding["asset_type"])
        sector = str(holding["sector"])
        industry = str(holding["industry"])

        if asset_type not in APPLICABLE_SECURITY_TYPES:
            not_applicable_symbols.append(symbol)
            continue

        applicable_count += 1
        first_date, last_date, trading_days, source = _price_series_stats(root, symbol)
        freshness = _freshness_days(last_date)
        status = _coverage_status(trading_days, freshness)
        if status == "PRESENT":
            present_count += 1
        elif status == "PARTIAL":
            partial_count += 1
        else:
            missing_count += 1

        rows.append(
            PriceCoverageRow(
                symbol=symbol,
                asset_type=asset_type,
                sector=sector,
                industry=industry,
                first_price_date=first_date,
                last_price_date=last_date,
                trading_days_available=trading_days,
                source=source,
                freshness_days=freshness,
                coverage_status=status,
            )
        )

    coverage_pct = 0.0
    if applicable_count > 0:
        coverage_pct = round((present_count / applicable_count) * 100.0, 2)

    return CoverageInventory(
        snapshot_date=snapshot_date,
        applicable_count=applicable_count,
        not_applicable_count=len(not_applicable_symbols),
        present_count=present_count,
        missing_count=missing_count,
        partial_count=partial_count,
        coverage_pct=coverage_pct,
        rows=tuple(sorted(rows, key=lambda r: r.symbol)),
        not_applicable_symbols=tuple(sorted(not_applicable_symbols)),
    )


def inventory_sector_parent_coverage(repo_root: str | Path = ".") -> list[SectorParentCoverageRow]:
    root = Path(repo_root)
    _snapshot_date, holdings = load_current_holdings(root)

    sector_counts: dict[str, int] = {}
    for h in holdings:
        asset_type = str(h["asset_type"])
        if asset_type not in APPLICABLE_SECURITY_TYPES:
            continue
        sector = str(h["sector"] or "UNKNOWN").strip()
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    rows: list[SectorParentCoverageRow] = []
    for sector, count in sorted(sector_counts.items()):
        parent = SECTOR_PARENT_ETF_MAP.get(sector.upper())
        first_date = None
        last_date = None
        trading_days = 0
        source = None
        history_available = False
        if parent:
            first_date, last_date, trading_days, source = _price_series_stats(root, parent)
            history_available = trading_days > 0

        rows.append(
            SectorParentCoverageRow(
                sector=sector,
                current_holdings_count=count,
                parent_series=parent,
                parent_source=source,
                history_available=history_available,
                first_date=first_date,
                last_date=last_date,
                trading_days_available=trading_days,
            )
        )
    return rows


def restore_current_portfolio_price_history(
    *,
    repo_root: str | Path = ".",
    lookback_calendar_days: int = 420,
    include_sector_parents: bool = True,
    include_benchmark: bool = True,
) -> dict[str, object]:
    """Restore price history for applicable current holdings and required parents.

    Uses existing Yahoo historical provider and existing immutable persistence
    contracts; does not alter normal signal refresh semantics.
    """

    root = Path(repo_root)
    before = inventory_current_price_coverage(root)
    provider = YahooHistoricalPriceProvider()

    snapshot_date, holdings = load_current_holdings(root)
    end_date = date.today()
    start_date = end_date - timedelta(days=max(30, int(lookback_calendar_days)))

    applicable_symbols = sorted(
        {
            str(h["symbol"])
            for h in holdings
            if str(h.get("asset_type", "")).upper() in APPLICABLE_SECURITY_TYPES
        }
    )

    target_symbols: set[str] = set(applicable_symbols)
    parent_symbols: set[str] = set()

    if include_sector_parents:
        for row in inventory_sector_parent_coverage(root):
            if row.parent_series:
                parent_symbols.add(row.parent_series)
        target_symbols.update(parent_symbols)

    historical_rows = []
    fetched_symbols: list[str] = []
    failed_symbols: list[str] = []
    for symbol in sorted(target_symbols):
        try:
            rows = provider.get_historical_prices(
                security_id=f"YF:{symbol}",
                symbol=symbol,
                security_type="ETF" if symbol in parent_symbols else "EQUITY",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        except Exception:
            rows = []
        if rows:
            fetched_symbols.append(symbol)
            historical_rows.extend(rows)
        else:
            failed_symbols.append(symbol)

    security_persist = {"current_rows": 0, "history_rows_appended": 0, "symbol_partition_count": 0}
    if historical_rows:
        security_persist = persist_security_prices(rows=historical_rows)

    benchmark_persist = {"current_rows": 0, "history_rows_appended": 0, "benchmark_partition_count": 0}
    benchmark_symbol = "^GSPC"
    if include_benchmark:
        bm_prices = provider.get_historical_prices(
            security_id="BENCH:BM_US_LARGE_SP500",
            symbol=benchmark_symbol,
            security_type="BENCHMARK_INDEX",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        bm_points = sorted([(r.date, float(r.adjusted_close)) for r in bm_prices if r.adjusted_close > 0], key=lambda x: x[0])
        if bm_points:
            base = bm_points[0][1]
            bm_rows = [
                BenchmarkReturnRow(
                    benchmark_id="BM_US_LARGE_SP500",
                    symbol_or_index=benchmark_symbol,
                    date=d,
                    adjusted_close=round(v, 8),
                    cumulative_return=round((v / base) - 1.0, 8),
                    source_provider="YAHOO_FINANCE",
                )
                for d, v in bm_points
                if base > 0
            ]
            benchmark_persist = persist_benchmark_returns(rows=bm_rows)

    after = inventory_current_price_coverage(root)
    sector_after = inventory_sector_parent_coverage(root)

    return {
        "snapshot_date": snapshot_date,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "applicable_symbols": applicable_symbols,
        "sector_parent_symbols": sorted(parent_symbols),
        "target_symbol_count": len(target_symbols),
        "fetched_symbols": sorted(fetched_symbols),
        "failed_symbols": sorted(failed_symbols),
        "security_persistence": security_persist,
        "benchmark_persistence": benchmark_persist,
        "coverage_before": {
            "applicable": before.applicable_count,
            "present": before.present_count,
            "missing": before.missing_count,
            "partial": before.partial_count,
            "coverage_pct": before.coverage_pct,
        },
        "coverage_after": {
            "applicable": after.applicable_count,
            "present": after.present_count,
            "missing": after.missing_count,
            "partial": after.partial_count,
            "coverage_pct": after.coverage_pct,
        },
        "sector_parent_coverage_after": [
            {
                "sector": row.sector,
                "current_holdings_count": row.current_holdings_count,
                "parent_series": row.parent_series,
                "parent_source": row.parent_source,
                "history_available": row.history_available,
                "first_date": row.first_date,
                "last_date": row.last_date,
                "trading_days_available": row.trading_days_available,
            }
            for row in sector_after
        ],
    }
