# Loading State Validation

## Automated Coverage
Updated `tests/test_pis_ui_phase1_dashboard.py` validates:
- loading banner/status panel hooks are present
- section metadata hooks are present
- loading/success/slow/failure status model constants exist
- progressive task orchestration exists in `app.js`
- lineage slow/failure messaging exists

## Runtime Validation
Observed on live dashboard at `http://127.0.0.1:8765/ui/pis_dashboard/`:

### Startup
- Global banner visible with `Portfolio Intelligence Dashboard` and `Loading data...`
- Section placeholders visible immediately
- Status panel begins in `LOADING`

### Mid-load (~6s)
- Healthy sections already render
- Detailed lineage sections show `SLOW`
- Message shown: `Lineage data is taking longer than expected...`
- Status panel shows lineage subsystem as `SLOW`

### Timeout (~13s)
- Healthy sections remain rendered and usable
- Detailed lineage sections show `FAILED`
- Message shown: `Data unavailable`
- Reason shown: `Request timed out while waiting for the server.`
- Status panel shows lineage subsystem as `FAILED`
- Global loading banner hides because all sections reached terminal states (`LOADED` or `FAILED`)

## Validation Conclusion
The dashboard now communicates startup progress, slow dependencies, and partial failures clearly enough for operator use.