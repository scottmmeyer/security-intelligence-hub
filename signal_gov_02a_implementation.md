# SIGNAL-GOV-02A Implementation — Advisory Conflict Badges

**Date:** 2026-06-15  
**Status:** COMPLETE

---

## Scope Delivered (Option B Advisory Only — Exact as Approved)

| Item | Status |
|------|--------|
| `src/portfolio/signal_conflict_classifier.py` | ✅ Created |
| `classify_signal_conflicts()` — all 5 badge types | ✅ Implemented |
| `get_conflicts_for_symbols()` — batch API | ✅ Implemented |
| `config/allocation_policy.yaml` — `signal_conflict` section | ✅ Added |
| `GET /api/signal-conflicts?symbols=...` | ✅ Live |
| Deployment queue card badges | ✅ Rendered |
| Signal profile panel badges | ✅ Rendered |
| CSS for WARN/INFO badge styles | ✅ Added |
| Operator annotation support (`config/signal_conflict_annotations.csv`) | ✅ Supported |
| 27 regression tests | ✅ All passing |
| No scoring changes | ✅ Confirmed |
| No ranking changes | ✅ Confirmed |
| No recommendation changes | ✅ Confirmed |

---

## Files Changed

### New
- `src/portfolio/signal_conflict_classifier.py` — classifier module
- `tests/test_signal_gov_02a_conflict_classifier.py` — 27 regression tests

### Modified
- `config/allocation_policy.yaml` — `signal_conflict` thresholds section
- `scripts/run_outcome_ui.py` — `GET /api/signal-conflicts` route
- `ui/portfolio_alignment/app.js` — `_signalConflictBadgesHtml()`, `_loadSignalConflicts()`, render calls
- `ui/portfolio_alignment/index.html` — `.gov02-conflict-badge`, `.gov02-badge-warn`, `.gov02-badge-info` CSS

### Unchanged
- All recommendation logic (`runner.py`, `analytical_universe_manager.py`)
- All scoring logic (CW-DAS, composite score, signal weights)
- All CPV rules (`compliance_validator.py`)
- All attribution and PIS pipeline files
- `drift_analyzer.py` (PA-006A)

---

## Module Design: `signal_conflict_classifier.py`

### `SignalConflict` dataclass
```python
@dataclass(frozen=True)
class SignalConflict:
    type: str        # CONFLICTING_SIGNAL | HIGH_ANALYST_DISAGREEMENT | ...
    severity: str    # WARN | INFO
    description: str # human-readable one-liner
```

### `classify_signal_conflicts(inputs, thresholds)` → `list[SignalConflict]`

Evaluation order (priority — higher suppresses lower):

1. **SIGNIFICANT_CONFLICT** — sell_ratio ≥ configured threshold (default 15%)
2. **HIGH_ANALYST_DISAGREEMENT** — sell_ratio ≥ 10% AND buys present OR operator annotation; suppressed if SIGNIFICANT_CONFLICT already active
3. **CONFLICTING_SIGNAL** — at least one bullish source AND one bearish source; suppressed if either level-2/3 already active
4. **HOLD_CONSENSUS** — FMP `consensus_label` == "HOLD" or "SELL"
5. **HIGH_HOLD_RATIO** — hold_count/total_analysts ≥ 50%; suppressed if HOLD_CONSENSUS active

Severity: CONFLICTING_SIGNAL, HIGH_ANALYST_DISAGREEMENT, SIGNIFICANT_CONFLICT = **WARN**; HOLD_CONSENSUS, HIGH_HOLD_RATIO = **INFO**

### Operator annotation file
`config/signal_conflict_annotations.csv` (created manually):
```csv
symbol,reason
NUE,Trading Central (98)=Buy vs Refinitiv/Verus (86)=Sell — operator verified 2026-06-15
```
If this file exists and contains a symbol, that symbol receives `HIGH_ANALYST_DISAGREEMENT` regardless of auto-detect criteria.

---

## API Endpoint

### GET `/api/signal-conflicts?symbols=VRT,NUE,PCB`

```json
{
  "conflicts": {
    "VRT":  [],
    "NUE":  [{"type": "CONFLICTING_SIGNAL", "severity": "WARN", "description": "At least one bullish and one bearish source are present."}],
    "PCB":  [{"type": "HOLD_CONSENSUS", "severity": "INFO", "description": "Street consensus is HOLD across 5 analysts."}]
  }
}
```

Symbols are returned uppercase. Unknown symbols or missing signal data return `[]` (no crash).

---

## Live API Verification (2026-06-15)

```
GET /api/signal-conflicts?symbols=NUE,MTZ,PCB,TSLA,VRT,SANM

MTZ:  [clean]
NUE:  [('CONFLICTING_SIGNAL', 'WARN')]       ← 3/32 sell votes
PCB:  [('HOLD_CONSENSUS', 'INFO')]            ← consensus_label=HOLD
SANM: [('HIGH_ANALYST_DISAGREEMENT', 'WARN'), ('HIGH_HOLD_RATIO', 'INFO')]  ← 2/17 sells (11.8%) + 10/17 holds
TSLA: [('SIGNIFICANT_CONFLICT', 'WARN')]      ← 15/81 sells = 18.5%
VRT:  [clean]
```

All results consistent with SIGNAL-GOV-02 design analysis.

---

## Configuration

```yaml
# config/allocation_policy.yaml
signal_conflict:
  significant_conflict_sell_ratio_pct: 15.0  # SIGNIFICANT_CONFLICT badge threshold
  high_hold_ratio_pct: 50.0                  # HIGH_HOLD_RATIO badge threshold
```

No scoring or ranking thresholds are configurable here — only advisory badge visibility thresholds.

---

## Dashboard Rendering

Badges appear in two locations in the deployment queue UI:

1. **Queue card** (`da-action-card`) — below the reason chips strip
2. **Signal profile expansion panel** — below the UCF summary, above the analyst agreement panel

Badge HTML example:
```html
<div class="gov02-conflict-strip">
  <span class="gov02-conflict-badge gov02-badge-warn" title="At least one bullish...">CONFLICTING SIGNAL</span>
</div>
```

Badges load asynchronously after analysis renders — if the API call is slow, the UI shows without badges first, then re-renders with badges when data arrives. No blocking.
