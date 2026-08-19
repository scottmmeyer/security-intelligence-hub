from __future__ import annotations

import json

from src.allocation.models import (
    AllocationEvidence,
    AllocationRecommendation,
    AllocationRecalculationSnapshot,
    StrategicAllocationTarget,
)
from src.history.allocation_manager import AllocationStoragePaths, publish_proposed_targets, save_proposed_targets


def _sample_target() -> StrategicAllocationTarget:
    return StrategicAllocationTarget(
        target_id="T-1",
        snapshot_date="2026-08-19",
        recalculation_id="RECALC-20260819-01",
        node_key="EQUITIES",
        node_label="Equities",
        parent_key=None,
        asset_class="EQUITIES",
        geography=None,
        market_structure=None,
        mega_subtier=None,
        hierarchy_depth=1,
        target_pct_of_parent=100.0,
        target_pct_of_total=88.0,
        prior_target_pct_of_total=85.0,
        delta_pct=3.0,
        confidence_score=0.8,
        evidence_summary="Replay and methodology",
        evidence_ids=("EV-1",),
        methodology_basis_ref="EQUITIES",
        policy_bounded=True,
    )


def _sample_recommendation() -> AllocationRecommendation:
    return AllocationRecommendation(
        recommendation_id="AR-1",
        snapshot_date="2026-08-19",
        policy_id="POL-1",
        recalculation_id="RECALC-20260819-01",
        node_key="EQUITIES",
        asset_class="EQUITIES",
        strategic_target_pct=88.0,
        tactical_overlay_pct=0.0,
        effective_target_pct=88.0,
        is_policy_capped=False,
        policy_ceiling=80.0,
        drift_from_prior=3.0,
    )


def _sample_snapshot() -> AllocationRecalculationSnapshot:
    return AllocationRecalculationSnapshot(
        recalculation_id="RECALC-20260819-01",
        recalculation_date="2026-08-19",
        prior_recalculation_id="RECALC-20260818-01",
        triggered_by="MANUAL",
        policy_version="v1",
        evidence_ids=("EV-1",),
        change_summary=("EQUITIES +3.0%",),
        unchanged_summary="No unchanged nodes.",
        confidence_summary={"EQUITIES": 0.8},
        total_allocation_valid=False,
        notes="validator persistence test",
    )


def _sample_validation_results() -> dict[str, list[str]]:
    return {
        "hierarchy_sums": [],
        "policy_bounds": ["EQUITIES exceeds ceiling"],
        "tactical_overflow": [],
        "overlay_staleness": [],
        "recalculation_churn": [],
        "evidence_alignment": [],
        "concentration_ceilings": ["Combined MICRO cap exposure exceeds max_micro_cap_pct"],
        "lineage_completeness": [],
    }


def test_save_proposed_targets_persists_validator_results(tmp_path) -> None:
    paths = AllocationStoragePaths(base_dir=tmp_path / "data")

    save_proposed_targets(
        [_sample_target()],
        _sample_snapshot(),
        [_sample_recommendation()],
        validation_results=_sample_validation_results(),
        paths=paths,
    )

    payload = json.loads(paths.proposed_snapshot.read_text(encoding="utf-8"))
    vr = payload.get("validator_results")

    assert isinstance(vr, dict)
    assert set(vr.keys()) == {
        "hierarchy_sums",
        "policy_bounds",
        "tactical_overflow",
        "overlay_staleness",
        "recalculation_churn",
        "evidence_alignment",
        "concentration_ceilings",
        "lineage_completeness",
    }
    assert vr["hierarchy_sums"]["status"] == "PASS"
    assert vr["policy_bounds"]["status"] == "FAIL"
    assert "exceeds ceiling" in vr["policy_bounds"]["message"]
    assert payload.get("target_model_scope") == "PROPOSED_NON_COMMIT"
    assert isinstance(payload.get("target_model_fingerprint"), str)
    assert payload.get("target_model_fingerprint")


def test_publish_proposed_targets_persists_validator_results(tmp_path) -> None:
    paths = AllocationStoragePaths(base_dir=tmp_path / "data")
    snapshot = _sample_snapshot()

    publish_proposed_targets(
        [_sample_target()],
        snapshot,
        [_sample_recommendation()],
        [
            AllocationEvidence(
                evidence_id="EV-1",
                evidence_date="2026-08-19",
                evidence_type="REPLAY_OUTPERFORMANCE",
                node_key="EQUITIES",
                asset_class="EQUITIES",
                metric_name="relative_return_90d",
                metric_value=1.0,
                benchmark_comparison="SPY",
                significance="HIGH",
                replay_id="RP-1",
                human_readable="test evidence",
            )
        ],
        validation_results=_sample_validation_results(),
        paths=paths,
    )

    snapshot_path = paths.snapshots_dir / f"{snapshot.recalculation_id}.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    vr = payload.get("validator_results")

    assert isinstance(vr, dict)
    assert vr["concentration_ceilings"]["status"] == "FAIL"
    assert "Combined MICRO cap exposure" in vr["concentration_ceilings"]["message"]
    assert vr["lineage_completeness"]["status"] == "PASS"
    assert payload.get("target_model_scope") == "ACTIVE_PUBLISHED"
    assert isinstance(payload.get("target_model_fingerprint"), str)
    assert payload.get("target_model_fingerprint")
