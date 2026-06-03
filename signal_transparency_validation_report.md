# Signal Transparency Validation Report — Phase 7.5E

**Run Date:** 2025-06-01  
**Phase:** 7.5E — Signal Transparency Layer  
**Status:** ✅ COMPLETE — 27 tests passing, 1 skipped (integration requires live CSV), 0 regressions

---

## 1. Objective

Implement a Signal Transparency layer directly within the Capital Deployment Queue UI so that operators can understand why any candidate is ranked where it is — without navigating away from the deployment view.

**Target display per candidate (expanded row):**
- UCF Score, UCF Rank, UCF Label
- Composite Score, ESS Classification
- Danelfin Score, Zacks Rank
- Replay Supported / Replay Percentile
- Trim Score, Conviction Tier, Current Weight, Projected Weight
- UCF Signal Summary narrative
- CW-DAS Score Breakdown (existing — retained below Signal Profile)

---

## 2. Architecture Changes

### 2.1 Data Model — `src/portfolio/models.py`
| Model | Field Added | Type | Default |
|-------|------------|------|---------|
| `PortfolioHolding` | `danelfin_score` | `Optional[str]` | `None` |
| `SecurityIntelligenceOverlay` | `danelfin_score` | `Optional[str]` | `None` |

Both fields placed with default=None to maintain backward compatibility with all existing dataclass construction.

### 2.2 Enrichment Pipeline — `src/portfolio/enrichment.py`
Added `danelfin_score=u.get("danelfin_score") or None` to the `replace()` call in `enrich_holdings()`.  
Source: `data/current/analytical_universe.csv` column `danelfin_score`.

**Reference values confirmed:**
- AEIS: `danelfin_score = "4.0"`
- VRT: `danelfin_score = "3.5"`

### 2.3 Overlay Construction — `src/portfolio/recommendations.py`
Added `danelfin_score=h.danelfin_score` to the `SecurityIntelligenceOverlay(...)` constructor in `build_security_overlays()`. The overlay CSV writer uses `dataclasses.asdict()`, so the field is automatically included in new runs.

### 2.4 Enriched Drilldown — `src/portfolio/runner.py`
Added `"danelfin_score": _fld(overlay, "danelfin_score", "")` to `enriched_rows` dict (alongside `zacks_rating`, `ess_score_text`).

### 2.5 UCF Integration into Runner Pipeline — `src/portfolio/runner.py`
Phase 7.5E integrates UCF computation into `run_analysis()`:

```python
from .unified_conviction import build_ucf_verdicts, UCF_VERSION
```

After `deployment_plan.json` is written, the runner:
1. Calls `build_ucf_verdicts(profiles, overlays, dq_payload)` 
2. Serializes to `ucf_verdicts.json` alongside other run artifacts
3. Includes `"ucf_verdicts_by_symbol"` in the return dict

`load_analysis_run()` also loads `ucf_verdicts.json` when present (additive — absent for pre-7.5E runs, no error).

### 2.6 UI — `ui/portfolio_alignment/app.js`
`_dqRenderTableRows()` enhanced with Phase 7.5E signal maps built once per render:

```javascript
const _ucfBySymbol = (_analysisResult && _analysisResult.ucf_verdicts_by_symbol) || {};
const _ovBySymbol  = {};  // symbol → security_overlay row
const _dpBySymbol  = {};  // symbol → deployment_plan recommendation
```

Each expanded row (`.dq-breakdown-row`) now renders a **Signal Profile** section above the existing CW-DAS breakdown grid:

| Card | Source |
|------|--------|
| UCF Score | `ucf_verdicts_by_symbol[sym].ucf_score` |
| UCF Rank | `ucf_verdicts_by_symbol[sym].ucf_rank` |
| UCF Label | `ucf_verdicts_by_symbol[sym].ucf_label` |
| Composite | `queue[i].composite_score` |
| ESS | `security_overlays[sym].ess_score_text` |
| Danelfin | `security_overlays[sym].danelfin_score` (new runs) |
| Zacks | `security_overlays[sym].zacks_rating` |
| Replay Pctile | `security_overlays[sym].replay_percentile` |
| Proj. Weight | `deployment_plan.recommendations[sym].projected_weight_pct` |

UCF `signal_summary` renders as a highlighted narrative block between the signal grid and the CW-DAS breakdown.

