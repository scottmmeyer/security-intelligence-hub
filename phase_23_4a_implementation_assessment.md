# Phase 23.4A — Q7: Implementation Assessment
**DESIGN ONLY — NO IMPLEMENTATION**
**Generated:** 2026-06-04
**Baseline:** PAR-20260604-8DB0393D | 853 tests | 0 failures | 1 skip

---

## 1. Scope of Phase 23.5 Implementation

Phase 23.5 implements two potentially separable features:
1. **BLOCK DIAGNOSTICS** — Why Blocked + Evidence + How To Unblock (redesigned from Phase 23.4 design)
2. **NEXT BEST ACTION** — NBA panel + Suggested Alternatives table (new, from Phase 23.4A design)

This document assesses each independently, then jointly.

---

## 2. BLOCK DIAGNOSTICS Only (Phase 23.4 Design)

### 2.1 Files Touched

| File | Change Type | Change Scope |
|---|---|---|
| `ui/portfolio_alignment/app.js` | Modify | Add `_buildBlockDiagnostics(r)` function, render in card |
| `src/portfolio/optimizer.py` | Modify | Add `mandate_type`, `concentration_tolerance` to `_build_result()` output |
| `src/portfolio/runner.py` | Modify | Ensure `optimizer_metadata` fields flow to `recommendations.json` |
| Test files | Add | Unit tests for new `optimizer_metadata` fields |

### 2.2 Code Change Estimate

| File | Lines Changed (est.) | Complexity |
|---|---|---|
| `optimizer.py` `_build_result()` | ~8 lines | Low — add 2 dict keys |
| `runner.py` | ~0–5 lines | Low — likely already passes through |
| `app.js` `_buildBlockDiagnostics()` | ~80–120 lines | Medium — new function, DOM structure |
| `app.js` rendering integration | ~20–30 lines | Low — call function in right place |
| New tests | ~30–50 lines | Low — 2–4 new assertions |

**Total estimate:** ~150–200 lines new/modified code

### 2.3 Data Gap Remediation Required

From Phase 23.4 Phase 23.4 gap table:
- `mandate_type` → add to `optimizer.py` `_build_result()`
- `concentration_tolerance` → add to `optimizer.py` `_build_result()`
- `overlap_with_ow_pct` → add to `optimizer.py` ETF candidate scoring
- `ow_node_key` → add to `optimizer.py` ETF candidate scoring

These are all additive changes to existing dict structures. No scoring logic changes.

### 2.4 Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| `_build_result()` change breaks existing test assertions | LOW | Only additive fields — existing assertions unchanged |
| `optimizer_metadata` shape change breaks frontend parsing | LOW | New fields optional — UI checks for presence |
| ETF gate context fields may require non-trivial refactoring | MEDIUM | Candidate-level context must be preserved through gate |

**BLOCK DIAGNOSTICS effort:** **LOW-MEDIUM**

---

## 3. NEXT BEST ACTION (Phase 23.4A Design)

### 3.1 Files Touched — Python Side

**NONE.** Per Q2 assessment: NBA is generated at presentation time in `app.js` from existing pipeline outputs. No Python files are touched.

### 3.2 Files Touched — Frontend Side

| File | Change Type | Change Scope |
|---|---|---|
| `ui/portfolio_alignment/app.js` | Modify | `_buildNextBestAction()` function |
| `ui/portfolio_alignment/app.js` | Modify | `_renderBlockDiagnosticsPanel()` orchestration |
| `ui/portfolio_alignment/app.js` | Modify | Data loading: verify `deployment_queue.json` is available to recommendation cards |
| CSS (inline or stylesheet) | Add | New CSS classes from Q5 |

### 3.3 Data Loading Dependency

**Key question:** Is `deployment_queue.json` currently loaded and available in `app.js` at recommendation card render time?

From Phase 23.3 context: `app.js?v=9`. The UI renders the deployment queue section (CW-DAS queue). This means `deployment_queue.json` is already fetched. The question is whether it is accessible in the scope of the per-recommendation card renderer.

If not in scope: requires passing `deploymentQueue` as parameter to the card renderer function. Estimated change: ~15–20 lines.

### 3.4 Code Change Estimate — NBA

| Component | Lines Changed (est.) | Complexity |
|---|---|---|
| `_buildNextBestAction()` function | ~100–150 lines | Medium — decision tree over 4 blocker types |
| `_renderBlockDiagnosticsPanel()` | ~60–80 lines | Medium — HTML assembly |
| CSS new classes | ~80–100 lines | Low — straightforward styling |
| Deployment queue scope wiring | ~15–20 lines | Low |
| Data gap: `allocation_node` per candidate | ~20–30 lines | Low if added to Python output |

**Total NBA-only estimate:** ~275–380 lines new/modified code (frontend only)

---

## 4. Combined: DIAGNOSTICS + NEXT BEST ACTION

### 4.1 Total Files Changed

