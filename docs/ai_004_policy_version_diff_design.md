# AI-004 — Allocation Policy Version Diff Visibility: Design Document

**Status:** APPROVED FOR IMPLEMENTATION  
**Date:** 2026-06-15  
**Scope:** Read-only policy governance visibility. SIH/PIS boundary strictly preserved.

---

## 1. Required Questions — Answered

| # | Question | Answer |
|---|----------|--------|
| Q1 | Can policy history be reconstructed from existing artifacts? | **YES — PARTIALLY.** The current policy files (allocation_policy.yaml, allocation_dimensions.yaml, allocation_methodology.yaml) can be fingerprinted and documented as the baseline version. PAR `alignment.csv` embeds `target_pct` and `tactical_target_pct` per node per run — **every PAR run is an implicit policy snapshot**. All 19 canonical runs share recalculation ID `SEED_20260520_D9E58D7F` — indicating a single policy version in production history. The diff engine is ready to detect future policy changes the moment they occur. |
| Q2 | Are schema changes required? | **NO** — New module reads existing config files and PAR alignment.csv artifacts. Writes only to `data/history/pis/policy/` (derived, regeneratable). |
| Q3 | Does this modify allocation policy? | **NO** |
| Q4 | Does this modify CRA? | **NO** |
| Q5 | Does this modify CW-DAS? | **NO** |
| Q6 | Does this modify DIL? | **NO** |
| Q7 | Does this preserve SIH/PIS separation? | **YES** — PIS reads and compares SIH policy outputs. No feedback path exists. All findings are governance artifacts. |
| Q8 | Does this provide meaningful governance intelligence? | **YES** — Provides the infrastructure to answer "why did the system change its mind?" on any future policy update. Current state: establishes version V1 baseline. Future state: automatic change detection and impact quantification. |
| Q9 | Does this explain recommendation evolution? | **YES** — When policy changes are detected, the engine attributes alignment drifts, CRA recommendation changes, and target changes to the specific policy version responsible. |
| Q10 | Does this improve auditability and traceability? | **YES** — Every PAR run is now linked to the policy fingerprint active at that time. Regulatory audit capability: "which policy was in effect when this recommendation was generated?" |

---

## 2. Data Availability Audit

### 2.1 Policy Config Files

| File | ID | SHA-256 (current) |
|------|----|--------------------|
| `config/allocation_policy.yaml` | `ALLOCATION_POLICY_V1` | `8f7195b655f3...` |
| `config/allocation_dimensions.yaml` | `v1` | `924484b2cf52...` |
| `config/allocation_methodology.yaml` | `v1_2026_05` | `db11aa89e284...` |

### 2.2 PAR Alignment Artifacts (Policy State per Run)

Each PAR `alignment.csv` embeds:
- `node_key` — allocation hierarchy node (30 nodes)
- `target_pct` — strategic target percentage of total portfolio
- `tactical_target_pct` — tactical-adjusted target
- `drift_pct` — actual minus tactical target
- `severity`, `alignment_score`

**This makes every PAR run an implicit policy snapshot.** Target changes between PAR runs signal policy recalculation events.

### 2.3 Policy Version History

**Current state:** Single version `SEED_20260520_D9E58D7F` across all 19 canonical dates.

This is expected behavior — the allocation policy recalculates when evidence thresholds are crossed or when the operator explicitly triggers recalculation. No policy changes have occurred in the observation window.

### 2.4 Recalculation ID as Version Key

The `recalculation_id` in `run_metadata.json` is the existing policy version identifier. When a new policy recalculation occurs, a new `recalculation_id` is minted. The diff engine tracks changes between recalculation IDs.

---

## 3. Architecture

### 3.1 New Module

**File:** `src/pis/policy_version_diff.py`

**Public API:**
```python
def pis_policy_current(repo_root) -> dict       # Current policy snapshot
def pis_policy_history(repo_root) -> dict        # Policy version timeline
def pis_policy_diff(repo_root) -> dict           # Diff between latest two versions
```

### 3.2 Policy Fingerprint

A policy fingerprint captures the full allocation target state at a point in time, derived from PAR alignment.csv:

```python
@dataclass(frozen=True)
class PolicyFingerprint:
    fingerprint_id: str           # derived from recalculation_id + content hash
    recalculation_id: str         # from run_metadata.json
    first_seen_date: str          # earliest PAR date with this recalculation_id
    last_seen_date: str           # latest PAR date with this recalculation_id
    run_count: int                # number of PAR runs using this policy version
    node_count: int               # number of allocation nodes
    node_targets: dict            # {node_key: target_pct}
    tactical_targets: dict        # {node_key: tactical_target_pct}
    policy_id: str                # from config/allocation_policy.yaml
    methodology_id: str           # from config/allocation_methodology.yaml
    config_hash: str              # SHA-256 of policy config files (current only)
    created_at: str
```

### 3.3 Policy Diff

```python
@dataclass(frozen=True)
class PolicyDiff:
    from_fingerprint_id: str
    to_fingerprint_id: str
    from_date: str
    to_date: str
    added_nodes: tuple[str, ...]
    removed_nodes: tuple[str, ...]
    changed_targets: tuple[TargetChange, ...]
    changed_tactical_targets: tuple[TargetChange, ...]
    total_changes: int
    affected_node_count: int
    summary: str

@dataclass(frozen=True)
class TargetChange:
    node_key: str
    node_label: str
    from_pct: float
    to_pct: float
    delta_pp: float          # to - from
    change_direction: str    # INCREASED | DECREASED | UNCHANGED
```

### 3.4 New API Endpoints (3)

| Endpoint | Returns |
|----------|---------|
| `GET /api/pis/policy/current` | Current policy fingerprint + structural constraints |
| `GET /api/pis/policy/history` | All distinct policy versions seen in PAR history |
| `GET /api/pis/policy/diff` | Diff between current and prior policy version (or baseline) |

### 3.5 New Dashboard Sections (4)

| Section Key | Content |
|-------------|---------|
| `policyCurrent` | Current policy summary cards |
| `policyHistory` | Policy version timeline table |
| `policyDiff` | Target changes table |
| `policyGovObs` | Governance observations |

---

## 4. Impact Analysis Approach

For each policy version transition, quantify:
1. **Node target changes**: which nodes moved and by how much
2. **Severity escalations**: nodes where drift severity changed (LOW → HIGH) due to target shift
3. **Alignment impact**: count of nodes where drift_direction flipped (OVERWEIGHT → UNDERWEIGHT)
4. **Recommendation delta**: estimated count of CRA recommendations affected

These are computed from PAR alignment data — no re-running of the policy engine.

---

## 5. SIH/PIS Separation Enforcement

The module:
1. **Reads** policy config files (SIH outputs) — read-only
2. **Reads** PAR alignment.csv artifacts (SIH outputs) — read-only
3. **Writes** only to `data/history/pis/policy/` (PIS governance artifacts)
4. **Produces** only governance observations — no policy modification
5. **Never** modifies targets, tolerances, weights, or any SIH input

---

## 6. Non-Goals

- No changes to policy recalculation logic
- No automatic target adjustment
- No CRA modification
- No UCF modification
- No ML or predictive models
- No recommendation generation based on policy diffs
