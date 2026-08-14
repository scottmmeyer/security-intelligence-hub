"""Dislocation classifier for the Security Intelligence Hub.

ISSUE-04B — Phase 04B: Class A1 (Fundamental Beat Divergence).
ISSUE-04D — Phase 04D: Class D1 (Replay-Signal Lag) + Class B2 (Analyst-AI Divergence).

Governance (ISSUE-04A Final Verdict):
  - Informational ONLY — no scoring, ranking, or CW-DAS influence
  - Operator advisory — surfaces evidence of signal divergence
  - No scoring input to composite score, Fundamental Modifier, or CW-DAS
  - No action implied

Class A1 — Fundamental Beat Divergence:
  Strong FMP fundamentals + weak ESS/Danelfin signals.

Class D1 — Replay-Signal Lag:
  replay_supported=True + high replay_percentile + weak ESS/Danelfin signals.

Class B2 — Analyst-AI Divergence:
  Strong analyst consensus (ABR ≤ 2.0, count ≥ 10) + weak ESS/Danelfin signals.
  Analyst count gate prevents thin-coverage false positives.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

# ── Tier constants ─────────────────────────────────────────────────────────────

DISLOCATION_NONE              = "NONE"
DISLOCATION_WATCH             = "WATCH"
DISLOCATION_MODERATE          = "MODERATE"
DISLOCATION_HIGH_CONVICTION   = "HIGH_CONVICTION"

DISLOCATION_CLASS_A1          = "A1_FUNDAMENTAL_BEAT_DIVERGENCE"
DISLOCATION_CLASS_D1          = "D1_REPLAY_SIGNAL_LAG"          # ISSUE-04D
DISLOCATION_CLASS_B2          = "B2_ANALYST_AI_DIVERGENCE"       # ISSUE-04D
DISLOCATION_CLASS_MULTI       = "MULTI_CLASS"                    # ISSUE-04D: 2+ classes

DISLOCATION_VERSION           = "1.1"   # bumped for 04D class extensions

# ── Thresholds ─────────────────────────────────────────────────────────────────

# Class A1 — beat rate
_BEAT_HIGH_CONVICTION = 0.875   # 7 of 8 quarters
_BEAT_MODERATE        = 0.750   # 6 of 8 quarters
_BEAT_WATCH           = 0.625   # 5 of 8 quarters

# Signal divergence — shared across classes
_DANELFIN_HIGH_CONVICTION = 2.0
_DANELFIN_MODERATE        = 3.0
_DANELFIN_WATCH           = 3.5

# ESS divergence sets — shared across classes
_ESS_STRONG_DIVERGENCE = frozenset({"VERY_BEARISH", "BEARISH"})
_ESS_MILD_DIVERGENCE   = frozenset({"NEUTRAL", ""})

# Class D1 — replay thresholds
_REPLAY_HIGH_CONVICTION = 80.0  # percentile
_REPLAY_MODERATE        = 65.0
_REPLAY_WATCH           = 50.0

# Class B2 — analyst consensus thresholds
_ABR_HIGH_CONVICTION  = 1.75   # STRONG_BUY territory
_ABR_MODERATE         = 2.0    # BUY
_ABR_WATCH            = 2.5    # MODERATE_BUY
_COUNT_HIGH_CONVICTION = 20    # analyst count gate for HIGH
_COUNT_MODERATE        = 10    # analyst count gate for MODERATE
_COUNT_WATCH           = 5     # analyst count gate for WATCH

# FMP coverage states that block A1
_FMP_NO_DATA_STATES = frozenset({
    "NO_DATA",
    "PROVIDER_NO_DATA",
    "FETCH_FAILED",
    "NOT_FETCHED",
    "ETF_NOT_APPLICABLE",
    "NOT_APPLICABLE",
    "",
})

# Tier ordering for multi-class resolution (higher index = higher tier)
_TIER_ORDER = {DISLOCATION_NONE: 0, DISLOCATION_WATCH: 1,
               DISLOCATION_MODERATE: 2, DISLOCATION_HIGH_CONVICTION: 3}


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclasses.dataclass(frozen=True)
class DislocationType:
    """Result of a dislocation classification for one security.

    Governance: informational only — no scoring, ranking, or action implied.
    All fields are serializable to JSON via dataclasses.asdict().
    """

    symbol:     str
    tier:       str            # NONE | WATCH | MODERATE | HIGH_CONVICTION
    dislocation_class: str     # A1_... | D1_... | B2_... | MULTI_CLASS | NONE
    evidence:   tuple[str, ...]# human-readable evidence list (2-5 items)
    active_classes: tuple[str, ...]  # all classes that fired (for transparency)
    version:    str = DISLOCATION_VERSION


# ── Internal helpers ───────────────────────────────────────────────────────────

def _to_float(v: object) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(str(v).replace(",", "").strip())
        return None if f != f else f
    except (ValueError, TypeError):
        return None


def _ess_normalized(ess_text: Optional[str]) -> str:
    return (ess_text or "").strip().upper()


def _get_ess(overlay: Optional[object]) -> str:
    if overlay is None:
        return ""
    if isinstance(overlay, dict):
        return str(overlay.get("ess_score_text") or "")
    return str(getattr(overlay, "ess_score_text", "") or "")


def _get_field(overlay: Optional[object], field: str) -> Optional[object]:
    if overlay is None:
        return None
    if isinstance(overlay, dict):
        return overlay.get(field)
    return getattr(overlay, field, None)


def _resolve_tier(results: list[tuple[str, str, list[str]]]) -> tuple[str, str, tuple[str, ...]]:
    """Resolve multiple class results to a single tier/class/evidence.

    Args:
        results: list of (tier, class_name, evidence) from each classifier

    Returns:
        (tier, dislocation_class, active_classes_tuple)

    When multiple classes fire:
    - Use the highest tier
    - Set class to MULTI_CLASS
    - Merge evidence (deduped, capped at 5)
    """
    firing = [(t, c, e) for t, c, e in results if t != DISLOCATION_NONE]
    if not firing:
        return DISLOCATION_NONE, DISLOCATION_NONE, ()

    # Find highest tier
    best_tier = max(firing, key=lambda x: _TIER_ORDER.get(x[0], 0))[0]
    active_classes = tuple(c for _, c, _ in firing)

    if len(firing) == 1:
        tier, cls, evidence = firing[0]
        return tier, cls, active_classes

    # Multiple classes: MULTI_CLASS label, merged evidence
    merged_evidence: list[str] = []
    seen: set[str] = set()
    for _, cls, ev in firing:
        for item in ev:
            if item not in seen:
                merged_evidence.append(item)
                seen.add(item)
    return best_tier, DISLOCATION_CLASS_MULTI, active_classes


# ── Class A1 classifier ────────────────────────────────────────────────────────

def _classify_a1(
    thesis:        str,
    consistency:   str,
    beat_rate:     Optional[float],
    ess:           str,
    danelfin:      Optional[float],
    revenue_growth: Optional[float],
    fmp_coverage:  str,
) -> tuple[str, list[str]]:
    """Classify Class A1 (Fundamental Beat Divergence).
    Returns (tier, evidence_list).
    """
    if fmp_coverage in _FMP_NO_DATA_STATES:
        return DISLOCATION_NONE, []
    if thesis != "INTACT":
        return DISLOCATION_NONE, []
    if beat_rate is None or beat_rate < _BEAT_WATCH:
        return DISLOCATION_NONE, []

    ess_strong   = ess in _ESS_STRONG_DIVERGENCE
    ess_mild     = ess in _ESS_MILD_DIVERGENCE
    dan_strong   = danelfin is not None and danelfin < _DANELFIN_HIGH_CONVICTION
    dan_moderate = danelfin is not None and danelfin < _DANELFIN_MODERATE
    dan_mild     = danelfin is not None and danelfin < _DANELFIN_WATCH

    any_divergence = ess_strong or ess_mild or dan_strong or dan_moderate or dan_mild
    if not any_divergence:
        return DISLOCATION_NONE, []

    evidence: list[str] = []
    beat_pct = round(beat_rate * 100)
    evidence.append(f"Beat rate {beat_pct}% — fundamentals consistently exceeded expectations")
    evidence.append("Thesis: INTACT")
    if ess_strong:
        evidence.append(f"ESS: {ess} — signal has not reflected fundamental execution")
    elif ess_mild:
        evidence.append(f"ESS: {ess or 'unavailable'} — signal neutral/absent")
    if danelfin is not None:
        evidence.append(f"Danelfin: {danelfin:.1f} — AI model diverging from fundamentals")
    if revenue_growth is not None and revenue_growth > 0:
        evidence.append(f"Revenue growth: +{revenue_growth * 100:.1f}% (confirming)")

    if consistency == "CONSISTENT":
        evidence.append("Fundamental consistency: CONSISTENT (multi-factor agreement)")
    elif consistency == "CONTRADICTORY":
        contradictory_note = "\u26a0 Consistency: CONTRADICTORY \u2014 tier capped at WATCH"
        return DISLOCATION_WATCH, evidence[:3] + [contradictory_note]

    if (beat_rate >= _BEAT_HIGH_CONVICTION and ess_strong
            and (dan_strong or ess == "VERY_BEARISH")):
        return DISLOCATION_HIGH_CONVICTION, evidence[:4]
    if (beat_rate >= _BEAT_MODERATE and (ess_strong or ess_mild) and dan_moderate):
        return DISLOCATION_MODERATE, evidence[:4]
    if beat_rate >= _BEAT_HIGH_CONVICTION and ess_strong:
        return DISLOCATION_MODERATE, evidence[:4]
    if beat_rate >= _BEAT_WATCH and (ess_mild or dan_mild):
        return DISLOCATION_WATCH, evidence[:4]

    return DISLOCATION_NONE, []


# ── Class D1 classifier (ISSUE-04D) ───────────────────────────────────────────

def _classify_d1(
    replay_supported:  bool,
    replay_percentile: Optional[float],
    ess:               str,
    danelfin:          Optional[float],
    thesis:            str,
) -> tuple[str, list[str]]:
    """Classify Class D1 (Replay-Signal Lag).

    A security with strong historical replay evidence has weak current signals —
    Layer 3 historical validation conflicts with Layer 1 signal quality.

    Returns (tier, evidence_list).
    """
    # Gate 1: must have verified replay support
    if not replay_supported:
        return DISLOCATION_NONE, []

    # Gate 2: replay percentile must meet minimum
    if replay_percentile is None or replay_percentile < _REPLAY_WATCH:
        return DISLOCATION_NONE, []

    # Gate 3: thesis must not be DETERIORATING (would validate signal weakness)
    if thesis == "DETERIORATING":
        return DISLOCATION_NONE, []

    # At least some signal divergence required
    ess_strong   = ess in _ESS_STRONG_DIVERGENCE
    ess_mild     = ess in _ESS_MILD_DIVERGENCE
    dan_strong   = danelfin is not None and danelfin < _DANELFIN_HIGH_CONVICTION
    dan_moderate = danelfin is not None and danelfin < _DANELFIN_MODERATE
    dan_mild     = danelfin is not None and danelfin < _DANELFIN_WATCH

    any_divergence = ess_strong or ess_mild or dan_strong or dan_moderate or dan_mild
    if not any_divergence:
        return DISLOCATION_NONE, []

    evidence: list[str] = []
    pct_str = f"{replay_percentile:.0f}th percentile"
    evidence.append(f"Replay evidence: {pct_str} — strong historical validation")
    evidence.append("replay_supported = True")
    if ess_strong:
        evidence.append(f"ESS: {ess} — current signal conflicts with replay evidence")
    elif ess_mild:
        evidence.append(f"ESS: {ess or 'unavailable'} — neutral/absent despite replay support")
    if danelfin is not None:
        evidence.append(f"Danelfin: {danelfin:.1f} — AI model diverging from replay history")
    if thesis == "INTACT":
        evidence.append("Thesis: INTACT (fundamental case intact)")

    # Tier assignment
    if (replay_percentile >= _REPLAY_HIGH_CONVICTION
            and ess_strong and (dan_strong or ess == "VERY_BEARISH")):
        return DISLOCATION_HIGH_CONVICTION, evidence[:4]

    if (replay_percentile >= _REPLAY_MODERATE
            and (ess_strong or ess_mild) and dan_moderate):
        return DISLOCATION_MODERATE, evidence[:4]

    if replay_percentile >= _REPLAY_MODERATE and ess_strong:
        return DISLOCATION_MODERATE, evidence[:4]

    if replay_percentile >= _REPLAY_WATCH and (ess_mild or dan_mild):
        return DISLOCATION_WATCH, evidence[:4]

    return DISLOCATION_NONE, []


# ── Class B2 classifier (ISSUE-04D) ───────────────────────────────────────────

def _classify_b2(
    abr:           Optional[float],
    analyst_count: Optional[int],
    ess:           str,
    danelfin:      Optional[float],
    thesis:        str,
) -> tuple[str, list[str]]:
    """Classify Class B2 (Analyst-AI Divergence).

    Strong analyst consensus (ABR direction) conflicts with AI/model signals
    (ESS, Danelfin). Analyst count gate prevents thin-coverage false positives.

    Returns (tier, evidence_list).
    """
    # Gate 1: ABR must be available and bullish
    if abr is None:
        return DISLOCATION_NONE, []
    if abr > _ABR_WATCH:
        return DISLOCATION_NONE, []

    # Gate 2: analyst count must meet minimum to avoid thin-coverage noise
    count = analyst_count or 0
    if count < _COUNT_WATCH:
        return DISLOCATION_NONE, []

    # Gate 3: thesis must not be DETERIORATING
    if thesis == "DETERIORATING":
        return DISLOCATION_NONE, []

    # At least some AI signal divergence required
    ess_strong   = ess in _ESS_STRONG_DIVERGENCE
    ess_mild     = ess in _ESS_MILD_DIVERGENCE
    dan_strong   = danelfin is not None and danelfin < _DANELFIN_HIGH_CONVICTION
    dan_moderate = danelfin is not None and danelfin < _DANELFIN_MODERATE
    dan_mild     = danelfin is not None and danelfin < _DANELFIN_WATCH

    any_divergence = ess_strong or ess_mild or dan_strong or dan_moderate or dan_mild
    if not any_divergence:
        return DISLOCATION_NONE, []

    # Build evidence
    abr_label = "Strong Buy" if abr <= 1.5 else "Buy" if abr <= 2.0 else "Moderate Buy"
    evidence: list[str] = []
    evidence.append(f"ABR {abr:.2f} ({abr_label}) from {count} analysts — consensus bullish")
    if ess_strong:
        evidence.append(f"ESS: {ess} — AI signal diverges from analyst consensus")
    elif ess_mild:
        evidence.append(f"ESS: {ess or 'unavailable'} — AI signal neutral despite analyst consensus")
    if danelfin is not None:
        evidence.append(f"Danelfin: {danelfin:.1f} — AI model diverging from analyst consensus")
    if thesis == "INTACT":
        evidence.append("Thesis: INTACT (fundamental case supports consensus)")

    # Tier assignment
    if (abr <= _ABR_HIGH_CONVICTION and count >= _COUNT_HIGH_CONVICTION
            and (ess_strong or dan_strong)):
        return DISLOCATION_HIGH_CONVICTION, evidence[:4]

    if (abr <= _ABR_MODERATE and count >= _COUNT_MODERATE
            and (ess_strong or ess_mild) and dan_moderate):
        return DISLOCATION_MODERATE, evidence[:4]

    if abr <= _ABR_MODERATE and count >= _COUNT_MODERATE and ess_strong:
        return DISLOCATION_MODERATE, evidence[:4]

    if abr <= _ABR_WATCH and count >= _COUNT_WATCH and (ess_mild or dan_mild):
        return DISLOCATION_WATCH, evidence[:4]

    return DISLOCATION_NONE, []


# ── Public entry point ─────────────────────────────────────────────────────────

def classify_dislocation(
    symbol:          str,
    fmp_row:         Optional[dict],
    overlay:         Optional[object],
    ac_row:          Optional[dict] = None,   # ISSUE-04D: analyst consensus entry
) -> DislocationType:
    """Classify dislocation for one security — all classes.

    Args:
        symbol:   Ticker symbol (uppercase)
        fmp_row:  FMP enriched universe row dict. May be None.
        overlay:  SecurityIntelligenceOverlay dataclass instance or dict. May be None.
        ac_row:   Analyst consensus dict (from analyst_consensus_by_symbol).
                  Contains abr, analyst_count, etc. May be None.

    Returns:
        DislocationType — always returns a result (never raises).
        tier = NONE when data is insufficient or no dislocation is detected.
    """
    sym = (symbol or "").strip().upper()

    ess      = _ess_normalized(_get_ess(overlay))
    danelfin = _to_float(_get_field(overlay, "danelfin_score"))

    # Derive thesis (needed by all classes)
    thesis = "INSUFFICIENT_DATA"
    if fmp_row:
        from src.portfolio.deployment_queue import (
            _classify_thesis_integrity,
            _classify_fundamental_consistency,
        )
        thesis      = _classify_thesis_integrity(fmp_row).upper()
        consistency = _classify_fundamental_consistency(
            fmp_row, ess_text=_get_ess(overlay), thesis=thesis,
        ).upper()
    else:
        consistency = "INSUFFICIENT_DATA"

    results: list[tuple[str, str, list[str]]] = []

    # ── Class A1 ─────────────────────────────────────────────────────────────
    if fmp_row:
        fmp_coverage   = str(fmp_row.get("fmp_coverage_status") or "").strip().upper()
        beat_rate      = _to_float(fmp_row.get("beat_rate_8q"))
        revenue_growth = _to_float(fmp_row.get("revenue_growth_q1_yoy"))
        t, e = _classify_a1(
            thesis=thesis, consistency=consistency, beat_rate=beat_rate,
            ess=ess, danelfin=danelfin, revenue_growth=revenue_growth,
            fmp_coverage=fmp_coverage,
        )
        if t != DISLOCATION_NONE:
            results.append((t, DISLOCATION_CLASS_A1, e))

    # ── Class D1 ─────────────────────────────────────────────────────────────
    replay_supported  = bool(_get_field(overlay, "replay_supported"))
    replay_percentile = _to_float(_get_field(overlay, "replay_percentile"))
    t, e = _classify_d1(
        replay_supported=replay_supported,
        replay_percentile=replay_percentile,
        ess=ess,
        danelfin=danelfin,
        thesis=thesis,
    )
    if t != DISLOCATION_NONE:
        results.append((t, DISLOCATION_CLASS_D1, e))

    # ── Class B2 ─────────────────────────────────────────────────────────────
    abr           = _to_float((ac_row or {}).get("abr"))
    analyst_count = None
    if ac_row and ac_row.get("analyst_count") is not None:
        try:
            analyst_count = int(ac_row["analyst_count"])
        except (ValueError, TypeError):
            analyst_count = None
    t, e = _classify_b2(
        abr=abr, analyst_count=analyst_count,
        ess=ess, danelfin=danelfin, thesis=thesis,
    )
    if t != DISLOCATION_NONE:
        results.append((t, DISLOCATION_CLASS_B2, e))

    # Resolve multi-class
    tier, dislocation_class, active_classes = _resolve_tier(results)

    return DislocationType(
        symbol=sym,
        tier=tier,
        dislocation_class=dislocation_class,
        evidence=tuple(_merge_evidence(results)),
        active_classes=active_classes,
    )


def _merge_evidence(results: list[tuple[str, str, list[str]]]) -> list[str]:
    """Merge evidence from all firing classes, deduped, capped at 5."""
    seen: set[str] = set()
    merged: list[str] = []
    for _, _, ev in results:
        for item in ev:
            if item not in seen:
                merged.append(item)
                seen.add(item)
    return merged[:5]


# ── Batch builder for runner.py ───────────────────────────────────────────────

def build_dislocation_payload(
    overlays:   list,
    fmp_by_sym: dict[str, dict],
    ac_by_sym:  Optional[dict[str, dict]] = None,   # ISSUE-04D: analyst consensus
) -> dict[str, dict]:
    """Build a {symbol: dislocation_dict} payload for the run response.

    Args:
        overlays:   list of SecurityIntelligenceOverlay instances or dicts
        fmp_by_sym: output of load_fmp_enriched_universe()
        ac_by_sym:  analyst_consensus_by_symbol dict (from runner). May be None.

    Returns:
        dict mapping uppercase symbol → serialized DislocationType dict.

    Governance: ISSUE-04D — informational only.
    """
    ac_map = ac_by_sym or {}
    result: dict[str, dict] = {}
    for ov in overlays:
        sym = str(_get_field(ov, "symbol") or "").strip().upper()
        if not sym:
            continue
        fmp_row = fmp_by_sym.get(sym) or fmp_by_sym.get(sym.lower())
        ac_row  = ac_map.get(sym) or ac_map.get(sym.upper())
        dt = classify_dislocation(symbol=sym, fmp_row=fmp_row, overlay=ov, ac_row=ac_row)
        result[sym] = {
            "symbol":            dt.symbol,
            "tier":              dt.tier,
            "dislocation_class": dt.dislocation_class,
            "active_classes":    list(dt.active_classes),
            "evidence":          list(dt.evidence),
            "version":           dt.version,
        }
    return result
