"""Tests for ISSUE-12B (detection persistence) and ISSUE-12C (outcome engine).

Tests use injectable price-fetch functions and temp directories to avoid
live network calls and file system side effects.
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.portfolio.outcome_tracker import (
    DETECTIONS_HEADERS,
    OUTCOMES_HEADERS,
    _outcome_status,
    _safe_median,
    _safe_mean,
    _nearest_price,
    persist_dislocation_detections,
    compute_outcomes,
    build_outcome_summary,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _tmp_dir():
    return Path(tempfile.mkdtemp())


def _write_detection(path: Path, rows: list[dict]) -> None:
    """Write detection rows to a temp CSV."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=DETECTIONS_HEADERS, restval="")
        writer.writeheader()
        writer.writerows(rows)


def _det(detection_date="2026-01-01", symbol="DELL", tier="MODERATE",
         dislocation_class="A1_FUNDAMENTAL_BEAT_DIVERGENCE",
         active_classes="A1_FUNDAMENTAL_BEAT_DIVERGENCE",
         price_at_detection="100.00",
         run_id="PAR-TEST-0001") -> dict:
    return {
        "detection_date": detection_date,
        "run_id": run_id,
        "symbol": symbol,
        "tier": tier,
        "dislocation_class": dislocation_class,
        "active_classes": active_classes,
        "ess_at_detection": "BEARISH",
        "danelfin_at_detection": "2.5",
        "replay_percentile_at_detection": "70.0",
        "replay_supported_at_detection": "True",
        "composite_score_at_detection": "3.8",
        "cw_das_score_at_detection": "72.5",
        "thesis_integrity_at_detection": "INTACT",
        "fundamental_modifier_at_detection": "2.0",
        "dislocation_version": "1.1",
        "price_at_detection": price_at_detection,
    }


def _make_price_fetcher(price_map: dict[str, dict[str, float]]):
    """Return a fake price-fetch function backed by price_map."""
    def _fetch(symbol: str, start: str, end: str) -> dict[str, float]:
        return price_map.get(symbol, {})
    return _fetch


# ── _outcome_status ────────────────────────────────────────────────────────────

def test_outcome_status_win():
    assert _outcome_status(5.0) == "WIN"

def test_outcome_status_loss():
    assert _outcome_status(-3.0) == "LOSS"

def test_outcome_status_flat_positive():
    assert _outcome_status(0.1) == "FLAT"

def test_outcome_status_flat_negative():
    assert _outcome_status(-0.1) == "FLAT"

def test_outcome_status_boundary_win():
    assert _outcome_status(0.26) == "WIN"

def test_outcome_status_boundary_loss():
    assert _outcome_status(-0.26) == "LOSS"


# ── _nearest_price ─────────────────────────────────────────────────────────────

def test_nearest_price_exact_match():
    prices = {"2026-01-15": 105.0, "2026-01-14": 104.0}
    assert _nearest_price(prices, "2026-01-15") == 105.0

def test_nearest_price_fallback_prior_day():
    prices = {"2026-01-14": 104.0}  # no entry for 2026-01-15
    result = _nearest_price(prices, "2026-01-15")
    assert result == 104.0  # falls back one day

def test_nearest_price_empty_returns_none():
    assert _nearest_price({}, "2026-01-15") is None

def test_nearest_price_too_far_back_returns_none():
    prices = {"2026-01-08": 100.0}  # 7 days before target
    assert _nearest_price(prices, "2026-01-15") is None


# ── Exclusion: immature detections ────────────────────────────────────────────

def test_immature_detections_excluded_30d():
    """Detections within holding_period_days of today must be excluded."""
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    recent = str(today - timedelta(days=20))  # only 20 days old → too young for 30d

    _write_detection(det_path, [_det(detection_date=recent)])
    results = compute_outcomes(30, det_path, out_path, today=str(today), _fetch_fn=lambda s,a,b: {})
    assert results == []


