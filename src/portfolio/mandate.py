"""Phase 6.2A/B/C/D — Portfolio Mandate Intelligence (PMI) evaluation engine.

PMI is a pure interpretation layer.

Governance:
  - NEVER modifies decomposition, suitability, replay, or exposure calculations.
  - Only the interpretation of drift and recommendation urgency changes.
  - All underlying AllocationAlignmentResult data is preserved unchanged.

Public API:
  get_mandate(mandate_type)              → PortfolioMandate
  list_mandate_types()                   → list[str]
  evaluate_drift_under_mandate(...)      → MandateDriftInterpretation
  evaluate_alignment_under_mandate(...)  → list[MandateDriftInterpretation]
  get_cash_interpretation(...)           → str
  build_mandate_recommendation_overlay(...)  → dict
"""

from __future__ import annotations

from typing import Optional

from .models import (
    AllocationAlignmentResult,
    MandateDriftInterpretation,
    PortfolioMandate,
    PortfolioRecommendation,
)


# ─────────────────────────────────────────────────────────────────────────────
# Mandate Registry
# ─────────────────────────────────────────────────────────────────────────────

_MANDATE_REGISTRY: dict[str, PortfolioMandate] = {
    "BALANCED": PortfolioMandate(
        mandate_type="BALANCED",
        display_name="Balanced",
        description=(
            "Traditional balanced portfolio. Diversification is the primary goal. "
            "Target adherence is important. Moderate tolerance for all deviations."
        ),
        concentration_tolerance=0.3,
        cash_tolerance=0.3,
        fixed_income_tolerance=0.2,
        small_cap_tolerance=0.4,
        thematic_concentration_tolerance=0.3,
        replay_alignment_priority=0.5,
        turnover_tolerance=0.5,
        diversification_priority=0.7,
        target_adherence_priority=0.7,
    ),
    "GROWTH": PortfolioMandate(
        mandate_type="GROWTH",
        display_name="Growth",
        description=(
            "Growth-oriented mandate. Higher small-cap and equity concentration "
            "is acceptable. Fixed income shortfalls are tolerated. Replay "
            "opportunities are favored over target model adherence."
        ),
        concentration_tolerance=0.6,
        cash_tolerance=0.5,
        fixed_income_tolerance=0.7,
        small_cap_tolerance=0.7,
        thematic_concentration_tolerance=0.6,
        replay_alignment_priority=0.7,
        turnover_tolerance=0.6,
        diversification_priority=0.4,
        target_adherence_priority=0.4,
    ),
    "DEFENSIVE": PortfolioMandate(
        mandate_type="DEFENSIVE",
        display_name="Defensive",
        description=(
            "Capital preservation mandate. Fixed income allocation is critical. "
            "Equity concentration risk must be controlled. Diversification is "
            "the paramount objective."
        ),
        concentration_tolerance=0.2,
        cash_tolerance=0.4,
        fixed_income_tolerance=0.1,
        small_cap_tolerance=0.2,
        thematic_concentration_tolerance=0.2,
        replay_alignment_priority=0.4,
        turnover_tolerance=0.3,
        diversification_priority=0.8,
        target_adherence_priority=0.8,
    ),
    "INCOME": PortfolioMandate(
        mandate_type="INCOME",
        display_name="Income",
        description=(
            "Income generation mandate. Fixed income allocation is the highest "
            "priority. Yield-generating assets preferred. Moderate diversification "
            "goal with stability emphasis."
        ),
        concentration_tolerance=0.3,
        cash_tolerance=0.3,
        fixed_income_tolerance=0.0,
        small_cap_tolerance=0.2,
        thematic_concentration_tolerance=0.3,
        replay_alignment_priority=0.3,
        turnover_tolerance=0.3,
        diversification_priority=0.6,
        target_adherence_priority=0.7,
    ),
    "REPLAY_OPTIMIZED": PortfolioMandate(
        mandate_type="REPLAY_OPTIMIZED",
        display_name="Replay Optimized",
        description=(
            "Evidence-driven mandate prioritizing replay-supported asymmetric "
            "opportunities. Cash reserves are welcome as deployment capital. "
            "The target model is a reference, not a constraint."
        ),
        concentration_tolerance=0.7,
        cash_tolerance=0.7,
        fixed_income_tolerance=0.8,
        small_cap_tolerance=0.7,
        thematic_concentration_tolerance=0.6,
        replay_alignment_priority=1.0,
        turnover_tolerance=0.8,
        diversification_priority=0.3,
        target_adherence_priority=0.3,
    ),
    "CONCENTRATED_ALPHA": PortfolioMandate(
        mandate_type="CONCENTRATED_ALPHA",
        display_name="Concentrated Alpha",
        description=(
            "High-conviction concentrated mandate. Target drift is intentionally "
            "accepted. Concentration is a deliberate feature. Diversification "
            "is a low priority relative to conviction-weighted positioning."
        ),
        concentration_tolerance=0.9,
        cash_tolerance=0.6,
        fixed_income_tolerance=0.9,
        small_cap_tolerance=0.8,
        thematic_concentration_tolerance=0.8,
        replay_alignment_priority=0.9,
        turnover_tolerance=0.7,
        diversification_priority=0.1,
        target_adherence_priority=0.2,
    ),
}


