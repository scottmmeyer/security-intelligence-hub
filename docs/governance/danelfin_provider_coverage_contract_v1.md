# Danelfin Provider Coverage Contract V1

Status: Accepted
Scope model: DISCOVERY_PLUS_CACHED_COVERAGE

## 1) Applicability
Applicability and provider coverage are separate.

- Security applicability answers whether a security is theoretically eligible to use Danelfin evidence under broad equity governance rules.
- Applicability does not prove Danelfin coverage.
- Applicability does not imply the security should be browser-requested in every rebuild.

## 2) Known Coverage
Known-covered symbols are symbols with durable Danelfin evidence (valid normalized Danelfin rows).

- Known-covered symbols are refreshed routinely.
- Successful discovery outcomes are promoted into known-covered and remain refreshable in future runs.

## 3) Discovery
Unknown symbols require bounded discovery rather than full-universe browser sweeps.

- Rebuild mode uses known-covered refresh plus bounded discovery.
- Discovery must be finite per run, deterministic, and resumable where practical.
- Discovery must allow new symbols to enter known coverage over time.

## 4) Known No-Coverage
Known no-coverage is distinct from execution failure.

- Only explicit no-coverage evidence may classify a symbol as known no-coverage.
- Browser challenge, queue interruption, timeout, or temporary network failure must not be interpreted as provider no-coverage.

## 5) Operational Failure
Operational failures are execution outcomes for attempted symbols.

- Operational failure means an attempted acquisition did not complete successfully.
- Operational failure is not a provider coverage verdict.

## 6) Rebuild Semantics
rebuild_research_universe rebuilds the global research foundation.

- It does not require Danelfin to attempt all research-universe symbols in one run.
- Danelfin rebuild denominator is bounded attempted symbols only.

## 7) Readiness Contract
Danelfin is a conditional provider requirement.

- KNOWN_COVERED: Danelfin freshness is required.
- KNOWN_NO_COVERAGE: Danelfin does not block core readiness.
- UNKNOWN or DISCOVERY_PENDING: Danelfin does not auto-classify stale, and coverage completeness remains visible separately.

Danelfin is not removed from readiness globally.

## 8) Coverage Transparency
Coverage and execution transparency are reported separately.

Required coverage dimensions:

- Research universe size
- Known-covered count
- Known no-coverage count
- Unknown/discovery count
- Fresh known-covered count
- Stale known-covered count
- Attempted count
- Succeeded count
- Operational failure count

This preserves visibility into partial provider breadth without conflating unattempted unknown symbols with provider failures.