def test_immature_detections_excluded_90d():
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    recent = str(today - timedelta(days=60))  # 60 days old → too young for 90d

    _write_detection(det_path, [_det(detection_date=recent)])
    results = compute_outcomes(90, det_path, out_path, today=str(today), _fetch_fn=lambda s,a,b: {})
    assert results == []


def test_mature_detection_included_90d():
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))   # 95 days old → mature for 90d
    outcome_date = str(date.fromisoformat(det_date) + timedelta(days=90))

    price_map = {
        "DELL": {det_date: 100.0, outcome_date: 110.0},
        "SPY":  {det_date: 500.0, outcome_date: 505.0},
    }
    _write_detection(det_path, [_det(detection_date=det_date, price_at_detection="100.00")])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))
    assert len(results) == 1


# ── Math validation ────────────────────────────────────────────────────────────

def test_excess_return_math():
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))
    outcome_date = str(date.fromisoformat(det_date) + timedelta(days=90))

    # DELL: +10%, SPY: +5% → excess = +5%
    price_map = {
        "DELL": {det_date: 100.0, outcome_date: 110.0},
        "SPY":  {det_date: 500.0, outcome_date: 525.0},
    }
    _write_detection(det_path, [_det(detection_date=det_date, price_at_detection="100.00")])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))

    assert len(results) == 1
    row = results[0]
    sym_ret = float(row["symbol_return_pct"])
    spy_ret = float(row["spy_return_pct"])
    excess  = float(row["excess_return_pct"])

    assert abs(sym_ret - 10.0) < 0.01
    assert abs(spy_ret - 5.0) < 0.01
    assert abs(excess - 5.0) < 0.01
    assert row["outcome_status"] == "WIN"


def test_negative_excess_return_is_loss():
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))
    outcome_date = str(date.fromisoformat(det_date) + timedelta(days=90))

    # DELL: -5%, SPY: +5% → excess = -10% → LOSS
    price_map = {
        "DELL": {det_date: 100.0, outcome_date: 95.0},
        "SPY":  {det_date: 500.0, outcome_date: 525.0},
    }
    _write_detection(det_path, [_det(detection_date=det_date, price_at_detection="100.00")])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))
    assert results[0]["outcome_status"] == "LOSS"


# ── Missing price handling ─────────────────────────────────────────────────────

def test_missing_spy_price_excludes_row():
    """If SPY prices are unavailable, row should be skipped."""
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))

    # Only DELL prices, no SPY
    price_map = {"DELL": {det_date: 100.0}}
    _write_detection(det_path, [_det(detection_date=det_date, price_at_detection="100.00")])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))
    assert results == []


def test_missing_symbol_price_excludes_row():
    """If symbol outcome price is unavailable, row should be skipped."""
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))
    outcome_date = str(date.fromisoformat(det_date) + timedelta(days=90))

    price_map = {
        "SPY": {det_date: 500.0, outcome_date: 510.0},
        # No DELL prices
    }
    _write_detection(det_path, [_det(detection_date=det_date, price_at_detection="100.00")])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))
    assert results == []


def test_no_price_at_detection_excludes_row():
    """Detection row without price_at_detection must be excluded."""
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))
    outcome_date = str(date.fromisoformat(det_date) + timedelta(days=90))

    price_map = {
        "DELL": {det_date: 100.0, outcome_date: 110.0},
        "SPY":  {det_date: 500.0, outcome_date: 510.0},
    }
    _write_detection(det_path, [_det(detection_date=det_date, price_at_detection="")])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))
    assert results == []


# ── Multi-class preservation ───────────────────────────────────────────────────

