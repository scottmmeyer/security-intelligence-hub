# Copilot Operational Instructions

## Git visibility
At task start and task end report:
- REPO_PATH
- BRANCH
- HEAD
- GIT_STATUS_SHORT

## No automatic source commits
- Never stage source changes unless explicitly authorized by the user.
- Never commit source changes unless explicitly authorized by the user.
- A user authorization to commit does not authorize push.
- Never push unless the user separately and explicitly authorizes the push.
- Source-changing tasks must end with modified unstaged files plus:
  - REPO_PATH
  - BRANCH
  - HEAD
  - GIT_STATUS_SHORT
  - modified and added files
  - concise diff summary
  - tests and validation run
  - files proposed for source control
  - files excluded from source control
  - proposed commit message
  - WAITING FOR COMMIT APPROVAL

## Runtime-data rule
- Do not add ignored or private runtime artifacts to Git simply to preserve them.
- Classify non-Git state as either:
  - REGENERABLE
  - DURABLE_OUTSIDE_GIT

## Recovery worktree
- Use /Users/scottmeyer/Projects/security-intelligence-hub-recovery-pis006 for current SIH recovery work.
- Do not modify /Users/scottmeyer/Projects/security-intelligence-hub unless explicitly authorized.

## Secrets
- Never stage .env.
- Never expose secret contents.

## Incoming folder processing contract
- Treat "process the incoming folder" as an intent that requires routing, not as a single blind command.
- First inventory and classify current incoming artifacts before processing.
- Do not guess artifact class from one generic processor invocation.

### When user says "process the incoming folder"
- Inventory files recursively under incoming.
- Classify each file by established repo contracts.
- Route each supported class to its own entrypoint.
- Keep unsupported files untouched and report classification.

### ESS / LSEG input routing
- ESS examples include files under:
  - incoming/ess/starmine/
  - incoming/ess/non_starmine_zacks/
- For ESS inputs, use: `python scripts/_run_intake.py`
- Do NOT use: `scripts/process_incoming_portfolio.py` for ESS files.
- Do NOT invoke `execute_ess_intake_stage` directly from ad-hoc Python snippets when the wrapper exists.

### Portfolio input routing
- For eligible portfolio CSVs under the portfolio incoming contract, use: `python scripts/process_incoming_portfolio.py`
- Do NOT route ESS/LSEG files through the portfolio processor.

### Support / unknown files
- Do not process unsupported artifacts such as .DS_Store, .gitkeep, or unknown/unclassified files.
- Classify and report unsupported artifacts; leave them untouched.

### Mixed incoming content
- If incoming contains multiple artifact classes:
  - inventory files
  - classify files
  - process each supported class with its own established entrypoint
  - do not feed all files through one processor

### Safety limits for "process the incoming folder"
- This phrase does not by itself authorize provider refresh.
- This phrase does not by itself authorize portfolio Analyze.
- This phrase does not by itself authorize replay rebuild.
- This phrase does not by itself authorize allocation recalculation.
- This phrase does not by itself authorize source-code changes.
- This phrase does not by itself authorize commits.
- This phrase does not by itself authorize pushes.
- If ESS intake completes and portfolio Analyze may be useful, report it as a separate next step and wait for authorization.

## Direct ESS operator command contract
- When the user explicitly asks to process ESS files (for example: "process the ESS files", "ingest today's ESS", "run intake", "process EquitySummaryScores", or "process the StarMine incoming files") and readiness requirements are met, use:
  - `python scripts/_run_intake.py`
- Do not substitute `process_incoming_portfolio.py` for ESS intake.
