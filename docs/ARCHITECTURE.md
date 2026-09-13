# Architecture

Glomancy Protocol is a contract layer, not an agent framework or editor runtime. Its job is to make the boundary between an AI-side system and an editor/tooling-side system explicit, versioned, and testable.

## Design constraints

The protocol is designed to remain:

- **transport-neutral** — the same messages can be carried over local IPC, sockets, queues, HTTP, or another transport;
- **provider-neutral** — no model vendor is required by the wire contract;
- **editor-neutral** — the protocol describes work and outcomes without embedding one editor's mutation API;
- **fail-closed** — unknown or incompatible input is rejected rather than guessed;
- **auditable** — schema IDs, hashes, approvals, evidence, and tracing metadata are explicit;
- **small** — orchestration, credentials, billing, UI, and proprietary runtime behavior stay outside this package.

## Conceptual flow

```text
AI / planning side
      |
      | handshake.request / handshake.response
      v
Protocol boundary + version negotiation
      |
      | task.submit
      v
Policy / approval decision
      |
      | approval.request <-> approval.decision (when required)
      v
Execution-side implementation
      |
      | task.progress
      | task.result + evidence.record
      | or task.error / task.cancel
      v
Consumer / observer
```

The protocol does not define how the execution-side implementation performs a requested operation. It defines the envelope and contracts around that operation.

## Rust layer

The Rust crate exposes:

- protocol and schema version helpers;
- stable message-kind enums and wire names;
- header validation;
- identifier and hash-shape checks;
- public protocol limits and error codes;
- generated schema registry descriptors.

The Rust layer intentionally has no external runtime dependency in the initial public baseline.

## Schema layer

`schemas/v1/` is the language-neutral contract surface. Each public message schema has a stable URN and a SHA-256 digest recorded in `registry/v1/manifest.json`.

The registry makes accidental schema drift detectable. `scripts/validate_repository.py` recalculates these hashes in CI.

## Fixtures

`examples/v1/valid/` contains payloads expected to satisfy their schemas. `examples/v1/invalid/` contains targeted negative cases and records the expected validation keyword in the fixture manifest.

These fixtures are intended to become a cross-language conformance surface, not merely documentation examples.

## Compatibility layer

`compatibility/v1/compatibility-matrix.json` defines negotiation rules separately from code. Rust compatibility helpers and documentation must remain aligned with this matrix.

At the current pre-1.0 wire version, a patch difference inside the same minor line is compatible, while a minor change is considered incompatible. This conservative rule prevents silent interpretation of a changed pre-1.0 contract.

## Trust boundaries

Protocol validation answers: **"Is this input structurally and semantically acceptable to the protocol?"**

It does not answer: **"Should this action be authorized in this environment?"**

Authorization, sandboxing, user consent, rate limits, filesystem boundaries, process isolation, and editor-specific safety checks remain responsibilities of the integrating system. See `docs/SECURITY_MODEL.md`.

## Public/private boundary

The open repository contains only reusable protocol infrastructure. Private Glomancy product code may consume these contracts, but this repository does not expose private runtime implementations or make them part of the protocol API.
