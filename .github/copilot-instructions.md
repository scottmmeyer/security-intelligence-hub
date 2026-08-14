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
