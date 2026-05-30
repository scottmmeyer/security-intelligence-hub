#!/usr/bin/env python3
"""Resolve and fix UNKNOWN geography in analytical_universe.csv.

Reads each row with geography=UNKNOWN (or empty), uses the classification
geography_resolver with yfinance security metadata to determine the correct
geography, and rewrites the row with the corrected value.

Also fixes ADR benchmark misassignment: if an ADR equity was assigned a US
benchmark, reassigns it to the appropriate INTERNATIONAL benchmark.

Changes are logged to data/classification_audit/geography_remediation_<timestamp>.csv.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/assign_geography.py
    PYTHONPATH=. .venv/bin/python scripts/assign_geography.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.classification.geography_resolver import (
    load_adr_domicile_policy,
    load_geography_overrides,
    resolve_geography,
    GEOGRAPHY_UNKNOWN,
)
from src.classification.benchmark_assignment_engine import (
    assign_benchmarks,
    METHOD_NOT_APPLICABLE,
)
from src.classification.security_type_policy import load_security_type_policy
from src.replay.registry_loader import (
    load_benchmark_category_registry,
    load_investable_vehicle_registry,
    resolve_category_mapping,
)

_UNIVERSE_PATH = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
_METADATA_PATH = _REPO_ROOT / "data" / "signals" / "security_metadata" / "latest_security_metadata.csv"
_AUDIT_DIR = _REPO_ROOT / "data" / "classification_audit"
_BENCHMARK_REGISTRY_PATH = _REPO_ROOT / "config" / "benchmark_category_registry.yaml"
_VEHICLE_REGISTRY_PATH = _REPO_ROOT / "config" / "investable_vehicle_registry.yaml"

_LOG_HEADERS = [
    "symbol",
    "old_geography",
    "new_geography",
    "old_benchmark_id",
    "new_benchmark_id",
    "resolution_method",
    "benchmark_confidence",
    "classification_method",
    "country_used",
    "changed",
]


def _load_security_metadata(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    result: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = str(row.get("symbol", "")).strip().upper()
            if sym:
                result[sym] = dict(row)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve UNKNOWN geography in analytical universe.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing to disk.")
    parser.add_argument("--universe", type=Path, default=_UNIVERSE_PATH)
    args = parser.parse_args()

    universe_path = Path(args.universe)
    if not universe_path.exists():
        print(f"[GEO] ERROR: Universe not found: {universe_path}", file=sys.stderr)
        return 1

    print(f"[GEO] Loading universe from {universe_path.name}...")
    with universe_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows = list(reader)

    # Ensure new Phase 1 headers are present (additive migration)
    new_headers = ["replay_eligible", "scoring_eligible", "allocation_eligible",
                   "benchmark_confidence", "sector_benchmark_id", "classification_method"]
    added_headers = [h for h in new_headers if h not in headers]
    if added_headers:
        headers = headers + added_headers
        print(f"[GEO] Adding new columns to schema: {added_headers}")

    # Load support data
    metadata = _load_security_metadata(_METADATA_PATH)
    domicile_map = load_adr_domicile_policy()
    geo_overrides = load_geography_overrides()
    type_policy = load_security_type_policy()
    benchmark_registry = load_benchmark_category_registry(path=_BENCHMARK_REGISTRY_PATH)
    vehicle_registry = load_investable_vehicle_registry(path=_VEHICLE_REGISTRY_PATH)

    print(f"[GEO] Loaded {len(metadata)} metadata records, {len(geo_overrides)} overrides.")

    changed = 0
    skipped = 0
    log_rows: list[dict] = []

    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        old_geo = str(row.get("geography", "")).strip().upper()
        old_bm = str(row.get("benchmark_id", "")).strip()
        security_type = str(row.get("security_type", "UNKNOWN")).strip() or "UNKNOWN"

        meta = metadata.get(sym, {})
        type_info = type_policy.get_type_info(security_type)

        geo_resolution = resolve_geography(
            symbol=sym,
            security_type=security_type,
            country=meta.get("country", ""),
            quote_type=meta.get("quote_type", ""),
            existing_geography=old_geo,
            domicile_map=domicile_map,
            overrides=geo_overrides,
        )
        new_geo = geo_resolution.geography

        # Assign benchmark using the resolved geography
        cap_bucket = str(row.get("market_cap_bucket", "")).strip().upper()
        bm_assignment = assign_benchmarks(
            symbol=sym,
            security_type_info=type_info,
            geography_resolution=geo_resolution,
            market_cap_bucket=cap_bucket,
            benchmark_registry=benchmark_registry,
            vehicle_registry=vehicle_registry,
        )
        new_bm = bm_assignment.primary_benchmark_id
        if new_bm == "NOT_APPLICABLE":
            new_bm = "UNMAPPED"

        # Determine if changes are needed
        geo_changed = new_geo != old_geo and new_geo != GEOGRAPHY_UNKNOWN
        bm_changed = new_bm not in ("UNMAPPED", old_bm) and new_bm != old_bm

        any_changed = geo_changed or bm_changed

        log_rows.append({
            "symbol": sym,
            "old_geography": old_geo,
            "new_geography": new_geo,
            "old_benchmark_id": old_bm,
            "new_benchmark_id": new_bm if bm_changed else old_bm,
            "resolution_method": geo_resolution.resolution_method,
            "benchmark_confidence": bm_assignment.benchmark_confidence,
            "classification_method": bm_assignment.classification_method,
            "country_used": geo_resolution.country_used,
            "changed": "YES" if any_changed else "NO",
        })

        if not any_changed:
            skipped += 1
            continue

        if not args.dry_run:
            if geo_changed:
                row["geography"] = new_geo
            if bm_changed:
                row["benchmark_id"] = new_bm
            row["benchmark_confidence"] = bm_assignment.benchmark_confidence
            row["classification_method"] = bm_assignment.classification_method
            row["sector_benchmark_id"] = row.get("sector_benchmark_id", "")
            # Set eligibility flags if columns exist
            row["replay_eligible"] = str(type_info.replay_eligible)
            row["scoring_eligible"] = str(type_info.scoring_eligible)
            row["allocation_eligible"] = str(type_info.allocation_eligible)

        changed += 1
        action = "(dry-run)" if args.dry_run else "updated"
        if geo_changed:
            print(f"  {sym}: geography {old_geo} → {new_geo} "
                  f"[{geo_resolution.resolution_method}] {action}")
        if bm_changed:
            print(f"  {sym}: benchmark  {old_bm} → {new_bm} {action}")

    # Write updated universe
    if not args.dry_run and changed > 0:
        with universe_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore", restval="")
            writer.writeheader()
            writer.writerows(rows)
        print(f"[GEO] Wrote {len(rows)} rows to {universe_path.name}")

    # Write audit log
    if not args.dry_run:
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_path = _AUDIT_DIR / f"geography_remediation_{ts}.csv"
        with log_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_LOG_HEADERS)
            writer.writeheader()
            writer.writerows(log_rows)
        print(f"[GEO] Change log written to {log_path.name}")

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{mode}Summary: {changed} rows changed, {skipped} rows unchanged out of {len(rows)} total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
