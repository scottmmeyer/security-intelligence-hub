"""PIS benchmark attribution foundation (01B-A).

Builds canonical-date-aligned portfolio-vs-SPY return series and persists
interval results for downstream benchmark attribution layers.
"""

from __future__ import annotations

import csv
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from .canonical_daily import pis_canonical_history
from .storage import _read_csv_rows, _to_float


DEFAULT_BENCHMARK_SYMBOL = "SPY"
DEFAULT_ALIGNMENT_POLICY = "NEAREST_PRIOR_TRADING_DAY"

BENCHMARK_RETURN_SERIES_HEADERS = [
    "snapshot_date",
    "prior_snapshot_date",
    "benchmark_symbol",
    "benchmark_entry_date",
    "benchmark_exit_date",
    "benchmark_entry_price",
    "benchmark_exit_price",
    "benchmark_return_pct",
    "portfolio_return_pct",
    "excess_return_pct",
    "alignment_policy",
    "data_quality_status",
]

RECOMMENDATION_BENCHMARK_HEADERS = [
    "snapshot_date",
    "prior_snapshot_date",
    "recommendation_id",
    "symbol",
    "recommendation_source",
    "change_type",
    "directional_return_pct",
    "benchmark_symbol",
    "benchmark_return_pct",
    "recommendation_excess_return_pct",
    "lineage_confidence",
    "data_quality_status",
    "directional_attribution",
]

SOURCE_BENCHMARK_SUMMARY_HEADERS = [
    "recommendation_source",
    "matched_recommendations",
    "avg_directional_return_pct",
    "avg_benchmark_return_pct",
    "avg_excess_return_pct",
    "positive_alpha_count",
    "negative_alpha_count",
    "alpha_win_rate",
    "total_directional_attribution",
    "included_rows",
    "excluded_rows",
    "excluded_reason_counts",
]

_BENCHMARK_REFRESH_LOCK = threading.Lock()


class BenchmarkPriceProvider(Protocol):
    def get_prices(self, *, symbol: str, start_date: str, end_date: str) -> dict[str, float]:
        ...


@dataclass(frozen=True)
class BenchmarkAttributionConfig:
    benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL
    alignment_policy: str = DEFAULT_ALIGNMENT_POLICY


DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG = BenchmarkAttributionConfig()


class CsvBenchmarkPriceProvider:
    """Load benchmark adjusted-close history from local persisted CSVs."""

    def __init__(
        self,
        *,
        benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
        benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    ) -> None:
        self._benchmark_current_path = Path(benchmark_current_path)
        self._benchmark_snapshots_path = Path(benchmark_snapshots_path)

    def _load_current_rows(self, symbol: str) -> dict[str, float]:
        rows = _read_csv_rows(self._benchmark_current_path)
        out: dict[str, float] = {}
        for row in rows:
            row_symbol = str(row.get("symbol_or_index", "")).strip().upper()
            row_date = str(row.get("date", "")).strip()
            if row_symbol != symbol or not row_date:
                continue
            price = _to_float(row.get("adjusted_close", 0.0))
            if price > 0:
                out[row_date] = round(price, 8)
        return out

    def _load_snapshot_rows(self, symbol: str) -> dict[str, float]:
        rows = _read_csv_rows(self._benchmark_snapshots_path)
        out: dict[str, float] = {}
        for row in rows:
            row_symbol = str(row.get("benchmark_symbol", "")).strip().upper()
            row_date = str(row.get("snapshot_date", "")).strip()
            if row_symbol != symbol or not row_date:
                continue
            price = _to_float(row.get("adjusted_close", 0.0))
            if price > 0:
                out[row_date] = round(price, 8)
        return out

    def get_prices(self, *, symbol: str, start_date: str, end_date: str) -> dict[str, float]:
        symbol = str(symbol).strip().upper()
        current_rows = self._load_current_rows(symbol)
        snapshot_rows = self._load_snapshot_rows(symbol)

        merged: dict[str, float] = {}
        merged.update(snapshot_rows)
        merged.update(current_rows)

        if not merged:
            return {}

        lower = str(start_date)
        upper = str(end_date)
        return {
            d: p
            for d, p in merged.items()
            if lower <= str(d) <= upper
        }


