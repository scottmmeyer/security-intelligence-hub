# Deployable Cash Validation

Repository: security-intelligence-hub  
PAR: PAR-20260529-7482D734  
Date: 2026-06-08

## Portfolio Cash Summary (May-29-2026)

| Field | Value |
|---|---|
| Total portfolio MV | $472,219.90 |
| SPAXX balance | $42,619.59 |
| Cash weight | 9.0254% |
| Mandate cash floor (7%) | $33,055.39 |
| Excess above floor | $9,564.20 |
| Settlement adjustment | $0 |
| SIH deployable | $9,564.20 |

## Q2 — Does SIH Agree with the $54,257.49 Figure?

No. SIH does not agree with $54,257.49 because the May-29 portfolio CSV shows SPAXX at $42,619.59.

The $54,257.49 figure likely comes from a more recent Fidelity account view that reflects cash accumulation after May-29. It is not consistent with the uploaded portfolio. The correct figure for this analysis is $42,619.59.

## Evaluation of Candidate Deployable Amounts

### Option 1: $0

This would apply if cash were at or below the mandate floor. Since actual cash (9.0254%) > floor (7.0%), this does not apply.

Verdict: Incorrect for this portfolio.

### Option 2: $9,564.20 (SIH Answer)

SIH deploys the excess above the 7% mandate floor.

Formula:
deployable = cash_mv − (total_mv × floor_pct)
deployable = $42,619.59 − ($472,219.90 × 0.07)
deployable = $42,619.59 − $33,055.39
deployable = $9,564.20

Verdict: CORRECT — this is SIH's authoritative answer.

### Option 3: $21,700 (approximate)

This would correspond to a deployable calculation using a different floor assumption (approximately 5% floor):
$42,619.59 − ($472,219.90 × 0.045) = $42,619.59 − $21,249.90 ≈ $21,369

No evidence suggests a ~$21.7K figure from this portfolio. This may have been derived from a different portfolio or a different floor assumption.

Verdict: Not applicable to this portfolio under CONCENTRATED_ALPHA mandate rules.

### Option 4: $42,619.59 (total SPAXX)

Full SPAXX balance. This would represent deploying all cash with no operational reserve.

Verdict: Operationally inadvisable; does not respect mandate cash floor.

## Recommended Answer: $9,564.20

Under CONCENTRATED_ALPHA mandate with 7% cash floor:
- Total SPAXX: $42,619.59
- Floor reserve: $33,055.39
- Deployable: $9,564.20 (2.03% of portfolio)

## If the Current SPAXX Balance Is $54,257.49

If the operator is using the current real-time account view showing $54,257.49, the deployable calculation would be:

deployable = $54,257.49 − ($472,219.90 × 0.07)
deployable = $54,257.49 − $33,055.39
deployable = $21,202.10

This gives a deployable figure of approximately $21,200, which aligns with the ~$21.7K option mentioned in the question. This is the most likely explanation for the discrepancy.

## Validation Verdict

| Scenario | Cash | Deployable |
|---|---|---|
| May-29 portfolio (SIH source of truth) | $42,619.59 | $9,564.20 |
| Current real-time Fidelity view | ~$54,257.49 | ~$21,202 |

The correct SIH-authoritative figure based on the uploaded portfolio is $9,564.20. If the operator wants to use the current real-time cash balance, a fresh portfolio upload is needed.
