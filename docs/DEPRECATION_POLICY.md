# Pre-1.0 Deprecation and Schema Evolution Policy

Glomancy Protocol is currently pre-1.0. That means meaningful contract changes are still possible, but they should never arrive as silent surprises.

This policy defines how the public project intends to announce, version, test, document, and eventually remove deprecated protocol behavior before 1.0.

The goal is not to promise indefinite backwards compatibility. The goal is to make change **deliberate, reviewable, machine-visible where practical, and accompanied by a migration path**.

## The three version layers

Glomancy Protocol has three separate version concepts:

1. **Rust crate version** — the package version in `Cargo.toml`.
2. **Wire protocol version** — the negotiated protocol version exchanged by peers.
3. **Schema version** — the version embedded in each public schema URN.

They may move independently.

A crate release can contain documentation/tests/tooling changes without changing the wire version. A schema can gain a new version while the crate version changes separately. A wire-version change is reserved for negotiation-level or cross-message contract changes.

Consumers should not assume that these three numbers always move together.

## Pre-1.0 compatibility stance

Before wire protocol 1.0, Glomancy Protocol intentionally uses a conservative compatibility rule:

- same `0.x` minor line with patch differences can be compatible;
- different `0.x` minor lines are treated as incompatible unless an explicit future profile says otherwise.

This allows a new pre-1.0 minor line to carry meaningful semantic changes without older peers accidentally accepting behavior they do not understand.

The Rust crate also follows normal pre-1.0 semantic-version expectations: breaking public API changes may require a crate minor-version bump rather than waiting for 1.0.

## What counts as a deprecation?

A public contract element is deprecated when maintainers still support or recognize it for a transition period but recommend that new implementations stop depending on it.

Examples include:

- a message field planned for removal or replacement;
- a schema version superseded by a newer schema version;
- a capability identifier/profile rule being replaced;
- a public helper API planned for removal;
- an error code/category whose semantics are being superseded;
- a compatibility behavior that will change in a future wire line.

Documentation-only wording changes and internal refactors that do not affect the public contract are not deprecations.

## No silent mutation of published schemas

A published schema ID is treated as immutable contract identity.

If a change alters what a schema accepts, rejects, requires, or means in a way that is externally observable, maintainers should not silently modify the published schema while keeping the same identity as though nothing changed.

The registry SHA-256 digest exists specifically to make accidental mutation visible.

For an intentional contract change, the preferred path is:

1. introduce a new schema version/ID when the accepted contract changes materially;
2. add/update registry metadata and hashes;
3. provide valid/invalid fixtures for both the old and new expectations when the old line is still supported;
4. document migration behavior;
5. update conformance tooling/tests;
6. only remove the deprecated schema from the supported surface in a later documented change.

Purely non-semantic formatting changes should still be treated carefully because they alter the registry hash. If a hash changes, the reason must be explicit in review.

## Deprecation lifecycle

The default lifecycle before 1.0 is:

### 1. Proposal

Open a public issue before removing or materially changing an existing public contract.

The proposal should explain:

- what is being deprecated;
- why the existing contract is insufficient or unsafe;
- compatibility impact;
- security impact;
- migration path;
- expected wire/schema/crate version effect;
- whether a transition period is practical.

### 2. Introduction of replacement

Where practical, land the replacement before removing the old contract.

The replacement should have:

- documentation;
- tests or conformance cases;
- registry/schema updates when applicable;
- a changelog entry;
- migration guidance.

### 3. Deprecated-but-recognized period

During the transition period, the old contract may remain accepted/recognized while documentation clearly directs new implementations to the replacement.

The project does **not** promise a fixed number of months or releases for every pre-1.0 deprecation. The appropriate transition depends on security impact, implementation complexity, and whether maintaining both paths is safe.

When possible, maintainers should avoid removing a newly deprecated public contract in the same release that first announces its deprecation.

### 4. Removal

Removal should happen only in a release whose compatibility implications make the break explicit.

Before 1.0, that normally means one or more of:

- a new incompatible wire minor line;
- a new schema version/ID;
- a crate minor-version bump for a breaking Rust API change;
- an explicitly documented compatibility transition.

