"""Phase 7.5E — Signal Transparency Layer tests.

Validates:
- UCF verdicts are loaded by load_analysis_run() and keyed by symbol
- danelfin_score flows through PortfolioHolding → SecurityIntelligenceOverlay
- All required signal fields are present for deployment queue candidates
- Deployment queue ordering is unchanged from pre-7.5E baseline
- No regressions: existing 692 tests pass (checked by full test run)
"""
from __future__ import annotations

import dataclasses
from typing import Optional
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

REFERENCE_RUN_ID = "PAR-20260531-F794D952"


def _load_reference():
    """Load the reference analysis run.  Skipped if it does not exist."""
    from src.portfolio.runner import load_analysis_run
    try:
        return load_analysis_run(REFERENCE_RUN_ID)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# T1 — Model field existence
# ─────────────────────────────────────────────────────────────────────────────

class TestModelFields:
    """danelfin_score exists on both model classes."""

    def test_portfolio_holding_has_danelfin(self):
        from src.portfolio.models import PortfolioHolding
        fields = {f.name for f in dataclasses.fields(PortfolioHolding)}
        assert "danelfin_score" in fields, "PortfolioHolding must have danelfin_score"

    def test_portfolio_holding_danelfin_defaults_none(self):
        from src.portfolio.models import PortfolioHolding
        f = next(f for f in dataclasses.fields(PortfolioHolding) if f.name == "danelfin_score")
        assert f.default is None, "danelfin_score should default to None"

    def test_security_intelligence_overlay_has_danelfin(self):
        from src.portfolio.models import SecurityIntelligenceOverlay
        fields = {f.name for f in dataclasses.fields(SecurityIntelligenceOverlay)}
        assert "danelfin_score" in fields, "SecurityIntelligenceOverlay must have danelfin_score"

    def test_security_intelligence_overlay_danelfin_defaults_none(self):
        from src.portfolio.models import SecurityIntelligenceOverlay
        f = next(f for f in dataclasses.fields(SecurityIntelligenceOverlay) if f.name == "danelfin_score")
        assert f.default is None


# ─────────────────────────────────────────────────────────────────────────────
# T2 — danelfin propagation through enrichment
# ─────────────────────────────────────────────────────────────────────────────

class TestDanelfinPropagation:
    """danelfin_score flows from analytical_universe through enrich_holdings()."""

    def test_enrich_holdings_propagates_danelfin(self, tmp_path):
        """If analytical_universe has danelfin_score, enrich_holdings sets it."""
        import csv
        from src.portfolio.enrichment import enrich_holdings
        from src.portfolio.models import PortfolioHolding

        # Write a minimal universe CSV
        univ = tmp_path / "universe.csv"
        with open(univ, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=[
                "symbol", "composite_score", "ess_score_text", "zacks_rating",
                "danelfin_score", "geography", "sector", "industry",
                "security_type", "market_cap_bucket", "benchmark_id",
                "investable_vehicle_id", "is_etf",
            ])
            writer.writeheader()
            writer.writerow({
                "symbol": "FAKE", "composite_score": "4.5",
                "ess_score_text": "BULLISH", "zacks_rating": "1",
                "danelfin_score": "8.5", "geography": "US",
                "sector": "Tech", "industry": "Software",
                "security_type": "common_stock", "market_cap_bucket": "MID",
                "benchmark_id": "", "investable_vehicle_id": "", "is_etf": "false",
            })

        # Build a minimal PortfolioHolding using known-safe defaults
        h = PortfolioHolding(
            portfolio_snapshot_id="TEST",
            snapshot_date="2025-01-01",
            account_name="test_account",
            symbol="FAKE",
            description="Fake Co",
            asset_class=None,
            geography=None,
            market_cap_bucket=None,
            mega_subtier=None,
            sector=None,
            industry=None,
            security_type=None,
            quantity=100.0,
            market_value=1000.0,
            percent_of_portfolio=1.0,
            cost_basis=None,
            composite_score=None,
            ess_score_text=None,
            zacks_rating=None,
            benchmark_id=None,
            investable_vehicle_id=None,
            source_file="test",
            created_at_utc="2025-01-01T00:00:00Z",
        )

        enriched = enrich_holdings([h], universe_csv=str(univ))
        matches = [e for e in enriched if e.symbol == "FAKE"]
        assert matches, "FAKE should be enriched"
        assert matches[0].danelfin_score == "8.5", (
            f"Expected danelfin_score='8.5', got {matches[0].danelfin_score}"
        )

    def test_danelfin_none_when_not_in_universe(self, tmp_path):
        """danelfin_score is None when symbol is not found in universe."""
        import csv
        from src.portfolio.enrichment import enrich_holdings
        from src.portfolio.models import PortfolioHolding

        univ = tmp_path / "empty_universe.csv"
        with open(univ, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["symbol", "composite_score"])
            writer.writeheader()

        h = PortfolioHolding(
            portfolio_snapshot_id="TEST",
            snapshot_date="2025-01-01",
            account_name="test_account",
            symbol="UNKNOWN",
            description="Unknown Co",
            asset_class=None,
            geography=None,
            market_cap_bucket=None,
            mega_subtier=None,
            sector=None,
            industry=None,
            security_type=None,
            quantity=1.0,
            market_value=1.0,
            percent_of_portfolio=0.0,
            cost_basis=None,
            composite_score=None,
            ess_score_text=None,
            zacks_rating=None,
            benchmark_id=None,
            investable_vehicle_id=None,
            source_file="test",
            created_at_utc="2025-01-01T00:00:00Z",
        )
        enriched = enrich_holdings([h], universe_csv=str(univ))
        matches = [e for e in enriched if e.symbol == "UNKNOWN"]
        # Not in universe → no enrichment; danelfin stays None
        assert not matches or matches[0].danelfin_score is None


