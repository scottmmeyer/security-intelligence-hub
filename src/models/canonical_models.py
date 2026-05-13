"""Canonical deterministic data models for Security Intelligence Hub.

These classes define stable contracts for foundational entities only.
Behavioral logic, ingestion routines, and persistence are intentionally deferred
to later waypoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Optional


@dataclass(frozen=True)
class SecurityMaster:
    """Canonical identity and classification record for a security."""

    security_id: str
    ticker: str
    name: str
    security_type: str
    region: str
    market_cap_bucket: str
    currency: str = "USD"
    is_active: bool = True


@dataclass(frozen=True)
class ProviderSignal:
    """Canonical provider signal payload normalized from source-specific fields."""

    provider_name: str
    security_id: str
    as_of_date: date
    signal_name: str
    signal_value: float
    raw_payload_ref: str
    signal_scope: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalSnapshot:
    """Immutable historical snapshot of canonical signal state."""

    snapshot_id: str
    security_id: str
    snapshot_ts_utc: datetime
    provider_name: str
    signal_name: str
    signal_value: float
    snapshot_version: int = 1
    correction_of_snapshot_id: Optional[str] = None


@dataclass(frozen=True)
class BenchmarkDefinition:
    """Benchmark mapping context used for relative performance interpretation."""

    benchmark_id: str
    benchmark_name: str
    region: str
    market_cap_bucket: str
    ticker: str
    effective_start_date: date
    effective_end_date: Optional[date] = None


@dataclass(frozen=True)
class MacroSnapshot:
    """Point-in-time macro context scaffold for future regime analytics."""

    macro_snapshot_id: str
    as_of_date: date
    regime_label: str
    indicators: Dict[str, float] = field(default_factory=dict)
    source_label: str = "TBD"


@dataclass(frozen=True)
class PerformanceOutcome:
    """Outcome tracking record for future benchmark-relative effectiveness work."""

    outcome_id: str
    security_id: str
    signal_snapshot_id: str
    benchmark_id: str
    horizon_days: int
    absolute_return: Optional[float] = None
    benchmark_return: Optional[float] = None
    relative_return: Optional[float] = None


# TODO(WP-03): add deterministic schema validation helpers for ESS payloads.
# TODO(WP-04): add classification validation for security_type and market_cap.
# TODO(FUTURE): introduce pydantic or typed validation adapters if needed.