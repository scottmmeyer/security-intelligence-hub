"""Tests for PIS-007A remediations.

Test matrix:
  A. position-count integrity: expected > 0, loaded = 0 → warning emitted, pair skipped
  B. position-count integrity: expected = 0, loaded = 0 → no warning
  C. refresh logging: started message printed to stderr
  D. refresh logging: failure message printed to stderr
  E. lineage summary returns latest snapshot_date even when newer PAR has older portfolio date
"""

from __future__ import annotations

import csv
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# A + B — Change Detection Integrity Validation
# ---------------------------------------------------------------------------

def _make_index_csv(tmp_path: Path, snapshots: list[dict]) -> Path:
    """Create a minimal pis_snapshot_index.csv with two snapshot rows."""
    idx = tmp_path / "pis_snapshot_index.csv"
    headers = [
        "snapshot_id", "snapshot_date", "account_id", "account_name",
        "source_file", "source_run_id", "source_format",
        "partition_path", "snapshot_path", "positions_path",
        "position_count", "portfolio_value", "cash_value", "equity_value",
        "ingestion_status", "created_at_utc",
    ]
    with idx.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for s in snapshots:
            w.writerow(s)
    return idx


def _make_positions_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("symbol,description,quantity,market_value,percent_of_account,"
                        "source_percent_of_account,cost_basis_total,security_type,"
                        "operational_state,is_cash_equivalent,source_file,created_at_utc\n")
        return
    headers = list(rows[0].keys())
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _make_canonical_csv(tmp_path: Path, snapshot_dates: list[str]) -> Path:
    can = tmp_path / "canonical" / "canonical_daily_snapshots.csv"
    can.parent.mkdir(parents=True, exist_ok=True)
    headers = ["snapshot_date", "canonical_snapshot_id", "governance_status",
               "selection_policy", "selection_reason", "source_file",
               "portfolio_value", "cash", "position_count"]
    with can.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        for i, d in enumerate(snapshot_dates):
            w.writerow({
                "snapshot_date": d,
                "canonical_snapshot_id": f"PSNAP-{d.replace('-','')}-TEST{i:04d}",
                "governance_status": "PASS",
                "selection_policy": "PASS_THEN_LATEST_INGESTION",
                "selection_reason": "test",
                "source_file": "test.csv",
                "portfolio_value": 100000.0,
                "cash": 0.0,
                "position_count": 1,
            })
    return can


def test_integrity_warning_emitted_when_positions_missing(tmp_path, monkeypatch):
    """A: expected > 0 positions, 0 loaded → warning in result."""
    import src.pis.change_detection as cd

    snap_id_a = "PSNAP-20260101-AAAA"
    snap_id_b = "PSNAP-20260102-BBBB"

    pos_a = tmp_path / f"snapshot_date=2026-01-01/account_id=P/snapshot_id={snap_id_a}/position_snapshots.csv"
    pos_b = tmp_path / f"snapshot_date=2026-01-02/account_id=P/snapshot_id={snap_id_b}/position_snapshots.csv"

    # A has valid positions; B has header only (empty = missing data)
    _make_positions_csv(pos_a, [
        {"snapshot_id": snap_id_a, "snapshot_date": "2026-01-01", "account_id": "P",
         "account_name": "General Brokerage", "symbol": "AAPL", "description": "Apple",
         "quantity": "10", "market_value": "1000", "percent_of_account": "1",
         "source_percent_of_account": "1", "cost_basis_total": "900",
         "security_type": "Common Stock", "operational_state": "ACTIVE_POSITION",
         "is_cash_equivalent": "false", "source_file": "test.csv", "created_at_utc": "2026-01-01T00:00:00"},
    ])
    _make_positions_csv(pos_b, [])  # empty — no rows despite position_count=5 in index

    row_a = {
        "snapshot_id": snap_id_a, "snapshot_date": "2026-01-01",
        "account_id": "P", "account_name": "General Brokerage",
        "positions_path": str(pos_a), "position_count": "1",
        "portfolio_value": "1000", "cash_value": "0",
    }
    row_b = {
        "snapshot_id": snap_id_b, "snapshot_date": "2026-01-02",
        "account_id": "P", "account_name": "General Brokerage",
        "positions_path": str(pos_b), "position_count": "5",
        "portfolio_value": "2000", "cash_value": "0",
    }

    # Bypass canonical machinery by patching _snapshot_groups directly
    fake_groups = [
        cd._DateSnapshotGroup(snapshot_date="2026-01-01", snapshot_ids=(snap_id_a,), rows=(row_a,)),
        cd._DateSnapshotGroup(snapshot_date="2026-01-02", snapshot_ids=(snap_id_b,), rows=(row_b,)),
    ]
    monkeypatch.setattr(cd, "_snapshot_groups", lambda *args, **kwargs: fake_groups)

    changes_root = tmp_path / "changes"
    changes_root.mkdir()

    result = cd.compute_all_snapshot_changes(
        changes_root=changes_root,
        repo_root=tmp_path,
    )

    warnings = result.get("integrity_warnings", [])
    assert len(warnings) >= 1, "Expected at least one integrity warning"
    assert any(snap_id_b in w for w in warnings), f"Warning should mention {snap_id_b}"
    assert any("INTEGRITY_WARNING" in w for w in warnings)

    # The corrupt pair should be skipped — no EXITED_POSITION records for AAPL
    change_records = result.get("change_records", [])
    exited = [r for r in change_records if r.get("change_type") == "EXITED_POSITION"]
    assert len(exited) == 0, "Corrupt snapshot pair should be skipped, not produce false EXITED records"


