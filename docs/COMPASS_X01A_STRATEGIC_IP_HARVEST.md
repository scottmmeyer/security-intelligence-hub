# COMPASS-X01A — Strategic IP Harvest from SIH & Portfolio Manager

**Classification:** Strategic Architecture Document  
**Date:** 2026-06-15  
**Scope:** HarborLine Compass — Collateral Risk System (CRS)  
**Source Systems:** Security Intelligence Hub (SIH) + Portfolio Manager (PAR)

---

## Executive Summary

SIH and Portfolio Manager collectively represent a mature, production-validated intelligent analytics platform built around five deep intellectual property domains: multi-provider signal fusion, hierarchical risk decomposition, deterministic explainability, governance-first data quality, and portfolio-level composite scoring. These systems were designed to answer "Should I invest in this portfolio?" HarborLine Compass answers "Can I safely lend against this portfolio?" The objectives differ; the analytical substrate is nearly identical.

This document identifies **47 reusable capabilities**, classifies each for Compass relevance, maps them into Compass CRS constructs, and identifies a **shared foundation architecture** that would allow Compass, SIH, and Portfolio Manager to share a common analytical platform while preserving product-specific differentiation.

**Top finding:** The single greatest competitive moat opportunity is the combination of SIH's multi-provider signal fusion engine, the Unified Conviction Framework (UCF), and the deterministic explainability layer — applied to collateral quality scoring. No bank-grade lending platform currently offers this level of explainability at the collateral level. This is a genuine differentiator.

---

## Part 1 — Complete Capability Inventory

### 1.1 Portfolio Analytics

#### 1.1.1 Concentration Risk Analysis — `ConcentrationRiskSummary`
**Description:** Computes Herfindahl-Hirschman Index (HHI), top-1/3/5/10 position dominance percentages, single-sector maximum, US/international/emerging splits, mega-subtier effective exposure, and assigns a four-tier concentration tier: CRITICAL / HIGH / MODERATE / DIVERSIFIED.

**Implementation depth:** Production-grade. Handles direct holdings AND ETF-decomposed effective exposure. Concentration tier uses layered thresholds with policy compliance overlay (CPV-02: Mega Cap Concentration ≤ 50%).

#### 1.1.2 Multi-Dimensional Allocation Alignment — `AllocationAlignmentResult`
**Description:** Per-node comparison of actual vs. strategic target allocation across four dimensions — ASSET_CLASS (weight 3.0), GEOGRAPHY (weight 2.0), MARKET_CAP (weight 1.5), MEGA_SUBTIER (weight 0.5). Produces drift_pct, drift_direction (OVERWEIGHT / UNDERWEIGHT / ON_TARGET), severity (HIGH / MODERATE / LOW / NONE), and alignment_score (0.0–1.0).

**Hierarchy:** 30 nodes in a four-level tree: Asset Class → Geography → Market Cap → Mega Subtier.

#### 1.1.3 ETF / Fund Exposure Decomposition — `ETFExposureDecomposition`
**Description:** Decomposes ETF and mutual fund holdings into effective underlying exposure by geography, market cap, mega subtier, sector, style, and thematic concentration. Assigns decomposition_source (REGISTRY / DIRECT_CLASSIFICATION / HEURISTIC_FALLBACK / UNRESOLVED) and decomposition_confidence_tier (HIGH / MEDIUM / LOW / UNKNOWN). Prevents simplistic one-bucket ETF classification from distorting allocation analytics.

**Thematic overlays:** Detects independent concentration flags (AI_INFRA, SEMICONDUCTOR) that are not normalized within the standard allocation hierarchy — they represent cross-cutting risk vectors.

#### 1.1.4 Composite Portfolio Quality Score — `MultiDimensionalScore`
**Description:** Three-component weighted composite:
- Component 1 — Concentration Quality (0–40 pts): inverse HHI with top-position penalty
- Component 2 — Signal Quality (0–30 pts): fraction of holdings with BULLISH/NEUTRAL signal direction
- Component 3 — Strategic Quality (0–30 pts): fraction in strong strategic classifications (CORE_COMPOUNDER, HIGH_CONVICTION_RETAIN, THEMATIC_LEADER)

Full decomposition is persisted with component-level explanations.

#### 1.1.5 Compliance Policy Violations (CPV) — `drift_analyzer.py`
**Description:** Eight named policy rules monitored continuously:
- CPV-01: Combined Micro Cap ceiling (5%)
- CPV-02: Mega Cap Concentration ceiling (50%)
- CPV-03: Digital Assets ceiling (8%)
- CPV-04: Cash Floor floor (2%)
- CPV-05: International Allocation floor (10%)
- CPV-06: Single Asset Class Max ceiling (80%)
- CPV-07: Equities Minimum floor (40%)
- CPV-08: Fixed Income Maximum ceiling (40%)

Each rule has advisory_pp, warn_pp, and fail thresholds. Trend direction (WORSENING / IMPROVING / STABLE) computed over 7d and 30d windows.

#### 1.1.6 Portfolio Drift Trend Analysis
**Description:** Time-series tracking of all CPV rule values across historical PAR runs. Detects WORSENING / IMPROVING / STABLE trends with directional semantics calibrated per rule type (ceiling rules vs. floor rules). Stable threshold: ±0.5 percentage points.

#### 1.1.7 Cash / Liquidity Analysis
**Description:** Deployable cash computation distinguishing: ACTIVE_POSITION, CASH_EQUIVALENT (money market / sweep), PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, CLOSED_POSITION, NON_ANALYZABLE. SPAXX and similar sweep funds recognized as cash equivalents. Settlement offset logic for committed-but-unsettled positions.

#### 1.1.8 Capital Source Analysis — `capital_source_builder.py`
**Description:** Identifies available capital for redeployment across five categories: available cash, trim candidates (low-conviction holdings), reduction candidates (overweight positions), strategic exits, and deferred positions. Each source has a funding_category, priority, and deployment_eligible flag.

#### 1.1.9 Mandate-Archetype Profiling — `archetype.py`
**Description:** Maps portfolio mandate types (CONCENTRATED_ALPHA, GROWTH, BALANCED, DEFENSIVE, INCOME, REPLAY_OPTIMIZED) to YAML-based allocation target profiles. Each profile defines target weights for all 30 hierarchy nodes. Used to customize alignment analysis per portfolio objective.

---

### 1.2 Position Analytics

#### 1.2.1 CW-DAS — Conviction-Weighted Deployment Allocation Score
**Description:** The core position-ranking engine. Integrates composite score, ESS momentum, replay support, UCF tier, overweight-node penalties, and concentration headroom to produce a single deployment-eligibility rank. CCL (Core Conviction Leader) tier receives 1.75× conviction multiplier; HCA (High Conviction Anchor) receives 1.25×. √rank decay concentrates capital in top-ranked positions.

#### 1.2.2 Unified Conviction Framework (UCF) — `unified_conviction.py`
**Description:** Six-label conviction synthesis layer (read-only) operating above all source signals:
1. CORE_CONVICTION_LEADER (score 100)
2. HIGH_CONVICTION_ANCHOR (score 80)
3. DEPLOYMENT_CANDIDATE (score 60)
4. TACTICAL_GROWTH (score 40)
5. MAINTAIN (score 20)
6. TRIM_WATCH (score 0)

Synthesizes: composite_score, signal_direction, narrative_tier, replay_supported, ESS momentum, overweight-node status, concentration headroom, strategic classification. Conflict flags are advisory-only; they never override the primary UCF label. UCF rank is portfolio-wide (cross-tier).

#### 1.2.3 Multi-Provider Signal Fusion
**Description:** Integrates signals from four independent providers:
- **Zacks** (scale 1–5: Strong Buy to Strong Sell)
- **Danelfin** (scale 1–10: AI-generated, 7–10 bullish, 1–3 bearish)
- **Yahoo Finance ABR** (Average Broker Recommendation, 1.0–5.0)
- **FMP Street Consensus** (buy/hold/sell analyst count aggregation)
- **StarMine ESS** (Equity Summary Score, 0–10, momentum-oriented)

Each provider has independent normalization, staleness thresholds, and coverage governance. Provider signals are NEVER mutually substituted — missing signals are tracked explicitly as coverage gaps.

#### 1.2.4 Signal Conflict Classification — `signal_conflict_classifier.py`
**Description:** Advisory-only badge system detecting:
- CONFLICTING_SIGNAL: bullish and bearish signals coexist
- HIGH_ANALYST_DISAGREEMENT: sell ratio ≥ threshold with explicit bearish source
- HIGH_HOLD_RATIO: majority Hold/Neutral
- HOLD_CONSENSUS: aggregate label is HOLD or SELL
- SIGNIFICANT_CONFLICT: sell ratio exceeds governance threshold

