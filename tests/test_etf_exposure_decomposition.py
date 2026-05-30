from __future__ import annotations

import csv
from dataclasses import replace

import pytest

from src.portfolio.alignment import compute_alignment, compute_concentration
from src.portfolio.exposure_decomposition import build_holding_decomposition
from src.portfolio.models import PortfolioHolding
from src.portfolio.recommendations import generate_recommendations


def _write_targets(path, rows):
    headers = [
        "target_id", "snapshot_date", "recalculation_id", "node_key", "node_label",
        "parent_key", "asset_class", "geography", "market_structure", "mega_subtier",
        "hierarchy_depth", "target_pct_of_parent", "target_pct_of_total",
        "prior_target_pct_of_total", "delta_pct", "confidence_score", "evidence_summary",
        "evidence_ids", "methodology_basis_ref", "policy_bounded",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _qqq_holding(percent: float = 10.0) -> PortfolioHolding:
    decomposition = build_holding_decomposition(
        symbol="QQQ",
        security_type="ETF",
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket="LARGE",
        mega_subtier="N/A",
        sector="Technology",
        timestamp_utc="2026-05-27T00:00:00Z",
    )
    return PortfolioHolding(
        portfolio_snapshot_id="PSNAP-TEST",
        snapshot_date="2026-05-27",
        account_name="Test",
        symbol="QQQ",
        description="Invesco QQQ Trust",
        quantity=1.0,
        market_value=percent * 1000.0,
        percent_of_portfolio=percent,
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket="LARGE",
        mega_subtier="N/A",
        sector="Technology",
        industry="ALL",
        security_type="ETF",
        cost_basis=None,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc="2026-05-27T00:00:00Z",
        exposure_geography_mix=decomposition.exposure_geography_mix,
        exposure_market_cap_mix=decomposition.exposure_market_cap_mix,
        exposure_mega_subtier_mix=decomposition.exposure_mega_subtier_mix,
        exposure_sector_mix=decomposition.exposure_sector_mix,
        exposure_style_mix=decomposition.exposure_style_mix,
        decomposition_method=decomposition.decomposition_method,
        decomposition_version=decomposition.decomposition_version,
        decomposition_timestamp=decomposition.decomposition_timestamp,
        decomposition_confidence=decomposition.decomposition_confidence,
    )


def test_qqq_decomposition_spreads_across_mega_subtiers() -> None:
    decomposition = build_holding_decomposition(
        symbol="QQQ",
        security_type="ETF",
        asset_class="EQUITIES",
        geography="US",
        market_cap_bucket="LARGE",
        mega_subtier="N/A",
        sector="Technology",
        timestamp_utc="2026-05-27T00:00:00Z",
    )

    assert decomposition.decomposition_method == "HEURISTIC_REGISTRY_V1"
    assert decomposition.decomposition_confidence >= 0.7
    assert decomposition.exposure_market_cap_mix[0][0] == "MEGA"
    assert decomposition.exposure_mega_subtier_mix[0][0] == "HYPER_MEGA"


def test_alignment_uses_effective_etf_exposure(tmp_path) -> None:
    targets = tmp_path / "targets.csv"
    overlays = tmp_path / "overlays.csv"
    _write_targets(
        targets,
        [
            {
                "target_id": "T1",
                "snapshot_date": "2026-05-27",
                "recalculation_id": "REC-TEST",
                "node_key": "EQUITIES",
                "node_label": "Equities",
                "parent_key": "",
                "asset_class": "EQUITIES",
                "geography": "",
                "market_structure": "",
                "mega_subtier": "",
                "hierarchy_depth": 1,
                "target_pct_of_parent": 100,
                "target_pct_of_total": 100,
                "prior_target_pct_of_total": "",
                "delta_pct": "",
                "confidence_score": 1,
                "evidence_summary": "seed",
                "evidence_ids": "",
                "methodology_basis_ref": "seed",
                "policy_bounded": "False",
            },
            {
                "target_id": "T2",
                "snapshot_date": "2026-05-27",
                "recalculation_id": "REC-TEST",
                "node_key": "EQUITIES.US.MEGA",
                "node_label": "US Mega Cap",
                "parent_key": "EQUITIES.US",
                "asset_class": "EQUITIES",
                "geography": "US",
                "market_structure": "MEGA",
                "mega_subtier": "",
                "hierarchy_depth": 3,
                "target_pct_of_parent": 95,
                "target_pct_of_total": 95,
                "prior_target_pct_of_total": "",
                "delta_pct": "",
                "confidence_score": 1,
                "evidence_summary": "seed",
                "evidence_ids": "",
                "methodology_basis_ref": "seed",
                "policy_bounded": "False",
            },
            {
                "target_id": "T3",
                "snapshot_date": "2026-05-27",
                "recalculation_id": "REC-TEST",
                "node_key": "EQUITIES.US.MEGA.EXTENDED_MEGA",
                "node_label": "Extended Mega",
                "parent_key": "EQUITIES.US.MEGA",
                "asset_class": "EQUITIES",
                "geography": "US",
                "market_structure": "MEGA",
                "mega_subtier": "EXTENDED_MEGA",
                "hierarchy_depth": 4,
                "target_pct_of_parent": 1,
                "target_pct_of_total": 1,
                "prior_target_pct_of_total": "",
                "delta_pct": "",
                "confidence_score": 1,
                "evidence_summary": "seed",
                "evidence_ids": "",
                "methodology_basis_ref": "seed",
                "policy_bounded": "False",
            },
        ],
    )
    overlays.write_text("overlay_id,effective_date,expiry_date,dimension_type,dimension_value,overlay_pct,max_overlay_pct,persistence_score,momentum_signal,replay_support_ids,notes,status\n", encoding="utf-8")

    holdings = [_qqq_holding()]
    alignment = compute_alignment(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        holdings=holdings,
        targets_csv=str(targets),
        overlays_csv=str(overlays),
    )

    mega = next(row for row in alignment if row.node_key == "EQUITIES.US.MEGA")
    extended = next(row for row in alignment if row.node_key == "EQUITIES.US.MEGA.EXTENDED_MEGA")

    assert mega.direct_actual_pct == 0.0
    assert mega.etf_derived_actual_pct == pytest.approx(9.5, rel=1e-3)
    assert mega.effective_actual_pct == pytest.approx(9.5, rel=1e-3)
    assert extended.etf_derived_actual_pct == pytest.approx(1.2, rel=1e-3)
    assert extended.effective_actual_pct == pytest.approx(1.2, rel=1e-3)

    concentration = compute_concentration(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        holdings=holdings,
    )
    assert concentration.mega_subtier_effective_pct == pytest.approx(4.8, rel=1e-3)
    assert concentration.mega_subtier_direct_pct == 0.0
    assert concentration.mega_subtier_etf_derived_pct == pytest.approx(4.8, rel=1e-3)


def test_recommendations_do_not_build_extended_mega_when_effective_exposure_is_present(tmp_path) -> None:
    targets = tmp_path / "targets.csv"
    overlays = tmp_path / "overlays.csv"
    _write_targets(
        targets,
        [
            {
                "target_id": "T1",
                "snapshot_date": "2026-05-27",
                "recalculation_id": "REC-TEST",
                "node_key": "EQUITIES",
                "node_label": "Equities",
                "parent_key": "",
                "asset_class": "EQUITIES",
                "geography": "",
                "market_structure": "",
                "mega_subtier": "",
                "hierarchy_depth": 1,
                "target_pct_of_parent": 100,
                "target_pct_of_total": 100,
                "prior_target_pct_of_total": "",
                "delta_pct": "",
                "confidence_score": 1,
                "evidence_summary": "seed",
                "evidence_ids": "",
                "methodology_basis_ref": "seed",
                "policy_bounded": "False",
            },
            {
                "target_id": "T2",
                "snapshot_date": "2026-05-27",
                "recalculation_id": "REC-TEST",
                "node_key": "EQUITIES.US.MEGA.EXTENDED_MEGA",
                "node_label": "Extended Mega",
                "parent_key": "EQUITIES.US.MEGA",
                "asset_class": "EQUITIES",
                "geography": "US",
                "market_structure": "MEGA",
                "mega_subtier": "EXTENDED_MEGA",
                "hierarchy_depth": 4,
                "target_pct_of_parent": 1,
                "target_pct_of_total": 1,
                "prior_target_pct_of_total": "",
                "delta_pct": "",
                "confidence_score": 1,
                "evidence_summary": "seed",
                "evidence_ids": "",
                "methodology_basis_ref": "seed",
                "policy_bounded": "False",
            },
        ],
    )
    overlays.write_text("overlay_id,effective_date,expiry_date,dimension_type,dimension_value,overlay_pct,max_overlay_pct,persistence_score,momentum_signal,replay_support_ids,notes,status\n", encoding="utf-8")

    holdings = [_qqq_holding()]
    alignment = compute_alignment(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        holdings=holdings,
        targets_csv=str(targets),
        overlays_csv=str(overlays),
    )
    concentration = compute_concentration(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        holdings=holdings,
    )
    recs = generate_recommendations(
        analysis_run_id="RUN-TEST",
        portfolio_snapshot_id="PSNAP-TEST",
        holdings=holdings,
        alignment_results=alignment,
        concentration=concentration,
        overlays=[],
    )

    assert not any("Build Extended Mega" in rec.title for rec in recs)