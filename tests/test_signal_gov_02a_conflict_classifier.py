"""Regression tests for SIGNAL-GOV-02A — Signal Conflict Classifier.

Covers:
  1. CONFLICTING_SIGNAL classification
  2. HIGH_ANALYST_DISAGREEMENT classification
  3. HOLD_CONSENSUS classification
  4. SIGNIFICANT_CONFLICT classification
  5. HIGH_HOLD_RATIO classification
  6. Threshold boundary behavior (exactly at threshold)
  7. Empty analyst set (no FMP data)
  8. API payload serialization (to_dict keys)
  9. No badges for clean signal
 10. Operator annotation triggers HIGH_ANALYST_DISAGREEMENT
 11. Cascading: SIGNIFICANT_CONFLICT suppresses lower-severity duplicates
 12. get_conflicts_for_symbols integration (with tmp signal files)
"""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest

from src.portfolio.signal_conflict_classifier import (
    SignalConflict,
    SignalInputs,
    classify_signal_conflicts,
    get_conflicts_for_symbols,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _inputs(
    symbol="TEST",
    buy=10, hold=2, sell=0, total=12,
    consensus="BUY",
    zacks=4.0, danelfin=7.0, yahoo=2.0,
    operator_ann=False,
) -> SignalInputs:
    return SignalInputs(
        symbol=symbol,
        buy_count=buy, hold_count=hold, sell_count=sell,
        total_analysts=total,
        consensus_label=consensus,
        zacks_score=zacks, danelfin_raw=danelfin, yahoo_abr=yahoo,
        operator_annotated_disagreement=operator_ann,
    )


# ---------------------------------------------------------------------------
# Test 1: CONFLICTING_SIGNAL — bullish + bearish sources coexist
# ---------------------------------------------------------------------------

def test_conflicting_signal_from_fmp_sell_votes():
    """1 sell vote + majority buys → CONFLICTING_SIGNAL badge."""
    inp = _inputs(buy=10, hold=2, sell=1, total=13, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "CONFLICTING_SIGNAL" in types


def test_conflicting_signal_bearish_zacks_bullish_danelfin():
    """Bearish Zacks + bullish Danelfin → CONFLICTING_SIGNAL."""
    inp = _inputs(buy=0, hold=2, sell=0, total=2, consensus="HOLD",
                  zacks=2.0, danelfin=8.0, yahoo=None)
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    # HOLD_CONSENSUS should appear, plus CONFLICTING_SIGNAL from zacks/dan disagreement
    assert "CONFLICTING_SIGNAL" in types


def test_no_conflicting_signal_all_bullish():
    """All signals bullish → no CONFLICTING_SIGNAL."""
    inp = _inputs(buy=15, hold=1, sell=0, total=16, consensus="BUY",
                  zacks=4.0, danelfin=7.0, yahoo=1.8)
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "CONFLICTING_SIGNAL" not in types


# ---------------------------------------------------------------------------
# Test 2: HIGH_ANALYST_DISAGREEMENT
# ---------------------------------------------------------------------------

def test_high_analyst_disagreement_operator_annotation():
    """Operator annotation → HIGH_ANALYST_DISAGREEMENT regardless of counts."""
    inp = _inputs(buy=5, hold=2, sell=0, total=7, operator_ann=True)
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HIGH_ANALYST_DISAGREEMENT" in types


def test_high_analyst_disagreement_auto_detect():
    """Auto-detect: sell_ratio >= 10%, buys present, sell present, total >= 5."""
    # 2 sells out of 18 = 11.1% — above 10% auto threshold
    inp = _inputs(buy=14, hold=2, sell=2, total=18, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HIGH_ANALYST_DISAGREEMENT" in types


def test_high_analyst_disagreement_not_when_significant():
    """HIGH_ANALYST_DISAGREEMENT not emitted when SIGNIFICANT_CONFLICT already present."""
    # 4 sells out of 20 = 20% >= 15% threshold → SIGNIFICANT_CONFLICT should fire
    inp = _inputs(buy=14, hold=2, sell=4, total=20, consensus="BUY", operator_ann=True)
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "SIGNIFICANT_CONFLICT" in types
    assert "HIGH_ANALYST_DISAGREEMENT" not in types


# ---------------------------------------------------------------------------
# Test 3: HOLD_CONSENSUS
# ---------------------------------------------------------------------------

def test_hold_consensus_from_consensus_label():
    """FMP consensus_label == HOLD → HOLD_CONSENSUS badge."""
    inp = _inputs(buy=1, hold=4, sell=0, total=5, consensus="HOLD")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HOLD_CONSENSUS" in types


def test_hold_consensus_severity_info():
    """HOLD_CONSENSUS has INFO severity."""
    inp = _inputs(buy=1, hold=4, sell=0, total=5, consensus="HOLD")
    badges = classify_signal_conflicts(inp)
    hc = next(b for b in badges if b.type == "HOLD_CONSENSUS")
    assert hc.severity == "INFO"


def test_no_hold_consensus_when_buy_label():
    """BUY consensus label → no HOLD_CONSENSUS."""
    inp = _inputs(buy=14, hold=1, sell=0, total=15, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HOLD_CONSENSUS" not in types


# ---------------------------------------------------------------------------
# Test 4: SIGNIFICANT_CONFLICT
# ---------------------------------------------------------------------------

def test_significant_conflict_above_threshold():
    """15+ % sell rate → SIGNIFICANT_CONFLICT (WARN)."""
    inp = _inputs(buy=14, hold=2, sell=3, total=19, consensus="BUY")
    # sell ratio = 3/19 = 15.8% >= 15%
    badges = classify_signal_conflicts(inp, significant_sell_ratio_pct=15.0)
    types = [b.type for b in badges]
    assert "SIGNIFICANT_CONFLICT" in types
    sc = next(b for b in badges if b.type == "SIGNIFICANT_CONFLICT")
    assert sc.severity == "WARN"


def test_significant_conflict_severity_warn():
    """SIGNIFICANT_CONFLICT always WARN."""
    inp = _inputs(buy=10, hold=2, sell=5, total=17, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    sc = next((b for b in badges if b.type == "SIGNIFICANT_CONFLICT"), None)
    assert sc is not None
    assert sc.severity == "WARN"


# ---------------------------------------------------------------------------
# Test 5: HIGH_HOLD_RATIO
# ---------------------------------------------------------------------------

def test_high_hold_ratio_majority_holds():
    """Majority hold AND BUY consensus → HIGH_HOLD_RATIO."""
    # 10/18 = 55.6% holds, consensus is BUY (so not HOLD_CONSENSUS)
    inp = _inputs(buy=7, hold=10, sell=1, total=18, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HIGH_HOLD_RATIO" in types
    hr = next(b for b in badges if b.type == "HIGH_HOLD_RATIO")
    assert hr.severity == "INFO"


def test_no_high_hold_ratio_when_hold_consensus():
    """HOLD_CONSENSUS takes priority over HIGH_HOLD_RATIO."""
    inp = _inputs(buy=1, hold=10, sell=0, total=11, consensus="HOLD")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HOLD_CONSENSUS" in types
    assert "HIGH_HOLD_RATIO" not in types


# ---------------------------------------------------------------------------
# Test 6: Threshold boundary behavior
# ---------------------------------------------------------------------------

def test_significant_conflict_exactly_at_threshold():
    """Exactly at 15% threshold → SIGNIFICANT_CONFLICT fires (>= comparison)."""
    # 3 sells out of 20 = exactly 15%
    inp = _inputs(buy=15, hold=2, sell=3, total=20, consensus="BUY")
    badges = classify_signal_conflicts(inp, significant_sell_ratio_pct=15.0)
    types = [b.type for b in badges]
    assert "SIGNIFICANT_CONFLICT" in types


def test_significant_conflict_below_threshold():
    """Just below 15% → no SIGNIFICANT_CONFLICT."""
    # 2 sells out of 14 = 14.3%
    inp = _inputs(buy=11, hold=1, sell=2, total=14, consensus="BUY")
    badges = classify_signal_conflicts(inp, significant_sell_ratio_pct=15.0)
    types = [b.type for b in badges]
    assert "SIGNIFICANT_CONFLICT" not in types


def test_high_hold_ratio_exactly_at_threshold():
    """Exactly at 50% hold ratio → HIGH_HOLD_RATIO fires."""
    # 5 holds out of 10 = exactly 50%
    inp = _inputs(buy=4, hold=5, sell=1, total=10, consensus="BUY")
    badges = classify_signal_conflicts(inp, high_hold_ratio_pct=50.0)
    types = [b.type for b in badges]
    assert "HIGH_HOLD_RATIO" in types


# ---------------------------------------------------------------------------
# Test 7: Empty analyst set
# ---------------------------------------------------------------------------

def test_empty_analyst_set_no_crash():
    """No FMP data → no crashes, empty badge list."""
    inp = SignalInputs(
        symbol="EMPTY",
        buy_count=0, hold_count=0, sell_count=0, total_analysts=0,
        consensus_label="",
        zacks_score=None, danelfin_raw=None, yahoo_abr=None,
    )
    badges = classify_signal_conflicts(inp)
    assert isinstance(badges, list)
    assert len(badges) == 0


def test_empty_fmp_with_bullish_other_sources():
    """No FMP data but bullish Zacks + Danelfin → no conflict badges."""
    inp = SignalInputs(
        symbol="CLEAN",
        buy_count=0, hold_count=0, sell_count=0, total_analysts=0,
        consensus_label="",
        zacks_score=4.0, danelfin_raw=7.0, yahoo_abr=2.0,
    )
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    # No bearish sources → no CONFLICTING_SIGNAL; no hold consensus/ratio
    assert "CONFLICTING_SIGNAL" not in types


# ---------------------------------------------------------------------------
# Test 8: API payload serialization
# ---------------------------------------------------------------------------

def test_signal_conflict_to_dict_keys():
    """SignalConflict.to_dict() has required keys."""
    sc = SignalConflict(
        type="CONFLICTING_SIGNAL",
        severity="WARN",
        description="Test description.",
    )
    d = sc.to_dict()
    assert set(d.keys()) == {"type", "severity", "description"}
    assert d["type"] == "CONFLICTING_SIGNAL"
    assert d["severity"] == "WARN"


def test_serialization_json_roundtrip():
    """Badge dict survives JSON serialization."""
    inp = _inputs(buy=10, hold=2, sell=2, total=14, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    serialized = json.dumps([b.to_dict() for b in badges])
    parsed = json.loads(serialized)
    assert isinstance(parsed, list)
    for item in parsed:
        assert "type" in item and "severity" in item and "description" in item


# ---------------------------------------------------------------------------
# Test 9: No badges for clean signal
# ---------------------------------------------------------------------------

def test_no_badges_for_clean_signal():
    """All-bullish symbol with no conflict sources produces zero badges."""
    inp = _inputs(buy=18, hold=1, sell=0, total=19, consensus="BUY",
                  zacks=5.0, danelfin=9.0, yahoo=1.5, operator_ann=False)
    badges = classify_signal_conflicts(inp)
    assert badges == []


# ---------------------------------------------------------------------------
# Test 10: Operator annotation
# ---------------------------------------------------------------------------

def test_operator_annotation_triggers_disagreement_even_with_no_sells():
    """Operator annotation overrides auto-detect — fires even with 0 sell votes."""
    inp = _inputs(buy=12, hold=2, sell=0, total=14, consensus="BUY",
                  operator_ann=True)
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "HIGH_ANALYST_DISAGREEMENT" in types


# ---------------------------------------------------------------------------
# Test 11: Cascading / deduplication
# ---------------------------------------------------------------------------

def test_significant_conflict_suppresses_conflicting_signal():
    """When SIGNIFICANT_CONFLICT fires, CONFLICTING_SIGNAL is not also emitted."""
    # 4 sells of 20 = 20% >= 15%
    inp = _inputs(buy=14, hold=2, sell=4, total=20, consensus="BUY")
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "SIGNIFICANT_CONFLICT" in types
    # CONFLICTING_SIGNAL should not double-badge since SIGNIFICANT covers it
    assert "CONFLICTING_SIGNAL" not in types


def test_significant_conflict_suppresses_high_analyst_disagreement():
    """SIGNIFICANT_CONFLICT fires; HIGH_ANALYST_DISAGREEMENT is not added."""
    inp = _inputs(buy=10, hold=2, sell=4, total=16, consensus="BUY", operator_ann=True)
    badges = classify_signal_conflicts(inp)
    types = [b.type for b in badges]
    assert "SIGNIFICANT_CONFLICT" in types
    assert "HIGH_ANALYST_DISAGREEMENT" not in types


# ---------------------------------------------------------------------------
# Test 12: get_conflicts_for_symbols integration
# ---------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def test_get_conflicts_for_symbols_integration(tmp_path):
    """End-to-end: writes fake signal CSVs and validates badge output."""
    fmp_rows = [
        {"symbol": "NUE",  "sourced_date": "2026-06-15",
         "strong_buy_count": 0, "buy_count": 18, "hold_count": 11,
         "sell_count": 3, "strong_sell_count": 0,
         "total_analysts": 32, "net_buy_score": 15, "consensus_label": "BUY"},
        {"symbol": "MTZ",  "sourced_date": "2026-06-15",
         "strong_buy_count": 0, "buy_count": 32, "hold_count": 4,
         "sell_count": 0, "strong_sell_count": 0,
         "total_analysts": 36, "net_buy_score": 32, "consensus_label": "BUY"},
        {"symbol": "PCB",  "sourced_date": "2026-06-12",
         "strong_buy_count": 0, "buy_count": 1, "hold_count": 4,
         "sell_count": 0, "strong_sell_count": 0,
         "total_analysts": 5, "net_buy_score": 1, "consensus_label": "HOLD"},
    ]
    zacks_rows = [
        {"symbol": "NUE",  "zacks_rank": 1.0, "zacks_score": 5.0, "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-15"},
        {"symbol": "MTZ",  "zacks_rank": 3.0, "zacks_score": 3.0, "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-15"},
        {"symbol": "PCB",  "zacks_rank": 3.0, "zacks_score": 3.0, "abr": "", "price_target": "", "eps_growth": "", "sourced_date": "2026-06-12"},
    ]
    dan_rows = [
        {"symbol": "NUE",  "danelfin_raw": 7, "danelfin_score": 3.5, "sourced_date": "2026-06-15"},
        {"symbol": "MTZ",  "danelfin_raw": 9, "danelfin_score": 4.5, "sourced_date": "2026-06-15"},
        {"symbol": "PCB",  "danelfin_raw": 7, "danelfin_score": 3.5, "sourced_date": "2026-06-12"},
    ]

    _write_csv(tmp_path / "data/signals/fmp/latest/latest_fmp_grades_consensus.csv", fmp_rows)
    _write_csv(tmp_path / "data/signals/zacks/latest_zacks.csv", zacks_rows)
    _write_csv(tmp_path / "data/signals/danelfin/latest_danelfin.csv", dan_rows)
    # No yahoo file — should not crash

    result = get_conflicts_for_symbols(["NUE", "MTZ", "PCB"], repo_root=tmp_path)

    assert "NUE" in result
    assert "MTZ" in result
    assert "PCB" in result

    # NUE: 3/32 sells = 9.4% < 15% threshold; auto-disagreement also needs >= 10% so no auto-detect
    # but has 3 sells and 18 buys so CONFLICTING_SIGNAL applies
    nue_types = [c["type"] for c in result["NUE"]]
    assert "CONFLICTING_SIGNAL" in nue_types

    # MTZ: 0 sells, BUY consensus → no conflict badges
    assert result["MTZ"] == []

    # PCB: HOLD consensus → HOLD_CONSENSUS badge
    pcb_types = [c["type"] for c in result["PCB"]]
    assert "HOLD_CONSENSUS" in pcb_types


def test_get_conflicts_empty_symbol_list_returns_empty(tmp_path):
    """Empty symbol list → empty result dict."""
    (tmp_path / "data/signals/fmp/latest").mkdir(parents=True)
    result = get_conflicts_for_symbols([], repo_root=tmp_path)
    assert result == {}


def test_get_conflicts_missing_signal_files_no_crash(tmp_path):
    """Missing signal CSV files → graceful empty result, no crash."""
    result = get_conflicts_for_symbols(["VRT", "TSLA"], repo_root=tmp_path)
    assert "VRT" in result
    assert "TSLA" in result
    assert result["VRT"] == []
    assert result["TSLA"] == []
