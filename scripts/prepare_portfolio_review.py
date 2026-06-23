#!/usr/bin/env python3
"""Prepare a portfolio review by refreshing signals and PIS derived artifacts.

This is an orchestration wrapper only. It does not change scoring, ranking,
or recommendation algorithms.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.refresh_signals import REFRESH_MODE_PORTFOLIO_SIGNALS, ensure_signals_fresh_with_report
from src.pis.refresh_orchestrator import refresh_derived_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a portfolio review refresh bundle.")
    parser.add_argument("--report-path", default="", help="Optional JSON report output path.")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    signal_report = ensure_signals_fresh_with_report(
        refresh_mode=REFRESH_MODE_PORTFOLIO_SIGNALS,
        smart=False,
        verbose=True,
        dry_run=False,
    )
    pis_report = refresh_derived_artifacts(repo_root=_REPO_ROOT)

    completed_at = datetime.now(timezone.utc).isoformat()
    report = {
        "refresh_mode": "prepare_portfolio_review",
        "refresh_mode_label": "Prepare Portfolio Review",
        "started_at": started_at,
        "completed_at": completed_at,
        "runtime_sec": round(time.perf_counter() - t0, 4),
        "signal_refresh": signal_report,
        "providers": signal_report.get("providers") or {},
        "pis_refresh": pis_report,
    }

    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
