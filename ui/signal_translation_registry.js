/* SIGNAL-UX-01 — Native Provider Translation Registry
 * Centralized mappings: native rating → provider meaning → normalized score → direction
 *
 * Governance: display-only. No scoring, ranking, recommendation, CW-DAS, ESS,
 * CRA, PAP, UCF, or replay calculations are modified.
 *
 * Used by: ui/portfolio_alignment/app.js, ui/ucf_operator_dashboard/index.html
 */

"use strict";

// ─────────────────────────────────────────────────────────────────────────────
// Zacks — Normalized score: 5.0 = best (#1 Strong Buy), 1.0 = worst (#5 Strong Sell)
// Native rank = Math.round(6 - normalized_score)
// ─────────────────────────────────────────────────────────────────────────────

const _SIH_ZACKS_RANK_LABELS = [
  /* 0 */ "",
  /* 1 */ "Strong Buy",
  /* 2 */ "Buy",
  /* 3 */ "Hold",
  /* 4 */ "Sell",
  /* 5 */ "Strong Sell",
];

const _SIH_ZACKS_RANK_DIRECTIONS = [
  /* 0 */ "",
  /* 1 */ "Bullish",
  /* 2 */ "Bullish",
  /* 3 */ "Neutral",
  /* 4 */ "Bearish",
  /* 5 */ "Bearish",
];

const _SIH_ZACKS_RANK_DIR_CLASS = [
  /* 0 */ "",
  /* 1 */ "bullish",
  /* 2 */ "bullish",
  /* 3 */ "neutral",
  /* 4 */ "bearish",
  /* 5 */ "bearish",
];

/**
 * Derive native Zacks rank (1–5) from normalized score (1–5 ascending).
 * @param {number|string} normalizedScore
 * @returns {number|null}
 */
function _sihZacksNativeRank(normalizedScore) {
  const z = parseFloat(normalizedScore);
  if (isNaN(z)) return null;
  return Math.round(6 - z);
}

/**
 * Full translation object for a Zacks normalized score.
 * @param {number|string} normalizedScore
 * @returns {{ nativeRating, meaning, normalizedScore, direction, dirClass }|null}
 */
