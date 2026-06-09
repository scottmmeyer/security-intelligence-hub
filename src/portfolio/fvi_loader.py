"""PRA-IMPL-05 — Fund Vehicle Intelligence (FVI) Phase 1 loader.

Loads advisory-only FVI peer group records from config/fvi_peer_groups.yaml
and exposes them as a simple symbol-keyed dict.

Design constraints:
- Advisory-only; never mutates scores, recommendations, or ranking.
- No external provider calls; Phase 1 uses manual config estimates.
- Graceful degradation: missing FVI data produces no error and no output.
- All outputs are informational metadata only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FVI_CONFIG = _REPO_ROOT / "config" / "fvi_peer_groups.yaml"

# Tier ordering for display (lower index = higher quality)
FVI_TIER_ORDER = {"ELITE": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "WEAK": 4}

# CSS-class-safe tier identifiers
FVI_TIER_CSS = {
    "ELITE":  "fvi-elite",
    "HIGH":   "fvi-high",
    "MEDIUM": "fvi-medium",
    "LOW":    "fvi-low",
    "WEAK":   "fvi-weak",
}


def load_fvi_registry(config_path: str | Path | None = None) -> dict[str, dict]:
    """Load FVI peer group registry from YAML config.

    Returns a symbol-keyed dict of FVI records.  Returns an empty dict if the
    config file is missing or malformed — FVI is advisory only and must never
    block pipeline execution.

    Each record contains:
        symbol, peer_group, morningstar_category, fvi_tier, estimated_fvi_score,
        confidence, data_source, advisory_text, retain_advisory, vehicle_type,
        asset_class, geography

    Args:
        config_path: Override path to YAML file. Defaults to config/fvi_peer_groups.yaml.

    Returns:
        dict mapping uppercase symbol → FVI record dict.
    """
    path = Path(config_path) if config_path else _FVI_CONFIG
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(raw, dict):
        return {}

    funds = raw.get("funds", {})
    if not isinstance(funds, dict):
        return {}

    registry: dict[str, dict] = {}
    for sym, record in funds.items():
        if not isinstance(record, dict):
            continue
        sym_upper = str(sym).strip().upper()
        registry[sym_upper] = {
            "symbol":               sym_upper,
            "peer_group":           record.get("peer_group", ""),
            "morningstar_category": record.get("morningstar_category", ""),
            "asset_class":          record.get("asset_class", ""),
            "geography":            record.get("geography", ""),
            "vehicle_type":         record.get("vehicle_type", ""),
            "fvi_tier":             str(record.get("fvi_tier", "")).upper(),
            "estimated_fvi_score":  record.get("estimated_fvi_score"),
            "confidence":           record.get("confidence", "LOW"),
            "data_source":          record.get("data_source", "MANUAL_ADVISORY_ESTIMATE"),
            "advisory_text":        record.get("advisory_text", ""),
            "retain_advisory":      bool(record.get("retain_advisory", False)),
        }
    return registry


def get_fvi_record(symbol: str, registry: dict[str, dict]) -> Optional[dict]:
    """Look up FVI record for a symbol.  Returns None if not found."""
    return registry.get(str(symbol).strip().upper())


def build_fvi_data_for_holdings(
    symbols: list[str],
    registry: dict[str, dict],
) -> dict[str, dict]:
    """Build a symbol-keyed FVI data dict for a list of portfolio holdings.

    Only includes symbols present in the registry.  Missing symbols are silently
    omitted — graceful degradation.

    Args:
        symbols:  List of portfolio holding symbols.
        registry: Loaded FVI registry (from load_fvi_registry).

    Returns:
        dict mapping uppercase symbol → FVI record for symbols with FVI data.
    """
    result: dict[str, dict] = {}
    for sym in symbols:
        sym_upper = str(sym).strip().upper()
        rec = registry.get(sym_upper)
        if rec is not None:
            result[sym_upper] = rec
    return result
