# Glomancy Protocol

[![CI](https://github.com/charman-07/glomancy-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/charman-07/glomancy-protocol/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust 1.85+](https://img.shields.io/badge/rust-1.85%2B-orange.svg)](rust-toolchain.toml)

**Transport-neutral, fail-closed protocol contracts for safe AI-to-editor integrations.**

Glomancy Protocol is a small Rust library plus versioned JSON Schemas for the boundary between AI systems and editor/tooling runtimes. It defines how integrations negotiate versions, submit work, request approvals, report progress, return evidence, surface errors, and stay observable without coupling the protocol to one transport, model provider, or editor implementation.

The public protocol is intentionally separated from the commercial Glomancy product. This repository contains no provider credentials, billing logic, private agent runtime, desktop application, signing infrastructure, or editor mutation implementation.

## Why this exists

AI-assisted developer tools increasingly need to cross a high-trust boundary: an AI proposes work and another process may execute it. Ad-hoc JSON messages make compatibility, auditing, approval gates, and failure behavior difficult to reason about.

Glomancy Protocol makes that boundary explicit with:

- versioned handshake and compatibility rules;
- stable task lifecycle messages (`submit`, `progress`, `result`, `error`, `cancel`);
- explicit approval request/decision messages for risk-aware workflows;
- evidence records for verifiable outcomes;
- strict identifiers, trace/span metadata, and bounded protocol limits;
- a SHA-256-backed schema registry;
- fail-closed handling for unknown message kinds, schemas, and incompatible versions;
- valid and intentionally invalid fixtures for conformance testing.

## Quick start

Requirements: Rust 1.85 or newer.

```bash
git clone https://github.com/charman-07/glomancy-protocol.git
cd glomancy-protocol
cargo test --all-targets
cargo run --example quick_start
python3 scripts/validate_repository.py
```

The Rust example parses protocol versions, evaluates compatibility, and resolves a known message kind. The repository validator checks JSON integrity, schema-registry hashes, fixture references, and protocol-version consistency.

## Protocol surface

Current wire protocol: **0.4.0**. Initial public crate line: **0.1.x**.

The v1 schema set covers:

| Area | Message kinds |
| --- | --- |
| Negotiation | `handshake.request`, `handshake.response` |
| Task lifecycle | `task.submit`, `task.progress`, `task.result`, `task.error`, `task.cancel` |
| Human/policy approval | `approval.request`, `approval.decision` |
| Verification | `evidence.record` |
| Liveness | `heartbeat` |

See the [Consumer Integration Guide](docs/INTEGRATION_GUIDE.md) for an end-to-end language-neutral flow. [Architecture](docs/ARCHITECTURE.md), [Compatibility](docs/COMPATIBILITY.md), and [Security Model](docs/SECURITY_MODEL.md) document the design rationale and trust boundaries.

## Security principles

Glomancy Protocol treats the message boundary as untrusted input.

1. **Fail closed.** Unknown kinds, unknown schemas, and unsupported protocol combinations are rejected.
2. **Validate before execution.** Protocol validation is a prerequisite, not authorization to perform an action.
3. **Keep policy explicit.** Risk level and approval state belong in explicit contracts rather than hidden implementation behavior.
4. **Preserve evidence.** Results can reference evidence so consumers can distinguish claims from verifiable artifacts.
5. **Bound inputs.** Public constants define message, nesting, extension, and artifact limits.
6. **Keep secrets out of the protocol.** Credentials and provider-specific authentication are out of scope.

For vulnerability reporting, read [SECURITY.md](SECURITY.md). Please do not disclose sensitive vulnerabilities in public issues.

## Repository layout

```text
src/                 Rust protocol types and validation helpers
schemas/v1/          JSON Schema contracts
registry/v1/         Canonical schema registry and SHA-256 metadata
examples/v1/         Valid and invalid protocol fixtures
compatibility/v1/    Version negotiation rules and cases
docs/                Architecture, compatibility, security, and integration guides
scripts/              Repository integrity checks
tests/                Public contract regression tests
.github/              CI and contribution workflow templates
```

## Compatibility and versioning

Before 1.0, a patch change within the same protocol minor line is compatible; a different minor line is treated as incompatible. At 1.0 and later, versions with the same major version are considered protocol-compatible. Exact rules and negotiation behavior live in `compatibility/v1/compatibility-matrix.json` and are documented in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

Schema versions and wire-protocol versions are separate on purpose: a schema can evolve independently while negotiation remains explicit.

## Project status

This public repository is newly open-sourced, but the underlying Glomancy protocol work has already been under active development, testing, debugging, and repeated validation for roughly two months before this repository was opened. The current public focus is a small, auditable protocol core with conformance fixtures and clear compatibility behavior rather than a large framework.

Planned work is tracked in [ROADMAP.md](ROADMAP.md) and GitHub Issues. Roadmap items are direction, not promises or fabricated adoption claims.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before opening a pull request. Good first contributions include additional fixtures, validation tests, documentation, and transport-neutral interoperability examples.

Project decisions and maintainer responsibilities are described in [GOVERNANCE.md](GOVERNANCE.md). Support guidance is in [SUPPORT.md](SUPPORT.md).

## Release discipline

Every release should pass formatting, Clippy, tests, documentation checks, cross-platform test jobs, and repository integrity validation. The release checklist is documented in [RELEASING.md](RELEASING.md), and notable changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## License

Glomancy Protocol is licensed under the [MIT License](LICENSE).

The separate commercial Glomancy product and its private implementation are **not** licensed under this repository's MIT license.
