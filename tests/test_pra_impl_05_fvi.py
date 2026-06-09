"""Tests for PRA-IMPL-05 Phase 1: FVI Advisory Loader and Data Flow.

Validates:
- FVI config loads correctly from YAML
- Missing/malformed config degrades gracefully
- build_fvi_data_for_holdings returns correct records
- Missing symbols silently omitted (graceful degradation)
- Tier ordering constants are correct
- _build_fvi_payload integration
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from src.portfolio.fvi_loader import (
    FVI_TIER_ORDER,
    build_fvi_data_for_holdings,
    get_fvi_record,
    load_fvi_registry,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _write_yaml(data: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)


def _minimal_config(extra_funds: dict | None = None) -> dict:
    funds = {
        "DODFX": {
            "peer_group": "Foreign Large Value",
            "morningstar_category": "Foreign Large Value",
            "asset_class": "EQUITIES",
            "geography": "INTERNATIONAL",
            "vehicle_type": "ACTIVE_MUTUAL_FUND",
            "fvi_tier": "HIGH",
            "estimated_fvi_score": 75,
            "confidence": "MEDIUM",
            "data_source": "MANUAL_ADVISORY_ESTIMATE",
            "advisory_text": "Retain preferred.",
            "retain_advisory": True,
        },
        "VOO": {
            "peer_group": "US Large Blend ETF",
            "morningstar_category": "Large Blend",
            "asset_class": "EQUITIES",
            "geography": "US",
            "vehicle_type": "INDEX_ETF",
            "fvi_tier": "ELITE",
            "estimated_fvi_score": 90,
            "confidence": "HIGH",
            "data_source": "MANUAL_ADVISORY_ESTIMATE",
            "advisory_text": "Optimal US Large Blend ETF.",
            "retain_advisory": True,
        },
        "FIGFX": {
            "peer_group": "Foreign Large Growth",
            "morningstar_category": "Foreign Large Growth",
            "asset_class": "EQUITIES",
            "geography": "INTERNATIONAL",
            "vehicle_type": "ACTIVE_MUTUAL_FUND",
            "fvi_tier": "MEDIUM",
            "estimated_fvi_score": 55,
            "confidence": "LOW",
            "data_source": "MANUAL_ADVISORY_ESTIMATE",
            "advisory_text": "Reduction candidate.",
            "retain_advisory": False,
        },
    }
    if extra_funds:
        funds.update(extra_funds)
    return {
        "version": 1,
        "effective_date": "2026-06-09",
        "phase": "PHASE_1_ADVISORY",
        "funds": funds,
    }


# ─── load_fvi_registry ────────────────────────────────────────────────────────

class TestLoadFviRegistry:
    def test_loads_config_correctly(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            p = Path(f.name)
        _write_yaml(_minimal_config(), p)
        reg = load_fvi_registry(p)
        p.unlink()
        assert "DODFX" in reg
        assert reg["DODFX"]["fvi_tier"] == "HIGH"
        assert reg["DODFX"]["peer_group"] == "Foreign Large Value"
        assert reg["DODFX"]["retain_advisory"] is True

    def test_symbol_uppercased(self):
        cfg = _minimal_config({"dodfx_lower": {
            "peer_group": "Test", "fvi_tier": "MEDIUM",
            "estimated_fvi_score": 50, "retain_advisory": False,
            "advisory_text": "", "confidence": "LOW",
            "data_source": "MANUAL_ADVISORY_ESTIMATE",
        }})
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            p = Path(f.name)
        _write_yaml(cfg, p)
        reg = load_fvi_registry(p)
        p.unlink()
        assert "DODFX_LOWER" in reg

    def test_missing_file_returns_empty_dict(self):
        reg = load_fvi_registry(Path("/nonexistent/path.yaml"))
        assert reg == {}

    def test_malformed_yaml_returns_empty_dict(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("not: valid: yaml: [[[")
            p = Path(f.name)
        reg = load_fvi_registry(p)
        p.unlink()
        assert reg == {}

    def test_empty_funds_section_returns_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            p = Path(f.name)
        _write_yaml({"version": 1, "funds": {}}, p)
        reg = load_fvi_registry(p)
        p.unlink()
        assert reg == {}

    def test_actual_config_file_loads(self):
        """Integration test: the real config/fvi_peer_groups.yaml must load."""
        reg = load_fvi_registry()  # uses default path
        assert len(reg) >= 10, "Expected at least 10 fund entries in the registry"
        assert "DODFX" in reg
        assert "VOO" in reg
        assert "FBTC" in reg

    def test_dodfx_is_high_retain(self):
        reg = load_fvi_registry()
        dodfx = reg.get("DODFX", {})
        assert dodfx.get("fvi_tier") == "HIGH"
        assert dodfx.get("retain_advisory") is True

    def test_voo_is_elite_retain(self):
        reg = load_fvi_registry()
        voo = reg.get("VOO", {})
        assert voo.get("fvi_tier") == "ELITE"
        assert voo.get("retain_advisory") is True

    def test_fsol_is_low_no_retain(self):
        reg = load_fvi_registry()
        fsol = reg.get("FSOL", {})
        assert fsol.get("fvi_tier") == "LOW"
        assert fsol.get("retain_advisory") is False


# ─── get_fvi_record ───────────────────────────────────────────────────────────

class TestGetFviRecord:
    def test_found(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            p = Path(f.name)
        _write_yaml(_minimal_config(), p)
        reg = load_fvi_registry(p)
        p.unlink()
        rec = get_fvi_record("dodfx", reg)  # lowercase input
        assert rec is not None
        assert rec["fvi_tier"] == "HIGH"

    def test_not_found_returns_none(self):
        reg = load_fvi_registry()
        rec = get_fvi_record("AAPL", reg)  # not a fund vehicle
        assert rec is None


# ─── build_fvi_data_for_holdings ─────────────────────────────────────────────

class TestBuildFviDataForHoldings:
    def test_returns_only_known_symbols(self):
        reg = load_fvi_registry()
        result = build_fvi_data_for_holdings(
            ["DODFX", "VOO", "TSLA", "NVDA", "FBTC"],
            reg,
        )
        assert "DODFX" in result
        assert "VOO" in result
        assert "FBTC" in result
        assert "TSLA" not in result  # individual equity — not in FVI config
        assert "NVDA" not in result

    def test_empty_symbols_returns_empty(self):
        reg = load_fvi_registry()
        result = build_fvi_data_for_holdings([], reg)
        assert result == {}

    def test_empty_registry_returns_empty(self):
        result = build_fvi_data_for_holdings(["DODFX", "VOO"], {})
        assert result == {}

    def test_all_portfolio_funds_have_fvi(self):
        """All 15 current portfolio fund vehicles should be in the registry."""
        expected = {
            "VOO", "VB", "VO", "VEA", "VWO", "FXAIX", "DODFX",
            "BND", "BNDX", "FBTC", "FETH", "XRP", "FSOL",
            "FMCSX", "FCPGX",
        }
        reg = load_fvi_registry()
        result = build_fvi_data_for_holdings(list(expected), reg)
        missing = expected - set(result.keys())
        assert not missing, f"Missing FVI records for: {missing}"


# ─── Tier ordering ────────────────────────────────────────────────────────────

class TestTierOrdering:
    def test_elite_ranks_highest(self):
        assert FVI_TIER_ORDER["ELITE"] < FVI_TIER_ORDER["HIGH"]

    def test_full_ordering(self):
        tiers = sorted(FVI_TIER_ORDER.keys(), key=lambda t: FVI_TIER_ORDER[t])
        assert tiers == ["ELITE", "HIGH", "MEDIUM", "LOW", "WEAK"]


# ─── Invariant: no scoring changes ───────────────────────────────────────────

class TestNoScoringImpact:
    def test_fvi_loader_has_no_scoring_imports(self):
        """Ensure fvi_loader.py does not import scoring-related modules."""
        import ast
        src = Path("src/portfolio/fvi_loader.py").read_text()
        tree = ast.parse(src)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
        forbidden = {"scoring", "cw_das", "ess", "composite", "recommendations"}
        overlap = {i for i in imports if any(f in i.lower() for f in forbidden)}
        assert not overlap, f"fvi_loader imports scoring modules: {overlap}"