def test_multi_class_preserved_in_output():
    d = _tmp_dir()
    det_path = d / "detections.csv"
    out_path = d / "outcomes.csv"

    today = date.today()
    det_date = str(today - timedelta(days=95))
    outcome_date = str(date.fromisoformat(det_date) + timedelta(days=90))

    active = "A1_FUNDAMENTAL_BEAT_DIVERGENCE|D1_REPLAY_SIGNAL_LAG|B2_ANALYST_AI_DIVERGENCE"
    price_map = {
        "DELL": {det_date: 100.0, outcome_date: 110.0},
        "SPY":  {det_date: 500.0, outcome_date: 505.0},
    }
    row = _det(detection_date=det_date, active_classes=active,
               dislocation_class="MULTI_CLASS", price_at_detection="100.00")
    _write_detection(det_path, [row])
    results = compute_outcomes(90, det_path, out_path, today=str(today),
                               _fetch_fn=_make_price_fetcher(price_map))
    assert len(results) == 1
    assert results[0]["active_classes"] == active


# ── Empty cohort ───────────────────────────────────────────────────────────────

def test_empty_detections_file_returns_empty():
    d = _tmp_dir()
    det_path = d / "no_file.csv"
    out_path = d / "outcomes.csv"
    results = compute_outcomes(90, det_path, out_path, today=str(date.today()),
                               _fetch_fn=lambda s,a,b: {})
    assert results == []


# ── Summary generation ─────────────────────────────────────────────────────────

