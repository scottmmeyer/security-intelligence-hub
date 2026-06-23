# Backlog Current State Audit
## SIH-BACKLOG-REALIGNMENT-01 — Part A

Date: 2026-06-17
Scope: Open issues #56, #55, #6, #5, #3, #2

## Audit Matrix

| Issue | Delivered Work | Remaining Work | Still Active? | Recommended Disposition |
|---|---|---|---|---|
| #56 ESS-INTAKE-PERSIST-01 | Bug reproduced and root cause documented. Same-day merged snapshot row counts can exceed current run manifest counts; issue filed with clear fix direction. | Implement validator logic that compares run-partition rows (not merged snapshot total), then restore automatic incoming-file cleanup on successful persistence. | Yes (active defect). | Keep OPEN (High). |
| #55 DISLOCATION-07 | Delivered: directional_accuracy module, 4 APIs, dashboard directional panel, comparative magnitude-vs-direction verdict, 66 tests passing, live data refresh and endpoint validation. | Optional follow-up only (threshold tuning, directional confidence UX polish, deeper per-symbol breakdown if desired). | Not for core scope. | Close issue as COMPLETE; open optional follow-up issue if additional UX/research desired. |
| #6 Governance & Tooling Epic | Completed: backlog establishment/governance standards; major closure hygiene completed; defect tracking active (#56). | Explicit unfinished items in epic body remain: CI on push, signal freshness monitoring, YAML debt cleanup. | Yes (platform-wide governance work remains). | Keep OPEN; update checklist with current baselines and create child issues for each remaining item. |
| #5 Signal Intelligence Evolution Epic | Completed: ISSUE-12D, DISLOCATION-02/03, DISLOCATION-06, DISLOCATION-07, conflict analytics dashboard, predictive findings from real data. | Remaining epic body items are older placeholders (FMP integration assessments, drift penalty progression). Needs scope refresh to current roadmap. | Yes, but stale scope definition. | Keep OPEN; rewrite epic scope to "Signal Intelligence v2" and archive delivered phases in issue comment. |
| #3 PAP Epic | Completed major PAP stack and deployment workflow foundations. | Remaining: 23.0B PAP v2 / operator workflow enhancements and any planned approval/audit trail features. | Yes. | Keep OPEN; split 23.0B into concrete child issues with acceptance criteria. |
| #2 CRA Epic | Completed core CRA implementation and trust remediation phases. | Remaining from issue body: ISSUE-02 draft persistence/export completion check and 23.6D TBD definition. | Yes. | Keep OPEN; convert "23.6D TBD" into named work items, close when export/sign-off workflow finalized. |

## Detailed Notes Per Issue

### #56 ESS-INTAKE-PERSIST-01
- Status truth: issue is valid and currently impacting operational outcome.
- Observed behavior: intake can write valid run partitions but still report FAILED because current merged snapshot row count includes prior same-day runs.
- Operational consequence: incoming files are not auto-cleaned because cleanup path is gated behind COMPLETE.
- Recommendation: prioritize defect fix before additional intake automation changes.

### #55 DISLOCATION-07
- Scope objective achieved:
  - Directional prediction reconstruction
  - Predicted vs actual direction comparison
  - Hit rate / precision / recall / FPR / FNR / balanced accuracy
  - Pattern reliability ranking and dashboard integration
  - Comparative analysis vs DISLOCATION-06 magnitude accuracy
- Real-data conclusion captured: conflict patterns do not currently support reliable per-instance direction forecasting.
- Recommendation: close as delivered; preserve verdict as a research finding, not a failure.

### #6 Governance & Tooling Epic
- Still appropriate as umbrella epic.
- Needs refreshed decomposition to avoid broad evergreen scope.
- Recommendation: attach three explicit child issues and track to completion:
  - GOV-CI-01 GitHub Actions test gate
  - GOV-FRESH-01 Signal freshness monitoring automation
  - GOV-DEBT-01 YAML registry cleanup

### #5 Signal Intelligence Evolution Epic
- Delivery has surpassed checklist content in current epic description.
- Recommendation: issue should remain open only if rewritten to current next-wave scope (for example, signal quality, freshness, calibration governance, and feature retirement strategy).

### #3 PAP Epic
- Core objective mostly delivered; remaining work is refinement and operator workflow hardening.
- Recommendation: retain as open parent until PAP v2 scope is concretely ticketed and executed.

### #2 CRA Epic
- Core CRA capability is mature, but issue body still lists unfinished placeholders.
- Recommendation: keep open until export/sign-off workflow is explicitly resolved and TBD phase is defined.

## Proposed Immediate GitHub Actions

1. Close #55 with completion comment referencing module, endpoints, tests, and live validation.
2. Keep #56 open and prioritize as active production defect.
3. Keep #6/#5/#3/#2 open, but post a "scope refresh" comment on each with:
   - delivered phases archived
   - remaining concrete child issues
   - closure criteria
