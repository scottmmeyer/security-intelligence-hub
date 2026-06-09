"""Phase D — Holding enrichment using SIH intelligence contracts.

Enriches UNKNOWN-classified holdings by joining against:
  - data/current/analytical_universe.csv  (primary classification source)
  - data/current/replay_inputs.csv        (benchmark / vehicle lookup)
  - ETF and cash override tables (hardcoded canonical vocabulary)

Classification priority:
  1. analytical_universe exact symbol match
  2. ETF override table
  3. Cash detection heuristic
  4. UNKNOWN (preserved for manual review)

Rule: This module REUSES SIH intelligence contracts. It does NOT implement
separate classification logic. The analytical_universe is the single source
of truth for symbol→SIH-dimension mappings.
"""

from __future__ import annotations

import csv
import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from .exposure_decomposition import build_holding_decomposition
from .models import FundingSourceEntry, FundingSourceAnalysis, PortfolioHolding


# ─────────────────────────────────────────────────────────────────────────────
# ETF / known-vehicle override table
# Maps ticker → (asset_class, geography, market_cap_bucket, mega_subtier, sector, industry)
# ─────────────────────────────────────────────────────────────────────────────

_ETF_OVERRIDES: dict[str, dict] = {
    # US broad equity
    "VOO":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "VTI":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "SPY":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "IVV":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "FXAIX": dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),  # Fidelity 500 Index Fund
    "QQQ":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",  mega_subtier="N/A", sector="Technology",   industry="ALL"),
    "OEF":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "MDY":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MID",    mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "VO":    dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MID",    mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "IJH":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MID",    mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "VB":    dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="SMALL",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "IJR":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="SMALL",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "IWM":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="SMALL",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "IWC":   dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MICRO",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    # International
    "EFA":   dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "VEA":   dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "VXUS":  dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "VWO":   dict(asset_class="EQUITIES", geography="EMERGING_MARKETS", market_cap_bucket="LARGE", mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    "EMXC":  dict(asset_class="EQUITIES", geography="EMERGING_MARKETS", market_cap_bucket="LARGE", mega_subtier="N/A", sector="Broad Market", industry="ALL"),
    # Fixed income
    "BND":   dict(asset_class="FIXED_INCOME", geography="US",        market_cap_bucket="N/A",    mega_subtier="N/A", sector="Fixed Income", industry="ALL"),
    "AGG":   dict(asset_class="FIXED_INCOME", geography="US",        market_cap_bucket="N/A",    mega_subtier="N/A", sector="Fixed Income", industry="ALL"),
    "BNDX":  dict(asset_class="FIXED_INCOME", geography="INTERNATIONAL", market_cap_bucket="N/A", mega_subtier="N/A", sector="Fixed Income", industry="ALL"),
    "SCHP":  dict(asset_class="FIXED_INCOME", geography="US",        market_cap_bucket="N/A",    mega_subtier="N/A", sector="Fixed Income", industry="TIPS"),
    # Commodities
    "GLD":   dict(asset_class="COMMODITIES", geography="GLOBAL",     market_cap_bucket="N/A",    mega_subtier="N/A", sector="Gold",         industry="Gold"),
    "IAU":   dict(asset_class="COMMODITIES", geography="GLOBAL",     market_cap_bucket="N/A",    mega_subtier="N/A", sector="Gold",         industry="Gold"),
    "PDBC":  dict(asset_class="COMMODITIES", geography="GLOBAL",     market_cap_bucket="N/A",    mega_subtier="N/A", sector="Broad Commodity", industry="ALL"),
    "XLE":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Energy",       industry="Oil & Gas"),
    "XLF":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Financials",   industry="ALL"),
    "XLK":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Technology",   industry="ALL"),
    "XLV":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Healthcare",   industry="ALL"),
    "XLI":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Industrials",  industry="ALL"),
    "SMH":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Technology",   industry="Semiconductors"),
    "SOXX":  dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Technology",   industry="Semiconductors"),
    "XLF":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Financials",   industry="ALL"),
    "XLK":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Technology",   industry="ALL"),
    "XLV":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Healthcare",   industry="ALL"),
    "XLI":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Industrials",  industry="ALL"),
    "SMH":   dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Technology",   industry="Semiconductors"),
    "SOXX":  dict(asset_class="EQUITIES",   geography="US",          market_cap_bucket="MEGA",   mega_subtier="N/A", sector="Technology",   industry="Semiconductors"),
    # Digital
    "IBIT":  dict(asset_class="DIGITAL",    geography="GLOBAL",      market_cap_bucket="N/A",    mega_subtier="N/A", sector="Digital Assets", industry="Bitcoin"),
    "FBTC":  dict(asset_class="DIGITAL",    geography="GLOBAL",      market_cap_bucket="N/A",    mega_subtier="N/A", sector="Digital Assets", industry="Bitcoin"),
    # Cash
    "SPAXX": dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Money Market"),
    "VMFXX": dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Money Market"),
    "FZFXX": dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Money Market"),
    "FDRXX": dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Money Market"),
    "SPRXX": dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Money Market"),
    "FCASH": dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Cash"),
    "CASH":  dict(asset_class="CASH",       geography="US",          market_cap_bucket="N/A",    mega_subtier="N/A", sector="Cash",         industry="Cash"),
    # ── Mutual funds — International equity ─────────────────────────────────
    # Phase 6.4B: added to resolve L1 gap (RC-02 FAIL, 4.1% unclassified).
    # These symbols were absent from both analytical_universe.csv and the ETF
    # override table, causing asset_class=UNKNOWN and exclusion from L1 sum.
    "DODFX": dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Broad Market",   industry="ALL"),  # Dodge & Cox International Stock Cl I
    "FIGFX": dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Broad Market",   industry="ALL"),  # Fidelity International Growth Fund
    # ── Mutual funds — US equity ─────────────────────────────────────────────
    "FMCSX": dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MID",    mega_subtier="N/A", sector="Broad Market",   industry="ALL"),  # Fidelity Mid Cap Stock
    "FCPGX": dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="SMALL",  mega_subtier="N/A", sector="Broad Market",   industry="ALL"),  # Fidelity Small Cap Growth
    # ── ADRs — International equity ──────────────────────────────────────────
    "TTNDY": dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE",  mega_subtier="N/A", sector="Industrials",    industry="Consumer Electronics"),  # Techtronic Industries Co. ADR (HKG: 669)
    # ── Individual equity overrides — RC-02 classification gap fix ───────────
    # These symbols are absent from analytical_universe.csv but present in the
    # portfolio.  Without an override they fall through to asset_class=UNKNOWN,
    # causing L1 allocation sum < 100% (RC-02 FAIL).
    # Source: company_profile data + security_metadata (sector/industry/country).
    # Classification follows SIH taxonomy conventions.
    "BSVN":  dict(asset_class="EQUITIES", geography="US",            market_cap_bucket="MICRO",  mega_subtier="N/A", sector="FINANCIAL SERVICES", industry="Banks - Regional"),   # Bank7 Corp, Oklahoma City, US; ~$300M market cap
    "STNG":  dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="SMALL",  mega_subtier="N/A", sector="ENERGY",            industry="Oil & Gas Midstream"), # Scorpio Tankers Inc., Monaco-domiciled, NYSE-listed; ~$1.3B market cap
    "SIMO":  dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="SMALL",  mega_subtier="N/A", sector="TECHNOLOGY",        industry="Semiconductors"),      # Silicon Motion Technology ADR, Hong Kong; ~$1.4B market cap
    # ── Zero-value contra entries ─────────────────────────────────────────────
    # M26CNT069 is a Fidelity-internal identifier for a CyberArk contra lot.
    # Market value is $0.00; included here to prevent UNKNOWN classification.
    "M26CNT069": dict(asset_class="EQUITIES", geography="INTERNATIONAL", market_cap_bucket="LARGE", mega_subtier="N/A", sector="Technology", industry="Cybersecurity", security_type="CONTRA_ENTRY"),  # CyberArk Software contra lot
    # ── Digital asset ETFs/funds ─────────────────────────────────────────────
    "FETH":  dict(asset_class="DIGITAL",  geography="GLOBAL",        market_cap_bucket="N/A",    mega_subtier="N/A", sector="Digital Assets", industry="Ethereum"),  # Fidelity Ethereum Fund
    "XRP":   dict(asset_class="DIGITAL",  geography="GLOBAL",        market_cap_bucket="N/A",    mega_subtier="N/A", sector="Digital Assets", industry="XRP"),       # Bitwise XRP ETF
    "FSOL":  dict(asset_class="DIGITAL",  geography="GLOBAL",        market_cap_bucket="N/A",    mega_subtier="N/A", sector="Digital Assets", industry="Solana"),    # Fidelity Solana Fund
}

