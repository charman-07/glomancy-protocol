# Changelog

All notable changes to Glomancy Protocol are documented here.

The project follows semantic versioning for the Rust package. Wire-protocol compatibility is documented separately because the crate version, wire version, and individual schema versions are intentionally independent.

## [Unreleased]

### Added

- Public OSS governance, roadmap, support, release, architecture, compatibility, and security-model documentation.
- GitHub issue forms, pull-request template, CODEOWNERS, and Dependabot configuration.
- Repository-integrity validation for JSON files, schema hashes, fixture references, and version consistency.
- Executable JSON Schema conformance checks for the public valid/invalid fixture corpus, including format validation and expected-failure keywords.
- Expanded malformed/boundary vectors for UUIDs, timestamps, trace IDs, URIs, duplicate capabilities, and empty instructions.
- Public `glomancy_conformance.py` CLI for validating payloads, executing fixtures, and listing registered message schemas without the private Glomancy runtime.
- External implementer conformance guide with stable CLI exit codes and CI examples.
- Supply-chain maintenance policy covering dependency review, update cadence, immutable Action pinning, and release gates.
- Pip dependency monitoring alongside GitHub Actions and Cargo Dependabot updates.
- Public contract regression tests.
- Cross-platform CI on Linux, Windows, and macOS in addition to formatting, Clippy, Rustdoc, and repository-contract checks.

### Security

- GitHub Actions checkout usage pinned to an immutable upstream commit SHA in CI.
- Release checklist expanded to include conformance and supply-chain review requirements.

## 0.1.0 source baseline — 2026-09-13

### Added

- Initial public Rust protocol package.
- Wire protocol `0.4.0` compatibility helpers.
- Message kinds for handshake, task lifecycle, approvals, evidence, and heartbeat.
- Versioned JSON Schema set and SHA-256 registry metadata.
- Valid and invalid example payloads.
- Compatibility matrix and cases.
- MIT license, contribution guidance, security policy, and baseline CI.

A tagged GitHub release should only be created after the release checklist in `RELEASING.md` has passed.
