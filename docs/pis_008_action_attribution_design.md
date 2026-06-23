# PIS-008 — Recommendation Action Attribution & Lineage Closure: Design Document

**Status:** APPROVED FOR IMPLEMENTATION  
**Date:** 2026-06-15  
**Phase:** PIS-008  
**Scope:** Read-only analytical enhancement — no recommendation, scoring, or optimizer changes

---

## 1. Purpose

PIS currently answers "what changed?" and "what recommendation existed at the time?" via change detection and recommendation lineage. It does not answer whether the recommendation was followed, ignored, partially executed, or opposed, nor does it produce source-level accountability metrics.

PIS-008 closes the attribution loop by adding an **Action Attribution Engine** that classifies every recommendation-to-change pairing with an execution status, calculates response delay, and produces source-level effectiveness scorecards.

---

## 2. Required Questions — Answered

| # | Question | Answer |
|---|----------|--------|
| Q1 | Can recommendation-action attribution be reconstructed from existing data? | **YES** — lineage records (53 rows) already contain matched_recommendation_id, symbol, change_type, days_between. Unmatched changes (NONE confidence) are classified as IGNORED. PAR recommendations.json provides directionality. All needed fields exist. |
| Q2 | Are schema changes required? | **NO** — New module reads existing lineage_records.csv, change_records.csv, and PAR recommendations.json. Writes only to a new `data/history/pis/action_attribution/` directory. No changes to existing schemas. |
| Q3 | Does this alter recommendation generation? | **NO** |
| Q4 | Does this alter CW-DAS? | **NO** |
| Q5 | Does this alter PAP? | **NO** |
| Q6 | Does this alter CRA? | **NO** |
| Q7 | Does this alter DIL? | **NO** |
| Q8 | Does this alter benchmark attribution? | **NO** |
| Q9 | Does this materially improve lineage quality? | **YES** — Transforms 53 lineage records + 63 change records from raw data into FOLLOWED/IGNORED/OPPOSED/PARTIALLY_FOLLOWED/EXPIRED classification with confidence scoring and delay metrics. |
| Q10 | Does this create a complete Recommendation → Action → Outcome chain? | **YES** — Connects existing lineage (Recommendation → Change) with existing attribution (Change → Outcome) and adds the missing middle layer: was the change a FOLLOWED execution of the recommendation? |

---

## 3. Current State Audit

### 3.1 Available Data

| Source | Count | Key Fields |
|--------|-------|-----------|
| `change_records.csv` | 63 non-UNCHANGED records across 18 dates | symbol, change_type (NEW_POSITION/INCREASED/REDUCED/EXITED_POSITION), delta_quantity, delta_market_value, snapshot_date |
| `lineage_records.csv` | 53 total (28 matched, 25 NONE confidence) | symbol, change_type, matched_recommendation_id, confidence, days_between, recommendation_source |
| PAR `recommendations.json` | ~12 per date × 19 dates | recommendation_id, recommendation_type, affected_symbols, priority, confidence, created_at_utc |
| PAR `deployment_plan.json` | per date | symbol, suggested_add, current_weight_pct (BUY direction) |
| PAR `ucf_verdicts.json` | per date | symbol, ucf_label (CORE_CONVICTION_LEADER, TRIM_WATCH etc.) |

### 3.2 Current Lineage Confidence Distribution

| Confidence | Count | % |
|-----------|-------|---|
| MEDIUM (matched) | 27 | 51% |
| LOW (matched) | 1 | 2% |
| NONE (unmatched) | 25 | 47% |
| HIGH | 0 | 0% |

### 3.3 Attribution Gap Analysis

Current lineage does NOT:
- Classify whether a matched change was FOLLOWED, OPPOSED, or PARTIAL
- Classify NONE-confidence changes as IGNORED recommendations  
- Track recommendation expiry across observation windows
- Compute source-level follow/ignore/oppose rates
- Link action status to the existing outcome (WINNER/NEUTRAL/LOSER)

---

## 4. Architecture

### 4.1 New Module

**File:** `src/pis/action_attribution.py`

**Public API:**
```python
def pis_action_attribution_summary(repo_root) -> dict
def pis_action_attribution_recommendations(repo_root) -> dict
def pis_action_attribution_sources(repo_root) -> dict
```

**Read-only** with respect to all existing artifacts. Writes derived output to `data/history/pis/action_attribution/`.

### 4.2 New API Endpoints (3)

| Endpoint | Returns |
|----------|---------|
| `GET /api/pis/action-attribution/summary` | Summary cards: counts by status, source effectiveness overview |
| `GET /api/pis/action-attribution/recommendations` | Per-recommendation action status records |
| `GET /api/pis/action-attribution/sources` | Source-level effectiveness scorecards |

### 4.3 New Dashboard Sections (4)

| Section Key | Content |
|-------------|---------|
| `actionAttributionSummary` | Cards: FOLLOWED/IGNORED/OPPOSED/PARTIAL/EXPIRED counts |
| `actionAttributionTable` | Per-recommendation status table |
| `actionAttributionSources` | Source effectiveness scorecard |
| `actionAttributionMissed` | Top missed (IGNORED) recommendations with outcome |

---

## 5. Recommendation Inventory (Current Sources)

| Source | ID Pattern | Direction | Volume |
|--------|-----------|-----------|--------|
| PAP (Portfolio Analytics Platform) | `REC-*` with type PORTFOLIO_CONSTRUCTION_NARRATIVE, IMPROVE_REPLAY_ALIGNMENT, STRATEGIC_RETAIN_* | Mixed | ~4/run |
| PAP Allocation | `REC-*` with type INCREASE_UNDERWEIGHT, REDUCE_OVERWEIGHT | BUY/REDUCE | ~5/run |
| DEPLOYMENT_QUEUE | `DP-{run_id}-{n}-{symbol}` | BUY | varies |
| DIL (Dislocation/UCF) | `DIL-{run_id}-{symbol}` | BUY or REDUCE | varies |
| REDUCTION_QUEUE | `REC-*` with type strategic trim | REDUCE | ~2/run |

---

## 6. Attribution Windows

| Window | Days | Use |
|--------|------|-----|
| Immediate | 1 | Same next trading day |
| Short | 3 | Near-term execution |
| Standard | 7 | Weekly rebalancing cycle |
| Extended | 14 | Bi-weekly execution horizon |
| Maximum | 30 | Monthly review cycle |

A recommendation is EXPIRED if no matching action is observed within the maximum window (30 days) and no active position change for that symbol occurred.

---

## 7. Data Flow

```
PAR recommendations.json          lineage_records.csv
        │                                 │
        ▼                                 ▼
  build_recommendation_inventory    load_lineage_records
        │                                 │
        └──────────────┬──────────────────┘
                       ▼
          join on (symbol × recommendation_id)
                       │
                       ▼
          classify_action_status()
          ├── FOLLOWED
          ├── PARTIALLY_FOLLOWED  
          ├── OPPOSED
          ├── IGNORED
          └── EXPIRED
                       │
                       ▼
          attach_outcome()  (from attribution_records.csv)
                       │
                       ▼
          compute_source_scorecard()
                       │
                       ▼
          persist to action_attribution/
```

---

## 8. Non-Goals

- No changes to lineage matching algorithm
- No changes to recommendation generation
- No changes to change detection
- No changes to PAR analysis pipeline
- No re-scoring of any signals
- No ML or predictive models
