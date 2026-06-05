# Phase 23.6B — Validation Results

**Date:** 2026-06-04
**Portfolio:** PAR-20260604-3565A7CD (2026-06-04 snapshot, $472,454 MV)

---

## Validation Checklist

| # | Criterion | Result | Detail |
|---|-----------|--------|--------|
| 1 | TSLA appears blocked | ✅ PASS | `blocked_by_policy=True`, `policy_type=DO_NOT_SELL`, shown in sources column with 🔒 badge and MONITOR ONLY label |
| 2 | FIS appears as source candidate | ✅ PASS | `category=SIGNAL_DETERIORATION`, `priority=HIGH`, `tax_bucket=A` (unrealized loss ~$12,594) |
| 3 | VRT appears as deployment target | ✅ PASS | `rank=1`, `deployment_score=95.14`, `suggested_amount=$49,506` |
| 4 | ARW appears as deployment target | ✅ PASS | `rank=2`, `deployment_score=93.92`, `suggested_amount=$49,506` |
| 5 | Capital pool renders correctly | ✅ PASS | `total_capital_pool=$99,011.20` (39 sources, 28 unblocked) |
| 6 | Impact estimates render | ✅ PASS | Alignment 0.4142 → 0.5542 (+0.14 est.), Concentration shown |
| 7 | ESTIMATE ONLY banner present | ✅ PASS | `is_estimate=True` always; yellow ⚠ banner in impact column |
| 8 | Proposal status badge | ✅ PASS | OPERATOR_REVIEW_REQUIRED badge shown with review flags |
| 9 | CW-DAS ordering preserved | ✅ PASS | VRT(#1) then ARW(#2); no re-ranking in UI |
| 10 | No backend modifications | ✅ PASS | 928 tests pass, 0 regressions |

---

## API Validation Results (live)

```
GET /api/cra/proposal → HTTP 200

proposal_id:       CRA-20260604-2844185D
proposal_status:   OPERATOR_REVIEW_REQUIRED
cra_version:       1.0
source_count:      39
deployment_count:  2
total_capital_pool: $99,011.20

review_flags:
  - "Capital pool (20.7% of portfolio) exceeds 10% threshold — operator review recommended"

Sources (top 5):
  TSLA  SIGNAL_DETERIORATION  URGENT  blocked=True   tax=C
  FIS   SIGNAL_DETERIORATION  HIGH    blocked=False  tax=A  (harvest opp.)
  KGC   SIGNAL_DETERIORATION  HIGH    blocked=False  tax=C
  HUBS  SIGNAL_DETERIORATION  HIGH    blocked=False  tax=D
  SNA   SIGNAL_DETERIORATION  HIGH    blocked=False  tax=C

Deployments:
  #1  VRT   DAS=95.14  $49,506  CCL   3.85% → 5.90%
  #2  ARW   DAS=93.92  $49,506  HCA   2.20% → 3.25%

Impact (estimate):
  Alignment:     0.4142 → 0.5542  (+0.1400)
  Concentration: 27.50% → 17.50%  (−10.00%)
  is_estimate:   True ✓
```

---

## UI Render Validation (structural)

Verified via `node` script checking `app.js` and `index.html`:

| Check | Result |
|-------|--------|
| `loadCRAProposal` function defined | ✅ FOUND |
| `_renderCRAProposal` function defined | ✅ FOUND |
| `_craBuildSourcesCol` function defined | ✅ FOUND |
| `_craBuildRotationMapCol` function defined | ✅ FOUND |
| `_craBuildImpactCol` function defined | ✅ FOUND |
| `_craBuildSourceCard` function defined | ✅ FOUND |
| `_craBuildTargetCard` function defined | ✅ FOUND |
| `_craFmt` function defined | ✅ FOUND |
| `loadCRAProposal()` in `renderResults` | ✅ FOUND |
| `id="craSection"` in HTML | ✅ FOUND |
| `id="craContent"` in HTML | ✅ FOUND |
| `.cra-panel` CSS defined | ✅ FOUND |
| `.cra-columns` CSS defined | ✅ FOUND |
| `app.js?v=11` script tag | ✅ FOUND |

---

## Regression Check

**Full test suite:** `PYTHONPATH=. .venv/bin/python3 -m pytest -q`

**Result: 928 passed, 1 skipped, 0 failed** (41.42s)

Zero regressions introduced by Phase 23.6B UI changes.
