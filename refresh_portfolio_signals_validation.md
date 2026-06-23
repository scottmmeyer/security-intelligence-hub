# REFRESH-UX-01A Portfolio Signals Refresh Verification Audit

Date of audit: 2026-06-18

## Executive Finding

The completed `Refresh Portfolio Signals` run did refresh the full applicable portfolio universe.

Final refresh report shows:

- Zacks: submitted 56, refreshed 56, failed 0
- Danelfin: submitted 56, refreshed 56, failed 0
- Yahoo: submitted 56, refreshed 56, failed 0
- FMP daily: triggered as part of the same orchestration, but not part of the portfolio-signal universe

This confirms that Portfolio Signals mode refreshed all 56 applicable securities for each provider.

## Q1-Q5: Refresh Execution Trace

Q1. What refresh mode was selected?

- UI selection: `Refresh Portfolio Signals`
- Backend execution mode: `portfolio_signals`

Q2. What endpoint was invoked?

- `POST /api/signal-refresh`

Q3. What parameters were passed?

- Request payload: `{"mode":"portfolio_signals"}`
- Server-side status confirms `mode: portfolio_signals`

Q4. What symbol universe was constructed?

- Portfolio Signals applicable universe: 56 symbols
- FMP daily remained a separate refresh branch with 2574 symbols

Q5. Produce the full symbol list.

- Intended 56-symbol Portfolio Signals universe:

`AEIS, AGEN, ALNT, AMG, AMZN, ANGO, ANIP, ARW, ASML, ATLC, AVGO, AVT, AZZ, CAH, CBOE, CIEN, CMCO, CRS, CVE, DELL, DVN, FHI, FIS, FSLR, GFF, GTX, HALO, HCI, IVZ, JBL, KGC, LMAT, LRCX, MKSI, MSFT, MTZ, MU, NUE, NVDA, NVS, PCB, PLTR, PRG, PRIM, PSX, SANM, SIMO, SNX, STLD, TSLA, TSM, UHS, UTHR, VRT, XYZ, YELP`

## Q10-Q12: Portfolio Signals Validation

Q10. When Portfolio Signals is selected, should the engine submit 56 securities or only stale securities?

- It should submit 56 applicable securities.

Q11. What actually happened during the completed run?

- Zacks: 56 submitted, 56 refreshed
- Danelfin: 56 submitted, 56 refreshed
- Yahoo: 56 submitted, 56 refreshed

Q12. Is the current behavior aligned with the intended design?

- Yes. The completed run matches the Portfolio Signals contract.

## Q13-Q17: Decision Readiness

Q13. Why is readiness not rendering?

- It is rendering.
- The panel shows `Readiness: MEDIUM`.

Q14. Is the calculation failing?

- No. The readiness calculation is producing a value.

Q15. Is the API endpoint returning data?

- Yes. `/api/signal-status` returns readiness-relevant provider and coverage data.

Q16. Is the UI binding functioning?

- Yes. The current page renders a populated readiness block.

Q17. What readiness value should currently be displayed?

- `MEDIUM`
- Reason: ESS is `Warning` because SIMO is stale; Zacks, Danelfin, and Yahoo are `Current`

## Q18-Q21: SIMO Investigation

Q18. Why is SIMO still the only warning symbol?

- The ESS warning artifact reports exactly one stale ESS gap, and that gap is SIMO.

Q19. What exact ESS condition is stale?

- `SIMO`
- `last_ess_date = 2026-05-20`
- `days_stale = 29`
- `gap_type = STALE_ESS`
- `current_ess_posture = BULLISH`

Q20. Is SIMO refreshable through the current ESS process?

- Yes, but only by providing a new StarMine ESS intake file in `incoming/ess/starmine/` and rerunning ESS intake.
- The current signal refresh button does not repair this condition.

Q21. Is operator action required?

- Yes.
- The operator needs a new StarMine export for SIMO to clear the stale ESS gap.

## Bottom Line

1. Did Portfolio Signals refresh all 56 applicable securities?

- Yes.

2. What does 1/1 actually mean?

- It is a provider cache row metric, not a 56-symbol coverage metric.

3. Why does coverage show 56 while refresh shows 1?

- Coverage measures applicable holdings in the portfolio universe.
- The top cards originally showed `1/1` because each provider cache file contained one row. After the completed refresh, the top cards now show `56/56` rows.

4. Why is Decision Readiness still loading?

- It is not loading.
- It now renders `MEDIUM`.

5. Is REFRESH-UX-01 operating as designed or partially implemented?

- It is now operating as designed for the Portfolio Signals path.