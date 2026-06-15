"""Deterministic policy-aware funding and reduction ranking for CRA.

PRA-IMPL-02 scope:
- Rank reduction candidates with explicit reasons and reproducible scores.
- Attach funding source recommendations to deployment targets.

Non-negotiable:
- Read-only relative to upstream scoring engines (CW-DAS, ESS, replay, PMI).
- No hidden/random scoring; deterministic tie-breakers by symbol.
"""

from __future__ import annotations

import dataclasses
from typing import Dict, List

from .models import CapitalSourceRecord, RotationDeploymentTarget


_CATEGORY_BASE = {
    "SIGNAL_DETERIORATION": 90.0,
    "STRATEGIC_EXIT": 84.0,
    "OVERWEIGHT_REDUCTION": 76.0,
    "TAX_AWARE_EXIT": 62.0,
    "LOW_CONVICTION_REDUCTION": 55.0,
}

_PRIORITY_BONUS = {
    "URGENT": 20.0,
    "HIGH": 12.0,
    "MODERATE": 6.0,
    "LOW": 2.0,
    "DEFER": -10.0,
}


def _ess_bonus(ess_score_text: str | None) -> float:
    ess = str(ess_score_text or "").upper()
    if ess == "VERY_BEARISH":
        return 12.0
    if ess == "BEARISH":
        return 7.0
    if ess == "BULLISH":
        return -8.0
    return 0.0


def _signal_bonus(signal_direction: str | None) -> float:
    signal = str(signal_direction or "").upper()
    if signal == "BEARISH":
        return 8.0
    if signal == "BULLISH":
        return -7.0
    return 0.0


def _tax_penalty(tax_bucket: str | None) -> float:
    bucket = str(tax_bucket or "").upper()
    if bucket == "A":
        return 4.0
    if bucket == "D":
        return -10.0
    if bucket == "E":
        return -7.0
    return 0.0


def _policy_penalty(policy_type: str | None) -> float:
    policy = str(policy_type or "").upper()
    if policy == "SELL_LAST":
        return -5.0
    if policy == "CORE_ANCHOR":
        return -8.0
    if policy == "DO_NOT_SELL":
        return -100.0
    return 0.0


def _conviction_penalty(source_symbol: str, deployment_queue: dict[str, dict]) -> float:
    row = deployment_queue.get(source_symbol.upper())
    if row is None:
        return 0.0
    tier = str(row.get("narrative_tier", "")).upper()
    rank = int(float(str(row.get("rank", 999) or 999)))
    if tier == "CORE_CONVICTION_LEADER":
        return -22.0
    if tier == "HIGH_CONVICTION_ANCHOR":
        return -13.0
    # Slightly protect higher-ranked names even when tier is missing.
    if rank <= 5:
        return -8.0
    return -2.0


def _reason_for_source(source: CapitalSourceRecord) -> str:
    if source.category == "SIGNAL_DETERIORATION":
        return "Weak signal posture and deterioration evidence justify reducing this holding first."
    if source.category == "STRATEGIC_EXIT":
        return "Strategic exit designation makes this a policy-prioritized funding source."
    if source.category == "OVERWEIGHT_REDUCTION":
        drift = float(source.drift_pct or 0.0)
        return f"Over-allocation drift ({drift:+.1f}pp) is reduced while funding higher-conviction targets."
    if source.category == "TAX_AWARE_EXIT":
        return "Tax-aware posture supports harvesting this position before touching stronger conviction names."
    if source.category == "LOW_CONVICTION_REDUCTION":
        return "Opportunity-cost reduction frees capital from lower-conviction exposure."
    return "Policy-aware reduction candidate."


def _alignment_reason(source: CapitalSourceRecord) -> str:
    return (
        "Aligned with concentrated-alpha philosophy: rotate from weaker or over-allocated "
        "exposures into higher-conviction opportunities with explicit policy constraints."
    )


