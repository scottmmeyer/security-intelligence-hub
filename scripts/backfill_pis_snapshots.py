#!/usr/bin/env python3
"""Backfill existing SIH analysis runs into PIS snapshot history.

This utility reconstructs canonical SIH snapshot/holding objects from
analysis run artifacts and reuses the canonical PIS registration service.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from src.pis.service import register_portfolio_snapshot_from_sih
from src.pis.storage import summarize_portfolio_history
from src.portfolio.models import PortfolioHolding, PortfolioSnapshot


DEFAULT_RUNS_ROOT = Path("data/portfolio_ingestion/analysis_runs")
DEFAULT_HISTORY_ROOT = Path("data/history/pis")
DEFAULT_INDEX_PATH = Path("data/history/pis/pis_snapshot_index.csv")


@dataclass(frozen=True)
class BackfillRunRecord:
    run_id: str
    snapshot_id: str
    status: str
    message: str = ""


@dataclass(frozen=True)
class BackfillSummary:
    eligible_runs: int
    registered_snapshots: int
    skipped_duplicates: int
    skipped_invalid_runs: int
    failures: int
    dry_run: bool
    output_history_root: str
    output_index_path: str
    records: tuple[BackfillRunRecord, ...]


def _to_float(raw: str | object, default: float = 0.0) -> float:
    try:
        text = str(raw or "").replace(",", "").replace("$", "").strip()
        return float(text) if text else default
    except ValueError:
        return default


def _to_opt_float(raw: str | object) -> float | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return _to_float(text, 0.0)
    except ValueError:
        return None


def _to_bool(raw: str | object) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "y"}


def _to_opt_text(raw: str | object) -> str | None:
    text = str(raw or "").strip()
    return text if text else None


def _load_snapshot(snapshot_path: Path) -> PortfolioSnapshot:
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    warnings = tuple(str(item) for item in data.get("normalization_warnings") or [])
    return PortfolioSnapshot(
        portfolio_snapshot_id=str(data.get("portfolio_snapshot_id") or ""),
        snapshot_date=str(data.get("snapshot_date") or ""),
        account_name=str(data.get("account_name") or ""),
        total_market_value=float(data.get("total_market_value") or 0.0),
        holding_count=int(data.get("holding_count") or 0),
        source_file=str(data.get("source_file") or ""),
        source_format=str(data.get("source_format") or ""),
        ingestion_status=str(data.get("ingestion_status") or ""),
        normalization_warnings=warnings,
        created_at_utc=str(data.get("created_at_utc") or ""),
        run_id=str(data.get("run_id") or ""),
    )


def _load_holdings(holdings_path: Path, snapshot: PortfolioSnapshot) -> list[PortfolioHolding]:
    rows = list(csv.DictReader(holdings_path.open("r", encoding="utf-8", newline="")))
    holdings: list[PortfolioHolding] = []
    for row in rows:
        holdings.append(
            PortfolioHolding(
                portfolio_snapshot_id=str(row.get("portfolio_snapshot_id") or snapshot.portfolio_snapshot_id),
                snapshot_date=str(row.get("snapshot_date") or snapshot.snapshot_date),
                account_name=str(row.get("account_name") or snapshot.account_name),
                symbol=str(row.get("symbol") or "").strip().upper(),
                description=str(row.get("description") or ""),
                quantity=_to_float(row.get("quantity"), 0.0),
                market_value=_to_float(row.get("market_value"), 0.0),
                percent_of_portfolio=_to_float(row.get("percent_of_portfolio"), 0.0),
                asset_class=str(row.get("asset_class") or "UNKNOWN"),
                geography=str(row.get("geography") or "UNKNOWN"),
                market_cap_bucket=str(row.get("market_cap_bucket") or "UNKNOWN"),
                mega_subtier=str(row.get("mega_subtier") or "N/A"),
                sector=str(row.get("sector") or "UNKNOWN"),
                industry=str(row.get("industry") or "UNKNOWN"),
                security_type=str(row.get("security_type") or "Other"),
                cost_basis=_to_opt_float(row.get("cost_basis")),
                composite_score=_to_opt_float(row.get("composite_score")),
                ess_score_text=_to_opt_text(row.get("ess_score_text")),
                zacks_rating=_to_opt_text(row.get("zacks_rating")),
                benchmark_id=_to_opt_text(row.get("benchmark_id")),
                investable_vehicle_id=_to_opt_text(row.get("investable_vehicle_id")),
                source_file=str(row.get("source_file") or snapshot.source_file),
                created_at_utc=str(row.get("created_at_utc") or snapshot.created_at_utc),
                operational_state=str(row.get("operational_state") or "ACTIVE_POSITION"),
                is_cash_equivalent=_to_bool(row.get("is_cash_equivalent")),
                safe_to_offset_cash=_to_bool(row.get("safe_to_offset_cash")),
                danelfin_score=_to_opt_text(row.get("danelfin_score")),
            )
        )
    return holdings


def _run_sort_key(run_dir: Path) -> tuple[str, str]:
    run_meta = run_dir / "run_metadata.json"
    if run_meta.exists():
        try:
            data = json.loads(run_meta.read_text(encoding="utf-8"))
            return str(data.get("created_at_utc") or ""), run_dir.name
        except Exception:
            pass
    return "", run_dir.name


def _discover_run_dirs(runs_root: Path, *, run_id: str | None, limit: int | None) -> list[Path]:
    if run_id:
        candidate = runs_root / run_id
        return [candidate] if candidate.exists() else []

    run_dirs = [p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("PAR-")]
    run_dirs.sort(key=_run_sort_key, reverse=True)
    if limit is not None:
        run_dirs = run_dirs[: max(0, limit)]
    return run_dirs


def backfill_pis_snapshots(
    *,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    history_root: Path = DEFAULT_HISTORY_ROOT,
    index_path: Path = DEFAULT_INDEX_PATH,
    run_id: str | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> BackfillSummary:
    records: list[BackfillRunRecord] = []

    run_dirs = _discover_run_dirs(runs_root, run_id=run_id, limit=limit)
    existing_snapshot_ids = set(
        summarize_portfolio_history(index_path=str(index_path)).get("snapshot_ids", [])
    )
    seen_snapshot_ids = set(existing_snapshot_ids)

    registered = 0
    duplicates = 0
    invalid = 0
    failures = 0

    for run_dir in run_dirs:
        rid = run_dir.name
        snapshot_path = run_dir / "snapshot.json"
        holdings_path = run_dir / "holdings.csv"

        if not snapshot_path.exists() or not holdings_path.exists():
            invalid += 1
            records.append(
                BackfillRunRecord(
                    run_id=rid,
                    snapshot_id="",
                    status="SKIPPED_INVALID",
                    message="Missing snapshot.json or holdings.csv",
                )
            )
            continue

        try:
            snapshot = _load_snapshot(snapshot_path)
            holdings = _load_holdings(holdings_path, snapshot)
            if not holdings:
                invalid += 1
                records.append(
                    BackfillRunRecord(
                        run_id=rid,
                        snapshot_id=snapshot.portfolio_snapshot_id,
                        status="SKIPPED_INVALID",
                        message="No holdings rows found",
                    )
                )
                continue

            if dry_run:
                if str(snapshot.ingestion_status).upper() == "REJECTED":
                    status = "DRY_RUN_SKIPPED"
                    msg = "Skipped because SIH snapshot was rejected."
                    invalid += 1
                elif snapshot.portfolio_snapshot_id in seen_snapshot_ids:
                    status = "DRY_RUN_DUPLICATE"
                    msg = "Duplicate PIS snapshot suppressed."
                    duplicates += 1
                else:
                    status = "DRY_RUN_REGISTER"
                    msg = ""
                    seen_snapshot_ids.add(snapshot.portfolio_snapshot_id)
                records.append(
                    BackfillRunRecord(
                        run_id=rid,
                        snapshot_id=snapshot.portfolio_snapshot_id,
                        status=status,
                        message=msg,
                    )
                )
                continue

            result = register_portfolio_snapshot_from_sih(
                snapshot=snapshot,
                holdings=holdings,
                history_root=str(history_root),
                index_path=str(index_path),
            )
            if result.registered:
                registered += 1
                status = "REGISTERED"
            elif result.duplicate:
                duplicates += 1
                status = "SKIPPED_DUPLICATE"
            else:
                invalid += 1
                status = "SKIPPED_INVALID"

            records.append(
                BackfillRunRecord(
                    run_id=rid,
                    snapshot_id=result.snapshot_id,
                    status=status,
                    message=result.warning,
                )
            )
        except ValueError as exc:
            invalid += 1
            records.append(
                BackfillRunRecord(
                    run_id=rid,
                    snapshot_id="",
                    status="SKIPPED_INVALID",
                    message=str(exc),
                )
            )
        except Exception as exc:
            failures += 1
            records.append(
                BackfillRunRecord(
                    run_id=rid,
                    snapshot_id="",
                    status="FAILED",
                    message=str(exc),
                )
            )

    return BackfillSummary(
        eligible_runs=len(run_dirs),
        registered_snapshots=registered,
        skipped_duplicates=duplicates,
        skipped_invalid_runs=invalid,
        failures=failures,
        dry_run=dry_run,
        output_history_root=str(history_root),
        output_index_path=str(index_path),
        records=tuple(records),
    )


def _print_summary(summary: BackfillSummary) -> None:
    print("PIS backfill summary")
    print("--------------------")
    print(f"eligible_runs: {summary.eligible_runs}")
    print(f"registered_snapshots: {summary.registered_snapshots}")
    print(f"skipped_duplicates: {summary.skipped_duplicates}")
    print(f"skipped_invalid_runs: {summary.skipped_invalid_runs}")
    print(f"failures: {summary.failures}")
    print(f"dry_run: {summary.dry_run}")
    print(f"output_history_root: {summary.output_history_root}")
    print(f"output_index_path: {summary.output_index_path}")
    print("records:")
    for record in summary.records:
        msg = f" ({record.message})" if record.message else ""
        print(f"- {record.run_id}: {record.status} snapshot={record.snapshot_id}{msg}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill existing SIH analysis runs into PIS snapshot history.")
    parser.add_argument("--all", action="store_true", help="Backfill all PAR runs.")
    parser.add_argument("--run-id", default="", help="Backfill a specific PAR run id.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be registered without writing.")
    parser.add_argument("--limit", type=int, default=None, help="Backfill most recent N runs.")
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT), help="Analysis runs root directory.")
    parser.add_argument("--history-root", default=str(DEFAULT_HISTORY_ROOT), help="PIS history root directory.")
    parser.add_argument("--index-path", default=str(DEFAULT_INDEX_PATH), help="PIS index csv path.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    run_id = args.run_id.strip() or None
    if not args.all and not run_id:
        parser.error("Specify --all or --run-id PAR-... to choose backfill scope.")

    summary = backfill_pis_snapshots(
        runs_root=Path(args.runs_root),
        history_root=Path(args.history_root),
        index_path=Path(args.index_path),
        run_id=run_id,
        dry_run=bool(args.dry_run),
        limit=args.limit,
    )
    _print_summary(summary)

    return 1 if summary.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
