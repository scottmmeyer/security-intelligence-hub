# ISSUE-09 Fix Recommendation

## Fix Applied

**File:** `ui/portfolio_alignment/app.js`  
**Line:** Before `const _CRA_CATEGORIES = [...]`

**Change:**
```javascript
// Before (missing declaration)
// Category metadata
const _CRA_CATEGORIES = [

// After (restored declaration)
// Category metadata
let _craProposal = null;   // ISSUE-09 fix: restored missing declaration
const _CRA_CATEGORIES = [
```

**Version bump:** `app.js?v=21` → `v=22` in `index.html`

## Rationale

- Single line addition
- Restores the declaration that was accidentally removed during ISSUE-07 refactoring
- `let` with `null` initial value is correct:
  - `let` — reassignable (required; it gets assigned on each CRA load)
  - `null` — safe sentinel value; all CRA functions check `if (!_craProposal)` before use
- No behavioral change: the fix restores the pre-ISSUE-07 behavior

## What Was NOT Changed

- No CRA business logic
- No proposal generation
- No save/load/export logic
- No CW-DAS scoring
- No PAP logic
- No recommendations

## Prevention

To prevent similar issues in future refactoring: module-level state variables should be declared in a dedicated block at the top of the file (or in a clear "State" section) rather than inline within the code that uses them.
