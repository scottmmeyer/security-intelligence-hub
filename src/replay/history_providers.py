"""WP-05 historical market data providers and replay series interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Protocol, Sequence

from src.models.market_data_models import (
    BenchmarkReturnRow,
    HistoricalPriceRow,
    InvestableVehicleReturnRow,
)
from src.replay.registry_loader import (
    derive_benchmark_symbols_from_registry,
    derive_vehicle_symbols_from_registry,
    load_benchmark_category_registry,
    load_investable_vehicle_registry,
)


@dataclass(frozen=True)
class PricePoint:
    """Deterministic historical value observation."""

    date: str
    value: float


class SecurityPriceHistoryProvider(Protocol):
    """Replay-facing interface for symbol value series."""

    def get_symbol_series(self, symbol: str, start_date: str, end_date: str) -> Sequence[PricePoint]:
        ...


class BenchmarkHistoryProvider(Protocol):
    """Replay-facing interface for benchmark value series."""

    def get_benchmark_series(
        self, benchmark_symbol_or_index: str, start_date: str, end_date: str
    ) -> Sequence[PricePoint]:
        ...


class InvestableVehicleHistoryProvider(Protocol):
    """Replay-facing interface for investable vehicle value series."""

    def get_vehicle_series(self, symbol: str, start_date: str, end_date: str) -> Sequence[PricePoint]:
        ...


class HistoricalPriceProvider(Protocol):
    """Canonical historical price provider abstraction."""

    def get_historical_prices(
        self,
        *,
        security_id: str,
        symbol: str,
        security_type: str,
        start_date: str,
        end_date: str,
    ) -> Sequence[HistoricalPriceRow]:
        ...


class BenchmarkReturnProvider(Protocol):
    """Canonical benchmark return provider abstraction."""

    def get_benchmark_returns(
        self,
        *,
        benchmark_id: str,
        symbol_or_index: str,
        start_date: str,
        end_date: str,
    ) -> Sequence[BenchmarkReturnRow]:
        ...


class InvestableVehicleReturnProvider(Protocol):
    """Canonical investable vehicle return provider abstraction."""

    def get_investable_vehicle_returns(
        self,
        *,
        vehicle_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Sequence[InvestableVehicleReturnRow]:
        ...


class NullSecurityPriceHistoryProvider:
    def get_symbol_series(self, symbol: str, start_date: str, end_date: str) -> Sequence[PricePoint]:
        return []


class NullBenchmarkHistoryProvider:
    def get_benchmark_series(
        self, benchmark_symbol_or_index: str, start_date: str, end_date: str
    ) -> Sequence[PricePoint]:
        return []


class NullInvestableVehicleHistoryProvider:
    def get_vehicle_series(self, symbol: str, start_date: str, end_date: str) -> Sequence[PricePoint]:
        return []


class YahooHistoricalPriceProvider(HistoricalPriceProvider, SecurityPriceHistoryProvider):
    """Yahoo-style daily history provider with deterministic row conversion.

    Supports both single-symbol and multi-symbol (batch) price retrieval.
    Batch download is preferred for FULL_UNIVERSE and TOP_N_STRATEGY curve
    building to minimise round-trips to Yahoo Finance.
    """

    SOURCE_PROVIDER = "YAHOO_FINANCE"

    def __init__(self) -> None:
        self._series_cache: Dict[tuple[str, str, str], List[PricePoint]] = {}
        self._price_cache: Dict[tuple[str, str, str, str], List[HistoricalPriceRow]] = {}
        self._batch_cache: Dict[tuple[tuple[str, ...], str, str], Dict[str, List[PricePoint]]] = {}

    def get_symbol_series(self, symbol: str, start_date: str, end_date: str) -> Sequence[PricePoint]:
        cache_key = (symbol.upper(), start_date, end_date)
        if cache_key in self._series_cache:
            return list(self._series_cache[cache_key])

        rows = self.get_historical_prices(
            security_id=f"YF:{symbol.upper()}",
            symbol=symbol,
            security_type="UNKNOWN",
            start_date=start_date,
            end_date=end_date,
        )
        points = [PricePoint(date=row.date, value=float(row.adjusted_close)) for row in rows]
        self._series_cache[cache_key] = points
        return list(points)

    def get_historical_prices(
        self,
        *,
        security_id: str,
        symbol: str,
        security_type: str,
        start_date: str,
        end_date: str,
    ) -> Sequence[HistoricalPriceRow]:
        cache_key = (security_id, symbol.upper(), start_date, end_date)
        if cache_key in self._price_cache:
            return list(self._price_cache[cache_key])

        rows = self._download_rows(symbol=symbol, start_date=start_date, end_date=end_date)
        created_at = datetime.now(timezone.utc).isoformat()
        output: List[HistoricalPriceRow] = []

        for row in rows:
            output.append(
                HistoricalPriceRow(
                    security_id=security_id,
                    symbol=symbol.upper(),
                    security_type=security_type,
                    date=str(row["date"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    adjusted_close=float(row["adjusted_close"]),
                    volume=int(row["volume"]),
                    dividend=float(row["dividend"]),
                    split_ratio=float(row["split_ratio"]),
                    source_provider=self.SOURCE_PROVIDER,
                    created_at_utc=created_at,
                )
            )

        self._price_cache[cache_key] = output
        self._series_cache[(symbol.upper(), start_date, end_date)] = [
            PricePoint(date=item.date, value=item.adjusted_close) for item in output
        ]
        return list(output)

    def _download_rows(self, *, symbol: str, start_date: str, end_date: str) -> List[Dict[str, object]]:
        try:
            import yfinance as yf
        except Exception:
            return []

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date) + timedelta(days=1)

        frame = yf.download(
            tickers=symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=True,
            actions=True,
            progress=False,
            threads=False,
        )

        if frame is None or len(frame.index) == 0:
            return []

        # yfinance can return MultiIndex columns even for a single ticker.
        # Normalize to single-level price columns so row lookups are scalar.
        if getattr(frame.columns, "nlevels", 1) > 1:
            level_values = [str(item) for item in frame.columns.get_level_values(-1)]
            preferred = None
            for candidate in (symbol, symbol.upper(), symbol.lower()):
                if candidate in level_values:
                    preferred = candidate
                    break
            if preferred is None and level_values:
                preferred = level_values[0]
            if preferred is not None:
                frame = frame.xs(preferred, axis=1, level=-1, drop_level=True)

        def _coerce_scalar(value: object, default: float) -> float:
            if value is None:
                return default
            if hasattr(value, "iloc"):
                try:
                    if len(value) == 0:
                        return default
                    value = value.iloc[0]
                except Exception:
                    return default
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return default
            if numeric != numeric:  # NaN guard
                return default
            return numeric

        rows: List[Dict[str, object]] = []
        for index, row in frame.iterrows():
            close = _coerce_scalar(row.get("Close"), 0.0)
            if close == 0.0:
                continue

            rows.append(
                {
                    "date": index.date().isoformat(),
                    "open": _coerce_scalar(row.get("Open"), 0.0),
                    "high": _coerce_scalar(row.get("High"), 0.0),
                    "low": _coerce_scalar(row.get("Low"), 0.0),
                    "close": float(close),
                    "adjusted_close": float(close),
                    "volume": int(_coerce_scalar(row.get("Volume"), 0.0)),
                    "dividend": _coerce_scalar(row.get("Dividends"), 0.0),
                    "split_ratio": _coerce_scalar(row.get("Stock Splits"), 0.0),
                }
            )

        return rows

    def get_batch_prices(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, List[PricePoint]]:
        """Download adjusted-close series for multiple symbols in one call.

        Preferred over calling get_symbol_series() in a loop for FULL_UNIVERSE
        and TOP_N_STRATEGY curve building.  Missing or invalid symbols return an
        empty list — no exception is raised for individual symbol failures.
        """
        if not symbols:
            return {}

        symbols_upper = tuple(sorted(s.upper() for s in symbols))
        cache_key = (symbols_upper, start_date, end_date)
        if cache_key in self._batch_cache:
            return {s.upper(): list(self._batch_cache[cache_key].get(s.upper(), [])) for s in symbols}

        result = self._download_batch(
            symbols=[s.upper() for s in symbols],
            start_date=start_date,
            end_date=end_date,
        )
        self._batch_cache[cache_key] = result
        # Back-fill per-symbol cache so subsequent get_symbol_series() calls are instant
        for sym, pts in result.items():
            self._series_cache[(sym, start_date, end_date)] = pts
        return {s.upper(): list(result.get(s.upper(), [])) for s in symbols}

    def _download_batch(
        self,
        *,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, List[PricePoint]]:
        """Internal: yfinance multi-ticker download. Returns {SYMBOL: [PricePoint]}."""
        try:
            import yfinance as yf
        except Exception:
            return {s: [] for s in symbols}

        start = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date) + timedelta(days=1)

        try:
            frame = yf.download(
                tickers=list(symbols),
                start=start.isoformat(),
                end=end_dt.isoformat(),
                interval="1d",
                auto_adjust=True,
                actions=True,
                progress=False,
                threads=False,
                group_by="ticker",
            )
        except Exception:
            return {s: [] for s in symbols}

        if frame is None or len(frame.index) == 0:
            return {s: [] for s in symbols}

        def _coerce_scalar(value: object, default: float) -> float:
            if value is None:
                return default
            if hasattr(value, "iloc"):
                try:
                    if len(value) == 0:
                        return default
                    value = value.iloc[0]
                except Exception:
                    return default
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return default
            if numeric != numeric:
                return default
            return numeric

        # yfinance batch layout depends on version; try group_by="ticker" (top-level=sym)
        # then fall back to xs-based slicing.
        nlevels = getattr(frame.columns, "nlevels", 1)
        result: Dict[str, List[PricePoint]] = {}

        for sym in symbols:
            pts: List[PricePoint] = []
            try:
                if nlevels > 1:
                    try:
                        sym_frame = frame[sym]
                    except KeyError:
                        try:
                            sym_frame = frame.xs(sym, axis=1, level=0)
                        except Exception:
                            try:
                                sym_frame = frame.xs(sym, axis=1, level=1)
                            except Exception:
                                result[sym] = []
                                continue
                else:
                    sym_frame = frame

                for index, row in sym_frame.iterrows():
                    close = _coerce_scalar(row.get("Close"), 0.0)
                    if close == 0.0:
                        continue
                    pts.append(PricePoint(date=index.date().isoformat(), value=float(close)))
            except Exception:
                pts = []
            result[sym] = pts

        return result


def _to_cumulative_rows(*, values: Sequence[PricePoint], row_factory):
    ordered = ensure_chronological(values)
    if not ordered:
        return []

    base = ordered[0].value
    if base == 0:
        return []

    rows = []
    for point in ordered:
        rows.append(row_factory(point.date, float(point.value), float((point.value / base) - 1.0)))
    return rows


class YahooBenchmarkProvider(BenchmarkReturnProvider, BenchmarkHistoryProvider):
    """Benchmark return provider using Yahoo historical values.

    Phase D: allowed symbols are derived from the benchmark registry YAML rather than
    a hardcoded frozenset. Pass ``allowed_symbols`` explicitly in tests or when the
    default registry path is unavailable.
    """

    SOURCE_PROVIDER = "YAHOO_FINANCE"
    _DEFAULT_REGISTRY_PATH = "config/benchmark_category_registry.yaml"

    def __init__(
        self,
        historical_provider: HistoricalPriceProvider | None = None,
        allowed_symbols: frozenset | None = None,
    ) -> None:
        self._historical_provider = historical_provider or YahooHistoricalPriceProvider()
        self._cache: Dict[tuple[str, str, str], List[BenchmarkReturnRow]] = {}
        if allowed_symbols is not None:
            self._allowed_symbols: frozenset = allowed_symbols
        else:
            _registry = load_benchmark_category_registry(self._DEFAULT_REGISTRY_PATH)
            self._allowed_symbols = derive_benchmark_symbols_from_registry(_registry)

    def get_benchmark_series(
        self, benchmark_symbol_or_index: str, start_date: str, end_date: str
    ) -> Sequence[PricePoint]:
        rows = self.get_benchmark_returns(
            benchmark_id=f"BENCHMARK:{benchmark_symbol_or_index}",
            symbol_or_index=benchmark_symbol_or_index,
            start_date=start_date,
            end_date=end_date,
        )
        return [PricePoint(date=row.date, value=row.value) for row in rows]

    def get_benchmark_returns(
        self,
        *,
        benchmark_id: str,
        symbol_or_index: str,
        start_date: str,
        end_date: str,
    ) -> Sequence[BenchmarkReturnRow]:
        if symbol_or_index.upper() not in self._allowed_symbols:
            raise ValueError(
                "Unsupported benchmark symbol for WP-05A foundation: "
                f"{symbol_or_index}. Supported symbols: {sorted(self._allowed_symbols)}"
            )

        cache_key = (benchmark_id, start_date, end_date)
        if cache_key in self._cache:
            return list(self._cache[cache_key])

        prices = self._historical_provider.get_historical_prices(
            security_id=f"BENCH:{benchmark_id}",
            symbol=symbol_or_index,
            security_type="BENCHMARK_INDEX",
            start_date=start_date,
            end_date=end_date,
        )
        points = [PricePoint(date=row.date, value=row.adjusted_close) for row in prices]
        rows = _to_cumulative_rows(
            values=points,
            row_factory=lambda d, v, c: BenchmarkReturnRow(
                benchmark_id=benchmark_id,
                symbol_or_index=symbol_or_index,
                date=d,
                adjusted_close=round(v, 8),
                cumulative_return=round(c, 8),
                source_provider=self.SOURCE_PROVIDER,
            ),
        )
        self._cache[cache_key] = rows
        return list(rows)


class YahooInvestableVehicleProvider(
    InvestableVehicleReturnProvider,
    InvestableVehicleHistoryProvider,
):
    """Investable vehicle return provider using Yahoo historical values.

    Phase D: allowed symbols are derived from the investable vehicle registry YAML rather
    than a hardcoded frozenset. Pass ``allowed_symbols`` explicitly in tests or when the
    default registry path is unavailable.
    """

    SOURCE_PROVIDER = "YAHOO_FINANCE"
    _DEFAULT_REGISTRY_PATH = "config/investable_vehicle_registry.yaml"

    def __init__(
        self,
        historical_provider: HistoricalPriceProvider | None = None,
        allowed_symbols: frozenset | None = None,
    ) -> None:
        self._historical_provider = historical_provider or YahooHistoricalPriceProvider()
        self._cache: Dict[tuple[str, str, str], List[InvestableVehicleReturnRow]] = {}
        if allowed_symbols is not None:
            self._allowed_symbols: frozenset = allowed_symbols
        else:
            _registry = load_investable_vehicle_registry(self._DEFAULT_REGISTRY_PATH)
            self._allowed_symbols = derive_vehicle_symbols_from_registry(_registry)

    def get_vehicle_series(self, symbol: str, start_date: str, end_date: str) -> Sequence[PricePoint]:
        rows = self.get_investable_vehicle_returns(
            vehicle_id=f"VEHICLE:{symbol}",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        return [PricePoint(date=row.date, value=row.value) for row in rows]

    def get_investable_vehicle_returns(
        self,
        *,
        vehicle_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Sequence[InvestableVehicleReturnRow]:
        if symbol.upper() not in self._allowed_symbols:
            raise ValueError(
                "Unsupported investable vehicle symbol for WP-05A foundation: "
                f"{symbol}. Supported symbols: {sorted(self._allowed_symbols)}"
            )

        cache_key = (vehicle_id, start_date, end_date)
        if cache_key in self._cache:
            return list(self._cache[cache_key])

        prices = self._historical_provider.get_historical_prices(
            security_id=f"VEH:{vehicle_id}",
            symbol=symbol,
            security_type="ETF",
            start_date=start_date,
            end_date=end_date,
        )
        points = [PricePoint(date=row.date, value=row.adjusted_close) for row in prices]

        rows = _to_cumulative_rows(
            values=points,
            row_factory=lambda d, v, c: InvestableVehicleReturnRow(
                vehicle_id=vehicle_id,
                symbol=symbol,
                date=d,
                adjusted_close=round(v, 8),
                cumulative_return=round(c, 8),
                source_provider=self.SOURCE_PROVIDER,
            ),
        )
        self._cache[cache_key] = rows
        return list(rows)


# Backward-compatible aliases while callers migrate to WP-05A names.
YahooFinanceHistoricalPriceProvider = YahooHistoricalPriceProvider
YahooFinanceBenchmarkReturnProvider = YahooBenchmarkProvider
YahooFinanceInvestableVehicleReturnProvider = YahooInvestableVehicleProvider


def equal_weighted_mean_series(
    symbol_series: Dict[str, Sequence[PricePoint]],
) -> List[PricePoint]:
    """Compute equal-weighted mean value series using date intersection."""

    if not symbol_series:
        return []

    non_empty = {key: ensure_chronological(value) for key, value in symbol_series.items() if value}
    if not non_empty:
        return []

    all_date_sets = [{point.date for point in series} for series in non_empty.values()]
    intersection = set.intersection(*all_date_sets) if all_date_sets else set()
    if not intersection:
        return []

    by_symbol_date = {
        symbol: {point.date: float(point.value) for point in series}
        for symbol, series in non_empty.items()
    }

    combined: List[PricePoint] = []
    symbol_count = len(by_symbol_date)
    for current_date in sorted(intersection):
        total = sum(series[current_date] for series in by_symbol_date.values())
        combined.append(PricePoint(date=current_date, value=total / float(symbol_count)))

    return combined


def ensure_chronological(points: Sequence[PricePoint]) -> List[PricePoint]:
    return sorted(points, key=lambda item: date.fromisoformat(item.date))
