# PA-006 — Algorithm Specification: Allocation Compliance Engine

**Date:** 2026-06-15

---

## 1. Module: `src/pis/allocation_compliance.py`

**Public API:**
```python
def pis_compliance_summary(repo_root: Path | str = ".") -> dict
def pis_compliance_latest(repo_root: Path | str = ".") -> dict
def pis_compliance_history(repo_root: Path | str = ".") -> dict
```

---

## 2. Data Models

```python
# Compliance status per node per date
@dataclass(frozen=True)
class ComplianceEntry:
    snapshot_date: str
    node_key: str
    node_label: str
    dimension_type: str
    compliance_status: str     # COMPLIANT | WARNING | NON_COMPLIANT
    severity: str              # original SIH severity: NONE | LOW | MODERATE | HIGH
    drift_pct: float
    actual_pct: float
    target_pct: float
    drift_direction: str       # OVERWEIGHT | UNDERWEIGHT | ON_TARGET

# Per-node compliance analytics
@dataclass(frozen=True)
class NodeComplianceResult:
    node_key: str
    node_label: str
    dimension_type: str
    dates_available: int
    compliant_count: int
    warning_count: int
    non_compliant_count: int
    compliance_rate_pct: float         # (compliant) / total * 100
    non_compliance_rate_pct: float     # (non_compliant) / total * 100
    compliance_severity: str           # HIGHLY_COMPLIANT | MOSTLY_COMPLIANT | MIXED | PERSISTENTLY_NON_COMPLIANT
    current_status: str                # latest date's compliance status
    current_streak: int                # consecutive dates with current_status
    longest_compliant_streak: int      # max consecutive COMPLIANT dates
    longest_non_compliant_streak: int  # max consecutive NON_COMPLIANT dates
    current_drift_pct: float           # latest drift_pct
    current_actual_pct: float          # latest actual_pct
    current_target_pct: float          # latest target_pct
```

---

## 3. Step 1 — Load Compliance History from PAR Artifacts

Reuses the same canonical PAR selection pattern as PIS-007:
- Enumerate PAR run directories
- For each snapshot_date, select the PAR with latest `created_at_utc`
- Parse `alignment.csv` for node compliance data

```python
def _collect_compliance_entries(repo_root: Path) -> list[ComplianceEntry]:
    """
    For each canonical PAR date, extract compliance status per node from alignment.csv.
    Uses severity field as compliance classifier.
    """
    par_dir = repo_root / "data" / "portfolio_ingestion" / "analysis_runs"
    # ... canonical selection (identical to PIS-007 pattern) ...
    
    entries = []
    for snap_date, align_file in canonical_runs:
        for row in read_csv(align_file):
            node_key = row["node_key"].strip()
            if not node_key: continue
            severity = row["severity"].strip().upper()
            compliance_status = _severity_to_compliance(severity)
            entries.append(ComplianceEntry(
                snapshot_date=snap_date,
                node_key=node_key,
                node_label=row["node_label"],
                dimension_type=row["dimension_type"],
                compliance_status=compliance_status,
                severity=severity,
                drift_pct=safe_float(row["drift_pct"]),
                actual_pct=safe_float(row["effective_actual_pct"] or row["actual_pct"]),
                target_pct=safe_float(row["tactical_target_pct"] or row["target_pct"]),
                drift_direction=row["drift_direction"],
            ))
    return sorted(entries, key=lambda e: (e.node_key, e.snapshot_date))
```

---

## 4. Step 2 — Compliance Classification

```python
def _severity_to_compliance(severity: str) -> str:
    """Map SIH severity to compliance status.
    
    Uses SIH's own severity computation — PIS does not re-derive this.
    """
    if severity in {"NONE", "LOW"}:
        return "COMPLIANT"
    if severity == "MODERATE":
        return "WARNING"
    if severity == "HIGH":
        return "NON_COMPLIANT"
    return "COMPLIANT"  # unknown severity → benefit of the doubt
```

---

## 5. Step 3 — Streak Computation

```python
def _compute_streaks(entries: list[ComplianceEntry]) -> tuple[int, int, int, int]:
    """Compute (current_streak, longest_compliant, longest_non_compliant, ...).
    
    entries must be sorted ascending by snapshot_date for a SINGLE node.
    Returns: (current_streak, longest_compliant_streak, longest_non_compliant_streak)
    """
    if not entries:
        return 0, 0, 0

    # Current streak: consecutive from the end with same status
    current_status = entries[-1].compliance_status
    current_streak = 0
    for e in reversed(entries):
        if e.compliance_status == current_status:
            current_streak += 1
        else:
            break

    # Longest streaks
    longest_compliant = 0
    longest_non_compliant = 0
    run_len = 1

    for i in range(1, len(entries)):
        if entries[i].compliance_status == entries[i-1].compliance_status:
            run_len += 1
        else:
            _update_longest(entries[i-1].compliance_status, run_len,
                           longest_compliant, longest_non_compliant)
            run_len = 1
    # Final run
    _update_longest(entries[-1].compliance_status, run_len,
                   longest_compliant, longest_non_compliant)

    return current_streak, longest_compliant, longest_non_compliant
```

