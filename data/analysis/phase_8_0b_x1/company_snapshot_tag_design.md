# Company Snapshot Business Model Tags Design — Phase 8.0B.X.2

## Objective
Evaluate adding 1–3 visual business model tags per company for rapid operator orientation.

## Purpose
Tags answer: "What market is this company in?"  
In less than 1 second, with no reading required.

## Tag Vocabulary (Controlled)

Tags are drawn from a fixed set to ensure consistency and prevent tag sprawl:

```
AI INFRASTRUCTURE    DATA CENTER       SEMICONDUCTOR     ENTERPRISE IT
TECH DISTRIBUTION   NETWORKING        SOFTWARE          DEFENSE / INTEL
ENERGY              CLEAN ENERGY      NUCLEAR           HEALTHCARE
PHARMA              BIOTECH           FINANCIALS        BANKING
INSURANCE           MATERIALS         STEEL             GOLD / MINING
INDUSTRIALS         AEROSPACE         EV                CONSUMER
REAL ESTATE         UTILITIES         FOOD & BEVERAGE
```

## Derivation Strategy

Tags are derived from two sources (applied in order):

1. **Primary: `(sector, industry)` → base tags** — deterministic, always applied
2. **Secondary: keyword scan of `business_summary`** — adds context tags if keywords detected

### Keyword Boosts

| Keyword in business_summary | Tag Added |
|-----------------------------|-----------|
| "AI" or "artificial intelligence" | AI INFRASTRUCTURE |
| "data center" | DATA CENTER |
| "nuclear" or "SMR" | NUCLEAR |
| "defense" or "intelligence community" or "counterterrorism" | DEFENSE / INTEL |
| "EV" or "electric vehicle" | EV |
| "solar" | CLEAN ENERGY |
| "lithography" or "chip manufacturing" | SEMICONDUCTOR |
| "semiconductor" | SEMICONDUCTOR |

## Primary Tag Mapping

| Sector | Industry | Base Tags |
|--------|----------|-----------|
| Technology | Semiconductors | SEMICONDUCTOR |
| Technology | Semiconductor Equipment & Materials | SEMICONDUCTOR |
| Technology | Computer Hardware | ENTERPRISE IT |
| Technology | Electronic Components | TECH DISTRIBUTION |
| Technology | Information Technology Services | ENTERPRISE IT, SOFTWARE |
| Technology | Software—Application | SOFTWARE, ENTERPRISE IT |
| Technology | Software—Infrastructure | SOFTWARE |
| Technology | Communication Equipment | NETWORKING |
| Industrials | Electrical Equipment & Parts | INDUSTRIALS |
| Industrials | Engineering & Construction | INDUSTRIALS |
| Industrials | Aerospace & Defense | AEROSPACE, DEFENSE / INTEL |
| Healthcare | Medical Distribution | HEALTHCARE |
| Healthcare | Biotechnology | BIOTECH, HEALTHCARE |
| Healthcare | Drug Manufacturers—General | PHARMA, HEALTHCARE |
| Healthcare | Medical Devices | HEALTHCARE |
| Energy | Oil & Gas Integrated | ENERGY |
| Energy | Oil & Gas E&P | ENERGY |
| Energy | Oil & Gas Refining & Marketing | ENERGY |
| Energy | Solar | CLEAN ENERGY |
| Financial Services | Asset Management | FINANCIALS |
| Financial Services | Banks—Regional | BANKING |
| Financial Services | Insurance—Property & Casualty | INSURANCE |
| Consumer Cyclical | Auto Manufacturers | EV, CONSUMER |
| Basic Materials | Steel | STEEL, MATERIALS |
| Basic Materials | Gold | GOLD / MINING, MATERIALS |

## Validation Examples

| Symbol | Primary Tags | Keyword Boosts | Final Tags |
|--------|-------------|----------------|-----------|
| VRT | INDUSTRIALS | "data center", "AI" | INDUSTRIALS, DATA CENTER, AI INFRASTRUCTURE |
| TSM | SEMICONDUCTOR | "AI", "chip" | SEMICONDUCTOR, AI INFRASTRUCTURE |
| ASML | SEMICONDUCTOR | "lithography" | SEMICONDUCTOR |
| DELL | ENTERPRISE IT | "AI infrastructure" | ENTERPRISE IT, AI INFRASTRUCTURE |
| ARW | TECH DISTRIBUTION | — | TECH DISTRIBUTION |
| PSX | ENERGY | — | ENERGY |
| CAH | HEALTHCARE | — | HEALTHCARE |
| CVE | ENERGY | — | ENERGY |
| PLTR | SOFTWARE | "intelligence community", "defense" | SOFTWARE, DEFENSE / INTEL |
| SMR | INDUSTRIALS | "nuclear" | INDUSTRIALS, NUCLEAR |

## Tag Limit: 3 maximum per symbol

If more than 3 tags qualify, priority order: keyword boosts first, then base tags.

## CSS Design

```css
.dq-cs-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.dq-cs-tag {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.67rem; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase;
  background: #e8f0fe; color: #1a56db;
  border: 1px solid #c3d7fb;
}
```

## Tag Placement

Tags appear on the same row as the "What They Do" label, or as a separate row between "What They Do" and "Why It Matters".

Recommended placement: immediately below the Company Snapshot header, before the grid rows.
This makes them the first visual element after the section title — fast scan path.

## Verdict: IMPLEMENT
Tags are a meaningful quick-scan element that add zero backend cost (pure JS derivation).
Limit to 3 max to avoid visual clutter.
