# Changelog

All notable changes to Glomancy Protocol are documented here.

The project follows semantic versioning for the Rust package. Wire-protocol compatibility is documented separately because the crate version, wire version, and individual schema versions are intentionally independent.

## [Unreleased]

### Added

- Public OSS governance, roadmap, support, release, architecture, compatibility, and security-model documentation.
- GitHub issue forms, pull-request template, CODEOWNERS, and Dependabot configuration.
- Repository-integrity validation for JSON files, schema hashes, fixture references, and version consistency.
- Public contract regression tests.
- Cross-platform CI on Linux, Windows, and macOS in addition to formatting, Clippy, Rustdoc, and repository-contract checks.

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
