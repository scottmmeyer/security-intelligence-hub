"""Phase 7.7A — Unified Conviction Framework: Foundation Tests.

Validates build_ucf_verdicts() against the acceptance criteria specified in:
  - conviction_framework_design.md (§4 Label definitions, §5 Conflict flags,
    §6 UCF score formula, §7 Ranking)
  - ucf_readiness_assessment.md (GREEN verdict, all 7 criteria pass)

Test groups:
  1. Label assignment — 8 canonical holdings (AEIS, VRT, PRIM, SPAXX, PRG,
     CVE, MU, TSLA)
  2. Conflict flag detection — all 5 flag types
  3. UCF score structure — range, formula properties
  4. Ranking stability — AEIS rank 1, VRT rank 2, TRIM_WATCH at bottom
  5. Deployment intent fields — deployment_eligible, deployment_blocked
  6. No-mutation guarantee — source signals preserved verbatim
"""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".")

from src.portfolio.unified_conviction import (
    UCF_LABELS,
    UCF_VERSION,
    UnifiedConvictionVerdict,
    build_ucf_verdicts,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers (duck-typed dicts match the profile/overlay field contract)
# ─────────────────────────────────────────────────────────────────────────────

_SNAP_ID = "PSNAP-7-7A-TEST"
_NOW     = "2026-05-31T14:00:00+00:00"


def _profile(
    symbol: str,
    narrative_tier: str = "TACTICAL_GROWTH_CANDIDATE",
    strategic_classification: str = "TACTICAL_GROWTH",
    trim_priority_score: float = 5.0,
) -> dict:
    return {
        "symbol": symbol,
        "narrative_tier": narrative_tier,
        "strategic_classification": strategic_classification,
        "trim_priority_score": trim_priority_score,
    }


def _overlay(
    symbol: str,
    composite_score: float | None = 4.0,
    ess_score_text: str = "BULLISH",
    signal_direction: str = "BULLISH",
    replay_supported: bool = True,
    replay_percentile: float | None = 90.0,
    percent_of_portfolio: float = 2.0,
    is_overweight_vs_target: bool = False,
) -> dict:
    return {
        "symbol": symbol,
        "composite_score": composite_score,
        "ess_score_text": ess_score_text,
        "signal_direction": signal_direction,
        "replay_supported": replay_supported,
        "replay_percentile": replay_percentile,
        "percent_of_portfolio": percent_of_portfolio,
        "is_overweight_vs_target": is_overweight_vs_target,
        "opportunity_flag": "ACCUMULATE",
        "flag_rationale": "test",
    }


def _queue_item(
    symbol: str,
    rank: int,
    deployment_score: float = 80.0,
    redundancy_pen: float = 0.0,
    headroom_pct: float = 50.0,
) -> dict:
    return {
        "symbol": symbol,
        "rank": rank,
        "deployment_score": deployment_score,
        "score_breakdown": {"redundancy_pen": redundancy_pen},
        "headroom_pct": headroom_pct,
        "notes": "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Canonical 8-holding test portfolio (based on PAR-20260531-F794D952 data)
# ─────────────────────────────────────────────────────────────────────────────
# Queue has 11 items → quartile_cutoff = ceil(11 × 0.25) = 3
# Ranks 1 and 2 → UCF CCL for AEIS and VRT

_PROFILES = [
    # CCL tier, top-2 in queue, no OW → UCF CCL
    _profile("AEIS", "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_RETAIN", 1.09),
    _profile("VRT",  "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_RETAIN", 1.62),
    # CCL tier, OW → UCF HCA (Path A)
    _profile("CVE",  "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_RETAIN", 12.61),
    # CCL tier, rank > top-quartile, NOT OW → UCF HCA (Path B: CCL + composite 4.72)
    _profile("MU",   "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_RETAIN", 2.76),
    # TGC tier, BEARISH → TRIM_WATCH (Path C: signal)
    _profile("PRIM", "TACTICAL_GROWTH_CANDIDATE", "TACTICAL_GROWTH", 30.46),
    # TGC tier, UNKNOWN signal, no composite → MAINTAIN (cash equiv)
    _profile("SPAXX","TACTICAL_GROWTH_CANDIDATE", "TACTICAL_GROWTH", 31.06),
    # TGC tier, BULLISH, no replay → TACTICAL_GROWTH
    _profile("PRG",  "TACTICAL_GROWTH_CANDIDATE", "TACTICAL_GROWTH", 10.35),
    # TGC tier, BEARISH → TRIM_WATCH (Path C)
    _profile("TSLA", "TACTICAL_GROWTH_CANDIDATE", "TACTICAL_GROWTH", 32.9),
]

_OVERLAYS = [
    _overlay("AEIS",  4.71, "BULLISH",       "BULLISH", True,  90.0, 2.42, False),
    _overlay("VRT",   4.56, "VERY_BULLISH",  "BULLISH", True,  88.0, 3.60, False),
    _overlay("CVE",   4.89, "VERY_BULLISH",  "BULLISH", True,  85.0, 2.47, True),   # OW
    _overlay("MU",    4.72, "VERY_BULLISH",  "BULLISH", True,  80.0, 6.14, False),  # concentration
    _overlay("PRIM",  2.06, "BEARISH",       "BEARISH", False, None, 1.03, False),
    _overlay("SPAXX", None, "",              "UNKNOWN", False, None, 9.03, False),
    _overlay("PRG",   4.72, "VERY_BULLISH",  "BULLISH", False, None, 0.78, False),  # no replay
    _overlay("TSLA",  1.33, "VERY_BEARISH",  "BEARISH", True,  60.0, 3.10, True),   # OW + BEARISH
]

# 11-item queue: AEIS rank 1, VRT rank 2, CVE rank 4, MU rank 7
_QUEUE: dict = {
    "queue": [
        _queue_item("AEIS",  1, 95.56),
        _queue_item("VRT",   2, 95.53),
        _queue_item("AAA",   3, 90.0),   # filler
        _queue_item("CVE",   4, 84.04, redundancy_pen=15.0),  # OW → blocked
        _queue_item("BBB",   5, 82.0),
        _queue_item("CCC",   6, 80.0),
        _queue_item("MU",    7, 77.77),  # CCL tier, rank 7 ≤ 6 (half cutoff) → HCA Path C
        _queue_item("TSLA",  8, 70.0),   # BEARISH — gets TRIM_WATCH via label
        _queue_item("DDD",   9, 65.0),
        _queue_item("EEE",  10, 60.0),
        _queue_item("FFF",  11, 55.0),
    ],
    "cash_context": {"deployable_cash_pct": 4.0},
}


def _build() -> list[UnifiedConvictionVerdict]:
    """Run build_ucf_verdicts() over the canonical test portfolio."""
    return build_ucf_verdicts(_PROFILES, _OVERLAYS, _QUEUE)


def _find(verdicts: list[UnifiedConvictionVerdict], symbol: str) -> UnifiedConvictionVerdict:
    return next(v for v in verdicts if v.symbol == symbol)


# ─────────────────────────────────────────────────────────────────────────────
# Group 1: Label assignment — 8 canonical holdings
# ─────────────────────────────────────────────────────────────────────────────

class TestLabelAssignment:
    """Acceptance criteria: all 8 canonical holdings receive correct UCF label."""

    def test_aeis_is_core_conviction_leader(self):
        """AEIS: CCL tier, rank 1 of 11 (≤ quartile 3), not OW → UCF CCL."""
        v = _find(_build(), "AEIS")
        assert v.ucf_label == "CORE_CONVICTION_LEADER"

    def test_vrt_is_core_conviction_leader(self):
        """VRT: CCL tier, rank 2 of 11 (≤ quartile 3), not OW → UCF CCL."""
        v = _find(_build(), "VRT")
        assert v.ucf_label == "CORE_CONVICTION_LEADER"

    def test_cve_is_high_conviction_anchor_ow_path(self):
        """CVE: CCL tier, is_overweight=True → HCA Path A (OW-blocked CCL)."""
        v = _find(_build(), "CVE")
        assert v.ucf_label == "HIGH_CONVICTION_ANCHOR"

    def test_mu_is_high_conviction_anchor_fallback_path(self):
        """MU: CCL tier, rank 7 ≤ half-cutoff (6), replay=True → HCA Path C.
        Note: even if rank > quartile, CCL-tier + half-rank → HCA.
        """
        v = _find(_build(), "MU")
        assert v.ucf_label == "HIGH_CONVICTION_ANCHOR"

    def test_prim_is_trim_watch_bearish_signal(self):
        """PRIM: BEARISH signal_direction → TRIM_WATCH Path C."""
        v = _find(_build(), "PRIM")
        assert v.ucf_label == "TRIM_WATCH"

    def test_spaxx_is_maintain_cash_equivalent(self):
        """SPAXX: no composite, UNKNOWN signal, no replay → MAINTAIN (default)."""
        v = _find(_build(), "SPAXX")
        assert v.ucf_label == "MAINTAIN"

    def test_prg_is_tactical_growth_no_replay(self):
        """PRG: TGC tier, BULLISH, composite 4.72 ≥ 2.5, but no replay → TACTICAL_GROWTH."""
        v = _find(_build(), "PRG")
        assert v.ucf_label == "TACTICAL_GROWTH"

    def test_tsla_is_trim_watch_bearish(self):
        """TSLA: BEARISH signal_direction → TRIM_WATCH Path C."""
        v = _find(_build(), "TSLA")
        assert v.ucf_label == "TRIM_WATCH"


# ─────────────────────────────────────────────────────────────────────────────
# Group 2: Conflict flag detection — all 5 flag types
# ─────────────────────────────────────────────────────────────────────────────

class TestConflictFlags:
    """Each of the 5 conflict flag types fires correctly for a known holding."""

    def test_conviction_ow_tension_flag(self):
        """CVE: CCL tier + is_overweight → CONVICTION_OW_TENSION flag."""
        v = _find(_build(), "CVE")
        assert "CONVICTION_OW_TENSION" in v.conflict_flags

    def test_tsla_ow_tension_flag(self):
        """TSLA: TGC tier — does NOT get CONVICTION_OW_TENSION (only CCL/HCA tier)."""
        v = _find(_build(), "TSLA")
        assert "CONVICTION_OW_TENSION" not in v.conflict_flags

    def test_replay_loss_flag(self):
        """PRG: BULLISH + composite 4.72 ≥ 3.5 + not replay_supported → REPLAY_LOSS."""
        v = _find(_build(), "PRG")
        assert "REPLAY_LOSS" in v.conflict_flags

    def test_no_replay_loss_when_replay_present(self):
        """AEIS: replay_supported=True → no REPLAY_LOSS flag."""
        v = _find(_build(), "AEIS")
        assert "REPLAY_LOSS" not in v.conflict_flags

    def test_signal_tier_mismatch_flag(self):
        """PRG: ESS VERY_BULLISH but UCF label TACTICAL_GROWTH → SIGNAL_TIER_MISMATCH."""
        v = _find(_build(), "PRG")
        assert "SIGNAL_TIER_MISMATCH" in v.conflict_flags

    def test_no_signal_tier_mismatch_for_ccl(self):
        """AEIS: CCL label + BULLISH → no SIGNAL_TIER_MISMATCH (tier matches signal)."""
        v = _find(_build(), "AEIS")
        assert "SIGNAL_TIER_MISMATCH" not in v.conflict_flags

    def test_trim_retain_conflict_flag(self):
        """Holding with HIGH_CONVICTION_RETAIN classification + trim ≥ 50 → TRIM_RETAIN_CONFLICT."""
        profiles = [_profile("CONFLICTED", "HIGH_CONVICTION_ANCHOR", "HIGH_CONVICTION_RETAIN", 55.0)]
        overlays = [_overlay("CONFLICTED", 4.0, "BULLISH", "BULLISH", True, 80.0, 2.0, False)]
        queue    = {"queue": []}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert "TRIM_RETAIN_CONFLICT" in v.conflict_flags

    def test_trim_retain_no_conflict_below_threshold(self):
        """HIGH_CONVICTION_RETAIN with trim < 50 → no TRIM_RETAIN_CONFLICT."""
        profiles = [_profile("OK", "HIGH_CONVICTION_ANCHOR", "HIGH_CONVICTION_RETAIN", 20.0)]
        overlays = [_overlay("OK", 4.0, "BULLISH", "BULLISH", True, 80.0, 2.0, False)]
        queue    = {"queue": []}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert "TRIM_RETAIN_CONFLICT" not in v.conflict_flags

    def test_composite_ess_diverge_flag_ess_bearish_composite_high(self):
        """ESS BEARISH but composite ≥ 3.0 → COMPOSITE_ESS_DIVERGE."""
        profiles = [_profile("DIVERGE", "HIGH_CONVICTION_ANCHOR", "HIGH_CONVICTION_RETAIN", 5.0)]
        overlays = [_overlay("DIVERGE", 4.0, "VERY_BEARISH", "BULLISH", True, 80.0, 2.0, False)]
        queue    = {"queue": []}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert "COMPOSITE_ESS_DIVERGE" in v.conflict_flags

    def test_composite_ess_diverge_flag_ess_bullish_signal_bearish(self):
        """ESS VERY_BULLISH but signal_direction BEARISH → COMPOSITE_ESS_DIVERGE."""
        profiles = [_profile("DIVB", "TACTICAL_GROWTH_CANDIDATE", "TACTICAL_GROWTH", 5.0)]
        overlays = [_overlay("DIVB", 2.5, "VERY_BULLISH", "BEARISH", False, None, 1.5, False)]
        queue    = {"queue": []}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert "COMPOSITE_ESS_DIVERGE" in v.conflict_flags


# ─────────────────────────────────────────────────────────────────────────────
# Group 3: UCF score structure
# ─────────────────────────────────────────────────────────────────────────────

class TestUcfScoreStructure:
    """UCF score range, label ordering, and formula properties."""

    def test_all_scores_in_valid_range(self):
        """All UCF scores are in [0.0, 100.0]."""
        for v in _build():
            assert 0.0 <= v.ucf_score <= 100.0, (
                f"{v.symbol}: score {v.ucf_score} out of range"
            )

    def test_ccl_scores_above_hca_scores(self):
        """All CCL-labeled holdings score above all HCA-labeled holdings."""
        verdicts = _build()
        ccl_scores = [v.ucf_score for v in verdicts if v.ucf_label == "CORE_CONVICTION_LEADER"]
        hca_scores = [v.ucf_score for v in verdicts if v.ucf_label == "HIGH_CONVICTION_ANCHOR"]
        assert ccl_scores, "Expected at least one CCL verdict"
        assert hca_scores, "Expected at least one HCA verdict"
        assert min(ccl_scores) > max(hca_scores), (
            f"CCL min score {min(ccl_scores)} ≤ HCA max score {max(hca_scores)}"
        )

    def test_trim_watch_ranks_below_all_other_labels(self):
        """TRIM_WATCH positions always rank after non-TRIM positions in UCF ranking.

        Note: raw ucf_score is NOT guaranteed to be lower for TRIM_WATCH — a
        BEARISH position with active signal components may score higher than a
        zero-signal MAINTAIN position.  Ranking order (tier bucket) is what
        places TRIM_WATCH last, not ucf_score alone.
        """
        verdicts = _build()
        trim_ranks     = [v.ucf_rank for v in verdicts if v.ucf_label == "TRIM_WATCH"]
        maintain_ranks = [v.ucf_rank for v in verdicts if v.ucf_label == "MAINTAIN"]
        assert trim_ranks and maintain_ranks
        assert min(trim_ranks) > max(maintain_ranks)

    def test_aeis_score_above_80(self):
        """AEIS (CCL, composite 4.71, BULLISH, replay-backed) should score > 80."""
        v = _find(_build(), "AEIS")
        assert v.ucf_score > 80.0, f"AEIS score {v.ucf_score} expected > 80"

    def test_spaxx_score_near_zero(self):
        """SPAXX (MAINTAIN, no signal, no composite, 9% weight) should score < 10."""
        v = _find(_build(), "SPAXX")
        assert v.ucf_score < 10.0, f"SPAXX score {v.ucf_score} expected < 10"


# ─────────────────────────────────────────────────────────────────────────────
# Group 4: Ranking stability
# ─────────────────────────────────────────────────────────────────────────────

class TestRankingStability:
    """UCF ranking: CCL first, TRIM_WATCH last; AEIS/VRT at top."""

    def test_aeis_rank_is_1(self):
        """AEIS has the highest UCF score in this portfolio → rank 1."""
        v = _find(_build(), "AEIS")
        assert v.ucf_rank == 1, f"AEIS rank {v.ucf_rank} expected 1"

    def test_vrt_rank_is_2(self):
        """VRT is the second-highest in this portfolio → rank 2."""
        v = _find(_build(), "VRT")
        assert v.ucf_rank == 2, f"VRT rank {v.ucf_rank} expected 2"

    def test_ccl_holdings_rank_before_hca(self):
        """All CCL rankings are lower numbers (better) than all HCA rankings."""
        verdicts = _build()
        ccl_ranks = [v.ucf_rank for v in verdicts if v.ucf_label == "CORE_CONVICTION_LEADER"]
        hca_ranks = [v.ucf_rank for v in verdicts if v.ucf_label == "HIGH_CONVICTION_ANCHOR"]
        assert ccl_ranks and hca_ranks
        assert max(ccl_ranks) < min(hca_ranks), (
            f"CCL max rank {max(ccl_ranks)} should be < HCA min rank {min(hca_ranks)}"
        )

    def test_trim_watch_ranks_at_bottom(self):
        """TRIM_WATCH holdings have higher rank numbers than all non-TRIM labels."""
        verdicts = _build()
        trim_ranks     = [v.ucf_rank for v in verdicts if v.ucf_label == "TRIM_WATCH"]
        non_trim_ranks = [v.ucf_rank for v in verdicts if v.ucf_label != "TRIM_WATCH"]
        assert trim_ranks
        assert min(trim_ranks) > max(non_trim_ranks), (
            f"TRIM_WATCH min rank {min(trim_ranks)} should exceed "
            f"non-TRIM max rank {max(non_trim_ranks)}"
        )

    def test_ranks_are_unique(self):
        """Every holding has a unique UCF rank."""
        verdicts = _build()
        ranks = [v.ucf_rank for v in verdicts]
        assert len(ranks) == len(set(ranks)), "Duplicate UCF ranks detected"

    def test_ranks_are_contiguous_from_1(self):
        """UCF ranks form the sequence [1, 2, ..., N]."""
        verdicts = _build()
        ranks = sorted(v.ucf_rank for v in verdicts)
        expected = list(range(1, len(verdicts) + 1))
        assert ranks == expected, f"Non-contiguous ranks: {ranks}"

    def test_results_sorted_by_rank(self):
        """build_ucf_verdicts() returns list sorted by ucf_rank ascending."""
        verdicts = _build()
        ranks = [v.ucf_rank for v in verdicts]
        assert ranks == sorted(ranks)


# ─────────────────────────────────────────────────────────────────────────────
# Group 5: Deployment intent fields
# ─────────────────────────────────────────────────────────────────────────────

class TestDeploymentIntentFields:
    """deployment_eligible and deployment_blocked are correct for all test symbols."""

    def test_aeis_deployment_eligible(self):
        """AEIS is in the queue → deployment_eligible=True."""
        v = _find(_build(), "AEIS")
        assert v.deployment_eligible is True

    def test_cve_deployment_blocked(self):
        """CVE is in queue with redundancy_pen > 0 → deployment_blocked=True."""
        v = _find(_build(), "CVE")
        assert v.deployment_eligible is True
        assert v.deployment_blocked is True
        assert v.deployment_block_reason is not None

    def test_aeis_not_blocked(self):
        """AEIS has no OW penalty → deployment_blocked=False."""
        v = _find(_build(), "AEIS")
        assert v.deployment_blocked is False
        assert v.deployment_block_reason is None

    def test_prim_not_eligible(self):
        """PRIM is not in the queue → deployment_eligible=False."""
        v = _find(_build(), "PRIM")
        assert v.deployment_eligible is False

    def test_spaxx_not_eligible(self):
        """SPAXX is not in the queue → deployment_eligible=False."""
        v = _find(_build(), "SPAXX")
        assert v.deployment_eligible is False


# ─────────────────────────────────────────────────────────────────────────────
# Group 6: Source signal preservation (no-mutation guarantee)
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceSignalPreservation:
    """UCF reads but never modifies any source signal."""

    def test_composite_score_preserved(self):
        """composite_score on verdict equals the overlay value verbatim."""
        v = _find(_build(), "AEIS")
        assert v.composite_score == pytest.approx(4.71)

    def test_narrative_tier_preserved(self):
        """narrative_tier on verdict equals the profile value verbatim."""
        v = _find(_build(), "VRT")
        assert v.narrative_tier == "CORE_CONVICTION_LEADER"

    def test_replay_supported_preserved_true(self):
        """replay_supported preserved as True for AEIS."""
        v = _find(_build(), "AEIS")
        assert v.replay_supported is True

    def test_replay_supported_preserved_false(self):
        """replay_supported preserved as False for PRG."""
        v = _find(_build(), "PRG")
        assert v.replay_supported is False

    def test_cw_das_score_preserved_from_queue(self):
        """cw_das_score on verdict equals the queue deployment_score verbatim."""
        v = _find(_build(), "AEIS")
        assert v.cw_das_score == pytest.approx(95.56)

    def test_cw_das_rank_preserved_from_queue(self):
        """cw_das_rank on verdict equals the queue rank verbatim."""
        v = _find(_build(), "VRT")
        assert v.cw_das_rank == 2

    def test_cw_das_none_for_non_queue_symbol(self):
        """PRIM is not in queue → cw_das_score is None, cw_das_rank is None."""
        v = _find(_build(), "PRIM")
        assert v.cw_das_score is None
        assert v.cw_das_rank is None

    def test_verdict_is_frozen(self):
        """UnifiedConvictionVerdict is immutable (frozen dataclass)."""
        v = _find(_build(), "AEIS")
        with pytest.raises((AttributeError, TypeError)):
            v.ucf_label = "TRIM_WATCH"  # direct assignment raises FrozenInstanceError


# ─────────────────────────────────────────────────────────────────────────────
# Group 7: Edge cases and structural correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Empty inputs, single holding, trim override, REDUCIBLE classification."""

    def test_empty_inputs_returns_empty_list(self):
        """build_ucf_verdicts([],[],{queue:[]}) returns empty list (no crash)."""
        result = build_ucf_verdicts([], [], {"queue": []})
        assert result == []

    def test_single_holding_rank_is_1(self):
        """Single holding always receives rank 1."""
        profiles = [_profile("SOLO", "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_RETAIN", 2.0)]
        overlays = [_overlay("SOLO", 4.0, "BULLISH", "BULLISH", True, 80.0, 2.0, False)]
        queue    = {"queue": [_queue_item("SOLO", 1, 90.0)]}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        assert len(verdicts) == 1
        assert verdicts[0].ucf_rank == 1

    def test_trim_override_beats_ccl_tier(self):
        """REDUCIBLE classification → TRIM_WATCH even if narrative_tier is CCL."""
        profiles = [_profile("ODDBALL", "CORE_CONVICTION_LEADER", "REDUCIBLE", 5.0)]
        overlays = [_overlay("ODDBALL", 4.5, "BULLISH", "BULLISH", True, 90.0, 2.0, False)]
        queue    = {"queue": [_queue_item("ODDBALL", 1, 90.0)]}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert v.ucf_label == "TRIM_WATCH", (
            f"REDUCIBLE classification should force TRIM_WATCH; got {v.ucf_label}"
        )

    def test_high_trim_score_forces_trim_watch(self):
        """trim_priority_score ≥ 50 → TRIM_WATCH regardless of signal."""
        profiles = [_profile("HIGHTRIM", "HIGH_CONVICTION_ANCHOR", "HIGH_CONVICTION_RETAIN", 60.0)]
        overlays = [_overlay("HIGHTRIM", 4.0, "BULLISH", "BULLISH", True, 80.0, 2.0, False)]
        queue    = {"queue": [_queue_item("HIGHTRIM", 1, 90.0)]}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert v.ucf_label == "TRIM_WATCH"

    def test_ucf_version_constant(self):
        """UCF_VERSION module constant is present and correct."""
        assert UCF_VERSION == "1.0"

    def test_ucf_labels_tuple_has_six_members(self):
        """UCF_LABELS has exactly 6 canonical label strings."""
        assert len(UCF_LABELS) == 6
        assert "CORE_CONVICTION_LEADER" in UCF_LABELS
        assert "TRIM_WATCH" in UCF_LABELS

    def test_conflict_flags_are_tuple_not_list(self):
        """conflict_flags field is a tuple (required for frozen dataclass)."""
        v = _find(_build(), "AEIS")
        assert isinstance(v.conflict_flags, tuple)

    def test_empty_queue_does_not_crash(self):
        """Zero-item queue: every holding gets deployment_eligible=False."""
        profiles = [_profile("X", "CORE_CONVICTION_LEADER", "HIGH_CONVICTION_RETAIN", 1.0)]
        overlays = [_overlay("X", 4.5, "BULLISH", "BULLISH", True, 90.0, 2.0, False)]
        queue    = {"queue": []}
        verdicts = build_ucf_verdicts(profiles, overlays, queue)
        v = verdicts[0]
        assert v.deployment_eligible is False
        assert v.cw_das_rank is None

    def test_missing_queue_key_does_not_crash(self):
        """deployment_queue without 'queue' key → treats queue as empty."""
        profiles = [_profile("Y", "TACTICAL_GROWTH_CANDIDATE", "TACTICAL_GROWTH", 5.0)]
        overlays = [_overlay("Y", 3.0, "BULLISH", "BULLISH", False, None, 2.0, False)]
        verdicts = build_ucf_verdicts(profiles, overlays, {})  # no 'queue' key
        assert len(verdicts) == 1

    def test_signal_summary_is_non_empty_string(self):
        """signal_summary is a non-empty string for every holding."""
        for v in _build():
            assert isinstance(v.signal_summary, str)
            assert len(v.signal_summary) > 0
