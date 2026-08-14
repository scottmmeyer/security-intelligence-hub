# Contributing

## Source Control and Runtime Data
See [docs/source_control_and_durability.md](docs/source_control_and_durability.md) for the canonical policy.

Summary:
- Source, non-secret configuration, and documentation belong in Git.
- Secrets and private runtime state do not belong in Git.
- Ignored does not mean disposable.
- Agent-assisted source changes require explicit commit approval; leave changes unstaged for review unless user authorizes staging/commit.
