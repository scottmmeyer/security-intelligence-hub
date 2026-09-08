#!/usr/bin/env python3
"""Materialize validated current Momentum and DRI intelligence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pis.current_intelligence import CurrentIntelligenceError, materialize_current_intelligence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize current Momentum and DRI intelligence.")
    parser.add_argument("--snapshot-date", default=None, help="Required current portfolio date, YYYY-MM-DD.")
    args = parser.parse_args(argv)
    try:
        result = materialize_current_intelligence(repo_root=_REPO_ROOT, snapshot_date=args.snapshot_date)
    except CurrentIntelligenceError as exc:
        print(f"ERROR_CODE={exc.code}")
        print(f"ERROR={exc}")
        return 1
    except Exception as exc:
        print("ERROR_CODE=CURRENT_INTELLIGENCE_MATERIALIZATION_FAILED")
        print(f"ERROR={exc}")
        return 1
    print("STATUS=COMPLETE")
    for key, value in result.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