def get_mandate(mandate_type: str) -> PortfolioMandate:
    """Return the registered mandate for the given type.  Defaults to BALANCED."""
    return _MANDATE_REGISTRY.get(mandate_type, _MANDATE_REGISTRY["BALANCED"])


def list_mandate_types() -> list[str]:
    """Return all registered mandate type strings."""
    return list(_MANDATE_REGISTRY.keys())


# ─────────────────────────────────────────────────────────────────────────────
# Node classification helpers
# ─────────────────────────────────────────────────────────────────────────────

def _node_dimension_class(node_key: str) -> str:
    """Classify the allocation node for mandate tolerance look-up.

    Returns one of: CASH | FIXED_INCOME | EQUITY_SMALL_CAP | EQUITY | OTHER
    """
    nk = node_key.upper()
    if nk == "CASH":
        return "CASH"
    if nk.startswith("FIXED_INCOME"):
        return "FIXED_INCOME"
    if nk.startswith("EQUITIES."):
        parts = nk.split(".")
        # EQUITIES.<geo>.SMALL  or  EQUITIES.<geo>.MICRO
        if len(parts) >= 3 and parts[2] in ("SMALL", "MICRO"):
            return "EQUITY_SMALL_CAP"
        return "EQUITY"
    return "OTHER"


def _tolerance_for_node(
    dim_class: str,
    direction: str,
    mandate: PortfolioMandate,
) -> float:
    """Return the mandate tolerance [0.0–1.0] for a node + direction combination.

    Higher tolerance = mandate is more permissive about this type of deviation.
    """
    if dim_class == "CASH":
        return mandate.cash_tolerance
    if dim_class == "FIXED_INCOME":
        if direction == "UNDERWEIGHT":
            # fixed_income_tolerance directly expresses how acceptable an FI shortfall is.
            # Low tolerance (INCOME=0.0, DEFENSIVE=0.1) → STRICT → severity elevated.
            # High tolerance (GROWTH=0.7, CONCENTRATED_ALPHA=0.9) → TOLERATED/INTENTIONAL.
            return mandate.fixed_income_tolerance
        return mandate.fixed_income_tolerance
    if dim_class == "EQUITY_SMALL_CAP":
        return mandate.small_cap_tolerance
    if dim_class == "EQUITY":
        return mandate.concentration_tolerance
    # OTHER: use target adherence as the tolerance proxy
    return 1.0 - mandate.target_adherence_priority


# ─────────────────────────────────────────────────────────────────────────────
# Severity adjustment
# ─────────────────────────────────────────────────────────────────────────────

_SEVERITY_ORDER = ("NONE", "LOW", "MODERATE", "HIGH")


def _adjust_severity(raw: str, steps: int) -> str:
    """Shift severity up (negative steps) or down (positive steps) the ladder."""
    idx = _SEVERITY_ORDER.index(raw) if raw in _SEVERITY_ORDER else 2
    return _SEVERITY_ORDER[max(0, min(len(_SEVERITY_ORDER) - 1, idx - steps))]


