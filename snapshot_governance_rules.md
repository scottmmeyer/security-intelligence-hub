# Snapshot Governance Rules

## Objective
Classify every PIS snapshot into PASS, WARNING, or REJECT without mutating historical records.

## Rule Set
### Account scope rules
PASS requires expected account scope pattern:
- General Brokerage
- Joint WROS - TOD
- Individual - TOD

REJECT when disallowed classes are detected:
- 401(k)
- FIS 401(K) PLAN
- BrokerageLink
- BrokerageLink Roth

Any missing expected scope pattern is treated as REJECT.

### Value sanity rules
PASS:
- portfolio_value <= 600000

WARNING:
- 600000 < portfolio_value <= 750000

REJECT:
- portfolio_value > 750000

### Source quality rules
WARNING when source_file matches known artifacts:
- test.csv
- audit_test.csv
- upload.csv
- certification_run.csv
- cert_step3.csv

## Status precedence
1. REJECT dominates WARNING and PASS
2. WARNING dominates PASS
3. PASS requires no reject and no warning conditions

## Output contract
Per snapshot output:
- status
- reasons
- scope_valid
- value_valid
- source_valid

Persisted output schema:
- snapshot_id
- snapshot_date
- governance_status
- reasons
- scope_valid
- value_valid
- source_valid

## Configurability
Rules are configurable through SnapshotGovernanceConfig in src/pis/governance.py.

Configurable fields:
- expected_account_scope_tokens
- disallowed_account_scope_tokens
- value_pass_max
- value_reject_gt
- warning_source_artifact_patterns
