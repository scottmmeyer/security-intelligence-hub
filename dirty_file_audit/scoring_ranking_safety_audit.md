# Scoring & Ranking Safety Audit
# DIRTY-FILE-AUDIT-01 — 2026-06-22

## CRITICAL QUESTION: Do any dirty files modify scoring or ranking behavior?

### Answer: NO

No file in the working tree modifies ESS scoring, CW-DAS ranking, UCF ranking, recommendation generation, replay computation, or allocation calculation logic.

---

## Explicit Verification by System

### ESS Scoring
**Files examined**: src/portfolio/ess_coverage.py, src/models/provider_health_models.py, src/pipeline/stages/ess_intake_stage.py

**Verdict**: No ESS scoring changes.
- `ess_coverage.py`: New functions detect StarMine freshness for diagnostic/warning display only
- `provider_health_models.py`: Adds sub-count fields to warning model — diagnostic display only
- `ess_intake_stage.py`: ESS-INTAKE-ORDERING-01 affects merge ordering of same-day partitions — changes WHEN data enters the pipeline, not HOW it is scored

**ESS scores unchanged**: ✅ YES

---

### CW-DAS Rankings
**Files examined**: All dirty source files

**Verdict**: No CW-DAS changes.
- No file touches cw_das ranking logic
- `run_outcome_ui.py` reads `cw_das` data for transparency display only
- `ui/outcome_visualization` reads and displays CW-DAS candidate lists for freshness metrics — no write path

**CW-DAS rankings unchanged**: ✅ YES

---

### UCF Rankings
**Files examined**: All dirty source files

**Verdict**: No UCF changes.
- No file touches ucf ranking, verdict generation, or scoring weights
- `run_outcome_ui.py` reads ucf_verdicts.json for candidate count display — no write path
- `ui/ucf_operator_dashboard/index.html` +27/-11 lines — display formatting only

**UCF rankings unchanged**: ✅ YES

---

### CRA (Capital Rotation Advisor)
**Files examined**: src/portfolio/cra/capital_source_builder.py, src/portfolio/cra/models.py

**Verdict**: No CRA ranking or allocation changes.

**capital_source_builder.py** adds `_compute_source_intent()`:
```python
def _compute_source_intent(category, ess_score_text, signal_direction, sizing_pct) -> str:
    # Returns a human-readable label from existing fields
    # Does NOT modify: category selection, sizing_pct, drift_pct, ordering, filtering
```
The function reads existing record fields and returns a string label. It is called only to populate a new `source_intent` field in the record. No existing logic paths are modified.

**models.py** adds `SOURCE_INTENT_*` string constants and `source_intent: str = ""` field.
- `CapitalSourceRecord` is a frozen dataclass — the new field is additive with a default
- No existing consumers are broken
- No sorting or ranking logic uses `source_intent`

**CRA rankings unchanged**: ✅ YES

---

### Recommendations
**Files examined**: All dirty source files

**Verdict**: No recommendation generation changes.
- `run_outcome_ui.py` reads `recommendations.json` to count symbols for freshness display — no write path
- No recommendation generation, filtering, or ranking logic is touched

**Recommendation generation unchanged**: ✅ YES

---

### Allocation
**Files examined**: src/portfolio/enrichment.py (+1 line), config/allocation_policy.yaml

**enrichment.py** (+1 line): Minor field addition — not allocation calculation logic.

**allocation_policy.yaml** adds `signal_conflict` section:
```yaml
signal_conflict:
  significant_conflict_sell_ratio_pct: 15.0
  high_hold_ratio_pct: 50.0
```
These thresholds drive badge display in the conflict review panel only. They are not consumed by the allocation policy engine, CW-DAS, UCF, or CRA. The inline comment confirms this explicitly.

**Allocation calculations unchanged**: ✅ YES

---

### Replay
**Files examined**: All dirty source files

**Verdict**: No replay changes.
- `docs/replay_architecture_review.md` and `docs/replay_threshold_sensitivity.md` are documentation only
- No replay computation, replay matrix, or replay scoring code is touched

**Replay unchanged**: ✅ YES

---

## Final Safety Statement

**All 23 tracked modified files and all 166 untracked files have been analyzed. No file modifies ESS scoring, CW-DAS ranking, UCF ranking, recommendation generation, CRA allocation, or replay computation.**

The 2 "HIGH risk" classified files (CRA capital_source_builder.py and models.py) carry HIGH classification by topology (they touch CRA code) but carry ZERO actual scoring/ranking risk — both changes are additive display-only extensions.

**Repository is safe to proceed to commit staging.**