---

## 6. Step 4 — Node Compliance Analytics

```python
def _compute_node_compliance(
    node_key: str,
    node_label: str,
    dimension_type: str,
    entries: list[ComplianceEntry],  # sorted ascending by date
) -> NodeComplianceResult:
    
    total = len(entries)
    compliant = sum(1 for e in entries if e.compliance_status == "COMPLIANT")
    warning = sum(1 for e in entries if e.compliance_status == "WARNING")
    non_compliant = sum(1 for e in entries if e.compliance_status == "NON_COMPLIANT")
    
    compliance_rate = round(compliant / total * 100, 1) if total else 0.0
    non_compliance_rate = round(non_compliant / total * 100, 1) if total else 0.0
    
    # Compliance severity label
    label = _compliance_severity_label(compliance_rate)
    
    # Latest values
    latest = entries[-1]
    
    # Streaks
    current_streak, longest_compliant, longest_non_compliant = _compute_streaks(entries)
    
    return NodeComplianceResult(
        node_key=node_key,
        node_label=node_label,
        dimension_type=dimension_type,
        dates_available=total,
        compliant_count=compliant,
        warning_count=warning,
        non_compliant_count=non_compliant,
        compliance_rate_pct=compliance_rate,
        non_compliance_rate_pct=non_compliance_rate,
        compliance_severity=label,
        current_status=latest.compliance_status,
        current_streak=current_streak,
        longest_compliant_streak=longest_compliant,
        longest_non_compliant_streak=longest_non_compliant,
        current_drift_pct=latest.drift_pct,
        current_actual_pct=latest.actual_pct,
        current_target_pct=latest.target_pct,
    )
```

---

## 7. Step 5 — Compliance Severity Labels

```python
def _compliance_severity_label(compliance_rate_pct: float) -> str:
    if compliance_rate_pct >= 80.0:
        return "HIGHLY_COMPLIANT"
    if compliance_rate_pct >= 60.0:
        return "MOSTLY_COMPLIANT"
    if compliance_rate_pct >= 40.0:
        return "MIXED"
    return "PERSISTENTLY_NON_COMPLIANT"
```

---

## 8. Step 6 — Governance Observations

Rules:
1. **Persistently non-compliant nodes** (all/most dates): "X has been non-compliant on N of M canonical dates."
2. **Highly compliant nodes**: "X has maintained compliance for N% of the observation period."
3. **Current longest streak**: "X has been non-compliant for N consecutive canonical dates."
4. **Mixed/oscillating**: "X alternates between compliant and non-compliant states."
5. **Summary**: "M of N allocation nodes are currently compliant."

---

## 9. API Payload Contracts

### GET /api/pis/compliance/summary

```json
{
  "generated_at": "ISO timestamp",
  "total_nodes": 39,
  "currently_compliant": 26,
  "currently_warning": 5,
  "currently_non_compliant": 0,
  "dates_covered": 19,
  "highly_compliant_count": 18,
  "persistently_non_compliant_count": 3,
  "top_violations": [
    {"node_key": "EQUITIES.INTERNATIONAL", "non_compliance_rate_pct": 89.5,
     "current_streak": 19}
  ],
  "observations": ["..."]
}
```

### GET /api/pis/compliance/latest

```json
{
  "generated_at": "ISO timestamp",
  "current_date": "2026-06-15",
  "nodes": [
    {
      "node_key": "EQUITIES.INTERNATIONAL",
      "node_label": "EQUITIES.INTERNATIONAL",
      "compliance_severity": "PERSISTENTLY_NON_COMPLIANT",
      "current_status": "WARNING",
      "compliance_rate_pct": 10.5,
      "current_streak": 19,
      "longest_non_compliant_streak": 19,
      "current_drift_pct": 6.83
    }
  ]
}
```

### GET /api/pis/compliance/history

```json
{
  "generated_at": "ISO timestamp",
  "dates": ["2026-05-21", "..."],
  "nodes": [
    {
      "node_key": "EQUITIES.INTERNATIONAL",
      "entries": [
        {"snapshot_date": "2026-05-21", "compliance_status": "WARNING",
         "severity": "MODERATE", "drift_pct": 8.1, "actual_pct": 20.1, "target_pct": 12.0}
      ]
    }
  ]
}
```

---

## 10. Edge Cases

| Case | Handling |
|------|---------|
| Empty alignment.csv | No entries for that date |
| severity = "" or unknown | Mapped to COMPLIANT (benefit of the doubt) |
| Node appears in some dates only | Only dates where node appears count |
| All nodes COMPLIANT | persistent_violation_count = 0 |
| Single date only | Streak = 1, longest_streak = 1 |
| No PAR runs | Empty payload, no exception |
