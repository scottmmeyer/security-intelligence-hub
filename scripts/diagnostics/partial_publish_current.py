"""
Partial publish: assemble data/current/ from completed 007 replay partitions.
This makes charts available for completed categories while the full 007 build
finishes. When 007's atomic publish runs, it overwrites these files with complete data.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPLAY_BASE = Path("data/history/replays/snapshot_date=2025-05-14")
CURRENT_DIR = Path("data/current")
NOW = datetime.now(timezone.utc).isoformat()
RUN_ID = "RUN-WP05D-20260514-007"

ALL_CATEGORIES = [
    ("US", "MEGA", "ALL"),
    ("US", "LARGE", "ALL"),
    ("US", "MID", "ALL"),
    ("US", "SMALL", "ALL"),
    ("US", "MICRO", "ALL"),
    ("INTERNATIONAL", "MEGA", "ALL"),
    ("INTERNATIONAL", "LARGE", "ALL"),
    ("INTERNATIONAL", "MID", "ALL"),
    ("INTERNATIONAL", "SMALL", "ALL"),
    ("INTERNATIONAL", "MICRO", "ALL"),
]

AVAILABILITY_HEADERS = [
    "geography", "market_cap_bucket", "industry",
    "benchmark_available", "vehicle_available",
    "stock_replay_available", "top_n_available",
    "replay_generated", "replay_status",
    "missing_dependencies", "generated_at_utc",
]
MATRIX_HEADERS = [
    "replay_id", "geography", "market_cap_bucket", "industry",
    "replay_status", "benchmark_id", "vehicle_id", "performance_row_count",
    "replay_selection_path", "replay_series_path", "replay_metadata_path",
    "replay_availability_path", "replay_evidence_summary_path", "generated_at_utc",
]
INPUTS_HEADERS = [
    "replay_id", "start_date", "end_date", "filter_market_cap_bucket",
    "filter_geography", "filter_industry", "selection_method", "top_n",
    "selected_symbols", "composite_score_snapshot_date", "replay_mode",
]
SERIES_HEADERS = [
    "series_id", "replay_id", "series_type", "date", "value",
    "cumulative_return", "source", "coverage_status",
]

availability_rows = []
matrix_rows = []
inputs_rows = []
series_rows = []

for geo, mcap, ind in ALL_CATEGORIES:
    suffix = f"{geo}-{mcap}-ALL"
    matches = [d for d in REPLAY_BASE.iterdir()
               if RUN_ID in d.name and d.name.endswith(suffix)]

    if not matches:
        availability_rows.append({
            "geography": geo, "market_cap_bucket": mcap, "industry": ind,
            "benchmark_available": "false", "vehicle_available": "false",
            "stock_replay_available": "false", "top_n_available": "false",
            "replay_generated": "false", "replay_status": "NOT_GENERATED",
            "missing_dependencies": "Replay build in progress.",
            "generated_at_utc": NOW,
        })
        print(f"  SKIP (not built yet): {geo} {mcap}")
        continue

    replay_dir = matches[0]
    avail_path = replay_dir / "replay_availability.json"
    meta_path = replay_dir / "replay_metadata.json"
    selection_path = replay_dir / "replay_selection.csv"
    series_path = replay_dir / "replay_performance_series.csv"
    evidence_path = replay_dir / "replay_evidence_summary.json"

    avail = json.loads(avail_path.read_text())
    meta = json.loads(meta_path.read_text())
    replay_id = avail["replay_id"]

    availability_rows.append({
        "geography": geo, "market_cap_bucket": mcap, "industry": ind,
        "benchmark_available": str(avail.get("benchmark_available", False)).lower(),
        "vehicle_available": str(avail.get("vehicle_available", False)).lower(),
        "stock_replay_available": str(avail.get("stock_replay_available", False)).lower(),
        "top_n_available": str(avail.get("top_n_available", False)).lower(),
        "replay_generated": str(avail.get("replay_generated", False)).lower(),
        "replay_status": avail.get("replay_status", "AVAILABLE"),
        "missing_dependencies": avail.get("missing_dependencies", ""),
        "generated_at_utc": avail.get("generated_at_utc", NOW),
    })

    with series_path.open() as f:
        cat_series = list(csv.DictReader(f))
    series_rows.extend(cat_series)

    with selection_path.open() as f:
        cat_inputs = list(csv.DictReader(f))
    inputs_rows.extend(cat_inputs)

    matrix_rows.append({
        "replay_id": replay_id,
        "geography": geo,
        "market_cap_bucket": mcap,
        "industry": ind,
        "replay_status": avail.get("replay_status", "AVAILABLE"),
        "benchmark_id": meta.get("benchmark_symbol_or_index", ""),
        "vehicle_id": meta.get("investable_vehicle_symbol", ""),
        "performance_row_count": len(cat_series),
        "replay_selection_path": str(selection_path),
        "replay_series_path": str(series_path),
        "replay_metadata_path": str(meta_path),
        "replay_availability_path": str(avail_path),
        "replay_evidence_summary_path": str(evidence_path) if evidence_path.exists() else "",
        "generated_at_utc": avail.get("generated_at_utc", NOW),
    })
    print(f"  INCLUDED: {geo} {mcap} ({len(cat_series)} series rows)")


def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


write_csv(CURRENT_DIR / "replay_availability.csv", AVAILABILITY_HEADERS, availability_rows)
write_csv(CURRENT_DIR / "replay_matrix.csv", MATRIX_HEADERS, matrix_rows)
write_csv(CURRENT_DIR / "replay_inputs.csv", INPUTS_HEADERS, inputs_rows)
write_csv(CURRENT_DIR / "replay_performance_series.csv", SERIES_HEADERS, series_rows)

available = sum(1 for r in availability_rows if r["replay_status"] == "AVAILABLE")
print(f"\nWrote availability: {len(availability_rows)} rows ({available} AVAILABLE)")
print(f"Wrote matrix:       {len(matrix_rows)} rows")
print(f"Wrote inputs:       {len(inputs_rows)} rows")
print(f"Wrote series:       {len(series_rows)} rows")
