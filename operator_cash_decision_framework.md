# Operator Cash Decision Framework

Repository: security-intelligence-hub  
Portfolio: May-29-2026 Fidelity Export  
Audit Date: 2026-06-08

## Portfolio Context

| Field | Value |
|---|---|
| Total portfolio MV | $472,219.90 |
| SPAXX (per CSV) | $42,619.59 |
| Cash weight | 9.03% |
| Mandate type | CONCENTRATED_ALPHA |
| Mandate cash target | 7.0% |
| Mandate cash floor | $33,055.39 |

## Q6 — Operator Cash Decision Framework

The question: if Fidelity shows approximately $54,257.49 in SPAXX/cash today, how much should a reasonable operator consider deployable?

Note: The current real-time figure ($54,257.49) is approximately $11,638 higher than the May-29 export value ($42,619.59). This delta likely represents cash accumulation from dividends, proceeds, or activity between May-29 and today. The May-29 portfolio remains the SIH source of truth until a new portfolio is uploaded.

---

## Answer 1: SIH Answer (Mandate-Governed)

SIH uses the uploaded portfolio cash value exclusively. Based on May-29 data:

Formula:
deployable = cash_mv − (total_mv × mandate_floor_pct)
deployable = $42,619.59 − ($472,219.90 × 0.07)
deployable = $42,619.59 − $33,055.39
deployable = $9,564.20

If the operator uploads a fresh portfolio reflecting $54,257.49 SPAXX:
deployable = $54,257.49 − $33,055.39
deployable = $21,202.10

SIH answer (current data): $9,564.20
SIH answer (if refreshed): ~$21,202

Rationale: The mandate floor preserves operational liquidity at 7% of total portfolio. Only cash above this floor is considered deployable. This prevents over-deployment in response to short-term cash elevation.

---

## Answer 2: Conservative Answer

Conservative operators treat some of the excess as transient or earmarked:
- Assume $5,000–$8,000 is pending settlement, dividend reinvestment timing, or discretionary buffer
- Deployable estimate: $13,000–$16,000 of the current $54,257.49 balance
- Or: deploy in two tranches, committing only 50% of apparent excess initially

Conservative deployable from $54,257.49: approximately $13,000–$15,000

Rationale:
- Cash can be in transit between dividend receipts and reinvestment
- A buffer protects against unexpected fees, margin calls, or near-term purchases
- Concentrated alpha mandate implies deliberate, measured deployment

---

## Answer 3: Aggressive Answer

An aggressive operator might treat all cash above a minimum working balance as deployable:
- Minimum working balance: $15,000–$20,000 (3–4% of $472K portfolio)
- Deployable from $54,257.49: $34,257–$39,257

Aggressive deployable from $54,257.49: approximately $34,000–$39,000

Rationale:
- High-conviction anchors in the deployment queue (VRT, ARW, ATLC, LRCX) have strong composite scores
- In a concentrated alpha mandate, deploying into top-conviction positions is the intended behavior
- Excess cash drag is a real cost in a conviction-based strategy

Risk: Over-deployment during elevated cash phase can reduce liquidity flexibility. This approach is only appropriate if the operator has high confidence in near-term deployment targets and no expected cash needs.

---

## Summary Table

| Scenario | Cash Base | Deployable | Approach |
|---|---|---|---|
| SIH (May-29 upload) | $42,619.59 | $9,564.20 | Mandate floor — current data |
| SIH (refreshed today) | $54,257.49 | ~$21,202 | Mandate floor — real-time data |
| Conservative | $54,257.49 | ~$13,000–$15,000 | Buffer + floor; staged deployment |
| Aggressive | $54,257.49 | ~$34,000–$39,000 | Minimal reserve; full conviction deployment |

---

## Recommendation to Operator

1. Upload the current Fidelity portfolio (today's export) to update SIH with real-time cash balance.
2. SIH will recalculate deployable cash using the current SPAXX balance against the mandate floor.
3. The SIH answer will be the most policy-consistent and auditable basis for deployment decisions.
4. If the operator wants to be conservative, reduce the SIH-computed deployable amount by 25–35% as a voluntary buffer.
5. Do not manually override the deployable amount to the full cash balance without acknowledging the mandate floor rationale.
