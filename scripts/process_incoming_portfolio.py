#!/usr/bin/env python3
"""Governed incoming portfolio processor with date-gating safeguards.

Behavior summary:
- Discovers CSV files under incoming/portfolio.
- Parses a filename date token like "Jun-27-2026" and passes it to run_analysis.
- By default processes only files matching --target-date (defaults to today's date).
- Supports --dry-run preview mode that never invokes run_analysis.
- Supports --all-dates only with --confirm-all-dates (unless dry-run).

Operational note:
Invoking run_analysis can trigger normal ingestion side effects, including
best-effort PIS registration and post-ingestion refresh behavior.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional, Sequence

from src.portfolio.runner import run_analysis


_REPO_ROOT = Path(__file__).resolve().parents[1]
_INCOMING_PORTFOLIO = _REPO_ROOT / "incoming" / "portfolio"
_FILENAME_DATE_RE = re.compile(r"([A-Za-z]{3})-(\d{1,2})-(\d{4})")
_FAILURE_STATUSES = {"FAILED", "ERROR", "REJECTED"}


@dataclass(frozen=True)
class ProcessResult:
    filename: str
    file_date: str
    status: str
    run_id: str


@dataclass(frozen=True)
class SkippedFile:
    filename: str
    reason: str


@dataclass(frozen=True)
class FailedFile:
    filename: str
    file_date: str
    reason: str


def parse_filename_date(filename: str) -> tuple[Optional[str], Optional[str]]:
    """Return (iso_date, error_reason) parsed from a filename token.

    Expected token format is a month/day/year triplet like Jun-27-2026.
    """
    match = _FILENAME_DATE_RE.search(filename)
    if not match:
        return None, "missing filename date token (Mon-DD-YYYY)"
    month, day, year = match.groups()
    try:
        return datetime.strptime(f"{month}-{day}-{year}", "%b-%d-%Y").date().isoformat(), None
    except ValueError:
        return None, "invalid filename date token"


def validate_target_date(target_date: str) -> date:
    """Validate strict ISO date input (YYYY-MM-DD)."""
    try:
        return datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"Invalid --target-date '{target_date}'. Expected format YYYY-MM-DD."
        ) from exc


def discover_csv_files(incoming_dir: Path) -> list[Path]:
    """Return stable, name-sorted CSV files from incoming directory."""
    return sorted([p for p in incoming_dir.iterdir() if p.is_file() and p.suffix.lower() == ".csv"], key=lambda p: p.name)


def select_files_for_processing(
    files: Sequence[Path],
    *,
    target_date: str,
    all_dates: bool,
) -> tuple[list[tuple[Path, str]], list[SkippedFile]]:
    """Apply filename-parse and date-gate selection logic."""
    selected: list[tuple[Path, str]] = []
    skipped: list[SkippedFile] = []

    for path in files:
        file_date, date_error = parse_filename_date(path.name)
        if file_date is None:
            skipped.append(SkippedFile(filename=path.name, reason=str(date_error)))
            continue

        if not all_dates and file_date != target_date:
            skipped.append(
                SkippedFile(
                    filename=path.name,
                    reason=f"stale date: file_date={file_date} target_date={target_date}",
                )
            )
            continue

        selected.append((path, file_date))

    return selected, skipped


def is_failure_status(status: str) -> bool:
    return status.strip().upper() in _FAILURE_STATUSES


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process incoming portfolio CSV files from incoming/portfolio with guarded execution.",
        epilog=(
            "Default behavior only processes files whose filename date matches --target-date. "
            "Use --dry-run to preview. Use --all-dates only with --confirm-all-dates unless dry-run."
        ),
    )
    parser.add_argument(
        "--target-date",
        default=date.today().isoformat(),
        help="ISO date gate (YYYY-MM-DD). Only matching filename dates process unless --all-dates.",
    )
    parser.add_argument(
        "--all-dates",
        action="store_true",
        help="Select all parseable filename dates (requires --confirm-all-dates unless --dry-run).",
    )
    parser.add_argument(
        "--confirm-all-dates",
        action="store_true",
        help="Required confirmation for non-dry-run --all-dates execution.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview selected files without calling run_analysis.",
    )
    parser.add_argument(
        "--mandate-type",
        default="CONCENTRATED_ALPHA",
        help="Mandate type forwarded to run_analysis (validation delegated to runtime pipeline).",
    )
    return parser.parse_args(argv)


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    incoming_dir: Path = _INCOMING_PORTFOLIO,
    analysis_runner: Callable[..., dict] = run_analysis,
    today_value: Optional[date] = None,
) -> int:
    args = parse_args(argv)

    if today_value is not None and args.target_date == date.today().isoformat():
        target_date = today_value.isoformat()
    else:
        target_date = args.target_date

    try:
        validate_target_date(target_date)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.all_dates and not args.dry_run and not args.confirm_all_dates:
        print(
            "ERROR: --all-dates requires --confirm-all-dates for non-dry-run execution. "
            "Use --dry-run first to preview."
        )
        return 2

    if not incoming_dir.exists():
        print(f"No incoming directory found at: {incoming_dir}")
        return 0

    files = discover_csv_files(incoming_dir)
    if not files:
        print("No incoming portfolio CSV files found.")
        return 0

    selected, skipped = select_files_for_processing(
        files,
        target_date=target_date,
        all_dates=bool(args.all_dates),
    )

    processed: list[ProcessResult] = []
    failed: list[FailedFile] = []

    print(f"Incoming folder: {incoming_dir}")
    print(f"Target date gate: {target_date}")
    print(f"All dates mode: {args.all_dates}")
    print(f"Dry run: {args.dry_run}")
    print("Note: run_analysis may trigger post-ingestion orchestration behavior.")

    for path, file_date in selected:
        filename = path.name
        if args.dry_run:
            processed.append(ProcessResult(filename=filename, file_date=file_date, status="DRY_RUN", run_id=""))
            continue

        try:
            content = path.read_text(encoding="utf-8")
            result = analysis_runner(
                content,
                filename,
                snapshot_date=file_date,
                mandate_type=args.mandate_type,
            )
            status = str(result.get("status", ""))
            run_id = str(result.get("run_id", ""))

            if is_failure_status(status):
                failed.append(
                    FailedFile(
                        filename=filename,
                        file_date=file_date,
                        reason=f"run_analysis returned failure status '{status}'",
                    )
                )
                processed.append(
                    ProcessResult(
                        filename=filename,
                        file_date=file_date,
                        status=status,
                        run_id=run_id,
                    )
                )
                continue

            processed.append(
                ProcessResult(
                    filename=filename,
                    file_date=file_date,
                    status=status or "OK",
                    run_id=run_id,
                )
            )
        except Exception as exc:
            failed.append(FailedFile(filename=filename, file_date=file_date, reason=str(exc)))

    print("\nSelected files:")
    if selected:
        for path, file_date in selected:
            print(f"  {path.name}: file_date={file_date}")
    else:
        print("  (none)")

    print("\nProcessed results:")
    if processed:
        for item in processed:
            print(
                f"  {item.filename}: file_date={item.file_date} status={item.status} run_id={item.run_id}"
            )
    else:
        print("  (none)")

    print("\nSkipped files:")
    if skipped:
        for item in skipped:
            print(f"  {item.filename}: {item.reason}")
    else:
        print("  (none)")

    print("\nFailed files:")
    if failed:
        for item in failed:
            print(f"  {item.filename}: file_date={item.file_date} reason={item.reason}")
    else:
        print("  (none)")

    dry_run_count = sum(1 for p in processed if p.status == "DRY_RUN")
    print("\nSummary:")
    print(f"  total_files={len(files)}")
    print(f"  selected={len(selected)}")
    print(f"  processed={len(processed)}")
    print(f"  failed={len(failed)}")
    print(f"  skipped={len(skipped)}")
    print(f"  dry_run={dry_run_count}")

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
