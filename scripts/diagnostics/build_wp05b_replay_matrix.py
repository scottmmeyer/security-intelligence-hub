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
from scripts.refresh_signals import ensure_signals_fresh


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WP-05B replay coverage matrix.")
    parser.add_argument("--run-id", required=True, help="Run identifier suffix for replay partitions.")
    parser.add_argument("--snapshot-date", required=True, help="Snapshot date in ISO format (YYYY-MM-DD).")
    parser.add_argument("--start-date", default=None, help="Replay window start date (defaults to snapshot date).")
    parser.add_argument("--end-date", default=None, help="Replay window end date (defaults to historical bounded +365).")
    parser.add_argument("--top-n", type=int, default=20, help="Top-N basket size placeholder.")
    parser.add_argument(
        "--filter-subtier",
        default=None,
        metavar="SUBTIER",
        help=(
            "Optional analytical subtier filter (e.g. HYPER_MEGA, ULTRA_MEGA, EXTENDED_MEGA). "
            "When omitted the full bucket is used — existing 10-category matrix behaviour is unchanged."
        ),
    )
    parser.add_argument(
        "--filter-industry",
        default="ALL",
        metavar="INDUSTRY",
        help=(
            "Optional industry/sector filter (e.g. TECHNOLOGY, HEALTHCARE, FINANCIAL SERVICES). "
            "When omitted or set to ALL, the full-bucket behaviour is unchanged."
        ),
    )
    parser.add_argument("--skip-signal-refresh", action="store_true", help="Skip automatic signal freshness check.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.skip_signal_refresh:
        ensure_signals_fresh()

    result = build_wp05b_replay_matrix(
        run_id=args.run_id,
        snapshot_date=args.snapshot_date,
        start_date=args.start_date,
        end_date=args.end_date,
        top_n=args.top_n,
        filter_analytical_subtier=args.filter_subtier,
        filter_industry=args.filter_industry,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
