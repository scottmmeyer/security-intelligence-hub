# Candidate Universe Lineage

This audit separates the holdings-facing refresh path from the candidate-facing recommendation path.

## Universe Map

| Universe | Count | Source files | Construction logic | Used for | Refresh dependency |
| --- | ---: | --- | --- | --- | --- |
| CW-DAS queue | 32 | [src/portfolio/deployment_queue.py](src/portfolio/deployment_queue.py), [src/portfolio/runner.py](src/portfolio/runner.py), [ui/portfolio_alignment/app.js](ui/portfolio_alignment/app.js) | Built from holdings, security overlays, alignment, strategic profiles, and policy state; ranked by deployment score. | New-capital deployment candidates | Rebuilt when the portfolio review/PAR bundle is regenerated. Not guaranteed by holdings-only refresh. |
| UCF verdicts | 76 | [src/portfolio/unified_conviction.py](src/portfolio/unified_conviction.py), [src/portfolio/runner.py](src/portfolio/runner.py), [ui/portfolio_alignment/app.js](ui/portfolio_alignment/app.js) | One verdict per holding, synthesized from overlays, strategic profiles, and the CW-DAS queue. | Security conviction ranking and review layers | Depends on CW-DAS plus overlays; rebuilt with the same review bundle. |
| CRA proposal | 27 sources / 31 deployments / 11 suppressed | [src/portfolio/cra/capital_source_builder.py](src/portfolio/cra/capital_source_builder.py), [src/portfolio/cra/rotation_proposal_builder.py](src/portfolio/cra/rotation_proposal_builder.py), [src/portfolio/cra/models.py](src/portfolio/cra/models.py), [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py) | Converts PAR artifacts into capital sources, deployment targets, and suppressed sources. | Capital rotation / deployment planning | Reads the latest PAR artifacts and portfolio state; refreshed when the review bundle is regenerated. |
| Portfolio Review / DOR | 751 records | [src/pis/dislocation_outcome_review.py](src/pis/dislocation_outcome_review.py), [scripts/run_outcome_ui.py](scripts/run_outcome_ui.py) | Builds DOR records from UCF history, attribution outcomes, and benchmark alpha. | Review / governance / outcome analysis | Rebuilt by the derived-artifact refresh, not by signal refresh alone. |
| Research universe | 2,473 symbols | [src/history/analytical_universe_manager.py](src/history/analytical_universe_manager.py), [data/current/analytical_universe.csv](data/current/analytical_universe.csv), [scripts/refresh_signals.py](scripts/refresh_signals.py) | Base universe merged with signal snapshot, provider data, benchmark assignment, and tier classification. | Recommendation context and replay evidence | The only mode that guarantees a full candidate-universe rebuild is `rebuild_research_universe`. |

## Key Takeaway

`portfolio_signals` is a holdings-first refresh. It is enough for the owned portfolio, but it does not guarantee that the recommendation universe is freshly rebuilt.