class YFinanceBenchmarkPriceProvider:
    """Optional online fallback provider.

    This provider is only used when explicitly enabled by callers.
    """

    def get_prices(self, *, symbol: str, start_date: str, end_date: str) -> dict[str, float]:
        try:
            import yfinance as yf  # type: ignore
        except Exception:
            return {}

        try:
            hist = yf.Ticker(symbol).history(start=start_date, end=end_date, auto_adjust=True)
        except Exception:
            return {}

        if hist is None or hist.empty:
            return {}

        out: dict[str, float] = {}
        for idx, row in hist.iterrows():
            date_text = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
            price = _to_float(row.get("Close", 0.0))
            if price > 0:
                out[date_text] = round(price, 8)
        return out


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _nearest_prior_date(prices_by_date: dict[str, float], target_date: str) -> tuple[str, float] | tuple[None, None]:
    if not prices_by_date:
        return None, None
    eligible = [d for d in prices_by_date.keys() if str(d) <= str(target_date)]
    if not eligible:
        return None, None
    resolved_date = max(eligible)
    return resolved_date, float(prices_by_date[resolved_date])


def _map_series_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "snapshot_date": str(row.get("snapshot_date", "")),
        "prior_snapshot_date": str(row.get("prior_snapshot_date", "")),
        "benchmark_symbol": str(row.get("benchmark_symbol", "")),
        "benchmark_entry_date": str(row.get("benchmark_entry_date", "")),
        "benchmark_exit_date": str(row.get("benchmark_exit_date", "")),
        "benchmark_entry_price": round(_to_float(row.get("benchmark_entry_price", 0.0)), 8),
        "benchmark_exit_price": round(_to_float(row.get("benchmark_exit_price", 0.0)), 8),
        "benchmark_return_pct": round(_to_float(row.get("benchmark_return_pct", 0.0)), 6),
        "portfolio_return_pct": round(_to_float(row.get("portfolio_return_pct", 0.0)), 6),
        "excess_return_pct": round(_to_float(row.get("excess_return_pct", 0.0)), 6),
        "alignment_policy": str(row.get("alignment_policy", DEFAULT_ALIGNMENT_POLICY)),
        "data_quality_status": str(row.get("data_quality_status", "MISSING_BENCHMARK_DATA")),
    }


def _canonical_selected_rows(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
) -> list[dict[str, object]]:
    canonical_output = Path(canonical_output_path)
    if canonical_output.exists():
        history = _read_csv_rows(canonical_output)
    else:
        history = pis_canonical_history(
            index_path=canonical_index_path,
            output_path=canonical_output_path,
        ).get("history", [])
    selected = [
        row for row in history
        if str(row.get("canonical_snapshot_id", "")).strip()
    ]
    selected.sort(key=lambda row: str(row.get("snapshot_date", "")), reverse=True)
    return selected


def _resolve_price_map(
    *,
    provider: BenchmarkPriceProvider,
    symbol: str,
    start_date: str,
    end_date: str,
    allow_online_fallback: bool,
) -> dict[str, float]:
    prices = provider.get_prices(symbol=symbol, start_date=start_date, end_date=end_date)
    if prices or not allow_online_fallback:
        return prices

    fallback_provider = YFinanceBenchmarkPriceProvider()
    fallback_start = (datetime.fromisoformat(start_date) - timedelta(days=8)).date().isoformat()
    return fallback_provider.get_prices(symbol=symbol, start_date=fallback_start, end_date=end_date)