# ─────────────────────────────────────────────────────────────────────────────
# Core evaluation function
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_drift_under_mandate(
    node_key: str,
    node_label: str,
    raw_drift_pct: float,
    raw_severity: str,
    drift_direction: str,
    mandate: PortfolioMandate,
) -> MandateDriftInterpretation:
    """Return the mandate-adjusted interpretation for a single alignment node.

    Governance:
        Only interpretation changes.  raw_drift_pct is preserved exactly.
        Exposure, decomposition, and replay data are not touched.

    Args:
        node_key:       e.g. "EQUITIES.US.SMALL"
        node_label:     human-readable label, e.g. "US Small Cap"
        raw_drift_pct:  alignment engine drift (actual − tactical_target)
        raw_severity:   alignment engine severity (HIGH|MODERATE|LOW|NONE)
        drift_direction: OVERWEIGHT|UNDERWEIGHT|ON_TARGET
        mandate:        active PortfolioMandate instance
    """
    # ON_TARGET or no severity → always pass through unchanged
    if drift_direction == "ON_TARGET" or raw_severity == "NONE":
        return MandateDriftInterpretation(
            node_key=node_key,
            node_label=node_label,
            mandate_type=mandate.mandate_type,
            raw_drift_pct=raw_drift_pct,
            raw_severity=raw_severity,
            mandate_severity=raw_severity,
            mandate_drift_label="ON_TARGET",
            mandate_urgency="INFORMATIONAL",
            mandate_rationale=(
                f"{node_label} is within target range under the "
                f"{mandate.display_name} mandate."
            ),
            suppress_recommendation=True,
        )

    dim_class = _node_dimension_class(node_key)
    tolerance = _tolerance_for_node(dim_class, drift_direction, mandate)

    # Map tolerance level → downgrade steps and label suffix
    # tolerance >= 0.8: INTENTIONAL — drift accepted as portfolio policy
    # tolerance >= 0.6: TOLERATED   — drift acceptable, reduction optional
    # tolerance >= 0.4: STANDARD    — drift is a concern, severity unchanged
    # tolerance <  0.4: STRICT      — severity may be elevated (FI underweight)
    if tolerance >= 0.8:
        downgrade_steps = 2
        label_suffix = "INTENTIONAL"
        # Suppress only if raw severity was not HIGH; HIGH conviction still surfaces
        suppress = raw_severity in ("LOW", "MODERATE")
    elif tolerance >= 0.6:
        downgrade_steps = 1
        label_suffix = "TOLERATED"
        suppress = raw_severity == "LOW"
    elif tolerance >= 0.4:
        downgrade_steps = 0
        label_suffix = "STANDARD"
        suppress = False
    else:
        # Strict: FI underweight under INCOME/DEFENSIVE may be elevated
        if (
            dim_class == "FIXED_INCOME"
            and drift_direction == "UNDERWEIGHT"
            and raw_severity in ("LOW", "MODERATE")
        ):
            downgrade_steps = -1   # elevate
        else:
            downgrade_steps = 0
        label_suffix = "STANDARD"
        suppress = False

    mandate_severity = _adjust_severity(raw_severity, downgrade_steps)

    # Drift label
    if drift_direction == "OVERWEIGHT":
        mandate_drift_label = f"{label_suffix}_OVERWEIGHT"
    else:
        mandate_drift_label = f"{label_suffix}_UNDERWEIGHT"

    # Urgency
    if suppress:
        mandate_urgency = "INFORMATIONAL"
    else:
        _urgency_map = {
            "HIGH": "URGENT",
            "MODERATE": "MODERATE",
            "LOW": "LOW",
            "NONE": "INFORMATIONAL",
        }
        mandate_urgency = _urgency_map.get(mandate_severity, "LOW")

    # Rationale narrative
    mandate_rationale = _build_drift_rationale(
        node_label=node_label,
        drift_pct=raw_drift_pct,
        direction=drift_direction,
        raw_severity=raw_severity,
        mandate_severity=mandate_severity,
        mandate=mandate,
        dim_class=dim_class,
        label_suffix=label_suffix,
        suppress=suppress,
    )

    return MandateDriftInterpretation(
        node_key=node_key,
        node_label=node_label,
        mandate_type=mandate.mandate_type,
        raw_drift_pct=raw_drift_pct,
        raw_severity=raw_severity,
        mandate_severity=mandate_severity,
        mandate_drift_label=mandate_drift_label,
        mandate_urgency=mandate_urgency,
        mandate_rationale=mandate_rationale,
        suppress_recommendation=suppress,
    )


