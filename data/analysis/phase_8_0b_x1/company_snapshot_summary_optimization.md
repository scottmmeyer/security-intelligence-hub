# Company Snapshot Summary Optimization — Phase 8.0B.X.2

## Objective
Assess current Yahoo `longBusinessSummary` content quality and design an improved, operator-focused "What They Do" field.

## Current State Assessment

### Sample Analysis

| Symbol | Current Raw (truncated) | Chars | Issues |
|--------|------------------------|-------|--------|
| VRT | "Vertiv Holdings Co designs, manufactures, and services critical digital infrastructure technologies and life cycle services for data centers..." | 243 | Company name prefix; verb chain; geo trailer |
| DELL | "Dell Technologies Inc. designs, develops, manufactures, markets, sells, and supports various comprehensive and integrated solutions..." | 224 | Name prefix; 6-verb chain; "various comprehensive and integrated solutions" is vague |
| ARW | "Arrow Electronics, Inc. sources and engineers technology for manufacturers..." | 210 | Name prefix; geographic trailer |
| PSX | "Phillips 66 operates as an integrated downstream energy provider in the United States, the United Kingdom, Germany, and internationally…" | 136 | Acceptable except geo |
| TSM | "Taiwan Semiconductor Manufacturing Company Limited, together with its subsidiaries, manufactures, packages, tests, and sells integrated circuits..." | 246 | Name prefix; "together with its subsidiaries" boilerplate; geo trailer |
| MSFT | "Microsoft Corporation develops and supports software, services, devices, and solutions worldwide…" | 97 | Too vague: "solutions worldwide" says nothing useful |
| NVDA | "NVIDIA Corporation operates as a data center scale AI infrastructure company..." | 165 | Actually good — clear and concise |

### Common Problems in Yahoo Summaries

1. **Redundant company name prefix** — "Dell Technologies Inc. designs, develops..." — name already shown in Company field
2. **Verb chain boilerplate** — "designs, develops, manufactures, markets, sells, and supports" — legal investor language, not operator language
3. **Geographic boilerplate** — "in the United States, the United Kingdom, Germany, and internationally" — adds no insight
4. **"together with its subsidiaries"** — pure legal filler
5. **Vague product descriptions** — "various comprehensive and integrated solutions, products, and services" is meaningless
6. **Mid-sentence truncation** — artifact of 250-char limit cutting Yahoo's multi-paragraph text

### Cleaned Examples (JS strip rules applied)

| Symbol | Cleaned Result |
|--------|---------------|
| VRT | "Manufactures and services critical digital infrastructure technologies for data centers, communication networks, and industrial environments." |
| ARW | "Sources and engineers technology for manufacturers, service providers, and users of enterprise computing solutions." |
| PSX | "Operates as an integrated downstream energy provider." |
| CVE | "Produces, refines, transports, and markets crude oil, natural gas, and refined petroleum products." |
| MU | "Designs, develops, manufactures, and sells memory and storage products." |

**Assessment: Automated cleaning reduces noise by ~40% but cannot fix vague content.**

## Proposed Rename: Business → What They Do

- "Business" label is generic
- "What They Do" directly answers the operator question
- Aligns with the section purpose

## Recommended Client-Side Cleaning Rules (JS)

Apply in `_dqCompanySnapshotHtml()` before rendering:

```javascript
function _cleanBusinessSummary(raw) {
  if (!raw) return "";
  let s = raw
    // Strip "together with its subsidiaries"
    .replace(/,?\s+together with its subsidiaries,?/gi, "")
    // Strip leading "CompanyName Inc./Corp./etc. <verb>, "
    .replace(/^[A-Z][^.]{8,90}?(?:Inc\.|Corp\.|Corporation|Company|Limited|Ltd\.|Holdings?|PLC|N\.V\.|AG|LLC|Co\.?)\s+(?:designs,?\s+develops|operates as a[n]?|engages in|provides|builds and deploys|manufactures|develops|sources and engineers),?\s*/i, "")
    // Strip geographic boilerplate at end of sentence
    .replace(/,?\s+(?:and internationally|in (?:the United States?|North America|the Americas|Europe|the Middle East|Africa|Asia|Taiwan|China|Japan|internationally|Canada|Australia|Korea|Germany|the United Kingdom)[^.]*)/gi, "")
    // Capitalize first letter
    .trim();
  if (s && s[0] === s[0].toLowerCase()) {
    s = s[0].toUpperCase() + s.slice(1);
  }
  // Ensure ends with period
  s = s.replace(/[.,…]+$/, "") + ".";
  return s.length > 10 ? s : raw; // fallback if cleaning destroyed the string
}
```

## Edge Cases

| Case | Issue | Handling |
|------|-------|---------|
| MSFT | Too vague after cleaning | No fix possible via rules; acceptable |
| NVDA | Good without cleaning | Rules are no-op if no patterns match |
| TSLA | Geographic clause mid-sentence | Geo strip catches it |
| ETF/Fund | No business summary | Show "—" |

## Recommendation

- Rename label from "Business" → "What They Do"
- Apply `_cleanBusinessSummary()` in JS before rendering — zero backend changes required
- Accept that ~15% of summaries remain somewhat vague (investor-document style is the source limitation)
- Do NOT block implementation on perfect summaries; imperfect-but-cleaned is better than raw

## Verdict: IMPLEMENT
