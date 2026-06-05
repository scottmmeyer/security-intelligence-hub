"""Capital Rotation Advisor (CRA) package.

Phase 23.6A — Read-only composition layer that bridges capital sources
(sell candidates) to deployment targets (CW-DAS queue).

Non-negotiable boundaries:
  - No modification to CW-DAS, ESS, Replay, FMI, or Policy engine.
  - All scoring from upstream outputs; CRA produces only new artifacts.
  - Operator authority is preserved; CRA is guidance, not execution.
"""

from .models import (
    CapitalSourceRecord,
    RotationDeploymentTarget,
    PortfolioImpactEstimate,
    RotationProposal,
)

__all__ = [
    "CapitalSourceRecord",
    "RotationDeploymentTarget",
    "PortfolioImpactEstimate",
    "RotationProposal",
]
