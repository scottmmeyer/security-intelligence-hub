# AI-004 — Algorithm Specification: Allocation Policy Version Diff Engine

**Date:** 2026-06-15

---

## 1. Module Entry Point

**File:** `src/pis/policy_version_diff.py`

**Public API:**
```python
def pis_policy_current(repo_root: Path | str = ".") -> dict
def pis_policy_history(repo_root: Path | str = ".") -> dict
def pis_policy_diff(repo_root: Path | str = ".") -> dict
```

---

## 2. Data Models

```python
@dataclass(frozen=True)
class TargetChange:
    node_key: str
    from_pct: float       # may be 0.0 if node was absent in prior version
    to_pct: float
    delta_pp: float       # to_pct - from_pct
    change_direction: str  # INCREASED | DECREASED | ADDED | REMOVED | UNCHANGED

@dataclass(frozen=True)
class PolicyVersion:
    fingerprint_id: str       # "{recalculation_id}:{content_hash[:8]}"
    recalculation_id: str
    first_seen_date: str      # earliest PAR date with this recalculation_id
    last_seen_date: str       # most recent PAR date with this recalculation_id
    run_count: int
    node_count: int
    node_targets: dict        # {node_key: target_pct}
    tactical_targets: dict    # {node_key: tactical_target_pct}
    created_at: str

@dataclass(frozen=True)
class PolicyDiff:
    from_version_id: str
    to_version_id: str
    from_date: str
    to_date: str
    added_nodes: tuple[str, ...]
    removed_nodes: tuple[str, ...]
    changed_targets: tuple[TargetChange, ...]
    total_changes: int
    summary: str
```

---

## 3. Step 1 — Collect PAR Policy Snapshots

```python
def _collect_policy_snapshots(repo_root: Path) -> list[dict]:
    """
    For each canonical PAR date, extract the recalculation_id and target_pct per node.
    
    Canonical selection: for each snapshot_date, retain the PAR with latest created_at_utc.
    """
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    by_date: dict[str, tuple[str, Path, Path]] = {}  # date → (created_at, meta_path, align_path)

    for par_path in par_dir.iterdir():
        if not par_path.is_dir(): continue
        meta_file = par_path / "run_metadata.json"
        align_file = par_path / "alignment.csv"
        if not meta_file.exists() or not align_file.exists(): continue

        meta = json.loads(meta_file.read_text())
        snap_date = str(meta.get("snapshot_date", ""))[:10]
        created_at = str(meta.get("created_at_utc", ""))
        if len(snap_date) != 10: continue
        try: date.fromisoformat(snap_date)
        except ValueError: continue

        if snap_date not in by_date or created_at > by_date[snap_date][0]:
            by_date[snap_date] = (created_at, meta_file, align_file)

    snapshots = []
    for snap_date in sorted(by_date):
        _, meta_file, align_file = by_date[snap_date]
        meta = json.loads(meta_file.read_text())
        recalc_id = str(meta.get("recalculation_id", "") or "UNKNOWN")

        rows = list(csv.DictReader(align_file.open()))
        node_targets = {}
        tactical_targets = {}
        for r in rows:
            nk = str(r.get("node_key", "")).strip()
            if not nk: continue
            node_targets[nk] = _safe_float(r.get("target_pct"))
            tactical_targets[nk] = _safe_float(r.get("tactical_target_pct"))

        snapshots.append({
            "snapshot_date": snap_date,
            "recalculation_id": recalc_id,
            "created_at": _,  # will use created_at from by_date
            "node_targets": node_targets,
            "tactical_targets": tactical_targets,
        })
    return snapshots
```

---

## 4. Step 2 — Build Policy Version Registry

Group snapshots by `recalculation_id`. Each distinct recalculation_id is a policy version.

```python
def _build_versions(snapshots: list[dict]) -> list[PolicyVersion]:
    by_recalc: dict[str, list[dict]] = {}
    for s in snapshots:
        rid = s["recalculation_id"]
        by_recalc.setdefault(rid, []).append(s)

    versions = []
    for rid in sorted(by_recalc, key=lambda r: by_recalc[r][0]["snapshot_date"]):
        snaps = sorted(by_recalc[rid], key=lambda s: s["snapshot_date"])
        first = snaps[0]; last = snaps[-1]

        # Use the last snapshot's targets as canonical (most recent = authoritative)
        node_targets = last["node_targets"]
        tactical_targets = last["tactical_targets"]

        # Content fingerprint from target state
        target_str = json.dumps(sorted(node_targets.items()), sort_keys=True)
        content_hash = hashlib.sha256(target_str.encode()).hexdigest()[:8]
        fingerprint_id = f"{rid}:{content_hash}"

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
```