The removal must appear in `CHANGELOG.md` with a migration note.

## When immediate removal is allowed

A transition period may be shortened or skipped when keeping the deprecated behavior would create unreasonable security or correctness risk.

Examples include:

- validation bypasses;
- acceptance of malformed/ambiguous protocol input;
- behavior that could weaken approval or capability gates;
- registry integrity issues;
- a contract that exposes or mishandles sensitive data.

In those cases the release notes should explain the security/correctness reason without publishing exploit details that would endanger users before a fix is available.

## Additive changes

An additive change is not automatically compatible.

For example, adding an optional field may be structurally acceptable to one schema but still change semantics for a consumer that performs strict validation or assumes a closed set of behaviors.

Every additive proposal should still answer:

- Does the current schema permit the addition?
- Do old consumers ignore it safely?
- Does it change authorization, approval, evidence, or capability semantics?
- Does it require a new capability?
- Does it require a new schema or wire version?

When in doubt, prefer an explicit versioned change over an ambiguous "compatible" change.

## Capability deprecations

Capability identifiers describe public observable behavior and are negotiated explicitly.

If a capability is superseded:

- do not silently reinterpret the old capability name to mean the new behavior;
- introduce a new capability name/version when semantics materially change;
- document whether both can be advertised during migration;
- keep required-capability behavior fail closed;
- update machine-readable capability cases and Rust tests.

A task must still request only capability names selected for its session.

## Error-code deprecations

Stable public error codes should not be silently reused for unrelated meanings.

If an error code is replaced:

- document the old and new meaning;
- keep the old code recognizable during migration when practical;
- do not map security-sensitive failures into a more permissive category just for compatibility;
- add regression tests for the transition.

## Rust API deprecations

Public Rust helpers should use ordinary Rust deprecation mechanisms when practical (`#[deprecated]`) before removal.

A breaking Rust public-API removal before crate 1.0 should normally be accompanied by a crate minor-version bump and changelog/migration notes.

The crate version does not by itself determine wire compatibility.

## Migration notes

A breaking or deprecating change should answer, as concisely as possible:

- **Old behavior:** what consumers rely on today.
- **New behavior:** what replaces it.
- **Who is affected:** which messages/schemas/capabilities/helpers are involved.
- **Action required:** what an implementer must change.
- **Failure mode:** what happens if they do not migrate.
- **Version boundary:** crate/wire/schema versions involved.
- **Security impact:** whether the change closes or introduces a security boundary.

## CI and conformance requirements

A deprecation is incomplete if the repository's executable contracts disagree with the documentation.

When applicable, changes must update:

- JSON Schemas;
- schema registry hashes;
- compatibility matrix and cases;
- capability profile/cases;
- valid/invalid conformance fixtures;
- Rust tests/helpers;
- repository validators;
- public conformance tooling;
- `CHANGELOG.md` and migration documentation.

CI must be green before a deprecating or breaking change is merged.

## Release-note requirements

Every release containing a public deprecation or removal should include a dedicated section describing it.

Do not hide breaking behavior under generic wording such as "cleanup" or "refactor."

The release should state whether:

- existing payloads remain accepted;
- a new schema ID is required;
- a new wire version is required;
- a capability name/version changed;
- code changes are required for consumers.

## What this policy does not promise

Because the project is pre-1.0 and newly public, this policy does not promise:

- long-term support for every pre-1.0 line;
- a fixed deprecation period measured in months;
- backports to every historical release;
- compatibility across different pre-1.0 wire minor versions;
- that every experimental helper will survive to 1.0 unchanged.

Those stronger guarantees should only be made after real integration experience supports them.

## Relationship to 1.0

Before a 1.0 protocol line is declared, the project intends to define a stronger stable compatibility promise informed by real integrations and external feedback.

The purpose of this pre-1.0 policy is to make the path toward that stability transparent without pretending the current project has already reached it.

See also:

- [Compatibility](COMPATIBILITY.md)
- [Capability Negotiation](CAPABILITY_NEGOTIATION.md)
- [Security Model](SECURITY_MODEL.md)
- [Releasing](../RELEASING.md)
- [Changelog](../CHANGELOG.md)
