"""One-time migration: add zacks_rating column to existing base universe CSVs."""
import csv
from pathlib import Path

files = [
    "data/current/base_equity_universe.csv",
    "data/history/universe/snapshot_date=2026-05-13/run_id=RUN-REAL-ESS-20260513-002/base_equity_universe.csv",
    "data/history/universe/snapshot_date=2026-05-14/run_id=RUN-WP05D-20260514-001/base_equity_universe.csv",
]

new_headers = [
    "symbol", "company_name", "security_type", "geography", "market_cap_raw_usd",
    "market_cap_bucket", "coverage_domain", "starmine_ess_text", "zacks_rating",
    "provider", "source_file", "snapshot_date", "created_at_utc", "run_id",
]

for fpath in files:
    p = Path(fpath)
    if not p.exists():
        print(f"SKIP (not found): {fpath}")
        continue
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        old_headers = reader.fieldnames or []
        rows = list(reader)
    if "zacks_rating" in old_headers:
        print(f"ALREADY MIGRATED: {fpath}")
        continue
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row.setdefault("zacks_rating", "")
            writer.writerow(row)
    print(f"MIGRATED ({len(rows)} rows): {fpath}")