def evaluate_alignment_under_mandate(
    alignment_results: list,
    mandate: PortfolioMandate,
) -> list[MandateDriftInterpretation]:
    """Apply mandate interpretation to all alignment results.

    Returns one MandateDriftInterpretation per AllocationAlignmentResult.
    The result list has the same length and order as alignment_results.
    """
    interpretations = []
    for ar in alignment_results:
        if hasattr(ar, "node_key"):
            nk = ar.node_key
            nl = ar.node_label
            rd = ar.drift_pct
            rs = ar.severity
            dd = ar.drift_direction
        else:
            nk = ar.get("node_key", "")
            nl = ar.get("node_label", nk)
            rd = float(ar.get("drift_pct") or 0)
            rs = ar.get("severity", "NONE")
            dd = ar.get("drift_direction", "ON_TARGET")

        interpretations.append(
            evaluate_drift_under_mandate(nk, nl, rd, rs, dd, mandate)
        )
    return interpretations


# ─────────────────────────────────────────────────────────────────────────────
# Cash and fixed income context labels (Phase 6.2C / 6.2D)
# ─────────────────────────────────────────────────────────────────────────────

_CASH_EXCESS_LABELS: dict[str, str] = {
    "BALANCED":          "Cash reserve — overweight vs target model.",
    "GROWTH":            "Moderate opportunity reserve — available for selective deployment.",
    "DEFENSIVE":         "Safety buffer — appropriate for capital preservation mandate.",
    "INCOME":            "Uninvested cash — opportunity cost vs income generation objectives.",
    "REPLAY_OPTIMIZED":  "Deployment reserve — held for asymmetric replay opportunities.",
    "CONCENTRATED_ALPHA": "Dry powder — strategic reserve for high-conviction entries.",
}

_CASH_DEFICIT_LABEL = "Cash is below target — consider liquidity needs."

_FI_SHORTFALL_URGENCY: dict[str, str] = {
    "BALANCED":          "moderate",
    "GROWTH":            "low",
    "DEFENSIVE":         "critical",
    "INCOME":            "critical",
    "REPLAY_OPTIMIZED":  "low",
    "CONCENTRATED_ALPHA": "minimal",
}


def get_cash_interpretation(
    cash_actual_pct: float,
    cash_target_pct: float,
    mandate: PortfolioMandate,
) -> str:
    """Return the mandate-specific narrative label for the portfolio's cash position."""
    if cash_actual_pct <= cash_target_pct:
        return _CASH_DEFICIT_LABEL
    excess = cash_actual_pct - cash_target_pct
    base = _CASH_EXCESS_LABELS.get(
        mandate.mandate_type,
        f"Cash is {excess:.1f}pp above target.",
    )
    return f"{base} ({excess:.1f}pp above target)"


def get_fixed_income_shortfall_urgency(mandate: PortfolioMandate) -> str:
    """Return the mandate-specific urgency label for a fixed income shortfall."""
    return _FI_SHORTFALL_URGENCY.get(mandate.mandate_type, "moderate")


# ─────────────────────────────────────────────────────────────────────────────
# Mandate overlay for recommendation dicts (Phase 6.2G)
# ─────────────────────────────────────────────────────────────────────────────

