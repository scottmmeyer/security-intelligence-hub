# Thin Replay Population Report
**Phase 7.6D.1 — SANM Replay Forensics**
**Run Reference:** PAR-20260601-9CFD7C63
**Date:** 2026-06-01

---

## Q4: All Holdings with Coverage Days < 30 or CURRENT_RECOMMENDATION Replay

---

## Methodology

**Data source:** `replay_evidence_inventory.csv` (81 portfolio holdings)

**Thin evidence criteria:**
- `max_coverage_days < 30` AND `replay_supported_in_ucf = True`
- OR `replay_type = CURRENT_RECOMMENDATION` AND `replay_supported_in_ucf = True`

Holdings with `replay_supported_in_ucf = False` are not included — they receive 0 replay pts and the evidence depth is irrelevant to scoring.

---

## Thin Evidence Holdings (coverage_days < 30, replay_supported=True)

| Symbol | Coverage Days | Replay Type | Basket | replay_supported | CW-DAS Rank | UCF Label | Root Cause |
|---|---|---|---|---|---|---|---|
| SANM | 6 | CURRENT_RECOMMENDATION | US.SMALL.ALL | True | 11 | HIGH_CONVICTION_ANCHOR | Routing artifact (365-day replay exists on disk, unregistered) |
| AEIS | 6 | CURRENT_RECOMMENDATION | US.SMALL.ALL | True | — (not in ranked queue) | DEPLOYMENT_CANDIDATE | Genuine thin evidence (no 365-day basket appearance) |

**Count: 2 holdings** with THIN evidence and `replay_supported=True` in the active portfolio.

---

## SANM — Routing Artifact

**Is SANM unique? Yes and no.**

SANM is the only thin-evidence holding in the CW-DAS ranked deployment queue. It is unique in impact (rank 11, HIGH_CONVICTION_ANCHOR). However, the underlying routing gap is systemic: any symbol whose only 365-day basket appearance is in an ALL-industry replay would face the same condition.

| Finding | Value |
|---|---|
| Coverage days | 6 |
| Replay type | CURRENT_RECOMMENDATION |
| Basket | US-SMALL-ALL (2026-05-20 to 2026-05-26) |
| 365-day historical evidence on disk | YES — `REPLAY-2025-05-14-TO-2026-05-14-US-SMALL-ALL-...` |
| 365-day replay in replay_matrix.csv | NO |
| Classification | Routing Artifact |

SANM has 365-day HISTORICAL_VALIDATION evidence on disk. It is "thin" only because the routing system does not know the 365-day replay exists. See `sanm_bucket_routing_analysis.md` for full analysis.

---

## AEIS — Genuine Thin Evidence

| Finding | Value |
|---|---|
| Coverage days | 6 |
| Replay type | CURRENT_RECOMMENDATION |
| Basket | US-SMALL-ALL (2026-05-20 to 2026-05-26) |
| 365-day historical evidence on disk | NO — AEIS does not appear in any 2025-05-14 snapshot basket |
| Classification | Genuine Thin Evidence |

AEIS (Advanced Energy Industries) was not selected in any HISTORICAL_VALIDATION basket at the 2025-05-14 snapshot. Its replay evidence is entirely from the recent 6-day current-recommendation window. AEIS is not in the CW-DAS ranked queue (UCF label: DEPLOYMENT_CANDIDATE with COMPOSITE_ESS_DIVERGE flag, UCF score 58.61) and is not a deployment-material concern.

---

## Bucket-Only Holdings (relay_supported via bucket assignment, not basket selection)

These holdings are distinct from THIN evidence: they have `replay_supported=True` but have **zero** individual basket appearances — their assignment comes from sector/cap-bucket qualification only.

| Symbol | Coverage Days | Basket Appearances | CW-DAS Rank | UCF Label | Classification |
|---|---|---|---|---|---|
| GTX | 0 | 0 | 34 | HIGH_CONVICTION_ANCHOR | Bucket-only |
| SIMO | 0 | 0 | 38 | HIGH_CONVICTION_ANCHOR | Bucket-only |
| SBS | 0 | 0 | 42 | HIGH_CONVICTION_ANCHOR | Bucket-only |

These are covered separately in Phase 7.6D. They are not affected by the SANM routing artifact — their issue is a different mechanism (bucket-level assignment without individual selection).

---

## Population Summary

| Category | Count | Deployment Impact |
|---|---|---|
| THIN (routing artifact, 365-day exists on disk) | 1 (SANM) | HIGH — rank 11 under current binary model |
| THIN (genuine, no 365-day evidence anywhere) | 1 (AEIS) | NONE — not in ranked queue |
| BUCKET_ONLY (no basket appearance) | 3 (GTX, SIMO, SBS) | MINOR — ranks 34–42 |
| STRONG (365-day, correctly routed) | 38 | UNAFFECTED |
| NONE (replay_supported=False) | 38+ | N/A (outside ranked queue) |

---

## Is SANM Unique?

**As a deployment-queue member with THIN evidence: YES, SANM is the only case.**

**As a routing artifact case: SANM is the clearest identified instance of a broader systemic gap.** The 365-day ALL-industry replays are excluded from the routing table for all cap buckets. Any other portfolio holding that:
1. Appears in the 365-day ALL-basket but NOT in its industry-specific basket
2. AND has `replay_supported=True`

...would face the same condition. SANM is the only current portfolio holding that meets both criteria. AEIS is in neither basket (genuine thin). ARW and AVT also appear in the 365-day SMALL-ALL basket but are correctly routed via the SMALL-TECHNOLOGY industry-specific basket (they appear in both).
