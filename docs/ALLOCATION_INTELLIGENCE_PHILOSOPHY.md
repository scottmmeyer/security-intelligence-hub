# Allocation Intelligence Philosophy

## Purpose

The Allocation Intelligence system is the strategic portfolio construction engine of the Security Intelligence Hub (SIH). It translates investment research, empirical replay evidence, and governance guardrails into explicit, version-controlled, semi-automatically updated strategic allocation targets.

Every number in the system has a traceable rationale. Every change is proposed by the engine and confirmed by the human. Nothing auto-commits.

---

## Core Principles

### 1. Evidence Over Opinion

Strategic targets are not set arbitrarily. Each node in the hierarchy begins with a methodology seed — a research-grounded baseline documented in `config/allocation_methodology.yaml`. As replay evidence accumulates, the recalculation engine proposes evidence-weighted adjustments. The evidence scoring formula is:

```
evidence_weight = outperformance_persistence × (1 − volatility_penalty)
proposed_delta  = (evidence_weight − 0.5) × max_delta × 2
```

A neutral `evidence_weight` of 0.5 produces zero delta. Evidence must exceed a minimum threshold before any change is proposed.

### 2. Governance First

All proposed changes are constrained by `config/allocation_policy.yaml` before they can be committed. This includes:

- **Per-asset-class ceilings** (e.g. max digital assets pct = 8%)
- **Cash floor** — the portfolio always maintains minimum liquidity
- **Maximum recalculation delta** — single recalculation cannot move a node more than N% (prevents overcorrection from noisy evidence)
- **Minimum recalculation interval** — prevents churn from short-term noise
- **Concentration ceilings** — mega cap, micro cap, single asset class limits

The 8 validators (`src/allocation/validators.py`) must all pass before `--commit` is permitted.

### 3. Hierarchy Preserves Invariants

Every parent's children must sum to 100.0% (±0.01). When a recalculation adjusts one sibling, the engine proportionally renormalizes the remaining siblings to maintain the invariant. This is not optional — it is enforced by `validate_hierarchy_sums`.

### 4. Replay Sophistication Tiering

Not all nodes benefit equally from quantitative replay:

| Tier | Nodes | Approach |
|------|-------|----------|
| HIGH | Equity nodes (EQUITIES.*) | Full replay evidence pipeline |
| LOW  | Fixed income nodes | Methodology baseline only — macro and duration analysis |
| NONE | DIGITAL, COMMODITIES, CASH | Methodology baseline — no quantitative replay |

LOW and NONE nodes are excluded from evidence-driven recalculation. Their targets are stable until a human manually updates the methodology YAML.

### 5. Semi-Automated, Human-Confirmed

The engine's role is to *propose*. A human must run:

```bash
PYTHONPATH=. .venv/bin/python scripts/recalculate_allocation_targets.py --commit
```

The `--commit` flag triggers publishing to `data/current/` and archiving to `data/allocation/recalculation_snapshots/`. Without it, only `data/allocation/proposed/` is written.

---

## Architecture Summary

```
config/
  allocation_policy.yaml       ← governance guardrails
  allocation_methodology.yaml  ← research rationale per node
  allocation_dimensions.yaml   ← hierarchy tree (all 30 nodes)

src/allocation/
  models.py                    ← frozen dataclasses
  structural_policy.py         ← policy YAML loader
  dimensions_loader.py         ← hierarchy navigation
  methodology_loader.py        ← seed target extraction
  recalculation_engine.py      ← evidence scoring + delta proposal
  replay_integration.py        ← replay_inputs.csv → AllocationEvidence
  tactical_overlay.py          ← momentum overlays (equity only)
  validators.py                ← 8 validators

src/history/
  allocation_manager.py        ← save/publish/manifest

scripts/
  recalculate_allocation_targets.py  ← CLI entry point

data/
  current/
    strategic_allocation_targets.csv
    tactical_overlays.csv
    allocation_recommendation.csv
  allocation/
    recalculation_snapshots/   ← append-only JSON lineage
    evidence_history/          ← per-recalculation evidence archive
    proposed/                  ← pre-commit staging area
    manifest.json              ← recalculation history index

ui/allocation_intelligence/
  index.html + app.js          ← 9-section visualization page
```

---

## What This System Is Not

- **Not a trading system.** It outputs target allocations, not orders.
- **Not fully automated.** Human confirmation is required for every commit.
- **Not a portfolio tracker.** `PortfolioComparisonResult` is a placeholder for future work.
- **Not a factor model.** The recalculation engine uses replay performance, not a multi-factor risk decomposition.
