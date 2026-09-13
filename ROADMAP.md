# Roadmap

This roadmap describes the intended direction of Glomancy Protocol. It is deliberately conservative: the project should remain a small, auditable protocol layer rather than absorb product-specific runtime behavior.

## v0.1 — Public foundation

- [x] Extract the protocol from the private product boundary.
- [x] Publish Rust protocol types and validation helpers under MIT.
- [x] Publish versioned JSON Schemas and a SHA-256 registry.
- [x] Publish valid and invalid conformance fixtures.
- [x] Document fail-closed compatibility rules.
- [x] Add formatting, linting, tests, and CI.
- [ ] Publish the first tagged GitHub release after release-readiness review.

## v0.2 — Integration ergonomics

- [x] Add a small conformance command-line tool for validating public protocol payloads and fixtures.
- [x] Add more boundary and malformed-input test vectors.
- [x] Add reference integration examples that remain transport-neutral.
- [x] Define a machine-readable capability negotiation profile.
- [x] Add a documented deprecation process for pre-1.0 schema changes.

## v0.3 — Interoperability

- [x] Add language-neutral conformance vectors suitable for non-Rust consumers.
- [ ] Add reference vectors for version negotiation and approval flows.
- [ ] Add compatibility tests across supported protocol snapshots.
- [ ] Collect integration feedback and document implementation pitfalls.

## v1.0 — Stable protocol line

The project will only target 1.0 after the public contracts have received real integration feedback. Before 1.0 we intend to define:

- a stable compatibility promise;
- a documented schema evolution policy;
- a release and security-support policy;
- a conformance suite that can be consumed independently of the Rust crate.

## Non-goals

The roadmap does not include model-provider clients, credentials, billing, agent orchestration, desktop UI, proprietary Glomancy runtime code, or editor mutation implementations. Those concerns are intentionally outside this open protocol boundary.

Roadmap items are plans, not commitments. Discussion and proposals should happen in public GitHub Issues before large changes are implemented.