def score_reduction_candidates(
    *,
    sources: List[CapitalSourceRecord],
    deployment_queue: List[dict],
) -> List[CapitalSourceRecord]:
    """Return sources with deterministic reduction scores and explicit rationale fields."""
    queue_by_symbol = {
        str(row.get("symbol", "")).upper(): row
        for row in deployment_queue
        if str(row.get("symbol", "")).strip()
    }

    scored: List[CapitalSourceRecord] = []
    for src in sources:
        base = _CATEGORY_BASE.get(src.category, 40.0)
        score = base
        score += _PRIORITY_BONUS.get(src.priority, 0.0)
        score += _ess_bonus(src.ess_score_text)
        score += _signal_bonus(src.signal_direction)
        score += min(18.0, max(0.0, float(src.drift_pct or 0.0)))
        score += _tax_penalty(src.tax_bucket)
        score += _policy_penalty(src.policy_type)
        score += _conviction_penalty(src.symbol, queue_by_symbol)

        if src.blocked_by_policy:
            score = 0.0

        scored.append(
            dataclasses.replace(
                src,
                reduction_reason=_reason_for_source(src),
                reduction_score=round(max(0.0, score), 2),
                policy_alignment_reason=_alignment_reason(src),
            )
        )

    scored.sort(
        key=lambda s: (
            -float(s.reduction_score),
            -float(s.estimated_proceeds),
            str(s.symbol),
        )
    )
    return scored


def annotate_deployments_with_funding_plan(
    *,
    deployments: List[RotationDeploymentTarget],
    sources: List[CapitalSourceRecord],
) -> List[RotationDeploymentTarget]:
    """Attach top funding source + alternatives to every deployment target.

    Ranking is deterministic and shared across targets; per-target exclusion only
    prevents self-funding from the same symbol.
    """
    actionable = [
        s for s in sources
        if not s.blocked_by_policy and s.priority != "DEFER" and float(s.estimated_proceeds) > 0
    ]
    actionable.sort(
        key=lambda s: (
            -float(s.reduction_score),
            -float(s.estimated_proceeds),
            str(s.symbol),
        )
    )

    remaining_capacity: Dict[str, float] = {
        s.symbol: float(s.estimated_proceeds) for s in actionable
    }

    out: List[RotationDeploymentTarget] = []
    for target in deployments:
        candidates = [
            s for s in actionable
            if s.symbol != target.symbol and remaining_capacity.get(s.symbol, 0.0) > 0.0
        ]
        if not candidates:
            out.append(target)
            continue

        required = max(0.0, float(target.suggested_amount))
        remaining_required = required
        contributors: List[CapitalSourceRecord] = []

        for candidate in candidates:
            available = max(0.0, float(remaining_capacity.get(candidate.symbol, 0.0)))
            if available <= 0.0:
                continue
            if required <= 0.0:
                contributors.append(candidate)
                break

            draw = min(available, remaining_required)
            if draw <= 0.0:
                continue

            remaining_capacity[candidate.symbol] = round(available - draw, 2)
            contributors.append(candidate)
            remaining_required = round(remaining_required - draw, 2)

            if remaining_required <= 0.0:
                break

        if not contributors:
            out.append(target)
            continue

        primary = contributors[0]
        remaining_candidates = [
            s for s in actionable
            if s.symbol != target.symbol
            and s.symbol != primary.symbol
            and remaining_capacity.get(s.symbol, 0.0) > 0.0
        ]
        alternatives = [
            f"{s.symbol} ({s.category.replace('_', ' ')}, score {s.reduction_score:.1f})"
            for s in remaining_candidates[:3]
        ]
        reason = (
            f"{primary.reduction_reason} Preferred over alternatives due to higher "
            f"policy-aware reduction score ({primary.reduction_score:.1f})."
        )

        out.append(
            dataclasses.replace(
                target,
                funding_source_symbol=primary.symbol,
                funding_source_category=primary.category,
                funding_source_reason=reason,
                funding_source_score=float(primary.reduction_score),
                funding_source_alternatives=alternatives,
                funding_policy_alignment_reason=primary.policy_alignment_reason,
            )
        )

    return out
