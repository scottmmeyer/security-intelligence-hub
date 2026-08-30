#!/usr/bin/env python3
"""Restore momentum price-history coverage for current portfolio holdings.

Reporting-only utility using existing historical price provider and persistence
contracts. No scoring/recommendation logic is modified.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pis.momentum_price_history import (
    DEFAULT_BACKFILL_BATCH_SIZE,
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_RESEARCH_HISTORY_START,
    backfill_research_universe_price_history,
    inventory_current_price_coverage,
    inventory_sector_parent_coverage,
    parse_symbols_csv,
    restore_current_portfolio_price_history,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore current-portfolio momentum price coverage.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--lookback-days", type=int, default=420)
    parser.add_argument("--no-sector-parents", action="store_true")
    parser.add_argument("--no-benchmark", action="store_true")
    parser.add_argument("--research-universe", action="store_true")
    parser.add_argument("--symbols", default="", help="Comma-separated explicit symbols for bounded backfill mode.")
    parser.add_argument("--start-date", default=DEFAULT_RESEARCH_HISTORY_START)
    parser.add_argument("--end-date", default="")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BACKFILL_BATCH_SIZE)
    parser.add_argument("--checkpoint-path", default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-benchmark", action="store_true")
    parser.add_argument("--report-path", default="", help="Optional JSON report output path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)

    explicit_symbols = parse_symbols_csv(args.symbols)
    backfill_mode = bool(args.research_universe or explicit_symbols)

    if backfill_mode:
        if args.research_universe and explicit_symbols:
            raise SystemExit("Choose only one scope: --research-universe or --symbols.")

        result = backfill_research_universe_price_history(
            repo_root=repo_root,
            symbols=explicit_symbols or None,
            research_universe_mode=bool(args.research_universe),
            start_date=args.start_date,
            end_date=(args.end_date or None),
            batch_size=int(args.batch_size),
            checkpoint_path=args.checkpoint_path,
            resume=bool(args.resume),
            include_benchmark=(not args.no_benchmark) if args.include_benchmark else False,
            dry_run=bool(args.dry_run),
        )

        payload = {
            "mode": "research_universe_backfill" if args.research_universe else "explicit_symbol_backfill",
            "backfill": result,
        }

        print(json.dumps(payload, indent=2, sort_keys=True))

        if args.report_path:
            report_path = Path(args.report_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return

    before = inventory_current_price_coverage(repo_root)
    sector_before = inventory_sector_parent_coverage(repo_root)

    result = restore_current_portfolio_price_history(
        repo_root=repo_root,
        lookback_calendar_days=args.lookback_days,
        include_sector_parents=not args.no_sector_parents,
        include_benchmark=not args.no_benchmark,
    )

    after = inventory_current_price_coverage(repo_root)
    sector_after = inventory_sector_parent_coverage(repo_root)

    payload = {
        "before": {
            "snapshot_date": before.snapshot_date,
            "applicable": before.applicable_count,
            "present": before.present_count,
            "missing": before.missing_count,
            "partial": before.partial_count,
            "coverage_pct": before.coverage_pct,
            "rows": [row.__dict__ for row in before.rows],
        },
        "after": {
            "snapshot_date": after.snapshot_date,
            "applicable": after.applicable_count,
            "present": after.present_count,
            "missing": after.missing_count,
            "partial": after.partial_count,
            "coverage_pct": after.coverage_pct,
            "rows": [row.__dict__ for row in after.rows],
        },
        "sector_before": [row.__dict__ for row in sector_before],
        "sector_after": [row.__dict__ for row in sector_after],
        "restore": result,
    }

    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
