"""Phase 6.4 — Portfolio Reconciliation Framework.

Deterministic accounting control layer.  Every portfolio analysis run is
validated against a battery of 10 reconciliation checks designed to catch
the exact class of defects discovered during Phase 6.3D:

  RC-01  Portfolio value reconciliation (holdings sum == reported total)
  RC-02  Allocation total reconciliation (L1 nodes sum == 100%)
  RC-03  Direct + ETF-derived == effective (per node decomposition integrity)
  RC-04  ETF decomposition weight validation (each registry entry sums to ~100%)
  RC-05  Cash position reconciliation (actual cash == reported CASH node)
  RC-06  Security classification audit (cash instruments ≠ ETF contributors)
  RC-07  Archetype target validation (all profiles sum to 100%, no orphan nodes)
  RC-08  Recommendation consistency (rec targets match active allocation model)
  RC-09  Holding classification consistency (impossible state detection)
  RC-10  Portfolio philosophy consistency (archetype coherence across all surfaces)
  RC-12  Taxonomy normalization (no alias/duplicate node keys in alignment output)
  RC-13  Coverage reconciliation (signal coverage math ≤ 100%; grade visibility)

Usage::

    from src.portfolio.reconciliation import run_reconciliation
    report = run_reconciliation(
        holdings=investable,
        alignment=alignment,
        recommendations=recs_with_drilldown,
        mandate_type="CONCENTRATED_ALPHA",
        snapshot_total_mv=snapshot.total_market_value,
        run_id=run_id,
    )
    # report.overall_status  → "PASS" | "WARN" | "FAIL"
    # report.checks          → list[ReconciliationCheck]
    # report.checks_passed   → int
    # report.checks_failed   → int
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ETF_REGISTRY_PATH = _REPO_ROOT / "config" / "etf_exposure_decomposition.yaml"
_MODELS_DIR = _REPO_ROOT / "config" / "allocation_models"

_CASH_EQUIVALENT_SYMBOLS = frozenset({
    "SPAXX", "FCASH", "FDRXX", "SPRXX", "VMFXX", "FZFXX",
    "FZSXX", "FTIXX", "FMPXX", "FDLXX",
})
_CASH_SECURITY_TYPES = frozenset({"CASH", "MONEY MARKET"})
_CASH_ASSET_CLASS = "CASH"

_L1_ASSET_CLASS_NODES = frozenset({
    "EQUITIES", "FIXED_INCOME", "DIGITAL", "COMMODITIES", "CASH"
})

# Recommendation types for which mandate_drift_label is semantically applicable.
# Non-allocation types (CONVICTION_EXPLAINABILITY_CARD, narrative cards, etc.) do
# not carry allocation drift context and are exempt from the label check in RC-10.
_ALLOCATION_REC_TYPES = frozenset({
    "INCREASE_UNDERWEIGHT",
    "REDUCE_OVERWEIGHT",
    "IMPROVE_REPLAY_ALIGNMENT",
})

_ARCHETYPE_MANDATE_MAP = {
    "CONCENTRATED_ALPHA": "concentrated_alpha_profile.yaml",
    "GROWTH":             "growth_allocation_profile.yaml",
    "BALANCED":           "balanced_allocation_profile.yaml",
    "DEFENSIVE":          "balanced_allocation_profile.yaml",
    "INCOME":             "balanced_allocation_profile.yaml",
    "REPLAY_OPTIMIZED":   "growth_allocation_profile.yaml",
}


# ─────────────────────────────────────────────────────────────────────────────
# Data contracts
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReconciliationCheck:
    """Result of a single reconciliation check."""

    check_id: str          # RC-01 through RC-10
    name: str
    status: str            # PASS | WARN | FAIL
    expected: Any
    actual: Any
    variance: Any
    tolerance: Any
    detail: list[str] = field(default_factory=list)
    sub_checks: list[dict] = field(default_factory=list)


@dataclass
class ReconciliationResult:
    """Aggregated result of all reconciliation checks for one analysis run."""

    run_id: str
    generated_at: str
    overall_status: str            # PASS | WARN | FAIL
    checks_passed: int
    checks_warned: int
    checks_failed: int
    checks: list[ReconciliationCheck]
    certification: str             # human-readable one-liner


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fld(obj: Any, attr: str, default: Any = None) -> Any:
    """Uniform field access for dataclass instances, CSV dicts, and plain dicts."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _to_float(v: Any, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _to_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return default if v is None else bool(v)


def _status(variance: float, tolerance: float) -> str:
    """Derive PASS / WARN / FAIL from abs(variance) vs tolerance."""
    abs_v = abs(variance)
    if abs_v <= tolerance:
        return "PASS"
    if abs_v <= tolerance * 5:
        return "WARN"
    return "FAIL"


