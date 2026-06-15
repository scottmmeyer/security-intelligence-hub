# Workstream Isolation Plan

## Baseline

- Isolation baseline commit: 18fbbd8 (AI-003)
- Dirty-file snapshot analyzed: 113 paths
- Source of truth for file-level mapping: `repository_stabilization_actions.md`

## Stream Grouping

### Signal Coverage / Refresh

- File count: 31
- Included from classification: all files tagged `Signal Coverage / Refresh`
- Branch: `stream/signal-coverage-refresh`
- Staging rule: only stage files tagged `Signal Coverage / Refresh`

### PRA-IMPL-02

- File count: 2
- Included from classification: all files tagged `PRA-IMPL-02`
- Branch: `stream/pra-impl-02`
- Staging rule: only stage files tagged `PRA-IMPL-02`

### Benchmark Attribution

- File count: 25
- Included from classification: all files tagged `Benchmark Attribution`
- Branch: `stream/benchmark-attribution-01b`
- Staging rule: only stage files tagged `Benchmark Attribution`

### Documentation Consolidation

- File count: 55
- Included from classification: files tagged `Documentation Draft`, `PIS Foundation`, `Temporary`, `Generated Artifact`, `Future Work`
- Branch: `stream/docs-consolidation`
- Staging rule: stage docs in logical batches; keep code-bearing files out of this stream

## Recommended Execution Order

1. Documentation Consolidation
2. Benchmark Attribution
3. Signal Coverage / Refresh
4. PRA-IMPL-02

## Guardrails

- Do not mix files across streams in the same commit.
- Use explicit allowlist staging via `git add <path...>`.
- Re-run stream-specific regression gates before each stream commit.