### 2.7 CSS — `ui/portfolio_alignment/index.html`
New CSS classes added:
- `.dq-signal-profile-header` — section label (indigo, all-caps)
- `.dq-signal-grid` — 9-column responsive grid
- `.dq-sig-card` — individual signal card (white bg, border)
- `.dq-sig-card.dq-sig-ucf` — UCF-branded cards (light indigo accent)
- `.dq-sig-val`, `.dq-sig-val.dq-sig-rank`, `.dq-sig-val.dq-sig-label`
- `.dq-sig-lbl` — card label (muted, tiny caps)
- `.dq-signal-summary` — narrative block (indigo left-border, italic)

---

## 3. Test Results

**Test file:** `tests/test_7_5e_signal_transparency.py`  
**Tests:** 27 passed, 1 skipped

| Class | Tests | Result |
|-------|-------|--------|
| `TestModelFields` | 4 | ✅ PASS |
| `TestDanelfinPropagation` | 2 | ✅ PASS |
| `TestUCFLoadedByRunner` | 9 | ✅ PASS |
| `TestQueueOrderingUnchanged` | 4 | ✅ PASS |
| `TestSignalTransparencyCompleteness` | 7 | ✅ PASS |
| `TestUCFInRunnerPipeline` | 1 pass + 1 skip | ✅ PASS / ⏭ SKIP |

**Full suite:** 719 passed, 1 skipped, 50 warnings (up from 692 pre-7.5E)

---

## 4. Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Operator can understand candidate ranking from one screen | ✅ | Signal Profile shows UCF Score/Rank/Label + all source signals in expanded row |
| No navigation required to Security Intelligence Overlay | ✅ | ESS, Zacks, composite, replay percentile all rendered inline |
| No navigation required to Conviction Explainability cards | ✅ | UCF Label + Signal Summary + narrative_tier all rendered inline |
| Existing deployment queue ordering unchanged | ✅ | `TestQueueOrderingUnchanged` — AEIS rank 1, VRT rank 2, monotonic ranks confirmed |
| Existing recommendation logic unchanged | ✅ | No changes to `recommendations.py` scoring; danelfin added additive-only |
| Existing tests pass (692) | ✅ | Full suite: 719 passed (692 + 27 new), 0 regressions |
| UCF verdicts loaded in result | ✅ | `load_analysis_run()` loads `ucf_verdicts.json`; test confirmed |
| danelfin flows through pipeline | ✅ | `enrich_holdings()` → `PortfolioHolding` → `SecurityIntelligenceOverlay` |

---

## 5. Governance Notes

- **Additive-only:** danelfin_score and UCF verdicts are display-only; they do not affect ranking, scoring, or recommendations.
- **Backward-compatible:** All new fields have `Optional[str] = None` defaults; existing run artifacts load without error.
- **UCF written per run:** New runs generate `ucf_verdicts.json` automatically; pre-7.5E runs load it if present (e.g., Phase 7.7B output).
- **Danelfin in overlay CSV:** Written via `dataclasses.asdict()` for new runs. Reference run (`PAR-20260531-F794D952`) overlay CSV predates 7.5E; danelfin gracefully shows "—" in UI.

---

## 6. Reference Run Signal Profile Snapshot

**Run:** `PAR-20260531-F794D952`  
**AEIS — Signal Profile:**

| Signal | Value |
|--------|-------|
| UCF Score | 90.39 |
| UCF Rank | #2 |
| UCF Label | CORE CONVICTION LEADER |
| Composite | 4.71 |
| ESS | — (not populated in overlay) |
| Danelfin | — (pre-7.5E run) |
| Zacks | — (not populated in overlay) |
| Replay Pctile | — |
| Proj. Weight | 4.06% |
| Signal Summary | "AEIS — Core conviction leader: BULLISH signal, replay-backed, composite 4.71. Best deployment target." |

**VRT — Signal Profile:**

| Signal | Value |
|--------|-------|
| UCF Score | 90.27 |
| UCF Rank | #3 |
| UCF Label | CORE CONVICTION LEADER |
| Composite | 4.71 |
| ESS | VERY_BULLISH |
| Danelfin | — (pre-7.5E run) |
| Zacks | — |
| Replay Pctile | — |
| Proj. Weight | 4.76% |

**Ordering rationale visible to operator:** AEIS ranks above VRT due to higher CW-DAS score (95.56 vs 95.53). Both are CORE_CONVICTION_LEADER. VRT gets larger projected weight due to lower current position vs WARN threshold.
