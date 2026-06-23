# REFRESH-HEALTH-02A Part B - New Directory Introduction Audit

Date: 2026-06-17
Scope: incoming/ess/_holding and incoming/ess/processed

## Summary Finding

The directories were introduced by an operator/assistant terminal move/archive command, not by ESS intake stage code.

## Timestamp Evidence

Directory birth times (filesystem birth timestamp):
- incoming/ess/_holding -> 2026-06-17 06:09:59
- incoming/ess/processed -> 2026-06-17 06:10:37
- incoming/ess/processed/20260617-061037 -> 2026-06-17 06:10:37

## Code-Path and Transcript Evidence

1. Intake stage code does not create these directories:
- src/pipeline/stages/ess_intake_stage.py only reads from incoming/ess/starmine and incoming/ess/non_starmine_zacks via intake readiness validator.
- Cleanup behavior is unlink(file) on discovered CSV files; no move/archive directory creation in stage logic.

2. Intake readiness contract only includes two expected source dirs:
- src/validation/intake_readiness_validator.py default intake directories:
  - incoming/ess/starmine
  - incoming/ess/non_starmine_zacks

3. Direct provenance from session transcript:
- Transcript line around event 2868 shows terminal command:
  - mkdir -p incoming/ess/processed/$ts/{starmine,non_starmine_zacks}
  - mv incoming/ess/_holding/EquitySummaryScores-17Jun2026.csv -> processed/$ts/starmine/
  - mv incoming/ess/non_starmine_zacks/non-ess.csv -> processed/$ts/non_starmine_zacks/
- This is explicit creator evidence for processed and for use of _holding.

4. .gitignore supports source-only contract and does not explicitly bless new subdirs:
- .gitignore includes incoming/ess/** with exceptions only for:
  - incoming/ess/
  - incoming/ess/starmine/.gitkeep
  - incoming/ess/non_starmine_zacks/.gitkeep

## Directory Classification Table

| Directory | Purpose | Creator | Creation Trigger | Expected Lifetime | Safe To Delete (Y/N) |
|---|---|---|---|---|---|
| incoming/ess/_holding | Temporary manual staging/quarantine bucket used during ad-hoc movement | Manual terminal command in session (not pipeline stage) | Operator/assistant restage workflow | Ephemeral; no code dependency found | Y (if empty and not used by active manual workflow) |
| incoming/ess/processed | Ad-hoc archive of already-handled input files with timestamped batch folder | Manual terminal command in session (not pipeline stage) | Post-intake file movement/archive convenience step | Potentially persistent if used operationally, but not required by pipeline | Y (pipeline does not read it) |

## Answers to Part B Questions

1. When was _holding first created?
- 2026-06-17 06:09:59 local (filesystem birth timestamp).

2. When was processed first created?
- 2026-06-17 06:10:37 local (filesystem birth timestamp).

3. Which code path creates them?
- Not created by repository Python pipeline code; created by direct shell command in session transcript.

4. Which component owns them?
- Operational/manual workflow, not a declared SIH ingestion component.

5. Were they introduced by a recent code change?
- No evidence of a committed code change introducing them.

6. Are they temporary working directories?
- _holding: yes, temporary working/staging behavior.

7. Are they archival directories?
- processed: yes, operational archive semantics based on folder structure and command behavior.

8. Are they expected to persist?
- Not by formal intake contract; persistence is optional/manual, not architectural requirement.

## Part B Conclusion

The appearance of _holding and processed is attributable to manual operational handling during restage and is outside the formally defined intake directory contract used by the ESS intake stage.