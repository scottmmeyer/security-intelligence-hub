# Phase 23.6B.1 — CRA Forensic Validation

**Date:** 2026-06-04  
**PAR Run Specified:** PAR-20260604-A47BD0AF  
**Analysis Type:** Read-only forensic — no code modifications

---

## Q1: Portfolio Snapshot Validation

### Trace

| Field | Value |
|-------|-------|
| Run ID | PAR-20260604-A47BD0AF |
| Portfolio Snapshot ID | PSNAP-20260604-13A6D8E7C222 |
| Source File | `Portfolio_Positions_Jun-04-2026 (4).csv` |
| Source Format | FIDELITY_CSV |
| Snapshot Date | 2026-06-04 |
| PAR Created | 2026-06-04T19:35:52 UTC |
| Total Market Value | $479,086.31 |
| Holding Count | 83 rows |

### Key Observation: "(4)" in Filename

The filename suffix `(4)` indicates this is the **fourth Fidelity export of the day**. This is significant — it strongly suggests the file was exported after multiple transaction rounds, not the morning opening state.

### Transaction Reflection Check

| Symbol | Status in PAR_A | Market Value | Notes |
|--------|-----------------|-------------|-------|
| FIS | **PRESENT** | $6,146.49 (149.2 shares) | Partial position — some shares sold, ~149 remain |
| FIGFX | **ABSENT** | — | Sale fully reflected; position closed |
| VXUS | **ABSENT** | — | Sale fully reflected; position closed |

### Answer A: Was this before or after today's transactions?

**AFTER.** FIGFX and VXUS are entirely absent from the holdings, meaning those sales are fully captured. FIS still shows a residual position at $6,146.49 (149.2 shares, cost basis $9,862.47), indicating partial sale activity — some FIS shares were sold but 149 remain.

### Answer B: Do holdings reflect the sales?

**Mostly yes.**
- FIGFX: ✅ Fully reflected (absent)
- VXUS: ✅ Fully reflected (absent)  
- FIS: ✅ Partially reflected — 149 shares remaining, not fully exited

### PENDING ACTIVITY Note

The holdings show a row:
- **Symbol:** PENDING ACTIVITY
- **Market Value:** $10,204.59
- **Operational State:** ACTIVE_POSITION (not excluded from analytics)

This $10,204.59 likely represents unsettled proceeds from today's sales (FIS/FIGFX/VXUS). The system classifies it as `ACTIVE_POSITION` rather than a settlement adjustment — see Q2 and Q3 for implications.

### CRA Run Mismatch

The CRA API (`GET /api/cra/proposal`) is currently serving results from **PAR-20260604-B01C0C82**, not **A47BD0AF**. However, both runs:
- Use the same source file: `Portfolio_Positions_Jun-04-2026 (4).csv`
- Show identical total MV: $479,086.31
- Were created within 4.3 minutes of each other (19:35 vs 19:40 UTC)

**Conclusion: The runs are functionally identical snapshots. The CRA mismatch is a version ordering artifact, not a stale data problem.**

---

## Q2: Cash Reconciliation

See `phase_23_6b1_cash_reconciliation.md`.

---

## Q3: CRA Capital Pool

See `phase_23_6b1_deployment_target_analysis.md`.

---

## Q4–Q7: Allocation Forensic

See `phase_23_6b1_deployment_target_analysis.md`.

---

## Q8: Summary

See `phase_23_6b1_final_verdict.md`.
