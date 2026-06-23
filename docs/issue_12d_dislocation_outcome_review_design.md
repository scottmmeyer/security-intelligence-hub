# ISSUE-12D — Dislocation Outcome Review Panel: Design Document

**Status:** APPROVED FOR IMPLEMENTATION  
**Date:** 2026-06-15  
**Scope:** Read-only PIS governance panel. SIH/PIS boundary strictly preserved.

---

## 1. Required Questions — Answered

| # | Question | Answer |
|---|----------|--------|
| Q1 | Can DIL outcomes be reconstructed from existing PIS data? | **YES** — UCF verdicts persisted per PAR run in `ucf_verdicts.json` (78 verdicts/run × 19 canonical dates). Action attribution (PIS-008) already covers DIL source. Attribution outcomes and benchmark records exist. All reconstruction is from existing artifacts. |
| Q2 | Are schema changes required? | **NO** — New module reads `ucf_verdicts.json`, `action_attribution/attribution_cache.json`, `attribution/attribution_records.csv`, and `benchmark_attribution/recommendation_benchmark_records.csv`. No changes to any existing schema. |
| Q3 | Does this modify DIL? | **NO** — Read-only observation of DIL outputs. |
| Q4 | Does this modify CW-DAS? | **NO** |
| Q5 | Does this modify UCF? | **NO** |
| Q6 | Does this modify recommendation generation? | **NO** |
| Q7 | Does this preserve SIH/PIS separation? | **YES** — PIS observes and measures SIH outputs. No feedback path. No automatic tuning. All findings are governance artifacts for human review. |
| Q8 | Does this provide meaningful governance intelligence? | **YES** — Cohort performance by UCF label, follow vs. ignore outcome comparison, and missed winner identification are materially new governance insights. |
| Q9 | Does this identify opportunity-cost insights? | **YES** — "Top Missed Winners" panel identifies IGNORED DIL recommendations that subsequently showed positive outcomes. |
| Q10 | Does this improve accountability without automatic feedback loops? | **YES** — All output is observational/governance. No path exists from DOR findings to DIL or UCF parameter changes. |

---

## 2. Data Availability Audit

### 2.1 UCF Verdict History

**19 canonical dates** with `ucf_verdicts.json` artifacts.  
**~1,482 total UCF verdicts** (78 per run × 19 dates).  
**DIL-eligible labels:** CORE_CONVICTION_LEADER (BUY), HIGH_CONVICTION_ANCHOR (BUY), DEPLOYMENT_CANDIDATE (BUY), TRIM_WATCH (REDUCE).

**Available fields per verdict:**
- `symbol`, `ucf_label`, `ucf_score`, `ucf_rank`
- `source_signals.composite_score`, `signal_direction`, `narrative_tier`, `replay_supported`, `replay_percentile`, `cw_das_score`, `cw_das_rank`, `trim_priority_score`
- `conflict_flags` (advisory disagreement badges)
- `signal_summary` (human-readable one-liner)
- `deployment.deployment_eligible`, `deployment_blocked`

**NOT available:** Raw dislocation class (A1_FUNDAMENTAL_BEAT_DIVERGENCE, D1_REPLAY_SIGNAL_LAG, B2_ANALYST_AI_DIVERGENCE) is not persisted in PAR artifacts. Cohort analysis uses UCF label as the primary grouping dimension.

### 2.2 Action Attribution (PIS-008)

**4,728 DIL action attribution records** already computed.  
**5 FOLLOWED** (all WINNER outcomes) — 4,723 IGNORED.  
Existing `action_attribution/attribution_cache.json` is the authoritative source.

### 2.3 Performance Attribution

**28 matched attribution records** across all sources.  
**5 DIL records** with `outcome` field (all WINNER in current data).

### 2.4 Benchmark Attribution

**28 benchmark records** with `excess_return_pct` (alpha).  
Available fields: `symbol`, `recommendation_source`, `directional_return_pct`, `benchmark_return_pct`, `recommendation_excess_return_pct`.

---

## 3. Architecture

### 3.1 New Module

**File:** `src/pis/dislocation_outcome_review.py`

This module reads existing PIS artifacts and produces governance output. It is strictly read-only with respect to all upstream data.

**Public API:**
```python
def pis_dor_summary(repo_root) -> dict        # Summary cards
def pis_dor_cohorts(repo_root) -> dict         # UCF label cohort analysis
def pis_dor_recommendations(repo_root) -> dict # Per-recommendation outcome table
```

### 3.2 New API Endpoints (3)

| Endpoint | Returns |
|----------|---------|
| `GET /api/pis/dor/summary` | Summary cards: total DIL, followed/ignored, winners, avg alpha, observations |
| `GET /api/pis/dor/cohorts` | UCF cohort analysis: per-label win rate, follow rate, avg alpha |
| `GET /api/pis/dor/recommendations` | Per-DIL-recommendation outcome records |

### 3.3 New Dashboard Sections (4)

| Section Key | Content | Panel |
|-------------|---------|-------|
| `dorSummary` | Summary cards + observations | full-width |
| `dorCohorts` | UCF label cohort table | full-width |
| `dorMissedWinners` | Top missed winners | half |
| `dorFollowedWinners` | Top followed winners | half |

---

## 4. Cohort Definitions

Cohorts are defined by UCF label — the primary DIL classification output:

| Cohort | UCF Labels | DIL Direction |
|--------|-----------|---------------|
| CONVICTION_LEADER | CORE_CONVICTION_LEADER | BUY |
| HIGH_ANCHOR | HIGH_CONVICTION_ANCHOR | BUY |
| DEPLOYMENT | DEPLOYMENT_CANDIDATE | BUY |
| TACTICAL | TACTICAL_GROWTH | BUY (advisory) |
| MAINTAIN | MAINTAIN | — (hold) |
| TRIM | TRIM_WATCH | REDUCE |

Only CONVICTION_LEADER, HIGH_ANCHOR, DEPLOYMENT, and TRIM are actionable DIL direction labels.

---

## 5. Data Flow

```
ucf_verdicts.json (per PAR run)
    │  19 dates × 78 verdicts = 1,482
    ▼
build_ucf_history()
    │  {(symbol, date): UCFVerdict}
    │
    ├──► join action_attribution_cache.json (DIL source filter)
    │         {symbol: action_status, outcome}
    │
    ├──► join attribution_records.csv
    │         {symbol: directional_return_pct}
    │
    └──► join benchmark_records.csv
               {symbol: excess_return_pct}
                    │
                    ▼
             DORRecord per (symbol, date)
                    │
                    ▼
         cohort_analysis() + governance_observations()
                    │
                    ▼
              DOR API payloads
```

---

## 6. SIH/PIS Separation Enforcement

This module enforces the boundary by:
1. **Reading only** PAR artifacts (ucf_verdicts.json is a SIH output, read-only here)
2. **Writing only** to `data/history/pis/dor/` (PIS-owned derived artifacts)
3. **Producing only** governance observations — no scores, no tuning recommendations, no threshold suggestions
4. **Flagging governance** issues for human review (e.g., "Ignored CCL recommendations showed positive outcomes") without implying any automatic adjustment

---

## 7. Non-Goals

- No changes to UCF label computation
- No changes to DIL thresholds  
- No changes to CW-DAS
- No changes to action attribution (PIS-008 — already handles DIL)
- No automated feedback from outcome to recommendation engine
- No ML or predictive models
