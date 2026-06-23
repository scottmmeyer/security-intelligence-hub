"""PA-006 — Allocation Drift Compliance & Persistence Intelligence.

Evaluates historical allocation drift against policy targets to determine
compliance status for every allocation node over time.

Reads existing PAR alignment.csv artifacts.  Uses the SIH-computed `severity`
field (HIGH/MODERATE/LOW/NONE) as the compliance classifier.  PIS does not
re-derive tolerance bands — it uses SIH's own assessment.

Architecture: SIH decides what severity a drift represents.
             PIS observes and tracks whether compliance is achieved.

Read from:
  - data/portfolio_ingestion/analysis_runs/*/alignment.csv

Write to:
  - data/history/pis/compliance/  (derived governance artifacts)

Public API
----------
  pis_compliance_summary(repo_root)  → dict   (summary cards)
  pis_compliance_latest(repo_root)   → dict   (per-node latest status + streaks)
  pis_compliance_history(repo_root)  → dict   (full timeline per node)
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_MAX_OBSERVATIONS = 6
_CACHE_FILENAME = "compliance_cache.json"

# Compliance severity label thresholds
_HIGHLY_COMPLIANT_MIN = 80.0
_MOSTLY_COMPLIANT_MIN = 60.0
_MIXED_MIN = 40.0


# ─── Data models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ComplianceEntry:
    snapshot_date: str
    node_key: str
    node_label: str
    dimension_type: str
    compliance_status: str    # COMPLIANT | WARNING | NON_COMPLIANT
    severity: str             # original SIH: NONE | LOW | MODERATE | HIGH
    drift_pct: float
    actual_pct: float
    target_pct: float
    drift_direction: str


@dataclass(frozen=True)
class NodeComplianceResult:
    node_key: str
    node_label: str
    dimension_type: str
    dates_available: int
    compliant_count: int
    warning_count: int
    non_compliant_count: int
    compliance_rate_pct: float
    non_compliance_rate_pct: float
    compliance_severity: str
    current_status: str
    current_streak: int
    longest_compliant_streak: int
    longest_non_compliant_streak: int
    current_drift_pct: float
    current_actual_pct: float
    current_target_pct: float


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _safe_float(v: object, default: float = 0.0) -> float:
    try:
        return float(str(v or "").strip() or default)
    except (TypeError, ValueError):
        return default


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ─── Classification ───────────────────────────────────────────────────────────


def _severity_to_compliance(severity: str) -> str:
    """Map SIH alignment severity to PIS compliance status.

    Uses SIH's own severity assessment — PIS does not re-derive tolerance bands.
    """
    sev = str(severity or "").strip().upper()
    if sev in {"NONE", "LOW"}:
        return "COMPLIANT"
    if sev == "MODERATE":
        return "WARNING"
    if sev == "HIGH":
        return "NON_COMPLIANT"
    return "COMPLIANT"  # unknown → benefit of the doubt


def _compliance_severity_label(compliance_rate_pct: float) -> str:
    if compliance_rate_pct >= _HIGHLY_COMPLIANT_MIN:
        return "HIGHLY_COMPLIANT"
    if compliance_rate_pct >= _MOSTLY_COMPLIANT_MIN:
        return "MOSTLY_COMPLIANT"
    if compliance_rate_pct >= _MIXED_MIN:
        return "MIXED"
    return "PERSISTENTLY_NON_COMPLIANT"


# ─── Step 1 — PAR data loading ────────────────────────────────────────────────


def _collect_canonical_runs(repo_root: Path) -> list[tuple[str, Path]]:
    """Return [(snapshot_date, alignment_path), ...] sorted ascending."""
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return []

    by_date: dict[str, tuple[str, Path]] = {}
    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta_file = par_path / "run_metadata.json"
        align_file = par_path / "alignment.csv"
        if not meta_file.exists() or not align_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        snap_date = str(meta.get("snapshot_date", "") or "")[:10]
        created_at = str(meta.get("created_at_utc", "") or "")
        if len(snap_date) != 10:
            continue
        try:
            date.fromisoformat(snap_date)
        except ValueError:
            continue
        if snap_date not in by_date or created_at > by_date[snap_date][0]:
            by_date[snap_date] = (created_at, align_file)

    return sorted([(d, by_date[d][1]) for d in by_date], key=lambda x: x[0])


def _collect_compliance_entries(repo_root: Path) -> list[ComplianceEntry]:
    canonical_runs = _collect_canonical_runs(repo_root)
    entries: list[ComplianceEntry] = []

    for snap_date, align_file in canonical_runs:
        for row in _read_csv(align_file):
            node_key = str(row.get("node_key", "") or "").strip()
            if not node_key:
                continue
            severity = str(row.get("severity", "") or "").strip().upper()
            compliance_status = _severity_to_compliance(severity)

            actual = _safe_float(row.get("effective_actual_pct") or row.get("actual_pct"))
            target = _safe_float(row.get("tactical_target_pct") or row.get("target_pct"))

            entries.append(ComplianceEntry(
                snapshot_date=snap_date,
                node_key=node_key,
                node_label=str(row.get("node_label", "") or node_key),
                dimension_type=str(row.get("dimension_type", "") or ""),
                compliance_status=compliance_status,
                severity=severity,
                drift_pct=_safe_float(row.get("drift_pct")),
                actual_pct=actual,
                target_pct=target,
                drift_direction=str(row.get("drift_direction", "") or ""),
            ))

    return sorted(entries, key=lambda e: (e.node_key, e.snapshot_date))


# ─── Step 2 — Streak computation ─────────────────────────────────────────────


def _compute_streaks(entries: list[ComplianceEntry]) -> tuple[int, int, int]:
    """Return (current_streak, longest_compliant_streak, longest_non_compliant_streak)."""
    if not entries:
        return 0, 0, 0

    current_status = entries[-1].compliance_status
    current_streak = 0
    for e in reversed(entries):
        if e.compliance_status == current_status:
            current_streak += 1
        else:
            break

    longest_compliant = 0
    longest_non_compliant = 0
    run_len = 1

    def _update(status: str, length: int) -> None:
        nonlocal longest_compliant, longest_non_compliant
        if status == "COMPLIANT":
            longest_compliant = max(longest_compliant, length)
        elif status == "NON_COMPLIANT":
            longest_non_compliant = max(longest_non_compliant, length)

    for i in range(1, len(entries)):
        if entries[i].compliance_status == entries[i - 1].compliance_status:
            run_len += 1
        else:
            _update(entries[i - 1].compliance_status, run_len)
            run_len = 1
    _update(entries[-1].compliance_status, run_len)

    return current_streak, longest_compliant, longest_non_compliant


# ─── Step 3 — Node analytics ─────────────────────────────────────────────────


def _compute_node_compliance(
    node_key: str,
    node_label: str,
    dimension_type: str,
    entries: list[ComplianceEntry],
) -> NodeComplianceResult:
    total = len(entries)
    compliant = sum(1 for e in entries if e.compliance_status == "COMPLIANT")
    warning = sum(1 for e in entries if e.compliance_status == "WARNING")
    non_compliant = sum(1 for e in entries if e.compliance_status == "NON_COMPLIANT")

    rate = round(compliant / total * 100, 1) if total else 0.0
    non_rate = round(non_compliant / total * 100, 1) if total else 0.0

    current_streak, longest_compliant, longest_non_compliant = _compute_streaks(entries)
    latest = entries[-1]

    return NodeComplianceResult(
        node_key=node_key,
        node_label=node_label,
        dimension_type=dimension_type,
        dates_available=total,
        compliant_count=compliant,
        warning_count=warning,
        non_compliant_count=non_compliant,
        compliance_rate_pct=rate,
        non_compliance_rate_pct=non_rate,
        compliance_severity=_compliance_severity_label(rate),
        current_status=latest.compliance_status,
        current_streak=current_streak,
        longest_compliant_streak=longest_compliant,
        longest_non_compliant_streak=longest_non_compliant,
        current_drift_pct=latest.drift_pct,
        current_actual_pct=latest.actual_pct,
        current_target_pct=latest.target_pct,
    )


def _build_node_results(entries: list[ComplianceEntry]) -> list[NodeComplianceResult]:
    by_node: dict[str, list[ComplianceEntry]] = defaultdict(list)
    node_meta: dict[str, tuple[str, str]] = {}
    for e in entries:
        by_node[e.node_key].append(e)
        if e.node_key not in node_meta:
            node_meta[e.node_key] = (e.node_label, e.dimension_type)

    results = []
    for node_key in sorted(by_node):
        node_entries = sorted(by_node[node_key], key=lambda e: e.snapshot_date)
        label, dim = node_meta[node_key]
        results.append(_compute_node_compliance(node_key, label, dim, node_entries))
    return results


# ─── Step 4 — Governance observations ────────────────────────────────────────


def _generate_observations(
    results: list[NodeComplianceResult],
    dates_covered: int,
) -> list[str]:
    obs: list[str] = []

    # Persistently non-compliant (worst)
    persistent = sorted(
        [r for r in results if r.compliance_severity == "PERSISTENTLY_NON_COMPLIANT"],
        key=lambda r: r.compliance_rate_pct,
    )
    for r in persistent[:2]:
        nc = r.compliant_count + r.warning_count + r.non_compliant_count
        obs.append(
            f"{r.node_label} has been non-compliant on "
            f"{r.non_compliant_count} of {nc} canonical dates "
            f"(compliance rate: {r.compliance_rate_pct:.0f}%). "
            "Governance review recommended."
        )

    # Warning-dominant nodes (warning ≥ 50% of dates)
    warning_heavy = [
        r for r in results
        if r.warning_count / r.dates_available >= 0.5 if r.dates_available > 0
        and r.compliance_severity not in ("PERSISTENTLY_NON_COMPLIANT",)
    ]
    for r in warning_heavy[:2]:
        if len(obs) >= _MAX_OBSERVATIONS:
            break
        obs.append(
            f"{r.node_label} has been in WARNING state for "
            f"{r.warning_count} of {r.dates_available} dates "
            f"(drift persists outside target)."
        )

    # Long non-compliant streak
    long_streak = sorted(results, key=lambda r: r.longest_non_compliant_streak, reverse=True)
    if long_streak and long_streak[0].longest_non_compliant_streak >= 5:
        r = long_streak[0]
        if len(obs) < _MAX_OBSERVATIONS:
            obs.append(
                f"{r.node_label} has the longest non-compliant streak: "
                f"{r.longest_non_compliant_streak} consecutive canonical dates."
            )

    # Highly compliant nodes
    hc = sorted(
        [r for r in results if r.compliance_severity == "HIGHLY_COMPLIANT" and r.dates_available >= 5],
        key=lambda r: r.compliance_rate_pct,
        reverse=True,
    )
    if hc and len(obs) < _MAX_OBSERVATIONS:
        r = hc[0]
        obs.append(
            f"{r.node_label} exhibits the highest compliance rate at "
            f"{r.compliance_rate_pct:.0f}% ({r.compliant_count} of {r.dates_available} dates)."
        )

    # Summary
    compliant_now = sum(1 for r in results if r.current_status == "COMPLIANT")
    if len(obs) < _MAX_OBSERVATIONS:
        obs.append(
            f"{compliant_now} of {len(results)} allocation nodes are currently compliant "
            f"across {dates_covered} observed dates."
        )

    return obs[:_MAX_OBSERVATIONS]


# ─── Cache ────────────────────────────────────────────────────────────────────


def _cache_path(repo_root: Path) -> Path:
    return repo_root / "data" / "history" / "pis" / "compliance" / _CACHE_FILENAME


def _cache_is_valid(cache: Path, repo_root: Path) -> bool:
    if not cache.exists():
        return False
    try:
        cache_mtime = cache.stat().st_mtime
    except OSError:
        return False
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return True
    for par_path in par_dir.iterdir():
        if not par_path.is_dir():
            continue
        meta = par_path / "run_metadata.json"
        try:
            if meta.exists() and meta.stat().st_mtime > cache_mtime:
                return False
        except OSError:
            continue
    return True


def _get_computed(repo_root: Path) -> tuple[
    list[ComplianceEntry],
    list[NodeComplianceResult],
    list[str],
    list[str],
]:
    """Return (entries, results, canonical_dates, observations)."""
    cache = _cache_path(repo_root)
    if _cache_is_valid(cache, repo_root):
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            entries = [ComplianceEntry(**e) for e in cached.get("entries", [])]
            results = [NodeComplianceResult(**r) for r in cached.get("results", [])]
            dates = cached.get("dates", [])
            obs = cached.get("observations", [])
            return entries, results, dates, obs
        except Exception:
            pass

    canonical_runs = _collect_canonical_runs(repo_root)
    canonical_dates = [d for d, _ in canonical_runs]
    entries = _collect_compliance_entries(repo_root)
    results = _build_node_results(entries)
    observations = _generate_observations(results, len(canonical_dates))

    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps({
                "entries": [asdict(e) for e in entries],
                "results": [asdict(r) for r in results],
                "dates": canonical_dates,
                "observations": observations,
            }, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

    return entries, results, canonical_dates, observations


# ─── Public API ───────────────────────────────────────────────────────────────


def pis_compliance_summary(repo_root: Path | str = ".") -> dict:
    """Summary cards for the Allocation Compliance Intelligence dashboard."""
    repo_root = Path(repo_root)
    _, results, canonical_dates, observations = _get_computed(repo_root)

    total = len(results)
    compliant_now = sum(1 for r in results if r.current_status == "COMPLIANT")
    warning_now = sum(1 for r in results if r.current_status == "WARNING")
    nc_now = sum(1 for r in results if r.current_status == "NON_COMPLIANT")

    highly = sum(1 for r in results if r.compliance_severity == "HIGHLY_COMPLIANT")
    mostly = sum(1 for r in results if r.compliance_severity == "MOSTLY_COMPLIANT")
    mixed = sum(1 for r in results if r.compliance_severity == "MIXED")
    persistent_nc = sum(1 for r in results if r.compliance_severity == "PERSISTENTLY_NON_COMPLIANT")

    top_violations = sorted(
        [r for r in results if r.compliance_severity == "PERSISTENTLY_NON_COMPLIANT"],
        key=lambda r: r.compliance_rate_pct,
    )[:5]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_nodes": total,
        "currently_compliant": compliant_now,
        "currently_warning": warning_now,
        "currently_non_compliant": nc_now,
        "dates_covered": len(canonical_dates),
        "highly_compliant_count": highly,
        "mostly_compliant_count": mostly,
        "mixed_count": mixed,
        "persistently_non_compliant_count": persistent_nc,
        "top_violations": [
            {
                "node_key": r.node_key,
                "node_label": r.node_label,
                "compliance_rate_pct": r.compliance_rate_pct,
                "non_compliance_rate_pct": r.non_compliance_rate_pct,
                "current_streak": r.current_streak,
                "current_status": r.current_status,
                "current_drift_pct": r.current_drift_pct,
            }
            for r in top_violations
        ],
        "observations": observations,
    }


def pis_compliance_latest(repo_root: Path | str = ".") -> dict:
    """Per-node latest compliance status with streaks and rates."""
    repo_root = Path(repo_root)
    _, results, canonical_dates, observations = _get_computed(repo_root)

    # Sort: NON_COMPLIANT first, then WARNING, then COMPLIANT; within each by rate ascending
    _status_order = {"NON_COMPLIANT": 0, "WARNING": 1, "COMPLIANT": 2}

    sorted_results = sorted(
        results,
        key=lambda r: (_status_order.get(r.current_status, 3), r.compliance_rate_pct),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_date": canonical_dates[-1] if canonical_dates else None,
        "dates_covered": len(canonical_dates),
        "nodes": [
            {
                "node_key": r.node_key,
                "node_label": r.node_label,
                "dimension_type": r.dimension_type,
                "dates_available": r.dates_available,
                "compliance_rate_pct": r.compliance_rate_pct,
                "non_compliance_rate_pct": r.non_compliance_rate_pct,
                "compliance_severity": r.compliance_severity,
                "current_status": r.current_status,
                "current_streak": r.current_streak,
                "longest_compliant_streak": r.longest_compliant_streak,
                "longest_non_compliant_streak": r.longest_non_compliant_streak,
                "current_drift_pct": r.current_drift_pct,
                "current_actual_pct": r.current_actual_pct,
                "current_target_pct": r.current_target_pct,
            }
            for r in sorted_results
        ],
        "observations": observations,
    }


def pis_compliance_history(repo_root: Path | str = ".") -> dict:
    """Full compliance timeline: every node × every canonical date."""
    repo_root = Path(repo_root)
    entries, _, canonical_dates, _ = _get_computed(repo_root)

    # Group entries by node_key
    by_node: dict[str, list[ComplianceEntry]] = defaultdict(list)
    for e in entries:
        by_node[e.node_key].append(e)

    nodes_payload = []
    for node_key in sorted(by_node):
        node_entries = sorted(by_node[node_key], key=lambda e: e.snapshot_date)
        nodes_payload.append({
            "node_key": node_key,
            "node_label": node_entries[0].node_label if node_entries else node_key,
            "entries": [
                {
                    "snapshot_date": e.snapshot_date,
                    "compliance_status": e.compliance_status,
                    "severity": e.severity,
                    "drift_pct": e.drift_pct,
                    "actual_pct": e.actual_pct,
                    "target_pct": e.target_pct,
                }
                for e in node_entries
            ],
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dates": canonical_dates,
        "nodes": nodes_payload,
    }
