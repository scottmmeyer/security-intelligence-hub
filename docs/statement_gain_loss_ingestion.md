# Statement Gain/Loss Ingestion Runbook

## Incoming PDF Placement
- Place Fidelity statement PDFs, TXT, or MD files in incoming/fidelity_statements/.
- Supported inputs for ingestion are .pdf, .txt, and .md.

Legacy compatibility incoming folder remains supported via CLI override:
- data/incoming/fidelity_statements/

## Dry-Run Command
- Run dry-run before ingestion to confirm detected dates, output paths, history updates, and archive actions.

```bash
PYTHONPATH=. .venv/bin/python scripts/ingest_statement_gain_loss.py \
  --incoming-dir incoming/fidelity_statements \
  --output-root artifacts/statement_gain_loss \
  --raw-archive-root data/raw/fidelity_statements \
  --dry-run
```

## Ingestion Command
```bash
PYTHONPATH=. .venv/bin/python scripts/ingest_statement_gain_loss.py \
  --incoming-dir incoming/fidelity_statements \
  --output-root artifacts/statement_gain_loss \
  --raw-archive-root data/raw/fidelity_statements
```

Backward-compatible override example:

```bash
PYTHONPATH=. .venv/bin/python scripts/ingest_statement_gain_loss.py \
  --incoming-dir data/incoming/fidelity_statements \
  --output-root artifacts/statement_gain_loss \
  --raw-archive-root data/raw/fidelity_statements
```

Optional: add --move-processed to move files from incoming into raw archive instead of copying.

```bash
PYTHONPATH=. .venv/bin/python scripts/ingest_statement_gain_loss.py \
  --incoming-dir incoming/fidelity_statements \
  --output-root artifacts/statement_gain_loss \
  --raw-archive-root data/raw/fidelity_statements \
  --move-processed
```

When `--move-processed` is used and ingestion succeeds, each processed file is removed from
`incoming/fidelity_statements/` and moved to
`data/raw/fidelity_statements/YYYY-MM-DD/`.

## Artifact Locations
- Dated artifact JSON: artifacts/statement_gain_loss/YYYY-MM-DD/STATEMENT_GAIN_LOSS_YYYY-MM-DD.json
- Dated artifact Markdown: artifacts/statement_gain_loss/YYYY-MM-DD/STATEMENT_GAIN_LOSS_YYYY-MM-DD.md
- Degraded parse quarantine: artifacts/statement_gain_loss/YYYY-MM-DD/degraded/
- Latest JSON pointer/output: artifacts/statement_gain_loss/latest.json
- Latest Markdown pointer/output: artifacts/statement_gain_loss/latest.md
- History index: artifacts/statement_gain_loss/history/statement_gain_loss_index.json

## Raw Archive Behavior
- Default behavior is copy to data/raw/fidelity_statements/YYYY-MM-DD/.
- With --move-processed, files are moved instead of copied.
- Dry-run performs no copy/move/write actions.

## Parse Quality Gate and Promotion
- A snapshot is promoted to latest only when required statement completeness checks pass.
- If parse quality is degraded (for example, missing realized gain/loss totals), the snapshot is written under
  artifacts/statement_gain_loss/YYYY-MM-DD/degraded/ and is marked with `parse_status: degraded` and
  `promoted_to_latest: false`.
- Existing `latest.json` and `latest.md` are preserved when new parses are degraded.

## Privacy and Commit Guidance
- Raw broker PDFs may contain sensitive information.
- Do not commit raw PDFs unless explicitly approved.
- Prefer committing normalized artifacts and code changes only.

## Reporting-Only Usage Rules
- Statement-derived values are reporting-only context.
- Do not use statement-derived values to modify scoring, ranking, recommendations, allocation targets, deployment ordering, or execution logic.
- Endpoint and artifacts must continue to report scoring_impact as none.
