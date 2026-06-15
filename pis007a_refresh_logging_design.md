# PIS-007A Refresh Logging Design

**Date:** 2026-06-15  
**Remediation:** R2 — Post-ingestion refresh operator visibility

---

## Problem

`_trigger_pis_refresh_background()` in `src/portfolio/runner.py` swallowed all exceptions with `pass`, producing no log output on start, success, or failure. Operators had no way to determine whether a post-ingestion refresh ran or succeeded.

## Implementation

**File:** `src/portfolio/runner.py`  
**Function:** `_trigger_pis_refresh_background()._run()`

Before (no logs):
```python
def _run() -> None:
    try:
        from src.pis.refresh_orchestrator import trigger_startup_refresh
        trigger_startup_refresh(repo_root=repo_root)
    except Exception:
        pass  # silent
```

After (three log messages):
```python
def _run() -> None:
    print("[PIS] Post-ingestion refresh started.", file=sys.stderr)
    try:
        from src.pis.refresh_orchestrator import trigger_startup_refresh
        trigger_startup_refresh(repo_root=repo_root)
        print("[PIS] Post-ingestion refresh completed.", file=sys.stderr)
    except Exception as exc:
        print(f"[PIS] Post-ingestion refresh failed: {exc}", file=sys.stderr)
```

## Log Messages

| Event | Message | Stream |
|-------|---------|--------|
| Thread starts | `[PIS] Post-ingestion refresh started.` | stderr |
| Refresh completes | `[PIS] Post-ingestion refresh completed.` | stderr |
| Refresh fails | `[PIS] Post-ingestion refresh failed: {exc}` | stderr |

## Preserved Behavior

- Fire-and-forget semantics: thread starts and returns immediately
- Exception isolation: exceptions are caught inside `_run()`, never propagate to SIH
- Daemon thread model: thread terminates with server process
- Non-blocking: analysis response path unaffected
- `trigger_startup_refresh` continues to print its own success/failure messages to stderr (these appear after the "started" line and before "completed")
