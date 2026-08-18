# SIH Danelfin Background Capture (MV3)

This extension captures Danelfin AI scores through ordinary Google Chrome background tabs and posts them to local SIH for ingestion.

## Installation

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Click Load unpacked.
4. Select this `chrome_danelfin_capture_extension` directory.
5. Load unpacked is normally required only once.

## Reload after code changes

After editing extension files, use the circular extension reload button in `chrome://extensions`.
Do not remove and re-add the extension unless that is specifically required.

## Prerequisites

- SIH local server must be running on `127.0.0.1:8765`.
- If Chrome prompts for localhost or local network access, allow the explicit permission.
- The one-time permission bootstrap probe is provided by `lna_probe.html` and `lna_probe.js`.

## Runtime behavior

Clicking the extension action starts the configured queue.

For each pair, the extension:

1. creates an inactive Danelfin tab,
2. loads the comparison page,
3. captures the rendered AI scores and source date from the DOM and aria labels,
4. posts the observation payload to local SIH,
5. closes the temporary tab,
6. proceeds to the next pair.

The validated queue currently processes the first production batch sequentially. It should not be treated as a permanent ordering contract unless the source queue is intentionally updated.

## Safety behavior

The capture run stops on:

- provider challenge,
- parse failure,
- ingest failure,
- same-day conflicting valid score.

This workflow does not use Playwright, challenge solving, cookie export, stealth logic, or manual score transcription.

## Provenance

Captured observations are stamped with:

- `acquisition_method=BROWSER_CAPTURE_DANELFIN_UI`
- `operator_source=PAIR_PAGE`

## Validation

Relevant deterministic tests:

- `tests/test_danelfin_browser_capture_api.py`
- `tests/test_danelfin_browser_capture_parser.py`
- `tests/test_danelfin_background_queue_contract.py`
- `tests/test_danelfin_manual_import.py`

Related broader checks that were also run in validation:

- `tests/test_7_5e_signal_transparency.py`
- `tests/test_7_5b_deployment_queue.py`

## Troubleshooting

If localhost posting fails, verify the SIH server is running and complete the localhost/local network permission prompt when Chrome shows it.
