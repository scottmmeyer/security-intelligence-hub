# Progressive Rendering Strategy

## Startup Model
`ui/pis_dashboard/app.js` now initializes the dashboard shell first, then launches independent section tasks concurrently.

## Mechanics
- Each section enters `LOADING` immediately.
- Each section starts its own async request path through `runSectionTask(...)`.
- Shared endpoints use a request cache so repeated section tasks do not duplicate backend work unnecessarily.
- Sections render as soon as their payload arrives.
- Slow sections are marked `SLOW` after 5 seconds.
- Timed-out or failed sections become `FAILED` and render `Data unavailable` with a reason.

## Result
- Snapshot inventory can render before lineage.
- Governance can render before canonical, or vice versa.
- Change-detection sections can render independently of lineage.
- Lineage failure no longer blocks the rest of the dashboard.

## Preserved Boundaries
- No backend route behavior was changed.
- No read-model calculation logic was changed.
- No governance/canonical/change-detection/lineage business rules were changed.