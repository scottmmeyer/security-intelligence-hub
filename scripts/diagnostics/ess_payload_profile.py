#!/usr/bin/env python3
"""Read-only ESS payload profiler for deterministic local diagnostics."""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path
from typing import Iterable

DEFAULT_INPUT_DIRS = (
    "incoming/ess/starmine",
    "incoming/ess/non_starmine_zacks",
)
TEXT_COLUMN_HINTS = ("ess_text", "category", "sentiment")
TOKEN_PATTERN = re.compile(r"\b[A-Z0-9]{3,}\b")


def get_token_sample(values: Iterable[str], max_tokens: int = 10) -> list[str]:
    """Return a deterministic token sample from string values."""
    tokens: set[str] = set()
    for value in values:
        tokens.update(TOKEN_PATTERN.findall(value.upper()))
        if len(tokens) > 20:
            break
    return sorted(tokens)[:max_tokens]


def profile_csv(csv_path: Path, sample_rows: int) -> None:
    """Print deterministic header and lightweight value profile for one CSV file."""
    try:
        with csv_path.open("r", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames
            if not headers:
                print(f"FILE: {csv_path}")
                print("STATUS: empty-or-headerless")
                return

            wp03_columns = [
                column for column in headers if "WP03" in column.upper() or "WP-03" in column.upper()
            ]
            text_columns = [
                column
                for column in headers
                if any(hint in column.lower() for hint in TEXT_COLUMN_HINTS)
            ]
            observed_values = {column: set() for column in text_columns}

            for row_index, row in enumerate(reader):
                if row_index >= sample_rows:
                    break
                for column in text_columns:
                    value = (row.get(column) or "").strip()
                    if value:
                        observed_values[column].add(value)

            print(f"FILE: {csv_path}")
            print(f"HEADERS: {headers}")
            print(f"WP03_COLUMNS: {wp03_columns if wp03_columns else 'NONE'}")
            for column in text_columns:
                sample = get_token_sample(observed_values[column])
                print(f"COLUMN {column}: unique={len(observed_values[column])}, token_sample={sample}")
    except Exception as exc:
        print(f"FILE: {csv_path}")
        print(f"ERROR: {exc}")


def iter_csv_files(input_dirs: Iterable[str]) -> list[Path]:
    """Resolve CSV files in deterministic lexicographic order."""
    csv_files: list[Path] = []
    for input_dir in input_dirs:
        root = Path(input_dir)
        if not root.exists():
            continue
        for current_root, _, file_names in os.walk(root):
            for file_name in sorted(file_names):
                if file_name.endswith(".csv"):
                    csv_files.append(Path(current_root) / file_name)
    return sorted(csv_files)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only profile of ESS CSV payload headers and selected text columns. "
            "This script never mutates repository state."
        )
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        dest="input_dirs",
        default=None,
        help="Input directory to scan for CSV files. Repeat for multiple directories.",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=500,
        help="Maximum rows sampled per file for value profiling (default: 500).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dirs = args.input_dirs if args.input_dirs else list(DEFAULT_INPUT_DIRS)
    csv_files = iter_csv_files(input_dirs)

    if not csv_files:
        print("No CSV files found in requested input directories.")
        return 0

    for csv_file in csv_files:
        profile_csv(csv_file, sample_rows=args.sample_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
