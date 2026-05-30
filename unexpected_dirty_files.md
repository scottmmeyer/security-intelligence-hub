# Unexpected Dirty Files — Phase SC-H1

**Generated:** 2026-05-30  
**Definition:** Files modified or created that do not correspond to any named phase deliverable (6.1–7.3B or WP-05D), or whose presence is unexplained.

---

## Tier 1 — ACCIDENTAL (delete immediately, no investigation needed)

| File | Evidence | Action |
|---|---|---|
| `xyz` | 0-byte empty file. Not referenced anywhere. No plausible purpose. Almost certainly a stray shell accident (`touch xyz`, `> xyz`, etc.) | DELETE |

---

## Tier 2 — UNEXPECTED MODIFIED TRACKED FILES

These are tracked files that carry unexplained diffs — they belong to prior WP phases but have lingering modifications not clearly attributable to a named Phase 6/7 deliverable.

| File | Δ Lines | Concern | Assessment |
|---|---|---|---|
| `src/history/base_universe_manager.py` | +1 | Single-line addition to a pre-6.x module | Low risk. Likely a minor compatibility fix (field addition or import) made during Phase 6.x integration. Review diff before commit. |
| `src/normalize/provider_normalizer.py` | +1 | Single-line addition | Same pattern as above. Likely a minor integration fix. Review diff before commit. |
| `src/models/canonical_models.py` | +3 | 3-line addition to core canonical model | Low risk. Likely a field added for Phase 6.x compatibility. Canonical models are extended across all phases. |
| `scripts/diagnostics/build_wp04_foundation.py` | +6 | Modification to WP-04 diagnostic | The WP-04 diagnostic script was modified post-commit. Likely adjusted to work with the Phase 6.x portfolio ingestion API changes. |
| `scripts/diagnostics/build_wp05b_replay_matrix.py` | +26 | Modification to WP-05B diagnostic | The WP-05B matrix builder received a larger +26 change. Likely adapted to produce data for Phase 7.x allocation alignment testing. |
| `scripts/score_lookup.py` | +13 | Score lookup utility modified | Likely extended to support Phase 6.x/7.x composite scoring. Not a named deliverable on its own. |

**Assessment:** None of these constitute an alarming accidental modification. All are plausibly integration-glue changes made while building Phase 6/7 features. They should be diffed individually before including in a commit.

---

## Tier 3 — UNTRACKED FILES WITHOUT A CLEAR PHASE OWNER

Files that exist in the working tree but cannot be definitively assigned to a specific numbered phase based on available documentation.

| File | Concern | Assessment |
|---|---|---|
| `scripts/compare_zacks_ess_vs_internet.py` | No named phase for a Zacks-vs-Internet comparison utility | Likely a diagnostic created during Phase 6.x signal validation. Not a committed operational tool. Should be archived or deleted. |
| `scripts/refresh_signals.py` | Two signal refresh scripts exist (`refresh_signals.py` and `refresh_portfolio_signals.py`) | Possible duplication or iteration. Unclear which is canonical. Investigate before commit. |
| `scripts/_portfolio_philosophy_validation.py` | Not clearly tied to a specific phase deliverable | Created during Phase 7.x as a philosophical consistency check. Superseded by formal reports. Archive or delete. |
| `data/derived/phase7_audit_data.json` | JSON artifact with no clear owner script | Produced by `scripts/_phase7_build_data.py` (itself a temp script). Ephemeral. Gitignore and delete. |
| `docs/recommendation_flow_analysis.md` | Not a defined deliverable for any listed phase | Likely created as scratch analysis during Phase 7.0/7.1 decision-making. Retain if it contains design rationale; delete if superseded by formal docs. |
| `tests/test_cash_semantics.py` | Phase attribution unclear — cash semantics tests not tied to a specific named phase | Likely Phase 7.x alignment/recommendation work. Low risk — all tests pass. Verify this was intentional. |
| `scripts/research/` (2 files) | `research/` scripts not tied to any named deliverable | Created during Phase 6.4 effectiveness work. Keep if factor research is ongoing; archive if complete. |

---

## Tier 4 — EXPECTED BUT WORTH REVIEWING BEFORE COMMIT

These files are expected products of named phases but contain elements that should be reviewed before committing (e.g., may contain hardcoded values, debug prints, or temporary workarounds).

| File | Reason for Review |
|---|---|
| `scripts/run_outcome_ui.py` | +414 lines — large delta; contains POST /api/portfolio/analyze, GET /api/portfolio/runs handlers; confirm no debug prints, no hardcoded paths, error handling complete |
| `src/history/analytical_universe_manager.py` | +364 lines — large delta to a pre-Phase-6 module; verify additions are clean and not experimental |
| `ui/outcome_visualization/app.js` | +784 lines — WP-05D stock replay UI additions; confirm no debug console.log statements |
| `ui/portfolio_alignment/app.js` | Major file (Phase 6.1–7.3B span); confirm no leftover debug code from any phase |
| `src/portfolio/runner.py` | Spans Phase 7.0–7.3A; optimizer injection in Phase 7.3A was additive but runner.py is large and has had multiple passes |

---

## Summary

| Tier | Count | Action |
|---|---|---|
| Tier 1 — Accidental | 1 (`xyz`) | DELETE immediately |
| Tier 2 — Unexpected tracked diffs | 6 files | Review diffs; low risk; include in commit after review |
| Tier 3 — Unclear phase owner | 7 files | Investigate; archive or delete most; keep docs if they contain design rationale |
| Tier 4 — Review before commit | 5 files | Manual diff review recommended before commit |
