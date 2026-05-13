# Canonical Terminology

## Snapshot
An immutable, append-only point-in-time record of normalized intelligence values and lineage metadata.

## Run
A deterministic execution instance identified by run_id that processes inputs for a specific snapshot_date.

## Manifest
A deterministic record describing run or stage status, validation outcomes, and lineage-relevant metadata.

## Artifact
A persisted output produced by a stage and tracked with artifact name, path, type, timestamp, and lineage notes.

## Canonical
A normalized internal representation with explicit contracts that is independent of provider-native field naming.

## Provider
An external data source whose native semantics are preserved and traceable through lineage fields.

## Coverage Domain
A first-class classification that states signal coverage intent for a security in a specific intake universe.

## Benchmark
An authoritative reference instrument used for comparability and contextual interpretation.

## Benchmark Relative
A comparison frame in which signal interpretation or outcomes are evaluated against benchmark context.

## Historical Truth
The exact state of known data at publication time, preserved without retroactive mutation.

## Point-in-Time Intelligence
Intelligence that is valid only for the recorded snapshot_date and must not include future information.

## Lineage
Provenance metadata that connects a published record to run_id, provider, source_file, and transformation context.

## Normalization
Deterministic transformation from provider-native payloads into canonical contracts.

## Validation
Fail-closed contract enforcement that rejects malformed, incomplete, or inconsistent records.

## Outcome Window
A future evaluation horizon used for benchmark-relative effectiveness measurement.

## Derived Value
A value computed from authoritative inputs under deterministic rules and explicit provenance.

## Authoritative Value
A value directly supplied by a trusted source record without inferential transformation.

## Estimated Value
A non-authoritative value inferred from deterministic mapping rules and explicitly flagged as estimated.

## Immutable
Not editable in place after publication; corrections are represented as new appended records.

## Security Master
The canonical identity and classification layer for securities across provider inputs and time.

## Signal Snapshot
An immutable appended record of normalized security signals at a specific snapshot_date.

## Coverage Universe
A defined intake population and provider context that determines applicable schemas and coverage rules.
