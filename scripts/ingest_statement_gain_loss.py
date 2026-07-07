#!/usr/bin/env python3
"""STATEMENT-GAIN-LOSS-01 ingestion entrypoint.

Reporting-only statement ingestion for Fidelity gain/loss snapshots.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.portfolio.statements.statement_gain_loss import (  # noqa: E402
    StatementParsingError,
    apply_snapshot_parse_status,
    build_snapshot_from_sources,
    evaluate_snapshot_completeness,
    load_statement_source,
    write_snapshot_artifacts,
)

_SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest broker statement gain/loss into reporting artifacts.")
    p.add_argument(
        "--source",
        action="append",
        default=[],
        help="Path to statement source (.pdf or .txt/.md). Repeat for multiple statements.",
    )
    p.add_argument(
        "--incoming-dir",
        default=str(REPO_ROOT / "incoming" / "fidelity_statements"),
        help="Incoming directory scanned for .pdf/.txt/.md when --source is not provided.",
    )
    p.add_argument(
        "--output-root",
        default=str(REPO_ROOT / "artifacts" / "statement_gain_loss"),
        help="Root output directory for dated artifacts, latest pointers, and history index.",
    )
    p.add_argument(
        "--raw-archive-root",
        default=str(REPO_ROOT / "data" / "raw" / "fidelity_statements"),
        help="Raw archive root directory for processed input files.",
    )
    p.add_argument(
        "--move-processed",
        action="store_true",
        help="Move incoming sources into raw archive instead of copying.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report detected work but do not write artifacts or move/copy files.",
    )
    p.add_argument("--statement-date", help="Statement date (YYYY-MM-DD)")
    p.add_argument("--statement-period-start", help="Statement period start (YYYY-MM-DD)")
    p.add_argument("--statement-period-end", help="Statement period end (YYYY-MM-DD)")
    p.add_argument(
        "--main-account",
        action="append",
        default=["X20-548022", "Z35-123695"],
        help="Account numbers included in the main statement totals.",
    )
    return p.parse_args(argv)


def _discover_incoming_sources(incoming_dir: Path) -> list[Path]:
    if not incoming_dir.exists():
        return []
    return sorted(
        [p for p in incoming_dir.iterdir() if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )


def _group_sources_by_statement_date(sources: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for src in sources:
        probe = build_snapshot_from_sources([src])
        date = probe.statement_date
        if not date:
            raise StatementParsingError(
                "Unable to group source without statement date.",
                reason="statement_date_unresolved",
                details={"source_file": src.source_file},
            )
        grouped.setdefault(date, []).append(src)
    return grouped


def _latest_pointer_paths(output_root: Path) -> tuple[Path, Path]:
    return output_root / "latest.json", output_root / "latest.md"


def _history_index_path(output_root: Path) -> Path:
    return output_root / "history" / "statement_gain_loss_index.json"


def _upsert_history_index(
    index_path: Path,
    snapshot,
    json_path: Path,
    md_path: Path,
    dry_run: bool,
) -> tuple[dict, bool]:
    existing = {"entries": []}
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise StatementParsingError(
                "History index exists but is invalid JSON.",
                reason="history_index_invalid",
                details={"path": str(index_path), "error": str(exc)},
            ) from exc

    entries = existing.get("entries") or []
    by_date = {entry.get("statement_date"): entry for entry in entries if entry.get("statement_date")}
    by_date[snapshot.statement_date] = {
        "statement_date": snapshot.statement_date,
        "statement_period": {
            "start": snapshot.statement_period_start,
            "end": snapshot.statement_period_end,
        },
        "json_artifact_path": str(json_path),
        "md_artifact_path": str(md_path),
        "source_files": snapshot.source_files,
        "source_provenance": snapshot.source_provenance,
        "extraction_timestamp_utc": snapshot.extraction_timestamp_utc,
        "scoring_impact": snapshot.scoring_impact,
        "parse_status": snapshot.parse_status,
        "promoted_to_latest": snapshot.promoted_to_latest,
        "warnings": snapshot.warnings,
    }

    result = {"entries": [by_date[k] for k in sorted(by_date)]}
    if not dry_run:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result, True


def _copy_or_move_sources(
    source_files: list[str],
    raw_archive_root: Path,
    statement_date: str,
    move_processed: bool,
    dry_run: bool,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    target_dir = raw_archive_root / statement_date
    for source_file in source_files:
        src = Path(source_file)
        if not src.exists() or not src.is_file():
            continue
        target = target_dir / src.name
        action = "move" if move_processed else "copy"
        actions.append({"action": action, "source": str(src), "target": str(target)})
        if dry_run:
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        if move_processed:
            shutil.move(str(src), str(target))
        else:
            shutil.copy2(src, target)
    return actions


def _write_latest_pointers(output_root: Path, latest_json_source: Path, latest_md_source: Path, dry_run: bool) -> tuple[Path, Path]:
    latest_json, latest_md = _latest_pointer_paths(output_root)
    if not dry_run:
        output_root.mkdir(parents=True, exist_ok=True)
        latest_json.write_text(latest_json_source.read_text(encoding="utf-8"), encoding="utf-8")
        latest_md.write_text(latest_md_source.read_text(encoding="utf-8"), encoding="utf-8")
    return latest_json, latest_md


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    explicit_sources = [Path(s) for s in args.source]
    incoming_sources = [] if explicit_sources else _discover_incoming_sources(Path(args.incoming_dir))
    source_paths = sorted(explicit_sources or incoming_sources, key=lambda p: p.name.lower())

    if not source_paths:
        print("No statement sources found. Use --source or place files under --incoming-dir.")
        return 2

    try:
        sources = [load_statement_source(source_path=s) for s in source_paths]
        grouped = _group_sources_by_statement_date(sources)

        output_root = Path(args.output_root)
        raw_archive_root = Path(args.raw_archive_root)
        history_path = _history_index_path(output_root)

        print(f"Discovered inputs ({len(source_paths)}):")
        for p in source_paths:
            print(f"- {p}")

        latest_date: str | None = None
        latest_json_source: Path | None = None
        latest_md_source: Path | None = None
        promoted_groups = 0
        degraded_groups = 0

        expected_realized_accounts = {"X20-548022", "Z26-346415", "Z35-123695"}

        for statement_date in sorted(grouped):
            grouped_sources = grouped[statement_date]
            snapshot = build_snapshot_from_sources(
                sources=grouped_sources,
                statement_date=args.statement_date or statement_date,
                statement_period_start=args.statement_period_start,
                statement_period_end=args.statement_period_end,
                main_statement_account_numbers=set(args.main_account or []),
            )

            date_out = output_root / statement_date
            target_json = date_out / f"STATEMENT_GAIN_LOSS_{statement_date}.json"
            target_md = date_out / f"STATEMENT_GAIN_LOSS_{statement_date}.md"

            print(f"\nStatement date group: {statement_date}")
            print(f"- Group source count: {len(grouped_sources)}")
            print(f"- Target JSON: {target_json}")
            print(f"- Target Markdown: {target_md}")

            parse_status, quality_warnings = evaluate_snapshot_completeness(
                snapshot,
                expected_accounts=expected_realized_accounts,
            )

            if parse_status == "degraded":
                degraded_groups += 1
                snapshot = apply_snapshot_parse_status(
                    snapshot,
                    parse_status="degraded",
                    promoted_to_latest=False,
                    warnings_to_add=quality_warnings,
                )
                date_out = date_out / "degraded"
                target_json = date_out / f"STATEMENT_GAIN_LOSS_{statement_date}.json"
                target_md = date_out / f"STATEMENT_GAIN_LOSS_{statement_date}.md"
                print("- Parse status: degraded")
                print("- Promotion: skipped (latest preserved)")
                print("- New PDF parse completed but was not promoted because realized gain/loss totals were missing.")
            else:
                promoted_groups += 1
                snapshot = apply_snapshot_parse_status(
                    snapshot,
                    parse_status="complete",
                    promoted_to_latest=True,
                    warnings_to_add=quality_warnings,
                )
                print("- Parse status: complete")
                print("- Promotion: eligible")

            if not args.dry_run:
                json_path, md_path = write_snapshot_artifacts(snapshot, date_out)
            else:
                json_path, md_path = target_json, target_md

            history_payload, _ = _upsert_history_index(
                history_path,
                snapshot,
                json_path,
                md_path,
                dry_run=args.dry_run,
            )
            print(f"- History index: {history_path} ({len(history_payload.get('entries', []))} entries)")

            archive_actions = _copy_or_move_sources(
                snapshot.source_files,
                raw_archive_root,
                statement_date,
                move_processed=args.move_processed,
                dry_run=args.dry_run,
            )
            for action in archive_actions:
                print(f"- Archive {action['action']}: {action['source']} -> {action['target']}")

            if snapshot.promoted_to_latest and (latest_date is None or statement_date > latest_date):
                latest_date = statement_date
                latest_json_source = json_path
                latest_md_source = md_path

        if latest_json_source is not None and latest_md_source is not None:
            latest_json_path, latest_md_path = _write_latest_pointers(
                output_root,
                latest_json_source,
                latest_md_source,
                dry_run=args.dry_run,
            )
            print(f"\nLatest JSON pointer/output: {latest_json_path}")
            print(f"Latest Markdown pointer/output: {latest_md_path}")
        else:
            latest_json_path, latest_md_path = _latest_pointer_paths(output_root)
            print("\nLatest pointers unchanged: no complete snapshot qualified for promotion.")
            print(f"Latest JSON pointer/output preserved: {latest_json_path}")
            print(f"Latest Markdown pointer/output preserved: {latest_md_path}")

        print(f"Promoted groups: {promoted_groups}")
        print(f"Degraded groups: {degraded_groups}")
        print(f"Dry run: {'yes' if args.dry_run else 'no'}")
    except StatementParsingError as exc:
        print(f"STATEMENT-GAIN-LOSS-01 failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
