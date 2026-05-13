from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import yaml

from src.models.canonical_models import SecurityMaster
from src.normalize.market_cap_normalizer import assign_canonical_bucket, normalize_market_cap
from src.validation.market_cap_validator import validate_market_cap_config


def _load_market_cap_config() -> dict:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "config" / "market_cap_buckets.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def test_market_cap_bucket_assignment() -> None:
    config = _load_market_cap_config()
    assert assign_canonical_bucket(1000000000, config) == "MICRO"
    assert assign_canonical_bucket(4000000000, config) == "SMALL"
    assert assign_canonical_bucket(20000000000, config) == "MID"
    assert assign_canonical_bucket(100000000000, config) == "LARGE"
    assert assign_canonical_bucket(700000000000, config) == "MEGA"


def test_boundary_edge_cases() -> None:
    config = _load_market_cap_config()
    assert assign_canonical_bucket(0, config) == "MICRO"
    assert assign_canonical_bucket(3509999999, config) == "MICRO"
    assert assign_canonical_bucket(3510000000, config) == "SMALL"
    assert assign_canonical_bucket(13980000000, config) == "MID"
    assert assign_canonical_bucket(84970000000, config) == "LARGE"
    assert assign_canonical_bucket(565620000000, config) == "MEGA"


def test_malformed_ranges_detection() -> None:
    config = _load_market_cap_config()
    bad = deepcopy(config)
    bad["buckets"]["MID"]["min_usd_inclusive"] = 90000000000
    bad["buckets"]["MID"]["max_usd_exclusive"] = 10000000000

    errors = validate_market_cap_config(bad)
    assert any("Invalid boundaries for MID" in err for err in errors)


def test_overlapping_ranges_detection() -> None:
    config = _load_market_cap_config()
    bad = deepcopy(config)
    bad["buckets"]["SMALL"]["max_usd_exclusive"] = 30000000000

    errors = validate_market_cap_config(bad)
    assert any("Overlapping ranges detected" in err for err in errors)


def test_provider_lineage_and_snapshot_date_propagation() -> None:
    config = _load_market_cap_config()
    snapshot_date = date(2026, 5, 13)
    normalized = normalize_market_cap(
        market_cap_raw_usd=72000000000,
        market_cap_snapshot_date=snapshot_date,
        provider="STARMINE",
        config=config,
    )

    assert normalized.market_cap_bucket == "MID"
    assert normalized.market_cap_bucket_provider == "STARMINE"
    assert normalized.market_cap_snapshot_date == snapshot_date


def test_missing_bucket_and_invalid_provider_metadata() -> None:
    config = _load_market_cap_config()
    bad = deepcopy(config)
    bad["provider"] = ""
    del bad["buckets"]["MICRO"]

    errors = validate_market_cap_config(bad)
    assert any("Invalid provider metadata" in err for err in errors)
    assert any("Missing buckets" in err for err in errors)


def test_security_master_supports_snapshot_market_cap_fields() -> None:
    record = SecurityMaster(
        security_id="SEC-001",
        ticker="ABC",
        name="ABC Corp",
        security_type="EQUITY",
        region="US",
        market_cap_bucket="LARGE",
        market_cap_raw_usd=100000000000,
        market_cap_bucket_provider="FIDELITY",
        market_cap_snapshot_date=date(2026, 5, 13),
    )

    assert record.market_cap_raw_usd == 100000000000
    assert record.market_cap_bucket_provider == "FIDELITY"
    assert record.market_cap_snapshot_date == date(2026, 5, 13)