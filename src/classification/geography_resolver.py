"""Geography resolution for analytical universe rows.

Resolution precedence (first match wins):
  1. Manual override from config/geography_overrides.yaml
  2. ADR detection: if quote_type == "ADR" → INTERNATIONAL
  3. Country lookup in adr_domicile_policy.yaml:
       "United States" → US
       DEVELOPED_INTERNATIONAL / EMERGING_MARKETS → INTERNATIONAL
  4. Country string heuristic: "United States" → US
  5. UNKNOWN (flagged by classification audit)

The distinction between DEVELOPED_INTERNATIONAL and EMERGING_MARKETS is
captured in geography_subclass but the primary geography value is always
US | INTERNATIONAL | UNKNOWN for benchmark assignment compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DOMICILE_PATH = _REPO_ROOT / "config" / "adr_domicile_policy.yaml"
_DEFAULT_OVERRIDES_PATH = _REPO_ROOT / "config" / "geography_overrides.yaml"

GEOGRAPHY_US = "US"
GEOGRAPHY_INTERNATIONAL = "INTERNATIONAL"
GEOGRAPHY_UNKNOWN = "UNKNOWN"

VALID_GEOGRAPHIES = {GEOGRAPHY_US, GEOGRAPHY_INTERNATIONAL, GEOGRAPHY_UNKNOWN}

# Subclass constants for informational use
SUBCLASS_DEVELOPED = "DEVELOPED_INTERNATIONAL"
SUBCLASS_EMERGING = "EMERGING_MARKETS"
SUBCLASS_US = "US"
SUBCLASS_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GeographyResolution:
    """Result of geography resolution for a single symbol."""

    symbol: str
    geography: str
    """Primary geography value: US | INTERNATIONAL | UNKNOWN."""

    geography_subclass: str
    """Finer classification: US | DEVELOPED_INTERNATIONAL | EMERGING_MARKETS | UNKNOWN."""

    resolution_method: str
    """How geography was determined:
      MANUAL_OVERRIDE | ADR_DOMICILE | COUNTRY_LOOKUP | COUNTRY_HEURISTIC |
      EXCHANGE_HEURISTIC | EXISTING_CLASSIFICATION | DEFAULT_UNKNOWN
    """

    confidence: str
    """HIGH | MEDIUM | LOW | UNRESOLVABLE."""

    country_used: str
    """The country value that informed the resolution (empty if unused)."""


def load_adr_domicile_policy(
    path: Path | str = _DEFAULT_DOMICILE_PATH,
) -> Dict[str, str]:
    """Load country → geography_subclass map from adr_domicile_policy.yaml.

    Returns dict mapping country string → "US" | "DEVELOPED_INTERNATIONAL" | "EMERGING_MARKETS".
    """
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return {
        str(k): str(v)
        for k, v in data.get("country_geography_map", {}).items()
    }


def load_geography_overrides(
    path: Path | str = _DEFAULT_OVERRIDES_PATH,
) -> Dict[str, str]:
    """Load manual symbol → geography overrides from geography_overrides.yaml.

    Returns dict mapping uppercase symbol → "US" | "INTERNATIONAL".
    """
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    raw = data.get("overrides") or {}
    return {
        str(k).strip().upper(): str(v).strip().upper()
        for k, v in raw.items()
        if k and v
    }


def _subclass_to_geography(subclass: str) -> str:
    """Map a geography_subclass value to primary geography (US | INTERNATIONAL)."""
    if subclass == SUBCLASS_US:
        return GEOGRAPHY_US
    if subclass in (SUBCLASS_DEVELOPED, SUBCLASS_EMERGING):
        return GEOGRAPHY_INTERNATIONAL
    return GEOGRAPHY_UNKNOWN


def resolve_geography(
    *,
    symbol: str,
    security_type: str = "",
    country: str = "",
    quote_type: str = "",
    existing_geography: str = "",
    domicile_map: Optional[Dict[str, str]] = None,
    overrides: Optional[Dict[str, str]] = None,
) -> GeographyResolution:
    """Resolve the canonical geography for a security.

    Args:
        symbol:              Ticker symbol (uppercase).
        security_type:       Raw security_type string (e.g., "Common Stock", "ETF").
        country:             Country string from yfinance metadata.
        quote_type:          Quote type from yfinance (e.g., "EQUITY", "ADR", "ETF").
        existing_geography:  Current geography value in the universe row (for fallback).
        domicile_map:        Pre-loaded country → subclass map (loads default if None).
        overrides:           Pre-loaded symbol → geography overrides (loads default if None).

    Returns:
        GeographyResolution with primary geography, subclass, method, and confidence.
    """
    sym = str(symbol or "").strip().upper()

    if domicile_map is None:
        domicile_map = load_adr_domicile_policy()
    if overrides is None:
        overrides = load_geography_overrides()

    # 1. Manual override — highest precedence
    if sym in overrides:
        geo = overrides[sym]
        if geo not in (GEOGRAPHY_US, GEOGRAPHY_INTERNATIONAL):
            geo = GEOGRAPHY_UNKNOWN
        subclass = SUBCLASS_US if geo == GEOGRAPHY_US else SUBCLASS_DEVELOPED
        return GeographyResolution(
            symbol=sym,
            geography=geo,
            geography_subclass=subclass,
            resolution_method="MANUAL_OVERRIDE",
            confidence="HIGH",
            country_used="",
        )

    # 2. ADR detection — quote_type == "ADR" means international regardless of exchange
    qt = str(quote_type or "").strip().upper()
    if qt == "ADR":
        country_str = str(country or "").strip()
        subclass = domicile_map.get(country_str, SUBCLASS_UNKNOWN)
        confidence = "HIGH" if subclass != SUBCLASS_UNKNOWN else "MEDIUM"
        return GeographyResolution(
            symbol=sym,
            geography=GEOGRAPHY_INTERNATIONAL,
            geography_subclass=subclass if subclass != SUBCLASS_UNKNOWN else SUBCLASS_DEVELOPED,
            resolution_method="ADR_DOMICILE",
            confidence=confidence,
            country_used=country_str,
        )

    # 3. Country lookup via domicile policy
    country_str = str(country or "").strip()
    if country_str:
        subclass = domicile_map.get(country_str)
        if subclass is not None:
            geo = _subclass_to_geography(subclass)
            return GeographyResolution(
                symbol=sym,
                geography=geo,
                geography_subclass=subclass,
                resolution_method="COUNTRY_LOOKUP",
                confidence="HIGH",
                country_used=country_str,
            )

        # Country present but not in map — likely INTERNATIONAL with LOW confidence
        if country_str and country_str != "United States":
            return GeographyResolution(
                symbol=sym,
                geography=GEOGRAPHY_INTERNATIONAL,
                geography_subclass=SUBCLASS_UNKNOWN,
                resolution_method="COUNTRY_HEURISTIC",
                confidence="LOW",
                country_used=country_str,
            )

    # 4. Existing classification if it's a valid non-UNKNOWN value
    existing = str(existing_geography or "").strip().upper()
    if existing in (GEOGRAPHY_US, GEOGRAPHY_INTERNATIONAL):
        return GeographyResolution(
            symbol=sym,
            geography=existing,
            geography_subclass=SUBCLASS_US if existing == GEOGRAPHY_US else SUBCLASS_UNKNOWN,
            resolution_method="EXISTING_CLASSIFICATION",
            confidence="MEDIUM",
            country_used="",
        )

    # 5. Default UNKNOWN
    return GeographyResolution(
        symbol=sym,
        geography=GEOGRAPHY_UNKNOWN,
        geography_subclass=SUBCLASS_UNKNOWN,
        resolution_method="DEFAULT_UNKNOWN",
        confidence="UNRESOLVABLE",
        country_used=country_str,
    )