# ─────────────────────────────────────────────────────────────────────────────
# Cash-equivalent symbol registry
# ─────────────────────────────────────────────────────────────────────────────

# Symbols in this set are treated as direct cash positions, NOT as fund
# exposure containers.  They must NOT receive security_type="ETF" in the
# enrichment step — doing so causes their CASH exposure to appear as
# ETF-derived rather than as a direct portfolio position.
_CASH_EQUIVALENT_SYMBOLS: frozenset[str] = frozenset(
    sym for sym, ov in _ETF_OVERRIDES.items() if ov.get("asset_class") == "CASH"
) | frozenset({"FDRXX", "SPRXX", "FCASH", "FGXX", "SWVXX", "VUSXX", "TTTXX", "PRTXX", "FDLXX"})

_HYPER_MEGA_SYMBOLS = {
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA",
    "AVGO", "ASML", "TSM", "MU",
}


def _load_universe(universe_csv: str) -> dict[str, dict]:
    """Load analytical_universe.csv into a symbol→row dict.

    When duplicate symbols exist (multiple runs), prefer the row with the
    highest composite_score to get the most informative classification.
    """
    universe: dict[str, dict] = {}
    if not os.path.exists(universe_csv):
        return universe
    with open(universe_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sym = row.get("symbol", "").strip().upper()
            if not sym:
                continue
            existing = universe.get(sym)
            try:
                score = float(row.get("composite_score") or 0)
            except ValueError:
                score = 0.0
            if existing is None:
                row["_score"] = score
                universe[sym] = row
            elif score > existing.get("_score", 0):
                row["_score"] = score
                universe[sym] = row
    return universe


def enrich_holdings(
    holdings: list[PortfolioHolding],
    universe_csv: str = "data/current/analytical_universe.csv",
) -> list[PortfolioHolding]:
    """Return a new list of PortfolioHolding with classification fields populated.

    Enrichment order:
      1. analytical_universe (highest authority — real SIH data)
      2. ETF override table
      3. Cash heuristic
      4. UNKNOWN (preserved)
    """
    universe = _load_universe(universe_csv)
    now_utc = datetime.now(timezone.utc).isoformat()

    enriched: list[PortfolioHolding] = []
    for h in holdings:
        sym = h.symbol.upper()

        if sym in universe:
            u = universe[sym]
            bucket = u.get("market_cap_bucket", "UNKNOWN").upper()
            subtier = _resolve_mega_subtier(sym, u.get("analytical_market_cap_subtier", ""))
            # Resolve security_type from universe BEFORE calling decomposition so that
            # registry-listed ETFs (e.g. VOO) are decomposed correctly even when the
            # portfolio CSV delivered a non-ETF security_type value.
            security_type_resolved = u.get("security_type") or h.security_type
            decomposition = build_holding_decomposition(
                symbol=sym,
                security_type=security_type_resolved,
                asset_class="EQUITIES",
                geography=u.get("geography", "UNKNOWN").upper(),
                market_cap_bucket=bucket,
                mega_subtier=subtier,
                sector=u.get("sector", "UNKNOWN"),
                timestamp_utc=now_utc,
            )
            enriched.append(replace(
                h,
                asset_class="EQUITIES",
                geography=u.get("geography", "UNKNOWN").upper(),
                market_cap_bucket=bucket,
                mega_subtier=subtier,
                sector=u.get("sector", "UNKNOWN"),
                industry=u.get("industry", "UNKNOWN"),
                security_type=security_type_resolved,
                composite_score=_safe_float(u.get("composite_score")),
                ess_score_text=u.get("ess_score_text") or None,
                zacks_rating=u.get("zacks_rating") or None,
                danelfin_score=u.get("danelfin_score") or None,
                benchmark_id=u.get("benchmark_id") or None,
                investable_vehicle_id=u.get("investable_vehicle_id") or None,
                exposure_geography_mix=decomposition.exposure_geography_mix,
                exposure_market_cap_mix=decomposition.exposure_market_cap_mix,
                exposure_mega_subtier_mix=decomposition.exposure_mega_subtier_mix,
                exposure_sector_mix=decomposition.exposure_sector_mix,
                exposure_style_mix=decomposition.exposure_style_mix,
                exposure_thematic_mix=decomposition.exposure_thematic_mix,
                decomposition_method=decomposition.decomposition_method,
                decomposition_version=decomposition.decomposition_version,
                decomposition_timestamp=decomposition.decomposition_timestamp,
                decomposition_confidence=decomposition.decomposition_confidence,
                decomposition_source=decomposition.decomposition_source,
                decomposition_confidence_tier=decomposition.decomposition_confidence_tier,
                strategic_role=decomposition.strategic_role,
                created_at_utc=now_utc,
            ))
        elif sym in _ETF_OVERRIDES:
            ov = _ETF_OVERRIDES[sym]
            # Zero-value legacy positions (contra lots, broker artifacts): skip ETF
            # decomposition — enrich with static override metadata only.
            if h.operational_state == "ZERO_VALUE_LEGACY_POSITION":
                enriched.append(replace(
                    h,
                    asset_class=ov["asset_class"],
                    geography=ov.get("geography", "UNKNOWN"),
                    market_cap_bucket=ov.get("market_cap_bucket", "UNKNOWN"),
                    mega_subtier=ov.get("mega_subtier", "N/A"),
                    sector=ov.get("sector", "UNKNOWN"),
                    industry=ov.get("industry", "UNKNOWN"),
                    security_type=ov.get("security_type", "CONTRA_ENTRY"),
                    is_cash_equivalent=False,
                    operational_state="ZERO_VALUE_LEGACY_POSITION",
                    created_at_utc=now_utc,
                ))
                continue
            # Cash-equivalent symbols (SPAXX, VMFXX, etc.) must NOT be promoted to
            # security_type="ETF" — doing so routes their CASH exposure through the
            # fund/ETF accumulator path, making it appear as ETF-derived exposure
            # rather than a direct position.  Keep the original "Cash" security_type.
            if sym in _CASH_EQUIVALENT_SYMBOLS:
                effective_security_type = "Cash"
                is_cash_equiv = True
                new_op_state = "CASH_EQUIVALENT"
            else:
                effective_security_type = "ETF"
                is_cash_equiv = False
                new_op_state = h.operational_state
            decomposition = build_holding_decomposition(
                symbol=sym,
                security_type=effective_security_type,
                asset_class=ov["asset_class"],
                geography=ov["geography"],
                market_cap_bucket=ov["market_cap_bucket"],
                mega_subtier=ov["mega_subtier"],
                sector=ov["sector"],
                timestamp_utc=now_utc,
            )
            enriched.append(replace(
                h,
                asset_class=ov["asset_class"],
                geography=ov["geography"],
                market_cap_bucket=ov["market_cap_bucket"],
                mega_subtier=ov["mega_subtier"],
                sector=ov["sector"],
                industry=ov["industry"],
                security_type=effective_security_type,
                is_cash_equivalent=is_cash_equiv,
                operational_state=new_op_state,
                exposure_geography_mix=decomposition.exposure_geography_mix,
                exposure_market_cap_mix=decomposition.exposure_market_cap_mix,
                exposure_mega_subtier_mix=decomposition.exposure_mega_subtier_mix,
                exposure_sector_mix=decomposition.exposure_sector_mix,
                exposure_style_mix=decomposition.exposure_style_mix,
                decomposition_method=decomposition.decomposition_method,
                decomposition_version=decomposition.decomposition_version,
                decomposition_timestamp=decomposition.decomposition_timestamp,
                decomposition_confidence=decomposition.decomposition_confidence,
                decomposition_source=decomposition.decomposition_source,
                decomposition_confidence_tier=decomposition.decomposition_confidence_tier,
                created_at_utc=now_utc,
            ))
        elif h.security_type == "Cash" or sym == "CASH" or sym in _CASH_EQUIVALENT_SYMBOLS:
            decomposition = build_holding_decomposition(
                symbol=sym,
                security_type="Cash",
                asset_class="CASH",
                geography="US",
                market_cap_bucket="N/A",
                mega_subtier="N/A",
                sector="Cash",
                timestamp_utc=now_utc,
            )
            enriched.append(replace(
                h,
                asset_class="CASH",
                geography="US",
                market_cap_bucket="N/A",
                mega_subtier="N/A",
                sector="Cash",
                industry="Cash",
                security_type="Cash",
                is_cash_equivalent=True,
                operational_state="CASH_EQUIVALENT",
                exposure_geography_mix=decomposition.exposure_geography_mix,
                exposure_market_cap_mix=decomposition.exposure_market_cap_mix,
                exposure_mega_subtier_mix=decomposition.exposure_mega_subtier_mix,
                exposure_sector_mix=decomposition.exposure_sector_mix,
                exposure_style_mix=decomposition.exposure_style_mix,
                exposure_thematic_mix=decomposition.exposure_thematic_mix,
                decomposition_method=decomposition.decomposition_method,
                decomposition_version=decomposition.decomposition_version,
                decomposition_timestamp=decomposition.decomposition_timestamp,
                decomposition_confidence=decomposition.decomposition_confidence,
                decomposition_source=decomposition.decomposition_source,
                decomposition_confidence_tier=decomposition.decomposition_confidence_tier,
                strategic_role=decomposition.strategic_role,
                created_at_utc=now_utc,
            ))
        else:
            decomposition = build_holding_decomposition(
                symbol=sym,
                security_type=h.security_type,
                asset_class=h.asset_class,
                geography=h.geography,
                market_cap_bucket=h.market_cap_bucket,
                mega_subtier=h.mega_subtier,
                sector=h.sector,
                timestamp_utc=now_utc,
            )
            enriched.append(replace(
                h,
                exposure_geography_mix=decomposition.exposure_geography_mix,
                exposure_market_cap_mix=decomposition.exposure_market_cap_mix,
                exposure_mega_subtier_mix=decomposition.exposure_mega_subtier_mix,
                exposure_sector_mix=decomposition.exposure_sector_mix,
                exposure_style_mix=decomposition.exposure_style_mix,
                exposure_thematic_mix=decomposition.exposure_thematic_mix,
                decomposition_method=decomposition.decomposition_method,
                decomposition_version=decomposition.decomposition_version,
                decomposition_timestamp=decomposition.decomposition_timestamp,
                decomposition_confidence=decomposition.decomposition_confidence,
                decomposition_source=decomposition.decomposition_source,
                decomposition_confidence_tier=decomposition.decomposition_confidence_tier,
                strategic_role=decomposition.strategic_role,
                created_at_utc=now_utc,
            ))

    return enriched


def _resolve_mega_subtier(symbol: str, subtier_raw: str) -> str:
    """Return canonical mega_subtier string for a symbol."""
    if subtier_raw:
        return subtier_raw
    if symbol in _HYPER_MEGA_SYMBOLS:
        return "HYPER_MEGA"
    return "N/A"


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val not in (None, "", "N/A") else None
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6.1C — Duplicate symbol aggregation
# ─────────────────────────────────────────────────────────────────────────────

def normalize_and_aggregate_holdings(
    holdings: list[PortfolioHolding],
) -> list[PortfolioHolding]:
    """Aggregate duplicate-symbol holdings deterministically.

    Fidelity CSVs occasionally produce multiple rows for the same symbol
    (e.g., SPAXX appearing across two sub-accounts, or the same stock held
    in both a taxable and retirement account exported together).

    Merging rules:
      - market_value and quantity are summed
      - percent_of_portfolio is recalculated from aggregated market values
      - all classification/decomposition fields are taken from the FIRST
        occurrence (they are symbol-level, not position-level)
      - row insertion order is preserved (first occurrence's position wins)

    Returns a new list; original holdings are unchanged.
    """
    seen: dict[str, int] = {}   # symbol → index in result
    result: list[PortfolioHolding] = []

    for h in holdings:
        sym = h.symbol.upper()
        if sym in seen:
            idx = seen[sym]
            existing = result[idx]
            result[idx] = replace(
                existing,
                market_value=existing.market_value + h.market_value,
                quantity=existing.quantity + h.quantity,
            )
        else:
            seen[sym] = len(result)
            result.append(h)

    # Recalculate percent_of_portfolio from aggregated market values.
    # Only count positive-value holdings in the denominator so that
    # accounting-adjustment rows (negative market_value) do not distort
    # the portfolio weight distribution.
    total_mv = sum(h.market_value for h in result if h.market_value > 0)
    if total_mv > 0:
        result = [
            replace(
                h,
                percent_of_portfolio=round(
                    max(h.market_value, 0.0) / total_mv * 100.0, 4
                ),
            )
            for h in result
        ]

    return result
