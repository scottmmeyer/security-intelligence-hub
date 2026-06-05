# Next Phase Recommendation — Phase GOV-001

## Options Evaluated

| Issue | Title | Priority | Status | Effort | Epic |
|-------|-------|----------|--------|--------|------|
| ISSUE-02 | CRA Draft Persistence + Export | HIGH | ready | M | CRA |
| ISSUE-03 | FMP Score Integration Assessment | HIGH | needs-design | L | FMP + Signal Evolution |
| ISSUE-04 | Dislocation Watchlist Panel | MEDIUM | needs-design | S | Company Context |
| ISSUE-05 | Queue Filter by Thesis Integrity | MEDIUM | ready | XS | Company Context |

---

## Dimension Analysis

### Operator Value

| Issue | Operator Value | Reasoning |
|-------|---------------|-----------|
| ISSUE-02 | **HIGH** | CRA proposals currently die when the browser is closed. Persistence and export directly extend the CRA's utility from advisory insight to actionable output. |
| ISSUE-03 | MEDIUM (research phase) | No operator-visible change in this phase — it's assessment only |
| ISSUE-04 | MEDIUM | Useful scan view; requires full-universe FMP data (already available post-ISSUE-01) |
| ISSUE-05 | MEDIUM | Good filtering capability; XS effort |

### Methodology Alignment

| Issue | Alignment | Reasoning |
|-------|----------|-----------|
| ISSUE-02 | **STRONG** | Directly serves the Portfolio Discipline layer (Layer 4) — capital deployment decisions need to be exportable |
| ISSUE-03 | VERY STRONG | Would validate whether FMP fundamentals belong in Layer 2→scoring integration |
| ISSUE-04 | STRONG | Serves the Dislocation Philosophy directly |
| ISSUE-05 | MODERATE | Quality-of-life filter, not methodology-critical |

### Implementation Risk

| Issue | Risk | Reasoning |
|-------|------|-----------|
| ISSUE-02 | **LOW** | CRA data model ready; endpoints are straightforward additions; no scoring changes |
| ISSUE-03 | MEDIUM | Research findings could require significant follow-on design; outcome unknown |
| ISSUE-04 | LOW-MEDIUM | Needs design phase; JS classification logic already exists |
| ISSUE-05 | **LOW** | Client-side only; trivial implementation |

### Strategic Importance

| Issue | Strategic | Reasoning |
|-------|----------|-----------|
| ISSUE-02 | HIGH | Completes Phase 23.6C — closes the CRA epic's most important open item |
| ISSUE-03 | **VERY HIGH** | Gateway to scoring evolution — the most strategically important research item |
| ISSUE-04 | MEDIUM | Enhances existing capability |
| ISSUE-05 | LOW | Convenience feature |

---

## Weighted Recommendation Matrix

| Issue | Operator Value (30%) | Methodology (25%) | Risk (20%) | Strategic (25%) | **Total** |
|-------|---------------------|-------------------|------------|-----------------|-----------|
| ISSUE-02 | 9 × 0.30 = 2.7 | 8 × 0.25 = 2.0 | 9 × 0.20 = 1.8 | 8 × 0.25 = 2.0 | **8.5** |
| ISSUE-03 | 5 × 0.30 = 1.5 | 9 × 0.25 = 2.25 | 7 × 0.20 = 1.4 | 10 × 0.25 = 2.5 | **7.65** |
| ISSUE-05 | 6 × 0.30 = 1.8 | 5 × 0.25 = 1.25 | 10 × 0.20 = 2.0 | 4 × 0.25 = 1.0 | **6.05** |
| ISSUE-04 | 7 × 0.30 = 2.1 | 8 × 0.25 = 2.0 | 8 × 0.20 = 1.6 | 6 × 0.25 = 1.5 | **7.2** |

---

## Recommendation: ISSUE-02 (CRA Draft Persistence + Export)

**Primary:** ISSUE-02 scores highest on the weighted matrix.

**Secondary option:** If the operator prefers strategic research over UX completion, ISSUE-03 is a valid alternative — it unlocks the scoring evolution track.

**Quick win before either:** ISSUE-05 (Queue Filter) is XS effort and can be done as a warmup in the same session as ISSUE-02.

### Recommended Session Sequence

```
Session start:
  ISSUE-05 (XS — 1 hour) — Queue filter by Thesis Integrity
  → immediately closes a ready issue

Then:
  ISSUE-02 (M — 3–4 hours) — CRA Draft Persistence + Export
  → closes the highest-value ready issue

Next session:
  ISSUE-03 (L — design phase) — FMP Score Integration Assessment
  → most strategically important open item
```

---

## Implementation Notes for ISSUE-02

Per `initial_issue_backlog.md`:

1. `POST /api/cra/proposal/draft` — saves to `data/operator/cra_draft.json`
2. `GET /api/cra/proposal/export` — returns CSV download
3. Clipboard copy button in CRA panel
4. Draft loads on page reload

The CRA data model (`src/portfolio/cra/models.py`) is ready. The `RotationProposal.to_dict()` method provides the serialization path. The UI already has the CRA panel rendered. This is pure API + UI wiring.
