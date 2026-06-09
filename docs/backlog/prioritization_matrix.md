# SIH Backlog Prioritization Matrix

Repository: security-intelligence-hub  
Created: 2026-06-09

---

## Priority / Complexity Matrix

|  | S (Small) | M (Medium) | L (Large) |
|---|---|---|---|
| **CRITICAL** | — | AI-001, PA-001, PA-004 | — |
| **HIGH** | AI-002, PA-002, PA-003 | AI-003, PA-005 | — |
| **MEDIUM** | — | AI-004 | PA-006 |

---

## Priority Score Method

Each item is scored on three dimensions (1–5 scale):

- **Operator Impact** — how much does this affect operator decision quality?
- **Trust Risk** — does the current behavior erode system trust if left unfixed?
- **Implementation Readiness** — how much prerequisite work is already complete?

| ID | Operator Impact | Trust Risk | Implementation Readiness | Total | Priority Tier |
|---|---|---|---|---|---|
| AI-001 | 4 | 5 | 3 | 12 | 1 — Fix First |
| PA-004 | 5 | 5 | 4 | 14 | 1 — Fix First |
| PA-001 | 5 | 4 | 5 | 14 | 1 — Fix First |
| PA-003 | 4 | 3 | 5 | 12 | 2 — Fix Soon |
| PA-002 | 4 | 3 | 5 | 12 | 2 — Fix Soon |
| PA-005 | 4 | 3 | 4 | 11 | 2 — Fix Soon |
| AI-002 | 3 | 4 | 5 | 12 | 2 — Fix Soon |
| AI-003 | 3 | 2 | 3 | 8 | 3 — Planned |
| AI-004 | 2 | 2 | 3 | 7 | 3 — Planned |
| PA-006 | 3 | 1 | 2 | 6 | 4 — Future |

---

## Tier 1 — Fix First (Trust-Critical)

These items either create logically contradictory outputs or cause operators to receive conflicting execution guidance. They undermine system trust.

1. **PA-004** — Policy Consistency Failure: TSLA receives TRIM guidance from PAP while DO_NOT_SELL is active
2. **AI-001** — Policy contradiction: system reports both "OVER ceiling" and "PASS" simultaneously
3. **PA-001** — Recommendation overload: 34-card stream with 6 true actions buried in informational content

---

## Tier 2 — Fix Soon (Usability-High)

These items materially reduce operator efficiency and add cognitive overhead but do not create contradictory signals.

4. **PA-003** — Count inflation misrepresents workload
5. **PA-002** — Poor ordering forces manual scanning for actions
6. **PA-005** — Explainability cards overwhelm the action stream
7. **AI-002** — Unlabeled allocation tables cause confusion

---

## Tier 3 — Planned (Governance Enhancement)

These items improve governance depth and transparency but have no current operational contradiction.

8. **AI-003** — Allocation philosophy narrative
9. **AI-004** — Policy version diff visibility

---

## Tier 4 — Future (Capability Expansion)

10. **PA-006** — Drift trend history requires new data aggregation infrastructure

---

## Dependency-Adjusted Sequence

Considering implementation dependencies:

1. AI-001 (investigation first — no code prerequisites)
2. PA-004 (investigation + PAP policy normalization, extends PRA-IMPL-02)
3. PA-001 / PA-003 / PA-002 (together as PRA-IMPL-03 lane separation)
4. PA-005 (PRA-IMPL-04 conviction anchors, depends on PA-001 lane model)
5. AI-002 (display label fix, no dependencies)
6. AI-003 (content + display, depends on governance content creation)
7. AI-004 (versioning infrastructure)
8. PA-006 (drift history infrastructure)
