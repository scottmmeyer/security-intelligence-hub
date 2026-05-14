#!/usr/bin/env python3
"""Build WP-04 analytical universe and replay contract outputs from current data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.replay.foundation_service import build_wp04_foundation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WP-04 analytical universe and replay foundations.")
    parser.add_argument("--run-id", required=True, help="Run identifier for analytical universe partition output.")
    parser.add_argument("--snapshot-date", required=True, help="Snapshot date in ISO format (YYYY-MM-DD).")
    parser.add_argument("--market-cap-bucket", default="LARGE", help="Replay market cap filter.")
    parser.add_argument("--geography", default="US", help="Replay geography filter.")
    parser.add_argument("--industry", default="ALL", help="Replay industry filter.")
    parser.add_argument("--top-n", type=int, default=20, help="Top-N basket size.")
    parser.add_argument("--start-date", default=None, help="Replay start date (defaults to snapshot date).")
    parser.add_argument("--end-date", default=None, help="Replay end date (defaults to +365 days).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_wp04_foundation(
        run_id=args.run_id,
        snapshot_date=args.snapshot_date,
        filter_market_cap_bucket=args.market_cap_bucket,
        filter_geography=args.geography,
        filter_industry=args.industry,
        top_n=args.top_n,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
