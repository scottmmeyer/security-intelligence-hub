#!/usr/bin/env python3
"""Restore momentum price-history coverage for current portfolio holdings.

Reporting-only utility using existing historical price provider and persistence
contracts. No scoring/recommendation logic is modified.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.pis.momentum_price_history import (
    inventory_current_price_coverage,
    inventory_sector_parent_coverage,
    restore_current_portfolio_price_history,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore current-portfolio momentum price coverage.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--lookback-days", type=int, default=420)
    parser.add_argument("--no-sector-parents", action="store_true")
    parser.add_argument("--no-benchmark", action="store_true")
    parser.add_argument("--report-path", default="", help="Optional JSON report output path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)

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
