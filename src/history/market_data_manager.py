"""WP-05 partitioned storage for market prices and return series."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from src.models.market_data_models import (
    BenchmarkReturnRow,
    HistoricalPriceRow,
    InvestableVehicleReturnRow,
)

SECURITY_PRICE_HEADERS = [
    "security_id",
    "symbol",
    "security_type",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "dividend",
    "split_ratio",
    "source_provider",
    "created_at_utc",
]

BENCHMARK_RETURN_HEADERS = [
    "benchmark_id",
    "symbol_or_index",
    "date",
    "adjusted_close",
    "cumulative_return",
    "source_provider",
]

INVESTABLE_RETURN_HEADERS = [
    "vehicle_id",
    "symbol",
    "date",
    "adjusted_close",
    "cumulative_return",
    "source_provider",
]


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, headers: Sequence[str], rows: Iterable[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def _append_immutable_rows(
    *,
    path: Path,
    headers: Sequence[str],
    rows: Sequence[Dict[str, object]],
    unique_fields: Sequence[str],
) -> int:
    existing = _read_csv_rows(path)
    existing_keys = {
        tuple(str(row.get(field, "")).strip() for field in unique_fields)
        for row in existing
    }

    appended: List[Dict[str, object]] = []
    for row in rows:
        key = tuple(str(row.get(field, "")).strip() for field in unique_fields)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        appended.append(row)

    all_rows = [*existing, *appended]
    all_rows_sorted = sorted(all_rows, key=lambda item: tuple(str(item.get(field, "")) for field in unique_fields))
    _write_csv(path, headers, all_rows_sorted)
    return len(appended)


def ensure_market_data_current_contracts(current_root: str | Path = "data/current") -> None:
    """Ensure mutable current output contracts exist."""

    current_root_path = Path(current_root)
    _write_csv(current_root_path / "security_prices.csv", SECURITY_PRICE_HEADERS, [])
    _write_csv(current_root_path / "benchmark_returns.csv", BENCHMARK_RETURN_HEADERS, [])
    _write_csv(current_root_path / "investable_vehicle_returns.csv", INVESTABLE_RETURN_HEADERS, [])


def persist_security_prices(
    *,
    rows: Sequence[HistoricalPriceRow],
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/prices",
) -> Dict[str, int]:
    """Persist mutable current security prices and immutable symbol partitions."""

    serialized = [
        {
            "security_id": row.security_id,
            "symbol": row.symbol,
            "security_type": row.security_type,
            "date": row.date,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "adjusted_close": row.adjusted_close,
            "volume": row.volume,
            "dividend": row.dividend,
            "split_ratio": row.split_ratio,
            "source_provider": row.source_provider,
            "created_at_utc": row.created_at_utc,
        }
        for row in rows
    ]

    current_output = Path(current_root) / "security_prices.csv"
    _write_csv(current_output, SECURITY_PRICE_HEADERS, sorted(serialized, key=lambda item: (item["symbol"], item["date"])))

    appended_total = 0
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for row in serialized:
        grouped.setdefault(str(row["symbol"]), []).append(row)

    for symbol, symbol_rows in grouped.items():
        partition_path = Path(history_root) / f"symbol={symbol}" / "prices.csv"
        appended_total += _append_immutable_rows(
            path=partition_path,
            headers=SECURITY_PRICE_HEADERS,
            rows=sorted(symbol_rows, key=lambda item: item["date"]),
            unique_fields=("symbol", "date"),
        )

    return {
        "current_rows": len(serialized),
        "history_rows_appended": appended_total,
        "symbol_partition_count": len(grouped),
    }


def persist_benchmark_returns(
    *,
    rows: Sequence[BenchmarkReturnRow],
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/benchmarks",
) -> Dict[str, int]:
    """Persist mutable benchmark returns and immutable benchmark partitions."""

    serialized = [
        {
            "benchmark_id": row.benchmark_id,
            "symbol_or_index": row.symbol_or_index,
            "date": row.date,
            "adjusted_close": row.adjusted_close,
            "cumulative_return": row.cumulative_return,
            "source_provider": row.source_provider,
        }
        for row in rows
    ]

    current_output = Path(current_root) / "benchmark_returns.csv"
    _write_csv(
        current_output,
        BENCHMARK_RETURN_HEADERS,
        sorted(serialized, key=lambda item: (item["benchmark_id"], item["date"])),
    )

    appended_total = 0
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for row in serialized:
        grouped.setdefault(str(row["benchmark_id"]), []).append(row)

    for benchmark_id, benchmark_rows in grouped.items():
        partition_path = Path(history_root) / f"benchmark_id={benchmark_id}" / "benchmark_returns.csv"
        appended_total += _append_immutable_rows(
            path=partition_path,
            headers=BENCHMARK_RETURN_HEADERS,
            rows=sorted(benchmark_rows, key=lambda item: item["date"]),
            unique_fields=("benchmark_id", "date"),
        )

    return {
        "current_rows": len(serialized),
        "history_rows_appended": appended_total,
        "benchmark_partition_count": len(grouped),
    }


def persist_investable_vehicle_returns(
    *,
    rows: Sequence[InvestableVehicleReturnRow],
    current_root: str | Path = "data/current",
    history_root: str | Path = "data/history/investable_vehicles",
) -> Dict[str, int]:
    """Persist mutable investable vehicle returns and immutable vehicle partitions."""

    serialized = [
        {
            "vehicle_id": row.vehicle_id,
            "symbol": row.symbol,
            "date": row.date,
            "adjusted_close": row.adjusted_close,
            "cumulative_return": row.cumulative_return,
            "source_provider": row.source_provider,
        }
        for row in rows
    ]

    current_output = Path(current_root) / "investable_vehicle_returns.csv"
    _write_csv(
        current_output,
        INVESTABLE_RETURN_HEADERS,
        sorted(serialized, key=lambda item: (item["vehicle_id"], item["date"])),
    )

    appended_total = 0
    grouped: Dict[str, List[Dict[str, object]]] = {}
    for row in serialized:
        grouped.setdefault(str(row["vehicle_id"]), []).append(row)

    for vehicle_id, vehicle_rows in grouped.items():
        partition_path = Path(history_root) / f"vehicle_id={vehicle_id}" / "vehicle_returns.csv"
        appended_total += _append_immutable_rows(
            path=partition_path,
            headers=INVESTABLE_RETURN_HEADERS,
            rows=sorted(vehicle_rows, key=lambda item: item["date"]),
            unique_fields=("vehicle_id", "date"),
        )

    return {
        "current_rows": len(serialized),
        "history_rows_appended": appended_total,
        "vehicle_partition_count": len(grouped),
    }
