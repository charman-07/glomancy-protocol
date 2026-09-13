# Rust / JSON Wire Enum Parity

Glomancy Protocol exposes several public wire enums in two places:

- Rust enums used by the public crate;
- enum values in `schemas/v1/common.schema.json`.

Those surfaces must stay identical.

## Covered enums

CI currently checks:

- `Component` ↔ `$defs.component`;
- `RiskLevel` ↔ `$defs.risk_level`;
- `ExecutionMode` ↔ `$defs.execution_mode`;
- `TaskStatus` ↔ `$defs.task_status`;
- `ErrorCategory` ↔ `$defs.error_category`.

Each Rust type exposes `as_wire` and fail-closed `from_wire` mappings. Unknown wire values return `None` rather than being guessed, normalized, or silently downgraded.

## CI invariant

Repository CI runs:

```bash
python3 scripts/validate_wire_enums.py
```

The validator uses only the Python standard library. It parses the Rust mappings and compares them to the canonical enum arrays in `common.schema.json`.

CI rejects:

- a schema enum value missing from Rust;
- an extra Rust wire value absent from the schema;
- duplicate schema or Rust wire values;
- mismatched `as_wire` / `from_wire` mappings;
- a missing public mapping method.

Rust unit tests additionally round-trip every current variant through `as_wire` and `from_wire` and verify representative unknown values fail closed.

## Why this matters

A payload can be structurally valid JSON while still carrying an enum value a Rust consumer cannot interpret. The schema and crate should therefore agree on the complete public vocabulary.

This parity check turns that agreement into an executable contract instead of relying on maintainers to update both files manually and notice drift during review.

## Maintainer workflow

When intentionally adding or removing a public enum value:

1. follow the pre-1.0 schema-evolution policy;
2. update the JSON Schema enum and the Rust enum in the same change;
3. update both `as_wire` and `from_wire` mappings;
4. add or update Rust tests;
5. run `python3 scripts/validate_wire_enums.py`;
6. run the full CI suite before merge.

Do not weaken the parity validator to accommodate an accidental mismatch. Resolve the public-contract drift instead.
