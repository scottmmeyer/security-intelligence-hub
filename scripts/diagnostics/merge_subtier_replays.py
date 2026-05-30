"""Merge base + subtier replay builds into data/current/ CSVs."""
import csv
from pathlib import Path

BASE = Path("data/history/replays/snapshot_date=2025-05-14")
CURRENT = Path("data/current")
RUN_IDS = [
    "RUN-WP05D-20260515-001",
    "RUN-WP05D-20260515-HYPER2",
    "RUN-WP05D-20260515-ULTRA2",
    "RUN-WP05D-20260515-EXTENDED2",
]

INPUTS_HEADERS = [
    "replay_id", "start_date", "end_date", "filter_market_cap_bucket",
    "filter_geography", "filter_industry", "filter_analytical_subtier",
    "selection_method", "top_n", "selected_symbols",
    "composite_score_snapshot_date", "replay_mode",
]
SERIES_HEADERS = [
    "series_id", "replay_id", "series_type", "date", "value",
    "cumulative_return", "source", "coverage_status",
]


def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


inputs_rows = []
series_rows = []
seen_replay_ids = set()

for run_id in RUN_IDS:
    dirs = [d for d in BASE.iterdir() if run_id in d.name]
    for d in sorted(dirs):
        sel = d / "replay_selection.csv"
        ser = d / "replay_performance_series.csv"
        if sel.exists():
            for row in csv.DictReader(sel.open()):
                rid = row.get("replay_id", "")
                if rid not in seen_replay_ids:
                    seen_replay_ids.add(rid)
                    inputs_rows.append(row)
        if ser.exists():
            series_rows.extend(csv.DictReader(ser.open()))

write_csv(CURRENT / "replay_inputs.csv", INPUTS_HEADERS, inputs_rows)
write_csv(CURRENT / "replay_performance_series.csv", SERIES_HEADERS, series_rows)

print(f"replay_inputs rows:            {len(inputs_rows)}")
print(f"replay_performance_series rows:{len(series_rows)}")
subtiers = sorted(set(r.get("filter_analytical_subtier", "") for r in inputs_rows))
print(f"subtiers in inputs:            {subtiers}")