def build_mandate_recommendation_overlay(
    rec_dict: dict,
    interp: Optional[MandateDriftInterpretation],
    mandate: PortfolioMandate,
) -> dict:
    """Return a mandate-overlay dict suitable for injection into a recommendation dict.

    The overlay contains additive fields — it does NOT replace any existing
    recommendation fields.  Original severity, rationale, priority, etc. are
    preserved in the parent recommendation.
    """
    if interp is None:
        return {
            "mandate_type": mandate.mandate_type,
            "mandate_display_name": mandate.display_name,
            "mandate_severity": rec_dict.get("severity", ""),
            "mandate_urgency": "MODERATE",
            "mandate_drift_label": "",
            "mandate_rationale": "",
            "mandate_narrative": "",
        }

    narrative = _build_recommendation_narrative(rec_dict, interp, mandate)
    return {
        "mandate_type": mandate.mandate_type,
        "mandate_display_name": mandate.display_name,
        "mandate_severity": interp.mandate_severity,
        "mandate_urgency": interp.mandate_urgency,
        "mandate_drift_label": interp.mandate_drift_label,
        "mandate_rationale": interp.mandate_rationale,
        "mandate_narrative": narrative,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Narrative builders (internal)
# ─────────────────────────────────────────────────────────────────────────────

def _build_drift_rationale(
    node_label: str,
    drift_pct: float,
    direction: str,
    raw_severity: str,
    mandate_severity: str,
    mandate: PortfolioMandate,
    dim_class: str,
    label_suffix: str,
    suppress: bool,
) -> str:
    abs_drift = abs(drift_pct)
    direction_str = "above" if direction == "OVERWEIGHT" else "below"

    if label_suffix == "INTENTIONAL":
        if direction == "OVERWEIGHT":
            return (
                f"{node_label} is {abs_drift:.1f}pp {direction_str} target. "
                f"Under the {mandate.display_name} mandate, this concentration level "
                f"is intentionally accepted as portfolio policy. "
                f"No corrective action required unless mandate or conviction changes."
            )
        else:
            return (
                f"{node_label} is {abs_drift:.1f}pp below target. "
                f"Under the {mandate.display_name} mandate, this underweight is "
                f"considered intentional portfolio positioning. "
                f"No corrective action required."
            )

    if label_suffix == "TOLERATED":
        if direction == "OVERWEIGHT":
            return (
                f"{node_label} exceeds target by {abs_drift:.1f}pp. "
                f"Under the {mandate.display_name} mandate, this degree of "
                f"overweight is within tolerated parameters. "
                f"Reduction is optional rather than urgent."
            )
        else:
            return (
                f"{node_label} is {abs_drift:.1f}pp below target. "
                f"Under the {mandate.display_name} mandate, this shortfall is "
                f"tolerated given portfolio objectives. "
                f"Correction is advisory rather than required."
            )

    # STANDARD — severity unchanged or elevated
    if (
        dim_class == "FIXED_INCOME"
        and direction == "UNDERWEIGHT"
        and mandate_severity in ("HIGH", "MODERATE")
    ):
        urgency_label = _FI_SHORTFALL_URGENCY.get(mandate.mandate_type, "moderate")
        return (
            f"{node_label} is {abs_drift:.1f}pp below target. "
            f"The {mandate.display_name} mandate assigns {urgency_label} priority "
            f"to fixed income allocation. This shortfall warrants attention."
        )

    return (
        f"{node_label} is {abs_drift:.1f}pp {direction_str} target. "
        f"Under the {mandate.display_name} mandate, this is a "
        f"{mandate_severity.lower()}-severity allocation concern."
    )


def _build_recommendation_narrative(
    rec_dict: dict,
    interp: MandateDriftInterpretation,
    mandate: PortfolioMandate,
) -> str:
    """Generate a mandate-aware recommendation narrative sentence."""
    label = interp.mandate_drift_label
    node_label = interp.node_label or rec_dict.get("title", "")
    abs_drift = abs(interp.raw_drift_pct)
    direction = "overweight" if "OVERWEIGHT" in label else "underweight"

    if label == "INTENTIONAL_OVERWEIGHT":
        return (
            f"{node_label} exceeds the target model by {abs_drift:.1f}pp. "
            f"Under the {mandate.display_name} mandate, this concentration is "
            f"intentionally accepted. No reduction required unless conviction changes."
        )
    if label == "INTENTIONAL_UNDERWEIGHT":
        return (
            f"{node_label} is {abs_drift:.1f}pp below target. "
            f"Under the {mandate.display_name} mandate, this is considered "
            f"deliberate positioning. No increase required."
        )
    if label == "TOLERATED_OVERWEIGHT":
        return (
            f"{node_label} is {abs_drift:.1f}pp above target. "
            f"Under the {mandate.display_name} mandate, this overweight is within "
            f"tolerated parameters. Reduction is optional rather than urgent."
        )
    if label == "TOLERATED_UNDERWEIGHT":
        return (
            f"{node_label} is {abs_drift:.1f}pp below target. "
            f"Under the {mandate.display_name} mandate, this shortfall is within "
            f"accepted parameters. Correction is advisory."
        )

    # STANDARD — use original rationale with mandate framing
    orig_rationale = rec_dict.get("rationale", "")
    if orig_rationale:
        return (
            f"[{mandate.display_name} mandate] {orig_rationale}"
        )
    return (
        f"{node_label} is {abs_drift:.1f}pp {direction} target. "
        f"Under the {mandate.display_name} mandate, this is flagged as "
        f"{interp.mandate_severity.lower()} severity."
    )
