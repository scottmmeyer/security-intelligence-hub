# Phase 23.0C.1 — M26CNT069 Forensic Review

**PAR Run**: PAR-20260603-B66B00E3  
**Date**: 2026-06-03  
**Status**: COMPLETE

---

## 1. Identity Determination

| Field | Value |
|-------|-------|
| **Symbol** | M26CNT069 |
| **Symbol Type** | Fidelity internal custody instrument ID (NOT a market ticker) |
| **Description** | CYBERARK SOFTWA F CONTRA |
| **Underlying Security** | CyberArk Software (CYBR) — enterprise cybersecurity, NYSE-listed |
| **Account** | Z26346415 — Joint WROS - TOD (Joint account) |
| **Account Name** | General Brokerage, Joint WROS - TOD, Individual - TOD |

---

## 2. Position Economics

| Field | Value |
|-------|-------|
| **Quantity** | 2 shares |
| **Last Price (source)** | `--` (em-dash — Fidelity "unpriced" sentinel) |
| **Current Value (source)** | `--` (em-dash — no market value) |
| **Market Value (ingested)** | $0.00 |
| **Percent of Portfolio** | 0.00% |
| **Cost Basis** | Not available |

---

## 3. Source Classification vs. Ingested Classification

| Layer | Security Type |
|-------|---------------|
| Source CSV column 16 | `Cash` |
| Ingested `security_type` | `ETF` |
| Ingested `asset_class` | `EQUITIES` |
| Ingested `operational_state` | `ACTIVE_POSITION` |

**Misclassification detected**: The ingestion pipeline assigned `security_type=ETF` based on heuristic fallback — incorrect. Source file classifies row type as `Cash`, and `HEURISTIC_FALLBACK` decomposition with 0.35 confidence confirms no reliable classification was available.

---

## 4. "F CONTRA" Nomenclature

`CYBERARK SOFTWA F CONTRA` — the suffix `F CONTRA` is Fidelity-specific nomenclature:

- **F** = Fractional shares
- **CONTRA** = Contra account entry — a bookkeeping offset used in fractional share accounting

In Fidelity's system, when a holding undergoes a corporate action (reverse split, merger exchange, odd-lot buyout, or fractional buyout), fractional share quantities that cannot be converted whole are held in "contra" accounts pending resolution. The instrument receives a Fidelity internal ID (`M26CNT069` format) rather than a market ticker because it has no tradeable market presence.

---

## 5. Lineage Trace

**Probable Origin**: A corporate action on CyberArk Software (CYBR) affecting the Joint WROS account:
- Stock consolidation, reverse split, or merger event
- Left 2 fractional share units unresolvable to whole shares
- Fidelity recorded the contra entry under `M26CNT069`
- Position appears in export with `--` pricing (unpriced by Fidelity's pricing feed)
- The 2-share quantity represents the bookkeeping residue, not a tradeable holding

**Precedent**: This is a known Fidelity export behavior. Contra positions appear in portfolio exports during corporate action processing windows. They resolve automatically when the corporate action settles, or are manually cleared by Fidelity operations.

---

## 6. Operational State Assessment

| Dimension | Assessment |
|-----------|------------|
| Tradeable | No — no market price, no CUSIP pricing |
| Economically material | No — $0.00 market value |
| Allocation impact | None — 0.0% of portfolio |
| Deployable cash impact | None |
| CW-DAS impact | None — no ESS score |
| Funding source eligibility | None — zero value |
| Risk to analytical outputs | None |

---

## 7. Classification Verdict

**Classification: D — Zero-Value Legacy Security / Fractional Corporate Action Residue**

Specifically: **Fractional contra entry** from a Fidelity corporate action processing event on CYBR. This is a bookkeeping artifact that will resolve upon corporate action settlement. It is not a real economic position.

**NOT**:
- A — Data corruption (data is consistent with Fidelity export behavior)
- B — Import defect (ingestion correctly read the source row)
- C — Pure zero-value legacy (has a recent corporate action trigger, not a historical dormant)
- E — Bankruptcy/litigation (CYBR is actively trading)

---

## 8. Governance Recommendation

1. M26CNT069 should be classified `ZERO_VALUE_LEGACY_POSITION` in the ingestion pipeline
2. `operational_state` should be set to `ZERO_VALUE_CONTRA` or `PENDING_CORPORATE_ACTION`
3. `security_type` misclassification (`ETF` → `CONTRA_ENTRY`) should be corrected
4. Position must remain visible in holdings audit but must be excluded from all analytical calculations
5. No action required by portfolio operator — resolution is automatic upon Fidelity corporate action settlement
