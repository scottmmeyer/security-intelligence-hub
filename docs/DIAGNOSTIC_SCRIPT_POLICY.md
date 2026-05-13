# Diagnostic Script Policy

## Purpose

Define governance boundaries for read-only diagnostics that support deterministic
triage without altering runtime outputs, history partitions, or platform state.

## Allowed Diagnostic Script Domain

Approved diagnostic scripts belong under scripts/diagnostics and must be:

- read-only
- deterministic in output ordering
- bounded in scope and runtime behavior
- explicitly documented with purpose and usage

## Determinism Expectations

Diagnostic scripts must:

- avoid writes, deletes, or implicit mutation of repository files
- sort discovered files/records before output when traversal order can vary
- use explicit row or sample limits when scanning large inputs
- emit stable field names and output structure

## Governance Alignment Expectations

Diagnostic scripts are support tooling only and are not execution entrypoints.
They must not bypass authoritative pipeline interfaces, validation contracts, or
run-governance controls.

## Root-Level Helper Drift Is Discouraged

Ad hoc helper files at repository root increase drift risk and bypass review
boundaries. New diagnostics are required to live in scripts/diagnostics with
clear policy documentation and deterministic behavior.

## Current Governed Diagnostic Scripts

- scripts/diagnostics/ess_payload_profile.py
