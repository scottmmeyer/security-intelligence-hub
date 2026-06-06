# CRA Validation Report — Phase 23.6C

## API Validation (Live — June 5, 2026)

| Test | Result |
|------|--------|
| GET /api/cra/proposal | ✅ 200 OK — CRA-20260605-E9ADE792, 26 sources, 31 targets |
| POST /api/cra/draft | ✅ 200 OK — `{saved: true, proposal_id: CRA-20260605-E9ADE792}` |
| GET /api/cra/draft | ✅ 200 OK — draft loaded, saved_at_utc populated |
| GET /api/cra/draft/export?format=csv | ✅ 200 OK — 66 lines, SOURCE rows with correct fields |
| GET /api/cra/draft/export?format=md | ✅ 200 OK — 93 lines, correct markdown structure |
| DELETE /api/cra/draft | ✅ 200 OK — `{deleted: true}` |
| GET /api/cra/draft (after delete) | ✅ 404 — expected |

## Regression

| Check | Result |
|-------|--------|
| pytest -q | ✅ 1,004 passed, 0 failed |
| node --check app.js | ✅ SYNTAX OK |

## Validation: Include/Skip Persistence

| Test | Result |
|------|--------|
| Skip checkbox state collected on save | ✅ `operator_include_map` in draft JSON |
| Matching run_id → auto-restore on load | ✅ Implemented via `_craRestoreIncludeMap()` |
| Stale draft (different run_id) → banner shown | ✅ Draft banner with Apply/Dismiss |

## Non-Negotiables

- ✅ NO CW-DAS changes
- ✅ NO UCF changes
- ✅ NO scoring changes
- ✅ NO ranking changes
- ✅ Raw portfolio CSV not persisted
- ✅ No PII or account numbers in draft
