# PA-006 — Validation Plan: Allocation Compliance Engine

**Date:** 2026-06-15

---

## 1. Test File
`tests/test_allocation_compliance.py`

All tests deterministic, filesystem-isolated. No network calls.

---

## 2. Test Coverage Domains

### Domain 1 — Compliance Classification
| T-01 | severity=NONE → COMPLIANT |
| T-02 | severity=LOW → COMPLIANT |
| T-03 | severity=MODERATE → WARNING |
| T-04 | severity=HIGH → NON_COMPLIANT |
| T-05 | empty/unknown severity → COMPLIANT |

### Domain 2 — Historical Reconstruction
| T-06 | Empty PAR directory → empty entries |
| T-07 | Single PAR with alignment.csv → entries created |
| T-08 | Multiple dates, canonical selection (latest PAR wins) |
| T-09 | Missing alignment.csv → run skipped |
| T-10 | Malformed snapshot_date → skipped |

### Domain 3 — Streak Computation
| T-11 | All COMPLIANT dates → current_streak = total |
| T-12 | Mixed: C/C/W/W/NC → current_streak = 1, longest_compliant = 2 |
| T-13 | All NON_COMPLIANT → longest_non_compliant = total |
| T-14 | Single entry → streak = 1 |
| T-15 | C/NC/C/NC alternating → longest_compliant = 1 |
| T-16 | Streak correctly counts from end of sequence |

### Domain 4 — Compliance Rates
| T-17 | 10 compliant, 10 non-compliant → compliance_rate = 50% |
| T-18 | All compliant → compliance_rate = 100% |
| T-19 | All non-compliant → compliance_rate = 0% |
| T-20 | Compliant+warning mix → compliance_rate only counts COMPLIANT |

### Domain 5 — Compliance Severity Labels
| T-21 | rate >= 80% → HIGHLY_COMPLIANT |
| T-22 | rate 60-79% → MOSTLY_COMPLIANT |
| T-23 | rate 40-59% → MIXED |
| T-24 | rate < 40% → PERSISTENTLY_NON_COMPLIANT |
| T-25 | rate exactly 80% → HIGHLY_COMPLIANT |
| T-26 | rate exactly 40% → MIXED |

### Domain 6 — Governance Observations
| T-27 | Persistent violation node → observation mentions it |
| T-28 | Highly compliant node → observation mentions it |
| T-29 | Long non-compliant streak → observation notes streak |
| T-30 | Observations capped at 6 |

### Domain 7 — API Payload Integrity
| T-31 | pis_compliance_summary() required fields present |
| T-32 | pis_compliance_latest() nodes list with all fields |
| T-33 | pis_compliance_history() entries ascending by date |
| T-34 | counts sum: compliant + warning + non_compliant = total_nodes |
| T-35 | node_key consistent across all three endpoints |

### Domain 8 — Edge Cases
| T-36 | No PAR runs → empty payload |
| T-37 | All nodes COMPLIANT → persistently_non_compliant_count = 0 |
| T-38 | Single date → streak = 1 for all nodes |
| T-39 | Node in subset of dates → dates_available reflects actual count |

---

## 3. Validation Pass Criteria

| Criteria | Pass Condition |
|----------|---------------|
| All T-01 through T-39 pass | 0 failures |
| Full existing test suite | 0 regressions |
| `pis_compliance_summary()` live | No exceptions, valid JSON |
| `pis_compliance_latest()` live | ≥ 1 node returned |
| `pis_compliance_history()` live | Entries for ≥ 19 dates |
| Dashboard sections load | No JS errors |
