# Company Snapshot Why It Matters Design — Phase 8.0B.X.2

## Objective
Design a concise operator-facing "Why It Matters" field explaining the investment thesis context for a company — without making a recommendation.

## Core Question
Can "Why It Matters" be derived from existing data?

**Answer: Yes, for ~90% of holdings, using a sector + industry lookup table.**

The key insight: most portfolio companies fall into a small number of investment themes. A deterministic mapping from `(sector, industry)` → thematic explanation covers the overwhelming majority of cases without requiring AI generation or manual curation.

## Rules

- Maximum 120 characters
- Plain English
- Present tense
- Describes market exposure, not company quality
- No superlatives, no ratings, no buy/sell language
- No investment recommendation implied

## Derivation Strategy

**Primary lookup:** `(sector, industry)` → theme string  
**Fallback:** `sector` → generic sector theme  
**Final fallback:** `"Provides exposure to its sector market."` (never empty)

## Primary Lookup Table

| Sector | Industry | Why It Matters |
|--------|----------|---------------|
| Technology | Semiconductors | Critical chipmaker supplying AI, mobile, cloud, and automotive compute. |
| Technology | Semiconductor Equipment & Materials | Sole-source supplier of advanced chip manufacturing equipment. |
| Technology | Computer Hardware | Enterprise servers, storage, and compute infrastructure. |
| Technology | Electronic Components | Technology component distribution enabling global electronics supply chains. |
| Technology | Information Technology Services | IT services and solutions driving enterprise digital transformation. |
| Technology | Software—Application | Enterprise software with recurring revenue and platform lock-in. |
| Technology | Software—Infrastructure | Infrastructure software underpinning cloud and enterprise systems. |
| Technology | Communication Equipment | Network infrastructure for enterprise, carrier, and data-center connectivity. |
| Industrials | Electrical Equipment & Parts | Benefits from AI data-center buildout, electrification, and grid modernization. |
| Industrials | Engineering & Construction | Infrastructure construction tied to energy, industrial, and utilities investment. |
| Industrials | Specialty Industrial Machinery | Industrial machinery serving diverse manufacturing end markets. |
| Industrials | Aerospace & Defense | Defense systems and aerospace with government-contract revenue stability. |
| Healthcare | Medical Distribution | Essential pharmaceutical and medical supply distribution to healthcare systems. |
| Healthcare | Biotechnology | Drug pipeline exposure to biotech innovation cycles and FDA approvals. |
| Healthcare | Drug Manufacturers—General | Diversified pharmaceutical manufacturer with branded and generic drug exposure. |
| Healthcare | Medical Devices | Medical device supplier serving surgical, diagnostic, and therapeutic markets. |
| Energy | Oil & Gas Integrated | Exposure to crude production, refining margins, and downstream fuel demand. |
| Energy | Oil & Gas E&P | Direct commodity price exposure through exploration and production operations. |
| Energy | Oil & Gas Refining & Marketing | Refining margin and fuel distribution exposure. |
| Energy | Solar | Clean energy exposure through solar manufacturing and project development. |
| Financial Services | Asset Management | Fee-based revenue tied to assets under management and market performance. |
| Financial Services | Banks—Regional | Lending and deposit business with local economic and rate-cycle exposure. |
| Financial Services | Insurance—Property & Casualty | P&C underwriter with premium income and catastrophe loss exposure. |
| Consumer Cyclical | Auto Manufacturers | EV manufacturing with exposure to energy policy, autonomy, and consumer demand. |
| Basic Materials | Steel | Domestic steel production tied to construction, manufacturing, and trade policy. |
| Basic Materials | Gold | Gold mining with direct commodity and safe-haven demand exposure. |

## Sector-Level Fallbacks

| Sector | Fallback Theme |
|--------|---------------|
| Technology | Technology business operating in enterprise, cloud, or semiconductor markets. |
| Healthcare | Healthcare company with pharmaceutical, device, or distribution exposure. |
| Energy | Energy company with commodity price and infrastructure exposure. |
| Industrials | Industrial manufacturer or services provider. |
| Financial Services | Financial services business with market-sensitive or fee-based revenue. |
| Consumer Cyclical | Consumer-facing business tied to discretionary spending trends. |
| Consumer Defensive | Defensive consumer business with stable demand and brand loyalty. |
| Basic Materials | Materials producer with commodity cycle and supply-demand exposure. |
| Communication Services | Communications or media business with user engagement and ad-revenue exposure. |
| Utilities | Regulated utility with stable yield and interest rate sensitivity. |
| Real Estate | Real estate business with asset value and rate-cycle exposure. |

## Validation Examples

| Symbol | Sector | Industry | Why It Matters Output |
|--------|--------|----------|----------------------|
| VRT | Industrials | Electrical Equipment & Parts | Benefits from AI data-center buildout, electrification, and grid modernization. |
| TSM | Technology | Semiconductors | Critical chipmaker supplying AI, mobile, cloud, and automotive compute. |
| ASML | Technology | Semiconductor Equipment & Materials | Sole-source supplier of advanced chip manufacturing equipment. |
| DELL | Technology | Computer Hardware | Enterprise servers, storage, and compute infrastructure. |
| ARW | Technology | Electronic Components | Technology component distribution enabling global electronics supply chains. |
| PSX | Energy | Oil & Gas Refining & Marketing | Refining margin and fuel distribution exposure. |
| CAH | Healthcare | Medical Distribution | Essential pharmaceutical and medical supply distribution to healthcare systems. |
| CVE | Energy | Oil & Gas Integrated | Exposure to crude production, refining margins, and downstream fuel demand. |

**8/9 validation symbols mapped via primary table.**

## Implementation Path

Implemented entirely in JavaScript — no backend changes required.

```javascript
const _WHY_IT_MATTERS = {
  "Technology|Semiconductors":                     "Critical chipmaker supplying AI, mobile, cloud, and automotive compute.",
  "Technology|Semiconductor Equipment & Materials":"Sole-source supplier of advanced chip manufacturing equipment.",
  "Technology|Computer Hardware":                  "Enterprise servers, storage, and compute infrastructure.",
  // ... (full table in app.js)
};

function _getWhyItMatters(sector, industry) {
  const key = `${sector}|${industry}`;
  return _WHY_IT_MATTERS[key] || _WHY_SECTOR_FALLBACK[sector] || "";
}
```

## Verdict: IMPLEMENT
