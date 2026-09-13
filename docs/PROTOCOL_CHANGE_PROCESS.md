# Protocol Change Process

Glomancy Protocol treats public contract changes as engineering decisions, not ordinary source edits. This process is designed to make compatibility, security, migration, and conformance impact visible before a change is merged.

The process is intentionally lightweight enough for a small project while still providing an auditable path for significant changes.

## Change classes

Every change that can affect a consumer should be classified before implementation.

### Class 0 — Editorial / non-contract

Examples:

- typo fixes;
- clearer prose that does not change normative meaning;
- CI refactors that preserve observable behavior;
- internal test cleanup with no public contract change.

A normal pull request is sufficient. A protocol-change proposal is not required.

### Class 1 — Additive compatible

Examples:

- a new optional conformance vector area that does not change existing expected outcomes;
- additional documentation or examples for an already-defined rule;
- a new helper API that preserves existing wire/schema behavior;
- a new machine-readable catalog that mirrors an existing public vocabulary.

Open an issue when the change touches a public contract surface. The proposal must explain why existing consumers remain compatible.

### Class 2 — Behavioral / compatibility-sensitive

Examples:

- changing negotiation behavior;
- changing capability or approval semantics;
- changing task lifecycle expectations;
- changing public limits or error handling;
- introducing a new message kind or schema identity;
- changing how unknown or malformed input is handled.

A protocol-change proposal is required before implementation. The proposal must include compatibility, migration, security, conformance, and rollout analysis.

### Class 3 — Breaking or security-sensitive

Examples:

- removing or renaming a public message kind;
- changing an existing schema identity or meaning incompatibly;
- changing a published wire behavior so an existing conforming consumer would reject or misinterpret data;
- weakening a fail-closed rule;
- changing an approval/security boundary;
- emergency remediation for a vulnerability that requires incompatible behavior.

A protocol-change proposal is required. Breaking changes must be explicit in release notes and migration guidance. Security-sensitive details may be withheld from public discussion until disclosure is safe, following `SECURITY.md`.

## Required proposal content

For Class 2 and Class 3 changes, the issue must answer all of the following:

1. **Problem** — What concrete problem is being solved?
2. **Affected contract** — Which schema, wire rule, registry entry, capability rule, approval rule, lifecycle rule, error contract, or public API is affected?
3. **Proposed behavior** — What exact observable behavior changes?
4. **Compatibility** — Which existing consumers/messages/releases remain compatible, and which do not?
5. **Migration** — What must an implementer change, and can old/new behavior coexist temporarily?
6. **Security** — Does the change affect trust boundaries, authorization assumptions, fail-closed behavior, parsing, validation, approval, evidence, or resource limits?
7. **Conformance** — Which tests, fixtures, vectors, registry parity checks, or examples will prove the new behavior?
8. **Alternatives** — What reasonable alternatives were considered and why were they rejected?
9. **Release impact** — What version/release-note/deprecation action is required?
10. **Public/private boundary** — Confirm that the proposal does not require proprietary Glomancy runtime/editor implementation details to become public.

The repository provides a structured GitHub Issue form for this purpose.

## Decision states

A proposal may be treated as:

- **proposed** — open for technical review;
- **accepted for implementation** — direction is sufficiently clear to begin a focused PR;
- **needs revision** — unresolved compatibility/security/design concerns remain;
- **declined** — not aligned with project scope or safety/compatibility goals;
- **superseded** — replaced by a newer proposal.

GitHub Issues remain the public record. The project does not currently maintain a separate standards body or voting committee.

## Implementation requirements

An accepted proposal does not bypass normal engineering gates. The implementation PR should:

- link the proposal issue;
- contain the smallest coherent contract change;
- update executable tests/fixtures/vectors where behavior changes;
- update machine-readable registries/catalogs when applicable;
- update compatibility and migration documentation;
- update CHANGELOG/release notes as appropriate;
- pass the full applicable CI suite;
- preserve the public/private boundary.

If implementation reveals a materially different design from the accepted proposal, update the issue before merge rather than allowing the PR to redefine the decision silently.

## Compatibility discipline

Published schema IDs and release snapshots are historical evidence. Do not rewrite them silently to make a new implementation appear compatible.

When compatibility cannot be preserved, prefer an explicit new version, schema identity, or documented migration path over ambiguous dual meaning.

Pre-1.0 status allows breaking changes, but it does not make undocumented breaking changes acceptable.

## Security discipline

Protocol validation is necessary but is not authorization. A proposal must not describe schema validation, capability negotiation, approval correlation, or a known error code as granting local execution authority.

Changes that could weaken fail-closed behavior require explicit security justification and targeted negative tests.

## Emergency security changes

A vulnerability may require maintainers to develop a fix privately before public disclosure. In that case:

1. use the private reporting process in `SECURITY.md`;
2. minimize disclosure until a fix/release is ready;
3. document non-sensitive compatibility/migration impact at release time;
4. add regression tests once doing so is safe;
5. avoid inventing a public proposal trail containing exploit details merely for process appearance.

## Rejected proposals and future reconsideration

A declined proposal can be revisited when new technical evidence, adoption needs, or interoperability constraints emerge. Reconsideration should link the earlier discussion so the decision history remains traceable.
