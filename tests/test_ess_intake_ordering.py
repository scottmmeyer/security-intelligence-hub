"""Tests for ESS-INTAKE-ORDERING-01: merged provider snapshot.

Validates that signal_snapshot.csv reflects a merged view of all providers
regardless of intake execution order.

Test matrix (from issue spec):
  T01: StarMine only
  T02: Non-StarMine only
  T03: StarMine then Non-StarMine
  T04: Non-StarMine then StarMine
  T05: Multiple same-day provider refreshes

Expected in all multi-provider cases:
  - StarMine symbols preserved
  - Non-StarMine symbols preserved
  - Coverage calculations identical regardless of execution order
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.history.signal_snapshot_manager import (
    _build_merged_snapshot,
    _coverage_rank,
    append_signal_snapshots,
    build_signal_storage_paths,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _starmine_row(symbol: str, ess_text: str = "BULLISH") -> dict:
    return {
        "snapshot_date": "2026-06-15",
        "created_at_utc": "2026-06-15T10:00:00+00:00",
        "run_id": "intake-20260615-sm",
        "provider": "FIDELITY",
        "source_file": "EquitySummaryScores-15Jun2026.csv",
        "symbol": symbol,
        "coverage_domain": "STARMINE_COVERED",
        "signal_coverage_status": "COVERED",
        "starmine_ess_text": ess_text,
        "starmine_ess_numeric": "4.0",
        "starmine_ess_numeric_estimated": "False",
        "starmine_ess_source_type": "DIRECT",
    }


def _nonstarmine_row(symbol: str) -> dict:
    return {
        "snapshot_date": "2026-06-15",
        "created_at_utc": "2026-06-15T11:00:00+00:00",
        "run_id": "intake-20260615-nonstarmine",
        "provider": "FIDELITY",
        "source_file": "non-ess.csv",
        "symbol": symbol,
        "coverage_domain": "NON_STARMINE_ANALYST",
        "signal_coverage_status": "NON_COVERED",
        "starmine_ess_text": "",
        "starmine_ess_numeric": "",
        "starmine_ess_numeric_estimated": "False",
        "starmine_ess_source_type": "UNKNOWN",
    }


def _write_partition(tmp_path: Path, run_id: str, rows: list[dict]) -> Path:
    """Write a fake historical partition and return its directory."""
    date = rows[0]["snapshot_date"] if rows else "2026-06-15"
    run_dir = tmp_path / f"snapshot_date={date}" / f"run_id={run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    from src.history.signal_snapshot_manager import SNAPSHOT_HEADERS, _write_csv_rows
    snap_path = run_dir / "signal_snapshots.csv"
    _write_csv_rows(snap_path, SNAPSHOT_HEADERS, rows)
    return run_dir


def _read_snapshot_syms(snapshot_path: Path) -> dict[str, dict]:
    """Return {symbol: row} from a signal_snapshot.csv."""
    result = {}
    for row in csv.DictReader(snapshot_path.open()):
        sym = row.get("symbol", "").strip().upper()
        if sym:
            result[sym] = row
    return result


# ---------------------------------------------------------------------------
# T01: StarMine only
# ---------------------------------------------------------------------------

def test_T01_starmine_only(tmp_path):
    """StarMine-only run: STARMINE_COVERED rows appear in merged snapshot."""
    rows = [_starmine_row("MU"), _starmine_row("VRT"), _starmine_row("NVDA")]
    merged = _build_merged_snapshot(
        snapshot_date="2026-06-15",
        history_root=tmp_path,
        extra_rows=rows,
    )
    syms = {r["symbol"] for r in merged}
    assert "MU" in syms
    assert "VRT" in syms
    assert "NVDA" in syms
    # All should be STARMINE_COVERED
    for r in merged:
        assert r["coverage_domain"] == "STARMINE_COVERED"


# ---------------------------------------------------------------------------
# T02: Non-StarMine only
# ---------------------------------------------------------------------------

def test_T02_nonstarmine_only(tmp_path):
    """Non-StarMine-only run: NON_STARMINE symbols appear in merged snapshot."""
    rows = [_nonstarmine_row("AAON"), _nonstarmine_row("BCO")]
    merged = _build_merged_snapshot(
        snapshot_date="2026-06-15",
        history_root=tmp_path,
        extra_rows=rows,
    )
    syms = {r["symbol"] for r in merged}
    assert "AAON" in syms
    assert "BCO" in syms


# ---------------------------------------------------------------------------
# T03: StarMine then Non-StarMine
# ---------------------------------------------------------------------------

def test_T03_starmine_then_nonstarmine(tmp_path):
    """StarMine runs first, Non-StarMine runs second.
    Merged snapshot must contain BOTH providers' symbols.
    MU must be STARMINE_COVERED (not overwritten by Non-StarMine run).
    """
    # StarMine run already persisted as a historical partition
    sm_rows = [_starmine_row("MU", "VERY_BULLISH"), _starmine_row("VRT", "BULLISH")]
    _write_partition(tmp_path, "intake-sm", sm_rows)

    # Non-StarMine runs now (extra_rows = current run)
    nonsm_rows = [_nonstarmine_row("AAON"), _nonstarmine_row("BCO")]
    merged = _build_merged_snapshot(
        snapshot_date="2026-06-15",
        history_root=tmp_path,
        extra_rows=nonsm_rows,
    )

    syms_by_sym = {r["symbol"]: r for r in merged}

    # StarMine symbols preserved
    assert "MU" in syms_by_sym
    assert syms_by_sym["MU"]["coverage_domain"] == "STARMINE_COVERED"
    assert syms_by_sym["MU"]["starmine_ess_text"] == "VERY_BULLISH"

    assert "VRT" in syms_by_sym
    assert syms_by_sym["VRT"]["coverage_domain"] == "STARMINE_COVERED"

    # Non-StarMine symbols also present
    assert "AAON" in syms_by_sym
    assert "BCO" in syms_by_sym


# ---------------------------------------------------------------------------
# T04: Non-StarMine then StarMine
# ---------------------------------------------------------------------------

def test_T04_nonstarmine_then_starmine(tmp_path):
    """Non-StarMine runs first, StarMine runs second.
    Result must be identical to T03 (order independence).
    """
    # Non-StarMine run already persisted
    nonsm_rows = [_nonstarmine_row("AAON"), _nonstarmine_row("BCO")]
    _write_partition(tmp_path, "intake-nonsm", nonsm_rows)

    # StarMine runs now (extra_rows = current run)
    sm_rows = [_starmine_row("MU", "VERY_BULLISH"), _starmine_row("VRT", "BULLISH")]
    merged = _build_merged_snapshot(
        snapshot_date="2026-06-15",
        history_root=tmp_path,
        extra_rows=sm_rows,
    )

    syms_by_sym = {r["symbol"]: r for r in merged}

    # StarMine symbols present with correct domain
    assert "MU" in syms_by_sym
    assert syms_by_sym["MU"]["coverage_domain"] == "STARMINE_COVERED"
    assert syms_by_sym["MU"]["starmine_ess_text"] == "VERY_BULLISH"

    assert "VRT" in syms_by_sym
    assert syms_by_sym["VRT"]["coverage_domain"] == "STARMINE_COVERED"

    # Non-StarMine symbols also present
    assert "AAON" in syms_by_sym
    assert "BCO" in syms_by_sym


# ---------------------------------------------------------------------------
# T05: Multiple same-day provider refreshes
# ---------------------------------------------------------------------------

def test_T05_multiple_same_day_refreshes(tmp_path):
    """Multiple refreshes on the same day: latest STARMINE_COVERED row wins."""
    # First StarMine run
    sm_rows_v1 = [_starmine_row("MU", "BULLISH")]  # older
    sm_rows_v1[0]["created_at_utc"] = "2026-06-15T08:00:00+00:00"
    _write_partition(tmp_path, "intake-sm-v1", sm_rows_v1)

    # Second StarMine run (same symbol, newer posture)
    sm_rows_v2 = [_starmine_row("MU", "VERY_BULLISH")]  # newer
    sm_rows_v2[0]["created_at_utc"] = "2026-06-15T12:00:00+00:00"

    merged = _build_merged_snapshot(
        snapshot_date="2026-06-15",
        history_root=tmp_path,
        extra_rows=sm_rows_v2,
    )

    syms_by_sym = {r["symbol"]: r for r in merged}
    # Latest StarMine run wins
    assert syms_by_sym["MU"]["starmine_ess_text"] == "VERY_BULLISH"
    assert syms_by_sym["MU"]["created_at_utc"] == "2026-06-15T12:00:00+00:00"


# ---------------------------------------------------------------------------
# T06: Order independence — T03 and T04 produce identical symbol sets
# ---------------------------------------------------------------------------

def test_T06_order_independence(tmp_path):
    """The same symbols appear regardless of which provider runs last."""
    # Setup 1: StarMine persisted, NonStarMine is current
    p1 = tmp_path / "order1"
    sm_rows = [_starmine_row("MU", "VERY_BULLISH"), _starmine_row("VRT", "BULLISH")]
    _write_partition(p1, "intake-sm", sm_rows)
    nonsm_rows = [_nonstarmine_row("AAON")]
    merged_order1 = _build_merged_snapshot(
        snapshot_date="2026-06-15", history_root=p1, extra_rows=nonsm_rows
    )

    # Setup 2: NonStarMine persisted, StarMine is current
    p2 = tmp_path / "order2"
    _write_partition(p2, "intake-nonsm", nonsm_rows)
    merged_order2 = _build_merged_snapshot(
        snapshot_date="2026-06-15", history_root=p2, extra_rows=sm_rows
    )

    syms1 = {r["symbol"] for r in merged_order1}
    syms2 = {r["symbol"] for r in merged_order2}

    assert syms1 == syms2, f"Symbol sets differ: {syms1} vs {syms2}"

    # StarMine quality preserved in both orderings
    by_sym1 = {r["symbol"]: r for r in merged_order1}
    by_sym2 = {r["symbol"]: r for r in merged_order2}
    assert by_sym1["MU"]["coverage_domain"] == "STARMINE_COVERED"
    assert by_sym2["MU"]["coverage_domain"] == "STARMINE_COVERED"
    assert by_sym1["MU"]["starmine_ess_text"] == by_sym2["MU"]["starmine_ess_text"]


# ---------------------------------------------------------------------------
# T07: Coverage rank function
# ---------------------------------------------------------------------------

def test_T07_coverage_rank():
    """_coverage_rank returns correct priority ordering."""
    starmine_with_ess = {"coverage_domain": "STARMINE_COVERED", "starmine_ess_text": "BULLISH"}
    has_ess_no_starmine = {"coverage_domain": "NON_STARMINE_ANALYST", "starmine_ess_text": "BULLISH"}
    no_ess = {"coverage_domain": "NON_STARMINE_ANALYST", "starmine_ess_text": ""}

    assert _coverage_rank(starmine_with_ess) > _coverage_rank(has_ess_no_starmine)
    assert _coverage_rank(has_ess_no_starmine) > _coverage_rank(no_ess)
    assert _coverage_rank(starmine_with_ess) == 2
    assert _coverage_rank(no_ess) == 0


# ---------------------------------------------------------------------------
# T08: Non-StarMine does not overwrite StarMine for same symbol
# ---------------------------------------------------------------------------

def test_T08_nonstarmine_does_not_overwrite_starmine(tmp_path):
    """When a symbol appears in both StarMine and Non-StarMine, StarMine wins."""
    sm_row = _starmine_row("MU", "VERY_BULLISH")
    nonsm_row = _nonstarmine_row("MU")  # same symbol, no ESS text

    # Both in extra_rows (as if from two simultaneous providers)
    merged = _build_merged_snapshot(
        snapshot_date="2026-06-15",
        history_root=tmp_path,
        extra_rows=[nonsm_row, sm_row],  # Non-StarMine listed first
    )

    by_sym = {r["symbol"]: r for r in merged}
    assert by_sym["MU"]["coverage_domain"] == "STARMINE_COVERED"
    assert by_sym["MU"]["starmine_ess_text"] == "VERY_BULLISH"


# ---------------------------------------------------------------------------
# T09: append_signal_snapshots writes merged snapshot (integration)
# ---------------------------------------------------------------------------

def test_T09_append_signal_snapshots_writes_merged(tmp_path):
    """append_signal_snapshots produces a merged signal_snapshot.csv."""
    from src.history.signal_snapshot_manager import SNAPSHOT_HEADERS, _write_csv_rows

    current_root = tmp_path / "current"
    history_root = tmp_path / "signals"
    index_path = tmp_path / "signal_index.csv"

    # Pre-populate a StarMine partition
    sm_rows = [_starmine_row("MU", "VERY_BULLISH"), _starmine_row("VRT", "BULLISH")]
    sm_date_dir = history_root / "snapshot_date=2026-06-15" / "run_id=intake-sm"
    sm_date_dir.mkdir(parents=True)
    _write_csv_rows(sm_date_dir / "signal_snapshots.csv", SNAPSHOT_HEADERS, sm_rows)
    _write_csv_rows(sm_date_dir / "signal_lineage_registry.csv", [], [])

    # Append non-StarMine via append_signal_snapshots
    nonsm_records = [
        {**_nonstarmine_row("AAON"), "snapshot_date": "2026-06-15",
         "starmine_ess_numeric_estimated": False},
    ]
    count = append_signal_snapshots(
        normalized_records=nonsm_records,
        run_id="intake-nonsm",
        current_root=str(current_root),
        history_root=str(history_root),
        index_path=str(index_path),
    )

    assert count == 1

    snap_path = current_root / "signal_snapshot.csv"
    assert snap_path.exists()

    syms = _read_snapshot_syms(snap_path)

    # StarMine symbols from pre-existing partition preserved
    assert "MU" in syms, "MU must be in merged snapshot"
    assert syms["MU"]["coverage_domain"] == "STARMINE_COVERED"
    assert syms["MU"]["starmine_ess_text"] == "VERY_BULLISH"
    assert "VRT" in syms

    # Non-StarMine symbol from current run also present
    assert "AAON" in syms
