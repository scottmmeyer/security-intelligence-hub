"""AI-004B — Allocation Policy Version Diff Visibility (Completion Phase).

Transforms raw policy diffs into operator-facing intelligence:
  - Policy change summaries with severity classification
  - Recommendation impact analysis
  - Before/after allocation views
  - Policy timeline with change metadata
  - Impact notifications

Reads from (read-only):
  - AI-004 existing policy_version_diff outputs (versions, diffs)
  - Latest PAR run recommendations for impact analysis

Writes (fully regeneratable):
  - data/history/pis/policy/policy_change_intelligence.json

Governance:
  - Read-only relative to ALL scoring, recommendation, and allocation engines.
  - No changes to allocation targets, CRA, ESS, CW-DAS, UCF, PAP, or governance rules.
  - Display-only / operator intelligence only.

Public API
----------
  policy_summary(repo_root)     → dict   (GET /api/pis/policy/summary)
  policy_impact(repo_root)      → dict   (GET /api/pis/policy/impact)
  policy_timeline(repo_root)    → dict   (GET /api/pis/policy/timeline)
  policy_version(vid, repo_root) → dict  (GET /api/pis/policy/version/<vid>)
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.pis.policy_version_diff import (
    pis_policy_current,
    pis_policy_diff,
    pis_policy_history,
)

# ── Constants ──────────────────────────────────────────────────────────────────

_AI004B_VERSION = "1.0"
_CACHE_FILE = "data/history/pis/policy/policy_change_intelligence.json"

# Severity thresholds
_SEVERITY_MINOR_NODES      = 1
_SEVERITY_MODERATE_NODES   = 3
_SEVERITY_MAJOR_NODES      = 6

_SEVERITY_MINOR_DELTA      = 1.0    # pp
_SEVERITY_MODERATE_DELTA   = 3.0    # pp
_SEVERITY_MAJOR_DELTA      = 6.0    # pp
_SEVERITY_STRUCTURAL_DELTA = 10.0   # pp

# High-importance nodes (changes to these escalate severity)
_HIGH_IMPORTANCE_NODES = frozenset({
    "EQUITIES.US.MID",
    "EQUITIES.INTERNATIONAL",
    "EQUITIES.US.LARGE",
    "EQUITIES.US.SMALL",
    "EQUITIES.EMERGING_MARKETS",
    "CASH",
})

_GOVERNANCE_NOTE = (
    "AI-004B is display-only. No allocation targets, recommendation algorithms, "
    "CRA, ESS, CW-DAS, UCF, or governance rules are modified. "
    "Policy change intelligence is derived from existing PAR artifacts and policy files."
)


# ── Part F: Severity classification ───────────────────────────────────────────

def _classify_severity(
    nodes_changed: int,
    max_abs_delta: float,
    high_importance_affected: bool,
) -> str:
    """Classify policy change severity: MINOR | MODERATE | MAJOR | STRUCTURAL."""
    if max_abs_delta >= _SEVERITY_STRUCTURAL_DELTA:
        return "STRUCTURAL"
    if max_abs_delta >= _SEVERITY_MAJOR_DELTA or nodes_changed >= _SEVERITY_MAJOR_NODES:
        return "MAJOR"
    if high_importance_affected and max_abs_delta >= _SEVERITY_MODERATE_DELTA:
        return "MAJOR"
    if max_abs_delta >= _SEVERITY_MODERATE_DELTA or nodes_changed >= _SEVERITY_MODERATE_NODES:
        return "MODERATE"
    if max_abs_delta >= _SEVERITY_MINOR_DELTA or nodes_changed >= _SEVERITY_MINOR_NODES:
        return "MINOR"
    return "MINOR"


def _severity_label(severity: str) -> str:
    return {
        "STRUCTURAL": "Structural realignment — fundamental portfolio strategy change",
        "MAJOR":      "Major change — significant allocation target shifts",
        "MODERATE":   "Moderate change — notable allocation adjustments",
        "MINOR":      "Minor change — small target refinements",
    }.get(severity, severity)


# ── Part A: Policy change summary ─────────────────────────────────────────────

def _build_change_summary(diff_payload: Dict, history_payload: Dict) -> List[Dict]:
    """Build a summary card for every policy version transition."""
    diffs   = diff_payload.get("diffs", [])
    versions = {v.get("fingerprint_id"): v for v in history_payload.get("versions", [])}

    summaries = []
    for d in diffs:
        changed_targets = d.get("changed_targets", [])
        added_nodes     = d.get("added_nodes", [])
        removed_nodes   = d.get("removed_nodes", [])

        all_changed_nodes = set(c.get("node_key", "") for c in changed_targets) | set(added_nodes) | set(removed_nodes)
        nodes_changed = len(all_changed_nodes)

        max_abs_delta = max(
            (abs(c.get("delta_pp", 0)) for c in changed_targets),
            default=0.0,
        )
        largest_change = max(
            changed_targets,
            key=lambda c: abs(c.get("delta_pp", 0)),
            default=None,
        )

        high_importance = bool(all_changed_nodes & _HIGH_IMPORTANCE_NODES)
        severity = _classify_severity(nodes_changed, max_abs_delta, high_importance)

        # Operator note
        note_parts = []
        if largest_change:
            lk = largest_change.get("node_key", "—")
            lf = largest_change.get("from_pct", 0)
            lt = largest_change.get("to_pct", 0)
            ld = largest_change.get("delta_pp", 0)
            note_parts.append(
                f"Largest shift: {lk} {lf:.1f}% → {lt:.1f}% ({ld:+.1f}pp)"
            )
        if added_nodes:
            note_parts.append(f"Added nodes: {', '.join(added_nodes[:3])}")
        if removed_nodes:
            note_parts.append(f"Removed nodes: {', '.join(removed_nodes[:3])}")

        summaries.append({
            "from_version_id": d.get("from_version_id"),
            "to_version_id":   d.get("to_version_id"),
            "from_date":       d.get("from_date"),
            "to_date":         d.get("to_date"),
            "nodes_changed":   nodes_changed,
            "max_abs_delta_pp": round(max_abs_delta, 4),
            "severity":        severity,
            "severity_label":  _severity_label(severity),
            "high_importance_nodes_affected": high_importance,
            "affected_nodes":  sorted(all_changed_nodes),
            "largest_change":  largest_change,
            "operator_note":   " | ".join(note_parts) if note_parts else "No significant changes.",
            "changed_targets": changed_targets,
            "added_nodes":     added_nodes,
            "removed_nodes":   removed_nodes,
        })

    return summaries


# ── Part B: Recommendation impact analysis ────────────────────────────────────

def _load_latest_recommendations(repo_root: Path) -> List[Dict]:
    """Load recommendations from the latest PAR run."""
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return []
    dirs = sorted(
        (d for d in par_dir.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
    )
    if not dirs:
        return []
    rec_path = dirs[-1] / "recommendations.json"
    if not rec_path.exists():
        return []
    try:
        data = json.loads(rec_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("recommendations", [])
    except (OSError, json.JSONDecodeError):
        return []


def _compute_recommendation_impact(
    recommendations: List[Dict],
    recent_change_summary: Optional[Dict],
) -> Dict:
    """Determine which recommendations align with recent policy changes."""
    if not recent_change_summary or not recommendations:
        return {"total": len(recommendations), "policy_impacted": [], "impact_count": 0, "impact_summary": "No policy changes detected."}

    affected_nodes = set(recent_change_summary.get("affected_nodes", []))
    increased_nodes = {
        c.get("node_key") for c in recent_change_summary.get("changed_targets", [])
        if c.get("delta_pp", 0) > 0
    }
    decreased_nodes = {
        c.get("node_key") for c in recent_change_summary.get("changed_targets", [])
        if c.get("delta_pp", 0) < 0
    }

    impacted: List[Dict] = []
    for rec in recommendations:
        rec_type = rec.get("recommendation_type", "")
        affected_syms = rec.get("affected_symbols", [])
        drilldown = rec.get("drilldown", {})
        drift_pct = rec.get("drift_pct")
        node_key = rec.get("affected_node_key") or (drilldown.get("affected_node_key") if drilldown else None)

        if not node_key:
            continue

        # Determine if this recommendation's node was affected by policy change
        if node_key not in affected_nodes:
            # Try partial match (e.g. EQUITIES.US.MID matches EQUITIES.US.MID.*)
            partial = any(node_key.startswith(n) or n.startswith(node_key) for n in affected_nodes)
            if not partial:
                continue

        # Classify impact
        if node_key in increased_nodes:
            impact_type = "TARGET_INCREASED"
            impact_note = f"Target for {node_key} was increased — this recommendation may reflect the new higher target."
        elif node_key in decreased_nodes:
            impact_type = "TARGET_DECREASED"
            impact_note = f"Target for {node_key} was decreased — this recommendation may reflect the new lower target."
        else:
            impact_type = "NODE_RESTRUCTURED"
            impact_note = f"{node_key} was added or removed in the policy change."

        impacted.append({
            "recommendation_type": rec_type,
            "node_key":            node_key,
            "affected_symbols":    affected_syms[:5],
            "impact_type":         impact_type,
            "impact_note":         impact_note,
            "drift_pct":           drift_pct,
            "title":               rec.get("title", ""),
        })

    severity = recent_change_summary.get("severity", "MINOR")
    if impacted:
        summary = (
            f"{len(impacted)} recommendation(s) are aligned with the recent {severity} policy change "
            f"({recent_change_summary.get('nodes_changed', 0)} node(s) modified). "
            f"These recommendations reflect the updated allocation targets."
        )
    else:
        summary = (
            f"No recommendations directly reference the recently changed nodes. "
            f"The policy change ({severity}) may not yet be reflected in current recommendations."
        )

    return {
        "total":           len(recommendations),
        "policy_impacted": impacted,
        "impact_count":    len(impacted),
        "impact_summary":  summary,
    }


# ── Part C: Before/after allocation view ──────────────────────────────────────

def _build_before_after(
    change_summary: Optional[Dict],
    current_payload: Dict,
) -> List[Dict]:
    """Build a before/after comparison for every changed node."""
    if not change_summary:
        return []

    changed_targets = change_summary.get("changed_targets", [])
    rows = []
    for c in sorted(changed_targets, key=lambda x: abs(x.get("delta_pp", 0)), reverse=True):
        nk = c.get("node_key", "—")
        rows.append({
            "node_key":         nk,
            "previous_pct":     c.get("from_pct", 0),
            "current_pct":      c.get("to_pct", 0),
            "delta_pp":         c.get("delta_pp", 0),
            "change_direction": c.get("change_direction", "—"),
            "is_high_importance": nk in _HIGH_IMPORTANCE_NODES,
        })
    return rows


# ── Part D: Policy timeline ───────────────────────────────────────────────────

def _build_timeline(
    history_payload: Dict,
    change_summaries: List[Dict],
) -> List[Dict]:
    """Build a timeline entry per policy version."""
    versions    = history_payload.get("versions", [])
    summary_by_to = {s.get("to_version_id"): s for s in change_summaries}

    timeline = []
    for v in versions:
        fid = v.get("fingerprint_id", "")
        change_s = summary_by_to.get(fid)
        timeline.append({
            "fingerprint_id":   fid,
            "recalculation_id": v.get("recalculation_id", ""),
            "first_seen_date":  v.get("first_seen_date", ""),
            "last_seen_date":   v.get("last_seen_date", ""),
            "run_count":        v.get("run_count", 0),
            "node_count":       v.get("node_count", 0),
            "nodes_changed":    change_s.get("nodes_changed", 0) if change_s else 0,
            "severity":         change_s.get("severity", "—") if change_s else "INITIAL",
            "operator_note":    change_s.get("operator_note", "Initial policy version.") if change_s else "Initial policy version.",
        })

    return sorted(timeline, key=lambda x: str(x.get("first_seen_date", "")), reverse=True)


# ── Part E: Impact notifications ─────────────────────────────────────────────

def _build_notifications(
    change_summaries: List[Dict],
    rec_impact: Dict,
    current_payload: Dict,
) -> List[Dict]:
    """Build operator notification cards for recent policy changes."""
    notifications = []

    # Most recent change notification
    if change_summaries:
        recent = change_summaries[-1]
        notifications.append({
            "type":     "RECENT_CHANGE",
            "severity": recent.get("severity", "MINOR"),
            "title":    f"Policy Updated — {recent.get('severity', 'MINOR')} Change",
            "body":     recent.get("operator_note", ""),
            "date":     recent.get("to_date", ""),
            "nodes_changed": recent.get("nodes_changed", 0),
        })

    # Recommendations impacted
    if rec_impact.get("impact_count", 0) > 0:
        notifications.append({
            "type":     "RECOMMENDATION_IMPACT",
            "severity": "INFO",
            "title":    f"{rec_impact['impact_count']} Recommendation(s) Reflect Policy Change",
            "body":     rec_impact.get("impact_summary", ""),
            "date":     "",
            "nodes_changed": 0,
        })

    # High-importance node affected
    if change_summaries and change_summaries[-1].get("high_importance_nodes_affected"):
        affected_hi = [
            n for n in change_summaries[-1].get("affected_nodes", [])
            if n in _HIGH_IMPORTANCE_NODES
        ]
        if affected_hi:
            notifications.append({
                "type":     "HIGH_IMPORTANCE_NODE",
                "severity": "WARN",
                "title":    "High-Importance Allocation Node Modified",
                "body":     f"The following core allocation nodes were modified: {', '.join(affected_hi[:3])}. These nodes are central to portfolio strategy.",
                "date":     change_summaries[-1].get("to_date", ""),
                "nodes_changed": len(affected_hi),
            })

    # Stable policy notification
    if not change_summaries:
        notifications.append({
            "type":     "STABLE",
            "severity": "OK",
            "title":    "Policy Stable",
            "body":     "No allocation policy changes detected across the observed analysis run history. A single policy version has been consistently applied.",
            "date":     current_payload.get("last_seen_date", ""),
            "nodes_changed": 0,
        })

    return notifications


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _cache_path(repo_root: Path) -> Path:
    return repo_root / _CACHE_FILE


def _load_cache(repo_root: Path) -> Optional[Dict]:
    path = _cache_path(repo_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save_cache(repo_root: Path, payload: Dict) -> None:
    path = _cache_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def _build_intelligence(repo_root: Path) -> Dict:
    """Compute full AI-004B intelligence payload."""
    current = pis_policy_current(repo_root)
    history = pis_policy_history(repo_root)
    diff    = pis_policy_diff(repo_root)
    recs    = _load_latest_recommendations(repo_root)

    change_summaries = _build_change_summary(diff, history)
    recent_change    = change_summaries[-1] if change_summaries else None
    rec_impact       = _compute_recommendation_impact(recs, recent_change)
    before_after     = _build_before_after(recent_change, current)
    timeline         = _build_timeline(history, change_summaries)
    notifications    = _build_notifications(change_summaries, rec_impact, current)

    payload = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "version":          _AI004B_VERSION,
        "policy_id":        current.get("policy_id"),
        "current_version":  current.get("fingerprint_id"),
        "change_count":     len(change_summaries),
        "has_changes":      len(change_summaries) > 0,
        "current_severity": recent_change.get("severity") if recent_change else "STABLE",
        "change_summaries": change_summaries,
        "before_after":     before_after,
        "timeline":         timeline,
        "rec_impact":       rec_impact,
        "notifications":    notifications,
        "governance_note":  _GOVERNANCE_NOTE,
        # Pass-through for convenience
        "current_policy":   current,
    }
    return payload


def _get_intelligence(repo_root: Path, force: bool = False) -> Dict:
    if not force:
        cached = _load_cache(repo_root)
        if cached:
            return cached
    payload = _build_intelligence(repo_root)
    _save_cache(repo_root, payload)
    return payload


# ── Public API ─────────────────────────────────────────────────────────────────

def policy_summary(repo_root: Path | str = ".") -> Dict:
    """Part A/E: Policy change summaries and impact notifications.

    Returns:
        { change_count, current_severity, has_changes,
          change_summaries: [...], notifications: [...], governance_note }
    """
    root = Path(repo_root)
    data = _get_intelligence(root)
    return {
        "generated_at":     data["generated_at"],
        "policy_id":        data["policy_id"],
        "current_version":  data["current_version"],
        "change_count":     data["change_count"],
        "has_changes":      data["has_changes"],
        "current_severity": data["current_severity"],
        "change_summaries": data["change_summaries"],
        "notifications":    data["notifications"],
        "governance_note":  data["governance_note"],
    }


def policy_impact(repo_root: Path | str = ".") -> Dict:
    """Part B/C: Recommendation impact + before/after allocation view.

    Returns:
        { rec_impact: {...}, before_after: [...] }
    """
    root = Path(repo_root)
    data = _get_intelligence(root)
    return {
        "generated_at": data["generated_at"],
        "rec_impact":   data["rec_impact"],
        "before_after": data["before_after"],
        "has_changes":  data["has_changes"],
        "governance_note": data["governance_note"],
    }


def policy_timeline(repo_root: Path | str = ".") -> Dict:
    """Part D: Policy version timeline.

    Returns:
        { timeline: [{ fingerprint_id, dates, run_count, severity, nodes_changed }] }
    """
    root = Path(repo_root)
    data = _get_intelligence(root)
    return {
        "generated_at": data["generated_at"],
        "timeline":     data["timeline"],
        "change_count": data["change_count"],
    }


def policy_version(version_id: str, repo_root: Path | str = ".") -> Dict:
    """Return full detail for a specific policy version."""
    root = Path(repo_root)
    data = _get_intelligence(root)
    vid = version_id.strip()

    # Check change summaries
    for s in data.get("change_summaries", []):
        if s.get("to_version_id") == vid or s.get("from_version_id") == vid:
            return {"version_id": vid, "summary": s, "generated_at": data["generated_at"]}

    # Check timeline
    for t in data.get("timeline", []):
        if t.get("fingerprint_id") == vid:
            return {"version_id": vid, "timeline_entry": t, "generated_at": data["generated_at"]}

    return {"version_id": vid, "error": "Version not found.", "generated_at": data["generated_at"]}