---

## 5. Step 3 — Load Current Policy Config State

```python
def _load_current_policy_config(repo_root: Path) -> dict:
    policy_file = repo_root / "config" / "allocation_policy.yaml"
    methodology_file = repo_root / "config" / "allocation_methodology.yaml"

    result = {
        "policy_id": "UNKNOWN",
        "effective_date": "",
        "methodology_id": "UNKNOWN",
        "structural_policy": {},
        "recalculation_governance": {},
        "methodology_baselines": {},  # {node_key: baseline_target_pct_of_parent}
        "config_hash": "",
    }

    if policy_file.exists():
        content = policy_file.read_bytes()
        result["config_hash"] = hashlib.sha256(content).hexdigest()[:12]
        policy = yaml.safe_load(policy_file.read_text())
        result["policy_id"] = str(policy.get("policy_id", ""))
        result["effective_date"] = str(policy.get("effective_date", ""))
        result["structural_policy"] = policy.get("structural_policy", {}) or {}
        result["recalculation_governance"] = policy.get("recalculation_governance", {}) or {}

    if methodology_file.exists():
        method = yaml.safe_load(methodology_file.read_text())
        result["methodology_id"] = str(method.get("methodology_id", ""))
        for node in method.get("nodes", []):
            nk = str(node.get("key", ""))
            if nk:
                result["methodology_baselines"][nk] = node.get("baseline_target_pct_of_parent", 0.0)

    return result
```

---

## 6. Step 4 — Compute Policy Diff

```python
def _compute_diff(v_from: PolicyVersion, v_to: PolicyVersion) -> PolicyDiff:
    keys_from = set(v_from.node_targets)
    keys_to   = set(v_to.node_targets)

    added   = sorted(keys_to - keys_from)
    removed = sorted(keys_from - keys_to)

    changed: list[TargetChange] = []
    for node_key in sorted(keys_from & keys_to):
        from_pct = v_from.node_targets[node_key]
        to_pct   = v_to.node_targets[node_key]
        delta    = round(to_pct - from_pct, 4)
        if abs(delta) > 0.001:  # ignore floating-point noise
            direction = "INCREASED" if delta > 0 else "DECREASED"
            changed.append(TargetChange(
                node_key=node_key,
                from_pct=from_pct,
                to_pct=to_pct,
                delta_pp=delta,
                change_direction=direction,
            ))

    for node_key in added:
        changed.append(TargetChange(
            node_key=node_key,
            from_pct=0.0,
            to_pct=v_to.node_targets[node_key],
            delta_pp=v_to.node_targets[node_key],
            change_direction="ADDED",
        ))

    for node_key in removed:
        changed.append(TargetChange(
            node_key=node_key,
            from_pct=v_from.node_targets[node_key],
            to_pct=0.0,
            delta_pp=-v_from.node_targets[node_key],
            change_direction="REMOVED",
        ))

    total = len(added) + len(removed) + len([c for c in changed if c.change_direction not in ("ADDED","REMOVED")])

    if total == 0:
        summary = f"No allocation target changes detected between {v_from.recalculation_id} and {v_to.recalculation_id}."
    else:
        summary = (
            f"{total} allocation target change{'s' if total > 1 else ''} detected: "
            f"{len(added)} added, {len(removed)} removed, "
            f"{len([c for c in changed if c.change_direction not in ('ADDED','REMOVED')])} modified."
        )

    return PolicyDiff(
        from_version_id=v_from.fingerprint_id,
        to_version_id=v_to.fingerprint_id,
        from_date=v_from.last_seen_date,
        to_date=v_to.last_seen_date,
        added_nodes=tuple(added),
        removed_nodes=tuple(removed),
        changed_targets=tuple(sorted(changed, key=lambda c: abs(c.delta_pp), reverse=True)),
        total_changes=total,
        summary=summary,
    )
```

