# Source Control and Durability Policy

## Purpose
This document defines the SIH operating contract for what belongs in Git, what must remain outside Git, and how non-Git artifacts must be preserved.

This is the canonical policy for source-control and durability decisions.

## Core Categories

### TRACKED_SOURCE
Examples:
- src/
- production scripts
- tests
- schemas
- validators
- managers
- pipeline orchestration

Rule:
- Durable in Git and reviewed through normal source-control process.

### TRACKED_CONFIGURATION
Examples:
- config/
- registries
- policy YAML
- schemas/contracts
- .env.example

Rules:
- Non-secret configuration belongs in Git.
- Operational policy (for example ESS freshness limits) belongs in tracked config, not .env.
- .env.example contains variable names/placeholders only.

### TRACKED_DOCUMENTATION
Examples:
- docs/
- CONTRIBUTING.md
- operational runbooks
- recovery and durability documentation

Rule:
- Durable in Git; changes are reviewable and versioned.

### SECRET
Examples:
- .env
- API credentials

Rules:
- Never committed.
- Never staged.
- Never printed.
- Durable in secure secret storage outside Git.

### REGENERABLE_RUNTIME
Examples (as applicable):
- .venv/
- caches
- data/current/
- temporary diagnostics
- generated runtime views that can be rebuilt deterministically

Rule:
- Not committed.
- Must have a documented reconstruction path.

### EXTERNAL_REACQUIRABLE
Examples:
- FMP fetched datasets
- replaceable public/provider metadata
- other external provider outputs that can be fetched again

Rule:
- Generally not committed.
- Must document source/provider and reconstruction process.

### PRIVATE_DURABLE
Examples:
- operator state
- portfolio source inputs
- Fidelity statements/source documents
- private historical run evidence
- private provider captures when exact historical auditability matters
- non-regenerable historical provenance

Rule:
- Do not put private runtime data in Git merely for durability.
- Preserve via durable private storage/archive strategy outside Git.

### TEMPORARY
Examples:
- tmp_*
- scratch logs

Rule:
- Not committed; safe to delete only after explicit confirmation they are nonessential.

## Core Non-Git Rule
Every artifact outside Git must be classified as either:
- REGENERABLE
- DURABLE_OUTSIDE_GIT

There must be no third class of ignored artifact that has no durability decision.

Important:
- .gitignore means do not place this in Git.
- .gitignore does not mean safe to lose.

## Current SIH Path Policy

| Path | Source-control category | Normally tracked | Private | Regenerable | Durability requirement | Notes |
|---|---|---|---|---|---|---|
| .env | SECRET | No | Yes | No | DURABLE_OUTSIDE_GIT | Never stage/commit/print secret values. |
| .env.example | TRACKED_CONFIGURATION | Yes | No | n/a | Git durability | Placeholders only. |
| src/ | TRACKED_SOURCE | Yes | No | n/a | Git durability | Core application source. |
| scripts/ | TRACKED_SOURCE | Yes | Usually No | Mixed | Git for production scripts; classify scratch outputs | Production scripts tracked; scratch helpers may be TEMPORARY. |
| tests/ | TRACKED_SOURCE | Yes | No | n/a | Git durability | Deterministic validation assets. |
| config/ | TRACKED_CONFIGURATION | Yes | Usually No | n/a | Git durability | Policy and registries belong in Git. |
| docs/ | TRACKED_DOCUMENTATION | Yes | No | n/a | Git durability | Governance/runbook documentation. |
| data/current/ | REGENERABLE_RUNTIME | No | Context-dependent | Yes | REGENERABLE | Runtime current-state views are normally not committed and rebuilt from source inputs/history unless a specific artifact is deliberately and explicitly reclassified under this durability policy. Reclassification must be explicit, never inferred from convenience or usefulness. |
| data/history/ | PRIVATE_DURABLE or REGENERABLE_RUNTIME by lane | Mixed | Often Yes | Mixed | Classify each lane as REGENERABLE or DURABLE_OUTSIDE_GIT | Do not assume all history is disposable; some lanes are non-regenerable private provenance. |
| data/signals/ | EXTERNAL_REACQUIRABLE (default) | No (runtime payloads) | Sometimes | Often Yes | REGENERABLE or DURABLE_OUTSIDE_GIT per lane | Provider payloads usually reacquirable; private captures may be durable. |
| data/operator/ | PRIVATE_DURABLE | Usually No for live state | Yes | Usually No | DURABLE_OUTSIDE_GIT | Live operator decisions/drafts require private persistence. |
| data/incoming/ | TRACKED_CONFIGURATION for scaffolding; PRIVATE_DURABLE for private payloads | Mixed | Mixed | Mixed | Per-artifact classification required | Keep scaffolding/contracts tracked; classify payload durability explicitly. |
| incoming/ | EXTERNAL_REACQUIRABLE or PRIVATE_DURABLE by feed | Mixed | Mixed | Mixed | Per-feed classification required | Provider feeds may be reacquirable; portfolio uploads are private durable inputs. |
| data/portfolio_ingestion/ | PRIVATE_DURABLE (runtime outputs) | Usually No for run outputs | Yes | Mixed | DURABLE_OUTSIDE_GIT unless explicitly reproducible | Contains run evidence and private portfolio processing artifacts. |
| tmp_* | TEMPORARY | No | Usually No | Yes | REGENERABLE | Do not rely on tmp artifacts for durability. |
| .venv/ | REGENERABLE_RUNTIME | No | No | Yes | REGENERABLE | Recreate from dependency manifest. |

## Source-Change Workflow
Mandatory rule:
- Copilot/automation must not automatically commit source changes.

After any source-changing task, leave intended changes as MODIFIED and UNSTAGED unless user explicitly authorizes otherwise.

Task completion report must include:
1. REPO_PATH
2. BRANCH
3. HEAD
4. git status --short
5. modified files
6. concise diff summary
7. tests executed and results
8. files proposed for Git
9. files explicitly excluded from Git
10. proposed commit message
11. WAITING FOR COMMIT APPROVAL

Approval gates:
- Stage and commit only after explicit user approval.
- Pushing requires separate explicit user approval.
- A request to commit does not imply push authorization.

## Recovery Worktree Visibility Contract
Current SIH recovery layout:
- PRIMARY: /Users/scottmeyer/Projects/security-intelligence-hub
- RECOVERY: /Users/scottmeyer/Projects/security-intelligence-hub-recovery-pis006

Rules:
- Source recovery work occurs in RECOVERY.
- PRIMARY must not be modified unless explicitly authorized.
- During recovery, every source-changing task must begin and end by reporting:
  - REPO_PATH
  - BRANCH
  - HEAD
  - GIT_STATUS_SHORT

This prevents Git UI and worktree ambiguity.

## Enforcement Notes
- Do not change .gitignore solely to force durability.
- Solve durability through explicit classification and storage strategy.
- Keep private runtime data out of Git while still preserving it appropriately.
