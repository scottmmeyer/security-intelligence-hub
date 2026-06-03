# Phase 22D.7 — Workstream B: Replay Quality Audit

**Generated:** Phase 22D.7 Production Trust Remediation  
**Status:** PASS — No defect found  
**Run Audited:** PAR-20260602-4A83D5BD

---

## Summary

Replay quality data is correctly populated and consistent across all artifact
layers. There is no code defect in replay handling.

---

## Holdings-Level Replay Coverage

Source: `security_overlays.csv` (81 rows)

| Metric | Value |
|--------|-------|
| Total holdings | 81 |
| `replay_supported = True` | 46 (56.8%) |
| `replay_supported = False` | 35 (43.2%) |
| `replay_percentile` populated | Consistent with replay_supported |

Coverage of 56.8% is expected for this portfolio. Replay support requires a
symbol to have sufficient historical data in the replay universe. Not all 81
holdings (including ETFs, cash, and international names) qualify.

---

## UCF Verdicts Replay Consistency

Source: `ucf_verdicts.json` (81 holdings)

| Metric | Value |
|--------|-------|
| Total holdings | 81 |
| `replay_supported = True` | **46** |
| `replay_supported = False` | **35** |
| UCF ↔ overlay agreement | ✅ 100% consistent |

The UCF `source_signals.replay_supported` field matches `security_overlays.csv`
values for every holding. No divergence detected.

---

## Deployment Queue Replay Gate

Source: `deployment_queue.json` (42 candidates pre-eligibility filter)

The CW-DAS scoring model uses `replay_supported` as a binary gate (20 points).
Only holdings with `replay_supported = True` pass the eligibility filter for
deployment candidacy. Final queue candidate count: **42** after all gates.

---

## Recommendations Layer

The `recommendations.json` does not contain a `replay_supported` field at the
recommendation level — this is by design. Recommendations are node-level
directives; replay support is a holding-level attribute surfaced in:
- `security_overlays.csv`
- `ucf_verdicts.json` (source_signals)
- `deployment_queue.json` (eligibility gate)

One recommendation of type `IMPROVE_REPLAY_ALIGNMENT` is present, correctly
flagging the replay coverage gap for the operator's awareness.

---

## Verdict

**PASS** — Replay data is correctly computed, stored, and consistent across all
artifact layers. No remediation required.
