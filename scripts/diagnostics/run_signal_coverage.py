from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.validation.run_signal_coverage import summarize_run_signal_coverage


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report run-level signal nonblank coverage from holdings.csv."
    )
    parser.add_argument("run_id", help="Analysis run id (for example PAR-20260817-0A53DC67).")
    parser.add_argument(
        "--analysis-runs-root",
        default="data/portfolio_ingestion/analysis_runs",
        help="Root directory containing PAR run folders.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args()

    run_dir = Path(args.analysis_runs_root) / args.run_id
    summary = summarize_run_signal_coverage(run_dir)

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"RUN={summary['run_id']}")
        print(f"SOURCE_FORMAT={summary['source_format']}")
        print(f"HOLDINGS_COUNT={summary['holdings_count']}")
        print(f"ZACKS_RUN_NONBLANK_HOLDINGS={summary['zacks_run_nonblank_holdings']}")
        print(f"DANELFIN_RUN_NONBLANK_HOLDINGS={summary['danelfin_run_nonblank_holdings']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
