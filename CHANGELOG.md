# Changelog

All notable changes to Glomancy Protocol are documented here.

The project follows semantic versioning for the Rust package. Wire-protocol compatibility is documented separately because the crate version, wire version, and individual schema versions are intentionally independent.

## [Unreleased]

### Added

- Versioned, language-neutral consumer conformance vectors in plain JSON for message-kind lookup, wire compatibility, capability negotiation, task-time capability gating, explicit advertised-version selection, and approval-flow correlation/expiry handling.
- End-to-end task-lifecycle conformance vectors covering approval-gated success, selected-capability enforcement, task correlation, evidence closure, denial/expiry behavior, and terminal-result ordering; the consumer-vector suite advances to `1.2.0`.
- Dependency-free repository validator for the consumer vectors so CI detects drift between expected outcomes and the public registry/compatibility/capability/approval/lifecycle rules.
- External implementer documentation explaining how non-Rust consumers can run the same expected-outcome suite without depending on the Rust crate or private Glomancy runtime.
- Stable, versioned machine-readable `--json` output for the public conformance CLI commands `validate`, `fixtures`, and `list-schemas`, while preserving the existing exit-code contract.
- Draft 2020-12 JSON Schema contract for conformance CLI JSON output version `1.0.0`, plus CI validation of representative real CLI results against that schema.
- Dependency-free independent Python consumer example that implements public version-selection, capability, task-gate, and approval decisions without importing the Rust crate or repository vector validator.
- Dependency-free independent JavaScript/Node.js consumer example that executes the same public decisions without delegating to Python or Rust.
- Published compatibility snapshots that pin real release metadata and public schema hashes, starting with the actual `v0.1.0` release, plus CI regression checks against the current contract.
- Snapshot compatibility documentation describing how maintainers add future real release baselines without fabricating historical states.
- Maintainer-derived integration pitfalls guide covering version selection, approval correlation, validation vs. authorization, schema identity, capability semantics, evidence handling, bounded inputs, and fail-closed dispatch.
- Unreal Engine product-context documentation clarifying that Glomancy is currently developed primarily for Unreal Engine while Glomancy Protocol remains editor-agnostic, transport-neutral, and provider-neutral.
- Pinned external-adoption guidance for consuming release tags, verifying registry hashes, vendoring non-Rust protocol assets, and upgrading pre-1.0 integrations deliberately.
- Structured integration-feedback path for genuine external implementers without implying adoption that has not occurred.
- Stdlib-only Rust/JSON registry parity validation that fails CI if public message kinds, schema IDs, schema versions, hashes, or schema paths drift between the canonical JSON registry and the Rust crate snapshot.
- Fail-closed Rust `from_wire` helpers for public component, risk-level, execution-mode, task-status, and error-category enums, plus CI parity checks against the canonical enum values in `common.schema.json`.
- Registry-aware Rust `MessageHeader::validate()` checks for incompatible wire versions, unknown registered schema IDs, and schema-ID/message-kind mismatches while preserving existing structural header validation.
- Versioned machine-readable protocol error-code catalog with fail-closed Rust parsing, round-trip tests, and CI parity checks between `errors/v1/catalog.json` and `ProtocolErrorCode`.
- Formal protocol-change governance with change classes, structured proposal requirements, a dedicated GitHub Issue form, and explicit compatibility/security/migration/conformance review expectations.
- Public `MAINTAINERS.md` register and release-quality gate documentation covering source quality, cross-platform portability, contract integrity, security review, release metadata, and post-release verification.
- Manually runnable release-readiness audit workflow with exact-ref checkout, Rust/repository-contract/cross-platform gates, deterministic release-facing metadata validation, and an audited ref/SHA summary without publishing or certifying a release.

### Clarified

