"""Deterministic ETF / fund exposure decomposition helpers.

The portfolio engine treats ETFs and mutual funds as exposure containers rather
than single-bucket securities.  This module provides a governance-friendly,
config-backed heuristic decomposition for those holdings so alignment,
concentration, and recommendation logic can work on effective exposure instead
of simplistic one-bucket labels.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Taxonomy alias normalization — imported lazily to avoid circular imports
def _normalize_sector_key(sector: str) -> str:
    """Normalize a sector string to its canonical taxonomy node key.

    This prevents non-canonical sector display values (e.g. "FIXED INCOME",
    "DIGITAL ASSETS") from polluting the effective node exposure map with
    alias keys that duplicate the canonical asset class entries.
    """
    from src.portfolio.taxonomy import normalize_node_key
    return normalize_node_key(sector)
_DEFAULT_CONFIG_PATH = _REPO_ROOT / "config" / "etf_exposure_decomposition.yaml"

_FUND_SECURITY_TYPES = {"ETF", "MUTUAL_FUND"}
_VALID_MARKET_CAP_BUCKETS = {"MEGA", "LARGE", "MID", "SMALL", "MICRO"}
_VALID_GEOGRAPHIES = {"US", "INTERNATIONAL", "EMERGING_MARKETS"}
_VALID_MEGA_SUBTIERS = {"HYPER_MEGA", "ULTRA_MEGA", "EXTENDED_MEGA"}

DEFAULT_DECOMPOSITION_VERSION = "etf-exposure-decomp-v1"
DEFAULT_DECOMPOSITION_METHOD = "DIRECT_CLASSIFICATION"


@dataclass(frozen=True)
class ETFExposureDecomposition:
    """Canonical exposure decomposition contract for a single holding."""

    symbol: str
    exposure_geography_mix: tuple[tuple[str, float], ...]
    exposure_market_cap_mix: tuple[tuple[str, float], ...]
    exposure_mega_subtier_mix: tuple[tuple[str, float], ...]
    exposure_sector_mix: tuple[tuple[str, float], ...]
    exposure_style_mix: tuple[tuple[str, float], ...]
    exposure_thematic_mix: tuple[tuple[str, float], ...] = ()  # independent concentration flags; NOT normalized to 100
    decomposition_method: str = ""
    decomposition_confidence: float = 0.0
    decomposition_version: str = ""
    decomposition_timestamp: str = ""
    decomposition_source: str = ""             # REGISTRY | DIRECT_CLASSIFICATION | HEURISTIC_FALLBACK | UNRESOLVED
    decomposition_confidence_tier: str = ""    # HIGH | MEDIUM | LOW | UNKNOWN
    strategic_role: str = ""                   # e.g. CORE_BROAD_US | AGGRESSIVE_GROWTH_CONCENTRATION


def load_decomposition_registry(path: Path | str = _DEFAULT_CONFIG_PATH) -> dict[str, dict]:
    """Load the ETF exposure decomposition registry."""
    path = Path(path)
    if not path.exists():
        return {"symbols": {}, "decomposition_version": DEFAULT_DECOMPOSITION_VERSION}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    symbols = data.get("symbols", {}) or {}
    if not isinstance(symbols, dict):
        symbols = {}
    return {
        "decomposition_version": str(data.get("decomposition_version") or DEFAULT_DECOMPOSITION_VERSION),
        "default": data.get("default", {}) or {},
        "symbols": symbols,
    }


def build_holding_decomposition(
    *,
    symbol: str,
    security_type: str,
    asset_class: str,
    geography: str,
    market_cap_bucket: str,
    mega_subtier: str,
    sector: str,
    style: str = "CORE",
    timestamp_utc: str | None = None,
    registry_path: Path | str = _DEFAULT_CONFIG_PATH,
) -> ETFExposureDecomposition:
    """Build a deterministic exposure decomposition for a holding."""

    symbol_clean = str(symbol or "").strip().upper()
    security_type_clean = str(security_type or "").strip().upper()
    asset_class_clean = str(asset_class or "").strip().upper()
    geography_clean = str(geography or "").strip().upper()
    market_cap_clean = str(market_cap_bucket or "").strip().upper()
    mega_subtier_clean = str(mega_subtier or "").strip().upper()
    sector_clean = str(sector or "").strip().upper() or "UNKNOWN"
    style_clean = str(style or "CORE").strip().upper() or "CORE"

    timestamp = timestamp_utc or datetime.now(timezone.utc).isoformat()
    registry = load_decomposition_registry(registry_path)
    registry_version = str(registry.get("decomposition_version") or DEFAULT_DECOMPOSITION_VERSION)
    symbol_models = registry.get("symbols", {}) or {}

    # ----------------------------------------------------------------
    # Defense-in-depth: check the YAML registry BEFORE the security_type
    # gate. This ensures holdings like VOO that arrive with
    # security_type="Equity" from a portfolio CSV are still decomposed
    # correctly rather than silently falling through to one-hot.
    # ----------------------------------------------------------------
    model = symbol_models.get(symbol_clean)
    if isinstance(model, dict):
        # Highest-confidence path: symbol found in the YAML registry.
        return ETFExposureDecomposition(
            symbol=symbol_clean,
            exposure_geography_mix=_parse_mix(model.get("exposure_geography_mix"), fallback=_one_hot_mix(geography_clean, _VALID_GEOGRAPHIES)),
            exposure_market_cap_mix=_parse_mix(model.get("exposure_market_cap_mix"), fallback=_one_hot_mix(market_cap_clean, _VALID_MARKET_CAP_BUCKETS)),
            exposure_mega_subtier_mix=_parse_mix(model.get("exposure_mega_subtier_mix"), fallback=()),
            exposure_sector_mix=_parse_mix(model.get("exposure_sector_mix"), fallback=_one_hot_mix(sector_clean)),
            exposure_style_mix=_parse_mix(model.get("exposure_style_mix"), fallback=_one_hot_mix(style_clean)),
            exposure_thematic_mix=_parse_thematic_mix(model.get("exposure_thematic_mix")),
            decomposition_method=str(model.get("decomposition_method") or "HEURISTIC_REGISTRY_V1"),
            decomposition_confidence=_coerce_confidence(model.get("decomposition_confidence"), default=0.35),
            decomposition_version=registry_version,
            decomposition_timestamp=timestamp,
            decomposition_source="REGISTRY",
            decomposition_confidence_tier="HIGH",
            strategic_role=str(model.get("strategic_role") or ""),
        )

    # Direct holdings that are not in the registry stay one-hot with full confidence.
    if security_type_clean not in _FUND_SECURITY_TYPES:
        return ETFExposureDecomposition(
            symbol=symbol_clean,
            exposure_geography_mix=_one_hot_mix(geography_clean, _VALID_GEOGRAPHIES),
            exposure_market_cap_mix=_one_hot_mix(market_cap_clean, _VALID_MARKET_CAP_BUCKETS),
            exposure_mega_subtier_mix=_one_hot_mix(mega_subtier_clean, _VALID_MEGA_SUBTIERS),
            exposure_sector_mix=_one_hot_mix(sector_clean),
            exposure_style_mix=_one_hot_mix(style_clean),
            decomposition_method=DEFAULT_DECOMPOSITION_METHOD,
            decomposition_confidence=1.0,
            decomposition_version=registry_version,
            decomposition_timestamp=timestamp,
            decomposition_source="DIRECT_CLASSIFICATION",
            decomposition_confidence_tier="HIGH",
        )

    # Fund-like security not covered by the registry — conservative heuristic fallback.
    return ETFExposureDecomposition(
        symbol=symbol_clean,
        exposure_geography_mix=_one_hot_mix(geography_clean, _VALID_GEOGRAPHIES),
        exposure_market_cap_mix=_one_hot_mix(market_cap_clean, _VALID_MARKET_CAP_BUCKETS),
        exposure_mega_subtier_mix=(),
        exposure_sector_mix=_one_hot_mix(sector_clean),
        exposure_style_mix=_one_hot_mix(style_clean),
        decomposition_method="HEURISTIC_FALLBACK",
        decomposition_confidence=0.35,
        decomposition_version=registry_version,
        decomposition_timestamp=timestamp,
        decomposition_source="HEURISTIC_FALLBACK",
        decomposition_confidence_tier="MEDIUM",
    )


def build_exposure_maps(
    holdings: Iterable[object],
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Return (direct_node_map, effective_node_map, effective_sector_map)."""

    direct: dict[str, float] = defaultdict(float)
    effective: dict[str, float] = defaultdict(float)
    sectors: dict[str, float] = defaultdict(float)

    for holding in holdings:
        _accumulate_holding_exposure(holding, direct, effective, sectors)

    return dict(direct), dict(effective), dict(sectors)


