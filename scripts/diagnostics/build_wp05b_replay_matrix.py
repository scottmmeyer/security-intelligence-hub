#!/usr/bin/env python3
"""Build WP-05B replay coverage matrix and availability contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.replay.foundation_service import build_wp05b_replay_matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WP-05B replay coverage matrix.")
    parser.add_argument("--run-id", required=True, help="Run identifier suffix for replay partitions.")
    parser.add_argument("--snapshot-date", required=True, help="Snapshot date in ISO format (YYYY-MM-DD).")
    parser.add_argument("--start-date", default=None, help="Replay window start date (defaults to snapshot date).")
    parser.add_argument("--end-date", default=None, help="Replay window end date (defaults to historical bounded +365).")
    parser.add_argument("--top-n", type=int, default=20, help="Top-N basket size placeholder.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_wp05b_replay_matrix(
        run_id=args.run_id,
        snapshot_date=args.snapshot_date,
        start_date=args.start_date,
        end_date=args.end_date,
        top_n=args.top_n,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