def compute_benchmark_return_series(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    output_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
    benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
) -> dict[str, object]:
    selected = _canonical_selected_rows(
        canonical_index_path=canonical_index_path,
        canonical_output_path=canonical_output_path,
    )
    if len(selected) < 2:
        _write_rows(Path(output_path), BENCHMARK_RETURN_SERIES_HEADERS, [])
        return {"series": [], "summary": {"interval_count": 0, "benchmark_symbol": config.benchmark_symbol}}

    start_date = str(selected[-1].get("snapshot_date", ""))
    end_date = str(selected[0].get("snapshot_date", ""))

    provider = price_provider or CsvBenchmarkPriceProvider(
        benchmark_current_path=benchmark_current_path,
        benchmark_snapshots_path=benchmark_snapshots_path,
    )
    seeded_start_date = (datetime.fromisoformat(start_date) - timedelta(days=8)).date().isoformat()
    prices_by_date = _resolve_price_map(
        provider=provider,
        symbol=config.benchmark_symbol,
        start_date=seeded_start_date,
        end_date=end_date,
        allow_online_fallback=allow_online_fallback,
    )

    rows: list[dict[str, object]] = []
    for idx in range(len(selected) - 1):
        current = selected[idx]
        prior = selected[idx + 1]

        current_date = str(current.get("snapshot_date", ""))
        prior_date = str(prior.get("snapshot_date", ""))

        prior_value = _to_float(prior.get("portfolio_value", 0.0))
        current_value = _to_float(current.get("portfolio_value", 0.0))

        portfolio_return_pct = 0.0
        portfolio_status = "OK"
        if prior_value <= 0:
            portfolio_status = "INVALID_PORTFOLIO_BASE"
        else:
            portfolio_return_pct = ((current_value - prior_value) / prior_value) * 100.0

        entry_date, entry_price = _nearest_prior_date(prices_by_date, prior_date)
        exit_date, exit_price = _nearest_prior_date(prices_by_date, current_date)

        benchmark_return_pct = 0.0
        quality_status = portfolio_status
        if entry_date is None or entry_price is None:
            quality_status = "MISSING_BENCHMARK_ENTRY"
        elif exit_date is None or exit_price is None:
            quality_status = "MISSING_BENCHMARK_EXIT"
        elif entry_price <= 0:
            quality_status = "INVALID_BENCHMARK_BASE"
        else:
            benchmark_return_pct = ((exit_price - entry_price) / entry_price) * 100.0
            if quality_status == "OK":
                quality_status = "OK"

        excess_return_pct = portfolio_return_pct - benchmark_return_pct

        rows.append(
            {
                "snapshot_date": current_date,
                "prior_snapshot_date": prior_date,
                "benchmark_symbol": config.benchmark_symbol,
                "benchmark_entry_date": entry_date or "",
                "benchmark_exit_date": exit_date or "",
                "benchmark_entry_price": round(entry_price or 0.0, 8),
                "benchmark_exit_price": round(exit_price or 0.0, 8),
                "benchmark_return_pct": round(benchmark_return_pct, 6),
                "portfolio_return_pct": round(portfolio_return_pct, 6),
                "excess_return_pct": round(excess_return_pct, 6),
                "alignment_policy": config.alignment_policy,
                "data_quality_status": quality_status,
            }
        )

    _write_rows(Path(output_path), BENCHMARK_RETURN_SERIES_HEADERS, rows)

    ok_rows = [r for r in rows if str(r.get("data_quality_status", "")) == "OK"]
    summary = {
        "interval_count": len(rows),
        "benchmark_symbol": config.benchmark_symbol,
        "ok_interval_count": len(ok_rows),
        "missing_interval_count": len(rows) - len(ok_rows),
        "average_benchmark_return_pct": round(
            sum(_to_float(r.get("benchmark_return_pct", 0.0)) for r in ok_rows) / len(ok_rows),
            6,
        ) if ok_rows else 0.0,
        "average_portfolio_return_pct": round(
            sum(_to_float(r.get("portfolio_return_pct", 0.0)) for r in rows) / len(rows),
            6,
        ) if rows else 0.0,
        "average_excess_return_pct": round(
            sum(_to_float(r.get("excess_return_pct", 0.0)) for r in rows) / len(rows),
            6,
        ) if rows else 0.0,
    }

    return {"series": rows, "summary": summary}


