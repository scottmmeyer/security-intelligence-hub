"""Mandate-specific allocation archetype loader.

Maps each PMI mandate type to a YAML-based allocation profile that defines
target weights for every node in the allocation hierarchy.

This is the Phase 6.3 extension point: profiles live in
  config/allocation_models/<profile>.yaml
and are loaded at runtime during run_analysis().  The result is a plain
dict[str, float] suitable for passing to compute_alignment() as
targets_override.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODELS_DIR = _REPO_ROOT / "config" / "allocation_models"

# Map mandate_type → profile filename
_PROFILE_FILES: dict[str, str] = {
    "CONCENTRATED_ALPHA": "concentrated_alpha_profile.yaml",
    "GROWTH":             "growth_allocation_profile.yaml",
    "BALANCED":           "balanced_allocation_profile.yaml",
    # Fallback: mandates without dedicated profiles use nearest analog
    "DEFENSIVE":          "balanced_allocation_profile.yaml",
    "INCOME":             "balanced_allocation_profile.yaml",
    "REPLAY_OPTIMIZED":   "growth_allocation_profile.yaml",
}

DEFAULT_MANDATE = "CONCENTRATED_ALPHA"


def load_archetype_targets(mandate_type: str) -> dict[str, float]:
    """Return {node_key: target_pct_of_total} for the given mandate type.

    Falls back to an empty dict if the profile file cannot be loaded,
    allowing compute_alignment() to degrade gracefully to the seed CSV.
    """
    key = (mandate_type or "").strip().upper()
    filename = _PROFILE_FILES.get(key, "balanced_allocation_profile.yaml")
    path = _MODELS_DIR / filename
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        nodes = data.get("nodes", {})
        return {k: float(v) for k, v in nodes.items()}
    except Exception:
        return {}


def get_archetype_display_name(mandate_type: str) -> Optional[str]:
    """Return the display_name from the profile YAML, or None if unavailable."""
    key = (mandate_type or "").strip().upper()
    filename = _PROFILE_FILES.get(key)
    if not filename:
        return None
    path = _MODELS_DIR / filename
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data.get("display_name")
    except Exception:
        return None
