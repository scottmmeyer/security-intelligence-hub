# ISSUE-09 Code Path Trace

## Lifecycle of _craProposal

### Expected Lifecycle (Correct)

```
Page load
  → _craProposal declared: let _craProposal = null;  ← MISSING

Portfolio analysis completes (renderResults called)
  → loadCRAProposal() called (line ~1020)
  → fetch("/api/cra/proposal")
  → _craProposal = await resp.json();   ← ASSIGNMENT
  → _renderCRAProposal(_craProposal)    ← FIRST READ
  → _craEnableButtons(true)             ← buttons enabled
  → _craCheckDraft(_craProposal.run_id) ← SECOND READ
```

### Actual Lifecycle (Broken, Pre-Fix)

```
Page load
  → _craProposal: NEVER DECLARED

Portfolio analysis completes
  → loadCRAProposal() called
  → fetch("/api/cra/proposal")
  → _craProposal = await resp.json();
     ↑ This line assigns to an undeclared variable
     ↑ The catch block above catches the ReferenceError
       from an earlier reference OR the assignment itself fails in strict mode

  → catch(e): content.innerHTML = `CRA error: ${String(e)}`
     ↑ "ReferenceError: _craProposal is not defined" displayed to user
```

## First Definition Point

**Expected:** Line ~4329 (before `_CRA_CATEGORIES` declaration)  
**Actual (pre-fix):** Never declared — first reference at line 4356 (`_craProposal = await resp.json()`)

## First Reference Point

Line 4356: `_craProposal = await resp.json();`  
This is an assignment, which in strict-mode would work as a global but the subsequent read on the same line (`_renderCRAProposal(_craProposal)`) would also work. However, the error appears to surface at the point of the first read-before-assignment pattern.

Actually, looking more carefully: `_craCheckDraft(_craProposal.run_id)` on line ~4366 reads `_craProposal.run_id` — if `_craProposal` is undeclared and the assignment on line 4356 fails, this read fails with the ReferenceError.

## Q4: Does the error prevent CRA recommendations from being generated?

**YES.** `loadCRAProposal()` catches the error and displays it, preventing `_renderCRAProposal()` from executing. The CRA proposal IS fetched from the server (`/api/cra/proposal` call succeeds) but is not stored or rendered.

## Q5: Does the error impact save/load/export?

**YES.** All CRA persistence functions start with:
```javascript
if (!_craProposal) return;   // Guards against null — but the variable must be declared
```
With the variable undeclared, these lines also throw `ReferenceError` before the null check can execute.

## Q6: Is there a broader state-management defect?

**NO.** This is a single missing declaration. All other state variables (`_lastAnalysisData`, `_analysisResult`, `_securityMetadata`, etc.) are correctly declared at the module level. The defect is isolated to `_craProposal`.

## Q7: Minimal safe fix

Add `let _craProposal = null;` before `const _CRA_CATEGORIES = [...]`.