def _load_or_compute_series(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    output_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
    benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
) -> list[dict[str, str]]:
    output = Path(output_path)
    if not output.exists():
        with _BENCHMARK_REFRESH_LOCK:
            compute_benchmark_return_series(
                canonical_index_path=canonical_index_path,
                canonical_output_path=canonical_output_path,
                output_path=output_path,
                benchmark_current_path=benchmark_current_path,
                benchmark_snapshots_path=benchmark_snapshots_path,
                config=config,
                price_provider=price_provider,
                allow_online_fallback=allow_online_fallback,
            )
    rows = _read_csv_rows(output)
    rows.sort(key=lambda row: str(row.get("snapshot_date", "")), reverse=True)
    return rows


def pis_benchmark_returns(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    output_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
    benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
) -> dict[str, object]:
    rows = _load_or_compute_series(
        canonical_output_path=canonical_output_path,
        canonical_index_path=canonical_index_path,
        output_path=output_path,
        benchmark_current_path=benchmark_current_path,
        benchmark_snapshots_path=benchmark_snapshots_path,
        config=config,
        price_provider=price_provider,
        allow_online_fallback=allow_online_fallback,
    )
    mapped = [_map_series_row(row) for row in rows]
    return {
        "benchmark_symbol": config.benchmark_symbol,
        "alignment_policy": config.alignment_policy,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "series": mapped,
    }


def pis_benchmark_latest(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    output_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
    benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
) -> dict[str, object]:
    payload = pis_benchmark_returns(
        canonical_output_path=canonical_output_path,
        canonical_index_path=canonical_index_path,
        output_path=output_path,
        benchmark_current_path=benchmark_current_path,
        benchmark_snapshots_path=benchmark_snapshots_path,
        config=config,
        price_provider=price_provider,
        allow_online_fallback=allow_online_fallback,
    )
    latest = payload["series"][0] if payload["series"] else None
    return {
        "benchmark_symbol": payload["benchmark_symbol"],
        "alignment_policy": payload["alignment_policy"],
        "latest": latest,
    }


def pis_benchmark_summary(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    output_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
    benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
) -> dict[str, object]:
    rows = _load_or_compute_series(
        canonical_output_path=canonical_output_path,
        canonical_index_path=canonical_index_path,
        output_path=output_path,
        benchmark_current_path=benchmark_current_path,
        benchmark_snapshots_path=benchmark_snapshots_path,
        config=config,
        price_provider=price_provider,
        allow_online_fallback=allow_online_fallback,
    )
    mapped = [_map_series_row(row) for row in rows]
    ok_rows = [row for row in mapped if str(row.get("data_quality_status", "")) == "OK"]
    return {
        "benchmark_symbol": config.benchmark_symbol,
        "alignment_policy": config.alignment_policy,
        "summary": {
            "interval_count": len(mapped),
            "ok_interval_count": len(ok_rows),
            "missing_interval_count": len(mapped) - len(ok_rows),
            "latest_snapshot_date": str(mapped[0].get("snapshot_date", "")) if mapped else "",
            "average_benchmark_return_pct": round(
                sum(_to_float(row.get("benchmark_return_pct", 0.0)) for row in ok_rows) / len(ok_rows),
                6,
            ) if ok_rows else 0.0,
            "average_portfolio_return_pct": round(
                sum(_to_float(row.get("portfolio_return_pct", 0.0)) for row in mapped) / len(mapped),
                6,
            ) if mapped else 0.0,
            "average_excess_return_pct": round(
                sum(_to_float(row.get("excess_return_pct", 0.0)) for row in mapped) / len(mapped),
                6,
            ) if mapped else 0.0,
        },
    }


