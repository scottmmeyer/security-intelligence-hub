"""src/portfolio/taxonomy.py

Canonical taxonomy registry for the Security Intelligence Hub.

This module is the single source of truth for:
  - Canonical node keys (dot-notation hierarchy)
  - Human-readable display labels
  - Alias normalization (non-canonical → canonical)

Node keys are loaded from config/allocation_dimensions.yaml, which is the
authoritative hierarchy definition.  Alias mappings handle legacy display
values (e.g. "Fixed Income" → "FIXED_INCOME", "Digital Assets" → "DIGITAL")
that appear in CSV sector fields, UI labels, and other data sources.

Usage:
    from src.portfolio.taxonomy import (
        CANONICAL_NODES,
        DISPLAY_LABELS,
        normalize_node_key,
        is_canonical,
        display_label,
        find_aliases_in_collection,
    )
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

# ─────────────────────────────────────────────────────────────────────────────
# Load canonical nodes from allocation_dimensions.yaml
# ─────────────────────────────────────────────────────────────────────────────

_CONFIG_ROOT = Path(__file__).parent.parent.parent / "config"
_DIMS_PATH = _CONFIG_ROOT / "allocation_dimensions.yaml"


@lru_cache(maxsize=1)
def _load_dimensions() -> dict:
    with open(_DIMS_PATH) as fh:
        return yaml.safe_load(fh)


def _build_canonical_nodes() -> tuple[frozenset, dict]:
    """Return (canonical_node_keys, display_labels_dict) from allocation_dimensions.yaml."""
    dims = _load_dimensions()
    nodes_list = dims.get("nodes", [])
    keys: set[str] = set()
    labels: dict[str, str] = {}
    for node in nodes_list:
        key = (node.get("key") or "").strip()
        label = (node.get("label") or "").strip()
        if key:
            keys.add(key)
            labels[key] = label or key
    return frozenset(keys), labels


CANONICAL_NODES: frozenset
DISPLAY_LABELS: dict[str, str]
CANONICAL_NODES, DISPLAY_LABELS = _build_canonical_nodes()

# ─────────────────────────────────────────────────────────────────────────────
# Alias map: non-canonical string → canonical node key
#
# These aliases arise from:
#   1. Sector field display values in portfolio CSVs (Title Case with spaces)
#      being uppercased and used as node keys in exposure maps
#   2. Legacy UI labels and report strings
#   3. Fidelity/provider CSV sector column values with spaces
#
# All lookups are against the UPPERCASED version of the input string.
# ─────────────────────────────────────────────────────────────────────────────

# Maps uppercased non-canonical string → canonical node key
_ALIAS_MAP: dict[str, str] = {
    # ── Fixed Income aliases ──────────────────────────────────────────────────
    "FIXED INCOME":                     "FIXED_INCOME",
    "FIXED-INCOME":                     "FIXED_INCOME",
    "BONDS":                            "FIXED_INCOME",
    "BOND":                             "FIXED_INCOME",
    "FIXED INCOME.US":                  "FIXED_INCOME.US",
    "FIXED INCOME.INTERNATIONAL":       "FIXED_INCOME.INTERNATIONAL",
    "FIXED INCOME.INFLATION PROTECTED": "FIXED_INCOME.INFLATION_PROTECTED",
    "INFLATION PROTECTED":              "FIXED_INCOME.INFLATION_PROTECTED",
    "INFLATION-PROTECTED":              "FIXED_INCOME.INFLATION_PROTECTED",
    "TIPS":                             "FIXED_INCOME.INFLATION_PROTECTED",
    # ── Digital Asset aliases ─────────────────────────────────────────────────
    "DIGITAL ASSETS":                   "DIGITAL",
    "DIGITAL_ASSETS":                   "DIGITAL",
    "CRYPTO":                           "DIGITAL",
    "CRYPTOCURRENCY":                   "DIGITAL",
    "DIGITAL ASSET":                    "DIGITAL",
    # ── Equities aliases ──────────────────────────────────────────────────────
    "EQUITY":                           "EQUITIES",
    "STOCKS":                           "EQUITIES",
    "STOCK":                            "EQUITIES",
    "US EQUITY":                        "EQUITIES.US",
    "US EQUITIES":                      "EQUITIES.US",
    "U.S. EQUITY":                      "EQUITIES.US",
    "U.S. EQUITIES":                    "EQUITIES.US",
    "DOMESTIC EQUITY":                  "EQUITIES.US",
    "DOMESTIC EQUITIES":                "EQUITIES.US",
    "INTERNATIONAL EQUITY":             "EQUITIES.INTERNATIONAL",
    "INTERNATIONAL EQUITIES":           "EQUITIES.INTERNATIONAL",
    "INTL EQUITY":                      "EQUITIES.INTERNATIONAL",
    "EMERGING MARKETS":                 "EQUITIES.EMERGING_MARKETS",
    "EMERGING MARKET":                  "EQUITIES.EMERGING_MARKETS",
    "EMERGING MARKETS EQUITY":          "EQUITIES.EMERGING_MARKETS",
    "EM EQUITY":                        "EQUITIES.EMERGING_MARKETS",
    # ── Commodities aliases ───────────────────────────────────────────────────
    "COMMODITY":                        "COMMODITIES",
    "GOLD":                             "COMMODITIES.GOLD",
    "PRECIOUS METALS":                  "COMMODITIES.GOLD",
    "ENERGY":                           "COMMODITIES.ENERGY",
    "BROAD COMMODITY":                  "COMMODITIES.BROAD_BASKET",
    "BROAD_COMMODITY":                  "COMMODITIES.BROAD_BASKET",
    "BROAD COMMODITIES":                "COMMODITIES.BROAD_BASKET",
    "BROAD BASKET":                     "COMMODITIES.BROAD_BASKET",
    "BROAD_BASKET":                     "COMMODITIES.BROAD_BASKET",
    "COMMODITIES.BROAD_COMMODITY":      "COMMODITIES.BROAD_BASKET",
    "COMMODITIES.BROAD":                "COMMODITIES.BROAD_BASKET",
    # ── Cash aliases ──────────────────────────────────────────────────────────
    "CASH AND EQUIVALENTS":             "CASH",
    "CASH EQUIVALENT":                  "CASH",
    "CASH EQUIVALENTS":                 "CASH",
    "MONEY MARKET":                     "CASH",
    "MONEY MARKETS":                    "CASH",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def normalize_node_key(key: str) -> str:
    """Return the canonical node key for ``key``, or ``key`` (uppercased) if
    already canonical or no alias is found.

    Normalization is case-insensitive: the input is uppercased for lookup.
    """
    if not key:
        return key
    upper = key.strip().upper()
    # Direct canonical match
    if upper in CANONICAL_NODES:
        return upper
    # Alias lookup
    canonical = _ALIAS_MAP.get(upper)
    if canonical is not None:
        return canonical
    # Unknown — return uppercased as-is
    return upper


def is_canonical(key: str) -> bool:
    """Return True if ``key`` is a canonical node key in the taxonomy."""
    return (key or "").strip().upper() in CANONICAL_NODES


def display_label(key: str) -> str:
    """Return the human-readable display label for a node key.

    Falls back to the canonical key string if no label is registered.
    """
    canonical = normalize_node_key(key)
    return DISPLAY_LABELS.get(canonical, canonical)


def find_aliases_in_collection(node_keys: list[str]) -> list[tuple[str, str | None]]:
    """Return ``[(alias, canonical_or_None)]`` for every non-canonical key found.

    A canonical key is silently skipped.  An alias key returns its canonical
    target.  A completely unknown key returns ``(key, None)``.
    """
    result: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for key in node_keys:
        upper = (key or "").strip().upper()
        if not upper or upper in seen:
            continue
        seen.add(upper)
        if upper in CANONICAL_NODES:
            continue  # Already canonical — no issue
        canonical = _ALIAS_MAP.get(upper)
        result.append((key, canonical))
    return result
