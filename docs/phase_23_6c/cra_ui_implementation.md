# CRA UI Implementation — Phase 23.6C

## Buttons Added (CRA Panel Header)

| Button | ID | Action | Enabled When |
|--------|----|--------|-------------|
| ✎ Save | `craSaveBtn` | `_craSaveDraft()` | Proposal loaded |
| ↻ Load | `craLoadBtn` | `_craLoadDraft()` | Always |
| ↓ CSV | `craExportCsvBtn` | `_craExportCsv()` | Proposal loaded |
| ↓ MD | `craExportMdBtn` | `_craExportMd()` | Proposal loaded |
| ✤ Copy | `craCopyBtn` | `_craCopySummary()` | Proposal loaded |
| ↺ Refresh | `craRefreshBtn` | `loadCRAProposal()` | Always |

## Draft Banner

A `#craDraftBanner` element shows when a draft is detected from a different run, with "Apply Selections" and "Dismiss" buttons.

## Auto-Restore on Load

When `loadCRAProposal()` completes, it automatically calls `_craCheckDraft()` which:
- If draft.run_id === current run_id: silently restores Include/Skip selections
- If stale: shows the draft banner

## Save Feedback

✎ Save button shows "Saving…" then "✓ Saved" for 2.5 seconds, then resets.

## Copy Fallback

If `navigator.clipboard` is unavailable (e.g., insecure context), a full-screen textarea is shown for manual copy.
