"""Phase F-2 — Vehicle Suitability Scoring unit tests.

Validates the six Phase 6 acceptance conditions:
  1. VOO allowed (HIGH suitability) for general US Mega.
  2. VOO downgraded (MEDIUM or LOW) for Extended Mega; VTI/SCHB score higher.
  3. QQQ excluded from Extended Mega suggested vehicles.
  4. Suggested vehicle list is sorted by suitability_score descending.
  5. Suitability explanation is populated in recommendation output.
  6. Vehicles that worsen existing overweight include a warning in explanation.
"""
from __future__ import annotations

from src.portfolio.models import AllocationAlignmentResult, VehicleSuitabilityNote
from src.portfolio.recommendations import (
    _compute_vehicle_suitability,
    _sorted_vehicles_with_suitability,
    _SUGGESTED_VEHICLES,
)

_NOW = "2026-05-28T00:00:00Z"
_RUN = "RUN-TEST"
_SNAP = "PSNAP-TEST"


def _alignment_result(
    node_key: str,
    drift_direction: str = "UNDERWEIGHT",
    severity: str = "HIGH",
    actual_pct: float = 5.0,
    tactical_target_pct: float = 20.0,
    drift_pct: float = -15.0,
) -> AllocationAlignmentResult:
    return AllocationAlignmentResult(
        analysis_run_id=_RUN,
        portfolio_snapshot_id=_SNAP,
        node_key=node_key,
        node_label=node_key,
        dimension_type="MARKET_CAP",
        actual_pct=actual_pct,
        target_pct=tactical_target_pct,
        tactical_target_pct=tactical_target_pct,
        drift_pct=drift_pct,
        drift_direction=drift_direction,
        severity=severity,
        concentration_risk="LOW",
        alignment_score=0.3,
        recommendation_priority=1,
        created_at_utc=_NOW,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — VOO is HIGH suitability for general US Mega
# ─────────────────────────────────────────────────────────────────────────────

def test_voo_high_suitability_general_mega():
    note = _compute_vehicle_suitability("VOO", "EQUITIES.US.MEGA", [])
    assert isinstance(note, VehicleSuitabilityNote)
    assert note.suitability_tier == "HIGH", (
        f"Expected VOO to be HIGH suitability for general MEGA, got {note.suitability_tier}. "
        f"Score={note.suitability_score}. Explanation: {note.suitability_explanation}"
    )
    assert note.suitability_score > 0.0


def test_ivv_acceptable_general_mega():
    note = _compute_vehicle_suitability("IVV", "EQUITIES.US.MEGA", [])
    assert note.suitability_tier in ("HIGH", "MEDIUM"), (
        f"IVV should be acceptable for general MEGA, got {note.suitability_tier}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — VOO downgraded (not HIGH) for Extended Mega; VTI/SCHB score higher
# ─────────────────────────────────────────────────────────────────────────────

def test_voo_not_high_for_extended_mega():
    note = _compute_vehicle_suitability("VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert note.suitability_tier != "HIGH", (
        f"VOO should not be HIGH suitability for EXTENDED_MEGA (too much off-target MEGA). "
        f"Got tier={note.suitability_tier}, score={note.suitability_score}. "
        f"Explanation: {note.suitability_explanation}"
    )


def test_vti_scores_higher_than_voo_for_extended_mega():
    vti = _compute_vehicle_suitability("VTI", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    voo = _compute_vehicle_suitability("VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert vti.suitability_score > voo.suitability_score, (
        f"VTI should outscore VOO for EXTENDED_MEGA. "
        f"VTI={vti.suitability_score} ({vti.suitability_tier}), "
        f"VOO={voo.suitability_score} ({voo.suitability_tier})"
    )


def test_schb_scores_higher_than_voo_for_extended_mega():
    schb = _compute_vehicle_suitability("SCHB", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    voo = _compute_vehicle_suitability("VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert schb.suitability_score > voo.suitability_score, (
        f"SCHB should outscore VOO for EXTENDED_MEGA. "
        f"SCHB={schb.suitability_score} ({schb.suitability_tier}), "
        f"VOO={voo.suitability_score} ({voo.suitability_tier})"
    )


def test_vti_high_suitability_extended_mega():
    vti = _compute_vehicle_suitability("VTI", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert vti.suitability_tier == "HIGH", (
        f"VTI should be HIGH suitability for EXTENDED_MEGA. "
        f"Score={vti.suitability_score}, tier={vti.suitability_tier}. "
        f"Explanation: {vti.suitability_explanation}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — QQQ excluded from Extended Mega suggested vehicles
# ─────────────────────────────────────────────────────────────────────────────

def test_qqq_not_in_extended_mega_vehicles():
    candidates = _SUGGESTED_VEHICLES.get("EQUITIES.US.MEGA.EXTENDED_MEGA", ())
    assert "QQQ" not in candidates, (
        f"QQQ should not appear in EXTENDED_MEGA suggested vehicles. Got: {candidates}"
    )


def test_qqq_low_suitability_extended_mega():
    note = _compute_vehicle_suitability("QQQ", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert note.suitability_tier == "LOW", (
        f"QQQ should be LOW suitability for EXTENDED_MEGA (only 12.6% subtier purity + "
        f"95% MEGA_TECH_CONCENTRATION penalty). "
        f"Got tier={note.suitability_tier}, score={note.suitability_score}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Suggested vehicle list sorted by suitability_score descending
# ─────────────────────────────────────────────────────────────────────────────

def test_extended_mega_vehicles_sorted_by_score():
    sorted_syms, notes = _sorted_vehicles_with_suitability(
        "EQUITIES.US.MEGA.EXTENDED_MEGA", []
    )
    assert len(sorted_syms) > 0, "Should return at least one vehicle for EXTENDED_MEGA"
    assert len(sorted_syms) == len(notes)
    scores = [n.suitability_score for n in notes]
    assert scores == sorted(scores, reverse=True), (
        f"Vehicles should be sorted by suitability_score descending. "
        f"Symbols: {sorted_syms}, scores: {scores}"
    )


def test_general_mega_vehicles_sorted_by_score():
    sorted_syms, notes = _sorted_vehicles_with_suitability("EQUITIES.US.MEGA", [])
    assert len(sorted_syms) > 0
    scores = [n.suitability_score for n in notes]
    assert scores == sorted(scores, reverse=True), (
        f"General MEGA vehicles should be sorted by score. "
        f"Symbols: {sorted_syms}, scores: {scores}"
    )


def test_vti_or_schb_first_for_extended_mega():
    sorted_syms, _ = _sorted_vehicles_with_suitability(
        "EQUITIES.US.MEGA.EXTENDED_MEGA", []
    )
    assert len(sorted_syms) > 0
    assert sorted_syms[0] in ("VTI", "SCHB"), (
        f"VTI or SCHB should rank first for EXTENDED_MEGA. Got: {sorted_syms}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Suitability explanation is populated in output
# ─────────────────────────────────────────────────────────────────────────────

def test_suitability_explanation_populated():
    _, notes = _sorted_vehicles_with_suitability(
        "EQUITIES.US.MEGA.EXTENDED_MEGA", []
    )
    assert len(notes) > 0
    for note in notes:
        assert note.suitability_explanation, (
            f"{note.symbol}: suitability_explanation should not be empty"
        )
        assert note.symbol in note.suitability_explanation, (
            f"{note.symbol}: symbol should appear in its own explanation"
        )
        assert note.suitability_tier in note.suitability_explanation, (
            f"{note.symbol}: tier ({note.suitability_tier}) should appear in explanation"
        )


def test_suitability_explanation_mentions_coverage():
    vti = _compute_vehicle_suitability("VTI", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    expl = vti.suitability_explanation.lower()
    assert "extended mega" in expl or "extended_mega" in expl or "extended" in expl, (
        f"VTI Extended Mega explanation should mention 'extended': {vti.suitability_explanation}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — Overweight warning appears in explanation when applicable
# ─────────────────────────────────────────────────────────────────────────────

def test_overweight_warning_in_voo_explanation_when_mega_overweight():
    overweight_ar = _alignment_result(
        "EQUITIES.US.MEGA",
        drift_direction="OVERWEIGHT",
        severity="HIGH",
        actual_pct=25.0,
        tactical_target_pct=15.0,
        drift_pct=10.0,
    )
    note = _compute_vehicle_suitability(
        "VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [overweight_ar]
    )
    assert note.worsens_existing_overweight is True, (
        "VOO should be flagged as worsening US Mega overweight when EQUITIES.US.MEGA is OVERWEIGHT"
    )
    expl = note.suitability_explanation.lower()
    assert "overweight" in expl or "worsen" in expl, (
        f"Overweight warning should appear in explanation when worsens=True. "
        f"Got: {note.suitability_explanation}"
    )


def test_no_overweight_warning_when_not_overweight():
    underweight_ar = _alignment_result(
        "EQUITIES.US.MEGA",
        drift_direction="UNDERWEIGHT",
        severity="HIGH",
    )
    note = _compute_vehicle_suitability(
        "VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [underweight_ar]
    )
    assert note.worsens_existing_overweight is False, (
        "VOO should not flag overweight worsening when EQUITIES.US.MEGA is UNDERWEIGHT"
    )


def test_voo_score_lower_when_mega_overweight():
    clean = _compute_vehicle_suitability("VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    overweight_ar = _alignment_result(
        "EQUITIES.US.MEGA",
        drift_direction="OVERWEIGHT",
        severity="HIGH",
        actual_pct=25.0,
        tactical_target_pct=15.0,
        drift_pct=10.0,
    )
    penalized = _compute_vehicle_suitability(
        "VOO", "EQUITIES.US.MEGA.EXTENDED_MEGA", [overweight_ar]
    )
    assert penalized.suitability_score < clean.suitability_score, (
        f"VOO score should be lower when portfolio has OVERWEIGHT US Mega. "
        f"Clean={clean.suitability_score}, penalized={penalized.suitability_score}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Additional structural tests
# ─────────────────────────────────────────────────────────────────────────────

def test_suitability_note_fields_all_present():
    note = _compute_vehicle_suitability("VTI", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert note.symbol == "VTI"
    assert 0.0 <= note.suitability_score <= 100.0
    assert note.suitability_tier in ("HIGH", "MEDIUM", "LOW")
    assert isinstance(note.worsens_existing_overweight, bool)
    assert note.strategic_role  # should be non-empty for registry symbols


def test_unknown_symbol_returns_low_score():
    note = _compute_vehicle_suitability("XYZUNKNOWN", "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
    assert note.suitability_tier == "LOW"
    assert note.suitability_score == 0.0
    assert "no decomposition registry entry" in note.suitability_explanation


def test_voo_vti_schb_all_scored_for_extended_mega():
    """All three Extended Mega candidates from _SUGGESTED_VEHICLES are scored."""
    for sym in ("VTI", "SCHB", "VOO"):
        note = _compute_vehicle_suitability(sym, "EQUITIES.US.MEGA.EXTENDED_MEGA", [])
        assert note.suitability_score >= 0.0
        assert note.suitability_tier in ("HIGH", "MEDIUM", "LOW")
        assert note.symbol == sym
