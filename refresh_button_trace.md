# REFRESH-BEHAVIOR-01 Refresh Button Trace

## 1) Endpoint chain when Refresh Stale is pressed

Button -> JavaScript -> API -> backend script

1. Button handler in ui/outcome_visualization/app.js:1599
   - function triggerSignalRefresh()
2. Trigger call in ui/outcome_visualization/app.js:1607
   - fetch("/api/signal-refresh", { method: "POST" })
3. Backend route in scripts/run_outcome_ui.py:807
   - elif path == "/api/signal-refresh":
4. Process launch in scripts/run_outcome_ui.py:812-813
   - subprocess.Popen([sys.executable, scripts/refresh_signals.py, "--smart"])

Status polling chain:

1. Poll loop in ui/outcome_visualization/app.js:1631
   - function _startRefreshPoll()
2. Poll request in ui/outcome_visualization/app.js:1634
   - fetch("/api/signal-refresh/status")
3. Backend route in scripts/run_outcome_ui.py:391
   - returns {"running": true/false} from module variable _refresh_proc

## 2) Does endpoint invoke provider refresh functions?

Yes.

scripts/refresh_signals.py main entry calls ensure_signals_fresh() at scripts/refresh_signals.py:408+.

ensure_signals_fresh() calls:

- _refresh_zacks() at scripts/refresh_signals.py:185
- _refresh_yahoo() at scripts/refresh_signals.py:256
- _refresh_danelfin() at scripts/refresh_signals.py:219
- also _refresh_fmp() for FMP daily freshness

However, each provider refresh first checks _is_stale() at scripts/refresh_signals.py:76.

If _is_stale() is False (latest sourced_date is today), that provider exits immediately as up-to-date.

## 3) Sync vs async

Refresh launch is asynchronous from the UI perspective:

- UI POST returns quickly with {"started": true}
- refresh runs in a child process launched by subprocess.Popen
- UI polls /api/signal-refresh/status for completion

Job state storage:

- module-level variable _refresh_proc in scripts/run_outcome_ui.py
- running state is _refresh_proc is not None and _refresh_proc.poll() is None

Why UI shows Refresh complete:

- in _startRefreshPoll(), first false running state triggers
  - button reset
  - message set to "Refresh complete. Signal dates updated."

This message is completion of process lifecycle, not proof that provider fetches actually fetched symbols.