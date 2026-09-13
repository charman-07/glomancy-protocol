# Compatibility

Glomancy Protocol separates three version concepts:

1. the **Rust crate version** (for example `0.1.0`);
2. the **wire protocol version** (currently `0.4.0`);
3. individual **schema versions** (currently `1.0.0` for the v1 public schema set).

They are related but not interchangeable.

## Wire negotiation rules

The canonical machine-readable rules live in `compatibility/v1/compatibility-matrix.json`.

| Local / remote relationship | Result |
| --- | --- |
| Versions exactly equal | `exact` |
| Major is `0`, minor equal, patch differs | `patch-compatible` |
| Major is `0`, minor differs | `incompatible` |
| Major is `1+` and major equal | `major-compatible` |
| Major differs | `incompatible` |

The current negotiation policy also requires:

- highest common supported version selection when more than one version is shared;
- handshake rejection when there is no compatible intersection;
- fail-closed behavior for unknown schema IDs;
- fail-closed behavior for unknown message kinds.

## Why pre-1.0 minor versions are incompatible

Before 1.0, a minor version can represent a meaningful contract change. Treating a new minor as automatically compatible would allow an implementation to accept semantics it does not understand. The project therefore uses a conservative same-minor rule before 1.0.

The detailed lifecycle for announcing, migrating, and removing pre-1.0 public behavior is documented in [Pre-1.0 Deprecation and Schema Evolution Policy](DEPRECATION_POLICY.md).

## Schema evolution

A schema's URN includes its schema version. A change that alters the accepted wire contract should not silently reuse a schema identifier whose published hash has changed.

The schema registry records SHA-256 digests so CI can detect accidental mutation of the registered source files.

For material contract changes, prefer a new schema version/ID, updated registry metadata, explicit fixtures/tests, and migration notes rather than silent mutation. The full process is defined in [DEPRECATION_POLICY.md](DEPRECATION_POLICY.md).

## Compatibility tests

Compatibility behavior should be represented in all applicable places:

- `compatibility/v1/compatibility-matrix.json` for the rule;
- `compatibility/v1/cases.json` for concrete cases;
- Rust tests for the public helper behavior;
- migration notes in `CHANGELOG.md` when users need to act.

A change is incomplete if code, matrix, fixtures, and documentation disagree.

## Breaking changes

The protocol is pre-1.0, so breaking changes can occur before 1.0. They must be explicit. A breaking proposal should describe:

- what stops being accepted or changes meaning;
- why an additive change is insufficient;
- migration options;
- security consequences;
- the intended wire/schema version transition.

Where practical, a public contract should be deprecated and accompanied by a replacement/migration path before removal. Immediate removal is reserved for cases where retaining the old behavior would create unreasonable security or correctness risk. See [DEPRECATION_POLICY.md](DEPRECATION_POLICY.md) for the complete lifecycle and non-guarantees.
