#!/usr/bin/env python3
"""Resumable FMP analyst-estimate backfill runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.history.fmp_estimate_backfill import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_PATH,
    parse_symbols_csv,
    run_fmp_estimate_backfill,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run resumable FMP analyst-estimate backfill.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--research-universe", action="store_true")
    parser.add_argument("--symbols", default="", help="Comma-separated explicit symbols for bounded runs.")
    parser.add_argument("--period", default="annual", choices=["annual"], help="Requested estimate period.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--checkpoint-path", default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-batches", type=int, default=0, help="Optional cap on batches per invocation.")
    parser.add_argument("--report-path", default="", help="Optional JSON report output path.")
    args = parser.parse_args()

    symbols = parse_symbols_csv(args.symbols)
    result = run_fmp_estimate_backfill(
        repo_root=Path(args.repo_root),
        research_universe=bool(args.research_universe),
        symbols=symbols or None,
        requested_periods=[args.period],
        batch_size=int(args.batch_size),
        checkpoint_path=args.checkpoint_path,
        resume=bool(args.resume),
        dry_run=bool(args.dry_run),
        max_batches=(int(args.max_batches) if int(args.max_batches) > 0 else None),
        report_path=(args.report_path or None),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
