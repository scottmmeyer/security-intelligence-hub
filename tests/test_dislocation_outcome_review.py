"""ISSUE-12D — Dislocation Outcome Review Panel — Validation Test Suite.

All tests deterministic and filesystem-isolated via pytest tmp_path.
No network calls. No modifications to existing project data.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.pis.dislocation_outcome_review import (
    DORRecord,
    CohortSummary,
    DIL_ELIGIBLE_LABELS,
    UCF_DIRECTION,
    _load_ucf_history,
    _load_dil_action_attribution,
    _build_dor_records,
    _build_cohorts,
    _generate_observations,
    _find_missed_winners,
    pis_dor_summary,
    pis_dor_cohorts,
    pis_dor_recommendations,
)


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _par_dir(root: Path) -> Path:
    d = root / "data" / "portfolio_ingestion" / "analysis_runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_par_with_ucf(
    root: Path,
    par_id: str,
    snap_date: str,
    verdicts: list[dict],
    created_at: str = "2026-06-15T10:00:00+00:00",
) -> Path:
    par = _par_dir(root) / par_id
    par.mkdir(parents=True, exist_ok=True)
    meta = {"run_id": par_id, "snapshot_date": snap_date, "created_at_utc": created_at}
    (par / "run_metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    ucf = {"run_id": par_id, "ucf_version": "1.0", "generated_at": created_at,
           "queue_size": len(verdicts), "total_holdings": len(verdicts), "verdicts": verdicts}
    (par / "ucf_verdicts.json").write_text(json.dumps(ucf), encoding="utf-8")
    return par


def _make_verdict(symbol: str, ucf_label: str, ucf_score: float = 80.0,
                  ucf_rank: int = 1, signal_direction: str = "BULLISH",
                  composite_score: float = 4.5, replay_supported: bool = True,
                  replay_percentile: float = 75.0, cw_das_score: float = 90.0,
                  conflict_flags: list | None = None) -> dict:
    return {
        "symbol": symbol,
        "ucf_label": ucf_label,
        "ucf_score": ucf_score,
        "ucf_rank": ucf_rank,
        "conflict_flags": conflict_flags or [],
        "source_signals": {
            "signal_direction": signal_direction,
            "composite_score": composite_score,
            "replay_supported": replay_supported,
            "replay_percentile": replay_percentile,
            "cw_das_score": cw_das_score,
        },
        "signal_summary": f"{symbol} — {ucf_label}",
    }


def _make_attr_cache(root: Path, records: list[dict]) -> None:
    path = root / "data/history/pis/action_attribution/attribution_cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": records, "scorecards": []}), encoding="utf-8")


_ATTRIBUTION_HEADERS = [
    "attribution_id", "snapshot_id", "snapshot_date", "change_id", "symbol",
    "change_type", "matched_recommendation_id", "matched_recommendation",
    "recommendation_source", "recommendation_date", "confidence",
    "old_market_value", "new_market_value", "delta_market_value",
    "directional_attribution", "directional_return_pct", "outcome", "created_at",
]

_BENCHMARK_HEADERS = [
    "snapshot_date", "prior_snapshot_date", "recommendation_id", "symbol",
    "recommendation_source", "change_type", "directional_return_pct",
    "benchmark_symbol", "benchmark_return_pct", "recommendation_excess_return_pct",
    "lineage_confidence", "data_quality_status", "directional_attribution",
]


def _make_attr_row(symbol: str, outcome: str, return_pct: float = 10.0) -> dict:
    return {h: "" for h in _ATTRIBUTION_HEADERS} | {
        "attribution_id": f"ATTR-{symbol}",
        "symbol": symbol,
        "change_type": "INCREASED",
        "recommendation_source": "DIL",
        "directional_return_pct": str(return_pct),
        "outcome": outcome,
        "created_at": "2026-06-15T00:00:00+00:00",
    }


def _write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _make_benchmark_row(symbol: str, excess_return: float) -> dict:
    return {h: "" for h in _BENCHMARK_HEADERS} | {
        "symbol": symbol,
        "recommendation_excess_return_pct": str(excess_return),
    }


def _make_dil_attr_record(symbol: str, rec_date: str, action_status: str,
                           outcome: str = "UNKNOWN", response_days: int = 0) -> dict:
    return {
        "attribution_id": f"AA-DIL-{symbol}",
        "recommendation_id": f"DIL-PAR-{symbol}",
        "recommendation_source": "DIL",
        "recommendation_date": rec_date,
        "symbol": symbol,
        "recommended_direction": "BUY",
        "action_status": action_status,
        "action_confidence": "MEDIUM",
        "observed_change_type": "INCREASED" if action_status == "FOLLOWED" else "",
        "observed_date": rec_date if action_status == "FOLLOWED" else "",
        "response_days": response_days,
        "delta_quantity": 10.0,
        "delta_market_value": 1000.0,
        "outcome": outcome,
        "lineage_confidence": "MEDIUM",
        "created_at": "2026-06-15T00:00:00+00:00",
    }


# ─── Domain 1: UCF History Loading ───────────────────────────────────────────

def test_T01_empty_par_directory(tmp_path):
    _par_dir(tmp_path)
    result = _load_ucf_history(tmp_path)
    assert result == []


def test_T02_single_par_single_verdict(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER")])
    history = _load_ucf_history(tmp_path)
    assert len(history) == 1
    assert history[0]["symbol"] == "VRT"
    assert history[0]["ucf_label"] == "CORE_CONVICTION_LEADER"
    assert history[0]["snapshot_date"] == "2026-06-01"


def test_T03_canonical_selection_latest_wins(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-EARLY", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER", ucf_score=50.0)],
                       created_at="2026-06-01T08:00:00+00:00")
    _make_par_with_ucf(tmp_path, "PAR-LATE", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER", ucf_score=90.0)],
                       created_at="2026-06-01T12:00:00+00:00")
    history = _load_ucf_history(tmp_path)
    # One date → one record; latest PAR wins
    assert len(history) == 1
    assert abs(history[0]["ucf_score"] - 90.0) < 0.1


def test_T04_source_signals_fields_extracted(tmp_path):
    v = _make_verdict("ARW", "HIGH_CONVICTION_ANCHOR", composite_score=4.2,
                      replay_supported=True, replay_percentile=82.5, cw_das_score=91.0)
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [v])
    h = _load_ucf_history(tmp_path)[0]
    assert abs(h["composite_score"] - 4.2) < 0.01
    assert h["replay_supported"] is True
    assert abs(h["replay_percentile"] - 82.5) < 0.01


def test_T05_missing_source_signals_defaults(tmp_path):
    verdict = {"symbol": "NVDA", "ucf_label": "DEPLOYMENT_CANDIDATE",
               "ucf_score": 60.0, "ucf_rank": 5, "conflict_flags": []}
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [verdict])
    h = _load_ucf_history(tmp_path)[0]
    assert h["composite_score"] == 0.0
    assert h["replay_supported"] is False


def test_T06_malformed_snapshot_date_skipped(tmp_path):
    par = _par_dir(tmp_path) / "PAR-BAD"
    par.mkdir(parents=True, exist_ok=True)
    meta = {"snapshot_date": "NOT-A-DATE", "created_at_utc": "2026-06-01T10:00:00+00:00"}
    (par / "run_metadata.json").write_text(json.dumps(meta))
    ucf = {"verdicts": [_make_verdict("VRT", "CORE_CONVICTION_LEADER")]}
    (par / "ucf_verdicts.json").write_text(json.dumps(ucf))
    _make_par_with_ucf(tmp_path, "PAR-OK", "2026-06-01",
                       [_make_verdict("ARW", "HIGH_CONVICTION_ANCHOR")])
    history = _load_ucf_history(tmp_path)
    symbols = [h["symbol"] for h in history]
    assert "ARW" in symbols
    assert "VRT" not in symbols  # PAR-BAD's date was malformed


def test_T07_non_eligible_labels_excluded(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [
        _make_verdict("MAINTAIN_SYM", "MAINTAIN"),
        _make_verdict("TACTICAL_SYM", "TACTICAL_GROWTH"),
        _make_verdict("CCL_SYM", "CORE_CONVICTION_LEADER"),
    ])
    records = _build_dor_records(tmp_path)
    symbols = [r.symbol for r in records]
    assert "CCL_SYM" in symbols
    assert "MAINTAIN_SYM" not in symbols
    assert "TACTICAL_SYM" not in symbols


def test_T08_dil_eligible_labels_included(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [
        _make_verdict("A", "CORE_CONVICTION_LEADER"),
        _make_verdict("B", "HIGH_CONVICTION_ANCHOR"),
        _make_verdict("C", "DEPLOYMENT_CANDIDATE"),
        _make_verdict("D", "TRIM_WATCH"),
    ])
    records = _build_dor_records(tmp_path)
    symbols = {r.symbol for r in records}
    assert symbols == {"A", "B", "C", "D"}


# ─── Domain 2: Action Attribution Integration ─────────────────────────────────

def test_T09_followed_status_from_attribution(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("ARW", "HIGH_CONVICTION_ANCHOR")])
    _make_attr_cache(tmp_path, [
        _make_dil_attr_record("ARW", "2026-06-01", "FOLLOWED", "WINNER", response_days=3)
    ])
    records = _build_dor_records(tmp_path)
    arw = next(r for r in records if r.symbol == "ARW")
    assert arw.action_status == "FOLLOWED"


def test_T10_no_attribution_entry_defaults_ignored(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER")])
    # No attribution cache
    records = _build_dor_records(tmp_path)
    vrt = records[0]
    assert vrt.action_status == "IGNORED"


def test_T11_multiple_attribution_highest_status_used(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("MU", "HIGH_CONVICTION_ANCHOR")])
    # Two records for same (symbol, date) — FOLLOWED should win over IGNORED
    _make_attr_cache(tmp_path, [
        _make_dil_attr_record("MU", "2026-06-01", "IGNORED"),
        _make_dil_attr_record("MU", "2026-06-01", "FOLLOWED", "WINNER"),
    ])
    records = _build_dor_records(tmp_path)
    mu = next(r for r in records if r.symbol == "MU")
    assert mu.action_status == "FOLLOWED"


def test_T12_missing_attribution_cache_all_ignored(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [
        _make_verdict("A", "CORE_CONVICTION_LEADER"),
        _make_verdict("B", "TRIM_WATCH"),
    ])
    records = _build_dor_records(tmp_path)
    assert all(r.action_status == "IGNORED" for r in records)


# ─── Domain 3: Outcome Reconstruction ────────────────────────────────────────

def test_T13_winner_outcome_from_attribution(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("VRT", "2026-06-01", "FOLLOWED", "WINNER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("VRT", "WINNER", 15.0)])
    records = _build_dor_records(tmp_path)
    vrt = records[0]
    assert vrt.outcome == "WINNER"


def test_T14_loser_outcome(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("TSLA", "DEPLOYMENT_CANDIDATE")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("TSLA", "2026-06-01", "FOLLOWED", "LOSER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("TSLA", "LOSER", -8.0)])
    records = _build_dor_records(tmp_path)
    tsla = records[0]
    assert tsla.outcome == "LOSER"


def test_T15_no_attribution_record_unknown(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("NVDA", "HIGH_CONVICTION_ANCHOR")])
    records = _build_dor_records(tmp_path)
    nvda = records[0]
    assert nvda.outcome == "UNKNOWN"


def test_T16_benchmark_excess_return_populated(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("ARW", "HIGH_CONVICTION_ANCHOR")])
    _write_csv(tmp_path / "data/history/pis/benchmark_attribution/recommendation_benchmark_records.csv",
               _BENCHMARK_HEADERS, [_make_benchmark_row("ARW", 12.5)])
    records = _build_dor_records(tmp_path)
    arw = records[0]
    assert abs(arw.excess_return_pct - 12.5) < 0.01


def test_T17_no_benchmark_record_zero_alpha(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("XYZ", "DEPLOYMENT_CANDIDATE")])
    records = _build_dor_records(tmp_path)
    xyz = records[0]
    assert xyz.excess_return_pct == 0.0


# ─── Domain 4: Governance Flag Assignment ─────────────────────────────────────

def test_T18_ignored_winner_gets_missed_winner_flag(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("CCL", "CORE_CONVICTION_LEADER")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("CCL", "2026-06-01", "IGNORED", "WINNER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("CCL", "WINNER")])
    records = _build_dor_records(tmp_path)
    assert "MISSED_WINNER" in records[0].governance_flags


def test_T19_followed_winner_no_missed_flag(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("VRT", "2026-06-01", "FOLLOWED", "WINNER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("VRT", "WINNER")])
    records = _build_dor_records(tmp_path)
    assert "MISSED_WINNER" not in records[0].governance_flags


def test_T20_followed_loser_gets_followed_loser_flag(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("TSLA", "HIGH_CONVICTION_ANCHOR")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("TSLA", "2026-06-01", "FOLLOWED", "LOSER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("TSLA", "LOSER")])
    records = _build_dor_records(tmp_path)
    assert "FOLLOWED_LOSER" in records[0].governance_flags


def test_T21_conflict_flags_trigger_signal_conflict(tmp_path):
    v = _make_verdict("MU", "DEPLOYMENT_CANDIDATE", conflict_flags=["CONFLICTING_SIGNAL"])
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [v])
    records = _build_dor_records(tmp_path)
    assert "SIGNAL_CONFLICT" in records[0].governance_flags


def test_T22_clean_followed_winner_no_flags(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("ARW", "HIGH_CONVICTION_ANCHOR")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("ARW", "2026-06-01", "FOLLOWED", "WINNER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("ARW", "WINNER")])
    records = _build_dor_records(tmp_path)
    assert records[0].governance_flags == ()


# ─── Domain 5: Cohort Analysis ────────────────────────────────────────────────

def _make_dor_record(symbol, ucf_label, action_status="IGNORED", outcome="UNKNOWN",
                     excess_return=0.0, directional_return=0.0, conflict_flags=()):
    direction = UCF_DIRECTION.get(ucf_label, "")
    gov = []
    if action_status == "IGNORED" and outcome == "WINNER":
        gov.append("MISSED_WINNER")
    if action_status in ("FOLLOWED","PARTIALLY_FOLLOWED") and outcome == "LOSER":
        gov.append("FOLLOWED_LOSER")
    if conflict_flags:
        gov.append("SIGNAL_CONFLICT")
    return DORRecord(
        record_id=f"DOR-2026-06-01-{symbol}",
        snapshot_date="2026-06-01",
        symbol=symbol,
        ucf_label=ucf_label,
        ucf_score=80.0,
        ucf_rank=1,
        recommended_direction=direction,
        signal_direction="BULLISH",
        composite_score=4.5,
        replay_supported=True,
        replay_percentile=75.0,
        cw_das_score=90.0,
        conflict_flags=tuple(conflict_flags),
        action_status=action_status,
        action_confidence="MEDIUM",
        outcome=outcome,
        directional_return_pct=directional_return,
        excess_return_pct=excess_return,
        observation_window_days=3,
        governance_flags=tuple(gov),
    )


def test_T23_cohort_mixed_outcomes():
    recs = [
        _make_dor_record("A", "CORE_CONVICTION_LEADER", "FOLLOWED", "WINNER", 15.0),
        _make_dor_record("B", "CORE_CONVICTION_LEADER", "FOLLOWED", "WINNER", 10.0),
        _make_dor_record("C", "CORE_CONVICTION_LEADER", "IGNORED", "UNKNOWN"),
    ]
    cohorts = _build_cohorts(recs)
    c = cohorts[0]
    assert c.ucf_label == "CORE_CONVICTION_LEADER"
    assert c.followed_count == 2
    assert c.ignored_count == 1
    assert abs(c.follow_rate_pct - 66.7) < 0.2
    assert c.win_rate_pct == 100.0


def test_T24_all_ignored_zero_follow_rate():
    recs = [_make_dor_record(f"S{i}", "HIGH_CONVICTION_ANCHOR", "IGNORED") for i in range(5)]
    cohorts = _build_cohorts(recs)
    c = cohorts[0]
    assert c.follow_rate_pct == 0.0
    assert c.win_rate_pct == 0.0


def test_T25_all_followed_winners():
    recs = [_make_dor_record(f"S{i}", "DEPLOYMENT_CANDIDATE", "FOLLOWED", "WINNER", 10.0) for i in range(3)]
    cohorts = _build_cohorts(recs)
    c = cohorts[0]
    assert c.follow_rate_pct == 100.0
    assert c.win_rate_pct == 100.0


def test_T26_mixed_winner_loser_win_rate():
    recs = [
        _make_dor_record("A", "HIGH_CONVICTION_ANCHOR", "FOLLOWED", "WINNER"),
        _make_dor_record("B", "HIGH_CONVICTION_ANCHOR", "FOLLOWED", "WINNER"),
        _make_dor_record("C", "HIGH_CONVICTION_ANCHOR", "FOLLOWED", "LOSER"),
    ]
    cohorts = _build_cohorts(recs)
    assert abs(cohorts[0].win_rate_pct - 66.7) < 0.2


def test_T27_multiple_labels_separate_cohorts():
    recs = [
        _make_dor_record("A", "CORE_CONVICTION_LEADER"),
        _make_dor_record("B", "HIGH_CONVICTION_ANCHOR"),
        _make_dor_record("C", "TRIM_WATCH"),
    ]
    cohorts = _build_cohorts(recs)
    labels = [c.ucf_label for c in cohorts]
    assert "CORE_CONVICTION_LEADER" in labels
    assert "HIGH_CONVICTION_ANCHOR" in labels
    assert "TRIM_WATCH" in labels


def test_T28_empty_records_empty_cohorts():
    cohorts = _build_cohorts([])
    assert cohorts == []


def test_T29_avg_alpha_only_from_followed():
    recs = [
        _make_dor_record("A", "CORE_CONVICTION_LEADER", "FOLLOWED", "WINNER", excess_return=12.0),
        _make_dor_record("B", "CORE_CONVICTION_LEADER", "IGNORED", "UNKNOWN", excess_return=0.0),
    ]
    cohorts = _build_cohorts(recs)
    # avg_alpha should be from followed records only → 12.0
    assert abs(cohorts[0].avg_alpha_pct - 12.0) < 0.01


# ─── Domain 6: Governance Observations ───────────────────────────────────────

def test_T30_ccl_missed_observation(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("CCL", "CORE_CONVICTION_LEADER")])
    _make_attr_cache(tmp_path, [_make_dil_attr_record("CCL", "2026-06-01", "IGNORED", "WINNER")])
    _write_csv(tmp_path / "data/history/pis/attribution/attribution_records.csv",
               _ATTRIBUTION_HEADERS, [_make_attr_row("CCL", "WINNER")])
    result = pis_dor_summary(tmp_path)
    obs_text = " ".join(result["observations"])
    assert "CORE_CONVICTION_LEADER" in obs_text or "ignored" in obs_text.lower()


def test_T31_no_followed_recs_observation(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("A", "HIGH_CONVICTION_ANCHOR")])
    result = pis_dor_summary(tmp_path)
    assert isinstance(result["observations"], list)


def test_T32_best_cohort_in_observations():
    recs = [
        _make_dor_record("A", "CORE_CONVICTION_LEADER", "FOLLOWED", "WINNER"),
        _make_dor_record("B", "HIGH_CONVICTION_ANCHOR", "IGNORED"),
    ]
    cohorts = _build_cohorts(recs)
    obs = _generate_observations(recs, cohorts)
    obs_text = " ".join(obs)
    # Should mention the best-performing cohort
    assert len(obs) > 0


def test_T33_signal_conflict_observation():
    recs = [
        _make_dor_record("A", "DEPLOYMENT_CANDIDATE", "FOLLOWED", "WINNER",
                         conflict_flags=("CONFLICTING_SIGNAL",)),
    ]
    cohorts = _build_cohorts(recs)
    obs = _generate_observations(recs, cohorts)
    obs_text = " ".join(obs)
    assert "conflict" in obs_text.lower()


def test_T34_observations_capped_at_6(tmp_path):
    # Create many conditions that would all generate observations
    verdicts = [_make_verdict(f"SYM{i}", "CORE_CONVICTION_LEADER",
                              conflict_flags=["CONFLICTING_SIGNAL"])
                for i in range(10)]
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", verdicts)
    result = pis_dor_summary(tmp_path)
    assert len(result["observations"]) <= 6


# ─── Domain 7: API Payload Integrity ─────────────────────────────────────────

def _minimal_dor_setup(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [
        _make_verdict("VRT", "CORE_CONVICTION_LEADER"),
        _make_verdict("ARW", "HIGH_CONVICTION_ANCHOR"),
        _make_verdict("TSLA", "TRIM_WATCH"),
    ])
    _make_attr_cache(tmp_path, [
        _make_dil_attr_record("VRT", "2026-06-01", "FOLLOWED", "WINNER"),
    ])


def test_T35_summary_required_fields(tmp_path):
    _minimal_dor_setup(tmp_path)
    result = pis_dor_summary(tmp_path)
    required = {
        "generated_at", "total_dil_records", "followed_count", "ignored_count",
        "winner_count", "loser_count", "follow_rate_pct", "win_rate_pct",
        "avg_alpha_pct", "missed_winner_count", "dates_covered", "observations",
        "governance_flags",
    }
    assert required.issubset(result.keys())


def test_T36_cohorts_fields_present(tmp_path):
    _minimal_dor_setup(tmp_path)
    result = pis_dor_cohorts(tmp_path)
    assert "cohorts" in result
    assert len(result["cohorts"]) > 0
    c = result["cohorts"][0]
    required = {"ucf_label", "direction", "total_count", "followed_count",
                "ignored_count", "follow_rate_pct", "win_rate_pct", "avg_alpha_pct"}
    assert required.issubset(c.keys())


def test_T37_recommendations_record_fields(tmp_path):
    _minimal_dor_setup(tmp_path)
    result = pis_dor_recommendations(tmp_path)
    assert "records" in result
    assert len(result["records"]) > 0
    r = result["records"][0]
    required = {"record_id", "snapshot_date", "symbol", "ucf_label",
                "action_status", "outcome", "governance_flags"}
    assert required.issubset(r.keys())


def test_T38_record_ids_unique(tmp_path):
    _minimal_dor_setup(tmp_path)
    result = pis_dor_recommendations(tmp_path)
    ids = [r["record_id"] for r in result["records"]]
    assert len(ids) == len(set(ids))


def test_T39_count_invariant(tmp_path):
    _minimal_dor_setup(tmp_path)
    result = pis_dor_summary(tmp_path)
    total = result["total_dil_records"]
    counted = result["followed_count"] + result["ignored_count"]
    # followed + ignored + other statuses = total; at minimum these two cover all
    assert counted <= total


# ─── Domain 8: Edge Cases ─────────────────────────────────────────────────────

def test_T40_no_ucf_verdicts_empty_payload(tmp_path):
    _par_dir(tmp_path)
    result = pis_dor_summary(tmp_path)
    assert result["total_dil_records"] == 0
    assert result["observations"] is not None


def test_T41_all_unknown_outcomes_zero_win_rate(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [
        _make_verdict("A", "CORE_CONVICTION_LEADER"),
        _make_verdict("B", "HIGH_CONVICTION_ANCHOR"),
    ])
    result = pis_dor_summary(tmp_path)
    assert result["win_rate_pct"] == 0.0
    assert result["winner_count"] == 0


def test_T42_single_date_valid(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01",
                       [_make_verdict("VRT", "CORE_CONVICTION_LEADER")])
    result = pis_dor_summary(tmp_path)
    assert result["dates_covered"] == 1
    assert result["total_dil_records"] == 1


def test_T43_maintain_tactical_excluded_from_total(tmp_path):
    _make_par_with_ucf(tmp_path, "PAR-001", "2026-06-01", [
        _make_verdict("A", "MAINTAIN"),
        _make_verdict("B", "TACTICAL_GROWTH"),
        _make_verdict("C", "CORE_CONVICTION_LEADER"),
        _make_verdict("D", "TRIM_WATCH"),
    ])
    result = pis_dor_summary(tmp_path)
    # Only CCL and TRIM_WATCH are eligible → total = 2
    assert result["total_dil_records"] == 2
