#!/usr/bin/env python3
"""Run or inspect recurring annual FMP estimate snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.history.fmp_annual_snapshot import discover_recent_captures, run_daily_fmp_annual_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Operational daily annual FMP estimate capture with same-day idempotence/resume."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument(
        "--mode",
        choices=("run", "status"),
        default="run",
        help="run: execute snapshot workflow; status: list recent snapshot reports",
    )
    parser.add_argument(
        "--snapshot-date",
        default="",
        help="Snapshot date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Optional explicit symbol scope (default: research universe)",
    )
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for provider calls")
    parser.add_argument("--max-batches", type=int, default=0, help="Optional cap on batches for bounded runs")
    parser.add_argument("--force", action="store_true", help="Force new execution even if complete")
    parser.add_argument(
        "--allow-non-trading-day",
        action="store_true",
        help="Allow execution on weekends/non-trading days",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute/emit plan without data mutation")
    parser.add_argument("--status-limit", type=int, default=10, help="Max rows returned for status mode")
    return parser


def _print_run_summary(result: dict[str, object]) -> None:
    print("FMP annual snapshot")
    print(f"  snapshot_date: {result.get('snapshot_date', '')}")
    print(f"  action: {result.get('action', '')}")
    print(f"  status: {result.get('status', '')}")
    print(f"  run_id: {result.get('run_id', '')}")
    print(f"  universe_count: {result.get('universe_count', 0)}")
    print(f"  symbols_with_data: {result.get('symbols_with_data', 0)}")
    print(f"  symbols_no_coverage: {result.get('symbols_no_coverage', 0)}")
    print(f"  symbols_failed: {result.get('symbols_failed', 0)}")
    print(f"  total_accounted: {result.get('total_accounted', 0)}")
    print(f"  unaccounted_symbols: {result.get('unaccounted_symbols', 0)}")
    print(f"  report_path: {result.get('report_path', '')}")
    print(f"  checkpoint_path: {result.get('checkpoint_path', '')}")


def _print_status_summary(result: dict[str, object]) -> None:
    captures = list(result.get("captures") or [])
    print("Recent FMP annual snapshots")
    print(f"  index_path: {result.get('index_path', '')}")
    print(f"  updated_at_utc: {result.get('updated_at_utc', '')}")
    print(f"  count: {len(captures)}")
    for item in captures:
        print(
            "  - "
            f"{item.get('snapshot_date', '')} "
            f"action={item.get('action', '')} "
            f"status={item.get('status', '')} "
            f"run_id={item.get('run_id', '')}"
        )


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root)

    if args.mode == "status":
        result = discover_recent_captures(repo_root=repo_root, limit=max(args.status_limit, 0))
        _print_status_summary(result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    max_batches = args.max_batches if args.max_batches > 0 else None
    snapshot_date = args.snapshot_date.strip() or None
    result = run_daily_fmp_annual_snapshot(
        repo_root=repo_root,
        snapshot_date=snapshot_date,
        symbols=args.symbols,
        batch_size=int(args.batch_size),
        force=bool(args.force),
        allow_non_trading_day=bool(args.allow_non_trading_day),
        dry_run=bool(args.dry_run),
        max_batches=max_batches,
    )
    _print_run_summary(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())