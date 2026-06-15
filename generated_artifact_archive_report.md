# Generated Artifact Archive Report

## Objective

Handle generated screenshot artifacts so they are preserved without polluting the active Benchmark Attribution dirty tree.

## Artifacts

- docs/pis-001/screenshots/pis_dashboard_phase1.png
- docs/pis-001/screenshots/sih_to_pis_navigation.png

## Decision

Selected option: C (Leave untracked but excluded)

Rationale:
- Safest preservation choice: no data loss and no content mutation.
- Avoids creating additional documentation-stream file moves before benchmark implementation starts.
- Keeps these binary artifacts out of active git status via local exclude rules.

## Action Taken

- Added exact paths to local exclusion file: .git/info/exclude
- Verified both artifacts no longer appear in `git status --porcelain -uall`.

## Impact

- Dirty-path count reduced by 2.
- Benchmark stream setup is cleaner without deleting potentially useful evidence screenshots.

## Notes

- This exclusion is local to the repository clone and does not affect tracked project configuration.