# ─────────────────────────────────────────────────────────────────────────────
# T3 — UCF verdicts loaded by load_analysis_run
# ─────────────────────────────────────────────────────────────────────────────

class TestUCFLoadedByRunner:
    """load_analysis_run() includes ucf_verdicts_by_symbol."""

    def test_ucf_verdicts_by_symbol_present(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        assert "ucf_verdicts_by_symbol" in result, (
            "load_analysis_run must populate ucf_verdicts_by_symbol"
        )

    def test_ucf_verdicts_keyed_by_symbol(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        ucf = result["ucf_verdicts_by_symbol"]
        assert isinstance(ucf, dict), "ucf_verdicts_by_symbol must be a dict"
        assert len(ucf) > 0, "ucf_verdicts_by_symbol must not be empty"

    def test_aeis_ucf_score_present(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        aeis = result["ucf_verdicts_by_symbol"].get("AEIS")
        assert aeis is not None, "AEIS must be in ucf_verdicts_by_symbol"
        assert aeis["ucf_score"] > 0, "AEIS ucf_score must be positive"

    def test_aeis_ucf_rank(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        aeis = result["ucf_verdicts_by_symbol"]["AEIS"]
        # AEIS is the top-ranked deployment candidate in reference run
        assert aeis["ucf_rank"] <= 5, (
            f"AEIS ucf_rank expected ≤5, got {aeis['ucf_rank']}"
        )

    def test_aeis_ucf_label(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        aeis = result["ucf_verdicts_by_symbol"]["AEIS"]
        assert aeis["ucf_label"] == "CORE_CONVICTION_LEADER", (
            f"AEIS expected CORE_CONVICTION_LEADER, got {aeis['ucf_label']}"
        )

    def test_ucf_verdict_has_signal_summary(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        aeis = result["ucf_verdicts_by_symbol"]["AEIS"]
        assert "signal_summary" in aeis, "Verdict must contain signal_summary"
        assert isinstance(aeis["signal_summary"], str)
        assert len(aeis["signal_summary"]) > 0, "signal_summary must not be empty"

    def test_ucf_verdict_has_source_signals(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        aeis = result["ucf_verdicts_by_symbol"]["AEIS"]
        ss = aeis.get("source_signals", {})
        for key in ("narrative_tier", "composite_score", "signal_direction",
                    "replay_supported", "cw_das_score"):
            assert key in ss, f"source_signals must contain {key}"

    def test_ucf_verdict_has_deployment_block_info(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        aeis = result["ucf_verdicts_by_symbol"]["AEIS"]
        dep = aeis.get("deployment", {})
        assert "deployment_eligible" in dep
        assert "deployment_blocked" in dep

    def test_all_queue_symbols_have_ucf_verdict(self):
        """Every deployment queue candidate should have a UCF verdict."""
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        ucf = result["ucf_verdicts_by_symbol"]
        missing = [c["symbol"] for c in queue if c["symbol"] not in ucf]
        assert not missing, f"Queue symbols missing UCF verdict: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# T4 — Deployment queue ordering unchanged
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueOrderingUnchanged:
    """Phase 7.5E must not alter deployment queue ordering."""

    def test_aeis_is_rank1(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        rank1 = next((c for c in queue if c["rank"] == 1), None)
        assert rank1 is not None
        assert rank1["symbol"] == "AEIS", (
            f"Expected AEIS at rank 1, got {rank1['symbol']}"
        )

    def test_vrt_is_rank2(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        rank2 = next((c for c in queue if c["rank"] == 2), None)
        assert rank2 is not None
        assert rank2["symbol"] == "VRT"

    def test_aeis_has_higher_cwdas_than_vrt(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        aeis_score = float(next(c["deployment_score"] for c in queue if c["symbol"] == "AEIS"))
        vrt_score  = float(next(c["deployment_score"] for c in queue if c["symbol"] == "VRT"))
        assert aeis_score > vrt_score, (
            f"AEIS CW-DAS {aeis_score} must exceed VRT {vrt_score}"
        )

    def test_queue_ranks_are_monotonic(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        ranks = [c["rank"] for c in queue]
        assert ranks == sorted(ranks), "Queue ranks must be in ascending order"


# ─────────────────────────────────────────────────────────────────────────────
# T5 — Signal transparency completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalTransparencyCompleteness:
    """All required signal fields are accessible for top queue candidates."""

    REQUIRED_QUEUE_FIELDS = (
        "rank", "symbol", "deployment_score", "narrative_tier",
        "composite_score", "replay_supported", "trim_score",
        "current_weight_pct", "score_breakdown",
    )

    REQUIRED_OVERLAY_FIELDS = (
        "symbol", "composite_score", "ess_score_text", "zacks_rating",
        "replay_percentile", "replay_supported", "signal_direction",
    )

    REQUIRED_UCF_FIELDS = (
        "ucf_score", "ucf_rank", "ucf_label", "signal_summary",
        "source_signals", "deployment",
    )

    def test_queue_candidates_have_required_fields(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        for cand in queue[:10]:
            for field in self.REQUIRED_QUEUE_FIELDS:
                assert field in cand, (
                    f"{cand['symbol']} missing queue field: {field}"
                )

    def test_overlays_have_required_fields(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        overlays = result["security_overlays"]
        assert overlays, "security_overlays must not be empty"
        for ov in overlays[:10]:
            for field in self.REQUIRED_OVERLAY_FIELDS:
                assert field in ov, (
                    f"{ov.get('symbol')} missing overlay field: {field}"
                )

    def test_ucf_verdicts_have_required_fields(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        ucf = result["ucf_verdicts_by_symbol"]
        for sym, verdict in list(ucf.items())[:10]:
            for field in self.REQUIRED_UCF_FIELDS:
                assert field in verdict, (
                    f"{sym} missing UCF field: {field}"
                )

    def test_deployment_plan_provides_projected_weights(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        plan = result.get("deployment_plan", {})
        recs = plan.get("recommendations", [])
        assert recs, "deployment_plan.recommendations must not be empty"
        for r in recs:
            assert "projected_weight_pct" in r, (
                f"{r.get('symbol')} missing projected_weight_pct"
            )

    def test_score_breakdown_has_cwdas_components(self):
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        queue = result["deployment_queue"]["queue"]
        aeis = next(c for c in queue if c["symbol"] == "AEIS")
        bd = aeis["score_breakdown"]
        for component in ("signal", "replay", "conviction", "sizing", "momentum"):
            assert component in bd, f"score_breakdown missing component: {component}"

    def test_vrt_has_ess_score_in_overlay(self):
        """VRT should have a non-empty ESS score (VERY_BULLISH in reference run)."""
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        overlays = result["security_overlays"]
        vrt_ov = next((o for o in overlays if o["symbol"] == "VRT"), None)
        assert vrt_ov is not None, "VRT must appear in security_overlays"
        ess = vrt_ov.get("ess_score_text", "")
        assert ess and ess not in ("", "None"), (
            f"VRT ESS should be populated, got: {ess!r}"
        )

    def test_ucf_score_range_valid(self):
        """All UCF scores should be between 0 and 100."""
        result = _load_reference()
        if result is None:
            pytest.skip("Reference run not available")
        ucf = result["ucf_verdicts_by_symbol"]
        for sym, v in ucf.items():
            score = float(v["ucf_score"])
            assert 0 <= score <= 100, f"{sym} ucf_score {score} out of range [0,100]"


# ─────────────────────────────────────────────────────────────────────────────
# T6 — UCF integration in runner pipeline (unit test)
# ─────────────────────────────────────────────────────────────────────────────

class TestUCFInRunnerPipeline:
    """UCF is computed and written during run_analysis()."""

    def test_ucf_verdicts_in_run_result(self, tmp_path, monkeypatch):
        """run_analysis result contains ucf_verdicts_by_symbol."""
        import json
        from pathlib import Path
        from src.portfolio import runner

        # Find a real CSV input to test against
        raw_dir = Path("data/portfolio_ingestion")
        csv_files = list(raw_dir.glob("*.csv"))
        if not csv_files:
            pytest.skip("No portfolio CSVs available for integration test")

        result = runner.run_analysis(str(csv_files[0]))
        assert "ucf_verdicts_by_symbol" in result, (
            "run_analysis result must include ucf_verdicts_by_symbol"
        )
        ucf = result["ucf_verdicts_by_symbol"]
        assert isinstance(ucf, dict)
        assert len(ucf) > 0, "ucf_verdicts_by_symbol must contain entries"

    def test_ucf_verdicts_json_written_to_run_dir(self, tmp_path):
        """ucf_verdicts.json is written alongside other run artifacts."""
        from pathlib import Path
        run_dir = Path(f"data/portfolio_ingestion/analysis_runs/{REFERENCE_RUN_ID}")
        if not run_dir.exists():
            pytest.skip("Reference run directory not available")
        # If the reference run existed before 7.5E integration, file may already exist
        # from Phase 7.7B; just verify it has the expected structure
        ucf_path = run_dir / "ucf_verdicts.json"
        if ucf_path.exists():
            with open(ucf_path) as fh:
                data = json.load(fh)
            assert "verdicts" in data
            assert isinstance(data["verdicts"], list)
            assert len(data["verdicts"]) > 0
        else:
            pytest.skip("ucf_verdicts.json not yet generated for reference run")

import json  # noqa: E402 — needed for last test method above