SEVERITY levels: WARN and INFO. Conflict badges are surfaced to operators without modifying any score or rank.

#### 1.2.5 Analyst Consensus Transparency — `analyst_consensus.py`
**Description:** Yahoo ABR mapped to consensus labels (STRONG_BUY / BUY / MODERATE_BUY / HOLD / SELL). Consensus strength (HIGH / MODERATE / LOW) derived from ABR distance from neutral midpoint. Price target, upside %, and sourced_date tracked per symbol.

#### 1.2.6 Historical Replay Evidence Integration
**Description:** Per-symbol replay performance evidence sourced from backtested TOP_N_STRATEGY replays. Tracks symbol tier (geography/market_cap/industry), replay_id, return percentile within cohort. Industry-specific replays compatible; cross-sector ALL replays take priority. Replay percentile used as tiebreaker in UCF and CW-DAS ranking. Replay quality score validates evidence reliability before use.

#### 1.2.7 Composite Score Architecture
**Description:** Numerical composite score (0.0–1.0 normalized) maintained in analytical_universe.csv per symbol. Updated via ESS intake pipeline. Source: StarMine ESS primary, with Zacks and Danelfin providing reinforcing signals. Composite score is used in: UCF synthesis, CW-DAS ranking, alignment quality scoring, replay percentile computation.

#### 1.2.8 Strategic Profile Classification — `trim_intelligence.py`
**Description:** Per-holding strategic role classification: CORE_COMPOUNDER, THEMATIC_LEADER, STRATEGIC_CORE, HIGH_CONVICTION_RETAIN, REDUCIBLE, REDUNDANT_EXPOSURE, CONCENTRATION_RISK. Classifications feed UCF label assignment, recommendation type, and deployment queue eligibility. Trim factors stored as (name, contribution, rationale) tuples — human-readable.

#### 1.2.9 FMP Fundamental Signals — `fetch_fmp_signals.py`
**Description:** Four FMP dataset integrations: key_metrics_ttm (PE, EV/EBITDA, ROE), earnings_surprises, income_growth, grades_consensus. Fields: evToEBITDATTM, returnOnEquityTTM, earningsYieldTTM. ETFs handled gracefully (empty arrays). International ADRs and Canadian cross-listed securities supported.

---

### 1.3 Monitoring

#### 1.3.1 PIS Portfolio Change Detection — `change_detection.py`
**Description:** Quantity-driven change classification between consecutive canonical snapshot dates: NEW_HOLDING, EXITED, INCREASED, REDUCED, UNCHANGED. Portfolio-level summary: portfolio_value_change, cash_change, position_count_change, new/exited/increased/reduced/unchanged counts. Delta quantities and market value deltas persisted.

#### 1.3.2 Allocation Drift Trend Monitoring
**Description:** Continuous CPV rule monitoring across historical runs. 7d and 30d delta computation per rule. Trend classification (WORSENING / IMPROVING / STABLE) with directional semantics. Advisory thresholds trigger before compliance thresholds — early warning built in.

#### 1.3.3 Signal Staleness Monitoring
**Description:** Per-symbol, per-provider staleness tracking with threshold_days=2 default. Stale/missing signals generate DEGRADED governance status. Coverage denominator uses holdings-level analysis against PAR baseline. Staleness is distinct from missing: stale = present but outdated; missing = never received.

#### 1.3.4 Snapshot Governance Classification — `governance.py`
**Description:** Deterministic PASS / WARNING / REJECT classification for every portfolio snapshot before it enters analytics pipelines. Checks: account scope validation, portfolio value range plausibility, disallowed account types, known-bad source artifact patterns. Only PASS (preferred) and WARNING (fallback) snapshots participate in canonical selection.

#### 1.3.5 Canonical Daily Selection — `canonical_daily.py`
**Description:** Selects the authoritative snapshot for each date: PASS preferred, WARNING fallback, REJECT excluded. Preserves all immutable historical snapshots while producing a clean analytical timeline. Used by change detection, lineage, and attribution as the governance-validated baseline.

#### 1.3.6 Benchmark Attribution Monitoring — `benchmark_attribution.py`
**Description:** Tracks portfolio performance against benchmark (SPY by default). Alpha computation, source-level attribution, return series alignment. Provider symbol key matching validated before attribution math runs.

#### 1.3.7 Artifact Freshness Monitoring — `artifact_freshness.py`
**Description:** Tracks freshness of all analytical artifacts (signal snapshots, replay evidence, allocation targets). Age-based freshness tiers. Feeds dashboard health badges (system health score).

#### 1.3.8 Provider Retry and Coverage Repair
**Description:** Structured retry semantics per provider: per-symbol refresh eligibility rules, coverage gap detection, retry queue construction, coverage repair tracking. Coverage governance distinguishes between "covered today" vs "stale" vs "missing from merged smart set."

---

### 1.4 Governance

#### 1.4.1 Immutable Snapshot History
**Description:** All data — portfolio snapshots, signal snapshots, analysis runs — stored in append-only partitions under `data/history/`. No overwrite. Corrections represented as new records with explicit lineage. Source files deleted after successful intake. Snapshot indexes maintained as append-only CSV files.

#### 1.4.2 Operator Policy Registry — `operator_policy.py`
**Description:** Four policy types with lifecycle management (ACTIVE / REVOKED / EXPIRED):
- DO_NOT_SELL: symbol excluded from all sell/trim queues
- SELL_LAST: symbol ranked last within sell cohort
- CORE_ANCHOR: annotation + UI confirmation gate before trim
- PREFERRED_ACCUMULATION: boosted to top of buy deployment queue

Conflict detection between incompatible policies. Semantic warning pairs. Expiry support. Full audit trail (policies never hard-deleted). Policies modify queue ordering ONLY — intelligence scores are never modified.

#### 1.4.3 Confidence Tier Framework
**Description:** Four-tier confidence classification (HIGH / MEDIUM / LOW / UNKNOWN) used for decomposition confidence, signal quality, and evidence reliability. Confidence degrades gracefully when providers are unavailable — system continues operating at reduced confidence rather than failing. Missing data is tracked explicitly and surfaced rather than silently substituted.

#### 1.4.4 Provider Abstraction Layer — `scoring/`
**Description:** Each provider (Zacks, Danelfin, Yahoo, FMP, StarMine) isolated behind a fetch contract. Provider-specific field names and semantics cannot leak into canonical models. Normalization functions map each provider's native vocabulary to canonical SIH signals. ETF handling, international security handling, and error handling are provider-specific concerns that do not affect downstream analytical contracts.

#### 1.4.5 Deterministic SDLC Philosophy
**Description:** All transformations deterministic: same inputs → same outputs. No random seeds, no stochastic tie-breaking. Artifact-driven delivery with versioned contracts. Run-level manifests with explicit input/output boundaries. Reproducibility is a first-class requirement.

#### 1.4.6 Fail-Safe Behavior
**Description:** Missing signals → explicit coverage gap, not substituted zero. Empty provider responses (ETFs) → graceful empty handling, not error. Malformed governance → conservative default (treat as no-expiry). Unknown operational state → NON_ANALYZABLE (excluded but tracked). Every failure mode has a defined governance outcome.

#### 1.4.7 Data Quality Taxonomy
**Description:** Structured taxonomy of data quality issues: zero-value positions, duplicate rows, pending activity masquerade, SPAXX duplicate analysis, reconciliation rules (RC-02 through RC-10 documented and applied). Zero-value position governance distinguishes CLOSED from ACCOUNTING_ADJUSTMENT from NON_ANALYZABLE.

---

## Part 2 — Compass Relevance Mapping

### Classification Legend
- **A** — Directly Reusable (minimal modification)
- **B** — Reusable with Adaptation (lending-oriented transformation required)
- **C** — Conceptually Valuable (inspiration, not direct implementation)
- **D** — Not Useful for Compass

---

