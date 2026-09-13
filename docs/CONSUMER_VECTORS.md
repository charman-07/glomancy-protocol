# Language-Neutral Consumer Conformance Vectors

The files under `vectors/v1/` provide machine-readable expected outcomes for core Glomancy Protocol consumer behavior. They are plain JSON so implementations in Rust, C++, TypeScript, Python, C#, Go, Java, or another language can consume the same cases without linking the Rust crate or the private Glomancy runtime.

## Purpose

The JSON Schemas validate message payload shape. These vectors test a different layer: the deterministic decisions a consumer makes around message-kind lookup, wire compatibility, capability negotiation, and task-time capability gating.

They are intended to reduce situations where two implementations both claim protocol support but interpret the same negotiation input differently.

## Layout

```text
vectors/v1/
  manifest.json
  message-kinds.json
  wire-compatibility.json
  capabilities.json
  task-capability-gate.json
```

`manifest.json` identifies the vector version, the wire protocol line the vectors target, and the files in the suite.

## Expected consumer pattern

An implementation should:

1. load `vectors/v1/manifest.json`;
2. verify that the declared wire protocol line is one it intends to test;
3. execute every case in each listed vector file using its own implementation;
4. compare the actual decision with the `expected` object exactly;
5. fail its conformance job if any case differs.

Do not import behavior from `scripts/validate_consumer_vectors.py` into your production implementation. That script exists as a repository consistency check. An independent implementation gets more value by implementing the public rules itself and using the JSON only as test input/expected output.

## Covered behavior

### Message-kind lookup

Known public kinds resolve to the canonical schema ID from `registry/v1/manifest.json`. Unknown kinds fail closed rather than falling back to a generic message type.

### Wire compatibility

The vectors cover:

- exact versions;
- patch compatibility within the same pre-1.0 minor line;
- pre-1.0 minor incompatibility;
- stable same-major compatibility;
- major-version incompatibility.

The normative explanation remains in `docs/COMPATIBILITY.md`.

### Capability negotiation

The vectors cover:

- exact name + exact version selection;
- required and optional capabilities;
- omission of unsupported optional capabilities;
- rejection of unsupported required capabilities;
- rejection when only a different capability version is available;
- duplicate requested-name rejection;
- invalid capability-name rejection.

The normative profile remains in `docs/CAPABILITY_NEGOTIATION.md` and `capabilities/v1/`.

### Task capability gate

The vectors verify that a task may request only valid capability names selected for the current session. An unselected or syntactically invalid name fails the gate.

Passing this gate does **not** grant authorization.

## Repository validator

The repository includes a dependency-free consistency validator:

```bash
python3 scripts/validate_consumer_vectors.py
```

It checks the vector expectations against the public registry and documented compatibility/capability rules. CI runs it on every change to catch drift between vectors and the rest of the public contract.

## Versioning

Vector versions are separate from:

- the Rust crate version;
- the wire protocol version;
- individual JSON Schema versions.

A vector change that changes an expected protocol decision must be reviewed together with the corresponding compatibility, capability, schema, documentation, and migration implications. Do not silently rewrite historical expected outcomes for a published protocol snapshot.

## What these vectors do not prove

Passing the vector suite does not prove that an implementation is secure or production-ready. It does not test authentication, authorization, sandboxing, transport security, editor permissions, provider credentials, or private Glomancy runtime behavior.

The vectors demonstrate agreement with specific public protocol decisions only.
