#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.scoring.danelfin_manual_import import (
    _DEFAULT_OUTPUT_DIR,
    DEFAULT_OPERATOR_SOURCE,
    MANUAL_ACQUISITION_METHOD,
    import_manual_danelfin_observations,
    read_manual_danelfin_csv,
)


def _parse_score_arg(value: str) -> dict[str, object]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--score must be SYMBOL=RAW_SCORE")
    symbol, raw_score = value.split("=", 1)
    symbol = symbol.strip().upper()
    raw_score = raw_score.strip()
    if not symbol:
        raise argparse.ArgumentTypeError("--score symbol cannot be blank")
    return {"symbol": symbol, "danelfin_raw": raw_score}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import operator-entered Danelfin raw scores into the normal cache."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Tiny CSV with columns symbol,danelfin_raw,sourced_date[,operator_source[,observed_at]]",
    )
    parser.add_argument(
        "--score",
        action="append",
        default=[],
        help="Repeatable SYMBOL=RAW_SCORE entries for quick pair-page entry.",
    )
    parser.add_argument(
        "--sourced-date",
        required=True,
        help="Source date for operator-entered scores (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Danelfin cache directory (defaults to the standard signal cache).",
    )
    parser.add_argument(
        "--operator-source",
        default=DEFAULT_OPERATOR_SOURCE,
        choices=["STOCK_PAGE", "PAIR_PAGE"],
        help="Where the score was observed in the Danelfin UI.",
    )
    parser.add_argument(
        "--observed-at",
        default=None,
        help="Optional UTC timestamp for the manual observation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    observations: list[dict[str, object]] = []
    if args.csv:
        observations.extend(
            {
                "symbol": obs.symbol,
                "danelfin_raw": obs.danelfin_raw,
                "sourced_date": args.sourced_date,
                "operator_source": obs.operator_source,
                "observed_at": obs.observed_at,
                "acquisition_method": MANUAL_ACQUISITION_METHOD,
            }
            for obs in read_manual_danelfin_csv(args.csv)
        )

    observations.extend(
        _parse_score_arg(value)
        | {
            "sourced_date": args.sourced_date,
            "operator_source": args.operator_source,
            "acquisition_method": MANUAL_ACQUISITION_METHOD,
            "observed_at": args.observed_at,
        }
        for value in args.score
    )

    if not observations:
        parser.error("Provide at least one --csv or --score entry.")

    summary = import_manual_danelfin_observations(
        observations,
        output_dir=args.output_dir or _DEFAULT_OUTPUT_DIR,
        operator_source=args.operator_source,
        acquisition_method=MANUAL_ACQUISITION_METHOD,
        observed_at=args.observed_at,
    )
    print(summary["latest_path"])
    print(f"applied={summary['applied_count']} skipped={summary['skipped_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
