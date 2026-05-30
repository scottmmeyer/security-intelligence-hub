#!/usr/bin/env python3
"""Apply eligibility flags to all rows in analytical_universe.csv.

Sets replay_eligible, scoring_eligible, and allocation_eligible based on
config/security_type_policy.yaml for each row's security_type.

Also adds the new Phase 1 columns (benchmark_confidence, sector_benchmark_id,
classification_method) with defaults if they don't already exist.

Idempotent: safe to run multiple times. Existing values are overwritten with
the current policy-computed values.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/apply_eligibility_flags.py
    PYTHONPATH=. .venv/bin/python scripts/apply_eligibility_flags.py --dry-run
    PYTHONPATH=. .venv/bin/python scripts/apply_eligibility_flags.py --universe data/current/analytical_universe.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from src.classification.security_type_policy import load_security_type_policy

_UNIVERSE_PATH = _REPO_ROOT / "data" / "current" / "analytical_universe.csv"
_AUDIT_DIR = _REPO_ROOT / "data" / "classification_audit"

# All Phase 1 columns — added to schema if missing
_PHASE1_COLUMNS = [
    "replay_eligible",
    "scoring_eligible",
    "allocation_eligible",
    "benchmark_confidence",
    "sector_benchmark_id",
    "classification_method",
]

# Base expected headers (pre-Phase 1)
_BASE_HEADERS = [
    "security_id", "symbol", "security_type", "snapshot_date", "run_id",
    "market_cap_bucket", "geography", "country", "industry", "sector",
    "composite_score", "ess_score_text", "zacks_rating", "yahoo_score", "danelfin_score",
    "benchmark_id", "investable_vehicle_id", "price_at_snapshot", "provider_lineage",
    "analytical_market_cap_subtier", "classification_policy_id", "classification_snapshot_date",
]

_FULL_HEADERS = _BASE_HEADERS + _PHASE1_COLUMNS

_CHANGE_LOG_HEADERS = [
    "symbol",
    "security_type",
    "canonical_class",
    "old_replay_eligible",
    "new_replay_eligible",
    "old_scoring_eligible",
    "new_scoring_eligible",
    "old_allocation_eligible",
    "new_allocation_eligible",
    "changed",
]


def _to_bool_str(val: str, default: bool = True) -> str:
    """Normalize existing bool column value."""
    v = str(val or "").strip().lower()
    if v in ("false", "0", "no"):
        return "False"
    if v in ("true", "1", "yes"):
        return "True"
    return "True" if default else "False"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply eligibility flags to analytical universe.")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing.")
    parser.add_argument("--universe", type=Path, default=_UNIVERSE_PATH)
    args = parser.parse_args()

    universe_path = Path(args.universe)
    if not universe_path.exists():
        print(f"[FLAGS] ERROR: Universe not found: {universe_path}", file=sys.stderr)
        return 1

    print(f"[FLAGS] Loading universe from {universe_path.name}...")
    with universe_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        existing_headers = list(reader.fieldnames or [])
        rows = list(reader)

    # Determine final header list (add missing Phase 1 cols)
    added_headers = [h for h in _PHASE1_COLUMNS if h not in existing_headers]
    if added_headers:
        final_headers = existing_headers + added_headers
        print(f"[FLAGS] Adding new columns: {added_headers}")
    else:
        final_headers = existing_headers

    type_policy = load_security_type_policy()
    print(f"[FLAGS] Processing {len(rows)} rows...")

    changed = 0
    unchanged = 0
    unknown_types: dict[str, int] = {}
    change_log: list[dict] = []

    for row in rows:
        sym = str(row.get("symbol", "")).strip().upper()
        security_type = str(row.get("security_type", "UNKNOWN")).strip() or "UNKNOWN"
        type_info = type_policy.get_type_info(security_type)

        new_replay = str(type_info.replay_eligible)
        new_scoring = str(type_info.scoring_eligible)
        new_alloc = str(type_info.allocation_eligible)

        old_replay = _to_bool_str(row.get("replay_eligible", ""), True)
        old_scoring = _to_bool_str(row.get("scoring_eligible", ""), True)
        old_alloc = _to_bool_str(row.get("allocation_eligible", ""), True)

        any_changed = (
            new_replay != old_replay
            or new_scoring != old_scoring
            or new_alloc != old_alloc
        )

        if not type_info.resolved_from_mapping:
            unknown_types[security_type] = unknown_types.get(security_type, 0) + 1

        change_log.append({
            "symbol": sym,
            "security_type": security_type,
            "canonical_class": type_info.canonical_class,
            "old_replay_eligible": old_replay,
            "new_replay_eligible": new_replay,
            "old_scoring_eligible": old_scoring,
            "new_scoring_eligible": new_scoring,
            "old_allocation_eligible": old_alloc,
            "new_allocation_eligible": new_alloc,
            "changed": "YES" if any_changed else "NO",
        })

        if not args.dry_run:
            row["replay_eligible"] = new_replay
            row["scoring_eligible"] = new_scoring
            row["allocation_eligible"] = new_alloc
            # Initialize Phase 1 cols with defaults if not set
            if "benchmark_confidence" not in row or not row.get("benchmark_confidence"):
                row["benchmark_confidence"] = ""
            if "sector_benchmark_id" not in row or not row.get("sector_benchmark_id"):
                row["sector_benchmark_id"] = ""
            if "classification_method" not in row or not row.get("classification_method"):
                row["classification_method"] = ""

        if any_changed:
            changed += 1
            if not args.dry_run:
                print(f"  {sym} ({security_type} → {type_info.canonical_class}): "
                      f"replay={old_replay}→{new_replay}, "
                      f"scoring={old_scoring}→{new_scoring}, "
                      f"alloc={old_alloc}→{new_alloc}")
        else:
            unchanged += 1

    # Write updated universe
    if not args.dry_run and (changed > 0 or added_headers):
        with universe_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=final_headers, extrasaction="ignore", restval="")
            writer.writeheader()
            writer.writerows(rows)
        print(f"[FLAGS] Wrote {len(rows)} rows to {universe_path.name}")

    # Write change log
    if not args.dry_run:
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_path = _AUDIT_DIR / f"eligibility_flags_{ts}.csv"
        with log_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_CHANGE_LOG_HEADERS)
            writer.writeheader()
            writer.writerows(change_log)
        print(f"[FLAGS] Change log written to {log_path.name}")

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{mode}Summary: {changed} rows changed, {unchanged} unchanged out of {len(rows)} total.")

    if unknown_types:
        print(f"\n[FLAGS] WARNING: {sum(unknown_types.values())} rows have unrecognized security types "
              f"(will default to UNKNOWN canonical class):")
        for st, count in sorted(unknown_types.items(), key=lambda x: -x[1]):
            print(f"  '{st}': {count} rows")
        print("  → Add entries to config/security_type_policy.yaml to resolve.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
