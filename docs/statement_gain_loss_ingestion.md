# Statement Gain/Loss Ingestion Runbook

## Incoming PDF Placement
- Place Fidelity statement PDFs in data/incoming/fidelity_statements/.
- Supported inputs for ingestion are .pdf, .txt, and .md.

## Dry-Run Command
- Run dry-run before ingestion to confirm detected dates, output paths, history updates, and archive actions.

```bash
PYTHONPATH=. .venv/bin/python scripts/ingest_statement_gain_loss.py \
  --incoming-dir data/incoming/fidelity_statements \
  --output-root artifacts/statement_gain_loss \
  --raw-archive-root data/raw/fidelity_statements \
  --dry-run
```

## Ingestion Command
```bash
PYTHONPATH=. .venv/bin/python scripts/ingest_statement_gain_loss.py \
  --incoming-dir data/incoming/fidelity_statements \
  --output-root artifacts/statement_gain_loss \
  --raw-archive-root data/raw/fidelity_statements
```

Optional: add --move-processed to move files from incoming into raw archive instead of copying.

## Artifact Locations
- Dated artifact JSON: artifacts/statement_gain_loss/YYYY-MM-DD/STATEMENT_GAIN_LOSS_YYYY-MM-DD.json
- Dated artifact Markdown: artifacts/statement_gain_loss/YYYY-MM-DD/STATEMENT_GAIN_LOSS_YYYY-MM-DD.md
- Latest JSON pointer/output: artifacts/statement_gain_loss/latest.json
- Latest Markdown pointer/output: artifacts/statement_gain_loss/latest.md
- History index: artifacts/statement_gain_loss/history/statement_gain_loss_index.json

## Raw Archive Behavior
- Default behavior is copy to data/raw/fidelity_statements/YYYY-MM-DD/.
- With --move-processed, files are moved instead of copied.
- Dry-run performs no copy/move/write actions.

## Privacy and Commit Guidance
- Raw broker PDFs may contain sensitive information.
- Do not commit raw PDFs unless explicitly approved.
- Prefer committing normalized artifacts and code changes only.

## Reporting-Only Usage Rules
- Statement-derived values are reporting-only context.
- Do not use statement-derived values to modify scoring, ranking, recommendations, allocation targets, deployment ordering, or execution logic.
- Endpoint and artifacts must continue to report scoring_impact as none.
