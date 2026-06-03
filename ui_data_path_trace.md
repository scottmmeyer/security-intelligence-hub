# UI Data Path Trace
**Generated:** 2026-06-01  
**Scope:** portfolio_alignment UI — all data fields from source file → API → render

---

## 1. ESS Signal Path

```
Fidelity StarMine API
  └─► data/current/signal_snapshot.csv        (ingest pipeline; field: ess_category)
        └─► enrich_holdings()                  src/portfolio/enrichment.py
              └─► PortfolioHolding.ess_score_text
                    └─► build_security_overlays()   src/portfolio/recommendations.py ~L196
                          ├─ if h.ess_score_text is empty → fallback: ess_history_master.csv
                          └─► SecurityIntelligenceOverlay.ess_score_text
                                ├─► security_overlays.csv  (persisted per run)
                                └─► run_analysis() JSON → data.security_overlays[].ess_score_text
                                      ├─► renderSecurityOverlays()  app.js L1682
                                      ├─► renderHoldingsTable()     app.js L1256
                                      └─► _computeSignalAgreement() app.js L960
```

**Fidelity panel (separate path):**
```
data/current/signal_snapshot.csv
  └─► _build_fidelity_payload()   runner.py
        └─► data.fidelity_signals_by_symbol[sym].ess_text
              └─► _fidelityPanelHtml() / _consensusStackHtml()   app.js
```

**Key divergence:** `security_overlays.ess_score_text` may differ from `fidelity_signals_by_symbol.ess_text` because:
- Overlays use `ess_history_master.csv` archive fallback for gaps
- Fidelity panel always reads live `signal_snapshot.csv` with no archive fallback
- For loaded (persisted) runs, overlays are static (CSV at run time); fidelity panel is live-loaded

---

## 2. Replay Alignment Path

```
data/current/replay_inputs.csv          (which symbols appeared in which replays)
data/current/replay_performance_series.csv
data/current/analytical_universe.csv   (composite_score → percentile computation)
  └─► _load_replay_evidence()   src/portfolio/recommendations.py ~L50
        ├─► symbol_tier, symbol_replay  (ALL cross-sector replays, first-seen wins)
        ├─► industry_replay_evidence    (industry-specific, tier-compatibility checked in overlay builder)
        └─► symbol_percentile           (rank within cohort by composite_score, ascending)
              └─► build_security_overlays()  ~L155
                    └─► SecurityIntelligenceOverlay
                          ├─ replay_supported   (bool)
                          ├─ replay_percentile  (float, 1–100 or None)
                          └─► security_overlays.csv (persisted)
                                └─► compute_multi_dimensional_score()
                                      └─► _compute_replay_alignment()  src/portfolio/scoring.py ~L340
                                            ├─ Coverage (0–60): % portfolio value that is replay-supported
                                            ├─ Quality  (0–40): mean replay_percentile of supported holdings
                                            └─► MultiDimensionalScore.replay_alignment_score (0–100)
```

**UI rendering:**
| Surface | Field | Source |
|---------|-------|--------|
| Multi-Dim scorecard | `replay_alignment_score` | `data.multi_dimensional_score.replay_alignment_score` |
| Replay section | Chip list + count | `data.security_overlays[].replay_supported` |
| Holdings table | `✓ NNth` | `h.replay_supported`, `h.replay_percentile` |
| Overlay table | `REPLAY` chip | `o.replay_supported` |
| Deployment Queue signal profile | `Replay Pctile` | `ov.replay_percentile` (from overlay lookup) |
| UCF verdict | `replay_supported`, `replay_percentile` | `data.ucf_verdicts_by_symbol[sym].source_signals` |

---

## 3. Signal Agreement / Composite Path

```
analytical_universe.csv  (composite_score = weighted blend of ESS+Danelfin+Zacks)
  └─► enrich_holdings() → PortfolioHolding.composite_score
        └─► build_security_overlays()
              └─► SecurityIntelligenceOverlay.signal_direction  (BULLISH/NEUTRAL/BEARISH/UNKNOWN)
                    Logic:
                      ESS=BULLISH → BULLISH
                      ESS=BEARISH + composite_score ≥ 2.5 → NEUTRAL (lifted)
                      ESS=BEARISH + composite_score < 2.5 → BEARISH
                      no ESS: score ≥ 3.5 → BULLISH; ≥ 2.0 → NEUTRAL; else BEARISH

data/signals/yahoo/latest_yahoo_supplemental.csv  (always live)
  └─► _build_consensus_payload() → data.analyst_consensus_by_symbol
        └─► _computeSignalAgreement()  app.js  (ESS + Zacks + Yahoo ABR + Danelfin)

data/signals/danelfin/latest_danelfin.csv  (always live via analytical_universe.csv)
data/signals/zacks/latest_zacks.csv        (always live via analytical_universe.csv)
```

---

## 4. Temporal Consistency: Live vs Persisted Runs

| Data field | Fresh run | Loaded run (`load_analysis_run`) |
|---|---|---|
| `security_overlays` (ESS, replay, composite, direction) | Computed at analysis time | Read from `security_overlays.csv` — **static, run-time snapshot** |
| `analyst_consensus_by_symbol` | Latest Yahoo supplemental | Latest Yahoo supplemental — **always live** |
| `fidelity_signals_by_symbol` | Latest `signal_snapshot.csv` | Latest `signal_snapshot.csv` — **always live** |
| `signal_source_metadata` (refresh dates) | Live | Live |
| `ucf_verdicts_by_symbol` | Computed at analysis time | Read from `ucf_verdicts.json` — **static** |
| `multi_dimensional_score` (incl. `replay_alignment_score`) | Computed at analysis time | **Not loaded from disk** — absent on loaded runs |

**Notable gap:** `multi_dimensional_score` is not persisted to a standalone JSON and is not reconstructed by `load_analysis_run()`. Loaded runs show the multi-dim scorecard empty/zero unless the browser has a cached `localStorage` result from the original run.

---

## 5. `load_analysis_run` vs `run_analysis` Response Shape Delta

Fields present in `run_analysis()` response but **absent** in `load_analysis_run()` response:

| Field | Notes |
|---|---|
| `multi_dimensional_score` | Not persisted; not reconstructed |
| `intentional_asymmetry` | Not persisted standalone |
| `cash_mandate_context` | Not persisted standalone |
| `mandate_interpretations` | Not persisted standalone |
| `strategic_profiles` | Not persisted standalone (computed from holdings) |
| `sti_warnings` | Not persisted standalone |
| `phase_e_warnings` | Not persisted standalone |
| `optimizer_scores` | Not persisted standalone |
| `operational_exclusions` | Not persisted standalone |
| `reconciliation_*` fields | Partial — some loaded from `run_metadata.json` |

Fields present in `load_analysis_run()` that differ semantically from `run_analysis()`:

| Field | Difference |
|---|---|
| `analyst_consensus_by_symbol` | Always current Yahoo data, not data at analysis time |
| `fidelity_signals_by_symbol` | Always current signal_snapshot, not snapshot at analysis time |
| `signal_source_metadata` | Always current refresh dates |
