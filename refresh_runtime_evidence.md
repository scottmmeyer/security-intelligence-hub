# REFRESH-BEHAVIOR-01 Runtime Evidence

## Measured request timing (captured live)

Refresh trigger call:

- POST /api/signal-refresh
- HTTP 200
- response body: {"started": true}
- post latency: 0.0627 sec

End-to-end until not running:

- 0.4801 sec
- /api/signal-refresh/status returned running=false almost immediately

## Provider execution evidence for last request

Applicable holdings baseline (from /api/signal-status):

- active holdings baseline: 74
- applicable per provider: 58

| Provider | Symbols Submitted | Symbols Refreshed | Symbols Skipped | Runtime Duration |
|---|---:|---:|---:|---|
| Zacks | 0 | 0 | 58 | exited at freshness guard; part of 0.4801 sec total |
| Danelfin | 0 | 0 | 58 | exited at freshness guard; part of 0.4801 sec total |
| Yahoo | 0 | 0 | 58 | exited at freshness guard; part of 0.4801 sec total |

Interpretation of Symbols Skipped here:

- applicable holdings not submitted to provider fetch loops in this run due up-to-date short-circuit

## Live post-run status snapshot

From /api/signal-status immediately after run:

- Zacks: applicable 58, covered today 34, stale 22, missing 0, status DEGRADED
- Danelfin: applicable 58, covered today 32, stale 22, missing 0, status DEGRADED
- Yahoo: applicable 58, covered today 15, stale 22, missing 0, status DEGRADED