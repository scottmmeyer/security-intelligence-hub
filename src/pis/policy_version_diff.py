"""AI-004 — Allocation Policy Version Diff Engine.

Governance visibility into allocation policy versions and changes.

Reads existing PAR alignment.csv artifacts and config/allocation_policy.yaml
to reconstruct the policy version history.  Computes diffs between consecutive
policy versions and produces governance observations.

Architectural constraint: this module reads SIH policy outputs and PAR artifacts.
It NEVER modifies any policy file, allocation target, CRA, DIL, or UCF.

SIH decides.  PIS observes.

Read from:
  - data/portfolio_ingestion/analysis_runs/*/alignment.csv (target_pct per node)
  - data/portfolio_ingestion/analysis_runs/*/run_metadata.json (recalculation_id)
  - config/allocation_policy.yaml
  - config/allocation_methodology.yaml

Write to:
  - data/history/pis/policy/  (derived governance artifacts, fully regeneratable)

Public API
----------
  pis_policy_current(repo_root)  → dict   (current policy snapshot)
  pis_policy_history(repo_root)  → dict   (version timeline)
  pis_policy_diff(repo_root)     → dict   (diff between consecutive versions)
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

# ─── Constants ────────────────────────────────────────────────────────────────

_NOISE_THRESHOLD = 0.001    # delta_pp below this = treated as UNCHANGED
_MAX_OBSERVATIONS = 6
_CACHE_FILENAME = "policy_cache.json"

# ─── Data models ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TargetChange:
    node_key: str
    from_pct: float
    to_pct: float
    delta_pp: float
    change_direction: str   # INCREASED | DECREASED | ADDED | REMOVED


@dataclass(frozen=True)
class PolicyVersion:
    fingerprint_id: str
    recalculation_id: str
    first_seen_date: str
    last_seen_date: str
    run_count: int
    node_count: int
    node_targets: dict       # {node_key: float}
    tactical_targets: dict   # {node_key: float}
    created_at: str


@dataclass(frozen=True)
class PolicyDiff:
    from_version_id: str
    to_version_id: str
    from_date: str
    to_date: str
    added_nodes: tuple
    removed_nodes: tuple
    changed_targets: tuple   # tuple[TargetChange]
    total_changes: int
    summary: str


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


def _load_yaml_safe(path: Path) -> dict:
    if not path.exists() or not _YAML_AVAILABLE:
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _content_hash(node_targets: dict) -> str:
    target_str = json.dumps(sorted(node_targets.items()), sort_keys=True)
    return hashlib.sha256(target_str.encode("utf-8")).hexdigest()[:8]


# ─── Step 1 — Collect policy snapshots from PAR history ──────────────────────


def _collect_policy_snapshots(repo_root: Path) -> list[dict]:
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    if not par_dir.exists():
        return []

    by_date: dict[str, tuple[str, Path, Path]] = {}
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
            by_date[snap_date] = (created_at, meta_file, align_file)

    snapshots = []
    for snap_date in sorted(by_date):
        created_at, meta_file, align_file = by_date[snap_date]
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        recalc_id = str(meta.get("recalculation_id", "") or "UNKNOWN")
        rows = _read_csv(align_file)
        node_targets: dict[str, float] = {}
        tactical_targets: dict[str, float] = {}
        for r in rows:
            nk = str(r.get("node_key", "") or "").strip()
            if not nk:
                continue
            node_targets[nk] = _safe_float(r.get("target_pct"))
            tactical_targets[nk] = _safe_float(r.get("tactical_target_pct"))

        snapshots.append({
            "snapshot_date": snap_date,
            "recalculation_id": recalc_id,
            "created_at": created_at,
            "node_targets": node_targets,
            "tactical_targets": tactical_targets,
        })
    return snapshots


# ─── Step 2 — Build policy version registry ───────────────────────────────────


def _build_versions(snapshots: list[dict]) -> list[PolicyVersion]:
    by_recalc: dict[str, list[dict]] = defaultdict(list)
    for s in snapshots:
        by_recalc[s["recalculation_id"]].append(s)

    versions: list[PolicyVersion] = []
    # Sort by first appearance date
    for rid in sorted(by_recalc, key=lambda r: by_recalc[r][0]["snapshot_date"]):
        snaps = sorted(by_recalc[rid], key=lambda s: s["snapshot_date"])
        first = snaps[0]
        last = snaps[-1]

        # Use most recent snapshot's targets as canonical for this version
        node_targets = last["node_targets"]
        tactical_targets = last["tactical_targets"]

        fingerprint_id = f"{rid}:{_content_hash(node_targets)}"

        versions.append(PolicyVersion(
            fingerprint_id=fingerprint_id,
            recalculation_id=rid,
            first_seen_date=first["snapshot_date"],
            last_seen_date=last["snapshot_date"],
            run_count=len(snaps),
            node_count=len(node_targets),
            node_targets=node_targets,
            tactical_targets=tactical_targets,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
    return versions


# ─── Step 3 — Load current policy config ──────────────────────────────────────


def _load_current_policy_config(repo_root: Path) -> dict:
    policy_file = repo_root / "config" / "allocation_policy.yaml"
    methodology_file = repo_root / "config" / "allocation_methodology.yaml"

    result: dict = {
        "policy_id": "UNKNOWN",
        "effective_date": "",
        "methodology_id": "UNKNOWN",
        "structural_policy": {},
        "recalculation_governance": {},
        "methodology_baselines": {},
        "config_hash": "",
    }

    if policy_file.exists():
        content = policy_file.read_bytes()
        result["config_hash"] = hashlib.sha256(content).hexdigest()[:12]
        policy = _load_yaml_safe(policy_file)
        result["policy_id"] = str(policy.get("policy_id", "") or "")
        result["effective_date"] = str(policy.get("effective_date", "") or "")
        result["structural_policy"] = dict(policy.get("structural_policy") or {})
        result["recalculation_governance"] = dict(policy.get("recalculation_governance") or {})

    if methodology_file.exists():
        method = _load_yaml_safe(methodology_file)
        result["methodology_id"] = str(method.get("methodology_id", "") or "")
        for node in method.get("nodes", []) or []:
            nk = str(node.get("key", "") or "")
            if nk:
                result["methodology_baselines"][nk] = _safe_float(node.get("baseline_target_pct_of_parent"))

    return result


# ─── Step 4 — Compute diff between two versions ───────────────────────────────


def _compute_diff(v_from: PolicyVersion, v_to: PolicyVersion) -> PolicyDiff:
    keys_from = set(v_from.node_targets)
    keys_to = set(v_to.node_targets)

    added = sorted(keys_to - keys_from)
    removed = sorted(keys_from - keys_to)
    changed: list[TargetChange] = []

    for node_key in sorted(keys_from & keys_to):
        fp = v_from.node_targets[node_key]
        tp = v_to.node_targets[node_key]
        delta = round(tp - fp, 4)
        if abs(delta) > _NOISE_THRESHOLD:
            changed.append(TargetChange(
                node_key=node_key,
                from_pct=fp,
                to_pct=tp,
                delta_pp=delta,
                change_direction="INCREASED" if delta > 0 else "DECREASED",
            ))

    for nk in added:
        changed.append(TargetChange(
            node_key=nk,
            from_pct=0.0,
            to_pct=v_to.node_targets[nk],
            delta_pp=v_to.node_targets[nk],
            change_direction="ADDED",
        ))
    for nk in removed:
        changed.append(TargetChange(
            node_key=nk,
            from_pct=v_from.node_targets[nk],
            to_pct=0.0,
            delta_pp=-v_from.node_targets[nk],
            change_direction="REMOVED",
        ))

    # Sort by abs delta descending
    changed_sorted = tuple(sorted(changed, key=lambda c: abs(c.delta_pp), reverse=True))

    modified_count = len([c for c in changed if c.change_direction not in ("ADDED", "REMOVED")])
    total = len(added) + len(removed) + modified_count

    if total == 0:
        summary = (
            f"No allocation target changes between "
            f"{v_from.recalculation_id[:20]} and {v_to.recalculation_id[:20]}."
        )
    else:
        summary = (
            f"{total} allocation target change{'s' if total != 1 else ''}: "
            f"{len(added)} added, {len(removed)} removed, {modified_count} modified."
        )

    return PolicyDiff(
        from_version_id=v_from.fingerprint_id,
        to_version_id=v_to.fingerprint_id,
        from_date=v_from.last_seen_date,
        to_date=v_to.last_seen_date,
        added_nodes=tuple(added),
        removed_nodes=tuple(removed),
        changed_targets=changed_sorted,
        total_changes=total,
        summary=summary,
    )


# ─── Step 5 — Governance observations ────────────────────────────────────────


def _generate_observations(
    versions: list[PolicyVersion],
    diffs: list[PolicyDiff],
    current_config: dict,
) -> list[str]:
    obs: list[str] = []

    pid = current_config.get("policy_id", "")
    eff = current_config.get("effective_date", "")
    mid = current_config.get("methodology_id", "")
    obs.append(
        f"Policy {pid or 'UNKNOWN'} is active"
        + (f" (effective {eff})" if eff else "")
        + (f". Methodology: {mid}." if mid else ".")
    )

    if len(versions) == 1:
        v = versions[0]
        obs.append(
            f"A single policy version ({v.recalculation_id[:24]}) has been in effect "
            f"across all {v.run_count} observed analysis runs "
            f"({v.first_seen_date} to {v.last_seen_date})."
        )
    elif len(versions) > 1:
        obs.append(
            f"{len(versions)} distinct policy versions detected across "
            f"{sum(v.run_count for v in versions)} analysis runs."
        )

    for diff in diffs:
        if diff.total_changes > 0:
            obs.append(f"Policy change detected: {diff.summary}")

    sp = current_config.get("structural_policy", {})
    if sp:
        obs.append(
            f"Active constraints: "
            f"cash floor {sp.get('cash_floor_pct', '?')}%, "
            f"max mega-cap {sp.get('max_mega_concentration_pct', '?')}%, "
            f"min international {sp.get('min_international_pct', '?')}%."
        )

    return obs[:_MAX_OBSERVATIONS]


# ─── Cache ────────────────────────────────────────────────────────────────────


def _cache_path(repo_root: Path) -> Path:
    return repo_root / "data" / "history" / "pis" / "policy" / _CACHE_FILENAME


def _cache_is_valid(cache: Path, repo_root: Path) -> bool:
    if not cache.exists():
        return False
    try:
        cache_mtime = cache.stat().st_mtime
    except OSError:
        return False
    watch = [
        repo_root / "config" / "allocation_policy.yaml",
        repo_root / "config" / "allocation_methodology.yaml",
    ]
    for wp in watch:
        try:
            if wp.exists() and wp.stat().st_mtime > cache_mtime:
                return False
        except OSError:
            continue
    return True


def _get_computed(repo_root: Path) -> tuple[
    list[PolicyVersion], list[PolicyDiff], dict, list[str]
]:
    cache = _cache_path(repo_root)
    if _cache_is_valid(cache, repo_root):
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            versions = [PolicyVersion(**v) for v in cached.get("versions", [])]
            diffs = [PolicyDiff(**d) for d in cached.get("diffs", [])]
            current_config = cached.get("current_config", {})
            observations = cached.get("observations", [])
            return versions, diffs, current_config, observations
        except Exception:
            pass

    snapshots = _collect_policy_snapshots(repo_root)
    versions = _build_versions(snapshots)
    current_config = _load_current_policy_config(repo_root)

    # Compute diffs between consecutive versions
    diffs: list[PolicyDiff] = []
    for i in range(1, len(versions)):
        diffs.append(_compute_diff(versions[i - 1], versions[i]))

    observations = _generate_observations(versions, diffs, current_config)

    # Write cache
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps({
                "versions": [asdict(v) for v in versions],
                "diffs": [asdict(d) for d in diffs],
                "current_config": current_config,
                "observations": observations,
            }, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass

    return versions, diffs, current_config, observations


# ─── Public API ───────────────────────────────────────────────────────────────


def pis_policy_current(repo_root: Path | str = ".") -> dict:
    """Current policy snapshot: active version fingerprint + structural constraints."""
    repo_root = Path(repo_root)
    versions, diffs, current_config, observations = _get_computed(repo_root)

    current_version = versions[-1] if versions else None
    node_targets = dict(current_version.node_targets) if current_version else {}
    tactical_targets = dict(current_version.tactical_targets) if current_version else {}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy_id": current_config.get("policy_id", ""),
        "methodology_id": current_config.get("methodology_id", ""),
        "effective_date": current_config.get("effective_date", ""),
        "config_hash": current_config.get("config_hash", ""),
        "recalculation_id": current_version.recalculation_id if current_version else "",
        "fingerprint_id": current_version.fingerprint_id if current_version else "",
        "run_count": current_version.run_count if current_version else 0,
        "node_count": current_version.node_count if current_version else 0,
        "first_seen_date": current_version.first_seen_date if current_version else "",
        "last_seen_date": current_version.last_seen_date if current_version else "",
        "structural_policy": current_config.get("structural_policy", {}),
        "recalculation_governance": current_config.get("recalculation_governance", {}),
        "node_targets": node_targets,
        "tactical_targets": tactical_targets,
        "observations": observations,
    }


def pis_policy_history(repo_root: Path | str = ".") -> dict:
    """All distinct policy versions seen in PAR history."""
    repo_root = Path(repo_root)
    versions, diffs, current_config, observations = _get_computed(repo_root)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version_count": len(versions),
        "versions": [
            {
                "fingerprint_id": v.fingerprint_id,
                "recalculation_id": v.recalculation_id,
                "first_seen_date": v.first_seen_date,
                "last_seen_date": v.last_seen_date,
                "run_count": v.run_count,
                "node_count": v.node_count,
            }
            for v in versions
        ],
        "observations": observations,
    }


def pis_policy_diff(repo_root: Path | str = ".") -> dict:
    """Diff between consecutive policy versions. Governance change log."""
    repo_root = Path(repo_root)
    versions, diffs, current_config, observations = _get_computed(repo_root)

    has_changes = any(d.total_changes > 0 for d in diffs)

    def _diff_dict(d: PolicyDiff) -> dict:
        return {
            "from_version_id": d.from_version_id,
            "to_version_id": d.to_version_id,
            "from_date": d.from_date,
            "to_date": d.to_date,
            "added_nodes": list(d.added_nodes),
            "removed_nodes": list(d.removed_nodes),
            "changed_targets": [
                {
                    "node_key": c.node_key,
                    "from_pct": c.from_pct,
                    "to_pct": c.to_pct,
                    "delta_pp": c.delta_pp,
                    "change_direction": c.change_direction,
                }
                for c in d.changed_targets
            ],
            "total_changes": d.total_changes,
            "summary": d.summary,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "versions_compared": len(versions),
        "has_changes": has_changes,
        "diffs": [_diff_dict(d) for d in diffs],
        "current_version": {
            "fingerprint_id": versions[-1].fingerprint_id if versions else "",
            "recalculation_id": versions[-1].recalculation_id if versions else "",
            "last_seen_date": versions[-1].last_seen_date if versions else "",
            "node_count": versions[-1].node_count if versions else 0,
        },
        "observations": observations,
    }
