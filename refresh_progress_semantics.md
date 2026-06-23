# Refresh Progress Semantics

## Observed Progress Pattern

Example live line:

[447/2518] Fetching Zacks data for MTN

## Exact Semantics

1. Numerator

- Current loop index i in the provider fetch loop.
- It means the current symbol being attempted within that provider batch.

2. Denominator

- Length of pending_symbols after checkpoint and retry filtering for that provider call.
- It is not the total analytical universe size in all contexts.
- For rebuild mode, it is usually close to the full base universe symbol list.

3. Count type

- Attempted symbol count in the current provider stage.
- Not completed end-to-end refresh count across all providers.
- Not a combined multi-provider progress denominator.

4. Scope

- Provider-specific stage progress.
- For the example, this is Zacks-stage progress only.

## Is It Technically Correct?

Yes, for provider-stage progress. No, as an overall refresh progress indicator.

The line is technically accurate but semantically incomplete because it does not state that it is provider-stage specific and it is displayed next to metrics from other universes.

## Recommended Labeling (Display Only)

- Prefix line with stage context, such as Stage Zacks (provider batch).
- Show denominator label explicitly, such as pending symbols this stage.
- Add separate overall refresh progress indicator based on completed provider stages, not per-symbol loop index alone.
