"""Per-factor score contribution calculator.

Computes the weighted contribution of each individual signal to the final
composite score.  Supports both v1 and v2_yahoo formula versions.

Factor contribution definition
--------------------------------
For a composite score computed as:

    composite = Σ(score_i × weight_i) / Σ(weight_i)   [available signals only]

The contribution of factor i is:

    contribution_i = score_i × weight_i / total_available_weight

Such that Σ(contribution_i) = composite.

This is suitable for a "stacked attribution" display in the UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.effectiveness.composite_versioning import COMPOSITE_VERSION_REGISTRY, CompositeVersion


# ---------------------------------------------------------------------------
# ESS text → numeric score (mirror of analytical_universe_manager mapping)
# ---------------------------------------------------------------------------
_ESS_TEXT_SCORE_MAP: Dict[str, float] = {
    "VERY_BULLISH": 5.0,
    "BULLISH":      4.0,
    "NEUTRAL":      3.0,
    "BEARISH":      2.0,
    "VERY_BEARISH": 1.0,
}

_ZACKS_TEXT_SCORE_MAP: Dict[str, float] = {
    "STRONG BUY": 5.0, "STRONG_BUY": 5.0,
    "OUTPERFORM": 4.0, "BUY": 4.0, "OVERWEIGHT": 4.0,
    "NEUTRAL": 3.0, "HOLD": 3.0, "MARKET PERFORM": 3.0,
    "MARKET_PERFORM": 3.0, "EQUAL WEIGHT": 3.0, "EQUAL_WEIGHT": 3.0,
    "UNDERPERFORM": 2.0, "SELL": 2.0, "UNDERWEIGHT": 2.0,
    "STRONG SELL": 1.0, "STRONG_SELL": 1.0,
}


def _to_float(raw: str | float | None) -> float:
    try:
        return float(str(raw or "").strip())
    except (ValueError, TypeError):
        return 0.0


@dataclass(frozen=True)
class FactorContribution:
    """Attribution of a single signal factor to the composite score."""

    factor: str
    """Signal name: ess | zacks | danelfin | yahoo."""
    raw_input: str
    """The raw field value from the universe row (for lineage display)."""
    numeric_score: float
    """Resolved 1–5 numeric score for this factor (0.0 if unavailable)."""
    base_weight: float
    """Nominal weight in this composite version (e.g. 0.55 for ESS v1)."""
    effective_weight: float
    """Actual weight after renormalization (0.0 if signal unavailable)."""
    contribution: float
    """Score × effective_weight — adds up to composite across all factors."""
    available: bool
    """Whether this factor contributed (True) or was absent (False)."""


@dataclass(frozen=True)
class CompositeAttribution:
    """Full attribution breakdown for a single security under one composite version."""

    symbol: str
    version_id: str
    composite_score: float
    factors: List[FactorContribution]
    signals_available: int
    """Number of factors that were present and contributed."""

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "version_id": self.version_id,
            "composite_score": self.composite_score,
            "signals_available": self.signals_available,
            "factors": [
                {
                    "factor": f.factor,
                    "raw_input": f.raw_input,
                    "numeric_score": f.numeric_score,
                    "base_weight": f.base_weight,
                    "effective_weight": round(f.effective_weight, 6),
                    "contribution": round(f.contribution, 6),
                    "available": f.available,
                }
                for f in self.factors
            ],
        }


def compute_factor_contributions(
    *,
    symbol: str,
    ess_score_text: str,
    zacks_rating: str,
    ess_zacks_rating: str = "",
    yahoo_abr_normalized: str = "",
    danelfin_score: str,
    version_id: str = "v1",
) -> CompositeAttribution:
    """Compute per-factor contributions for a given security.

    Parameters
    ----------
    symbol:
        Ticker symbol (for display / lineage).
    ess_score_text:
        ESS signal text (e.g. ``"BULLISH"``).
    zacks_rating:
        Zacks numeric score string (e.g. ``"3.0"``).
    ess_zacks_rating:
        Legacy ESS file Zacks rank (rank 1–5, will be inverted).
    yahoo_abr_normalized:
        Pre-normalized Yahoo ABR string (``"4.2"`` meaning 6-abr was already applied).
        Pass empty string for v1 where Yahoo is not populated.
    danelfin_score:
        Danelfin numeric score string (e.g. ``"3.5"``).
    version_id:
        Which composite version weights to use.

    Returns
    -------
    CompositeAttribution with full per-factor breakdown.
    """
    version = COMPOSITE_VERSION_REGISTRY[version_id]
    w = version.weights

    # --- ESS ---
    ess_text = str(ess_score_text or "").strip().upper()
    ess_available = ess_text in _ESS_TEXT_SCORE_MAP
    ess_score = _ESS_TEXT_SCORE_MAP.get(ess_text, 0.0)

    # --- Zacks ---
    zacks_key = str(zacks_rating or "").strip()
    zacks_raw = _to_float(zacks_key)
    if zacks_raw and 1.0 <= zacks_raw <= 5.0:
        zacks_score = zacks_raw
        zacks_available = True
    elif zacks_key.upper() in _ZACKS_TEXT_SCORE_MAP:
        zacks_score = _ZACKS_TEXT_SCORE_MAP[zacks_key.upper()]
        zacks_available = True
    else:
        ez_raw = _to_float(str(ess_zacks_rating or "").strip())
        if ez_raw and 1.0 <= ez_raw <= 5.0:
            zacks_score = round(6.0 - ez_raw, 2)
            zacks_available = True
        else:
            zacks_score = 3.0
            zacks_available = False

    # --- Yahoo ABR normalized ---
    yahoo_val = _to_float(yahoo_abr_normalized)
    yahoo_available = yahoo_val > 0.0

    # --- Danelfin ---
    danelfin_val = _to_float(danelfin_score)
    danelfin_available = danelfin_val > 0.0

    raw_signals = [
        ("ess",      ess_score_text,      ess_score,     w.get("ess", 0.0),      ess_available),
        ("zacks",    zacks_rating,         zacks_score,   w.get("zacks", 0.0),    zacks_available),
        ("yahoo",    yahoo_abr_normalized, yahoo_val,     w.get("yahoo", 0.0),    yahoo_available),
        ("danelfin", danelfin_score,       danelfin_val,  w.get("danelfin", 0.0), danelfin_available),
    ]

    total_weight = sum(bw for _, _, _, bw, avail in raw_signals if avail)
    if total_weight == 0.0:
        total_weight = 1.0  # fallback to neutral; contributions will all be 0

    composite = sum(score * bw for _, _, score, bw, avail in raw_signals if avail) / total_weight
    composite = round(composite, 6) if any(avail for *_, avail in raw_signals) else 3.0

    factors: List[FactorContribution] = []
    for factor, raw_input, numeric_score, base_weight, available in raw_signals:
        if available:
            eff_w = base_weight / total_weight
            contrib = numeric_score * eff_w
        else:
            eff_w = 0.0
            contrib = 0.0
        factors.append(FactorContribution(
            factor=factor,
            raw_input=str(raw_input or ""),
            numeric_score=numeric_score,
            base_weight=base_weight,
            effective_weight=eff_w,
            contribution=contrib,
            available=available,
        ))

    return CompositeAttribution(
        symbol=symbol,
        version_id=version_id,
        composite_score=composite,
        factors=factors,
        signals_available=sum(1 for *_, avail in raw_signals if avail),
    )


def compare_versions(
    *,
    symbol: str,
    ess_score_text: str,
    zacks_rating: str,
    ess_zacks_rating: str = "",
    yahoo_abr_normalized: str = "",
    danelfin_score: str,
    version_ids: Optional[List[str]] = None,
) -> Dict[str, CompositeAttribution]:
    """Compute attributions under multiple versions simultaneously.

    Returns a dict mapping version_id → CompositeAttribution.
    Defaults to comparing v1 vs v2_yahoo_exp_20260522.
    """
    if version_ids is None:
        version_ids = ["v1", "v2_yahoo_exp_20260522"]

    results: Dict[str, CompositeAttribution] = {}
    for vid in version_ids:
        # v1 doesn't use yahoo_abr_normalized; pass empty to keep it excluded.
        ya = yahoo_abr_normalized if vid != "v1" else ""
        results[vid] = compute_factor_contributions(
            symbol=symbol,
            ess_score_text=ess_score_text,
            zacks_rating=zacks_rating,
            ess_zacks_rating=ess_zacks_rating,
            yahoo_abr_normalized=ya,
            danelfin_score=danelfin_score,
            version_id=vid,
        )
    return results
