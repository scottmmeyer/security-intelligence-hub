"""Capital Source Builder — Phase 23.6A.

Builds CapitalSourceRecord list from existing PAR run artifacts.

Non-negotiable: This module is READ-ONLY.
  - No modification to CW-DAS, ESS, Replay, FMI, or Policy engine outputs.
  - All categorization logic reads from upstream artifacts only.
  - Scoring is never recalculated here.

Category detection:
  1. SIGNAL_DETERIORATION  — ESS BEARISH/VERY_BEARISH or opportunity_flag TRIM
  2. STRATEGIC_EXIT        — operator-designated exit or STI REDUCIBLE/REDUNDANT
  3. OVERWEIGHT_REDUCTION  — is_overweight_vs_target=True + drift in alignment
  4. TAX_AWARE_EXIT        — cost_basis > market_value (unrealized loss: Bucket A)
  5. LOW_CONVICTION_REDUCTION — HOLD flag, no replay, above de minimis threshold

Priority stack (descending):
  SIGNAL_DETERIORATION → STRATEGIC_EXIT → OVERWEIGHT_REDUCTION
  → TAX_AWARE_EXIT → LOW_CONVICTION_REDUCTION

Design source: docs/phase_23_6/02_capital_source_taxonomy.md
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .models import (
    CATEGORY_LOW_CONVICTION,
    CATEGORY_OVERWEIGHT_REDUCTION,
    CATEGORY_SIGNAL_DETERIORATION,
    CATEGORY_STRATEGIC_EXIT,
    CATEGORY_TAX_AWARE_EXIT,
    SOURCE_INTENT_OVERWEIGHT_REPAIR,
    SOURCE_INTENT_PORTFOLIO_REALLOCATION,
    SOURCE_INTENT_TAX_FUNDING_SOURCE,
    SOURCE_INTENT_THESIS_EXIT,
    SOURCE_INTENT_THESIS_TRIM,
    TAX_BUCKET_A,
    TAX_BUCKET_B,
    TAX_BUCKET_C,
    TAX_BUCKET_D,
    CapitalSourceRecord,
)
from .funding_policy import score_reduction_candidates

log = logging.getLogger(__name__)

# ── Tuning constants ──────────────────────────────────────────────────────────

# Minimum position size to surface (de minimis filter for Cat 5)
_DE_MINIMIS_PCT = 1.0

# Minimum actionable proceeds — sources below this are suppressed from the
# primary source list.  They are returned in a separate suppressed_sources list
# for diagnostics but do not appear in the main CRA workflow.
# Rationale: transaction costs typically exceed value of sub-$500 trades.
MINIMUM_ACTIONABLE_PROCEEDS = 500.0

# Overweight drift thresholds
_DRIFT_HIGH    = 15.0
_DRIFT_MODERATE = 8.0

# Significant unrealized gain threshold for Bucket D annotation (USD)
_SIGNIFICANT_GAIN_THRESHOLD = 5_000.0

# Sizing fractions by scenario
_SIZING_FULL            = 1.0
_SIZING_HALF            = 0.5
_SIZING_QUARTER         = 0.25
_SIZING_LOW_CONVICTION  = 0.25

# Category priority order (index = priority rank; lower = higher priority)
_CATEGORY_PRIORITY = [
    CATEGORY_SIGNAL_DETERIORATION,
    CATEGORY_STRATEGIC_EXIT,
    CATEGORY_OVERWEIGHT_REDUCTION,
    CATEGORY_TAX_AWARE_EXIT,
    CATEGORY_LOW_CONVICTION,
]

# ESS bearish values
_BEARISH_ESS = frozenset({"BEARISH", "VERY_BEARISH"})
_VERY_BEARISH_ESS = frozenset({"VERY_BEARISH"})


# ── Internal record type (pre-dedup) ─────────────────────────────────────────

def _compute_source_intent(
    category: str,
    ess_score_text: Optional[str],
    signal_direction: Optional[str],
    sizing_pct: float,
) -> str:
    """Derive operator-visible source_intent from category + signal context.

    CRA-EXPLAIN-02: Distinguishes WHY a position is in the queue from HOW it
    was detected.  The key insight is that OVERWEIGHT_REDUCTION positions that
    still carry bullish conviction are being used as *funding sources* (not
    because SIH has turned bearish on them), whereas positions without positive
    conviction signals are being reduced for *allocation repair*.

    Mapping:
      STRATEGIC_EXIT                         → THESIS_EXIT
      SIGNAL_DETERIORATION (VERY_BEARISH or full-exit sizing) → THESIS_EXIT
      SIGNAL_DETERIORATION (otherwise)       → THESIS_TRIM
      OVERWEIGHT_REDUCTION + bullish signals → TAX_FUNDING_SOURCE
      OVERWEIGHT_REDUCTION (neutral/bearish) → OVERWEIGHT_REPAIR
      TAX_AWARE_EXIT                         → TAX_FUNDING_SOURCE
      LOW_CONVICTION_REDUCTION               → PORTFOLIO_REALLOCATION
    """
    ess = (ess_score_text or "").upper()
    sig = (signal_direction or "").upper()

    if category == CATEGORY_STRATEGIC_EXIT:
        return SOURCE_INTENT_THESIS_EXIT

    if category == CATEGORY_SIGNAL_DETERIORATION:
        if ess == "VERY_BEARISH" or sizing_pct >= 1.0:
            return SOURCE_INTENT_THESIS_EXIT
        return SOURCE_INTENT_THESIS_TRIM

    if category == CATEGORY_OVERWEIGHT_REDUCTION:
        # Still positive conviction → being tapped as funding, not a bearish call
        if ess in ("BULLISH", "VERY_BULLISH") or sig == "BULLISH":
            return SOURCE_INTENT_TAX_FUNDING_SOURCE
        return SOURCE_INTENT_OVERWEIGHT_REPAIR

    if category == CATEGORY_TAX_AWARE_EXIT:
        return SOURCE_INTENT_TAX_FUNDING_SOURCE

    # LOW_CONVICTION_REDUCTION and any unrecognised categories
    return SOURCE_INTENT_PORTFOLIO_REALLOCATION


class _CandidateRecord:
    """Mutable staging record before CapitalSourceRecord construction."""

    __slots__ = (
        "symbol", "current_value_usd", "sizing_pct", "category", "priority",
        "evidence_parts", "tax_bucket", "tax_annotation", "policy_type",
        "blocked_by_policy", "operator_review_required",
        "ess_score_text", "signal_direction", "is_overweight", "drift_pct",
        "cost_basis", "unrealized_gain_loss",
    )

    def __init__(
        self,
        symbol: str,
        current_value_usd: float,
        sizing_pct: float,
        category: str,
        priority: str,
        evidence_parts: list[str],
        tax_bucket: Optional[str] = None,
        tax_annotation: str = "",
        policy_type: Optional[str] = None,
        blocked_by_policy: bool = False,
        operator_review_required: bool = False,
        ess_score_text: Optional[str] = None,
        signal_direction: Optional[str] = None,
        is_overweight: bool = False,
        drift_pct: Optional[float] = None,
        cost_basis: Optional[float] = None,
        unrealized_gain_loss: Optional[float] = None,
    ) -> None:
        self.symbol = symbol
        self.current_value_usd = current_value_usd
        self.sizing_pct = sizing_pct
        self.category = category
        self.priority = priority
        self.evidence_parts = list(evidence_parts)
        self.tax_bucket = tax_bucket
        self.tax_annotation = tax_annotation
        self.policy_type = policy_type
        self.blocked_by_policy = blocked_by_policy
        self.operator_review_required = operator_review_required
        self.ess_score_text = ess_score_text
        self.signal_direction = signal_direction
        self.is_overweight = is_overweight
        self.drift_pct = drift_pct
        self.cost_basis = cost_basis
        self.unrealized_gain_loss = unrealized_gain_loss

    def to_record(self) -> CapitalSourceRecord:
        proceeds = round(self.current_value_usd * self.sizing_pct, 2)
        return CapitalSourceRecord(
            symbol=self.symbol,
            current_value_usd=round(self.current_value_usd, 2),
            estimated_proceeds=proceeds,
            sizing_pct=round(self.sizing_pct, 4),
            category=self.category,
            priority=self.priority,
            evidence_summary=" | ".join(self.evidence_parts),
            tax_bucket=self.tax_bucket,
            tax_annotation=self.tax_annotation,
            policy_type=self.policy_type,
            blocked_by_policy=self.blocked_by_policy,
            operator_review_required=self.operator_review_required,
            ess_score_text=self.ess_score_text,
            signal_direction=self.signal_direction,
            is_overweight=self.is_overweight,
            drift_pct=self.drift_pct,
            cost_basis=self.cost_basis,
            unrealized_gain_loss=self.unrealized_gain_loss,
            source_intent=_compute_source_intent(
                self.category,
                self.ess_score_text,
                self.signal_direction,
                self.sizing_pct,
            ),
        )


# ── Public API ────────────────────────────────────────────────────────────────

def build_capital_sources(
    overlays: List[Dict],
    holdings: List[Dict],
    alignment: List[Dict],
    deployment_queue: Dict,
    tax_state: Optional[Dict] = None,
    strategic_profiles: Optional[List[Dict]] = None,
    minimum_proceeds: float = MINIMUM_ACTIONABLE_PROCEEDS,
) -> "tuple[List[CapitalSourceRecord], List[CapitalSourceRecord]]":
    """Build CapitalSourceRecord lists from PAR run artifacts.

    Args:
        overlays:           Rows from security_overlays.csv (list of dicts).
        holdings:           Rows from holdings.csv (list of dicts).
        alignment:          Rows from alignment.csv (list of dicts).
        deployment_queue:   Parsed deployment_queue.json dict.
        tax_state:          Parsed portfolio_alignment_state.json dict (optional).
        strategic_profiles: Parsed strategic_profiles.json list (optional).
                            When absent, Category 2 falls back to overlay signals
                            and tax_state.strategic_exit_symbols.
        minimum_proceeds:   Sources with estimated_proceeds below this threshold
                            are moved to the suppressed_sources list.
                            Default: MINIMUM_ACTIONABLE_PROCEEDS ($500).

    Returns:
        Tuple of (sources, suppressed_sources):
          sources            — actionable sources (estimated_proceeds >= threshold)
          suppressed_sources — de minimis sources (estimated_proceeds < threshold)
        Both lists are sorted by priority desc, then proceeds desc.
        Holdings in multiple categories are de-duplicated; highest-priority wins.
    """
    if not overlays:
        return [], []

    # ── Index input data ──────────────────────────────────────────────────────
    holdings_by_sym: Dict[str, Dict] = {
        _sym(h): h for h in holdings if _sym(h)
    }
    overlay_by_sym: Dict[str, Dict] = {
        _sym(o): o for o in overlays if _sym(o)
    }

    # ── Build non-tradeable exclusion set (Defect 1 fix) ─────────────────────
    # Exclude symbols whose holdings row marks them as non-investable.
    # Sources:
    #   is_cash_equivalent=True   → money-market / sweep funds (e.g. SPAXX)
    #   operational_state not in ACTIVE_POSITION → settlement rows, adjustments,
    #                              pending activity, closed positions, etc.
    #   safe_to_offset_cash=True  → settlement-only accounting rows
    # Rationale: none of these are tradeable equity positions.  Including them
    # would produce sell signals for cash or administrative artifacts.
    _ACTIVE_OP_STATES = frozenset({"ACTIVE_POSITION", ""})  # empty = unknown, allow
    non_tradeable: frozenset[str] = frozenset(
        _sym(h)
        for h in holdings
        if _bool_field(h.get("is_cash_equivalent"))
        or (h.get("operational_state") or "") not in _ACTIVE_OP_STATES
        or _bool_field(h.get("safe_to_offset_cash"))
    )

    # Secondary guard: known non-tradeable placeholder symbol patterns.
    # Fidelity CSV exports include rows such as "PENDING ACTIVITY" and
    # "M26CNT069" (contra / legacy) that may be classified as ACTIVE_POSITION
    # by the ingestion layer when their market value is positive.  These are
    # settlement artifacts, not equity positions.
    _NON_TRADEABLE_PATTERNS = ("PENDING", "ACTIVITY", "CONTRA", "M26CNT", "CYBERARK SOFTWA F")
    non_tradeable = non_tradeable | frozenset(
        _sym(h)
        for h in holdings
        if any(p in (_sym(h) or "").upper() for p in _NON_TRADEABLE_PATTERNS)
    )

    # Alignment: build node_key → drift mapping and per-symbol node lookup
    alignment_by_node: Dict[str, Dict] = {
        r.get("node_key", ""): r for r in alignment if r.get("node_key")
    }
    # Build symbol → list of allocation nodes it participates in
    # We derive allocation_node from holdings geography + market_cap_bucket
    sym_to_nodes: Dict[str, List[str]] = {}
    for sym, h in holdings_by_sym.items():
        nodes = _derive_allocation_nodes(h)
        if nodes:
            sym_to_nodes[sym] = nodes

    # Deployment queue symbols (to exclude from Low Conviction)
    queue_symbols: frozenset[str] = frozenset(
        e.get("symbol", "").upper()
        for e in deployment_queue.get("queue", [])
        if e.get("symbol")
    )

    # Tax state
    tax_state = tax_state or {}
    strategic_exit_symbols: frozenset[str] = frozenset(
        s.upper() for s in tax_state.get("strategic_exit_symbols", []) if s
    )
    operator_policies_raw: list = tax_state.get("operator_policies", [])
    # Build active policy map: symbol → policy_type
    active_policies: Dict[str, str] = {}
    for p in operator_policies_raw:
        if not isinstance(p, dict):
            continue
        if p.get("status") == "ACTIVE" and not p.get("revoked_at"):
            sym = (p.get("symbol") or "").upper()
            if sym:
                active_policies[sym] = p.get("policy_type", "")

    # Strategic profiles by symbol (if available)
    profiles_by_sym: Dict[str, Dict] = {}
    if strategic_profiles:
        for p in strategic_profiles:
            sym = (p.get("symbol") or "").upper()
            if sym:
                profiles_by_sym[sym] = p

    # ── Collect all candidates (one per category per symbol) ──────────────────
    # dict: symbol → _CandidateRecord (best priority per symbol)
    candidates: Dict[str, _CandidateRecord] = {}

    def _merge_or_add(cand: _CandidateRecord) -> None:
        """Add candidate; if symbol exists, keep higher-priority category."""
        existing = candidates.get(cand.symbol)
        if existing is None:
            candidates[cand.symbol] = cand
            return
        # Compare category priority
        existing_idx = _category_index(existing.category)
        new_idx = _category_index(cand.category)
        if new_idx < existing_idx:
            # New category has higher priority; replace but merge evidence
            cand.evidence_parts = cand.evidence_parts + [
                f"[also: {existing.category}] {e}"
                for e in existing.evidence_parts
            ]
            candidates[cand.symbol] = cand
        else:
            # Existing is higher priority; just merge evidence
            existing.evidence_parts.extend(
                f"[also: {cand.category}] {e}"
                for e in cand.evidence_parts
            )

    # ── Category 1: Signal Deterioration ────────────────────────────────────
    for sym, ov in overlay_by_sym.items():
        if sym in non_tradeable:
            continue  # cash equivalent or non-ACTIVE operational state
        ess = (ov.get("ess_score_text") or "").upper()
        sig = (ov.get("signal_direction") or "").upper()
        flag = (ov.get("opportunity_flag") or "").upper()
        is_ow = _bool_field(ov.get("is_overweight_vs_target"))

        if ess not in _BEARISH_ESS and flag not in ("TRIM", "WATCH"):
            continue

        mv = _holding_mv(sym, holdings_by_sym)
        if mv <= 0:
            continue

        # Policy check
        policy = active_policies.get(sym)
        blocked = policy == "DO_NOT_SELL"
        needs_review = policy == "CORE_ANCHOR"

        # Priority
        if ess in _VERY_BEARISH_ESS:
            priority = "URGENT"
            sizing = _SIZING_FULL
        elif ess in _BEARISH_ESS and is_ow:
            priority = "HIGH"
            sizing = _SIZING_HALF
        elif flag == "TRIM":
            priority = "HIGH"
            sizing = _SIZING_HALF
        else:
            priority = "MODERATE"
            sizing = _SIZING_QUARTER

        # Drift for overweight context
        max_drift = _max_node_drift(sym, sym_to_nodes, alignment_by_node)

        evidence = [
            f"ESS={ess}" if ess else f"flag={flag}",
        ]
        if is_ow:
            evidence.append("overweight node")
        if max_drift and max_drift > 0:
            evidence.append(f"node drift +{max_drift:.1f}%")

        _merge_or_add(_CandidateRecord(
            symbol=sym,
            current_value_usd=mv,
            sizing_pct=sizing,
            category=CATEGORY_SIGNAL_DETERIORATION,
            priority=priority,
            evidence_parts=evidence,
            policy_type=policy or None,
            blocked_by_policy=blocked,
            operator_review_required=needs_review,
            ess_score_text=ess if ess else None,
            signal_direction=sig if sig else None,
            is_overweight=is_ow,
            drift_pct=max_drift,
        ))

    # ── Category 2: Strategic Exit ───────────────────────────────────────────
    # Source A: operator-designated strategic_exit_symbols
    for sym in strategic_exit_symbols:
        if sym in non_tradeable:
            continue  # should never happen for strategic_exit_symbols, but guard
        mv = _holding_mv(sym, holdings_by_sym)
        if mv <= 0:
            continue
        # Skip if already URGENT from Cat 1 with full exit
        existing = candidates.get(sym)
        if existing and existing.priority == "URGENT" and existing.sizing_pct >= 1.0:
            # Already full exit — just add evidence
            existing.evidence_parts.append(f"[also: {CATEGORY_STRATEGIC_EXIT}] operator-designated strategic exit")
            continue

        policy = active_policies.get(sym)
        blocked = policy == "DO_NOT_SELL"
        needs_review = policy == "CORE_ANCHOR"

        # Look up profile if available
        profile = profiles_by_sym.get(sym)
        if profile:
            strat_class = profile.get("strategic_classification", "")
            trim_score = float(profile.get("trim_priority_score") or 0)
            trim_rationale = profile.get("trim_rationale", "Operator-designated exit")
            sizing = _SIZING_FULL if trim_score >= 70 else _SIZING_HALF
            priority = "HIGH" if trim_score >= 60 else "MODERATE"
            evidence = [f"operator-designated strategic exit | {strat_class} | trim_score={trim_score:.0f} | {trim_rationale[:80]}"]
        else:
            sizing = _SIZING_FULL
            priority = "HIGH"
            evidence = ["operator-designated strategic exit (no STI profile available)"]

        _merge_or_add(_CandidateRecord(
            symbol=sym,
            current_value_usd=mv,
            sizing_pct=sizing,
            category=CATEGORY_STRATEGIC_EXIT,
            priority=priority,
            evidence_parts=evidence,
            policy_type=policy or None,
            blocked_by_policy=blocked,
            operator_review_required=needs_review,
        ))

    # Source B: STI profiles with REDUCIBLE / REDUNDANT_EXPOSURE classification
    _STI_TRIM_CLASSES = frozenset({"REDUCIBLE", "REDUNDANT_EXPOSURE", "CONCENTRATION_RISK"})
    for sym, profile in profiles_by_sym.items():
        if sym in non_tradeable:
            continue
        strat_class = (profile.get("strategic_classification") or "").upper()
        if strat_class not in _STI_TRIM_CLASSES:
            continue
        if sym in strategic_exit_symbols:
            continue  # already handled above

        mv = _holding_mv(sym, holdings_by_sym)
        if mv <= 0:
            continue

        trim_score = float(profile.get("trim_priority_score") or 0)
        if trim_score < 60:
            continue  # below Category 2 threshold

        policy = active_policies.get(sym)
        blocked = policy == "DO_NOT_SELL"
        needs_review = policy == "CORE_ANCHOR"

        sizing = _SIZING_FULL if strat_class == "REDUCIBLE" else _SIZING_HALF
        priority = "HIGH" if trim_score >= 70 else "MODERATE"
        rationale = profile.get("trim_rationale", "")
        evidence = [f"{strat_class} | trim_score={trim_score:.0f}/100 | {rationale[:80]}"]

        _merge_or_add(_CandidateRecord(
            symbol=sym,
            current_value_usd=mv,
            sizing_pct=sizing,
            category=CATEGORY_STRATEGIC_EXIT,
            priority=priority,
            evidence_parts=evidence,
            policy_type=policy or None,
            blocked_by_policy=blocked,
            operator_review_required=needs_review,
        ))

    # ── Category 3: Overweight Reduction ─────────────────────────────────────
    for sym, ov in overlay_by_sym.items():
        if sym in non_tradeable:
            continue
        is_ow = _bool_field(ov.get("is_overweight_vs_target"))
        if not is_ow:
            continue

        mv = _holding_mv(sym, holdings_by_sym)
        if mv <= 0:
            continue

        max_drift = _max_node_drift(sym, sym_to_nodes, alignment_by_node)
        if max_drift is None or max_drift <= 0:
            continue

        policy = active_policies.get(sym)
        blocked = policy == "DO_NOT_SELL"
        needs_review = policy == "CORE_ANCHOR"

        # Priority by drift magnitude
        if max_drift >= _DRIFT_HIGH:
            priority = "HIGH"
            sizing = _SIZING_HALF
        elif max_drift >= _DRIFT_MODERATE:
            priority = "MODERATE"
            sizing = _SIZING_QUARTER
        else:
            priority = "LOW"
            sizing = _SIZING_QUARTER

        # Skip de minimis drift
        if priority == "LOW" and max_drift < 3.0:
            continue

        evidence = [f"overweight allocation node | drift +{max_drift:.1f}%"]

        # Capture ESS and signal so _compute_source_intent can distinguish
        # bullish-conviction overweights (TAX_FUNDING_SOURCE) from neutral/bearish
        # overweights that are being reduced for allocation repair (OVERWEIGHT_REPAIR).
        ow_ess = (ov.get("ess_score_text") or "").upper() or None
        ow_sig = (ov.get("signal_direction") or "").upper() or None

        _merge_or_add(_CandidateRecord(
            symbol=sym,
            current_value_usd=mv,
            sizing_pct=sizing,
            category=CATEGORY_OVERWEIGHT_REDUCTION,
            priority=priority,
            evidence_parts=evidence,
            policy_type=policy or None,
            blocked_by_policy=blocked,
            operator_review_required=needs_review,
            is_overweight=True,
            drift_pct=max_drift,
            ess_score_text=ow_ess,
            signal_direction=ow_sig,
        ))

    # ── Category 4: Tax-Aware Exit ───────────────────────────────────────────
    for sym, h in holdings_by_sym.items():
        if sym in non_tradeable:
            continue
        cb = _parse_float(h.get("cost_basis"))
        mv = _parse_float(h.get("market_value"))
        if mv is None or mv <= 0:
            continue
        if cb is None:
            # No cost basis — create a no-cost-basis entry if not already captured
            # Only surface if not already in higher category
            if sym in candidates:
                # Add tax annotation to existing record
                existing = candidates[sym]
                existing.tax_annotation = "No cost basis data — tax impact unknown"
                existing.cost_basis = None
            continue

        unrealized = mv - cb
        bucket, annotation = _derive_tax_bucket(mv, cb, unrealized)

        # Only create a new Cat 4 record if not already captured in Cat 1-3
        if sym not in candidates:
            if bucket != TAX_BUCKET_A:
                # Category 4 only initiates for loss harvest (Bucket A)
                continue

            policy = active_policies.get(sym)
            blocked = policy == "DO_NOT_SELL"
            needs_review = policy == "CORE_ANCHOR"

            evidence = [f"unrealized loss ~${abs(unrealized):,.0f} | tax loss harvest opportunity"]

            _merge_or_add(_CandidateRecord(
                symbol=sym,
                current_value_usd=mv,
                sizing_pct=_SIZING_FULL,
                category=CATEGORY_TAX_AWARE_EXIT,
                priority="MODERATE",
                evidence_parts=evidence,
                tax_bucket=bucket,
                tax_annotation=annotation,
                policy_type=policy or None,
                blocked_by_policy=blocked,
                operator_review_required=needs_review,
                cost_basis=cb,
                unrealized_gain_loss=round(unrealized, 2),
            ))
        else:
            # Enrich existing record with tax context
            existing = candidates[sym]
            existing.tax_bucket = bucket
            existing.tax_annotation = annotation
            existing.cost_basis = cb
            existing.unrealized_gain_loss = round(unrealized, 2)

            # Apply tax modifier to priority
            _apply_tax_modifier(existing, bucket)

    # ── Category 5: Low Conviction Reduction ────────────────────────────────
    for sym, ov in overlay_by_sym.items():
        if sym in non_tradeable:
            continue
        flag = (ov.get("opportunity_flag") or "").upper()
        if flag != "HOLD":
            continue
        if sym in candidates:
            continue  # already in higher category
        if sym in queue_symbols:
            continue  # in deployment queue → not low conviction
        # PREFERRED_ACCUMULATION → exclude from Cat 5
        if active_policies.get(sym) == "PREFERRED_ACCUMULATION":
            continue

        pct = _parse_float(ov.get("percent_of_portfolio")) or 0.0
        if pct < _DE_MINIMIS_PCT:
            continue

        mv = _holding_mv(sym, holdings_by_sym)
        if mv <= 0:
            continue

        # Require: no replay support and neutral/no signal
        replay = _bool_field(ov.get("replay_supported"))
        if replay:
            continue  # has replay → not low conviction

        sig = (ov.get("signal_direction") or "").upper()
        if sig in ("BULLISH",):
            continue  # has bullish signal → skip

        policy = active_policies.get(sym)
        blocked = policy == "DO_NOT_SELL"
        needs_review = policy == "CORE_ANCHOR"

        priority = "MODERATE" if pct >= 3.0 else "LOW"
        evidence = [f"HOLD flag | no replay support | {pct:.1f}% weight | opportunity cost position"]

        _merge_or_add(_CandidateRecord(
            symbol=sym,
            current_value_usd=mv,
            sizing_pct=_SIZING_LOW_CONVICTION,
            category=CATEGORY_LOW_CONVICTION,
            priority=priority,
            evidence_parts=evidence,
            policy_type=policy or None,
            blocked_by_policy=blocked,
            operator_review_required=needs_review,
            signal_direction=sig if sig else None,
        ))

    # ── Apply tax annotations to all remaining records ────────────────────────
    for sym, cand in candidates.items():
        if cand.tax_bucket is not None:
            continue  # already set
        h = holdings_by_sym.get(sym, {})
        cb = _parse_float(h.get("cost_basis"))
        mv = _parse_float(h.get("market_value"))
        if cb is not None and mv is not None and mv > 0:
            unrealized = mv - cb
            bucket, annotation = _derive_tax_bucket(mv, cb, unrealized)
            cand.tax_bucket = bucket
            cand.tax_annotation = annotation
            cand.cost_basis = cb
            cand.unrealized_gain_loss = round(unrealized, 2)
            _apply_tax_modifier(cand, bucket)
        else:
            if cand.tax_annotation == "":
                cand.tax_annotation = "No cost basis data — tax impact unknown"

    # ── Fix 2: Strategic exit override (Phase 23.6B.4) ───────────────────────
    # When a symbol is in strategic_exit_symbols, the operator has explicitly
    # designated it for full exit.  Override any other category to STRATEGIC_EXIT
    # and force 100% sizing, regardless of what signal-based detection assigned.
    # Evidence is merged so ESS signal context is preserved.
    for sym in strategic_exit_symbols:
        cand = candidates.get(sym)
        if cand is None:
            continue  # not in candidates; already handled in Cat 2 loop
        if cand.category == CATEGORY_STRATEGIC_EXIT:
            # Already correctly categorised; ensure 100% sizing
            cand.sizing_pct = _SIZING_FULL
        else:
            # Override: preserve evidence but promote category and sizing
            original_evidence = list(cand.evidence_parts)
            cand.evidence_parts = [
                "operator-designated strategic exit (no STI profile available)",
            ] + [f"[signal context] {e}" for e in original_evidence]
            cand.category = CATEGORY_STRATEGIC_EXIT
            cand.sizing_pct = _SIZING_FULL
            # Priority remains HIGH (strategic exits are always actionable)
            if cand.priority in ("MODERATE", "LOW", "DEFER"):
                cand.priority = "HIGH"

    # ── Sort: priority descending, then proceeds descending within tier ───────
    priority_rank = {p: i for i, p in enumerate(["URGENT", "HIGH", "MODERATE", "LOW", "DEFER"])}

    sorted_records = sorted(
        candidates.values(),
        key=lambda c: (
            priority_rank.get(c.priority, 99),
            -(c.current_value_usd * c.sizing_pct),
        ),
    )

    # ── Fix 3: Minimum proceeds filter (Phase 23.6B.4) ───────────────────────
    # Separate de-minimis sources (estimated_proceeds < minimum_proceeds) from
    # the primary actionable source list.  De-minimis sources are returned as
    # suppressed_sources for diagnostics but do not enter the main CRA workflow.
    all_records = [c.to_record() for c in sorted_records]
    all_records = score_reduction_candidates(
        sources=all_records,
        deployment_queue=list(deployment_queue.get("queue", [])),
    )
    sources: List[CapitalSourceRecord] = []
    suppressed: List[CapitalSourceRecord] = []
    for rec in all_records:
        if rec.estimated_proceeds < minimum_proceeds:
            suppressed.append(rec)
        else:
            sources.append(rec)

    return sources, suppressed


# ── Internal helpers ──────────────────────────────────────────────────────────

def _sym(row: Dict) -> str:
    return (row.get("symbol") or "").strip().upper()


def _parse_float(val) -> Optional[float]:
    if val is None or val == "" or val == "None":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _bool_field(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def _holding_mv(sym: str, holdings_by_sym: Dict[str, Dict]) -> float:
    h = holdings_by_sym.get(sym, {})
    mv = _parse_float(h.get("market_value"))
    return mv if mv is not None else 0.0


def _derive_allocation_nodes(holding: Dict) -> List[str]:
    """Derive EQUITIES-style allocation node keys from a holding row."""
    geo = (holding.get("geography") or "").upper()
    cap = (holding.get("market_cap_bucket") or "").upper()
    asset = (holding.get("asset_class") or "").upper()

    if asset not in ("EQUITIES", "UNKNOWN", ""):
        return []
    if not geo or geo == "UNKNOWN":
        return []

    nodes = [f"EQUITIES.{geo}"]
    if cap and cap not in ("UNKNOWN", "N/A", ""):
        nodes.append(f"EQUITIES.{geo}.{cap}")
    return nodes


def _max_node_drift(
    sym: str,
    sym_to_nodes: Dict[str, List[str]],
    alignment_by_node: Dict[str, Dict],
) -> Optional[float]:
    """Return maximum positive drift_pct across all allocation nodes for a symbol."""
    nodes = sym_to_nodes.get(sym, [])
    max_drift: Optional[float] = None
    for node_key in nodes:
        row = alignment_by_node.get(node_key)
        if row is None:
            continue
        drift = _parse_float(row.get("drift_pct"))
        if drift is None or drift <= 0:
            continue
        if max_drift is None or drift > max_drift:
            max_drift = drift
    return max_drift


def _derive_tax_bucket(
    market_value: float,
    cost_basis: float,
    unrealized: float,
) -> tuple[str, str]:
    """Derive simplified tax bucket from cost_basis vs market_value.

    Simplified model (no holding_days available):
      Bucket A: unrealized loss (harvest candidate)
      Bucket C: unrealized gain ≤ _SIGNIFICANT_GAIN_THRESHOLD
      Bucket D: unrealized gain > _SIGNIFICANT_GAIN_THRESHOLD (operator review)

    Bucket B (ST gain) and E (approaching LT) require holding_days data
    which is not available in the PAR artifacts; they are not assigned here.
    """
    if unrealized < 0:
        gain_str = f"~${abs(unrealized):,.0f}"
        return TAX_BUCKET_A, f"Unrealized loss {gain_str} — tax loss harvest opportunity"
    elif unrealized <= _SIGNIFICANT_GAIN_THRESHOLD:
        gain_str = f"~${unrealized:,.0f}"
        return TAX_BUCKET_C, f"Long-term gain {gain_str} — no deferral concern"
    else:
        gain_str = f"~${unrealized:,.0f}"
        return TAX_BUCKET_D, f"Significant gain {gain_str} — confirm tax strategy before executing"


def _apply_tax_modifier(cand: _CandidateRecord, bucket: str) -> None:
    """Apply tax modifier rules (from docs/phase_23_6/04_tax_integration_analysis.md).

    Bucket A: priority upgrade (MODERATE→HIGH, LOW→MODERATE)
    Bucket D: operator_review_required=True; priority downgrade (HIGH→MODERATE)
    Bucket E: priority set to DEFER; excluded from pool
    """
    if bucket == TAX_BUCKET_A:
        if cand.priority == "MODERATE":
            cand.priority = "HIGH"
        elif cand.priority == "LOW":
            cand.priority = "MODERATE"
    elif bucket == TAX_BUCKET_D:
        cand.operator_review_required = True
        if cand.priority == "HIGH":
            cand.priority = "MODERATE"
    # Bucket E not assigned by _derive_tax_bucket currently (no holding_days)
    # but handle defensively
    elif bucket == "E":
        cand.priority = "DEFER"


def _category_index(category: str) -> int:
    try:
        return _CATEGORY_PRIORITY.index(category)
    except ValueError:
        return len(_CATEGORY_PRIORITY)
