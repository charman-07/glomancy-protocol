# Rust / JSON Registry Parity

`registry/v1/manifest.json` is the canonical machine-readable registry for public protocol schemas. The Rust crate also exposes a generated message-schema snapshot through `GENERATED_SCHEMA_REGISTRY`.

Those two surfaces must not drift.

## CI invariant

Repository CI runs:

```bash
python3 scripts/validate_rust_registry.py
```

The validator uses only the Python standard library and compares three public sources:

- `registry/v1/manifest.json` — canonical message kinds, schema IDs, versions, hashes, and schema paths;
- `src/message.rs` — the public `MessageKind` enum and its wire names;
- `src/generated_schema_registry.rs` — the registry snapshot compiled into the Rust crate.

For every public message kind, CI requires an exact match for:

- Rust `MessageKind` variant ↔ wire message kind;
- schema ID;
- schema version;
- SHA-256 digest;
- normalized repository-relative schema path.

The check also rejects missing, duplicate, stale, unexpected, or unparseable Rust registry descriptors.

## Support schemas

`common.schema.json` and `envelope.schema.json` are support schemas in the canonical JSON registry. They do not correspond to standalone `MessageKind` values and therefore are intentionally not entries in the message-kind Rust registry.

If the public Rust API later exposes support schemas directly, that should be an explicit reviewed contract change rather than an accidental side effect of regeneration.

## Why this matters

A consumer should not receive one schema identity through the JSON registry and a different schema identity through the Rust crate. Hash validation protects schema bytes, while the parity check additionally protects the mapping between public wire names and Rust descriptors.

Together these checks make silent registry drift fail CI before it reaches a release.

## Maintainer workflow

When a public message schema changes legitimately:

1. follow the schema-evolution and compatibility policy;
2. update the canonical JSON registry and schema hash;
3. update the Rust generated registry snapshot in the same change;
4. run `python3 scripts/validate_repository.py`;
5. run `python3 scripts/validate_rust_registry.py`;
6. run the full CI suite before merge.

Do not work around a parity failure by weakening the validator. Resolve the underlying public-contract mismatch.
