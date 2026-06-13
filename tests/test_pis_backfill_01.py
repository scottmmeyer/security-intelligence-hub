from __future__ import annotations

import csv
import json
from pathlib import Path

from scripts.backfill_pis_snapshots import backfill_pis_snapshots
from src.pis.storage import (
    pis_latest_snapshot_summary,
    pis_snapshot_history_health,
    pis_snapshot_inventory,
    pis_value_timeline,
)


_PASS_ACCOUNT_NAME = "General Brokerage, Joint WROS - TOD, Individual - TOD"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_holdings(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "portfolio_snapshot_id",
        "snapshot_date",
        "account_name",
        "symbol",
        "description",
        "quantity",
        "market_value",
        "percent_of_portfolio",
        "asset_class",
        "geography",
        "market_cap_bucket",
        "mega_subtier",
        "sector",
        "industry",
        "security_type",
        "cost_basis",
        "composite_score",
        "ess_score_text",
        "zacks_rating",
        "benchmark_id",
        "investable_vehicle_id",
        "source_file",
        "created_at_utc",
        "operational_state",
        "is_cash_equivalent",
        "safe_to_offset_cash",
        "danelfin_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _make_run(run_root: Path, run_id: str, *, missing_holdings: bool = False) -> Path:
    run_dir = run_root / run_id
    snapshot = {
        "portfolio_snapshot_id": f"PSNAP-{run_id}",
        "snapshot_date": "2026-05-29",
        "account_name": _PASS_ACCOUNT_NAME,
        "total_market_value": 1500.0,
        "holding_count": 2,
        "source_file": "sample.csv",
        "source_format": "FIDELITY_CSV",
        "ingestion_status": "PARTIAL",
        "normalization_warnings": ["example warning"],
        "created_at_utc": "2026-05-29T14:00:00+00:00",
        "run_id": run_id,
    }
    _write_json(run_dir / "snapshot.json", snapshot)
    _write_json(
        run_dir / "run_metadata.json",
        {
            "run_id": run_id,
            "portfolio_snapshot_id": f"PSNAP-{run_id}",
            "snapshot_date": "2026-05-29",
            "status": "COMPLETE",
            "created_at_utc": "2026-05-29T14:00:00+00:00",
        },
    )

    if not missing_holdings:
        _write_holdings(
            run_dir / "holdings.csv",
            [
                {
                    "portfolio_snapshot_id": f"PSNAP-{run_id}",
                    "snapshot_date": "2026-05-29",
                    "account_name": _PASS_ACCOUNT_NAME,
                    "symbol": "MSFT",
                    "description": "Microsoft",
                    "quantity": "2",
                    "market_value": "1000",
                    "percent_of_portfolio": "66.67",
                    "asset_class": "EQUITIES",
                    "geography": "US",
                    "market_cap_bucket": "MEGA",
                    "mega_subtier": "HYPER_MEGA",
                    "sector": "TECHNOLOGY",
                    "industry": "SOFTWARE",
                    "security_type": "Common Stock",
                    "cost_basis": "900",
                    "composite_score": "4.2",
                    "ess_score_text": "BULLISH",
                    "zacks_rating": "1",
                    "benchmark_id": "BM_US_MEGA_SP500",
                    "investable_vehicle_id": "VEH_US_MEGA_SPY",
                    "source_file": "sample.csv",
                    "created_at_utc": "2026-05-29T14:00:00+00:00",
                    "operational_state": "ACTIVE_POSITION",
                    "is_cash_equivalent": "false",
                    "safe_to_offset_cash": "false",
                    "danelfin_score": "9.0",
                },
                {
                    "portfolio_snapshot_id": f"PSNAP-{run_id}",
                    "snapshot_date": "2026-05-29",
                    "account_name": _PASS_ACCOUNT_NAME,
                    "symbol": "SPAXX**",
                    "description": "Cash Sweep",
                    "quantity": "1",
                    "market_value": "500",
                    "percent_of_portfolio": "33.33",
                    "asset_class": "CASH",
                    "geography": "US",
                    "market_cap_bucket": "UNKNOWN",
                    "mega_subtier": "N/A",
                    "sector": "UNKNOWN",
                    "industry": "UNKNOWN",
                    "security_type": "Cash",
                    "cost_basis": "500",
                    "composite_score": "",
                    "ess_score_text": "",
                    "zacks_rating": "",
                    "benchmark_id": "",
                    "investable_vehicle_id": "",
                    "source_file": "sample.csv",
                    "created_at_utc": "2026-05-29T14:00:00+00:00",
                    "operational_state": "CASH_EQUIVALENT",
                    "is_cash_equivalent": "true",
                    "safe_to_offset_cash": "false",
                    "danelfin_score": "",
                },
            ],
        )

    return run_dir


def test_backfill_registers_existing_par_run(tmp_path: Path) -> None:
    runs_root = tmp_path / "analysis_runs"
    history_root = tmp_path / "history" / "pis"
    index_path = history_root / "pis_snapshot_index.csv"

    run_id = "PAR-20260529-AAAA1111"
    _make_run(runs_root, run_id)

    summary = backfill_pis_snapshots(
        runs_root=runs_root,
        history_root=history_root,
        index_path=index_path,
        run_id=run_id,
    )

    assert summary.eligible_runs == 1
    assert summary.registered_snapshots == 1
    assert index_path.exists()

    rows = list(csv.DictReader(index_path.open("r", encoding="utf-8", newline="")))
    assert len(rows) == 1
    assert rows[0]["source_run_id"] == run_id


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    runs_root = tmp_path / "analysis_runs"
    history_root = tmp_path / "history" / "pis"
    index_path = history_root / "pis_snapshot_index.csv"
    run_id = "PAR-20260529-BBBB2222"
    _make_run(runs_root, run_id)

    first = backfill_pis_snapshots(
        runs_root=runs_root,
        history_root=history_root,
        index_path=index_path,
        run_id=run_id,
    )
    second = backfill_pis_snapshots(
        runs_root=runs_root,
        history_root=history_root,
        index_path=index_path,
        run_id=run_id,
    )

    assert first.registered_snapshots == 1
    assert second.registered_snapshots == 0
    assert second.skipped_duplicates == 1


def test_backfill_dry_run_does_not_write(tmp_path: Path) -> None:
    runs_root = tmp_path / "analysis_runs"
    history_root = tmp_path / "history" / "pis"
    index_path = history_root / "pis_snapshot_index.csv"
    run_id = "PAR-20260529-CCCC3333"
    _make_run(runs_root, run_id)

    summary = backfill_pis_snapshots(
        runs_root=runs_root,
        history_root=history_root,
        index_path=index_path,
        run_id=run_id,
        dry_run=True,
    )

    assert summary.dry_run is True
    assert summary.eligible_runs == 1
    assert not index_path.exists()


def test_invalid_missing_holdings_is_skipped_with_warning(tmp_path: Path) -> None:
    runs_root = tmp_path / "analysis_runs"
    history_root = tmp_path / "history" / "pis"
    index_path = history_root / "pis_snapshot_index.csv"
    run_id = "PAR-20260529-DDDD4444"
    _make_run(runs_root, run_id, missing_holdings=True)

    summary = backfill_pis_snapshots(
        runs_root=runs_root,
        history_root=history_root,
        index_path=index_path,
        run_id=run_id,
    )

    assert summary.skipped_invalid_runs == 1
    assert summary.records[0].status == "SKIPPED_INVALID"
    assert "Missing snapshot.json or holdings.csv" in summary.records[0].message


def test_dashboard_storage_views_populate_after_backfill(tmp_path: Path) -> None:
    runs_root = tmp_path / "analysis_runs"
    history_root = tmp_path / "history" / "pis"
    index_path = history_root / "pis_snapshot_index.csv"
    run_id = "PAR-20260529-EEEE5555"
    _make_run(runs_root, run_id)

    summary = backfill_pis_snapshots(
        runs_root=runs_root,
        history_root=history_root,
        index_path=index_path,
        run_id=run_id,
    )
    assert summary.registered_snapshots == 1

    inventory = pis_snapshot_inventory(index_path=index_path)
    timeline = pis_value_timeline(index_path=index_path)
    latest = pis_latest_snapshot_summary(index_path=index_path, repo_root=tmp_path)
    health = pis_snapshot_history_health(index_path=index_path)

    assert len(inventory) == 1
    assert len(timeline) == 1
    assert latest["snapshot_date"] == "2026-05-29"
    assert latest["position_count"] == 2
    assert health["snapshot_count"] == 1