def _status_bool(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def _load_etf_registry() -> dict[str, dict]:
    """Load the ETF exposure decomposition registry from YAML."""
    if not _ETF_REGISTRY_PATH.exists():
        return {}
    try:
        data = yaml.safe_load(_ETF_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
        return data.get("symbols", {}) or {}
    except Exception:
        return {}


def _load_archetype_profile(filename: str) -> dict[str, Any]:
    """Load an allocation model profile YAML."""
    path = _MODELS_DIR / filename
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# RC-01 — Portfolio value reconciliation
# ─────────────────────────────────────────────────────────────────────────────

def _rc01_portfolio_value(
    holdings: list,
    snapshot_total_mv: float,
) -> ReconciliationCheck:
    """SUM(active holding market values) == reported portfolio total.

    Tolerance: $0.01 (one cent) — rounding only.
    """
    holdings_sum = sum(
        _to_float(_fld(h, "market_value"))
        for h in holdings
        if _to_float(_fld(h, "market_value")) > 0
    )
    variance = holdings_sum - snapshot_total_mv
    tol = 0.01
    status = _status(variance, tol)
    return ReconciliationCheck(
        check_id="RC-01",
        name="Portfolio Value Reconciliation",
        status=status,
        expected=f"${snapshot_total_mv:,.2f}",
        actual=f"${holdings_sum:,.2f}",
        variance=f"${variance:+,.2f}",
        tolerance=f"${tol:.2f}",
        detail=[
            f"Holdings sum: ${holdings_sum:,.2f}",
            f"Reported total: ${snapshot_total_mv:,.2f}",
            f"Variance: ${variance:+,.4f}",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-02 — Allocation total reconciliation
# ─────────────────────────────────────────────────────────────────────────────

def _rc02_allocation_totals(
    alignment: list,
    holdings: list = None,
) -> ReconciliationCheck:
    """L1 asset class nodes must sum to ~100%.

    If holdings are provided, any holding with asset_class=UNKNOWN is
    explicitly enumerated in sub_checks and the detail lines, so the gap
    is never silently ignored.

    Classification rule:
      - Gap > tol AND any unclassified holding has MV > 0  → FAIL
      - Gap > tol AND ALL unclassified holdings have MV = 0 → WARN
      - Gap ≤ tol                                           → PASS
    Tolerance: 0.10 percentage points.
    """
    holdings = holdings or []
    l1_sum = 0.0
    found_nodes = []
    for ar in alignment:
        node_key = _fld(ar, "node_key", "")
        if node_key in _L1_ASSET_CLASS_NODES:
            actual = _to_float(_fld(ar, "actual_pct") or _fld(ar, "effective_actual_pct"))
            l1_sum += actual
            found_nodes.append(f"{node_key}={actual:.4f}%")
    variance = l1_sum - 100.0
    tol = 0.10

    # ── Identify UNKNOWN holdings ────────────────────────────────────────────
    total_mv = sum(_to_float(_fld(h, "market_value")) for h in holdings)
    unknown_holdings = [
        h for h in holdings
        if str(_fld(h, "asset_class", "") or "").strip().upper() == "UNKNOWN"
    ]
    nonzero_unknown = [h for h in unknown_holdings if _to_float(_fld(h, "market_value")) > 0]
    zero_unknown    = [h for h in unknown_holdings if _to_float(_fld(h, "market_value")) <= 0]

    unc_mv     = sum(_to_float(_fld(h, "market_value")) for h in nonzero_unknown)
    unc_pct    = (unc_mv / total_mv * 100) if total_mv else 0.0
    zero_mv    = sum(_to_float(_fld(h, "market_value")) for h in zero_unknown)
    zero_pct   = (zero_mv / total_mv * 100) if total_mv else 0.0
    total_pct  = l1_sum + unc_pct + zero_pct

    # ── Status ───────────────────────────────────────────────────────────────
    if abs(variance) <= tol:
        status = "PASS"
    elif nonzero_unknown:
        status = "FAIL"   # real money with no L1 classification
    elif zero_unknown:
        status = "WARN"   # only zero-value rows are unclassified
    else:
        status = _status(variance, tol)

    # ── Detail lines ─────────────────────────────────────────────────────────
    missing = sorted(_L1_ASSET_CLASS_NODES - {_fld(ar, "node_key") for ar in alignment})
    detail = [
        f"L1 sum: {l1_sum:.4f}%",
        f"Expected: 100.00%",
        f"Nodes found: {', '.join(found_nodes)}",
    ]
    if missing:
        detail.append(f"Missing L1 nodes (contribute 0%): {', '.join(missing)}")

    if nonzero_unknown:
        syms = ", ".join(
            f"{_fld(h,'symbol','?')} ${_to_float(_fld(h,'market_value')):,.2f} "
            f"({_to_float(_fld(h,'market_value'))/total_mv*100:.2f}%)"
            if total_mv else _fld(h, "symbol", "?")
            for h in sorted(nonzero_unknown,
                            key=lambda x: _to_float(_fld(x, "market_value")),
                            reverse=True)
        )
        detail.append(f"Unclassified (UNKNOWN, non-zero MV, {unc_pct:.4f}%): {syms}")
    if zero_unknown:
        syms = ", ".join(_fld(h, "symbol", "?") for h in zero_unknown)
        detail.append(f"Zero-value UNKNOWN holdings (excluded from gap): {syms}")

    detail.append(
        f"L1 Recognized: {l1_sum:.4f}% | "
        f"L1 Unclassified (non-zero): {unc_pct:.4f}% | "
        f"L1 Excluded (zero-value): {zero_pct:.4f}% | "
        f"Total: {total_pct:.4f}%"
    )

    # ── Sub-checks: one entry per UNKNOWN holding ────────────────────────────
    sub_checks = []
    for h in sorted(unknown_holdings,
                    key=lambda x: _to_float(_fld(x, "market_value")),
                    reverse=True):
        mv  = _to_float(_fld(h, "market_value"))
        pct = mv / total_mv * 100 if total_mv else 0.0
        sub_checks.append({
            "symbol":           _fld(h, "symbol", "?"),
            "description":      _fld(h, "description", ""),
            "market_value":     round(mv, 2),
            "pct_portfolio":    round(pct, 4),
            "security_type":    _fld(h, "security_type", ""),
            "asset_class":      "UNKNOWN",
            "sector":           _fld(h, "sector", ""),
            "operational_state":_fld(h, "operational_state", ""),
            "mv_impact":        "POSITIVE" if mv > 0 else "ZERO",
            "root_cause":       "A: missing_asset_class_mapping",
        })

    return ReconciliationCheck(
        check_id="RC-02",
        name="Allocation Total Reconciliation",
        status=status,
        expected="100.00%",
        actual=f"{l1_sum:.4f}%",
        variance=f"{variance:+.4f}pp",
        tolerance="0.10pp",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-03 — Direct + ETF-derived == effective (per node)
# ─────────────────────────────────────────────────────────────────────────────

def _rc03_decomposition_integrity(
    alignment: list,
) -> ReconciliationCheck:
    """For every alignment node: direct_pct + etf_derived_pct == effective_pct.

    Tolerance: 0.01 percentage points per node.
    """
    tol = 0.01
    sub_checks = []
    failures = []
    for ar in alignment:
        node_key = _fld(ar, "node_key", "")
        direct = _to_float(_fld(ar, "direct_actual_pct"))
        etf = _to_float(_fld(ar, "etf_derived_actual_pct"))
        effective = _to_float(_fld(ar, "effective_actual_pct") or _fld(ar, "actual_pct"))
        calc = direct + etf
        variance = calc - effective
        node_status = _status(variance, tol)
        sub_checks.append({
            "node": node_key,
            "direct": direct,
            "etf_derived": etf,
            "calculated": round(calc, 4),
            "effective": effective,
            "variance": round(variance, 4),
            "status": node_status,
        })
        if node_status != "PASS":
            failures.append(f"{node_key}: direct({direct})+etf({etf})={calc:.4f} ≠ effective({effective})")
    overall_status = "PASS" if not failures else ("WARN" if all(abs(s["variance"]) <= tol * 5 for s in sub_checks) else "FAIL")
    detail = [f"Checked {len(sub_checks)} nodes"] + failures[:10]
    return ReconciliationCheck(
        check_id="RC-03",
        name="Decomposition Integrity (Direct + ETF = Effective)",
        status=overall_status,
        expected="direct + etf_derived == effective for all nodes",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} nodes PASS",
        variance=f"{len(failures)} node(s) mismatch",
        tolerance="0.01pp per node",
        detail=detail,
        sub_checks=sub_checks[:30],
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-04 — ETF decomposition weight validation
# ─────────────────────────────────────────────────────────────────────────────

def _rc04_etf_decomposition_weights() -> ReconciliationCheck:
    """Each ETF registry entry's exposure mix weights must sum to ~100%.

    Checks: exposure_geography_mix, exposure_market_cap_mix, exposure_sector_mix,
            exposure_style_mix.  exposure_thematic_mix is intentionally NOT
            normalized (it uses independent flags).

    Tolerance: 0.10% per mix.
    """
    registry = _load_etf_registry()
    tol = 0.10
    sub_checks = []
    failures = []

    mix_keys = [
        "exposure_geography_mix",
        "exposure_market_cap_mix",
        "exposure_sector_mix",
        "exposure_style_mix",
    ]

    for symbol, model in registry.items():
        if not isinstance(model, dict):
            continue
        for mix_key in mix_keys:
            mix = model.get(mix_key)
            if mix is None:
                continue
            if isinstance(mix, dict):
                total = sum(float(v) for v in mix.values() if v is not None)
            elif isinstance(mix, list):
                total = sum(float(item.get("weight", 0)) for item in mix if isinstance(item, dict))
            else:
                continue
            variance = total - 100.0
            node_status = _status(variance, tol)
            sub_checks.append({
                "symbol": symbol,
                "mix": mix_key,
                "weight_sum": round(total, 4),
                "variance": round(variance, 4),
                "status": node_status,
            })
            if node_status != "PASS":
                failures.append(f"{symbol}.{mix_key}: sum={total:.4f}% (variance {variance:+.4f}pp)")

    overall_status = "PASS" if not failures else "FAIL"
    detail = [f"Checked {len(sub_checks)} mix tables across {len(registry)} registry entries"] + failures[:10]
    return ReconciliationCheck(
        check_id="RC-04",
        name="ETF Decomposition Weight Validation",
        status=overall_status,
        expected="Each mix sums to 100%",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} PASS",
        variance=f"{len(failures)} invalid mix table(s)",
        tolerance="0.10pp per mix",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-05 — Cash position reconciliation
# ─────────────────────────────────────────────────────────────────────────────

def _rc05_cash_reconciliation(
    holdings: list,
    alignment: list,
    snapshot_total_mv: float,
) -> ReconciliationCheck:
    """Actual cash holdings must match the CASH alignment node exactly.

    This check detects the exact double-counting defect uncovered in Phase 6.3D:
    when a holding's sector.upper() == asset_class, it contributes twice.

    Tolerance: $0.01 (one cent).
    """
    # Collect all cash holdings from enriched data
    cash_holdings = []
    for h in holdings:
        ac = str(_fld(h, "asset_class", "") or "").upper()
        op_state = str(_fld(h, "operational_state", "") or "").upper()
        is_ce = _to_bool(_fld(h, "is_cash_equivalent", False))
        sec_type = str(_fld(h, "security_type", "") or "").upper()
        sym = str(_fld(h, "symbol", "") or "").upper()
        if (
            ac == _CASH_ASSET_CLASS
            or op_state == "CASH_EQUIVALENT"
            or is_ce
            or sec_type in _CASH_SECURITY_TYPES
            or sym in _CASH_EQUIVALENT_SYMBOLS
        ):
            mv = _to_float(_fld(h, "market_value"))
            pct = _to_float(_fld(h, "percent_of_portfolio"))
            cash_holdings.append({
                "symbol": _fld(h, "symbol", "?"),
                "market_value": mv,
                "percent_of_portfolio": pct,
                "security_type": _fld(h, "security_type", ""),
                "operational_state": _fld(h, "operational_state", ""),
                "is_cash_equivalent": _to_bool(_fld(h, "is_cash_equivalent", False)),
                "asset_class": _fld(h, "asset_class", ""),
            })

    actual_cash_mv = sum(h["market_value"] for h in cash_holdings)
    actual_cash_pct = (actual_cash_mv / snapshot_total_mv * 100) if snapshot_total_mv > 0 else 0.0

    # Get reported CASH from alignment
    cash_ar = next(
        (ar for ar in alignment if _fld(ar, "node_key") == "CASH"),
        None
    )
    reported_cash_pct = _to_float(_fld(cash_ar, "actual_pct") or _fld(cash_ar, "effective_actual_pct")) if cash_ar else 0.0
    reported_cash_mv = reported_cash_pct / 100.0 * snapshot_total_mv if snapshot_total_mv > 0 else 0.0

    # Compare in percentage points (not dollars) to avoid rounding errors from
    # 4-decimal percentage storage (e.g. 9.0254% → $0.10 residual at $472k).
    # The Phase 6.3D double-count produced a ~9pp variance, so 0.10pp tolerance
    # cleanly separates a genuine defect from a rounding artefact.
    tol_pp = 0.10
    variance_pp = reported_cash_pct - actual_cash_pct
    status = _status(variance_pp, tol_pp)
    variance_mv = reported_cash_mv - actual_cash_mv

    sub_checks = [
        {
            "symbol": h["symbol"],
            "market_value": h["market_value"],
            "security_type": h["security_type"],
            "operational_state": h["operational_state"],
            "is_cash_equivalent": h["is_cash_equivalent"],
            "included_in_cash": True,
        }
        for h in cash_holdings
    ]
    # Spot-check known cash-equivalent symbols not in portfolio
    for sym in sorted(_CASH_EQUIVALENT_SYMBOLS):
        if not any(h["symbol"].upper() == sym for h in cash_holdings):
            sub_checks.append({
                "symbol": sym,
                "market_value": 0.0,
                "security_type": "—",
                "operational_state": "—",
                "is_cash_equivalent": False,
                "included_in_cash": False,
                "not_in_portfolio": True,
            })

    detail = [
        f"Cash holdings found: {len(cash_holdings)}",
        f"Actual cash MV: ${actual_cash_mv:,.2f} ({actual_cash_pct:.4f}%)",
        f"Reported CASH node: {reported_cash_pct:.4f}% (${reported_cash_mv:,.2f})",
        f"Variance: {variance_pp:+.4f}pp (${variance_mv:+,.2f})",
    ]
    if abs(variance_pp) > tol_pp:
        detail.append("⚠️ DOUBLE-COUNT DETECTED — sector.upper()==asset_class path in exposure_decomposition.py")

    return ReconciliationCheck(
        check_id="RC-05",
        name="Cash Position Reconciliation",
        status=status,
        expected=f"${actual_cash_mv:,.2f} ({actual_cash_pct:.4f}%)",
        actual=f"${reported_cash_mv:,.2f} ({reported_cash_pct:.4f}%)",
        variance=f"{variance_pp:+.4f}pp (${variance_mv:+,.2f})",
        tolerance=f"0.10pp",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-06 — Security classification audit
# ─────────────────────────────────────────────────────────────────────────────

def _rc06_classification_audit(
    holdings: list,
    recommendations: list,
) -> ReconciliationCheck:
    """Cash instruments must:
      1. Have security_type == 'Cash'
      2. Have is_cash_equivalent == True
      3. NOT appear in any ETF contributor list

    Detects Phase 6.3D Issue #2: SPAXX leaked into ETF contributor lists.
    """
    registry = _load_etf_registry()
    registry_symbols = {s.upper() for s in registry.keys()}

    violations = []      # hard violations → FAIL
    advisory_notes = []  # CASH_DECOMPOSABLE registry presence → WARN
    sub_checks = []

    for h in holdings:
        ac = str(_fld(h, "asset_class", "") or "").upper()
        op_state = str(_fld(h, "operational_state", "") or "").upper()
        is_ce = _to_bool(_fld(h, "is_cash_equivalent", False))
        sec_type = str(_fld(h, "security_type", "") or "").upper()
        sym = str(_fld(h, "symbol", "") or "").upper()
        mv = _to_float(_fld(h, "market_value"))
        if mv <= 0:
            continue

        is_cash_holding = (
            ac == _CASH_ASSET_CLASS
            or op_state == "CASH_EQUIVALENT"
            or is_ce
        )
        if not is_cash_holding:
            continue

        row_violations = []
        row_notes = []  # advisory notes for this row

        # Rule 1: security_type should be 'Cash'
        if sec_type not in _CASH_SECURITY_TYPES:
            row_violations.append(f"security_type={sec_type!r} (expected 'CASH')")

        # Rule 2: is_cash_equivalent must be True
        if not is_ce:
            row_violations.append("is_cash_equivalent=False (expected True)")

        # Rule 3: must NOT be in ETF registry UNLESS it is a CASH_DECOMPOSABLE entry.
        # CASH_DECOMPOSABLE entries (e.g. SPAXX, VMFXX) have legitimate registry
        # entries to model their economic exposure — not a classification defect.
        if sym in registry_symbols:
            entry = registry.get(sym, {}) or {}
            if entry.get("registry_entry_type") == "CASH_DECOMPOSABLE":
                row_notes.append(
                    f"present in ETF decomposition registry (CASH_DECOMPOSABLE — advisory)"
                )
            else:
                row_violations.append(f"present in ETF decomposition registry ({sym})")

        # Rule 4: must NOT appear as ETF contributor in any recommendation
        for rec in recommendations:
            rec_node = _fld(rec, "affected_node_key", "")
            etf_contrib = _fld(rec, "etf_contributors", []) or []
            if sym in [str(c).upper() for c in etf_contrib]:
                row_violations.append(f"appears as ETF contributor in rec for node={rec_node}")

        if row_violations and row_notes:
            row_status = "FAIL"
        elif row_violations:
            row_status = "FAIL"
        elif row_notes:
            row_status = "WARN"
        else:
            row_status = "PASS"

        if row_violations:
            violations.extend([f"{sym}: {v}" for v in row_violations])
        if row_notes:
            advisory_notes.extend([f"{sym}: {n}" for n in row_notes])

        entry_type = None
        if sym in registry_symbols:
            entry_type = (registry.get(sym, {}) or {}).get("registry_entry_type")

        sub_checks.append({
            "symbol": sym,
            "security_type": sec_type,
            "is_cash_equivalent": is_ce,
            "operational_state": op_state,
            "in_etf_registry": sym in registry_symbols,
            "registry_entry_type": entry_type,
            "status": row_status,
            "violations": row_violations,
            "advisory_notes": row_notes,
        })

    if violations:
        overall_status = "FAIL"
    elif advisory_notes:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    detail = (
        [f"Cash positions audited: {len(sub_checks)}"]
        + [f"VIOLATION: {v}" for v in violations[:10]]
        + [f"ADVISORY: {n}" for n in advisory_notes[:5]]
    )

    return ReconciliationCheck(
        check_id="RC-06",
        name="Security Classification Audit",
        status=overall_status,
        expected="All cash instruments: security_type=Cash, is_cash_equivalent=True, not in non-decomposable ETF registry",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} PASS",
        variance=f"{len(violations)} hard violation(s), {len(advisory_notes)} advisory note(s)",
        tolerance="zero hard violations",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-07 — Archetype target validation
# ─────────────────────────────────────────────────────────────────────────────

def _rc07_archetype_targets() -> ReconciliationCheck:
    """Each archetype profile must:
      1. Sum to 100% across L1 nodes
      2. Have no duplicate node keys
      3. Reference only nodes in the allocation dimensions

    Tolerance: 0.10pp for L1 sum.
    """
    tol = 0.10
    sub_checks = []
    failures = []

    for mandate, filename in {k: v for k, v in _ARCHETYPE_MANDATE_MAP.items()
                               if k in ("CONCENTRATED_ALPHA", "GROWTH", "BALANCED")}.items():
        profile = _load_archetype_profile(filename)
        nodes: dict = profile.get("nodes", {}) or {}
        if not nodes:
            failures.append(f"{mandate}: no nodes loaded from {filename}")
            sub_checks.append({"mandate": mandate, "node_count": 0, "l1_sum": 0, "status": "FAIL"})
            continue

        # Check for duplicate keys (YAML won't have true dups but check anyway)
        keys = list(nodes.keys())
        unique_keys = set(keys)
        has_dups = len(keys) != len(unique_keys)

        # L1 sum
        l1_sum = sum(float(v) for k, v in nodes.items() if k in _L1_ASSET_CLASS_NODES)
        variance = l1_sum - 100.0
        node_status = _status(variance, tol)
        if has_dups:
            node_status = "FAIL"
            failures.append(f"{mandate}: duplicate node keys detected")
        if node_status != "PASS":
            failures.append(f"{mandate}: L1 sum={l1_sum:.4f}% (variance {variance:+.4f}pp)")

        sub_checks.append({
            "mandate": mandate,
            "profile_file": filename,
            "node_count": len(nodes),
            "l1_sum": round(l1_sum, 4),
            "l1_variance": round(variance, 4),
            "has_duplicate_keys": has_dups,
            "status": node_status,
        })

    overall_status = "PASS" if not failures else "FAIL"
    detail = [f"Archetypes validated: {len(sub_checks)}"] + failures[:10]

    return ReconciliationCheck(
        check_id="RC-07",
        name="Archetype Target Validation",
        status=overall_status,
        expected="L1 nodes sum to 100% for all archetypes, no duplicate nodes",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} archetypes PASS",
        variance=f"{len(failures)} failure(s)",
        tolerance="0.10pp L1 sum per archetype",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-08 — Recommendation consistency
# ─────────────────────────────────────────────────────────────────────────────

def _rc08_recommendation_consistency(
    recommendations: list,
    alignment: list,
    mandate_type: str,
) -> ReconciliationCheck:
    """Each recommendation must:
      1. Carry mandate_type == active mandate
      2. Have drift_pct consistent with alignment node (actual - target)

    Tolerance: 0.01pp on drift.
    """
    tol = 0.01
    ar_by_node = {_fld(ar, "node_key"): ar for ar in alignment}
    sub_checks = []
    failures = []

    for rec in recommendations:
        rec_id = _fld(rec, "recommendation_id", "?")
        rec_mandate = str(_fld(rec, "mandate_type", "") or "").upper()
        rec_node = _fld(rec, "affected_node_key", "")
        rec_drift = _to_float(_fld(rec, "drift_pct"))

        row_ok = True
        row_violations = []

        # Rule 1: mandate_type must match
        if rec_mandate and rec_mandate != mandate_type.upper():
            row_violations.append(f"mandate_type={rec_mandate!r} ≠ active {mandate_type!r}")
            row_ok = False

        # Rule 2: drift must match alignment node
        if rec_node and rec_node in ar_by_node:
            ar = ar_by_node[rec_node]
            ar_drift = _to_float(_fld(ar, "drift_pct"))
            drift_delta = abs(rec_drift - ar_drift)
            if drift_delta > tol:
                row_violations.append(
                    f"drift mismatch: rec={rec_drift:.4f}% vs alignment={ar_drift:.4f}% (delta={drift_delta:.4f})"
                )
                row_ok = False

        row_status = "PASS" if row_ok else "FAIL"
        if row_violations:
            failures.extend([f"{rec_id}/{rec_node}: {v}" for v in row_violations])

        sub_checks.append({
            "recommendation_id": rec_id,
            "affected_node_key": rec_node,
            "mandate_type": rec_mandate,
            "drift_pct": rec_drift,
            "status": row_status,
            "violations": row_violations,
        })

    overall_status = "PASS" if not failures else "FAIL"
    detail = [f"Recommendations checked: {len(sub_checks)}"] + failures[:10]

    return ReconciliationCheck(
        check_id="RC-08",
        name="Recommendation Consistency",
        status=overall_status,
        expected=f"All recs: mandate_type={mandate_type}, drift matches alignment",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} PASS",
        variance=f"{len(failures)} violation(s)",
        tolerance="0.01pp drift delta",
        detail=detail,
        sub_checks=sub_checks[:20],
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-09 — Holding classification consistency
# ─────────────────────────────────────────────────────────────────────────────

# Impossible combinations: (asset_class, security_type) pairs that cannot
# logically coexist.
_IMPOSSIBLE_STATES: list[tuple[str, str, str]] = [
    ("CASH",         "ETF",          "Cash holding classified as ETF"),
    ("CASH",         "MUTUAL_FUND",  "Cash holding classified as Mutual Fund"),
    ("CASH",         "COMMON STOCK", "Cash holding classified as Common Stock"),
    ("CASH",         "BOND",         "Cash holding classified as Bond"),
    ("FIXED_INCOME", "COMMON STOCK", "Bond holding classified as Common Stock"),
    ("DIGITAL",      "BOND",         "Digital asset classified as Bond"),
    ("DIGITAL",      "FIXED_INCOME", "Digital asset classified as Fixed Income"),
    ("EQUITIES",     "BOND",         "Equity classified as Bond"),
]

def _rc09_classification_consistency(
    holdings: list,
) -> ReconciliationCheck:
    """Detect impossible asset_class / security_type combinations."""
    sub_checks = []
    violations = []

    for h in holdings:
        mv = _to_float(_fld(h, "market_value"))
        if mv <= 0:
            continue
        sym = str(_fld(h, "symbol", "") or "").upper()
        ac = str(_fld(h, "asset_class", "") or "").upper()
        sec_type = str(_fld(h, "security_type", "") or "").upper()

        row_violations = []
        for (bad_ac, bad_st, msg) in _IMPOSSIBLE_STATES:
            if ac == bad_ac and sec_type == bad_st:
                row_violations.append(msg)

        if row_violations:
            violations.extend([f"{sym}: {v}" for v in row_violations])
            sub_checks.append({
                "symbol": sym,
                "asset_class": ac,
                "security_type": sec_type,
                "status": "FAIL",
                "violations": row_violations,
            })

    overall_status = "PASS" if not violations else "FAIL"
    detail = [f"Impossible state violations: {len(violations)}"] + violations[:15]

    return ReconciliationCheck(
        check_id="RC-09",
        name="Holding Classification Consistency",
        status=overall_status,
        expected="No impossible asset_class / security_type combinations",
        actual=f"{len(violations)} impossible state(s) detected",
        variance=f"{len(violations)} violation(s)",
        tolerance="zero violations",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-10 — Portfolio philosophy consistency
# ─────────────────────────────────────────────────────────────────────────────

def _rc10_philosophy_consistency(
    recommendations: list,
    mandate_type: str,
) -> ReconciliationCheck:
    """All recommendations must use the same mandate as the analysis run.

    Also validates that all PMI fields (mandate_type, mandate_severity,
    mandate_urgency, mandate_drift_label) are populated.
    """
    violations = []
    sub_checks = []
    active_mandate = mandate_type.upper()

    for rec in recommendations:
        rec_id = _fld(rec, "recommendation_id", "?")
        rec_mandate = str(_fld(rec, "mandate_type", "") or "").upper()
        rec_type = str(_fld(rec, "recommendation_type", "") or "").upper()
        mandate_sev = _fld(rec, "mandate_severity", None)
        mandate_urg = _fld(rec, "mandate_urgency", None)
        mandate_label = _fld(rec, "mandate_drift_label", None)

        row_violations = []

        # Mandate consistency
        if rec_mandate and rec_mandate != active_mandate:
            row_violations.append(f"mandate_type={rec_mandate!r} ≠ run mandate {active_mandate!r}")

        # PMI fields present (apply to all recommendation types)
        if mandate_sev is None or mandate_sev == "":
            row_violations.append("mandate_severity missing")
        if mandate_urg is None or mandate_urg == "":
            row_violations.append("mandate_urgency missing")

        # mandate_drift_label is only applicable to allocation-type recommendations.
        # Non-allocation types (explainability cards, narrative cards, etc.) do not
        # carry allocation drift context — absence of the label is correct, not a defect.
        label_applicable = rec_type in _ALLOCATION_REC_TYPES
        if label_applicable:
            if mandate_label is None or mandate_label == "":
                row_violations.append("mandate_drift_label missing")

        if row_violations:
            violations.extend([f"{rec_id}: {v}" for v in row_violations])

        sub_checks.append({
            "recommendation_id": rec_id,
            "recommendation_type": rec_type,
            "mandate_type": rec_mandate,
            "mandate_severity": mandate_sev,
            "mandate_urgency": mandate_urg,
            "mandate_drift_label": mandate_label,
            "label_applicable": label_applicable,
            "status": "PASS" if not row_violations else "FAIL",
            "violations": row_violations,
        })

    overall_status = "PASS" if not violations else "FAIL"
    n_allocation = sum(1 for s in sub_checks if s["label_applicable"])
    detail = [
        f"Active mandate: {active_mandate}",
        f"Recommendations checked: {len(sub_checks)}",
        f"Allocation-type recs (label check applies): {n_allocation}",
        f"Violations: {len(violations)}",
    ] + violations[:10]

    return ReconciliationCheck(
        check_id="RC-10",
        name="Portfolio Philosophy Consistency",
        status=overall_status,
        expected=f"All recs: mandate_type={active_mandate}, PMI fields populated; allocation recs: mandate_drift_label populated",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} PASS",
        variance=f"{len(violations)} violation(s)",
        tolerance="zero violations",
        detail=detail,
        sub_checks=sub_checks[:20],
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-12 — Taxonomy normalization
# ─────────────────────────────────────────────────────────────────────────────

def _rc12_taxonomy_normalization(alignment: list) -> ReconciliationCheck:
    """RC-12 — Taxonomy Normalization.

    Verify that every node_key produced by the alignment engine uses canonical
    dot-notation taxonomy (e.g. FIXED_INCOME, not FIXED INCOME).

    FAIL  — one or more known alias keys or duplicate canonical mappings found.
    WARN  — unknown node keys exist that cannot be aliased (may be new nodes).
    PASS  — all node keys are canonical.
    """
    from src.portfolio.taxonomy import find_aliases_in_collection, normalize_node_key

    node_keys = [_fld(r, "node_key", "") for r in alignment if _fld(r, "node_key")]

    # Split into alias violations, unknown keys
    raw_aliases = find_aliases_in_collection(node_keys)
    alias_violations = [(k, c) for k, c in raw_aliases if c is not None]
    unknown_violations = [(k, c) for k, c in raw_aliases if c is None]

    # Detect duplicate canonical collisions: node appears under both alias and
    # canonical form in the same alignment output.
    canonical_forms: dict[str, set[str]] = {}
    for key in node_keys:
        canon = normalize_node_key(key) if key else ""
        if canon:
            canonical_forms.setdefault(canon, set()).add(key.strip().upper())
    duplicates = {k: sorted(v) for k, v in canonical_forms.items() if len(v) > 1}

    n_alias = len(alias_violations)
    n_dup = len(duplicates)
    n_unknown = len(unknown_violations)

    if n_alias > 0 or n_dup > 0:
        status = "FAIL"
    elif n_unknown > 0:
        status = "WARN"
    else:
        status = "PASS"

    sub_checks: list[dict] = []
    for alias, canonical in alias_violations:
        sub_checks.append({
            "node_key": alias,
            "description": f"Alias '{alias}' should be canonical '{canonical}'",
            "status": "FAIL",
            "root_cause": "alias_collision",
        })
    for node, variants in duplicates.items():
        sub_checks.append({
            "node_key": node,
            "description": f"Node '{node}' appears with mixed forms: {variants}",
            "status": "FAIL",
            "root_cause": "duplicate_canonical",
        })
    for alias, _ in unknown_violations:
        sub_checks.append({
            "node_key": alias,
            "description": f"Node key '{alias}' not in canonical taxonomy (possible new node)",
            "status": "WARN",
            "root_cause": "unknown_node",
        })

    total_nodes = len(set(node_keys))
    detail_parts: list[str] = []
    for k, c in alias_violations[:5]:
        detail_parts.append(f"Alias violation: '{k}' → '{c}'")
    for n in list(duplicates)[:5]:
        detail_parts.append(f"Duplicate canonical: '{n}'")
    for k, _ in unknown_violations[:5]:
        detail_parts.append(f"Unknown node: '{k}'")

    return ReconciliationCheck(
        check_id="RC-12",
        name="Taxonomy Normalization",
        status=status,
        expected="All alignment node_keys use canonical dot-notation taxonomy",
        actual=(
            f"{total_nodes} unique node keys | "
            f"{n_alias} alias(es) | {n_dup} duplicate(s) | {n_unknown} unknown(s)"
        ),
        variance=f"{n_alias + n_dup} violation(s)" if (n_alias + n_dup) else "none",
        tolerance="zero violations",
        detail="; ".join(detail_parts) if detail_parts else "All node keys canonical.",
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-13 — Coverage reconciliation
# ─────────────────────────────────────────────────────────────────────────────

# Signal field definitions: display name → holdings CSV column name
_COVERAGE_SIGNALS: dict[str, str] = {
    "ESS": "ess_score_text",
    "Zacks": "zacks_rating",
    "Composite": "composite_score",
}

# Grade thresholds (% holdings coverage)
_COVERAGE_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (95.0, "A"),
    (90.0, "B"),
    (80.0, "C"),
    (70.0, "D"),
    (0.0,  "F"),
]

# Security types that are eligible for individual-stock signal coverage.
# ETFs, Cash, Digital assets, and mutual funds are structurally excluded —
# providers do not issue per-holding ESS/Zacks scores for these instruments.
_COVERAGE_ELIGIBLE_SECURITY_TYPES: frozenset[str] = frozenset({
    "Common Stock",
    "Depository Receipt",
})

# Asset classes that are structurally excluded from individual-stock signals
# regardless of security_type (e.g. a fund misclassified as Common Stock).
_COVERAGE_EXCLUDED_ASSET_CLASSES: frozenset[str] = frozenset({
    "CASH",
    "DIGITAL",
})


def _coverage_grade(pct: float) -> str:
    for threshold, grade in _COVERAGE_GRADE_THRESHOLDS:
        if pct >= threshold:
            return grade
    return "F"


def _is_ess_eligible(holding: Any) -> bool:
    """Return True when a holding is eligible for individual-stock signal coverage.

    Eligibility requires:
    - security_type is Common Stock or Depository Receipt, AND
    - asset_class is not CASH or DIGITAL (structural exclusions).
    """
    sec_type = str(_fld(holding, "security_type", "") or "").strip()
    asset_class = str(_fld(holding, "asset_class", "") or "").strip().upper()
    return (
        sec_type in _COVERAGE_ELIGIBLE_SECURITY_TYPES
        and asset_class not in _COVERAGE_EXCLUDED_ASSET_CLASSES
    )


def _rc13_coverage_reconciliation(holdings: list) -> ReconciliationCheck:
    """RC-13 — Coverage Reconciliation.

    Distinguishes eligible equity coverage from total portfolio coverage.

    Eligible equities: Common Stock and Depository Receipt holdings whose
    asset_class is not CASH or DIGITAL. ETFs, cash, digital assets, and
    mutual funds are structurally excluded from individual-stock signals.

    Status rules:
      FAIL  — any signal reports impossible coverage (> 100%) or math error.
      WARN  — any signal earns grade F on eligible-equity coverage (< 70%).
      PASS  — all eligible-equity coverage is grade D or better; math reconciles.

    Total portfolio coverage is always reported in sub_checks for transparency
    but does not drive WARN/FAIL by itself.
    """
    n_total = len(holdings)
    if n_total == 0:
        return ReconciliationCheck(
            check_id="RC-13",
            name="Coverage Reconciliation",
            status="WARN",
            expected="Non-empty holdings list with coverage signals",
            actual="0 holdings",
            variance="N/A",
            tolerance="zero coverage > 100% violations",
            detail="No holdings to evaluate coverage.",
            sub_checks=[],
        )

    total_mv = sum(_to_float(_fld(h, "market_value")) for h in holdings)

    eligible = [h for h in holdings if _is_ess_eligible(h)]
    excluded = [h for h in holdings if not _is_ess_eligible(h)]
    n_eligible = len(eligible)
    n_excluded = len(excluded)

    violations: list[str] = []
    sub_checks: list[dict] = []
    f_grade_eligible_signals: list[str] = []

    for signal_name, field in _COVERAGE_SIGNALS.items():
        def _has_signal(h: Any) -> bool:
            return bool(str(_fld(h, field, "") or "").strip())

        # ── Total portfolio coverage (transparency only) ──────────────────
        covered_total = [h for h in holdings if _has_signal(h)]
        n_covered_total = len(covered_total)
        pct_total = n_covered_total / n_total * 100.0
        mv_covered_total = sum(_to_float(_fld(h, "market_value")) for h in covered_total)
        pct_mv_total = mv_covered_total / total_mv * 100.0 if total_mv > 0 else 0.0
        grade_total = _coverage_grade(pct_total)

        # ── Eligible equity coverage (drives grading) ─────────────────────
        covered_elig = [h for h in eligible if _has_signal(h)]
        n_covered_elig = len(covered_elig)
        pct_eligible = n_covered_elig / n_eligible * 100.0 if n_eligible > 0 else 100.0
        grade_eligible = _coverage_grade(pct_eligible) if n_eligible > 0 else "A"

        # ── Reconciliation integrity checks ───────────────────────────────
        over_100 = pct_total > 100.01 or pct_mv_total > 100.01
        count_mismatch = n_covered_total > n_total
        if over_100 or count_mismatch:
            violations.append(
                f"{signal_name}: impossible coverage "
                f"({n_covered_total}/{n_total} = {pct_total:.1f}% holdings)"
            )

        if grade_eligible == "F" and n_eligible > 0:
            f_grade_eligible_signals.append(signal_name)

        sub_checks.append({
            "signal": signal_name,
            "field": field,
            # Total portfolio metrics (all holdings)
            "holdings_covered": n_covered_total,
            "holdings_total": n_total,
            "pct_holdings": round(pct_total, 2),
            "pct_mv": round(pct_mv_total, 2),
            "grade": grade_total,
            # Eligible equity metrics (drives status)
            "eligible_covered": n_covered_elig,
            "eligible_total": n_eligible,
            "pct_eligible": round(pct_eligible, 2),
            "grade_eligible": grade_eligible,
            # Structural exclusion summary
            "structural_excluded": n_excluded,
            "status": "FAIL" if (over_100 or count_mismatch) else "PASS",
        })

    has_fail = bool(violations)
    if has_fail:
        status = "FAIL"
    elif f_grade_eligible_signals:
        status = "WARN"
    else:
        status = "PASS"

    summary_parts = [
        f"{sc['signal']}: {sc['eligible_covered']}/{sc['eligible_total']} eligible "
        f"({sc['pct_eligible']:.1f}% Grade {sc['grade_eligible']}) | "
        f"total {sc['holdings_covered']}/{n_total} ({sc['pct_holdings']:.1f}% Grade {sc['grade']})"
        for sc in sub_checks
    ]

    structural_note = (
        f"{n_excluded}/{n_total} holdings structurally excluded "
        f"(ETFs, cash, digital, funds)"
        if n_excluded > 0
        else "no structural exclusions"
    )

    return ReconciliationCheck(
        check_id="RC-13",
        name="Coverage Reconciliation",
        status=status,
        expected=(
            "Eligible equity coverage ≥ 70% (grade D) per signal; "
            "coverage counts ≤ 100%"
        ),
        actual=" | ".join(summary_parts),
        variance=f"{len(violations)} violation(s)" if violations else "none",
        tolerance="zero coverage > 100% violations; eligible equity grade D or better",
        detail=(
            "Violations: " + "; ".join(violations)
            if violations
            else (
                f"Eligible equity grade F: {', '.join(f_grade_eligible_signals)}. "
                f"{structural_note}."
                if f_grade_eligible_signals
                else f"All eligible equity coverage grade D or better. {structural_note}."
            )
        ),
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RC-ZV01 — Zero-value position integrity
# ─────────────────────────────────────────────────────────────────────────────

def _rczv01_zero_value_integrity(holdings: list) -> ReconciliationCheck:
    """RC-ZV01 — Zero-Value Position Integrity.

    Verify that no zero-value holding (market_value == 0.0) has leaked into
    the investable holdings list.  All such positions should have been
    classified as ZERO_VALUE_LEGACY_POSITION by the ingestion pipeline and
    excluded from analytics before reconciliation runs.

    Rules (applied only when zero-value holdings are found):
      1. operational_state must be ZERO_VALUE_LEGACY_POSITION
      2. percent_of_portfolio must be 0.0
      3. is_cash_equivalent must be False

    Status:
      PASS  — no zero-value holdings in investable list (correct exclusion), or
              all zero-value holdings found are correctly classified.
      FAIL  — one or more zero-value holdings are misclassified.
    """
    zero_holdings = [
        h for h in holdings
        if _to_float(_fld(h, "market_value")) == 0.0
    ]

    if not zero_holdings:
        return ReconciliationCheck(
            check_id="RC-ZV01",
            name="Zero-Value Position Integrity",
            status="PASS",
            expected="All zero-value holdings classified as ZERO_VALUE_LEGACY_POSITION",
            actual="0 zero-value holdings in investable list",
            variance="none",
            tolerance="zero violations",
            detail=["No zero-value holdings in investable list — correctly excluded by pipeline."],
            sub_checks=[],
        )

    violations = []
    sub_checks = []

    for h in zero_holdings:
        sym = str(_fld(h, "symbol", "") or "").upper()
        op_state = str(_fld(h, "operational_state", "") or "").upper()
        pct_portfolio = _to_float(_fld(h, "percent_of_portfolio"))
        is_ce = _to_bool(_fld(h, "is_cash_equivalent", False))

        row_violations = []

        # Rule 1: must be classified as ZERO_VALUE_LEGACY_POSITION
        if op_state != "ZERO_VALUE_LEGACY_POSITION":
            row_violations.append(
                f"operational_state={op_state!r} (expected 'ZERO_VALUE_LEGACY_POSITION')"
            )

        # Rule 2: percent_of_portfolio must be 0.0
        if pct_portfolio > 0.0:
            row_violations.append(f"percent_of_portfolio={pct_portfolio} (expected 0.0)")

        # Rule 3: must not be marked as cash equivalent
        if is_ce:
            row_violations.append("is_cash_equivalent=True (must be False for zero-value positions)")

        if row_violations:
            violations.extend([f"{sym}: {v}" for v in row_violations])

        sub_checks.append({
            "symbol": sym,
            "operational_state": op_state,
            "market_value": _to_float(_fld(h, "market_value")),
            "percent_of_portfolio": pct_portfolio,
            "is_cash_equivalent": is_ce,
            "status": "PASS" if not row_violations else "FAIL",
            "violations": row_violations,
        })

    overall_status = "PASS" if not violations else "FAIL"
    detail = [
        f"Zero-value holdings in investable list: {len(zero_holdings)}",
        f"Correctly classified: {sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)}",
    ] + violations[:10]

    return ReconciliationCheck(
        check_id="RC-ZV01",
        name="Zero-Value Position Integrity",
        status=overall_status,
        expected="All zero-value holdings: operational_state=ZERO_VALUE_LEGACY_POSITION, percent_of_portfolio=0.0",
        actual=f"{sum(1 for s in sub_checks if s['status'] == 'PASS')}/{len(sub_checks)} PASS",
        variance=f"{len(violations)} violation(s)",
        tolerance="zero violations",
        detail=detail,
        sub_checks=sub_checks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_reconciliation(
    *,
    holdings: list,
    alignment: list,
    recommendations: list,
    mandate_type: str,
    snapshot_total_mv: float,
    run_id: str,
    generated_at: Optional[str] = None,
) -> ReconciliationResult:
    """Execute all reconciliation checks and return a ReconciliationResult.

    Checks executed:
      RC-01  Portfolio Value Reconciliation
      RC-02  Allocation Total Reconciliation
      RC-03  Decomposition Integrity (Direct + ETF = Effective)
      RC-04  ETF Decomposition Weight Validation
      RC-05  Cash Position Reconciliation
      RC-06  Security Classification Audit (CASH_DECOMPOSABLE advisory)
      RC-07  Archetype Target Validation
      RC-08  Recommendation Consistency
      RC-09  Holding Classification Consistency
      RC-10  Portfolio Philosophy Consistency (_ALLOCATION_REC_TYPES scoped)
      RC-12  Taxonomy Normalization
      RC-13  Coverage Reconciliation
      RC-ZV01 Zero-Value Position Integrity

    Args:
        holdings:          list of PortfolioHolding (dataclass) or dict rows
        alignment:         list of AllocationAlignmentResult (dataclass) or dict rows
        recommendations:   list of recommendation dicts (with mandate overlay fields)
        mandate_type:      active mandate type for this run
        snapshot_total_mv: total market value from the PortfolioSnapshot
        run_id:            analysis run identifier
        generated_at:      ISO datetime string (defaults to now)
    """
    from datetime import datetime, timezone
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    checks = [
        _rc01_portfolio_value(holdings, snapshot_total_mv),
        _rc02_allocation_totals(alignment, holdings),
        _rc03_decomposition_integrity(alignment),
        _rc04_etf_decomposition_weights(),
        _rc05_cash_reconciliation(holdings, alignment, snapshot_total_mv),
        _rc06_classification_audit(holdings, recommendations),
        _rc07_archetype_targets(),
        _rc08_recommendation_consistency(recommendations, alignment, mandate_type),
        _rc09_classification_consistency(holdings),
        _rc10_philosophy_consistency(recommendations, mandate_type),
        _rc12_taxonomy_normalization(alignment),
        _rc13_coverage_reconciliation(holdings),
        _rczv01_zero_value_integrity(holdings),
    ]

    passed = sum(1 for c in checks if c.status == "PASS")
    warned = sum(1 for c in checks if c.status == "WARN")
    failed = sum(1 for c in checks if c.status == "FAIL")

    # Overall: FAIL if any FAIL; WARN if any WARN; else PASS
    if failed > 0:
        overall = "FAIL"
    elif warned > 0:
        overall = "WARN"
    else:
        overall = "PASS"

    certification = (
        f"{passed}/{len(checks)} checks PASS"
        + (f", {warned} WARN" if warned else "")
        + (f", {failed} FAIL" if failed else "")
    )

    return ReconciliationResult(
        run_id=run_id,
        generated_at=generated_at,
        overall_status=overall,
        checks_passed=passed,
        checks_warned=warned,
        checks_failed=failed,
        checks=checks,
        certification=certification,
    )