def test_no_integrity_warning_when_positions_expected_zero(tmp_path, monkeypatch):
    """B: expected = 0, loaded = 0 → no integrity warning."""
    import src.pis.change_detection as cd

    snap_id_a = "PSNAP-20260201-CCCC"
    snap_id_b = "PSNAP-20260202-DDDD"

    pos_a = tmp_path / f"snapshot_date=2026-02-01/account_id=P/snapshot_id={snap_id_a}/position_snapshots.csv"
    pos_b = tmp_path / f"snapshot_date=2026-02-02/account_id=P/snapshot_id={snap_id_b}/position_snapshots.csv"
    _make_positions_csv(pos_a, [])
    _make_positions_csv(pos_b, [])

    row_a = {
        "snapshot_id": snap_id_a, "snapshot_date": "2026-02-01",
        "account_id": "P", "account_name": "General Brokerage",
        "positions_path": str(pos_a), "position_count": "0",
        "portfolio_value": "0", "cash_value": "0",
    }
    row_b = {
        "snapshot_id": snap_id_b, "snapshot_date": "2026-02-02",
        "account_id": "P", "account_name": "General Brokerage",
        "positions_path": str(pos_b), "position_count": "0",
        "portfolio_value": "0", "cash_value": "0",
    }

    fake_groups = [
        cd._DateSnapshotGroup(snapshot_date="2026-02-01", snapshot_ids=(snap_id_a,), rows=(row_a,)),
        cd._DateSnapshotGroup(snapshot_date="2026-02-02", snapshot_ids=(snap_id_b,), rows=(row_b,)),
    ]
    monkeypatch.setattr(cd, "_snapshot_groups", lambda *args, **kwargs: fake_groups)

    changes_root = tmp_path / "changes2"
    changes_root.mkdir()

    result = cd.compute_all_snapshot_changes(
        changes_root=changes_root,
        repo_root=tmp_path,
    )

    warnings = result.get("integrity_warnings", [])
    assert len(warnings) == 0, f"No warning expected when position_count=0; got: {warnings}"


# ---------------------------------------------------------------------------
# C + D — Refresh Logging
# ---------------------------------------------------------------------------

def test_refresh_logging_started_and_completed(monkeypatch, capsys):
    """C: Both started and completed messages go to stderr on success."""

    class _SyncThread:
        """Run target synchronously so we can capture output in the test."""
        def __init__(self, target, daemon, name, **kwargs):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr("threading.Thread", _SyncThread)
    monkeypatch.setattr(
        "src.pis.refresh_orchestrator.trigger_startup_refresh",
        lambda **_: None,
    )

    import src.portfolio.runner as runner
    runner._trigger_pis_refresh_background(repo_root=Path("."))

    captured = capsys.readouterr()
    assert "[PIS] Post-ingestion refresh started." in captured.err
    assert "[PIS] Post-ingestion refresh completed." in captured.err


def test_refresh_logging_failure_message(monkeypatch, capsys):
    """D: Failure message goes to stderr when refresh raises."""

    class _SyncThread:
        def __init__(self, target, daemon, name, **kwargs):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr("threading.Thread", _SyncThread)

    def _bad_refresh(**_):
        raise RuntimeError("test-induced failure")

    monkeypatch.setattr(
        "src.pis.refresh_orchestrator.trigger_startup_refresh",
        _bad_refresh,
    )

    import src.portfolio.runner as runner
    # Must not raise
    runner._trigger_pis_refresh_background(repo_root=Path("."))

    captured = capsys.readouterr()
    assert "[PIS] Post-ingestion refresh started." in captured.err
    assert "[PIS] Post-ingestion refresh failed:" in captured.err
    assert "test-induced failure" in captured.err
    # Completed should NOT appear when failure occurs
    assert "[PIS] Post-ingestion refresh completed." not in captured.err


# ---------------------------------------------------------------------------
# E — Dashboard Upload Date Truthfulness
# ---------------------------------------------------------------------------

def test_lineage_summary_returns_latest_snapshot_date(tmp_path):
    """E: latest_upload_date reflects latest snapshot_date, not latest created_at_utc.

    Setup: PAR-B has an older snapshot_date (2026-05-01) but a newer created_at_utc
    (because it was re-analyzed later today).  PAR-A has a newer snapshot_date
    (2026-06-14).  The dashboard must show 2026-06-14, not 2026-05-01.
    """
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.pis.storage import pis_sih_lineage_summary

    manifest = {
        "portfolios": [
            {
                "run_id": "PAR-A",
                "snapshot_date": "2026-06-14",
                "created_at_utc": "2026-06-14T09:00:00+00:00",
            },
            {
                "run_id": "PAR-B",
                "snapshot_date": "2026-05-01",
                "created_at_utc": "2026-06-15T11:00:00+00:00",  # newer created_at, older data
            },
        ]
    }
    mf_path = tmp_path / "manifest.json"
    mf_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = pis_sih_lineage_summary(
        manifest_path=mf_path,
        analysis_runs_root=tmp_path,
        repo_root=tmp_path,
    )

    assert result["latest_upload_date"] == "2026-06-14", (
        f"Expected 2026-06-14 (latest snapshot_date), got {result['latest_upload_date']!r}. "
        "The sort key should prioritize snapshot_date, not created_at_utc."
    )
    assert result["latest_par"] == "PAR-A"
    assert result["total_sih_analyses_captured"] == 2