def _map_recommendation_record(row: dict[str, str]) -> dict[str, object]:
    return {
        "snapshot_date": str(row.get("snapshot_date", "")),
        "prior_snapshot_date": str(row.get("prior_snapshot_date", "")),
        "recommendation_id": str(row.get("recommendation_id", "")),
        "symbol": str(row.get("symbol", "")),
        "recommendation_source": str(row.get("recommendation_source", "")),
        "change_type": str(row.get("change_type", "")),
        "directional_return_pct": round(_to_float(row.get("directional_return_pct", 0.0)), 6),
        "benchmark_symbol": str(row.get("benchmark_symbol", DEFAULT_BENCHMARK_SYMBOL)),
        "benchmark_return_pct": round(_to_float(row.get("benchmark_return_pct", 0.0)), 6),
        "recommendation_excess_return_pct": round(_to_float(row.get("recommendation_excess_return_pct", 0.0)), 6),
        "lineage_confidence": str(row.get("lineage_confidence", "")),
        "data_quality_status": str(row.get("data_quality_status", "MISSING_BENCHMARK_INTERVAL")),
        "directional_attribution": round(_to_float(row.get("directional_attribution", 0.0)), 2),
    }


def _map_source_summary(row: dict[str, str]) -> dict[str, object]:
    excluded_reason_counts_raw = str(row.get("excluded_reason_counts", "{}")).strip() or "{}"
    try:
        excluded_reason_counts = json.loads(excluded_reason_counts_raw)
    except Exception:
        excluded_reason_counts = {}
    return {
        "recommendation_source": str(row.get("recommendation_source", "")),
        "matched_recommendations": int(float(str(row.get("matched_recommendations", "0") or "0"))),
        "avg_directional_return_pct": round(_to_float(row.get("avg_directional_return_pct", 0.0)), 6),
        "avg_benchmark_return_pct": round(_to_float(row.get("avg_benchmark_return_pct", 0.0)), 6),
        "avg_excess_return_pct": round(_to_float(row.get("avg_excess_return_pct", 0.0)), 6),
        "positive_alpha_count": int(float(str(row.get("positive_alpha_count", "0") or "0"))),
        "negative_alpha_count": int(float(str(row.get("negative_alpha_count", "0") or "0"))),
        "alpha_win_rate": round(_to_float(row.get("alpha_win_rate", 0.0)), 6),
        "total_directional_attribution": round(_to_float(row.get("total_directional_attribution", 0.0)), 2),
        "included_rows": int(float(str(row.get("included_rows", "0") or "0"))),
        "excluded_rows": int(float(str(row.get("excluded_rows", "0") or "0"))),
        "excluded_reason_counts": excluded_reason_counts,
    }