| # | Capability | Class | Rationale |
|---|-----------|-------|-----------|
| 1 | Concentration Risk (HHI, top-N, tier) | **A** | Directly applicable: HHI and top-N concentration are core collateral risk inputs. Lending requires exactly these metrics. |
| 2 | Multi-Dimensional Allocation Alignment | **B** | Investment mandate alignment is irrelevant; but the framework for measuring actual vs. target with severity tiers directly maps to collateral composition vs. acceptable lending thresholds. |
| 3 | ETF/Fund Exposure Decomposition | **A** | Look-through exposure analysis is essential for collateral. A borrower pledging QQQ must be evaluated on effective NVDA/MSFT/AAPL exposure, not "large-cap ETF." |
| 4 | Composite Portfolio Quality Score | **B** | The three-component scoring architecture (concentration, signal quality, strategic quality) is directly reusable. Components must be relabeled for lending: Collateral Quality Score (CQS). |
| 5 | CPV Compliance Policy Violations | **B** | Investment policy rules are different from lending covenants, but the monitoring framework (named rules, threshold tiers, trend direction, advisory/warn/fail levels) is directly reusable as Lending Covenant Monitoring. |
| 6 | Allocation Drift Trend Analysis | **A** | Portfolio drift over time is directly relevant to collateral surveillance. A collateral that is drifting toward concentration is a lending risk, not just an investment concern. |
| 7 | Cash / Liquidity Analysis | **A** | Liquidity coverage is a core lending metric. The operational state taxonomy (CASH_EQUIVALENT, PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT) maps directly to lending liquidity analysis. |
| 8 | Capital Source Analysis | **C** | The capital source classification concept (identifying what's available and why) is inspirational for collateral liquidation analysis, but the investment rotation context does not transfer. |
| 9 | Mandate-Archetype Profiling | **B** | Investment mandate types → Borrower Portfolio Archetype. A Compass borrower profile (CONSERVATIVE / BALANCED / AGGRESSIVE / CONCENTRATED) could use the same YAML-based profiling architecture. |
| 10 | CW-DAS Position Ranking | **B** | The rank-weighted proportional allocation algorithm (with conviction multipliers, √rank decay) is not a lending concept. However, adapted as a Collateral Position Quality Ranking, it could identify which positions within a pledged portfolio are highest-quality collateral. |
| 11 | Unified Conviction Framework (UCF) | **B** | The six-label conviction hierarchy and synthesis architecture are directly transferable. For lending: CORE_COLLATERAL → HIGH_QUALITY_COLLATERAL → ACCEPTABLE_COLLATERAL → MARGINAL_COLLATERAL → WATCH_COLLATERAL → IMPAIRED_COLLATERAL. |
| 12 | Multi-Provider Signal Fusion | **A** | Signal fusion is directly reusable. For Compass, providers might include credit bureau feeds, market data, analyst consensus, fundamental data. The provider abstraction layer, conflict detection, and confidence tiers all transfer. |
| 13 | Signal Conflict Classification | **A** | Directly reusable as Collateral Signal Conflict Detection. Conflicting signals on a pledged security (bullish fundamental, bearish analyst, high sell ratio) are relevant collateral risk indicators. |
| 14 | Analyst Consensus Transparency | **A** | Analyst consensus on pledged securities is directly relevant. If 35% of analysts recommend selling a position the borrower holds as collateral, that is material lending intelligence. |
| 15 | Historical Replay Evidence | **C** | Investment backtesting replay is not applicable to lending. However, the concept of evidence-backed scoring with historical performance validation is directly inspirational for LTV ratio calibration. |
| 16 | Composite Score Architecture | **A** | The per-security composite score (0.0–1.0) architecture transfers directly to a Collateral Quality Score per pledged security. Update pipeline, staleness tracking, and provider weighting all reusable. |
| 17 | Strategic Profile Classification | **B** | CORE_COMPOUNDER, THEMATIC_LEADER etc. → CORE_COLLATERAL, LIQUID_COLLATERAL, CONCENTRATED_RISK, IMPAIRED_COLLATERAL. The taxonomy changes; the classification engine and downstream routing logic are reusable. |
| 18 | FMP Fundamental Signals | **A** | Fundamental signals (EV/EBITDA, ROE, earnings surprises, analyst grades) are directly relevant for collateral quality assessment. Same API integration, same normalization. |
| 19 | Portfolio Change Detection | **A** | Directly reusable as Collateral Surveillance: new pledged positions, exits, quantity changes, value changes. Identical detection logic, identical schema. |
| 20 | Allocation Drift Monitoring | **A** | Directly reusable as Collateral Composition Drift Monitoring. Portfolio drifting toward concentration, illiquidity, or sector risk are early warning signals for lenders. |
| 21 | Signal Staleness Monitoring | **A** | Directly reusable. Stale signals on collateral are a lending governance concern. If Zacks rating on pledged NVDA is 45 days old, the lender needs to know. |
| 22 | Snapshot Governance (PASS/WARN/REJECT) | **A** | Directly reusable as Collateral Report Governance. Lending covenants require periodic collateral reporting; governance classification ensures only valid reports enter the risk pipeline. |
| 23 | Canonical Daily Selection | **A** | Directly reusable. The canonical selection algorithm (PASS preferred, WARNING fallback, REJECT excluded) is the correct approach for collateral valuation date management. |
| 24 | Benchmark Attribution | **C** | Investment alpha attribution is not a lending concept. However, relative risk measurement (portfolio vs. benchmark) is inspirational for collateral stress scenarios. |
| 25 | Artifact Freshness Monitoring | **A** | Directly reusable as Collateral Data Freshness Dashboard. Same freshness tiers, same health badge architecture. |
| 26 | Provider Retry / Coverage Repair | **A** | Directly reusable. Provider failures in a lending context must be handled with the same graceful degradation, retry semantics, and coverage gap tracking. |
| 27 | Immutable Snapshot History | **A** | Directly reusable and arguably MORE important in lending (regulatory audit requirements). Append-only immutable history is a regulatory necessity. |
| 28 | Operator Policy Registry | **B** | DO_NOT_SELL maps to DO_NOT_LIQUIDATE covenant. CORE_ANCHOR maps to EXEMPT_FROM_MARGIN_CALL (borrower agreement). PREFERRED_ACCUMULATION maps to PREFERRED_COLLATERAL type. Same lifecycle management. |
| 29 | Confidence Tier Framework | **A** | Directly reusable. HIGH/MEDIUM/LOW/UNKNOWN confidence on all Compass scoring outputs. |
| 30 | Provider Abstraction Layer | **A** | Directly reusable architecture. Compass needs the same provider isolation pattern for credit bureaus, market data vendors, and fundamental data providers. |
| 31 | Deterministic SDLC Philosophy | **A** | Directly reusable. Regulators require deterministic, reproducible loan decision artifacts. Same inputs must produce same outputs. |
| 32 | Fail-Safe Behavior | **A** | Directly reusable. Missing collateral data → explicit coverage gap, not assumed acceptable. Critical for regulatory compliance. |
| 33 | Data Quality Taxonomy | **B** | Investment-specific categories need lending-specific equivalents, but the taxonomy design approach (named rules, explicit categories, governance disposition) is directly reusable. |
| 34 | Allocation Explainability Engine | **A** | The deterministic recommendation explainability architecture (primary_reason, supporting_reasons, signal_drivers, policy_drivers, funding_drivers, philosophy_drivers) is the foundation for Compass CRS explanation generation. Direct reuse with lending-vocabulary substitution. |
| 35 | Philosophy Driver Attribution | **B** | Investment philosophies (Concentrated Alpha, Capital Rotation, Risk Reduction) map to lending risk frameworks (Concentration Risk, Liquidity Risk, Market Risk, Credit Risk). |
| 36 | ETF Security Type Classification | **A** | The operational state taxonomy (ACTIVE_POSITION, CASH_EQUIVALENT, PENDING_SETTLEMENT, ACCOUNTING_ADJUSTMENT, CLOSED_POSITION) transfers directly to collateral classification in lending. |
| 37 | Hierarchical Taxonomy | **B** | 30-node investment hierarchy → Compass collateral taxonomy. The hierarchical scoring and roll-up architecture is reusable; the nodes themselves are different. |
| 38 | Herfindahl-Hirschman Index | **A** | Industry-standard concentration measure. Directly reusable. |
| 39 | CRA Capital Rotation Advisor | **C** | Investment rotation context is not applicable. However, the liquidation sequence modeling (which positions to sell first, in what order, at what proceeds) maps conceptually to margin call collateral liquidation priority. |
| 40 | Tax-Aware Action Framework | **C** | Tax optimization is an investment concern, not a lending concern. However, the concept of action buckets (A–E) with different treatment rules maps to collateral liquidation treatment buckets. |
| 41 | Dislocation Recovery Classification | **C** | Investment dislocation recovery is not a lending concept. However, detecting positions in "temporary dislocation vs. fundamental deterioration" maps to Compass collateral impairment classification. |
| 42 | Signal Authority Framework | **A** | The concept of signal authority (which provider's signal takes precedence when conflicts arise) is directly applicable to Compass. Lending signal authority must be explicitly defined. |
| 43 | Coverage Denominator Governance | **A** | Holdings-level signal coverage tracking against PAR baseline is directly applicable. Compass must know exactly which collateral positions have current signals and which have coverage gaps. |
| 44 | Fidelity / Brokerage Integration | **B** | Fidelity CSV ingestion is specific to one custodian. The ingestion normalization architecture is reusable for any custodian format (Schwab, Fidelity, IBKR, Prime Brokerage). |
| 45 | Thematic Concentration Detection | **A** | AI_INFRA, SEMICONDUCTOR cross-cutting concentration flags are directly relevant to collateral. Lenders need to know if a portfolio has thematic concentration risk that doesn't appear in sector or geography breakdowns. |
| 46 | Lineage and Attribution Pipeline | **A** | Recommendation lineage (tracing a recommendation back to its signal source) is the foundation for Compass CRS decision audit trails. Regulators will require this. |
| 47 | Progressive Rendering Architecture | **B** | The UI progressive rendering strategy (per-endpoint timeout + fallback, fail-open behavior) is reusable for Compass dashboard design. |

---

## Part 3 — Lending-Specific Value Assessment

### 3.1 Borrower Equity Lending Value (BELV)

**Candidate inputs from SIH/PM:**
- Composite Portfolio Quality Score → portfolio quality discount factor
- Concentration Risk Tier (CRITICAL/HIGH/MODERATE/DIVERSIFIED) → concentration haircut
- ETF decomposition effective exposure → look-through LTV calculation
- Cash + CASH_EQUIVALENT percentage → high-quality liquid asset (HQLA) contribution
- Operational state taxonomy → eligible vs. ineligible collateral classification
- Top-N position dominance → single-name concentration adjustment

### 3.2 Adjusted Lending Value (ALV)

**Candidate inputs from SIH/PM:**
- HHI → concentration haircut multiplier
- Drift direction trend (WORSENING / IMPROVING / STABLE) → dynamic ALV adjustment
- Signal conflict badges → uncertainty discount
- Confidence tier (HIGH/MEDIUM/LOW) → confidence-adjusted LTV
- CPV compliance violations → covenant-breach ALV reduction triggers

### 3.3 Confidence Score

**Candidate inputs from SIH/PM:**
- Decomposition confidence tier (HIGH/MEDIUM/LOW/UNKNOWN) → collateral analysis confidence
- Provider coverage completeness → signal coverage confidence
- Snapshot governance status (PASS/WARNING) → data quality confidence
- Signal freshness age vs. staleness threshold → temporal confidence
- Multi-provider agreement vs. conflict → consensus confidence
- Artifact freshness health badge → overall system confidence

**Direct reuse:** The four-tier confidence framework is directly transferable with minimal adaptation. Apply to every Compass scoring output.

### 3.4 Stress Survival Score

**Candidate inputs from SIH/PM:**
- Portfolio Quality Score (Component 1: Concentration Quality) → baseline resilience
- ETF thematic concentration flags (AI_INFRA, SEMICONDUCTOR) → sector-specific stress vulnerability
- International/Emerging pct → geopolitical stress exposure
- Signal direction distribution (% BEARISH holdings) → quality-of-portfolio stress input
- Historical replay evidence quality → performance evidence under stress periods
- CPV-02 (Mega Cap ceiling) compliance → large-cap concentration stress

### 3.5 Margin Call Probability

**Candidate inputs from SIH/PM:**
- Drift trend direction (WORSENING) → trending toward margin call
- HHI + top-1 pct → concentration-driven volatility proxy
- Significant conflict / high analyst disagreement badges → signal uncertainty
- % holdings with BEARISH signal direction → downside pressure indicator
- UCF TRIM_WATCH count as portfolio fraction → deterioration indicator
- Thematic concentration (semiconductor, AI) → correlated drawdown risk

### 3.6 Portfolio Stability Score

**Candidate inputs from SIH/PM:**
- Allocation drift 7d/30d trend stability (STABLE classification) → stability evidence
- UCF distribution (% CORE_CONVICTION_LEADER + HIGH_CONVICTION_ANCHOR) → conviction stability
- Change detection (UNCHANGED count as fraction of total) → position stability
- Signal conflict rate (conflicting badges as pct of holdings) → analytical stability
- Provider coverage completeness → data stability
- Snapshot governance PASS rate → ingestion stability

### 3.7 Liquidity Coverage

**Candidate inputs from SIH/PM:**
- Cash percentage (CPV-04 compliance) → immediate liquidity
- CASH_EQUIVALENT classification → near-cash liquidity
- ETF vs. individual stock ratio → structural liquidity (ETFs more liquid)
- Market cap distribution (MEGA > LARGE > MID > SMALL > MICRO liquidity) → position liquidity
- Position sizing (headroom analysis) → marketability
- Concentration risk CRITICAL flag → liquidation risk indicator

### 3.8 Recovery Probability

**Candidate inputs from SIH/PM:**
- Strategic profile classifications (CORE_COMPOUNDER fraction) → recovery quality
- UCF label distribution (CCL + HCA fraction) → quality fraction
- Signal direction consensus (BULLISH fraction) → positive outlook
- Analyst consensus price target upside → recovery potential
- ESS score distribution → momentum quality
- HHI (lower = better recovery through diversification) → diversification recovery benefit

### 3.9 Collateral Quality Score

**Candidate inputs from SIH/PM:**
- Composite Portfolio Quality Score (direct adapter)
- Multi-provider consensus direction → quality consensus
- Signal conflict rate → quality uncertainty
- Concentration tier → quality penalty
- ETF decomposition confidence tier → analytical quality
- Data freshness (all providers current) → information quality

**Architecture note:** The `MultiDimensionalScore` model with its `ScoreComponent` breakdown is the direct architectural ancestor of the Compass Collateral Quality Score. Replace investment-oriented components with collateral-oriented components; preserve decomposition architecture.

### 3.10 Concentration Risk Score

**Candidate inputs from SIH/PM:**
- HHI (direct)
- top-1, top-3, top-5, top-10 pct (direct)
- single-sector maximum pct (direct)
- mega_subtier_effective_pct (direct)
- Thematic concentration flags (AI_INFRA, SEMICONDUCTOR) (direct)
- CPV-02 compliance status (direct)

**Direct reuse:** `ConcentrationRiskSummary` model is transferable with field additions (e.g., single-issuer risk for credit collateral).

### 3.11 Diversification Benefit Score

**Candidate inputs from SIH/PM:**
- 1 − HHI (inverse concentration = diversification benefit)
- Geography distribution (US + INTERNATIONAL + EMERGING spread) → geographic diversification
- Sector distribution (max single sector below threshold) → sector diversification
- Market cap distribution breadth → cap diversification
- ETF vs. individual stock mix → instrument diversification
- Thematic overlap absence → thematic diversification

### 3.12 Ongoing Monitoring Score

**Candidate inputs from SIH/PM:**
- Change detection event rate (low rate = stable collateral) → stability monitoring
- Drift trend direction across all CPV rules → compliance monitoring
- Signal staleness rate → data freshness monitoring
- Provider coverage completeness → intelligence coverage monitoring
- Governance PASS rate → quality monitoring
- Artifact freshness health score → system health monitoring

---

## Part 4 — Explainability Harvest

### 4.1 Current Explainability Architecture

The SIH/PM explainability system (`allocation_explainability.py`) produces per-recommendation records with:

```
recommendation_id        → unique recommendation identity
analysis_run_id          → links to full analytical context
symbol                   → affected security
recommendation_type      → semantic label
primary_reason           → single most-important driver sentence
supporting_reasons_json  → ordered list of supporting evidence
signal_drivers_json      → signals that triggered this recommendation
policy_drivers_json      → operator policy constraints applied
funding_drivers_json     → capital source context
philosophy_drivers_json  → investment philosophy alignment scores
explanation_version      → versioned contract for auditability
```

Philosophy scoring framework maps recommendations to five investment philosophies: Concentrated Alpha, Capital Rotation, Risk Reduction, Cash Deployment, Dislocation Recovery — each scored 0–3.

### 4.2 Directly Reusable for Compass CRS

The explainability record schema is directly reusable with vocabulary substitution:

| SIH Field | Compass CRS Equivalent |
|-----------|----------------------|
| `primary_reason` | Primary lending risk driver sentence |
| `supporting_reasons_json` | Supporting risk evidence list |
| `signal_drivers_json` | Signal risk drivers (analyst consensus, price pressure) |
| `policy_drivers_json` | Covenant and lending policy constraints |
| `funding_drivers_json` | Collateral liquidation pathway context |
| `philosophy_drivers_json` | Risk framework alignment (Concentration Risk, Liquidity Risk, Market Risk, Credit Risk) |

The driver attribution pattern — enumerate drivers, classify by type, persist with version — is exactly what bank regulators require for loan decision documentation.

### 4.3 Components to Adapt

- **Philosophy scores** → Replace with **Risk Framework scores** (Concentration Risk, Liquidity Risk, Market Risk, Volatility Risk, Credit Quality Risk)
- **Recommendation types** → Replace with CRS output types (MARGIN_CALL_RISK, CONCENTRATION_WARNING, LIQUIDITY_CONCERN, COVENANT_BREACH, QUALITY_DETERIORATION)
- **Funding drivers** → Replace with liquidation pathway drivers (MARGIN_CALL_SEQUENCE, COLLATERAL_LIQUIDATION_ORDER)

### 4.4 Components to Replace

- Replay evidence narratives → Replace with stress scenario narratives
- Investment return context → Replace with collateral value / LTV context
- Deployment queue rationale → Replace with margin call trigger rationale

### 4.5 CRS Explanation Architecture (Recommended)

```
crs_explanation_id
loan_id
analysis_run_id
portfolio_snapshot_id
snapshot_date
primary_risk_driver         ← maps from primary_reason
supporting_risk_evidence    ← maps from supporting_reasons_json
signal_risk_drivers         ← maps from signal_drivers_json
covenant_drivers            ← maps from policy_drivers_json
liquidation_drivers         ← maps from funding_drivers_json
risk_framework_alignment    ← maps from philosophy_drivers_json
explanation_version
generated_at_utc
```

---

## Part 5 — Monitoring & Surveillance Opportunities

### 5.1 Collateral Surveillance → PIS Change Detection (Direct Adapter)

The PIS `change_detection.py` module tracks NEW_HOLDING / EXITED / INCREASED / REDUCED / UNCHANGED per position per snapshot date. For Compass:

- NEW_HOLDING: Borrower added new position to pledged portfolio → review for eligibility
- EXITED: Borrower exited pledged position → recalculate collateral value
- INCREASED: Borrower added to existing position → update concentration metrics
- REDUCED: Borrower reduced position → flag if concentration threshold changing

Direct reuse. Schema unchanged. Triggers: loan officer review queue.

### 5.2 Portfolio Deterioration Monitoring → Drift Trend Analysis (Direct Adapter)

Continuous CPV-style rule monitoring over collateral composition. Lending covenant rules:
- LCV-01: Maximum single-position concentration (e.g., 20%)
- LCV-02: Minimum equity percentage (e.g., 60%)
- LCV-03: Maximum illiquid securities (e.g., 15%)
- LCV-04: Minimum investment-grade percentage
- LCV-05: Maximum single-sector concentration

Direct reuse of drift_analyzer framework. Replace CPV rules with LCV (Lending Covenant Violation) rules. Same WORSENING / IMPROVING / STABLE trend classification. Same 7d / 30d delta windows.

### 5.3 Margin Risk Monitoring → UCF Composition Tracking

Monitor the distribution of UCF-equivalent collateral quality labels over time. Alert when:
- CORE_COLLATERAL fraction falls below threshold
- IMPAIRED_COLLATERAL fraction exceeds threshold
- Overall portfolio quality score crosses advisory/warn/fail tiers

### 5.4 Risk Drift Monitoring → Composite Quality Score Trending

Implement portfolio-level quality score history. Trigger review when 30-day trend is WORSENING across multiple quality dimensions. The multi-dimensional score decomposition (concentration quality, signal quality, strategic quality) provides attribution for the drift source.

### 5.5 Early Warning Systems → Signal Conflict + Staleness Combination

Combine three signals for early warning:
1. Increasing signal conflict badge rate (CONFLICTING_SIGNAL appearing on pledged positions)
2. Signal staleness exceeding threshold (data quality degradation)
3. UCF quality label WORSENING trend

Alert: "Collateral intelligence quality deteriorating. 4 pledged positions have conflicting analyst signals. Recommend loan officer review."

### 5.6 Covenant Monitoring → CPV Framework (Direct Adapter)

Replace CPV rules with Lending Covenant Violation (LCV) rules. Same advisory/warn/fail tier structure. Same trend direction semantics. Add:
- Covenant breach trigger: automatic notification to relationship manager
- Cure period tracking (time remaining before hard default)
- Portfolio-level covenant health score

### 5.7 Loan Review Triggers → Governance + Drift Combination

Auto-generate loan review triggers when:
- Portfolio snapshot governance: WARNING (two consecutive) or REJECT (any)
- Any LCV rule status = FAIL
- WORSENING trend on ≥ 3 LCV rules simultaneously
- New CRITICAL concentration detected in pledged portfolio
- Signal conflict on position representing > X% of collateral

### 5.8 Relationship Manager Alerts → Tiered Notification Architecture

Adapt the SIH tiered governance framework (ADVISORY / WARN / FAIL) into RM notification levels:
- **ADVISORY**: FYI — collateral drift approaching threshold. No immediate action.
- **WARN**: Attention needed — collateral nearing covenant boundary. Review recommended.
- **FAIL**: Action required — covenant breach or margin call eligibility triggered.

### 5.9 Borrower Dashboard Alerts → PIS Dashboard Architecture (Direct Adapter)

The PIS Executive Dashboard (Section 6 from PIS-UI-03) with KPI header, system health badge, summary cards, and collapsible detail tables is directly reusable as a Borrower Collateral Dashboard. Replace: portfolio analytics cards → collateral quality cards; signal coverage → data quality; recommendation queue → covenant status.

---

## Part 6 — Hidden Gems / Secret Sauce Discovery

### HG-01: Confidence Tier Framework — THE Core Moat

The four-tier confidence system (HIGH / MEDIUM / LOW / UNKNOWN) applied consistently across every analytical output — decomposition confidence, signal coverage confidence, governance confidence, artifact freshness confidence — is the most transferable and most underappreciated IP asset.

**Why it's a moat:** Banks and bank examiners care intensely about the confidence and reliability of risk data. A lending system that says "LTV is 65%, CONFIDENCE: HIGH (all signals current, full provider coverage, governance PASS)" vs. "LTV is 65%, CONFIDENCE: LOW (2 of 5 signals stale, ETF decomposition HEURISTIC_FALLBACK)" gives risk managers genuinely different information. No competitor does this at this granularity.

### HG-02: ETF Look-Through Decomposition — Understated Lending Power

The ETF/fund exposure decomposition with REGISTRY / DIRECT_CLASSIFICATION / HEURISTIC_FALLBACK / UNRESOLVED sourcing and per-decomposition confidence tiers is deeply valuable for lending.

**Why it's a moat:** A borrower pledging $500K in QQQ, SPY, and VGT does not have a diversified portfolio — they have concentrated exposure to 10 mega-cap tech stocks. Most lending systems book "Large Cap ETF" at face value. A lender using this decomposition applies appropriate concentration haircuts based on effective underlying holdings. This is a genuine competitive advantage in accurate collateral valuation.

### HG-03: Multi-Provider Signal Fusion + Conflict Detection — Risk Intelligence Layer

The combination of Zacks + Danelfin + Yahoo ABR + FMP consensus fusion with explicit conflict badge detection is a transferable risk intelligence layer. Applied to collateral, it answers: "Do multiple independent analytical sources agree or disagree about the quality of this pledged security?"

**Why it's a moat:** Signal consensus on collateral is a novel application. If 3 of 4 providers are bearish on a pledged position that represents 18% of collateral, the lender knows. If only 1 of 4 providers is bearish (CONFLICTING_SIGNAL badge), the lender knows the uncertainty is high. This is qualitatively different from a single credit score.

### HG-04: Immutable History + Governance Pipeline — Regulatory Compliance Architecture

The append-only immutable snapshot history with deterministic governance classification, canonical selection, and full lineage tracing is precisely the architecture banking regulators require. Every loan decision can be traced to exactly which data, which signals, which governance status, from which snapshot, on which date.

**Why it's a moat:** Building this correctly is hard. Most fintech lending platforms have ad-hoc audit trails. SIH's architecture (built for investment intelligence) accidentally produces exactly the audit trail architecture that banking regulators demand. This is reusable at minimal marginal cost.

### HG-05: Operator Policy Registry — Human-in-the-Loop Governance Architecture

The policy registry (DO_NOT_SELL / SELL_LAST / CORE_ANCHOR / PREFERRED_ACCUMULATION) with lifecycle management, conflict detection, expiry, revocation, and full audit trail represents a sophisticated human-in-the-loop governance model. Applied to lending, this becomes lending covenant management, borrower agreement tracking, and loan officer override documentation.

**Why it's a moat:** Giving relationship managers a structured way to document "this borrower has agreed to maintain X% minimum in blue-chip equities" with version history, expiry, and audit trail is an enterprise-grade differentiator. Most platforms lack this.

### HG-06: Deterministic SDLC + Reproducibility Architecture

The principle that same inputs always produce same outputs, combined with run-level manifests, versioned contracts, and explicit input/output boundaries, is a competitive differentiator in regulated financial services.

**Why it's a moat:** Regulatory examiners require that you can reproduce any past risk calculation. Systems with non-deterministic state (caches, dynamic external queries, stochastic elements) cannot easily satisfy this requirement. SIH's architecture satisfies it by design.

### HG-07: UCF Six-Label Conviction Hierarchy — Collateral Grading Vocabulary

The six-label UCF hierarchy (CCL > HCA > DC > TG > MAINTAIN > TRIM_WATCH) with a portfolio-wide ordinal rank is a reusable collateral grading vocabulary. Adapted to lending, it becomes a Collateral Grade system (AAA → CCC equivalent for equity collateral). The synthesis algorithm — integrating multiple independent signals into a single label without overriding any source — is the right approach for regulated lending decisions.

**Why it's a moat:** Banks already use rating systems, but not for equity portfolio collateral composition. A Compass "Collateral Quality Grade" per position would be a novel, defensible product feature.

### HG-08: Portfolio Quality Decomposition — Composite Score Architecture

The `MultiDimensionalScore` with named `ScoreComponent` records (component_name, raw_score, weight, weighted_score, explanation) is directly reusable for any composite scoring need. The architecture ensures every composite score is fully decomposable — users can always see which sub-component drove the overall score.

**Why it's a moat:** "Black box" scores fail regulatory review. SIH's score decomposition architecture is inherently regulatorily defensible. Every composite score has a traceable, explainable breakdown. This is rare in practice.

### HG-09: Thematic Concentration Detection — Cross-Cutting Risk Architecture

The thematic concentration detection (AI_INFRA, SEMICONDUCTOR as exposure_thematic_mix flags that are independent of the standard hierarchy) is a sophisticated risk detection pattern. Standard concentration analysis misses correlated thematic exposure that crosses sector and geography boundaries.

**Why it's a moat:** A portfolio holding NVIDIA, AMD, Broadcom, TSMC, and SOXX is heavily exposed to semiconductor risk even though it spans US/INTERNATIONAL and Technology/other sectors. Standard HHI and sector analysis miss this. Thematic exposure detection catches it. In a lending context, this prevents a lender from thinking they're holding diversified collateral when they actually have concentrated cyclical risk.

### HG-10: Provider Abstraction Layer — Platform Extensibility

The provider abstraction architecture (each provider isolated behind a fetch contract, normalization layer, and coverage governance) allows new signal providers to be added without changing analytical models.

**Why it's a moat:** Compass will need to integrate credit bureaus, alternative data providers, bank-specific signals, and regulatory data feeds over time. The provider abstraction architecture means each new integration adds capability without breaking existing models. Competitors who hardcode provider semantics cannot change providers without rebuilding their models.

---

## Part 7 — Compass CRS Alignment

*Note: COMPASS-004 was referenced in the task specification but is not present in the current workspace. The following CRS mapping is based on the COMPASS-X01A analytical framework and the CRS construct definitions provided in the task brief.*

### 7.1 riskMetrics → SIH/PM Source Mapping

```
riskMetrics.concentrationScore   ← ConcentrationRiskSummary.herfindahl_index (inverted)
                                  ← top1_pct, top3_pct, top5_pct
                                  ← single_sector_max_pct
                                  ← mega_subtier_effective_pct

riskMetrics.liquidityScore       ← cash_equivalent_pct (from operational state)
                                  ← market_cap distribution (MEGA/LARGE high liquidity weight)
                                  ← ETF fraction (structural liquidity)
                                  ← pending_settlement exclusion logic

riskMetrics.qualityScore         ← MultiDimensionalScore.overall_score
                                  ← UCF label distribution (CCL+HCA fraction)
                                  ← signal direction distribution (BULLISH fraction)

riskMetrics.driftScore           ← Allocation drift trend (WORSENING/IMPROVING/STABLE)
                                  ← 7d and 30d delta computation
                                  ← CPV-equivalent LCV rule compliance

riskMetrics.confidenceScore      ← Provider coverage completeness
                                  ← Decomposition confidence tier
                                  ← Snapshot governance status
                                  ← Signal freshness aggregate
```

### 7.2 drivers → Philosophy Driver Attribution (Direct Map)

| CRS Driver | SIH/PM Source | Adaptation |
|-----------|--------------|-----------|
| CONCENTRATION_RISK | Concentration Quality component | Direct reuse |
| LIQUIDITY_RISK | Cash/liquidity analysis | Direct reuse |
| MARKET_RISK | Signal direction distribution | Adapt |
| QUALITY_DETERIORATION | UCF TRIM_WATCH fraction | Adapt |
| DATA_QUALITY_CONCERN | Staleness + coverage gaps | Direct reuse |
| COVENANT_PROXIMITY | CPV rule WARN/FAIL status | Direct reuse |

### 7.3 strengths → UCF High-Label Positions

Map from strategic profiles and UCF labels:
- "X positions classified as CORE_CONVICTION equivalent — high collateral quality"
- "Portfolio shows geographic diversification across US/International/Emerging"
- "Signal consensus across Zacks, Danelfin, and Yahoo — high confidence"
- "ETF decomposition HIGH confidence on all fund holdings"
- "Governance PASS on all recent portfolio submissions"

### 7.4 watchItems → Signal Conflicts + Drift + Concentration

Map from:
- Signal conflict badges (CONFLICTING_SIGNAL, HIGH_ANALYST_DISAGREEMENT)
- Drift trend WORSENING on any LCV rule
- Concentration CRITICAL or HIGH tier
- UCF TRIM_WATCH positions representing > X% of collateral
- Signal staleness exceeding threshold on top-N positions

### 7.5 recommendations → CRS Action Recommendations

| PM Recommendation Type | Compass CRS Equivalent |
|----------------------|----------------------|
| REDUCE_OVERWEIGHT | Reduce position X to comply with concentration covenant |
| DIVERSIFY_CONCENTRATION | Add diversifying assets to maintain lending eligibility |
| IMPROVE_RISK_PROFILE | Quality deterioration warning — loan officer review recommended |
| INCREASE_UNDERWEIGHT | Not applicable (borrower portfolio management is not Compass's concern) |

### 7.6 explanations → Deterministic CRS Explanations

Direct reuse of `allocation_explainability.py` schema with vocabulary substitution:

```python
# Example CRS explanation record
{
  "primary_reason": "Concentration risk: NVDA represents 23.4% of pledged collateral, "
                    "exceeding the 20% single-position covenant threshold.",
  "supporting_reasons": [
    "Top-3 positions represent 54.2% of collateral (HHI: 0.142).",
    "Thematic concentration detected: AI_INFRA exposure at 41% via NVDA + QQQ decomposition.",
    "Analyst signal conflict on NVDA: 2 of 4 providers BULLISH, 2 NEUTRAL — moderate uncertainty."
  ],
  "signal_drivers": [
    {"provider": "Zacks", "direction": "BULLISH", "score": "5 (Strong Buy)"},
    {"provider": "Danelfin", "direction": "NEUTRAL", "score": "6"},
    {"provider": "Yahoo ABR", "direction": "BULLISH", "abr": "1.8"},
    {"provider": "FMP Consensus", "direction": "NEUTRAL", "sell_ratio": "12%"}
  ],
  "covenant_drivers": ["LCV-01: Single position ceiling 20% — FAIL (23.4%)"],
  "risk_framework": {"Concentration Risk": 3, "Liquidity Risk": 1, "Market Risk": 1}
}
```

### 7.7 monitoring events → Change Detection + Drift Events

Direct reuse of PIS change detection events for Compass monitoring:
- NEW_HOLDING → alert: "New pledged position detected. Review for eligibility."
- EXITED → alert: "Pledged position liquidated. Recalculate collateral value."
- REDUCED (> 20% quantity drop) → alert: "Significant collateral reduction. Review LTV."
- WORSENING drift on LCV rules → alert: "Covenant proximity warning."

### 7.8 confidence indicators → Multi-Source Confidence Model

```
confidence_level: HIGH | MEDIUM | LOW | UNKNOWN

HIGH   = Snapshot PASS + all providers current + decomposition HIGH + no conflicts
MEDIUM = Snapshot PASS + ≤1 provider stale + decomposition MEDIUM + ≤2 conflicts
LOW    = Snapshot WARNING + multiple stale + decomposition LOW + multiple conflicts
UNKNOWN = Snapshot REJECT or missing critical signals
```

---

## Part 8 — Common Foundation Architecture

### 8.1 Shared IP Layer — Services that All Three Products Need

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED FOUNDATION PLATFORM                    │
├──────────────────┬──────────────────┬───────────────────────────┤
│  Risk Engine     │ Confidence Engine│  Explainability Engine    │
│  ─────────────── │ ──────────────── │  ─────────────────────── │
│  HHI             │ Four-tier scale  │  Driver attribution       │
│  Concentration   │ Coverage-aware   │  Primary reason           │
│  Drift detection │ Provider-aware   │  Supporting reasons       │
│  Threshold tiers │ Temporal decay   │  Score decomposition      │
│  WORSENING/IMPR  │ Governance-aware │  Version contracts        │
├──────────────────┼──────────────────┼───────────────────────────┤
│  Monitoring Eng  │ Change Detection │  Data Quality Engine      │
│  ─────────────── │ ──────────────── │  ─────────────────────── │
│  Snapshot history│ NEW/EXITED       │  PASS/WARN/REJECT govern  │
│  Governance sel  │ INCREASED/REDUCED│  Immutable history        │
│  Drift trending  │ Delta computation│  Canonical selection      │
│  Alert tiers     │ Summary reports  │  Staleness tracking       │
├──────────────────┼──────────────────┼───────────────────────────┤
│  Signal Fusion   │ Governance Engine│  Attribution Engine       │
│  ─────────────── │ ──────────────── │  ─────────────────────── │
│  Provider abstr  │ Policy registry  │  Lineage tracing          │
│  Conflict detect │ Lifecycle mgmt   │  Recommendation lineage   │
│  Authority rules │ Audit trail      │  Driver attribution       │
│  Coverage govern │ Override mgmt    │  Benchmark attribution    │
└──────────────────┴──────────────────┴───────────────────────────┘
```

### 8.2 What Should Be Shared

| Service | Shared Because |
|---------|---------------|
| Confidence Engine | All three products need confidence tiers on all outputs |
| Concentration Risk Engine (HHI, top-N) | All three products compute portfolio concentration |
| ETF Decomposition Engine | All three products need look-through exposure |
| Provider Abstraction Layer | All three products use external data providers |
| Snapshot Governance | All three products need data quality classification |
| Change Detection Engine | All three products monitor portfolio evolution |
| Explainability Engine | All three products require auditable explanations |
| Data Quality Engine | All three products need staleness and coverage tracking |
| Immutable History Store | All three products need append-only audit history |
| Confidence Tier Framework | All three products output confidence-qualified results |

### 8.3 What Should Remain Product-Specific

| Product | Product-Specific Because |
|---------|--------------------------|
| SIH | Analytical universe management, signal intake pipelines (ESS, Zacks, Danelfin), replay backtest architecture |
| Portfolio Manager | Deployment queue, conviction multipliers, mandate archetypes, capital rotation logic, tax-aware action framework |
| Compass | LTV computation, margin call logic, covenant registry, loan-level risk management, regulatory reporting |

### 8.4 Common Services API Design Principles

Shared services should expose:
1. **Deterministic computation** — identical inputs → identical outputs
2. **Confidence-qualified output** — every result includes confidence tier
3. **Explainable decomposition** — every score has component breakdown
4. **Version-controlled contracts** — breaking changes require version bump
5. **Provider-agnostic interfaces** — consumers never call providers directly
6. **Governance-aware pipeline** — all data enters through governance classification

---

## Part 9 — HarborLine Competitive Moat Assessment

### 9.1 Capabilities to Reuse Immediately

1. **HHI + Concentration Risk Framework** — ready to use, zero adaptation
2. **ETF Decomposition Engine** — ready to use, critical for collateral accuracy
3. **Snapshot Governance (PASS/WARN/REJECT)** — ready to use for collateral reports
4. **Immutable History Store** — ready to use, regulatory requirement
5. **Signal Staleness Monitoring** — ready to use, collateral intelligence quality
6. **Change Detection Engine** — ready to use, collateral surveillance
7. **Confidence Tier Framework** — ready to use, attach to all Compass outputs
8. **Provider Abstraction Architecture** — ready to use, new providers plug in
9. **Data Quality Taxonomy** — ready to use with lending-vocabulary extension
10. **Explainability Record Schema** — ready to use with vocabulary substitution

### 9.2 Capabilities to Adapt

1. **UCF → Collateral Quality Grade** — Six investment conviction labels → six collateral quality grades
2. **MultiDimensionalScore → Collateral Quality Score** — Swap investment components for lending components
3. **CPV Framework → LCV Framework** — Replace investment policy rules with lending covenant rules
4. **Operator Policy Registry → Covenant / Agreement Registry** — Same lifecycle architecture, lending vocabulary
5. **Mandate Archetypes → Borrower Portfolio Profiles** — Same YAML architecture, lending profiles
6. **Signal Fusion → Collateral Intelligence Fusion** — Add credit bureau and market stress providers
7. **Philosophy Driver Attribution → Risk Framework Attribution** — Map investment philosophies to lending risk frameworks
8. **Deployment Queue → Collateral Liquidation Priority** — Invert: identify which positions to liquidate first in margin scenario

### 9.3 Capabilities to Keep Separate

- ESS/StarMine intake pipeline (investment-specific)
- Replay backtest engine (investment-specific)
- Conviction multipliers / CW-DAS (investment-specific)
- Capital rotation advisor (investment-specific)
- Tax-aware action framework (investment-specific, unless structured finance use case)
- Strategic alpha philosophy (investment-specific)

### 9.4 Capabilities Creating Largest Competitive Moat

**Rank 1: Confidence-Qualified Composite Scoring**
No bank-grade lending system currently reports "LTV: 65%, Confidence: HIGH, decomposed into 4 components." This is the single most differentiated feature Compass could ship. Regulators will reward it; risk managers will trust it; competitors won't have it.

**Rank 2: ETF Look-Through Decomposition with Confidence Tiers**
Applying high-confidence ETF decomposition to collateral valuation produces materially more accurate LTV calculations than face-value ETF booking. This directly affects lending economics — better collateral accuracy = better loan pricing = competitive advantage.

**Rank 3: Multi-Provider Signal Fusion on Collateral**
Integrating Zacks + Danelfin + Yahoo + FMP consensus on pledged securities creates a collateral intelligence layer no lending platform currently offers. The conflict detection (CONFLICTING_SIGNAL badge on pledged securities) is a novel early warning capability.

**Rank 4: Immutable History + Deterministic Governance**
The regulatory architecture advantage. Building this correctly from inception creates a permanent advantage over competitors who build it retroactively.

**Rank 5: Explainability at Every Level**
Driver attribution, component decomposition, primary reason, supporting reasons — all persisted and versioned. This is the foundation of regulatory defensibility.

### 9.5 Capabilities Hardest for Competitors to Replicate

1. **Multi-provider fusion + conflict detection** — requires years of provider integration and signal normalization work
2. **ETF decomposition registry** — requires curating and maintaining a registry of fund holdings (ongoing operational work)
3. **Immutable governance history** — must be built from day one; retro-fitting is expensive and imperfect
4. **Deterministic explainability at transaction level** — architectural commitment required from inception
5. **UCF-equivalent conviction hierarchy** — requires tuning and calibration against real portfolio data

### 9.6 Capabilities Most Improving Lending Decision Quality

1. ETF look-through decomposition (more accurate collateral value)
2. Concentration risk (better LTV calibration)
3. Signal conflict detection (better uncertainty quantification)
4. Drift monitoring (earlier covenant intervention)
5. Change detection (real-time collateral surveillance)

### 9.7 Capabilities Most Improving Explainability

1. MultiDimensionalScore with ScoreComponent decomposition
2. Driver attribution (signal, covenant, liquidation, risk framework)
3. Primary reason + supporting reasons architecture
4. Confidence tier attached to every output
5. Philosophy/risk framework alignment scores

### 9.8 Capabilities Most Improving Bank Adoption

1. Immutable history + governance (passes regulatory examination)
2. Deterministic SDLC (reproducible calculations)
3. Explainability architecture (loan file documentation quality)
4. Operator/Covenant policy registry (relationship manager workflow)
5. Confidence-qualified outputs (risk officer trust)

---

## Top 25 Reusable Concepts

| Rank | Concept | Source | Compass Application |
|------|---------|--------|---------------------|
| 1 | Confidence Tier Framework (HIGH/MEDIUM/LOW/UNKNOWN) | SIH | Attach to every CRS output |
| 2 | HHI Concentration Risk | PAR | Core collateral concentration metric |
| 3 | ETF Look-Through Decomposition | PAR | Accurate collateral valuation |
| 4 | Multi-Provider Signal Fusion | SIH | Collateral intelligence layer |
| 5 | Signal Conflict Detection | PAR | Uncertainty quantification |
| 6 | Immutable Append-Only History | SIH | Regulatory audit architecture |
| 7 | Snapshot Governance (PASS/WARN/REJECT) | PIS | Collateral report governance |
| 8 | Deterministic Explainability Schema | PAR/SIH | CRS decision documentation |
| 9 | Driver Attribution (signal/policy/funding) | SIH | CRS driver attribution |
| 10 | Drift Trend Analysis (7d/30d, WORSENING/IMPROVING) | PAR | Covenant drift monitoring |
| 11 | Change Detection (NEW/EXITED/INCREASED/REDUCED) | PIS | Collateral surveillance |
| 12 | UCF Six-Label Hierarchy | PAR | Collateral quality grading |
| 13 | Operational State Taxonomy | PAR | Collateral classification |
| 14 | Provider Abstraction Layer | SIH | Multi-provider integration |
| 15 | Coverage Gap Tracking (vs. staleness) | SIH | Data quality governance |
| 16 | Composite Score with ScoreComponent Decomposition | PAR | Collateral Quality Score |
| 17 | Operator Policy Registry + Lifecycle | PAR | Covenant registry |
| 18 | Canonical Selection Algorithm | PIS | Collateral report selection |
| 19 | CPV Rule Framework (named rules, threshold tiers) | PAR | LCV covenant monitoring |
| 20 | Philosophy/Risk Framework Alignment Scores | SIH | Risk framework attribution |
| 21 | Thematic Concentration Detection | PAR | Cross-cutting collateral risk |
| 22 | Mandate/Archetype Profiling | PAR | Borrower portfolio profiling |
| 23 | Analyst Consensus (ABR label + strength) | PAR | Collateral quality signal |
| 24 | Fail-Safe / Graceful Degradation Architecture | SIH | Reliability in lending |
| 25 | Benchmark Attribution Framework | PIS | Portfolio vs. benchmark risk |

---

## Top 10 Hidden Gems

| Rank | Hidden Gem | Why It Matters for Compass |
|------|-----------|---------------------------|
| HG-01 | Confidence-qualified scoring at every level | No lending competitor does this. Regulators will demand it eventually. First-mover advantage. |
| HG-02 | ETF decomposition with sourcing and confidence | Prevents LTV overstatement on ETF-heavy collateral portfolios. Direct lending economics impact. |
| HG-03 | Multi-provider consensus + conflict detection | Novel risk intelligence layer on pledged securities. No current equivalent in lending. |
| HG-04 | Immutable + deterministic governance architecture | Regulatory examination passes this. Retro-fitting it later is expensive. |
| HG-05 | Operator Policy Registry with full lifecycle | Covenant and agreement management with audit trail. Relationship manager workflow differentiator. |
| HG-06 | Thematic concentration flags | AI_INFRA / SEMICONDUCTOR cross-cutting risk detection. Standard analytics miss this. |
| HG-07 | Drift trend with directional semantics | Early warning before breach. WORSENING trend is more actionable than a point-in-time snapshot. |
| HG-08 | Coverage gap tracking (distinct from staleness) | Data quality granularity. Knowing WHY coverage is incomplete improves operational response. |
| HG-09 | Driver attribution with philosophy scoring | Risk framework attribution per lending decision. Regulatorily defensible. Operationally useful. |
| HG-10 | Fail-safe graceful degradation | Missing data produces explicit flags, not silent wrong answers. Critical in regulated lending. |

---

## Final Recommendation

### Strategic Posture

HarborLine should treat SIH and Portfolio Manager not as legacy investment tools but as a mature analytical platform with approximately 70% reusable IP for lending use cases. The marginal cost of adapting this IP to Compass is dramatically lower than building equivalent capabilities from scratch.

The three highest-ROI actions are:

**1. Establish a Shared Foundation Layer immediately**
Extract the following into a shared library before building Compass: Concentration Engine (HHI, top-N, tier), Confidence Engine (four tiers, coverage-aware), Explainability Engine (driver attribution schema), Governance Engine (PASS/WARN/REJECT), Change Detection Engine, and Data Quality Engine. These are product-agnostic capabilities. Building them three times independently is wasteful and creates divergence.

**2. Adapt the UCF as the Compass Collateral Quality Grade**
The six-label UCF hierarchy is the right architecture for collateral grading. Replace investment conviction labels with collateral quality labels. Preserve the synthesis algorithm. This gives Compass an explainable, auditable, multi-signal collateral grading system within weeks, not months.

**3. Deploy ETF Decomposition as a core Compass capability from day one**
The ETF decomposition registry is production-validated. Applying it to collateral valuation produces more accurate LTV calculations than any competitor currently offers. Ship this as a differentiating feature from Compass v1.

### What Compass Uniquely Needs (Not in SIH/PM)

- LTV computation model (loan-specific)
- Margin call trigger logic (lending-specific)
- Covenant breach detection and cure period tracking (lending-specific)
- Regulatory reporting artifacts (lending-specific)
- Credit bureau provider integrations (lending-specific)
- Loan file documentation generation (lending-specific)

### Target Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                   HARBORLINE PLATFORM                        │
│                                                              │
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │    SIH      │  │ PORTFOLIO MGR  │  │    COMPASS       │  │
│  │             │  │                │  │                  │  │
│  │ Universe    │  │ Conviction     │  │ LTV Engine       │  │
│  │ ESS Intake  │  │ Deployment Q   │  │ Margin Call      │  │
│  │ Replay      │  │ Cap Rotation   │  │ Covenant Mgmt    │  │
│  │ Signal Arch │  │ Tax Framework  │  │ Regulatory Rpts  │  │
│  └──────┬──────┘  └───────┬────────┘  └────────┬─────────┘  │
│         │                 │                    │             │
│         └─────────────────┼────────────────────┘             │
│                           │                                  │
│         ┌─────────────────▼────────────────────┐             │
│         │         SHARED FOUNDATION             │             │
│         │                                      │             │
│         │  Concentration Engine                │             │
│         │  ETF Decomposition Engine            │             │
│         │  Signal Fusion + Conflict Engine     │             │
│         │  Confidence Engine                   │             │
│         │  Explainability Engine               │             │
│         │  Governance Engine                   │             │
│         │  Change Detection Engine             │             │
│         │  Data Quality Engine                 │             │
│         │  Monitoring Engine                   │             │
│         │  Provider Abstraction Layer          │             │
│         │  Immutable History Store             │             │
│         └──────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

### Final Answer — What Belongs in the Shared Platform

**Elevate to Shared Platform:**
Concentration analysis, ETF decomposition, signal fusion, conflict detection, confidence tiers, explainability schema, governance classification, change detection, drift monitoring, alert tiers, immutable history, provider abstraction, data quality taxonomy, coverage governance, artifact freshness monitoring, operator/covenant policy registry.

**Keep in SIH:**
ESS intake, replay backtest, Zacks/Danelfin intake, analytical universe management, signal authority precedence for investment context.

**Keep in Portfolio Manager:**
CW-DAS, UCF synthesis for investment conviction, mandate archetype profiles, capital rotation, tax-aware frameworks, deployment queue, conviction multipliers.

**Keep in Compass:**
LTV computation, margin call logic, covenant breach and cure tracking, credit risk modeling, regulatory reporting, loan file generation, borrower credit integration.

**Rationale:** The shared platform should contain everything that is about *understanding a portfolio* — its composition, quality, risk, data integrity, and evolution over time. Each product layer should contain only what is specific to its domain: investment optimization for SIH/PM; credit risk management for Compass. The shared foundation creates a compounding analytical advantage: every improvement to concentration analysis, explainability, or confidence scoring benefits all three products simultaneously.

---

*Document generated: 2026-06-15*  
*Source analysis: SIH v23.0A+ / Portfolio Manager Phase 7.7A+ / PIS Phase 1*  
*Status: Strategic IP Harvest — For HarborLine Compass Development Planning*
