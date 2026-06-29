from __future__ import annotations

from datetime import datetime, timezone

from src.portfolio.enrichment import enrich_holdings
from src.portfolio.exposure_decomposition import build_exposure_maps
from src.portfolio.models import PortfolioHolding
from src.portfolio.reconciliation import _rc02_allocation_totals
from src.portfolio.taxonomy import normalize_node_key

_NOW = datetime.now(timezone.utc).isoformat()


def _holding(symbol: str, *, security_type: str = "Common Stock") -> PortfolioHolding:
    return PortfolioHolding(
        portfolio_snapshot_id="PSNAP-TEST",
        snapshot_date="2026-06-29",
        account_name="TEST",
        symbol=symbol,
        description=symbol,
        quantity=1.0,
        market_value=1_000.0,
        percent_of_portfolio=1.0,
        asset_class="UNKNOWN",
        geography="UNKNOWN",
        market_cap_bucket="UNKNOWN",
        mega_subtier="N/A",
        sector="UNKNOWN",
        industry="UNKNOWN",
        security_type=security_type,
        cost_basis=None,
        composite_score=None,
        ess_score_text=None,
        zacks_rating=None,
        benchmark_id=None,
        investable_vehicle_id=None,
        source_file="test.csv",
        created_at_utc=_NOW,
    )


def test_direct_commodity_etf_classification_to_canonical_nodes() -> None:
    expected = {
        "IAU": "COMMODITIES.GOLD",
        "GLD": "COMMODITIES.GOLD",
        "SGOL": "COMMODITIES.GOLD",
        "BNO": "COMMODITIES.ENERGY",
        "USO": "COMMODITIES.ENERGY",
        "UNG": "COMMODITIES.ENERGY",
        "PDBC": "COMMODITIES.BROAD_BASKET",
        "DBC": "COMMODITIES.BROAD_BASKET",
        "GSG": "COMMODITIES.BROAD_BASKET",
    }

    for symbol, node in expected.items():
        enriched = enrich_holdings([_holding(symbol)])[0]
        assert enriched.asset_class == "COMMODITIES"
        assert enriched.security_type == "ETF"
        assert normalize_node_key(enriched.sector) == node


def test_broad_commodity_aliases_normalize_to_broad_basket() -> None:
    aliases = [
        "BROAD COMMODITY",
        "BROAD_COMMODITY",
        "Broad Commodity",
        "Broad_Commodity",
        "COMMODITIES.BROAD_COMMODITY",
        "COMMODITIES.BROAD",
    ]

    for alias in aliases:
        assert normalize_node_key(alias) == "COMMODITIES.BROAD_BASKET"


def test_pdbc_effective_exposure_uses_canonical_broad_basket_node() -> None:
    pdbc = enrich_holdings([_holding("PDBC")])[0]
    _, effective, _ = build_exposure_maps([pdbc])

    assert "COMMODITIES.BROAD_BASKET" in effective
    assert "BROAD COMMODITY" not in effective


def test_bno_no_longer_appears_as_missing_asset_class_mapping() -> None:
    bno = enrich_holdings([_holding("BNO")])[0]
    assert bno.asset_class == "COMMODITIES"

    alignment = [
        {"node_key": "EQUITIES", "actual_pct": 95.0},
        {"node_key": "FIXED_INCOME", "actual_pct": 2.0},
        {"node_key": "DIGITAL", "actual_pct": 1.0},
        {"node_key": "COMMODITIES", "actual_pct": 1.0},
        {"node_key": "CASH", "actual_pct": 1.0},
    ]
    rc02 = _rc02_allocation_totals(alignment, [bno])

    assert all(sc.get("symbol") != "BNO" for sc in rc02.sub_checks)


def test_equity_adjacent_proxies_are_not_direct_commodity_fillers() -> None:
    from src.portfolio.enrichment import _ETF_OVERRIDES

    proxies = ["KGC", "XLE", "PSX", "CVE", "DVN", "NUE", "STLD", "CRS"]
    for symbol in proxies:
        override = _ETF_OVERRIDES.get(symbol)
        if override is not None:
            assert override.get("asset_class") != "COMMODITIES"
