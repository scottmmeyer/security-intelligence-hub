# CRA API Implementation — Phase 23.6C

## Endpoints Implemented

| Method | Path | Description | Response |
|--------|------|-------------|---------|
| GET | `/api/cra/proposal` | Build fresh proposal from latest PAR run | `RotationProposal.to_dict()` |
| GET | `/api/cra/draft` | Load saved draft | Draft JSON or 404 |
| POST | `/api/cra/draft` | Save proposal as draft (+ operator_include_map) | `{saved: true, proposal_id}` |
| DELETE | `/api/cra/draft` | Clear saved draft | `{deleted: true}` |
| GET | `/api/cra/draft/export?format=csv` | Export draft as CSV download | CSV file |
| GET | `/api/cra/draft/export?format=md` | Export draft as Markdown download | .md file |

## Storage

`data/operator/cra_draft.json` — single file, atomic write via tmp+rename.

Added to `.gitignore` as runtime operational data.

## Non-Negotiables

- NO CW-DAS changes ✅
- NO scoring changes ✅  
- NO ranking changes ✅
- Does NOT persist raw portfolio CSV, account numbers, or credentials ✅