- Handshake version selection is distinct from compatibility classification: consumers select the highest exact version explicitly advertised by both peers and fail closed when no shared advertised version exists.
- Approval decisions are correlated by both `approval_id` and `task_id`; expired or mismatched decisions are rejected, while a valid deny decision is accepted as a decision but never authorizes execution.
- Published schema IDs are immutable identities: a compatible current contract may not silently change the SHA-256 content or message-kind mapping behind a pinned release schema ID.
- Maintainer-derived implementation notes are tracked separately from genuine external integration feedback; the project does not claim third-party production adoption or feedback that has not occurred.
- The `v0.1.0` wording describes the first public pre-1.0 release rather than implying that the underlying Glomancy/protocol work began when the public repository was opened.
- The generic JSON Schema `error.code` pattern permits future well-formed codes, while the versioned error catalog records the codes currently defined by this protocol package; unknown codes remain unknown and must not be treated as implicitly supported.
- Project process requirements are distinct from GitHub-enforced repository controls; branch/ruleset protection is not claimed until it is actually configured and verified.

## [0.1.0] — 2026-09-13

First public pre-1.0 release of Glomancy Protocol.

### Added

- Initial MIT-licensed Rust protocol package and public validation helpers.
- Wire protocol `0.4.0` compatibility helpers and machine-readable compatibility cases.
- Message kinds for handshake, task lifecycle, approvals, evidence, and heartbeat.
- Versioned Draft 2020-12 JSON Schemas and a canonical SHA-256 schema registry.
- Valid and intentionally invalid conformance fixtures.
- Repository-integrity validation for JSON files, registry hashes, fixture references, and version consistency.
- Executable JSON Schema conformance checks with UUID/date-time/URI format validation and expected-failure keyword checking.
- Expanded malformed/boundary vectors for identifiers, timestamps, trace IDs, URIs, duplicate capabilities, and empty instructions.
- Public `glomancy_conformance.py` CLI for validating payloads, running the fixture corpus, and listing registered schemas without the private Glomancy runtime.
- Transport-neutral executable reference consumer demonstrating wire compatibility, exact capability negotiation, task capability gating, schema resolution, fail-closed required-capability rejection, and the separate authorization boundary.
- External implementer conformance guide with stable CI-oriented exit codes.
- Capability-negotiation profile v1 with exact name/version matching, required/optional semantics, duplicate-name rejection, and task-time selected-capability subset checks.
- Rust capability-negotiation helpers/tests and machine-readable capability conformance cases.
- Comprehensive Glomancy product/protocol overview explaining the broader product goal, protocol role, benefits, target audiences, example workflows, maturity, and public/private boundary.
- Public architecture, integration, compatibility, security-model, governance, support, roadmap, release, and supply-chain documentation.
- Pre-1.0 deprecation and schema-evolution policy with explicit migration and removal expectations.
- GitHub issue forms, pull-request template, CODEOWNERS, and Dependabot configuration.
- Dependency monitoring for Cargo, Python conformance tooling, and GitHub Actions.
- Public contract regression tests.
- Cross-platform CI on Linux, Windows, and macOS plus formatting, Clippy, tests, executable examples, Rustdoc, repository-contract, capability-profile, fixture, and conformance CLI checks.

### Security

- Fail-closed behavior for unknown message kinds, unknown schema IDs, incompatible wire versions, and unsupported required capabilities.
- Explicit task-time rejection semantics for capability names that were not selected during the session handshake.
- Public/private boundary checks for obvious credential, key material, developer-private path, and private-repository leakage.
- GitHub Actions checkout pinned to the verified immutable commit SHA for upstream `actions/checkout` v7.0.1.
- Release checklist includes conformance, public/private boundary, and supply-chain review requirements.
- Pre-1.0 evolution policy permits shortened deprecation windows when retaining old behavior would create unreasonable security or correctness risk, while requiring explicit migration/release notes.

### Maintenance

- Pinned Python `jsonschema` conformance dependency updated from 4.23.0 to 4.26.0 after a green full CI run.

### Compatibility

- Rust crate version: `0.1.0`.
- Current wire protocol: `0.4.0`.
- Current public v1 schema IDs: `1.0.0` line.
- Pre-1.0 wire versions use conservative compatibility semantics: same `0.x` minor with patch differences may be compatible; different pre-1.0 minor lines are incompatible.

### Status

This release is pre-1.0. The public repository was newly open-sourced at this point, while the underlying Glomancy/protocol work had already been under active development, testing, debugging, and repeated validation before publication. It does not claim broad production adoption, industry-standard status, or long-term compatibility guarantees. The commercial/private Glomancy implementation is not part of this MIT-licensed repository.