def test_summary_by_tier_correct():
    d = _tmp_dir()
    out_path = d / "outcomes.csv"
    summary_path = d / "summary.json"

    # Write 3 outcome rows directly: 2 WIN, 1 LOSS for MODERATE
    rows = [
        {"detection_date":"2026-01-01","symbol":"DELL","tier":"MODERATE",
         "active_classes":"A1","holding_period_days":"90",
         "price_at_detection":"100","price_at_outcome":"110",
         "spy_price_at_detection":"500","spy_price_at_outcome":"505",
         "symbol_return_pct":"10.0","spy_return_pct":"1.0","excess_return_pct":"9.0","outcome_status":"WIN"},
        {"detection_date":"2026-01-01","symbol":"VRT","tier":"MODERATE",
         "active_classes":"A1","holding_period_days":"90",
         "price_at_detection":"50","price_at_outcome":"55",
         "spy_price_at_detection":"500","spy_price_at_outcome":"505",
         "symbol_return_pct":"10.0","spy_return_pct":"1.0","excess_return_pct":"9.0","outcome_status":"WIN"},
        {"detection_date":"2026-01-01","symbol":"PSX","tier":"MODERATE",
         "active_classes":"A1","holding_period_days":"90",
         "price_at_detection":"80","price_at_outcome":"75",
         "spy_price_at_detection":"500","spy_price_at_outcome":"505",
         "symbol_return_pct":"-6.25","spy_return_pct":"1.0","excess_return_pct":"-7.25","outcome_status":"LOSS"},
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUTCOMES_HEADERS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    summary = build_outcome_summary(out_path, 90, summary_path)
    mod = summary["by_tier"]["MODERATE"]
    assert mod["detection_count"] == 3
    assert abs(mod["hit_rate"] - 66.67) < 0.1


def test_summary_json_written():
    d = _tmp_dir()
    out_path = d / "outcomes.csv"
    summary_path = d / "summary.json"

    rows = [
        {"detection_date":"2026-01-01","symbol":"DELL","tier":"HIGH_CONVICTION",
         "active_classes":"A1|D1","holding_period_days":"90",
         "price_at_detection":"100","price_at_outcome":"115",
         "spy_price_at_detection":"500","spy_price_at_outcome":"502",
         "symbol_return_pct":"15.0","spy_return_pct":"0.4","excess_return_pct":"14.6","outcome_status":"WIN"},
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=OUTCOMES_HEADERS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    build_outcome_summary(out_path, 90, summary_path)
    assert summary_path.exists()
    data = json.loads(summary_path.read_text())
    assert "by_tier" in data
    assert "by_class" in data
    assert data["holding_period_days"] == 90


# ── Detection persistence ──────────────────────────────────────────────────────

def test_persist_detections_writes_csv(tmp_path):
    det_path = tmp_path / "detections.csv"
    payload = {
        "DELL": {"tier": "MODERATE", "dislocation_class": "A1_FUNDAMENTAL_BEAT_DIVERGENCE",
                 "active_classes": ["A1_FUNDAMENTAL_BEAT_DIVERGENCE"], "evidence": [], "version": "1.1"},
        "PSX":  {"tier": "NONE", "dislocation_class": "NONE", "active_classes": [], "evidence": [], "version": "1.1"},
    }
    overlays = [{"symbol": "DELL", "ess_score_text": "BEARISH", "danelfin_score": "2.0",
                 "replay_percentile": "70", "replay_supported": "True", "composite_score": "3.8"}]

    # Monkeypatch the constant path
    import src.portfolio.outcome_tracker as ot
    original = ot.DETECTIONS_CSV
    ot.DETECTIONS_CSV = det_path
    ot._DERIVED_DIR = tmp_path
    try:
        count = persist_dislocation_detections("2026-06-05", "PAR-TEST-001",
                                               payload, overlays)
    finally:
        ot.DETECTIONS_CSV = original
        ot._DERIVED_DIR = original.parent

    assert count == 1  # only DELL (PSX is NONE)
    rows = list(csv.DictReader(open(det_path)))
    assert len(rows) == 1
    assert rows[0]["symbol"] == "DELL"
    assert rows[0]["tier"] == "MODERATE"


def test_persist_detections_deduplication(tmp_path):
    det_path = tmp_path / "detections.csv"
    payload = {
        "DELL": {"tier": "MODERATE", "dislocation_class": "A1", "active_classes": ["A1"], "evidence": [], "version": "1.1"},
    }
    overlays = [{"symbol": "DELL", "ess_score_text": "BEARISH", "danelfin_score": "2.0",
                 "replay_percentile": "70", "replay_supported": "True", "composite_score": "3.8"}]

    import src.portfolio.outcome_tracker as ot
    original_path = ot.DETECTIONS_CSV
    original_dir = ot._DERIVED_DIR
    ot.DETECTIONS_CSV = det_path
    ot._DERIVED_DIR = tmp_path
    try:
        count1 = persist_dislocation_detections("2026-06-05", "PAR-001", payload, overlays)
        count2 = persist_dislocation_detections("2026-06-05", "PAR-002", payload, overlays)
    finally:
        ot.DETECTIONS_CSV = original_path
        ot._DERIVED_DIR = original_dir

    assert count1 == 1
    assert count2 == 0  # duplicate, not re-appended


def test_persist_none_tier_not_recorded(tmp_path):
    det_path = tmp_path / "detections.csv"
    payload = {
        "NVDA": {"tier": "NONE", "dislocation_class": "NONE", "active_classes": [], "evidence": [], "version": "1.1"},
    }

    import src.portfolio.outcome_tracker as ot
    original_path = ot.DETECTIONS_CSV
    original_dir = ot._DERIVED_DIR
    ot.DETECTIONS_CSV = det_path
    ot._DERIVED_DIR = tmp_path
    try:
        count = persist_dislocation_detections("2026-06-05", "PAR-001", payload, [])
    finally:
        ot.DETECTIONS_CSV = original_path
        ot._DERIVED_DIR = original_dir

    assert count == 0
    assert not det_path.exists()


# ── _safe_median / _safe_mean ─────────────────────────────────────────────────

def test_safe_median_odd():
    assert _safe_median([1.0, 3.0, 5.0]) == 3.0

def test_safe_median_even():
    assert _safe_median([1.0, 3.0]) == 2.0

def test_safe_median_empty_returns_none():
    assert _safe_median([]) is None

def test_safe_mean_basic():
    assert abs(_safe_mean([1.0, 2.0, 3.0]) - 2.0) < 0.001

def test_safe_mean_empty_returns_none():
    assert _safe_mean([]) is None
