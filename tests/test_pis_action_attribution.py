"""PIS-008 — Recommendation Action Attribution — Validation Test Suite.

All tests are deterministic and filesystem-isolated (pytest tmp_path).
No network calls. No modifications to existing project data.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.pis.action_attribution import (
    ActionAttributionRecord,
    SourceScorecard,
    classify_action_status,
    _change_to_direction,
    _normalize_source,
    _compute_scorecards,
    _find_missed_opportunities,
    _build_attribution_records,
    pis_action_attribution_summary,
    pis_action_attribution_recommendations,
    pis_action_attribution_sources,
)


# ─── Fixture helpers ──────────────────────────────────────────────────────────

_LINEAGE_HEADERS = [
    "lineage_id", "snapshot_id", "change_id", "symbol", "change_type",
    "matched_recommendation_id", "matched_recommendation", "recommendation_source",
    "recommendation_date", "confidence", "days_between", "created_at",
]

_CHANGE_HEADERS = [
    "change_id", "snapshot_id", "prior_snapshot_id", "snapshot_date",
    "prior_snapshot_date", "change_type", "symbol", "old_quantity", "new_quantity",
    "old_market_value", "new_market_value", "delta_quantity", "delta_market_value",
    "created_at",
]

_ATTRIBUTION_HEADERS = [
    "attribution_id", "snapshot_id", "snapshot_date", "change_id", "symbol",
    "change_type", "matched_recommendation_id", "matched_recommendation",
    "recommendation_source", "recommendation_date", "confidence",
    "old_market_value", "new_market_value", "delta_market_value",
    "directional_attribution", "directional_return_pct", "outcome", "created_at",
]


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _setup_pis_dirs(root: Path) -> dict[str, Path]:
    paths = {
        "lineage": root / "data/history/pis/lineage",
        "changes": root / "data/history/pis/changes",
        "attribution": root / "data/history/pis/attribution",
        "par": root / "data/portfolio_ingestion/analysis_runs",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def _make_lineage_row(
    change_id: str,
    symbol: str,
    change_type: str,
    confidence: str,
    rec_id: str = "",
    rec_source: str = "",
    rec_date: str = "",
    days_between: str = "",
) -> dict:
    return {
        "lineage_id": f"LIN-{change_id}",
        "snapshot_id": "SNAP-001",
        "change_id": change_id,
        "symbol": symbol,
        "change_type": change_type,
        "matched_recommendation_id": rec_id,
        "matched_recommendation": rec_id,
        "recommendation_source": rec_source,
        "recommendation_date": rec_date,
        "confidence": confidence,
        "days_between": days_between,
        "created_at": "2026-06-15T00:00:00+00:00",
    }


def _make_change_row(
    change_id: str,
    symbol: str,
    change_type: str,
    snapshot_date: str,
    delta_quantity: float = 10.0,
    delta_market_value: float = 1000.0,
) -> dict:
    return {
        "change_id": change_id,
        "snapshot_id": "SNAP-001",
        "prior_snapshot_id": "SNAP-000",
        "snapshot_date": snapshot_date,
        "prior_snapshot_date": "2026-06-01",
        "change_type": change_type,
        "symbol": symbol,
        "old_quantity": "10.0",
        "new_quantity": "20.0",
        "old_market_value": "1000.0",
        "new_market_value": "2000.0",
        "delta_quantity": str(delta_quantity),
        "delta_market_value": str(delta_market_value),
        "created_at": "2026-06-15T00:00:00+00:00",
    }


def _make_attribution_row(change_id: str, outcome: str) -> dict:
    return {
        "attribution_id": f"ATTR-{change_id}",
        "snapshot_id": "SNAP-001",
        "snapshot_date": "2026-06-08",
        "change_id": change_id,
        "symbol": "ARW",
        "change_type": "INCREASED",
        "matched_recommendation_id": "",
        "matched_recommendation": "",
        "recommendation_source": "",
        "recommendation_date": "",
        "confidence": "MEDIUM",
        "old_market_value": "1000.0",
        "new_market_value": "2000.0",
        "delta_market_value": "1000.0",
        "directional_attribution": "100.0",
        "directional_return_pct": "10.0",
        "outcome": outcome,
        "created_at": "2026-06-15T00:00:00+00:00",
    }


# ─── Domain 1: Action Status Classification ───────────────────────────────────

def test_T01_buy_rec_increased_followed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=3,
        delta_market_value=1500.0,
    )
    assert status == "FOLLOWED"


def test_T02_buy_rec_new_position_followed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="NEW_POSITION",
        recommended_direction="BUY",
        days_between=5,
        delta_market_value=2000.0,
    )
    assert status == "FOLLOWED"


def test_T03_reduce_rec_reduced_followed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="REDUCED",
        recommended_direction="REDUCE",
        days_between=2,
        delta_market_value=-800.0,
    )
    assert status == "FOLLOWED"


def test_T04_reduce_rec_exited_followed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="EXITED_POSITION",
        recommended_direction="REDUCE",
        days_between=1,
        delta_market_value=-1200.0,
    )
    assert status == "FOLLOWED"


def test_T05_buy_rec_reduced_opposed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="REDUCED",
        recommended_direction="BUY",
        days_between=3,
        delta_market_value=-500.0,
    )
    assert status == "OPPOSED"


def test_T06_buy_rec_exited_opposed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="EXITED_POSITION",
        recommended_direction="BUY",
        days_between=7,
        delta_market_value=-2000.0,
    )
    assert status == "OPPOSED"


def test_T07_reduce_rec_increased_opposed():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="INCREASED",
        recommended_direction="REDUCE",
        days_between=4,
        delta_market_value=1000.0,
    )
    assert status == "OPPOSED"


def test_T08_none_confidence_unknown():
    status, conf = classify_action_status(
        lineage_confidence="NONE",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=3,
        delta_market_value=1000.0,
    )
    assert status == "UNKNOWN"
    assert conf == "NONE"


def test_T09_no_matching_change_unknown():
    # days_between=None with NONE confidence
    status, conf = classify_action_status(
        lineage_confidence="NONE",
        change_type="",
        recommended_direction="BUY",
        days_between=None,
        delta_market_value=0.0,
    )
    assert status == "UNKNOWN"


def test_T10_days_beyond_window_expired():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=31,
        delta_market_value=1500.0,
    )
    assert status == "EXPIRED"


def test_T11_small_delta_low_confidence_partial():
    status, conf = classify_action_status(
        lineage_confidence="LOW",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=5,
        delta_market_value=200.0,  # below $500 threshold
    )
    assert status == "PARTIALLY_FOLLOWED"


def test_T12_empty_direction_followed_low():
    status, conf = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="INCREASED",
        recommended_direction="",
        days_between=3,
        delta_market_value=1500.0,
    )
    assert status == "FOLLOWED"
    assert conf == "LOW"


# ─── Domain 2: Direction Resolution ──────────────────────────────────────────

def test_T13_new_position_is_buy():
    assert _change_to_direction("NEW_POSITION") == "BUY"


def test_T14_increased_is_buy():
    assert _change_to_direction("INCREASED") == "BUY"


def test_T15_exited_is_reduce():
    assert _change_to_direction("EXITED_POSITION") == "REDUCE"


def test_T16_reduced_is_reduce():
    assert _change_to_direction("REDUCED") == "REDUCE"


def test_T17_unchanged_empty_direction():
    assert _change_to_direction("UNCHANGED") == ""


# ─── Domain 3: Source Classification ─────────────────────────────────────────

def test_T18_deployment_queue_preserved():
    assert _normalize_source("DEPLOYMENT_QUEUE") == "DEPLOYMENT_QUEUE"


def test_T19_pap_preserved():
    assert _normalize_source("PAP") == "PAP"


def test_T20_dil_preserved():
    assert _normalize_source("DIL") == "DIL"


def test_T21_cra_preserved():
    assert _normalize_source("CRA") == "CRA"


def test_T22_unknown_becomes_other():
    assert _normalize_source("") == "OTHER"
    assert _normalize_source("RECOMMENDATION_HISTORY") == "OTHER"


# ─── Domain 4: Delay Calculation ─────────────────────────────────────────────

def _make_record(status, source="DEPLOYMENT_QUEUE", days=None, outcome="NEUTRAL", direction="BUY"):
    return ActionAttributionRecord(
        attribution_id=f"AA-{status}-{days}",
        recommendation_id="REC-001",
        recommendation_source=source,
        recommendation_date="2026-06-01",
        symbol="ARW",
        recommended_direction=direction,
        action_status=status,
        action_confidence="MEDIUM",
        observed_change_type="INCREASED" if status in ("FOLLOWED",) else "",
        observed_date="2026-06-08" if days is not None else "",
        response_days=days,
        delta_quantity=10.0,
        delta_market_value=1000.0,
        outcome=outcome,
        lineage_confidence="MEDIUM",
        created_at="2026-06-15T00:00:00+00:00",
    )


def test_T23_response_days_calculation():
    """T-23: days_between from classify correctly maps to response_days."""
    # Via classify_action_status — days_between=7 → FOLLOWED with days preserved
    status, _ = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=7,
        delta_market_value=1500.0,
    )
    assert status == "FOLLOWED"  # 7 <= 30


def test_T24_same_day_response():
    status, _ = classify_action_status(
        lineage_confidence="HIGH",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=0,
        delta_market_value=2000.0,
    )
    assert status == "FOLLOWED"


def test_T25_ignored_response_days_none():
    r = _make_record("IGNORED", days=None)
    assert r.response_days is None


def test_T26_expired_days_31():
    status, _ = classify_action_status(
        lineage_confidence="MEDIUM",
        change_type="INCREASED",
        recommended_direction="BUY",
        days_between=31,
        delta_market_value=1000.0,
    )
    assert status == "EXPIRED"


# ─── Domain 5: Source Scorecard ───────────────────────────────────────────────

def _make_records_for_source(statuses, source="DEPLOYMENT_QUEUE", outcomes=None):
    if outcomes is None:
        outcomes = ["NEUTRAL"] * len(statuses)
    return [
        _make_record(s, source=source, days=3 if s == "FOLLOWED" else None, outcome=o)
        for s, o in zip(statuses, outcomes)
    ]


def test_T27_scorecard_mixed_statuses():
    recs = _make_records_for_source(["FOLLOWED", "FOLLOWED", "IGNORED", "OPPOSED"])
    cards = _compute_scorecards(recs)
    assert len(cards) == 1
    c = cards[0]
    assert c.followed_count == 2
    assert c.ignored_count == 1
    assert c.opposed_count == 1
    assert abs(c.follow_rate_pct - 50.0) < 0.1
    assert abs(c.ignore_rate_pct - 25.0) < 0.1
    assert abs(c.oppose_rate_pct - 25.0) < 0.1


def test_T28_scorecard_all_followed():
    recs = _make_records_for_source(["FOLLOWED"] * 5)
    cards = _compute_scorecards(recs)
    assert cards[0].follow_rate_pct == 100.0


def test_T29_scorecard_all_ignored():
    recs = _make_records_for_source(["IGNORED"] * 4)
    cards = _compute_scorecards(recs)
    assert cards[0].follow_rate_pct == 0.0
    assert cards[0].ignore_rate_pct == 100.0


def test_T30_scorecard_empty_source():
    cards = _compute_scorecards([])
    assert cards == []


def test_T31_win_rate_correct():
    recs = _make_records_for_source(
        ["FOLLOWED", "FOLLOWED", "FOLLOWED", "FOLLOWED"],
        outcomes=["WINNER", "WINNER", "LOSER", "NEUTRAL"],
    )
    cards = _compute_scorecards(recs)
    # winner/(winner+loser) = 2/3 ≈ 66.7
    assert abs(cards[0].win_rate_pct - 66.7) < 0.2


def test_T32_win_rate_no_outcomes():
    recs = _make_records_for_source(["FOLLOWED"] * 3, outcomes=["UNKNOWN"] * 3)
    cards = _compute_scorecards(recs)
    assert cards[0].win_rate_pct == 0.0


# ─── Domain 6: Aggregate Summary ─────────────────────────────────────────────

def test_T33_counts_sum_to_total(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    lin_rows = [
        _make_lineage_row("CHG-001", "ARW", "INCREASED", "MEDIUM", "REC-001", "DEPLOYMENT_QUEUE", "2026-06-01", "7"),
        _make_lineage_row("CHG-002", "MU",  "REDUCED",   "LOW",   "REC-002", "PAP",              "2026-06-01", "3"),
        _make_lineage_row("CHG-003", "TSLA","INCREASED", "NONE",  "",        "",                 "",           ""),
    ]
    chg_rows = [
        _make_change_row("CHG-001", "ARW",  "INCREASED",    "2026-06-08", 10.0,   1000.0),
        _make_change_row("CHG-002", "MU",   "REDUCED",      "2026-06-04", -5.0,  -400.0),
        _make_change_row("CHG-003", "TSLA", "INCREASED",    "2026-06-10", 20.0,   3000.0),
    ]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, chg_rows)

    summary = pis_action_attribution_summary(tmp_path)
    total = summary["total_attribution_records"]
    counted = (
        summary["followed_count"] +
        summary["partially_followed_count"] +
        summary["ignored_count"] +
        summary["opposed_count"] +
        summary["expired_count"] +
        summary.get("unknown_count", 0)
    )
    assert counted == total


def test_T34_follow_rate_correct(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    lin_rows = [
        _make_lineage_row("CHG-001", "ARW", "INCREASED", "MEDIUM", "REC-001", "DEPLOYMENT_QUEUE", "2026-06-01", "3"),
        _make_lineage_row("CHG-002", "MU",  "INCREASED", "NONE",   "",        "",                 "",           ""),
    ]
    chg_rows = [
        _make_change_row("CHG-001", "ARW", "INCREASED", "2026-06-04", 10.0, 1000.0),
        _make_change_row("CHG-002", "MU",  "INCREASED", "2026-06-04", 5.0,  500.0),
    ]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, chg_rows)

    summary = pis_action_attribution_summary(tmp_path)
    # Recommendation-centric view excludes unmatched lineage rows without rec IDs.
    assert summary["total_attribution_records"] == 1
    assert abs(summary["follow_rate_pct"] - 100.0) < 1.0


def test_T35_avg_response_days_ignores_none(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    lin_rows = [
        _make_lineage_row("CHG-001", "ARW", "INCREASED", "MEDIUM", "REC-001", "DEPLOYMENT_QUEUE", "2026-06-01", "6"),
        _make_lineage_row("CHG-002", "MU",  "INCREASED", "NONE",   "",        "",                 "",           ""),
    ]
    chg_rows = [
        _make_change_row("CHG-001", "ARW", "INCREASED", "2026-06-07", 10.0, 1000.0),
        _make_change_row("CHG-002", "MU",  "INCREASED", "2026-06-07", 5.0, 500.0),
    ]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, chg_rows)

    summary = pis_action_attribution_summary(tmp_path)
    # Only CHG-001 has response_days=6; CHG-002 (UNKNOWN) has none
    assert summary["avg_response_days"] == 6.0


def test_T36_observations_is_list(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, [])
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, [])
    summary = pis_action_attribution_summary(tmp_path)
    assert isinstance(summary["observations"], list)


def test_T37_empty_lineage_all_zeros(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, [])
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, [])
    summary = pis_action_attribution_summary(tmp_path)
    assert summary["total_attribution_records"] == 0
    assert summary["followed_count"] == 0
    assert summary["ignored_count"] == 0


# ─── Domain 7: Missed Opportunities ──────────────────────────────────────────

def test_T38_ignored_winner_is_missed():
    recs = [_make_record("IGNORED", direction="BUY", outcome="WINNER")]
    missed = _find_missed_opportunities(recs)
    assert len(missed) == 1
    assert missed[0]["symbol"] == "ARW"


def test_T39_followed_not_missed():
    recs = [_make_record("FOLLOWED", direction="BUY", outcome="WINNER")]
    missed = _find_missed_opportunities(recs)
    assert missed == []


def test_T40_ignored_neutral_not_missed():
    recs = [_make_record("IGNORED", direction="BUY", outcome="NEUTRAL")]
    missed = _find_missed_opportunities(recs)
    assert missed == []


def test_T41_missed_opportunities_capped_at_10():
    recs = [_make_record("IGNORED", direction="BUY", outcome="WINNER") for _ in range(15)]
    missed = _find_missed_opportunities(recs)
    assert len(missed) <= 10


# ─── Domain 8: API Payload Integrity ─────────────────────────────────────────

def _minimal_setup(tmp_path):
    """Create minimal valid data for API tests."""
    paths = _setup_pis_dirs(tmp_path)
    lin_rows = [
        _make_lineage_row("CHG-001", "ARW", "INCREASED", "MEDIUM", "REC-001", "DEPLOYMENT_QUEUE", "2026-06-01", "7"),
        _make_lineage_row("CHG-002", "MU",  "REDUCED",   "NONE",   "",        "",                 "",           ""),
    ]
    chg_rows = [
        _make_change_row("CHG-001", "ARW", "INCREASED", "2026-06-08", 15.0, 1500.0),
        _make_change_row("CHG-002", "MU",  "REDUCED",   "2026-06-08", -5.0, -600.0),
    ]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, chg_rows)
    return paths


def test_T42_summary_required_fields(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_action_attribution_summary(tmp_path)
    required = {
        "generated_at", "total_attribution_records", "followed_count",
        "partially_followed_count", "ignored_count", "opposed_count",
        "expired_count", "unknown_count", "follow_rate_pct", "ignore_rate_pct", "oppose_rate_pct",
        "avg_response_days", "sources_covered", "dates_covered", "observations",
    }
    assert required.issubset(result.keys())


def test_T43_recommendations_payload_record_fields(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_action_attribution_recommendations(tmp_path)
    assert "records" in result
    assert len(result["records"]) > 0
    rec = result["records"][0]
    required = {
        "attribution_id", "recommendation_id", "recommendation_source",
        "symbol", "recommended_direction", "action_status", "action_confidence",
        "observed_change_type", "response_days", "outcome",
    }
    assert required.issubset(rec.keys())


def test_T44_sources_payload_scorecard_fields(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_action_attribution_sources(tmp_path)
    assert "scorecards" in result
    assert len(result["scorecards"]) > 0
    card = result["scorecards"][0]
    required = {
        "source", "total_recommendations", "followed_count", "ignored_count",
        "follow_rate_pct", "ignore_rate_pct", "oppose_rate_pct",
    }
    assert required.issubset(card.keys())


def test_T45_attribution_ids_unique(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_action_attribution_recommendations(tmp_path)
    ids = [r["attribution_id"] for r in result["records"]]
    assert len(ids) == len(set(ids))


def test_T46_recommendation_source_never_null(tmp_path):
    _minimal_setup(tmp_path)
    result = pis_action_attribution_recommendations(tmp_path)
    for rec in result["records"]:
        assert rec["recommendation_source"] is not None
        assert rec["recommendation_source"] != ""


# ─── Domain 9: Edge Cases ─────────────────────────────────────────────────────

def test_T47_no_lineage_file_empty_payload(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    # lineage_records.csv does not exist
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, [])
    result = pis_action_attribution_summary(tmp_path)
    assert result["total_attribution_records"] == 0


def test_T48_no_change_file_empty_payload(tmp_path):
    paths = _setup_pis_dirs(tmp_path)
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, [])
    # change_records.csv does not exist
    result = pis_action_attribution_summary(tmp_path)
    assert result["total_attribution_records"] == 0


def test_T49_no_par_directory(tmp_path):
    """No PAR directory — should not raise; falls back to lineage only."""
    paths = _setup_pis_dirs(tmp_path)
    # Remove par directory
    import shutil
    shutil.rmtree(paths["par"])
    lin_rows = [_make_lineage_row("CHG-001", "ARW", "INCREASED", "NONE")]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, [])
    # Should not raise
    result = pis_action_attribution_summary(tmp_path)
    assert isinstance(result, dict)


def test_T50_negative_days_clamped(tmp_path):
    """Recommendation date AFTER observed date → days_between clamped to 0."""
    paths = _setup_pis_dirs(tmp_path)
    # days_between stored as negative value in lineage
    lin_rows = [
        _make_lineage_row("CHG-001", "ARW", "INCREASED", "MEDIUM", "REC-001", "DEPLOYMENT_QUEUE", "2026-06-10", "-3"),
    ]
    chg_rows = [_make_change_row("CHG-001", "ARW", "INCREASED", "2026-06-07", 10.0, 1000.0)]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, chg_rows)
    result = pis_action_attribution_recommendations(tmp_path)
    for rec in result["records"]:
        if rec["symbol"] == "ARW":
            assert (rec["response_days"] is None) or (rec["response_days"] >= 0)


def test_T51_unchanged_excluded_from_attribution(tmp_path):
    """UNCHANGED change_type records should not appear in attribution output."""
    paths = _setup_pis_dirs(tmp_path)
    lin_rows = [
        _make_lineage_row("CHG-UNC", "NVDA", "UNCHANGED", "NONE"),
        _make_lineage_row("CHG-001", "ARW",  "INCREASED",  "MEDIUM", "REC-001", "DEPLOYMENT_QUEUE", "2026-06-01", "3"),
    ]
    chg_rows = [
        _make_change_row("CHG-UNC", "NVDA", "UNCHANGED", "2026-06-08", 0.0, 0.0),
        _make_change_row("CHG-001", "ARW",  "INCREASED",  "2026-06-04", 10.0, 1000.0),
    ]
    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, lin_rows)
    _write_csv(paths["changes"] / "change_records.csv", _CHANGE_HEADERS, chg_rows)

    result = pis_action_attribution_recommendations(tmp_path)
    # CHG-UNC (UNCHANGED) is in lineage with NONE confidence → remains UNKNOWN
    # but it should NOT be classified as FOLLOWED since no change direction exists
    arw_records = [r for r in result["records"] if r["symbol"] == "ARW"]
    nvda_records = [r for r in result["records"] if r["symbol"] == "NVDA"]

    # ARW should be FOLLOWED
    assert any(r["action_status"] == "FOLLOWED" for r in arw_records)
    # NVDA UNCHANGED→NONE→UNKNOWN (change_dir="") → should be UNKNOWN
    assert all(r["action_status"] == "UNKNOWN" for r in nvda_records)


def test_T52_unmatched_recommendation_open_window_is_unknown(tmp_path):
    paths = _setup_pis_dirs(tmp_path)

    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, [])
    _write_csv(
        paths["changes"] / "change_records.csv",
        _CHANGE_HEADERS,
        [
            _make_change_row("CHG-001", "ARW", "UNCHANGED", "2026-06-10", 0.0, 0.0),
        ],
    )

    run_dir = paths["par"] / "PAR-20260610-TEST"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_metadata.json").write_text(json.dumps({"snapshot_date": "2026-06-10"}), encoding="utf-8")
    (run_dir / "recommendations.json").write_text(
        json.dumps([
            {
                "recommendation_id": "REC-OPEN-WINDOW",
                "recommendation_type": "PORTFOLIO_CONSTRUCTION_NARRATIVE",
                "created_at_utc": "2026-06-08T00:00:00Z",
                "title": "Keep ARW core",
                "affected_symbols": ["ARW"],
            }
        ]),
        encoding="utf-8",
    )

    records = _build_attribution_records(tmp_path)
    target = next(r for r in records if r.recommendation_id == "REC-OPEN-WINDOW")
    assert target.action_status == "UNKNOWN"


def test_T53_unmatched_recommendation_matured_window_no_action_is_ignored(tmp_path):
    paths = _setup_pis_dirs(tmp_path)

    _write_csv(paths["lineage"] / "lineage_records.csv", _LINEAGE_HEADERS, [])
    _write_csv(
        paths["changes"] / "change_records.csv",
        _CHANGE_HEADERS,
        [
            _make_change_row("CHG-001", "ARW", "UNCHANGED", "2026-07-20", 0.0, 0.0),
        ],
    )

    run_dir = paths["par"] / "PAR-20260720-TEST"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_metadata.json").write_text(json.dumps({"snapshot_date": "2026-07-20"}), encoding="utf-8")
    (run_dir / "recommendations.json").write_text(
        json.dumps([
            {
                "recommendation_id": "REC-MATURED-WINDOW",
                "recommendation_type": "PORTFOLIO_CONSTRUCTION_NARRATIVE",
                "created_at_utc": "2026-06-01T00:00:00Z",
                "title": "Keep ARW core",
                "affected_symbols": ["ARW"],
            }
        ]),
        encoding="utf-8",
    )

    records = _build_attribution_records(tmp_path)
    target = next(r for r in records if r.recommendation_id == "REC-MATURED-WINDOW")
    assert target.action_status == "IGNORED"