def compute_benchmark_recommendation_attribution(
    *,
    benchmark_series_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    attribution_records_path: str | Path = "data/history/pis/attribution/attribution_records.csv",
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    recommendation_output_path: str | Path = "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv",
    source_output_path: str | Path = "data/history/pis/benchmark_attribution/source_benchmark_summary.csv",
    benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL,
) -> dict[str, object]:
    benchmark_rows = _read_csv_rows(Path(benchmark_series_path))
    attribution_rows = _read_csv_rows(Path(attribution_records_path))
    change_rows = _read_csv_rows(Path(change_records_path))

    benchmark_by_interval: dict[tuple[str, str], dict[str, str]] = {}
    for row in benchmark_rows:
        key = (str(row.get("snapshot_date", "")), str(row.get("prior_snapshot_date", "")))
        if key[0] and key[1]:
            benchmark_by_interval[key] = row

    prior_by_change_key: dict[tuple[str, str], str] = {}
    for row in change_rows:
        key = (str(row.get("snapshot_id", "")), str(row.get("change_id", "")))
        prior_by_change_key[key] = str(row.get("prior_snapshot_date", ""))

    records: list[dict[str, object]] = []
    for row in attribution_rows:
        recommendation_id = str(row.get("matched_recommendation_id", "")).strip()
        if not recommendation_id:
            continue

        snapshot_date = str(row.get("snapshot_date", ""))
        snapshot_id = str(row.get("snapshot_id", ""))
        change_id = str(row.get("change_id", ""))
        prior_snapshot_date = prior_by_change_key.get((snapshot_id, change_id), "")

        benchmark_row = benchmark_by_interval.get((snapshot_date, prior_snapshot_date))
        benchmark_return_pct = 0.0
        quality_status = "MISSING_BENCHMARK_INTERVAL"
        if benchmark_row is not None:
            benchmark_return_pct = _to_float(benchmark_row.get("benchmark_return_pct", 0.0))
            quality_status = str(benchmark_row.get("data_quality_status", "MISSING_BENCHMARK_INTERVAL"))

        directional_return_pct = _to_float(row.get("directional_return_pct", 0.0))
        recommendation_excess_return_pct = directional_return_pct - benchmark_return_pct

        records.append(
            {
                "snapshot_date": snapshot_date,
                "prior_snapshot_date": prior_snapshot_date,
                "recommendation_id": recommendation_id,
                "symbol": str(row.get("symbol", "")),
                "recommendation_source": str(row.get("recommendation_source", "") or "OTHER"),
                "change_type": str(row.get("change_type", "")),
                "directional_return_pct": round(directional_return_pct, 6),
                "benchmark_symbol": str(benchmark_row.get("benchmark_symbol", benchmark_symbol)) if benchmark_row else benchmark_symbol,
                "benchmark_return_pct": round(benchmark_return_pct, 6),
                "recommendation_excess_return_pct": round(recommendation_excess_return_pct, 6),
                "lineage_confidence": str(row.get("confidence", "")),
                "data_quality_status": quality_status,
                "directional_attribution": round(_to_float(row.get("directional_attribution", 0.0)), 2),
            }
        )

    records.sort(key=lambda r: (str(r.get("snapshot_date", "")), str(r.get("recommendation_id", ""))), reverse=True)
    _write_rows(Path(recommendation_output_path), RECOMMENDATION_BENCHMARK_HEADERS, records)

    by_source: dict[str, dict[str, object]] = {}
    for row in records:
        source = str(row.get("recommendation_source", "") or "OTHER")
        agg = by_source.setdefault(
            source,
            {
                "recommendation_source": source,
                "matched_recommendations": 0,
                "included_rows": 0,
                "excluded_rows": 0,
                "_sum_directional": 0.0,
                "_sum_benchmark": 0.0,
                "_sum_excess": 0.0,
                "positive_alpha_count": 0,
                "negative_alpha_count": 0,
                "total_directional_attribution": 0.0,
                "_excluded_reason_counts": {},
            },
        )
        agg["matched_recommendations"] = int(agg["matched_recommendations"]) + 1

        quality = str(row.get("data_quality_status", ""))
        if quality == "OK":
            agg["included_rows"] = int(agg["included_rows"]) + 1
            directional = _to_float(row.get("directional_return_pct", 0.0))
            benchmark = _to_float(row.get("benchmark_return_pct", 0.0))
            excess = _to_float(row.get("recommendation_excess_return_pct", 0.0))
            agg["_sum_directional"] = float(agg["_sum_directional"]) + directional
            agg["_sum_benchmark"] = float(agg["_sum_benchmark"]) + benchmark
            agg["_sum_excess"] = float(agg["_sum_excess"]) + excess
            agg["total_directional_attribution"] = float(agg["total_directional_attribution"]) + _to_float(
                row.get("directional_attribution", 0.0)
            )
            if excess > 0:
                agg["positive_alpha_count"] = int(agg["positive_alpha_count"]) + 1
            elif excess < 0:
                agg["negative_alpha_count"] = int(agg["negative_alpha_count"]) + 1
        else:
            agg["excluded_rows"] = int(agg["excluded_rows"]) + 1
            reason_counts = agg["_excluded_reason_counts"]
            reason_counts[quality] = int(reason_counts.get(quality, 0)) + 1

    source_rows: list[dict[str, object]] = []
    for source, agg in sorted(by_source.items(), key=lambda kv: kv[0]):
        included_rows = int(agg["included_rows"])
        source_rows.append(
            {
                "recommendation_source": source,
                "matched_recommendations": int(agg["matched_recommendations"]),
                "avg_directional_return_pct": round(float(agg["_sum_directional"]) / included_rows, 6) if included_rows else 0.0,
                "avg_benchmark_return_pct": round(float(agg["_sum_benchmark"]) / included_rows, 6) if included_rows else 0.0,
                "avg_excess_return_pct": round(float(agg["_sum_excess"]) / included_rows, 6) if included_rows else 0.0,
                "positive_alpha_count": int(agg["positive_alpha_count"]),
                "negative_alpha_count": int(agg["negative_alpha_count"]),
                "alpha_win_rate": round((int(agg["positive_alpha_count"]) / included_rows) * 100.0, 6) if included_rows else 0.0,
                "total_directional_attribution": round(float(agg["total_directional_attribution"]), 2),
                "included_rows": included_rows,
                "excluded_rows": int(agg["excluded_rows"]),
                "excluded_reason_counts": json.dumps(agg["_excluded_reason_counts"], sort_keys=True),
            }
        )

    _write_rows(Path(source_output_path), SOURCE_BENCHMARK_SUMMARY_HEADERS, source_rows)

    excluded_reason_counts: dict[str, int] = {}
    for row in records:
        quality = str(row.get("data_quality_status", ""))
        if quality != "OK":
            excluded_reason_counts[quality] = int(excluded_reason_counts.get(quality, 0)) + 1

    return {
        "recommendation_records": records,
        "source_summary": source_rows,
        "quality": {
            "included_rows": sum(1 for row in records if str(row.get("data_quality_status", "")) == "OK"),
            "excluded_rows": sum(1 for row in records if str(row.get("data_quality_status", "")) != "OK"),
            "excluded_reason_counts": excluded_reason_counts,
        },
    }


