# Upload Lifecycle Trace

## Current Flow
1. User uploads a Fidelity portfolio CSV in the Portfolio Alignment UI.
2. The browser posts the raw CSV to `POST /api/portfolio/analyze` in [scripts/run_outcome_ui.py](../../scripts/run_outcome_ui.py).
3. The runner calls `ingest_portfolio(...)` in [src/portfolio/ingestion.py](../../src/portfolio/ingestion.py).
4. The parser produces the canonical SIH portfolio contract:
   - `PortfolioSnapshot`
   - `list[PortfolioHolding]`
5. If ingestion fails, the upload is rejected and no PIS snapshot is created.
6. If ingestion succeeds, the SIH runner calls the PIS best-effort registration helper with the already-parsed snapshot and holdings.
7. SIH analysis continues through enrichment, alignment, recommendations, queue generation, and persistence.
8. PIS exposes a read-only status summary through `/api/pis/status`.

## Key Boundary
PIS does not reopen the uploaded file. It consumes the SIH parsed snapshot object and its holdings list directly.

## Analysis Start Point
Analysis generation begins immediately after `ingest_portfolio(...)` returns successfully inside `run_analysis(...)`.