| File | Change Type |
|---|---|
| `src/portfolio/optimizer.py` | Add 4 fields to `_build_result()` |
| `src/portfolio/runner.py` | Minimal passthrough check |
| `ui/portfolio_alignment/app.js` | New functions + integration |
| CSS | New classes |
| Test files | ~4–6 new tests |

**Total files changed: 4–5**

### 4.2 Total Lines Changed

| Scope | Lines (est.) |
|---|---|
| Python backend (optimizer + runner) | 20–40 lines |
| Python tests | 30–50 lines |
| `app.js` new functions | 200–260 lines |
| `app.js` integration (wiring) | 35–50 lines |
| CSS | 80–100 lines |
| **TOTAL** | **365–500 lines** |

### 4.3 API Impact

**NONE.** There is no external API in this system. The UI reads JSON files from the PAR run directory. No endpoints change.

### 4.4 Data Model Impact

**Minimal.** Two types of change:
1. `optimizer_metadata` dict in `recommendations.json` gains 4 new optional fields (`mandate_type`, `concentration_tolerance`, `overlap_with_ow_pct`, `ow_node_key`)
2. `DeploymentCandidate` output in `deployment_queue.json` may gain `allocation_node` field (optional, Phase 23.5 can defer with fallback behavior)

Both are additive. No existing fields removed or renamed.

---

## 5. Effort Classification

| Scope | Effort | Rationale |
|---|---|---|
| BLOCK DIAGNOSTICS only | **LOW** | ~150–200 lines, mostly UI, 4 new optional backend fields |
| NBA only | **LOW-MEDIUM** | ~275–380 lines, frontend only, no backend changes |
| DIAGNOSTICS + NBA combined | **MEDIUM** | ~365–500 lines, 4–5 files, all changes are additive |

**Classification: MEDIUM**

The work is bounded and well-understood. There are no architectural changes, no scoring changes, no API changes. The risk of regression is LOW because all changes are additive. The constraint satisfaction (no changes to optimizer/CW-DAS/ESS/replay/conviction/mandate) is provably met: 0 scoring logic changes.

---

## 6. Sequencing Options

### Option 1: DIAGNOSTICS FIRST, NBA in follow-up

```
Phase 23.5: DIAGNOSTICS only (150–200 lines)
Phase 23.6: NBA panel (275–380 lines)
```
- Pros: Smaller Phase 23.5, testable diagnostics first
- Cons: Two deployment phases for what is logically one UX feature

### Option 2: DIAGNOSTICS + NBA in one phase

```
Phase 23.5: DIAGNOSTICS + NBA combined (365–500 lines)
```
- Pros: Single deployment, complete user experience
- Cons: Slightly larger scope for one phase

**Assessment:** Option 2 is preferred. The NBA and Diagnostics panels are tightly coupled in the UI — the section order depends on both existing. Delivering diagnostics without NBA means shipping a panel that's ordered wrong from the start and requires a second layout change in Phase 23.6.

---

## 7. Risk Log

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| `deployment_queue.json` not in scope at card render | MEDIUM | LOW | Pass as argument to renderer |
| `allocation_node` gap causes imprecise OW-node filtering | HIGH | LOW | Fallback: surface all top-5, add caveat note |
| CSS class names conflict with existing styles | LOW | LOW | Use `nba-` prefix namespace |
| `mandate_type` field not consistently set in optimizer | LOW | MEDIUM | Add defensive `|| "UNKNOWN"` fallback |
| New test assertions for optimizer_metadata fields break on edge cases | LOW | LOW | Use `.get()` pattern in tests |

---

## 8. What Is NOT Changed

This is the explicit non-change list — the constraint satisfaction record:

| Component | Changed? |
|---|---|
| `src/portfolio/optimizer.py` scoring logic | NO |
| `run_parallel_optimizer()` | NO |
| `_mandate_gate_for_node()` gate logic | NO |
| `score_security_candidate()` scoring | NO |
| `score_etf_candidate()` scoring | NO |
| `src/portfolio/mandate.py` | NO |
| `src/portfolio/deployment_queue.py` CW-DAS scoring | NO |
| `src/portfolio/recommendations.py` | NO |
| `src/portfolio/unified_conviction.py` | NO |
| `src/portfolio/operator_policy.py` | NO |
| ESS pipeline | NO |
| Replay engine | NO |
| Conviction model | NO |
| Any test regression from scoring changes | NO RISK |

---

## 9. Summary

| Dimension | Assessment |
|---|---|
| Effort | MEDIUM (~365–500 lines, 4–5 files) |
| Backend changes | MINIMAL (4 additive fields in optimizer_metadata) |
| Frontend changes | MEDIUM (~300+ lines new JS + CSS) |
| Scoring impact | ZERO |
| API impact | NONE |
| Regression risk | LOW (all additive) |
| Recommended sequencing | DIAGNOSTICS + NBA in one phase (Phase 23.5) |

**Status: Q7 COMPLETE — IMPLEMENTATION ASSESSMENT CERTIFIED**
