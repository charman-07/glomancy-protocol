# Changelog

All notable changes to Glomancy Protocol are documented here.

The project follows semantic versioning for the Rust package. Wire-protocol compatibility is documented separately because the crate version, wire version, and individual schema versions are intentionally independent.

## [Unreleased]

No unreleased public changes yet.

## [0.1.0] — 2026-09-13

First public early-stage release of Glomancy Protocol.

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
- External implementer conformance guide with stable CI-oriented exit codes.
- Capability-negotiation profile v1 with exact name/version matching, required/optional semantics, duplicate-name rejection, and task-time selected-capability subset checks.
- Rust capability-negotiation helpers/tests and machine-readable capability conformance cases.
- Comprehensive Glomancy product/protocol overview explaining the broader product goal, protocol role, benefits, target audiences, example workflows, maturity, and public/private boundary.
- Public architecture, integration, compatibility, security-model, governance, support, roadmap, release, and supply-chain documentation.
- Pre-1.0 deprecation and schema-evolution policy with explicit migration and removal expectations.
- GitHub issue forms, pull-request template, CODEOWNERS, and Dependabot configuration.
- Dependency monitoring for Cargo, Python conformance tooling, and GitHub Actions.
- Public contract regression tests.
- Cross-platform CI on Linux, Windows, and macOS plus formatting, Clippy, tests, example execution, Rustdoc, repository-contract, capability-profile, fixture, and conformance CLI checks.

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

This release is pre-1.0 and early-stage. It does not claim broad production adoption, industry-standard status, or long-term compatibility guarantees. The commercial/private Glomancy implementation is not part of this MIT-licensed repository.