---

## 7. Step 5 — Governance Observations

```python
def _generate_policy_observations(
    versions: list[PolicyVersion],
    diffs: list[PolicyDiff],
    current_config: dict,
) -> list[str]:
    obs = []

    obs.append(
        f"Policy version {current_config['policy_id']} is active "
        f"(effective {current_config['effective_date'] or 'unknown'}). "
        f"Methodology: {current_config['methodology_id']}."
    )

    if len(versions) == 1:
        v = versions[0]
        obs.append(
            f"A single policy version has been in effect across all {v.run_count} "
            f"observed analysis runs ({v.first_seen_date} to {v.last_seen_date})."
        )
    elif len(versions) > 1:
        obs.append(
            f"{len(versions)} distinct policy versions detected across "
            f"{sum(v.run_count for v in versions)} analysis runs."
        )

    for diff in diffs:
        if diff.total_changes > 0:
            obs.append(
                f"Policy transition {diff.from_version_id[:20]} → {diff.to_version_id[:20]}: "
                f"{diff.summary}"
            )

    # Structural constraint summary
    sp = current_config.get("structural_policy", {})
    if sp:
        obs.append(
            f"Active structural constraints: "
            f"cash floor {sp.get('cash_floor_pct',0)}%, "
            f"max mega {sp.get('max_mega_concentration_pct',0)}%, "
            f"min international {sp.get('min_international_pct',0)}%."
        )

    return obs[:6]
```

---

## 8. API Payload Contracts

### GET /api/pis/policy/current

```json
{
  "generated_at": "ISO timestamp",
  "policy_id": "ALLOCATION_POLICY_V1",
  "methodology_id": "v1_2026_05",
  "effective_date": "2026-05-20",
  "config_hash": "8f7195b655f3",
  "recalculation_id": "SEED_20260520_D9E58D7F",
  "run_count": 19,
  "node_count": 39,
  "structural_policy": {
    "cash_floor_pct": 2.0,
    "max_mega_concentration_pct": 50.0,
    "min_international_pct": 10.0
  },
  "node_targets": {"EQUITIES": 88.0, "CASH": 5.0, "...": "..."},
  "observations": ["..."]
}
```

### GET /api/pis/policy/history

```json
{
  "generated_at": "ISO timestamp",
  "version_count": 1,
  "versions": [
    {
      "fingerprint_id": "SEED_20260520_D9E58D7F:abc12345",
      "recalculation_id": "SEED_20260520_D9E58D7F",
      "first_seen_date": "2026-05-21",
      "last_seen_date": "2026-06-15",
      "run_count": 19,
      "node_count": 39
    }
  ]
}
```

### GET /api/pis/policy/diff

```json
{
  "generated_at": "ISO timestamp",
  "versions_compared": 1,
  "has_changes": false,
  "diffs": [],
  "current_version": {...},
  "observations": ["Single policy version in effect. No changes detected."]
}
```

When multiple versions exist:
```json
{
  "diffs": [
    {
      "from_version_id": "SEED_A:hash1",
      "to_version_id": "SEED_B:hash2",
      "from_date": "2026-05-21",
      "to_date": "2026-06-01",
      "added_nodes": [],
      "removed_nodes": [],
      "changed_targets": [
        {
          "node_key": "EQUITIES.US.MID",
          "from_pct": 20.0,
          "to_pct": 15.0,
          "delta_pp": -5.0,
          "change_direction": "DECREASED"
        }
      ],
      "total_changes": 1,
      "summary": "1 allocation target change detected: 0 added, 0 removed, 1 modified."
    }
  ]
}
```

---

## 9. Edge Cases

| Case | Handling |
|------|---------|
| No PAR runs | Returns empty payload, no exception |
| Single PAR run | One version, no diffs possible |
| All same recalculation_id | One version, diff shows no changes |
| Multiple recalculation_ids | Multiple versions, diffs computed between consecutive pairs |
| Missing alignment.csv | That PAR run skipped |
| Missing config files | Structural policy shown as empty dict |
| Node in one version but not other | Classified as ADDED or REMOVED |
| Floating point target differences < 0.001pp | Treated as UNCHANGED (noise threshold) |