function _sihZacksTranslate(normalizedScore) {
  const z = parseFloat(normalizedScore);
  if (isNaN(z)) return null;
  const rank = Math.round(6 - z);
  if (rank < 1 || rank > 5) return null;
  return {
    nativeRating:    `#${rank}`,
    meaning:         _SIH_ZACKS_RANK_LABELS[rank],
    normalizedScore: z.toFixed(1),
    direction:       _SIH_ZACKS_RANK_DIRECTIONS[rank],
    dirClass:        _SIH_ZACKS_RANK_DIR_CLASS[rank],
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Danelfin — Raw score: 1–10 (10 = most bullish)
// Normalized: raw / 2 → 0.5–5.0
// ─────────────────────────────────────────────────────────────────────────────

const _SIH_DANELFIN_MEANING = [
  /* 0  */ null,
  /* 1  */ { meaning: "Strong Bearish", direction: "Bearish", dirClass: "bearish" },
  /* 2  */ { meaning: "Strong Bearish", direction: "Bearish", dirClass: "bearish" },
  /* 3  */ { meaning: "Strong Bearish", direction: "Bearish", dirClass: "bearish" },
  /* 4  */ { meaning: "Bearish",        direction: "Bearish", dirClass: "bearish" },
  /* 5  */ { meaning: "Bearish",        direction: "Bearish", dirClass: "bearish" },
  /* 6  */ { meaning: "Neutral",        direction: "Neutral", dirClass: "neutral" },
  /* 7  */ { meaning: "Neutral",        direction: "Neutral", dirClass: "neutral" },
  /* 8  */ { meaning: "Bullish",        direction: "Bullish", dirClass: "bullish" },
  /* 9  */ { meaning: "Bullish",        direction: "Bullish", dirClass: "bullish" },
  /* 10 */ { meaning: "Strong Bullish", direction: "Bullish", dirClass: "bullish" },
];

/**
 * Derive native Danelfin raw score (1–10) from normalized (1–5).
 * @param {number|string} normalizedScore
 * @returns {number|null}
 */
function _sihDanelfinNativeRaw(normalizedScore) {
  const d = parseFloat(normalizedScore);
  if (isNaN(d)) return null;
  return Math.round(d * 2);
}

/**
 * Full translation object for a Danelfin normalized score.
 * @param {number|string} normalizedScore
 * @returns {{ nativeRating, meaning, normalizedScore, direction, dirClass }|null}
 */
function _sihDanelfinTranslate(normalizedScore) {
  const d = parseFloat(normalizedScore);
  if (isNaN(d)) return null;
  const raw = Math.round(d * 2);
  if (raw < 1 || raw > 10) return null;
  const m = _SIH_DANELFIN_MEANING[raw];
  return {
    nativeRating:    `${raw} / 10`,
    meaning:         m.meaning,
    normalizedScore: d.toFixed(2),
    direction:       m.direction,
    dirClass:        m.dirClass,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// ESS (Equity Summary Score) — text labels are the native representation
// ─────────────────────────────────────────────────────────────────────────────

const _SIH_ESS_MAP = {
  "VERY_BULLISH": { meaning: "Very Bullish",  normalizedScore: "5.0", direction: "Bullish", dirClass: "bullish" },
  "BULLISH":      { meaning: "Bullish",        normalizedScore: "4.0", direction: "Bullish", dirClass: "bullish" },
  "NEUTRAL":      { meaning: "Neutral",        normalizedScore: "3.0", direction: "Neutral", dirClass: "neutral" },
  "BEARISH":      { meaning: "Bearish",        normalizedScore: "2.0", direction: "Bearish", dirClass: "bearish" },
  "VERY_BEARISH": { meaning: "Very Bearish",   normalizedScore: "1.0", direction: "Bearish", dirClass: "bearish" },
};

/**
 * Full translation object for an ESS text label.
 * @param {string} essText  e.g. "VERY_BULLISH", "BEARISH"
 * @returns {{ nativeRating, meaning, normalizedScore, direction, dirClass }|null}
 */
function _sihEssTranslate(essText) {
  if (!essText) return null;
  const key = String(essText).toUpperCase().replace(/[\s-]/g, "_");
  const m = _SIH_ESS_MAP[key];
  if (!m) return null;
  return {
    nativeRating:    m.meaning,     // ESS native label IS the meaning
    meaning:         m.meaning,
    normalizedScore: m.normalizedScore,
    direction:       m.direction,
    dirClass:        m.dirClass,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Analyst Consensus / Yahoo ABR
// ABR scale: 1.0 = Strong Buy, 5.0 = Strong Sell (inverted — lower is more bullish)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Full translation object for Yahoo ABR / analyst consensus label.
 * @param {number|string|null} abrValue  e.g. 1.5
 * @param {string|null}        consensusLabel  e.g. "STRONG_BUY"
 * @returns {{ nativeRating, meaning, normalizedScore, direction, dirClass }|null}
 */
function _sihAnalystConsensusTranslate(abrValue, consensusLabel) {
  const abr = parseFloat(abrValue);
  let meaning, direction, dirClass, nativeRating;

  if (!isNaN(abr) && abr >= 1.0 && abr <= 5.0) {
    if      (abr <= 1.5) { meaning = "Strong Buy";   direction = "Bullish"; dirClass = "bullish"; }
    else if (abr <= 2.0) { meaning = "Buy";           direction = "Bullish"; dirClass = "bullish"; }
    else if (abr <= 2.5) { meaning = "Moderate Buy";  direction = "Bullish"; dirClass = "bullish"; }
    else if (abr <= 3.5) { meaning = "Hold";          direction = "Neutral"; dirClass = "neutral"; }
    else                  { meaning = "Sell";          direction = "Bearish"; dirClass = "bearish"; }
    nativeRating = `ABR ${abr.toFixed(2)}`;
  } else if (consensusLabel) {
    const l = consensusLabel.toUpperCase();
    if      (l.includes("STRONG_BUY"))    { meaning = "Strong Buy";   direction = "Bullish"; dirClass = "bullish"; }
    else if (l.includes("MODERATE_BUY"))  { meaning = "Moderate Buy"; direction = "Bullish"; dirClass = "bullish"; }
    else if (l.includes("BUY"))           { meaning = "Buy";          direction = "Bullish"; dirClass = "bullish"; }
    else if (l.includes("HOLD"))          { meaning = "Hold";         direction = "Neutral"; dirClass = "neutral"; }
    else if (l.includes("SELL"))          { meaning = "Sell";         direction = "Bearish"; dirClass = "bearish"; }
    else                                  { return null; }
    nativeRating = consensusLabel.replace(/_/g, " ");
  } else {
    return null;
  }

  const normalizedScore = !isNaN(abr) ? Math.max(1.0, Math.min(5.0, 6.0 - abr)).toFixed(2) : "—";
  return { nativeRating, meaning, normalizedScore, direction, dirClass };
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared display color helpers
// ─────────────────────────────────────────────────────────────────────────────

const _SIH_DIR_COLORS = {
  bullish: "var(--green, #1a7c4f)",
  neutral: "var(--muted, #888)",
  bearish: "var(--sev-high, #c0392b)",
  unknown: "var(--muted, #888)",
};

/** Return an inline CSS color style string for a direction class. */
function _sihDirColorStyle(dirClass) {
  return `color:${_SIH_DIR_COLORS[dirClass] || _SIH_DIR_COLORS.unknown};font-weight:600`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared HTML render helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compact inline translation badge (single line):
 *   "#5 · Strong Sell · 1.0 · Bearish"
 */
function _sihTranslationInline(t) {
  if (!t) return "—";
  return `<span class="nt-native">${t.nativeRating}</span>`
       + `<span class="nt-sep"> · </span>`
       + `<span class="nt-meaning">${t.meaning}</span>`
       + `<span class="nt-sep"> · </span>`
       + `<span class="nt-norm">${t.normalizedScore}</span>`
       + `<span class="nt-sep"> · </span>`
       + `<span class="nt-dir" style="${_sihDirColorStyle(t.dirClass)}">${t.direction}</span>`;
}

/**
 * Four-row vertical translation block for security detail cards:
 *   Native Rating: #5
 *   Provider Opinion: Strong Sell
 *   Normalized Score: 1.0
 *   CW-DAS Direction: Bearish
 */
function _sihTranslationDetailBlock(t, providerLabel) {
  if (!t) return "";
  return `<div class="nt-detail-block">
    <div class="nt-detail-provider">${providerLabel || ""}</div>
    <div class="nt-detail-row"><span class="nt-detail-lbl">Native Rating</span><span class="nt-detail-val">${t.nativeRating}</span></div>
    <div class="nt-detail-row"><span class="nt-detail-lbl">Provider Opinion</span><span class="nt-detail-val">${t.meaning}</span></div>
    <div class="nt-detail-row"><span class="nt-detail-lbl">Normalized Score</span><span class="nt-detail-val">${t.normalizedScore}</span></div>
    <div class="nt-detail-row"><span class="nt-detail-lbl">CW-DAS Direction</span><span class="nt-detail-val nt-dir" style="${_sihDirColorStyle(t.dirClass)}">${t.direction}</span></div>
  </div>`;
}

/**
 * Evidence string for CRA / recommendation context:
 *   "Zacks #5 (Strong Sell) · Normalized: 1.0 · Direction: Bearish [Zacks Direct, 2026-06-17]"
 */
function _sihTranslationEvidenceStr(providerName, t, sourceLabel, sourceDate) {
  if (!t) return null;
  return `${providerName} ${t.nativeRating} (${t.meaning}) · Normalized: ${t.normalizedScore} · Direction: ${t.direction} [${sourceLabel}, ${sourceDate}]`;
}

/**
 * Conflict/dislocation panel cell:
 *   "Very Bullish (5.0)"  or  "Strong Sell (1.0)"
 */
function _sihTranslationConflictCell(t) {
  if (!t) return "—";
  if (t.nativeRating === t.meaning) {
    // ESS-style: meaning IS the rating — just show "Very Bullish (5.0)"
    return `<span style="${_sihDirColorStyle(t.dirClass)}">${t.meaning}</span> <span style="font-size:0.72rem;color:var(--muted)">(${t.normalizedScore})</span>`;
  }
  // Zacks/Danelfin: show native + meaning + score
  return `<span class="nt-native" style="font-weight:600">${t.nativeRating}</span>`
       + ` <span class="nt-meaning">${t.meaning}</span>`
       + ` <span style="font-size:0.72rem;color:var(--muted)">(${t.normalizedScore})</span>`;
}
