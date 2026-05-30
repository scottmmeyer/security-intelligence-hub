# Conflict Graph Report

**Phase 7.3 — Architecture Design**
**Document type:** Recommendation conflict taxonomy + conflict graph specification
**Based on:** Phase 7.2 live run data (2026-05-30)

---

## 1. Conflict Taxonomy

Recommendations can conflict in three ways:

### Type 1 — Direct Node Conflict
**Definition:** Rec A proposes an action that worsens the node condition that
Rec B was generated to repair.

**Pattern:** Build[NODE_X] + vehicle(NODE_X) leaks into NODE_Y → simultaneously
worsening Reduce[NODE_Y].

**Current Examples:**
- Build US Large (VOO) + Reduce Hyper Mega
- Build Extended Mega (VTI/SCHB) + Reduce Hyper Mega
- Build Extended Mega (VOO) + Reduce Hyper Mega + Reduce Ultra Mega

### Type 2 — Vehicle Redundancy Conflict
**Definition:** Two separate Build recommendations propose the same vehicle,
meaning deploying one partially completes the other — but the engine treats
them as independent.

**Current Example:**
- Build US Large → VOO
- Build Extended Mega → VOO (secondary option)
→ Same instrument recommended for two distinct node repair targets.
→ Buying VOO for US Large will simultaneously (marginally) help Extended Mega,
  making the second rec partially redundant.

### Type 3 — PMI-Engine Contradiction
**Definition:** The allocation engine generates a recommendation at a given
severity, and the PMI layer independently assigns INFORMATIONAL urgency —
meaning the engine says "act" and the PMI says "this is intentional, no action."

**Current Examples:**
- Build US Large: Engine=MODERATE, PMI=INFORMATIONAL
- Build Extended Mega: Engine=MODERATE, PMI=INFORMATIONAL

---

## 2. Current Conflict Graph

Nodes in the graph represent **active recommendations** from the current run.
Edges represent **conflict relationships** with their type and direction.

```
CONFLICT GRAPH — Current Portfolio Run (2026-05-30)

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │   [BUILD US LARGE]          [BUILD EXTENDED MEGA]          │
  │   VOO / IVV / SPY           VTI / SCHB / VOO               │
  │   severity=MODERATE         severity=MODERATE               │
  │   PMI=INFORMATIONAL         PMI=INFORMATIONAL               │
  │        │                         │                         │
  │        │ T1: both VOO vehicles   │                         │
  │        │ worsen HYPER_MEGA OW    │                         │
  │        │ (+~0.3% per 1% deploy.) │                         │
  │        ▼                         ▼                         │
  │   ┌────────────────────────────────────┐                   │
  │   │      [REDUCE HYPER_MEGA]           │                   │
  │   │      severity=MODERATE             │◄── CONFLICT (T1)  │
  │   │      PMI=STANDARD_OVERWEIGHT       │                   │
  │   └────────────────────────────────────┘                   │
  │                   │                                         │
  │              No conflict                                    │
  │                   ▼                                         │
  │   ┌────────────────────────────────────┐                   │
  │   │   [REDUCE INTERNATIONAL]           │                   │
  │   │   severity=MODERATE                │                   │
  │   │   PMI=STANDARD_OVERWEIGHT          │                   │
  │   └────────────────────────────────────┘                   │
  │                                                             │
  │   ┌────────────────────────────────────┐                   │
  │   │   [REDUCE INTERNATIONAL LARGE]     │                   │
  │   │   severity=MODERATE                │                   │
  │   │   PMI=STANDARD_OVERWEIGHT          │                   │
  │   └────────────────────────────────────┘                   │
  │                                                             │
  │  VEHICLE REDUNDANCY CONFLICTS (T2):                        │
  │  BUILD_US_LARGE ←──── VOO (shared) ────► BUILD_EXT_MEGA   │
  │                                                             │
  │  PMI-ENGINE CONTRADICTIONS (T3):                           │
  │  BUILD_US_LARGE:    engine=MODERATE ≠ pmi=INFORMATIONAL    │
  │  BUILD_EXT_MEGA:    engine=MODERATE ≠ pmi=INFORMATIONAL    │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

---

## 3. Conflict Matrix

Rows = recommendations. Columns = recommendations. Cell = conflict type.
`—` = no conflict. `C` = conflict. `S` = synergistic. `N` = neutral.

| | BUILD US LARGE | BUILD EXT MEGA | REDUCE HYPER MEGA | REDUCE INTL | REDUCE INTL LARGE |
|---|---|---|---|---|---|
| **BUILD US LARGE** | — | T2 (VOO overlap) | T1 (VOO worsens OW) | N | N |
| **BUILD EXT MEGA** | T2 (VOO overlap) | — | T1 (VTI/SCHB worsen OW) | N | N |
| **REDUCE HYPER MEGA** | T1 (opposed) | T1 (opposed) | — | N | N |
| **REDUCE INTL** | N | N | N | — | S (both reduce intl) |
| **REDUCE INTL LARGE** | N | N | N | S (both reduce intl) | — |

**Legend:**
- T1 = Type 1 (direct node conflict)
- T2 = Type 2 (vehicle redundancy)
- S = Synergistic (mutually reinforcing)
- N = Neutral (no interaction)

---

## 4. Synergistic Recommendation Pairs

These pairs are mutually reinforcing — executing either one supports the goal of the other.

| Pair | Rationale |
|------|-----------|
| REDUCE INTERNATIONAL + REDUCE INTERNATIONAL LARGE | Intl Large is a sub-node of International — reducing both addresses the same structural overweight from two levels. |
| REDUCE HYPER MEGA + TRIM any CCL/HCA in HYPER_MEGA node | Trim intelligence identifies NVDA, MSFT, AVGO as trim candidates in HYPER_MEGA. A Reduce rec + a targeted trim rec are fully synergistic. |

---

## 5. Neutral Recommendation Pairs

These pairs have no material interaction — executing one does not affect the other.

| Pair | Rationale |
|------|-----------|
| REDUCE INTERNATIONAL + BUILD US LARGE | Reducing intl does not directly fill the US Large gap (capital returns to cash first). |
| REDUCE HYPER MEGA + BUILD US LARGE | Trim of HYPER_MEGA holdings releases cash for US Large, but mechanism is indirect (cash intermediate). With conviction-gated security path, this could become synergistic in a future architecture. |

---

## 6. Future Conflict Detection Algorithm

For the proposed unified optimizer, conflict detection should run as a post-generation
pass over the full recommendation set.

### Algorithm: Detect Direct Node Conflicts (T1)

```
FOR each Build rec R_build targeting node N_underweight:
  vehicles = R_build.affected_symbols
  FOR each vehicle V in vehicles:
    FOR each OW node N_overweight in current_overweight_nodes:
      exposure_added = V.node_weight[N_overweight] × deployment_fraction
      IF exposure_added > CONFLICT_THRESHOLD (suggest: 0.1%):
        FOR each Reduce rec R_reduce targeting N_overweight:
          EMIT conflict(R_build, R_reduce, type=T1,
                        amount=exposure_added,
                        vehicle=V)
