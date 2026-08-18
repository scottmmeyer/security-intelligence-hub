(() => {
  const SCORE_RE = /\b(10|[1-9])\s*out\s+of\s+10\b/gi;
  const ISO_DATE_RE = /\b(\d{4}-\d{2}-\d{2})\b/;
  const LAST_UPDATE_LINE_RE = /\b(last\s+update|updated?)\b[^\n]*/i;
  const MONTH_DAY_YEAR_RE = /\b([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})\b/i;
  const DAY_MONTH_YEAR_RE = /\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b/i;

  const MONTHS = {
    jan: 1,
    january: 1,
    feb: 2,
    february: 2,
    mar: 3,
    march: 3,
    apr: 4,
    april: 4,
    may: 5,
    jun: 6,
    june: 6,
    jul: 7,
    july: 7,
    aug: 8,
    august: 8,
    sep: 9,
    sept: 9,
    september: 9,
    oct: 10,
    october: 10,
    nov: 11,
    november: 11,
    dec: 12,
    december: 12
  };

  function toIsoDate(maybeDateText) {
    const raw = String(maybeDateText || "").trim();
    if (!raw) return null;
    const iso = raw.match(ISO_DATE_RE);
    if (iso) return iso[1];

    const mdy = raw.match(MONTH_DAY_YEAR_RE);
    if (mdy) {
      const month = MONTHS[(mdy[1] || "").toLowerCase()];
      const day = Number(mdy[2]);
      const year = Number(mdy[3]);
      if (!month || !Number.isInteger(day) || !Number.isInteger(year)) return null;
      if (day < 1 || day > 31 || year < 2000 || year > 2100) return null;
      const mm = String(month).padStart(2, "0");
      const dd = String(day).padStart(2, "0");
      return `${year}-${mm}-${dd}`;
    }

    const dmy = raw.match(DAY_MONTH_YEAR_RE);
    if (dmy) {
      const day = Number(dmy[1]);
      const month = MONTHS[(dmy[2] || "").toLowerCase()];
      const year = Number(dmy[3]);
      if (!month || !Number.isInteger(day) || !Number.isInteger(year)) return null;
      if (day < 1 || day > 31 || year < 2000 || year > 2100) return null;
      const mm = String(month).padStart(2, "0");
      const dd = String(day).padStart(2, "0");
      return `${year}-${mm}-${dd}`;
    }

    const parts = raw.replace(",", "").split(/\s+/);
    if (parts.length < 3) return null;
    const month = MONTHS[(parts[0] || "").toLowerCase()];
    const day = Number(parts[1].replace(/(?:st|nd|rd|th)$/i, ""));
    const year = Number(parts[2]);
    if (!month || !Number.isInteger(day) || !Number.isInteger(year)) return null;
    if (day < 1 || day > 31 || year < 2000 || year > 2100) return null;
    const mm = String(month).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    return `${year}-${mm}-${dd}`;
  }

  function extractScores(text) {
    const values = [];
    let m;
    while ((m = SCORE_RE.exec(text)) !== null) {
      const raw = Number(m[1]);
      if (Number.isInteger(raw) && raw >= 1 && raw <= 10) {
        values.push(raw);
      }
    }
    return values;
  }

  function extractSourcedDate(text) {
    const iso = text.match(ISO_DATE_RE);
    if (iso) return iso[1];

    const updateLine = text.match(LAST_UPDATE_LINE_RE);
    if (updateLine && updateLine[0]) {
      const parsed = toIsoDate(updateLine[0]);
      if (parsed) return parsed;
    }

    const parsedAny = toIsoDate(text);
    if (parsedAny) return parsedAny;

    return null;
  }

  function pathInfo(url) {
    try {
      const u = new URL(url);
      const path = u.pathname || "";
      const single = path.match(/^\/stock\/([A-Za-z0-9.\-]+)/i);
      if (single) {
        const symbol = single[1].toUpperCase();
        if (/^[A-Z][A-Z0-9.]{0,4}$/.test(symbol)) {
          return { type: "single", symbols: [symbol] };
        }
        return { type: "single", symbols: [] };
      }
      const pair = path.match(/^\/stocks\/([A-Za-z0-9.\-]+)-vs-([A-Za-z0-9.\-]+)/i);
      if (pair) {
        const left = pair[1].toUpperCase();
        const right = pair[2].toUpperCase();
        if (/^[A-Z][A-Z0-9.]{0,4}$/.test(left) && /^[A-Z][A-Z0-9.]{0,4}$/.test(right)) {
          return { type: "pair", symbols: [left, right] };
        }
        return { type: "pair", symbols: [] };
      }
      return { type: "unknown", symbols: [] };
    } catch (_err) {
      return { type: "unknown", symbols: [] };
    }
  }

  function parseDanelfinCapture({ url, text, expectedSymbols = [] }) {
    const info = pathInfo(url);
    const scores = extractScores(text || "");
    const sourcedDate = extractSourcedDate(text || "");
    const challenge = /cloudflare|checking\s+your\s+browser|verify\s+you\s+are\s+human/i.test(text || "");

    if (challenge) {
      return {
        challenge: true,
        sourced_date: sourcedDate,
        observations: []
      };
    }

    const symbols = info.symbols.length ? info.symbols : expectedSymbols.map((s) => String(s || "").toUpperCase()).filter(Boolean);

    if (info.type === "single") {
      if (scores.length < 1 || symbols.length < 1) {
        throw new Error("single-page capture failed: missing symbol or score");
      }
      return {
        challenge: false,
        sourced_date: sourcedDate,
        observations: [
          {
            symbol: symbols[0],
            danelfin_raw: scores[0],
            sourced_date: sourcedDate
          }
        ]
      };
    }

    if (scores.length < 2 || symbols.length < 2) {
      throw new Error("pair-page capture failed: missing symbols or scores");
    }

    return {
      challenge: false,
      sourced_date: sourcedDate,
      observations: [
        {
          symbol: symbols[0],
          danelfin_raw: scores[0],
          sourced_date: sourcedDate
        },
        {
          symbol: symbols[1],
          danelfin_raw: scores[1],
          sourced_date: sourcedDate
        }
      ]
    };
  }

  self.DanelfinDomParser = {
    parseDanelfinCapture
  };
})();
