# Phase 23.6B.3 — Strategic Exit Workflow Review

**Date:** 2026-06-04  
**Symbol Under Review:** FIS  
**Analysis type:** Forensic only — no code changes

---

## 1. Current FIS State

| Field | Value |
|-------|-------|
| Market Value | $6,146.49 |
| Shares Remaining | 149.2049 |
| Cost Basis | $9,862.47 |
| Unrealized Loss | −$3,715.98 |
| % of Portfolio | 1.28% |
| ESS | BEARISH |
| Signal Direction | BEARISH |
| Opportunity Flag | WATCH |
| Overweight | No |
| Replay Supported | No |
| Operator Designation | `strategic_exit_symbols: ["FIS"]` |
| Tax Bucket | A (loss harvest) |

---

## 2. CRA Source Record for FIS

```
category:          SIGNAL_DETERIORATION
priority:          HIGH
estimated_proceeds: $1,537 (25% sizing of $6,146)
sizing_pct:        0.25
evidence_summary:  "ESS=BEARISH | [also: STRATEGIC_EXIT] operator-designated strategic exit"
tax_annotation:    "Unrealized loss ~$3,716 — tax loss harvest opportunity"
```

The evidence summary correctly captures both signals — BEARISH ESS as the primary detector, and the operator's strategic exit designation as a secondary annotation.

---

## 3. Does CRA Correctly Model Strategic Exits?

**Partially.** The detection is correct: FIS appears in the capital source list. The category assignment is the issue.

FIS is categorized as `SIGNAL_DETERIORATION` because the de-duplication logic promotes the highest-priority category, and `SIGNAL_DETERIORATION` ranks higher than `STRATEGIC_EXIT`. The `STRATEGIC_EXIT` designation is visible only in the evidence summary as a secondary annotation: `[also: STRATEGIC_EXIT]`.

**The problem:** A position that the operator has intentionally designated for exit (`strategic_exit_symbols`) should arguably display as `STRATEGIC_EXIT` even when a deterioration signal also exists — because the intent is different. Signal deterioration is a reactive observation; strategic exit is a proactive decision.

---

## 4. Does the System Recognize Intentional Operator Liquidation?

**Indirectly.** The `strategic_exit_symbols` list is read and processed. However, the system doesn't maintain any history of the operator's liquidation progress. There is no concept of:

- "This position was X shares last week, now Y shares — the operator is actively reducing"
- "This position has been in `strategic_exit_symbols` for N days"
- "This is a multi-session exit campaign"

The CRA treats FIS as a fresh sell candidate every run, not as a position already in mid-exit. The 149 remaining shares are treated identically to how 1,500 shares would be — no distinction between "initiating an exit" and "completing an exit."

**The 25% sizing problem:**

Because FIS has BEARISH (not VERY_BEARISH) ESS and is not overweight, the sizing heuristic applies 25% sizing: $6,146 × 25% = $1,537 estimated proceeds.

But the operator's actual intent is a **full exit** — they've already liquidated most of the original position (the cost basis of $9,862 vs current value of $6,146 suggests significant prior selling). The CRA's 25% sizing produces a de-minimis $1,537 recommendation that understates the operator's actual intent.

---

## 5. Should Strategic Exit Positions Be Handled Differently?

**Yes.** A position in `strategic_exit_symbols` should receive:

1. **Full sizing by default** (1.0, not 0.25 or 0.5) — the operator has explicitly designated this for exit
2. **`STRATEGIC_EXIT` as the primary category**, not a secondary annotation, even when a signal deterioration also applies
3. **Priority elevation** — operator-designated exits are more actionable than system-inferred signals

The current behavior where SIGNAL_DETERIORATION overrides STRATEGIC_EXIT produces a correct but misleading result: the sell recommendation is there, but for the wrong reason and at the wrong size.

---

## 6. Does the Exit State Require Additional System State?

**Yes, two specific additions would materially improve operator utility:**

### Addition A: Exit progress tracking
A persistent state field per symbol: `{symbol: {exit_initiated_date, original_position_size, remaining_size, sessions_active}}`. This would allow CRA to display: "FIS: 149 of ~400 shares remaining — exit 63% complete."

### Addition B: Full-exit sizing for strategic_exit_symbols
When a symbol appears in `strategic_exit_symbols`, override the category sizing heuristic to `1.0` (full exit) regardless of ESS severity. The operator has explicitly named this security for exit.

### What is NOT needed
- A separate PAR run for strategic exits
- Any modification to CW-DAS or ESS
- Any new UI panels

---

## 7. Summary

| Question | Answer |
|----------|--------|
| Does CRA correctly detect strategic exits? | Yes — FIS appears in sources |
| Is the sizing correct? | No — 25% when operator intent is 100% |
| Is the category correct? | Debatable — SIGNAL_DETERIORATION overrides STRATEGIC_EXIT |
| Does the system recognize active liquidation? | No — no progress awareness |
| Is additional state required? | Yes — exit progress tracking and full-exit sizing |
| Is the current behavior harmful? | Not harmful, but understated — $1,537 suggested vs ~$6,146 full intent |