def build_holding_exposure_contribs(holding: object) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Return node-level direct/effective/sector contribution maps for one holding."""

    direct: dict[str, float] = defaultdict(float)
    effective: dict[str, float] = defaultdict(float)
    sectors: dict[str, float] = defaultdict(float)
    _accumulate_holding_exposure(holding, direct, effective, sectors)
    return dict(direct), dict(effective), dict(sectors)


def _accumulate_holding_exposure(
    holding: object,
    direct: dict[str, float],
    effective: dict[str, float],
    sectors: dict[str, float],
) -> None:
    symbol = str(getattr(holding, "symbol", "") or "").strip().upper()
    security_type = str(getattr(holding, "security_type", "") or "").strip().upper()
    asset_class = str(getattr(holding, "asset_class", "") or "").strip().upper()
    geography = str(getattr(holding, "geography", "") or "").strip().upper()
    market_cap_bucket = str(getattr(holding, "market_cap_bucket", "") or "").strip().upper()
    mega_subtier = str(getattr(holding, "mega_subtier", "") or "").strip().upper()
    sector = str(getattr(holding, "sector", "") or "").strip().upper() or "UNKNOWN"
    style = str(getattr(holding, "style", "CORE") or "CORE").strip().upper() or "CORE"
    holding_pct = float(getattr(holding, "percent_of_portfolio", 0.0) or 0.0)

    if holding_pct <= 0:
        return

    if asset_class == "EQUITIES":
        # ----------------------------------------------------------------
        # For EQUITIES, always build decomposition via registry-first logic
        # in build_holding_decomposition so ETFs with wrong security_type
        # (e.g. "Equity" from a Fidelity CSV) are still decomposed correctly.
        # ----------------------------------------------------------------
        timestamp_value = getattr(holding, "decomposition_timestamp", "") or None
        decomposition = build_holding_decomposition(
            symbol=symbol,
            security_type=security_type,
            asset_class=asset_class,
            geography=geography,
            market_cap_bucket=market_cap_bucket,
            mega_subtier=mega_subtier,
            sector=sector,
            style=style,
            timestamp_utc=timestamp_value,
        )
        # Treat as an exposure container when the registry found the symbol
        # OR when security_type is explicitly a known fund type.
        is_fund = (
            decomposition.decomposition_source in ("REGISTRY", "HEURISTIC_FALLBACK", "SYMBOL_HEURISTIC")
            or security_type in _FUND_SECURITY_TYPES
        )
        geo_mix = decomposition.exposure_geography_mix
        cap_mix = decomposition.exposure_market_cap_mix
        subtier_mix = decomposition.exposure_mega_subtier_mix
        sector_mix = decomposition.exposure_sector_mix
    else:
        # Non-EQUITIES: enrichment correctly sets security_type="ETF" for
        # ETF overrides, so the fund check here is reliable.
        is_fund = security_type in _FUND_SECURITY_TYPES
        geo_mix = cap_mix = subtier_mix = sector_mix = ()

    # Asset class always contributes to the effective view.
    if asset_class and asset_class != "UNKNOWN":
        effective[asset_class] += holding_pct
        if not is_fund:
            direct[asset_class] += holding_pct

    if asset_class != "EQUITIES":
        # Normalize sector display values to canonical taxonomy node keys before
        # using them as map keys.  This prevents alias pollution where sector
        # field values like "Fixed Income" (→ "FIXED INCOME" after .upper()) or
        # "Digital Assets" (→ "DIGITAL ASSETS") produce spurious duplicate entries
        # alongside the canonical "FIXED_INCOME" / "DIGITAL" asset class keys.
        if sector != "UNKNOWN":
            normalized_sector = _normalize_sector_key(sector)
            # Skip if the normalized sector is just an alias of the asset class
            # (prevents double-counting such as CASH holding with sector="Cash").
            if normalized_sector != asset_class:
                effective[normalized_sector] += holding_pct
                if not is_fund:
                    direct[normalized_sector] += holding_pct
        return

    # Effective geography exposure (EQUITIES only).
    for geo, geo_pct in geo_mix:
        if geo not in _VALID_GEOGRAPHIES:
            continue
        effective[f"EQUITIES.{geo}"] += holding_pct * geo_pct / 100.0
        if not is_fund:
            direct[f"EQUITIES.{geo}"] += holding_pct * geo_pct / 100.0

        # Effective market-cap exposure.
        for cap, cap_pct in cap_mix:
            if cap not in _VALID_MARKET_CAP_BUCKETS:
                continue
            cap_weight = holding_pct * geo_pct / 100.0 * cap_pct / 100.0
            effective[f"EQUITIES.{geo}.{cap}"] += cap_weight
            if not is_fund:
                direct[f"EQUITIES.{geo}.{cap}"] += cap_weight

            # Effective mega-subtier exposure is nested within the MEGA share.
            if cap == "MEGA":
                for sub, sub_pct in subtier_mix:
                    if sub not in _VALID_MEGA_SUBTIERS:
                        continue
                    sub_weight = cap_weight * sub_pct / 100.0
                    effective[f"EQUITIES.{geo}.MEGA.{sub}"] += sub_weight
                    if not is_fund:
                        direct[f"EQUITIES.{geo}.MEGA.{sub}"] += sub_weight

        # Sector / style are exposed independently for concentration / style analysis.
        for sec, sec_pct in sector_mix:
            sec_label = str(sec or "").strip().upper()
            if not sec_label:
                continue
            sectors[sec_label] += holding_pct * geo_pct / 100.0 * sec_pct / 100.0


def _one_hot_mix(value: str, allowed: set[str] | None = None) -> tuple[tuple[str, float], ...]:
    item = str(value or "").strip().upper()
    if not item:
        return ()
    if allowed is not None and item not in allowed:
        return ()
    return ((item, 100.0),)


def _parse_mix(raw: object, *, fallback: tuple[tuple[str, float], ...]) -> tuple[tuple[str, float], ...]:
    if raw is None:
        return fallback
    if isinstance(raw, Mapping):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = []
        for entry in raw:
            if isinstance(entry, Mapping):
                key = entry.get("label") or entry.get("name") or entry.get("value") or entry.get("dimension")
                pct = entry.get("pct") or entry.get("percent") or entry.get("weight") or entry.get("value_pct")
                items.append((key, pct))
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                items.append((entry[0], entry[1]))
    else:
        return fallback

    cleaned: list[tuple[str, float]] = []
    for key, pct in items:
        key_clean = str(key or "").strip().upper()
        if not key_clean:
            continue
        try:
            pct_clean = float(pct)
        except (TypeError, ValueError):
            continue
        if pct_clean <= 0:
            continue
        cleaned.append((key_clean, pct_clean))

    if not cleaned:
        return fallback

    total = sum(pct for _, pct in cleaned)
    if total <= 0:
        return fallback

    # Normalize to 100 while preserving order.
    normalized = [(key, round((pct / total) * 100.0, 4)) for key, pct in cleaned]
    return tuple(normalized)


def _coerce_confidence(value: object, default: float = 0.35) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, confidence))


def _parse_thematic_mix(raw: object) -> tuple[tuple[str, float], ...]:
    """Parse a thematic exposure mix WITHOUT normalising to 100.

    Thematic values are independent concentration flags — a value of 65 means
    ~65% of this ETF has that thematic exposure.  Multiple themes can each be
    100% and the sum is intentionally unconstrained.
    """
    if raw is None:
        return ()
    if isinstance(raw, Mapping):
        items = list(raw.items())
    elif isinstance(raw, list):
        items = []
        for entry in raw:
            if isinstance(entry, Mapping):
                key = entry.get("label") or entry.get("name") or entry.get("value")
                pct = entry.get("pct") or entry.get("percent") or entry.get("weight")
                items.append((key, pct))
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                items.append((entry[0], entry[1]))
    else:
        return ()
    cleaned: list[tuple[str, float]] = []
    for key, pct in items:
        key_clean = str(key or "").strip().upper()
        if not key_clean:
            continue
        try:
            pct_clean = float(pct)
        except (TypeError, ValueError):
            continue
        if pct_clean <= 0:
            continue
        cleaned.append((key_clean, pct_clean))
    return tuple(cleaned)


# ─────────────────────────────────────────────────────────────────────────────
# Decomposition registry validators (B.6)
# Designed to WARN, not fail-close — validators return strings so callers
# can decide how to surface issues (log, API response, diagnostic UI).
# ─────────────────────────────────────────────────────────────────────────────

def validate_registry_entry(symbol: str, model: dict) -> list[str]:
    """Return a list of warning strings for a single registry entry.  Empty = clean."""
    warnings: list[str] = []

    def _check_sum_mix(name: str, raw: object, allowed: set[str] | None = None) -> None:
        if raw is None:
            return
        if isinstance(raw, Mapping):
            raw_total = 0.0
            for key, val in raw.items():
                try:
                    raw_total += float(val)
                except (TypeError, ValueError):
                    warnings.append(f"{symbol}: {name} key '{key}' has non-numeric value {val!r}")
                    return
            if not (98.0 <= raw_total <= 102.0):
                warnings.append(
                    f"{symbol}: {name} sums to {raw_total:.2f}% (expected ~100%, got {raw_total:.2f}%)"
                )
            if allowed:
                for key in raw:
                    k = str(key).strip().upper()
                    if k not in allowed:
                        warnings.append(
                            f"{symbol}: {name} contains unrecognized key '{key}' "
                            f"(valid: {sorted(allowed)})"
                        )

    _check_sum_mix("exposure_geography_mix",    model.get("exposure_geography_mix"),    _VALID_GEOGRAPHIES)
    _check_sum_mix("exposure_market_cap_mix",   model.get("exposure_market_cap_mix"),   _VALID_MARKET_CAP_BUCKETS)
    _check_sum_mix("exposure_mega_subtier_mix", model.get("exposure_mega_subtier_mix"), _VALID_MEGA_SUBTIERS)
    _check_sum_mix("exposure_sector_mix",       model.get("exposure_sector_mix"),       None)
    _check_sum_mix("exposure_style_mix",        model.get("exposure_style_mix"),        None)
    # NOTE: exposure_thematic_mix is NOT sum-validated (values are independent flags)

    conf = model.get("decomposition_confidence")
    if conf is not None:
        try:
            cf = float(conf)
            if not (0.0 <= cf <= 1.0):
                warnings.append(f"{symbol}: decomposition_confidence={cf} out of range [0.0, 1.0]")
        except (TypeError, ValueError):
            warnings.append(f"{symbol}: decomposition_confidence={conf!r} is not numeric")

    return warnings


def validate_decomposition_registry(
    path: Path | str = _DEFAULT_CONFIG_PATH,
) -> list[str]:
    """Validate all registry entries and return warning strings.  Empty list = clean.

    Designed to WARN not fail-close, per decomposition governance philosophy.
    Call at startup or in diagnostic scripts to surface configuration drift.
    """
    registry = load_decomposition_registry(path)
    symbols = registry.get("symbols", {}) or {}
    all_warnings: list[str] = []

    if not symbols:
        all_warnings.append("decomposition_registry: no symbol entries found — registry may be empty or mis-parsed")
        return all_warnings

    for symbol, model in symbols.items():
        if not isinstance(model, dict):
            all_warnings.append(
                f"{symbol}: registry entry is not a mapping (got {type(model).__name__})"
            )
            continue
        all_warnings.extend(validate_registry_entry(str(symbol), model))

    return all_warnings
    return max(0.0, min(1.0, confidence))