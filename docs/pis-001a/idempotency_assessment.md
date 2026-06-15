# Idempotency Assessment

## Recommendation
Do not create a second PIS snapshot for the exact same portfolio upload.

## Current Uniqueness Rule
PIS snapshot registration is keyed off the canonical SIH snapshot identity. If the same upload is processed again and produces the same SIH snapshot identity, registration is treated as a duplicate and suppressed.

## Why This Works
- It keeps the upload workflow single-pass.
- It avoids duplicate history rows for accidental re-uploads.
- It keeps the deduplication rule at the canonical portfolio object boundary, not at the file boundary.

## Future Hardening Option
If the platform later needs duplicate detection across renamed files, add a content fingerprint derived from the canonical snapshot and holdings without changing the SIH/PIS contract.
