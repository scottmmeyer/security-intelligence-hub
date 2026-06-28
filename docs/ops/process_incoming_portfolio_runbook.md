# Process Incoming Portfolio Runbook

## Purpose

`scripts/process_incoming_portfolio.py` is an operator utility for controlled processing of incoming portfolio CSV files from `incoming/portfolio`.

It provides date-gated execution, dry-run preview, and guarded all-dates behavior.

## When To Use

- You need to process one or more incoming portfolio CSV files through the standard `run_analysis(...)` pipeline.
- You need deterministic date gating tied to filename date tokens.
- You need a preview (`--dry-run`) before execution.

## When Not To Use

- You need to change scoring, ranking, recommendation, allocation, or execution algorithms.
- You need to run a full-universe refresh or directly manage refresh internals.
- You need ad hoc data correction that is outside standard ingestion flow.

## Expected Incoming Folder

- Input directory: `incoming/portfolio`
- File type: `.csv` only
- Filename date token expected: `Mon-DD-YYYY` (example: `Portfolio_Positions_Jun-27-2026.csv`)

Files without parseable filename date tokens are skipped with reason output.

## Default Target-Date Behavior

- Default gate is `--target-date` = today's date in `YYYY-MM-DD` format.
- Only files whose filename date equals target date are selected.

## Dry-Run Examples

```bash
PYTHONPATH=. .venv/bin/python scripts/process_incoming_portfolio.py --dry-run
```

```bash
PYTHONPATH=. .venv/bin/python scripts/process_incoming_portfolio.py \
  --target-date 2026-06-27 \
  --dry-run
```

## Single-Date Processing Example

```bash
PYTHONPATH=. .venv/bin/python scripts/process_incoming_portfolio.py \
  --target-date 2026-06-27 \
  --mandate-type CONCENTRATED_ALPHA
```

## All-Dates Warning And Confirmation

`--all-dates` is high-impact and can process many files.

- Non-dry-run requires `--confirm-all-dates`.
- Dry-run does not require confirmation.

Examples:

```bash
# Preview all parseable files
PYTHONPATH=. .venv/bin/python scripts/process_incoming_portfolio.py \
  --all-dates --dry-run
```

```bash
# Execute all parseable files (explicit confirmation required)
PYTHONPATH=. .venv/bin/python scripts/process_incoming_portfolio.py \
  --all-dates --confirm-all-dates
```

## Side Effects

This utility calls `run_analysis(...)` for selected files.

Standard pipeline side effects may occur, including:

- ingestion and artifact writes
- best-effort PIS snapshot registration
- post-ingestion refresh behavior triggered by normal orchestration

## Avoiding Conflict With Active Refresh Windows

- Prefer `--dry-run` first to confirm scope.
- Avoid non-dry-run execution during active high-volume refresh windows.
- Prefer single-date execution when possible.
- If a refresh job is currently active, defer non-urgent bulk ingestion.

## Output And Exit Behavior

Utility prints:

- selected files
- processed results
- skipped files with reasons
- failed files with reasons
- summary counts (`processed`, `failed`, `skipped`, `dry_run`, etc.)

Exit codes:

- `0` if selected processing succeeds (or dry-run succeeds)
- `1` if one or more selected files fail during processing
- non-zero (`2`) for invalid guarded inputs (for example invalid `--target-date`, unconfirmed `--all-dates`)

## Validation Commands

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_process_incoming_portfolio.py -v
```

```bash
PYTHONPATH=. .venv/bin/python -m py_compile scripts/process_incoming_portfolio.py
```

## Rollback / Escalation Guidance

- Stop execution if repeated file failures occur.
- Capture terminal output for failed filenames and reasons.
- Escalate to ingestion/portfolio pipeline owners with:
  - command used
  - selected target date
  - failed file list
  - error reasons
- Do not bypass guardrails by editing utility behavior during active incident response.

## Governance Boundary Confirmation

This utility does not introduce scoring, ranking, recommendation, allocation, or execution algorithm logic.
It is orchestration tooling that invokes existing pipeline behavior.
