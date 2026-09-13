# Pull request

## What changes?

<!-- Describe the problem and the smallest coherent change. -->

## Change class / proposal

- [ ] Class 0 — editorial / non-contract
- [ ] Class 1 — additive compatible
- [ ] Class 2 — behavioral / compatibility-sensitive
- [ ] Class 3 — breaking or security-sensitive

Protocol-change proposal issue (required for Class 2/3 unless handled privately under SECURITY.md):

<!-- e.g. Closes #123 / N/A for Class 0 -->

## Public contract impact

Affected surfaces:

- [ ] No public contract behavior changes
- [ ] Wire protocol / version negotiation
- [ ] JSON Schema / schema identity / registry
- [ ] Capability negotiation
- [ ] Approval / task lifecycle / evidence
- [ ] Error codes / categories / public limits
- [ ] Rust public API/helper behavior
- [ ] Conformance vectors / compatibility snapshots
- [ ] Documentation-only normative clarification

Compatibility and migration notes:

<!-- State what remains compatible, what changes, and what implementers must do. -->

## Security and trust-boundary impact

<!-- Describe fail-closed behavior, parsing/validation, authorization assumptions, approval/evidence, resource limits, or other security impact. Write "None" only when genuinely not applicable. -->

- [ ] This change does not treat protocol validation/conformance as execution authorization.
- [ ] Unknown/unsupported input remains fail-closed, or an approved proposal explicitly explains the change.

## Executable evidence

<!-- List tests, fixtures, vectors, parity checks, examples, or snapshots changed/added. -->

- [ ] Observable behavior changes have executable evidence.
- [ ] Machine-readable contracts and Rust/helpers remain consistent.

## Verification

- [ ] `cargo fmt --check`
- [ ] `cargo clippy --all-targets -- -D warnings`
- [ ] `cargo test --all-targets`
- [ ] `python3 scripts/validate_repository.py`
- [ ] Relevant repository-contract validators were run for the changed surface
- [ ] Linux/Windows/macOS CI is green where applicable
- [ ] Documentation and CHANGELOG/release notes are updated when needed

## Release impact

<!-- Mention crate/wire/schema/catalog/vector version impact, deprecation/migration notes, or why no release-facing change is needed. -->

## Public boundary check

- [ ] No credentials, tokens, private certificates, customer data, sensitive private paths, signing material, proprietary runtime/provider/billing/editor-mutation code, or other private Glomancy implementation details are included.
- [ ] The change does not claim adoption, certification, production usage, or compatibility evidence that has not actually been demonstrated.
