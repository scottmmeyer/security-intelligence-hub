# REFRESH-HEALTH-02A - Required Questions (Q1-Q16)

Date: 2026-06-17

Q1: Did the manually re-staged ESS files actually reprocess?
- Yes, earlier restage batch reprocessed (new 2026-06-17 run_ids and partitions). Current files now present in incoming have not yet produced a newer run after intake-20260617-061018-noness.

Q2: Was a new merged signal state generated?
- Yes. data/current/signal_snapshot.csv mtime 06:10:18 aligns with latest noness run completion.

Q3: Was ess_coverage_warning.json regenerated?
- No. mtime 06:02:42 predates 06:10 reprocess merges.

Q4: Why does the dashboard still show the warning?
- API reads stale ess_coverage_warning.json and UI renders API payload as-is.

Q5: Why did _holding appear?
- Created by manual terminal workflow during restage/move operations (transcript evidence), not by intake stage code.

Q6: Why did processed appear?
- Created by manual terminal archive command (mkdir -p incoming/ess/processed/$ts/... and mv), not by intake stage code.

Q7: Are those directories expected?
- Not in formal intake contract. Expected directories are only starmine and non_starmine_zacks.

Q8: Were they introduced by a recent change?
- No committed code-change evidence; introduced operationally in-session.

Q9: Should incoming remain source-only?
- Yes, per current architecture and intake readiness contract.

Q10: Is intake-area contamination occurring?
- Yes, operationally. Non-contract working/archive dirs were mixed into incoming/ess.

Q11: Why does Zacks still display stale?
- Top-card uses provider sourced_date from latest_zacks.csv (2026-06-16), so 2026-06-17 view marks stale.

Q12: Is Zacks freshness logic correct?
- It is internally consistent for a dual-model design (provider-day freshness + holdings-threshold compliance).

Q13: Which freshness calculation is authoritative?
- Depends on objective:
  - Provider recency authority: top-card sourced_date.
  - Portfolio applicability authority: holdings_coverage threshold status.

Q14: Are any remaining issues purely display-layer defects?
- ESS warning persistence issue is not display-only; source warning artifact is stale. UI is mostly a faithful renderer.

Q15: What exact actions are required to clear ESS health?
- Forensic answer (no fix implementation): ensure warning artifact is regenerated from current merged state after latest intake merge and before dashboard/API consumption; then refresh API view.

Q16: What exact actions are required to clear Zacks health?
- Forensic answer (no fix implementation): update latest_zacks.csv with current-day sourced_date rows (or align top-card semantics to threshold model if policy prefers compliance framing).
