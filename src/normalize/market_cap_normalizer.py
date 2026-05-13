"""Deterministic market-cap normalization scaffolding.

This module maps raw USD market cap values into canonical buckets while
preserving provider lineage and snapshot-date context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict

import yaml

from src.validation.market_cap_validator import assert_valid_market_cap_config


@dataclass(frozen=True)
class NormalizedMarketCap:
    """Canonical market-cap normalization output record."""

    market_cap_raw_usd: int
    market_cap_bucket: str
    market_cap_bucket_provider: str
    market_cap_snapshot_date: date


def load_market_cap_config(file_path: str | Path) -> Dict[str, Any]:
    """Load YAML market-cap config and validate deterministic contracts."""

    payload = yaml.safe_load(Path(file_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Market-cap config root must be a mapping object.")
    assert_valid_market_cap_config(payload)
    return payload


def assign_canonical_bucket(market_cap_raw_usd: int, config: Dict[str, Any]) -> str:
    """Assign canonical market-cap bucket from raw USD market cap."""

    assert_valid_market_cap_config(config)
    if not isinstance(market_cap_raw_usd, int):
        raise ValueError("market_cap_raw_usd must be integer.")
    if market_cap_raw_usd < 0:
        raise ValueError("market_cap_raw_usd cannot be negative.")

    buckets = config["buckets"]
    ordered_buckets = ("MICRO", "SMALL", "MID", "LARGE", "MEGA")
    for bucket_name in ordered_buckets:
        definition = buckets[bucket_name]
        min_value = definition["min_usd_inclusive"]
        max_value = definition["max_usd_exclusive"]
        above_min = market_cap_raw_usd >= min_value
        below_max = True if max_value is None else market_cap_raw_usd < max_value
        if above_min and below_max:
            return bucket_name

    raise ValueError("No canonical market-cap bucket matched value. Check bucket boundaries.")


def normalize_market_cap(
    market_cap_raw_usd: int,
    market_cap_snapshot_date: date,
    provider: str,
    config: Dict[str, Any],
) -> NormalizedMarketCap:
    """Normalize market cap and preserve provider lineage and snapshot date."""

    if not isinstance(market_cap_snapshot_date, date):
        raise ValueError("market_cap_snapshot_date must be a date.")
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("provider must be a non-empty string.")

    bucket = assign_canonical_bucket(market_cap_raw_usd=market_cap_raw_usd, config=config)
    return NormalizedMarketCap(
        market_cap_raw_usd=market_cap_raw_usd,
        market_cap_bucket=bucket,
        market_cap_bucket_provider=provider,
        market_cap_snapshot_date=market_cap_snapshot_date,
    )


# TODO(WP-03): add provider-specific translation maps once alternate providers are onboarded.