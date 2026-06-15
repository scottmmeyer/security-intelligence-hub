# PRA-IMPL-02 UI Audit

## Scope

Independent audit of Portfolio Alignment UI changes in `ui/portfolio_alignment/app.js`.
Evidence from code inspection of rendering functions for CRA source and target cards.

---

## Q17. Can operators understand why a source was chosen?

**Yes, when reduction_score > 0.**

The `_craBuildSourceCard(s)` function renders a `reductionMeta` block:

```javascript
const reductionMeta = (typeof s.reduction_score === "number" && s.reduction_score > 0)
  ? `<div ...>
       Reduction Score: <strong>${Number(s.reduction_score).toFixed(1)}</strong>
       ${s.reduction_reason ? ` · ${escHtml(s.reduction_reason)}` : ""}
     </div>
     ${s.policy_alignment_reason ? `<div ...>Policy: ${escHtml(s.policy_alignment_reason)}</div>` : ""}`
  : "";
```

This renders:
- Reduction score (numeric, to 1 decimal)
- Reduction reason (human-readable sentence)
- Policy alignment reason (philosophy context)

An operator viewing the CRA Capital Sources column sees for each source:
1. Why this source is a reduction candidate (reason)
2. How much priority it has numerically (score)
3. How it aligns with portfolio philosophy (policy)

---

## Q18. Can operators understand why alternatives lost?

**Partially.**

Target cards now show:

```javascript
const fundingHtml = t.funding_source_symbol
  ? `<div ...>
       Funding: <strong>${escHtml(t.funding_source_symbol)}</strong>
       (${escHtml(t.funding_source_category)}, score ${Number(t.funding_source_score || 0).toFixed(1)})
     </div>
     ${t.funding_source_reason ? `<div ...>${escHtml(t.funding_source_reason)}</div>` : ""}
     ${Array.isArray(t.funding_source_alternatives) && t.funding_source_alternatives.length
       ? `<div ...>Alternatives: ${escHtml(t.funding_source_alternatives.join("; "))}</div>`
       : ""}
     ${t.funding_policy_alignment_reason ? `<div ...>Policy: ${escHtml(t.funding_policy_alignment_reason)}</div>` : ""}`
  : "";
```

Operators see:
1. Which source was selected and its score
2. The reason for selection
3. The alternatives that were NOT selected (with their category and score)

**Gap:** The alternatives show `category + score` but NOT the individual reason why
each alternative was ranked lower. An operator sees "AAPL (SIGNAL DETERIORATION,
score 117.0)" but not "AAPL scored lower than MSFT because MSFT is URGENT while
AAPL is HIGH priority." The relative scoring logic is implicit in the score numbers
but not stated.

This is an acceptable gap for the current implementation — the numeric scores are
sufficient for operators who understand the scoring model, and the category labels
provide intuitive ordering rationale.

---

## Q19. Is information discoverable without opening logs?

**Yes.**

All new PRA-IMPL-02 fields are rendered inline in the existing CRA source and target
cards within the Portfolio Alignment UI. No log access, no API call, no modal required.

The reduction metadata appears immediately below the proceeds row in each source card.
The funding annotation appears immediately below the allocation note in each target card.

Both surfaces auto-render when `loadCRAProposal()` is called after analysis — this
happens automatically after every portfolio analysis run (`renderResults(data)` calls
`loadCRAProposal()`).

---

## Q20. Is rendering resilient to missing funding metadata?

**Yes.**

Both rendering paths have explicit absence checks:

**Source card:**
```javascript
const reductionMeta = (typeof s.reduction_score === "number" && s.reduction_score > 0)
  ? /* render block */
  : "";
```
If `reduction_score` is 0, null, or non-numeric → empty string → no crash.

**Target card:**
```javascript
const fundingHtml = t.funding_source_symbol
  ? /* render block */
  : "";
```
If `funding_source_symbol` is falsy → empty string → no crash.

Individual sub-fields also have conditional checks:
- `s.reduction_reason ? ...` — omitted if empty
- `s.policy_alignment_reason ? ...` — omitted if empty
- `t.funding_source_reason ? ...` — omitted if empty
- `Array.isArray(t.funding_source_alternatives) && t.funding_source_alternatives.length` — omitted if empty
- `t.funding_policy_alignment_reason ? ...` — omitted if empty

Pre-PRA CRA proposals served from old PAR runs would have zero/empty new fields,
and the cards will render identically to their pre-PRA appearance. No visual
regression for old data.

---

## Serialization Contract Verification

The CRA models serialize new fields to the API payload in `src/portfolio/cra/models.py`:

Source record:
```python
"reduction_reason":        s.reduction_reason,        # str, default ""
"reduction_score":         s.reduction_score,          # float, default 0.0
"policy_alignment_reason": s.policy_alignment_reason,  # str, default ""
```

Target record:
```python
"funding_source_alternatives": t.funding_source_alternatives,      # List[str]
"funding_policy_alignment_reason": t.funding_policy_alignment_reason, # str
```

(Plus previously existing `funding_source_symbol`, `funding_source_category`,
`funding_source_score`, `funding_source_reason` fields.)

**Gap:** There is no automated test that verifies the `/api/cra/proposal` API
payload contains these new fields with correct values. The serialization code is
correct but untested via API-level assertion.

---

## Visual Design Assessment

New metadata uses:
- `font-size: 0.72rem` — compact, does not overwhelm existing card content
- `color: var(--muted)` for reasons — readable but secondary
- `color: #5b4f36` for policy alignment — warm amber, consistent with the existing
  palette used for policy annotations elsewhere in the UI
- `<strong>` for score value — easily scannable

No new CSS classes were added; inline style tokens are used. This keeps the changes
minimal and contained. No layout regression expected.
