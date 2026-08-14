from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.validation.analysis_preflight import format_preflight_summary, run_analysis_preflight


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SIH analysis preflight diagnostics.")
    parser.add_argument("--repo-root", default=".", help="Repository root path.")
    parser.add_argument(
        "--require-active-ess",
        choices=("true", "false"),
        default="true",
        help="Whether active ESS freshness is required for advisory readiness.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    args = parser.parse_args()

    result = run_analysis_preflight(
        repo_root=Path(args.repo_root),
        require_active_ess=(args.require_active_ess.lower() == "true"),
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(format_preflight_summary(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())