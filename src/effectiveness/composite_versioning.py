"""Composite version registry.

Tracks metadata about each versioned composite score formula.  Historical rows
are NEVER retroactively mutated; this registry is purely additive.

Design principles
-----------------
* ``composite_score`` in ``analytical_universe.csv`` is always the **production v1**
  score.  It must not be silently overwritten.
* Experimental versions are stored in separate named columns.
* ``composite_version`` on each row identifies which formula produced the
  production ``composite_score`` value — defaults to ``"v1"`` for all rows built
  before this framework was introduced.
* Each version entry carries its weight map so downstream tools can audit
  exactly what produced a given score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class CompositeVersion:
    """Immutable descriptor for a composite scoring formula version."""

    version_id: str
    """Unique version identifier, e.g. ``"v1"`` or ``"v2_yahoo_exp_20260522"``."""
    description: str
    """Human-readable description of what distinguishes this version."""
    weights: Dict[str, float]
    """Base signal weights *before* renormalization.  Keys: ess, zacks, danelfin, yahoo."""
    introduced_date: str
    """ISO date (YYYY-MM-DD) when this version was introduced."""
    status: str
    """PRODUCTION | EXPERIMENTAL | DEPRECATED."""
    column: str
    """CSV column that stores this version's score."""


# ---------------------------------------------------------------------------
# Registry — add new versions here; never remove or mutate existing entries.
# ---------------------------------------------------------------------------
COMPOSITE_VERSION_REGISTRY: Dict[str, CompositeVersion] = {
    "v1": CompositeVersion(
        version_id="v1",
        description=(
            "Production baseline.  ESS-heavy weighted average renormalized over "
            "available signals.  Yahoo weight reserved but unpopulated (yahoo_score "
            "always empty in production)."
        ),
        weights={"ess": 0.55, "zacks": 0.25, "danelfin": 0.10, "yahoo": 0.10},
        introduced_date="2025-01-01",
        status="PRODUCTION",
        column="composite_score",
    ),
    "v2_yahoo_exp_20260522": CompositeVersion(
        version_id="v2_yahoo_exp_20260522",
        description=(
            "Experimental.  Adds Yahoo ABR (normalized: 6-abr) as a live signal at "
            "10% weight.  ESS reduced to 50%, Zacks to 22.5%, Danelfin increased to "
            "17.5%.  Renormalized over available signals.  NOT production; requires "
            "effectiveness validation before promotion."
        ),
        weights={"ess": 0.50, "zacks": 0.225, "danelfin": 0.175, "yahoo": 0.10},
        introduced_date="2026-05-22",
        status="EXPERIMENTAL",
        column="composite_v2_yahoo",
    ),
}

# Shorthand alias used by generate_v2_scores.py and UI layer.
V2_YAHOO = COMPOSITE_VERSION_REGISTRY["v2_yahoo_exp_20260522"]
V1 = COMPOSITE_VERSION_REGISTRY["v1"]


def get_version(version_id: str) -> CompositeVersion:
    """Look up a version by ID; raises ``KeyError`` for unknown versions."""
    return COMPOSITE_VERSION_REGISTRY[version_id]


def list_versions(status_filter: str | None = None) -> list[CompositeVersion]:
    """Return all registered versions, optionally filtered by status string."""
    versions = list(COMPOSITE_VERSION_REGISTRY.values())
    if status_filter:
        versions = [v for v in versions if v.status == status_filter.upper()]
    return versions