def _load_or_compute_recommendation_tables(
    *,
    benchmark_series_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    attribution_records_path: str | Path = "data/history/pis/attribution/attribution_records.csv",
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    recommendation_output_path: str | Path = "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv",
    source_output_path: str | Path = "data/history/pis/benchmark_attribution/source_benchmark_summary.csv",
    benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    with _BENCHMARK_REFRESH_LOCK:
        payload = compute_benchmark_recommendation_attribution(
            benchmark_series_path=benchmark_series_path,
            attribution_records_path=attribution_records_path,
            change_records_path=change_records_path,
            recommendation_output_path=recommendation_output_path,
            source_output_path=source_output_path,
            benchmark_symbol=benchmark_symbol,
        )
    recommendation_rows = _read_csv_rows(Path(recommendation_output_path))
    source_rows = _read_csv_rows(Path(source_output_path))
    recommendation_rows.sort(
        key=lambda row: (str(row.get("snapshot_date", "")), str(row.get("recommendation_id", ""))),
        reverse=True,
    )
    source_rows.sort(key=lambda row: str(row.get("recommendation_source", "")))
    return recommendation_rows, source_rows, payload.get("quality", {})


def pis_benchmark_recommendations(
    *,
    benchmark_series_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    attribution_records_path: str | Path = "data/history/pis/attribution/attribution_records.csv",
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    recommendation_output_path: str | Path = "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv",
    source_output_path: str | Path = "data/history/pis/benchmark_attribution/source_benchmark_summary.csv",
    benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL,
) -> dict[str, object]:
    recommendation_rows, _, quality = _load_or_compute_recommendation_tables(
        benchmark_series_path=benchmark_series_path,
        attribution_records_path=attribution_records_path,
        change_records_path=change_records_path,
        recommendation_output_path=recommendation_output_path,
        source_output_path=source_output_path,
        benchmark_symbol=benchmark_symbol,
    )
    return {
        "benchmark_symbol": benchmark_symbol,
        "records": [_map_recommendation_record(row) for row in recommendation_rows],
        "quality": quality,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def pis_benchmark_sources(
    *,
    benchmark_series_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    attribution_records_path: str | Path = "data/history/pis/attribution/attribution_records.csv",
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    recommendation_output_path: str | Path = "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv",
    source_output_path: str | Path = "data/history/pis/benchmark_attribution/source_benchmark_summary.csv",
    benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL,
) -> dict[str, object]:
    _, source_rows, quality = _load_or_compute_recommendation_tables(
        benchmark_series_path=benchmark_series_path,
        attribution_records_path=attribution_records_path,
        change_records_path=change_records_path,
        recommendation_output_path=recommendation_output_path,
        source_output_path=source_output_path,
        benchmark_symbol=benchmark_symbol,
    )
    return {
        "benchmark_symbol": benchmark_symbol,
        "source_summary": [_map_source_summary(row) for row in source_rows],
        "quality": quality,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def pis_benchmark_latest(
    *,
    canonical_index_path: str | Path = "data/history/pis/pis_snapshot_index.csv",
    canonical_output_path: str | Path = "data/history/pis/canonical/canonical_daily_snapshots.csv",
    output_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    benchmark_current_path: str | Path = "data/current/benchmark_returns.csv",
    benchmark_snapshots_path: str | Path = "data/history/benchmarks/benchmark_snapshots.csv",
    benchmark_series_path: str | Path = "data/history/pis/benchmark_attribution/benchmark_return_series.csv",
    attribution_records_path: str | Path = "data/history/pis/attribution/attribution_records.csv",
    change_records_path: str | Path = "data/history/pis/changes/change_records.csv",
    recommendation_output_path: str | Path = "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv",
    source_output_path: str | Path = "data/history/pis/benchmark_attribution/source_benchmark_summary.csv",
    config: BenchmarkAttributionConfig = DEFAULT_BENCHMARK_ATTRIBUTION_CONFIG,
    price_provider: BenchmarkPriceProvider | None = None,
    allow_online_fallback: bool = False,
) -> dict[str, object]:
    portfolio_latest = pis_benchmark_returns(
        canonical_index_path=canonical_index_path,
        canonical_output_path=canonical_output_path,
        output_path=output_path,
        benchmark_current_path=benchmark_current_path,
        benchmark_snapshots_path=benchmark_snapshots_path,
        config=config,
        price_provider=price_provider,
        allow_online_fallback=allow_online_fallback,
    )
    records_payload = pis_benchmark_recommendations(
        benchmark_series_path=benchmark_series_path,
        attribution_records_path=attribution_records_path,
        change_records_path=change_records_path,
        recommendation_output_path=recommendation_output_path,
        source_output_path=source_output_path,
        benchmark_symbol=config.benchmark_symbol,
    )
    sources_payload = pis_benchmark_sources(
        benchmark_series_path=benchmark_series_path,
        attribution_records_path=attribution_records_path,
        change_records_path=change_records_path,
        recommendation_output_path=recommendation_output_path,
        source_output_path=source_output_path,
        benchmark_symbol=config.benchmark_symbol,
    )

    records = list(records_payload.get("records", []))
    included_records = [row for row in records if str(row.get("data_quality_status", "")) == "OK"]
    included_records.sort(key=lambda row: float(row.get("recommendation_excess_return_pct", 0.0)), reverse=True)
    top_positive = [row for row in included_records if float(row.get("recommendation_excess_return_pct", 0.0)) > 0][:5]
    worst_negative = [
        rec
        for rec in sorted(included_records, key=lambda r: float(r.get("recommendation_excess_return_pct", 0.0)))
        if float(rec.get("recommendation_excess_return_pct", 0.0)) < 0
    ][:5]

    source_summary = list(sources_payload.get("source_summary", []))
    source_summary.sort(
        key=lambda row: (
            float(row.get("avg_excess_return_pct", 0.0)),
            float(row.get("total_directional_attribution", 0.0)),
        ),
        reverse=True,
    )

    latest_portfolio = portfolio_latest.get("series", [None])[0] if portfolio_latest.get("series") else None
    return {
        "benchmark_symbol": config.benchmark_symbol,
        "alignment_policy": config.alignment_policy,
        "latest_portfolio_excess_return": latest_portfolio,
        "top_positive_alpha_recommendations": top_positive,
        "worst_negative_alpha_recommendations": worst_negative,
        "source_alpha_ranking": source_summary,
        "quality": records_payload.get("quality", {}),
    }