```

### Algorithm: Detect Vehicle Redundancy Conflicts (T2)

```
FOR each pair of Build recs (R1, R2):
  shared_vehicles = R1.vehicles ∩ R2.vehicles
  IF shared_vehicles is not empty:
    EMIT conflict(R1, R2, type=T2, vehicles=shared_vehicles)
```

### Algorithm: Detect PMI-Engine Contradictions (T3)

```
FOR each rec R:
  IF R.severity in (MODERATE, HIGH):
    IF R.mandate_urgency == INFORMATIONAL:
      EMIT contradiction(R, type=T3,
                         engine_severity=R.severity,
                         pmi_urgency=R.mandate_urgency)
```

---

## 7. Conflict Resolution Rules

When conflicts are detected, the engine should resolve them before surfacing
recommendations to the user. Proposed resolution hierarchy:

### T1 Conflict Resolution
1. Compute net node improvement for each conflicting pair
2. If Build rec has net_improvement ≤ 0: **SUPPRESS Build rec**
3. If Build rec has net_improvement > 0 but is CONFLICT_RISK: **DOWNGRADE to
   INFORMATIONAL with conflict explanation**
4. Reduce rec is **never suppressed** due to a Build conflict

### T2 Conflict Resolution
1. When same vehicle appears in multiple Build recs, combine them:
   **"Adding VOO addresses both US Large (−7.3%) and Extended Mega (−4.2%)
   underweights, though at low effective coverage for each."**
2. Do not emit duplicate Build recs for the same vehicle.

### T3 Conflict Resolution
1. If mandate_urgency = INFORMATIONAL: **Engine rec is automatically DOWNGRADED**
   to match mandate interpretation. PMI is authoritative.
2. Engine severity is preserved in `raw_severity` field for audit/diagnostics.
3. User sees a single coherent recommendation: INFORMATIONAL, with explanation
   that mandate treats this deviation as intentional.

---

## 8. Recommendation Conflict Summary (Current Run)

| Conflict ID | Type | Recs Involved | Severity | Resolution |
|-------------|------|---------------|----------|------------|
| CF-001 | T1 | Build US Large (VOO) ↔ Reduce Hyper Mega | HIGH | Suppress Build US Large (net_improvement < 0) |
| CF-002 | T1 | Build Ext Mega (VTI) ↔ Reduce Hyper Mega | MODERATE | Suppress Build Ext Mega (VTI also leaks into Hyper Mega) |
| CF-003 | T2 | Build US Large (VOO) ↔ Build Ext Mega (VOO) | LOW | Merge into single vehicle rec |
| CF-004 | T3 | Build US Large ↔ PMI INFORMATIONAL | HIGH | PMI is authoritative; demote to INFORMATIONAL |
| CF-005 | T3 | Build Ext Mega ↔ PMI INFORMATIONAL | HIGH | PMI is authoritative; demote to INFORMATIONAL |

**After resolution:** Zero actionable Build recommendations remain for this portfolio
under the CONCENTRATED_ALPHA mandate. This is the **correct** outcome — the mandate
explicitly tolerates the underweights as intentional, and the ETF vehicles proposed
would create net harm. The three Reduce recommendations remain coherent and actionable.
