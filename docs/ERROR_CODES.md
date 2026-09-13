# Protocol Error Codes

Glomancy Protocol publishes a versioned, machine-readable catalog of protocol error codes under `errors/v1/catalog.json`.

The catalog exists so non-Rust consumers can depend on the same public error vocabulary without scraping Rust source code or depending on the private Glomancy runtime.

## Scope

The catalog records the `GLM-PROTO-*` codes currently defined by this public protocol package. Each entry contains:

- a stable symbolic name;
- the wire code;
- a concise public description.

The current catalog version is independent from the Rust crate version, wire protocol version, and JSON Schema versions. Its `wire_protocol_version` field identifies the public wire line the catalog accompanies.

## Current codes

| Symbolic name | Wire code | Meaning |
| --- | --- | --- |
| `invalid_envelope` | `GLM-PROTO-1001` | Malformed or invalid protocol envelope. |
| `unsupported_version` | `GLM-PROTO-1002` | Unsupported wire protocol version. |
| `unknown_schema` | `GLM-PROTO-1003` | Unknown public schema identifier. |
| `unknown_message_kind` | `GLM-PROTO-1004` | Unknown message kind; consumers must fail closed. |
| `policy_denied` | `GLM-PROTO-1005` | Local policy rejected the requested operation. |
| `message_too_large` | `GLM-PROTO-1006` | Message exceeds an enforced size limit. |
| `invalid_identifier` | `GLM-PROTO-1007` | A required protocol identifier is invalid. |
| `internal` | `GLM-PROTO-1999` | Internal protocol-processing failure without a more specific public code. |

The machine-readable catalog is authoritative for the set currently defined by this package.

## Rust API parity

The Rust crate exposes the same vocabulary through `ProtocolErrorCode::as_wire()` and fail-closed `ProtocolErrorCode::from_wire()` parsing.

Repository CI runs:

```bash
python3 scripts/validate_error_catalog.py
```

The validator rejects:

- a catalog code missing from Rust;
- an unexpected Rust code absent from the catalog;
- duplicate symbolic names or wire codes;
- mismatched `as_wire` / `from_wire` mappings;
- invalid catalog metadata;
- drift between the catalog wire version and the canonical registry.

Unknown wire values return `None` in Rust. Consumers in other languages should preserve the same fail-closed behavior rather than mapping unknown codes to a permissive default.

## Relationship to `error.code`

The common JSON Schema intentionally validates the public error-code shape (`GLM-PROTO-NNNN`) rather than enumerating only today's catalog entries. That allows future protocol releases to add new documented codes without rewriting old schema identities solely to expand an enum.

This does **not** mean an implementation should treat every syntactically valid code as known. A consumer should distinguish:

1. syntactically valid error-code shape;
2. a code currently known to the implementation/catalog;
3. local handling or recovery policy.

Unknown but well-formed codes should remain unknown to the consumer unless a newer supported catalog or protocol release defines them.

## Error codes are not authorization policy

A protocol error code describes a protocol-level failure condition. It does not authenticate a peer, grant permissions, make an editor action safe, or define whether an operation should be retried automatically.

Authentication, authorization, risk policy, approval, sandboxing, editor/tool permissions, and retry behavior remain integration responsibilities.

## Maintainer workflow

When adding or changing a public protocol error code:

1. update the Rust `ProtocolErrorCode` enum and both wire mappings;
2. update `errors/v1/catalog.json` in the same change;
3. add or update Rust round-trip tests;
4. run `python3 scripts/validate_error_catalog.py`;
5. review compatibility and migration impact;
6. update release notes / CHANGELOG;
7. require the full CI suite to pass before merge.

Existing published meanings must not be silently reassigned to different conditions. If semantics need to change materially, introduce a new documented code or versioned contract rather than mutating history.
