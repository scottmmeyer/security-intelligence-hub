# PA-006 — Allocation Drift Compliance & Persistence Intelligence: Design Document

**Status:** APPROVED FOR IMPLEMENTATION  
**Date:** 2026-06-15  
**Scope:** Read-only compliance governance. SIH/PIS boundary strictly preserved.

---

## 1. Required Questions — Answered

| # | Question | Answer |
|---|----------|--------|
| Q1 | Can compliance history be reconstructed from existing PIS artifacts? | **YES** — Every PAR `alignment.csv` contains `severity` (HIGH/MODERATE/LOW/NONE), `drift_pct`, `actual_pct`, `target_pct`, and `drift_direction`. These fields fully support compliance classification without any new data. 19 canonical dates × ~39 nodes = ~741 data points available immediately. |
| Q2 | Are schema changes required? | **NO** — Reads same PAR alignment artifacts as PIS-007. No new data collection. |
| Q3 | Does this modify allocation policy? | **NO** |
| Q4 | Does this modify CRA? | **NO** |
| Q5 | Does this modify CW-DAS? | **NO** |
| Q6 | Does this modify DIL? | **NO** |
| Q7 | Does this preserve SIH/PIS separation? | **YES** — PIS observes alignment results produced by SIH. No feedback path. |
| Q8 | Does this provide meaningful compliance intelligence? | **YES** — EQUITIES.INTERNATIONAL has been MODERATE/HIGH drift across all 19 dates. EQUITIES.US.LARGE similarly persistent. This is actionable governance intelligence. |
| Q9 | Does this identify persistent policy violations? | **YES** — Streak analysis identifies nodes with consecutive non-compliant dates. |
| Q10 | Does this improve governance visibility without creating policy feedback loops? | **YES** — All output is observational. Governance observations explicitly state they do not imply policy modification. |

---

## 2. Data Availability Audit

### 2.1 Available Fields per PAR Run (alignment.csv)

| Field | Use in Compliance |
|-------|------------------|
| `node_key` | Node identifier |
| `node_label` | Display name |
| `dimension_type` | ASSET_CLASS / GEOGRAPHY / MARKET_CAP / MEGA_SUBTIER |
| `severity` | **Primary compliance classifier**: HIGH / MODERATE / LOW / NONE |
| `drift_pct` | Signed drift from tactical target (actual - tactical_target) |
| `drift_direction` | OVERWEIGHT / UNDERWEIGHT / ON_TARGET |
| `actual_pct` | Effective actual allocation |
| `target_pct` | Strategic target |
| `tactical_target_pct` | Tactical-adjusted target |
| `alignment_score` | 0.0–1.0; 1.0 = perfectly aligned |

### 2.2 Compliance Classification (from severity)

The `severity` field is computed by the SIH allocation alignment engine and encodes the policy-aware tolerance assessment. Using it directly ensures PIS compliance classifications exactly match SIH's intent.

| Severity | Compliance Status |
|----------|------------------|
| NONE | COMPLIANT |
| LOW | COMPLIANT |
| MODERATE | WARNING |
| HIGH | NON_COMPLIANT |

### 2.3 Live Severity Distribution (2026-06-15 latest PAR)

- NONE: 26 nodes — COMPLIANT  
- LOW: 9 nodes — COMPLIANT  
- MODERATE: 5 nodes — WARNING  
- HIGH: 0 nodes — NON_COMPLIANT (currently)

---

## 3. Architecture

### 3.1 New Module

**File:** `src/pis/allocation_compliance.py`

**Public API:**
```python
def pis_compliance_summary(repo_root) -> dict
def pis_compliance_latest(repo_root) -> dict
def pis_compliance_history(repo_root) -> dict
```

### 3.2 New API Endpoints (3)

| Endpoint | Returns |
|----------|---------|
| `GET /api/pis/compliance/summary` | Summary cards: counts, compliance rates, top violations |
| `GET /api/pis/compliance/latest` | Per-node latest compliance status with streaks |
| `GET /api/pis/compliance/history` | Full compliance timeline per node per date |

### 3.3 New Dashboard Sections (4)

| Section Key | Content |
|-------------|---------|
| `complianceSummary` | Cards: total/compliant/warning/non-compliant/persistent violation count |
| `complianceLeaderboard` | All nodes: compliance rate, current status, current streak, longest streak |
| `complianceViolations` | Top persistent violations (worst compliance rate) |
| `complianceBest` | Most compliant nodes |

---

## 4. Compliance Labels

| Compliance Rate | Compliance Severity Label |
|-----------------|--------------------------|
| ≥ 80% | HIGHLY_COMPLIANT |
| ≥ 60% | MOSTLY_COMPLIANT |
| ≥ 40% | MIXED |
| < 40% | PERSISTENTLY_NON_COMPLIANT |

---

## 5. SIH/PIS Separation

- Reads SIH-produced `severity` field from alignment.csv — read-only
- No modification to any SIH output
- Governance observations are informational for human review
- Explicitly states: "This is a governance observation. Policy modification decisions are made by the SIH allocation engine."

---

## 6. Non-Goals

- No allocation target modification
- No tolerance band modification
- No CRA modification
- No automatic rebalancing triggers
- No ML or forecasting
