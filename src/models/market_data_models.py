"""WP-05 historical market data and return engine contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalPriceRow:
    """Canonical historical security price row."""

    security_id: str
    symbol: str
    security_type: str
    date: str
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int
    dividend: float
    split_ratio: float
    source_provider: str
    created_at_utc: str


@dataclass(frozen=True)
class BenchmarkReturnRow:
    """Benchmark return line row for replay comparisons."""

    benchmark_id: str
    symbol_or_index: str
    date: str
    adjusted_close: float
    cumulative_return: float
    source_provider: str

    @property
    def value(self) -> float:
        return self.adjusted_close


@dataclass(frozen=True)
class InvestableVehicleReturnRow:
    """Investable vehicle return line row for replay comparisons."""

    vehicle_id: str
    symbol: str
    date: str
    adjusted_close: float
    cumulative_return: float
    source_provider: str

    @property
    def value(self) -> float:
        return self.adjusted_close
