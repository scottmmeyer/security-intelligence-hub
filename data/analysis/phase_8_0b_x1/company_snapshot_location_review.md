# Company Snapshot Location Format Review — Phase 8.0B.X.2

## Current Format

`city, state_abbrev, country`

Examples:
- Westerville, OH, United States
- Round Rock, TX, United States
- Hsinchu City, Taiwan
- Veldhoven, Netherlands
- Calgary, AB, Canada

## Options Evaluated

### Option A: `City, State Abbrev, Country` (current)
- Westerville, OH, United States
- Calgary, AB, Canada
- Veldhoven, Netherlands
- **Pros:** Compact, professional shorthand
- **Cons:** OH/TX/AB are US/Canada-centric abbreviations; "United States" is long

### Option B: `City, State Full, Country`
- Westerville, Ohio, United States
- Calgary, Alberta, Canada
- Veldhoven, Netherlands
- **Pros:** Unambiguous; readable for all audiences
- **Cons:** Longer; "United States" still long

### Option C: `City, State Abbrev, Country Abbrev`
- Westerville, OH, USA
- Calgary, AB, Canada
- Veldhoven, Netherlands
- **Pros:** Concise; USA is universally recognized; consistent length
- **Cons:** Requires country abbreviation lookup for common countries

### Option D: `City, State Full` (drop country for US)
- Westerville, Ohio
- (International retains country)
- **Pros:** Clean for US holdings
- **Cons:** Inconsistent format between US and international

## Recommendation

**Option C: `City, State Abbrev, Country Abbrev`**

Rationale:
- "USA" is as readable as "United States" and more compact
- State abbreviations (OH, TX, CA) are professional business standard in the US
- Keeps international format consistent (`Veldhoven, Netherlands`, `Hsinchu City, Taiwan`)
- Canada uses province abbreviations professionally (AB, ON, BC)

### Country Abbreviation Table

| Full Name | Display |
|-----------|---------|
| United States | USA |
| All others | Full name as-is |

> Only "United States" is abbreviated. All other countries display their full name, since they are already reasonably concise (Taiwan, Netherlands, Switzerland, Brazil, etc.).

## Implementation

Update `_compose_hq()` in `fetch_company_profile.py`:

```python
_COUNTRY_ABBREV = {"United States": "USA"}

def _compose_hq(city: str, state: str, country: str) -> str:
    country_display = _COUNTRY_ABBREV.get(country, country)
    parts = [p.strip() for p in [city, state, country_display] if p.strip()]
    return ", ".join(parts) if parts else ""
```

This requires a one-time re-fetch or a one-time transformation of existing cached data.
Since country is stored raw in `latest_company_profile.csv`, the simplest path is to apply the abbreviation at the API endpoint level (in `run_outcome_ui.py` when composing the `hq` field).

## Before/After

| Symbol | Before | After |
|--------|--------|-------|
| VRT | Westerville, OH, United States | Westerville, OH, USA |
| DELL | Round Rock, TX, United States | Round Rock, TX, USA |
| TSM | Hsinchu City, Taiwan | Hsinchu City, Taiwan (unchanged) |
| ASML | Veldhoven, Netherlands | Veldhoven, Netherlands (unchanged) |
| CVE | Calgary, AB, Canada | Calgary, AB, Canada (unchanged) |

## Verdict: IMPLEMENT Option C
Minimal change: only "United States" → "USA" in the `_compose_hq()` function.
