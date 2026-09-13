# Security Model

Glomancy Protocol is intended for a security-sensitive boundary: structured messages can describe work that another component may eventually execute. This document describes what the protocol protects, what it assumes, and what remains the responsibility of an integration.

## Assets

The protocol helps protect the integrity of:

- version negotiation;
- message-kind interpretation;
- schema identity;
- task lifecycle state;
- approval decisions;
- evidence references;
- trace and span identifiers;
- public limits and error semantics.

## Threats considered

The project is designed to reduce risk from:

- unknown or unsupported message kinds being interpreted optimistically;
- incompatible protocol versions being silently accepted;
- malformed identifiers and tracing metadata;
- accidental mutation of registered schemas;
- oversized or deeply nested messages exceeding public policy limits;
- a high-risk workflow proceeding without an explicit approval contract;
- results being represented without the expected evidence contract;
- protocol drift between code, schemas, fixtures, and documentation.

## Security properties

### Fail-closed parsing

Unknown message kinds and unsupported protocol combinations are rejected. Integrations should preserve this behavior and must not map unknown values to a permissive default.

### Registry-aware Rust header validation

The public Rust `MessageHeader::validate()` helper performs more than identifier-shape checks. For the current compiled public protocol registry it also requires:

- a wire protocol version compatible with the crate's current `PROTOCOL_VERSION` rules;
- a registered schema ID rather than merely a syntactically valid schema URN;
- an exact match between the registered schema's message kind and the header's `kind`.

A syntactically valid but unknown schema URN therefore fails closed, as does pairing a known schema ID with the wrong message kind. Compatible pre-1.0 patch versions remain valid under the documented compatibility rules, while incompatible protocol lines are rejected.

This helper is still **not** complete message validation. It does not replace JSON Schema validation of the payload, capability checks, authentication, authorization, policy, approval, sandboxing, or editor/tool permissions.

### Schema integrity

The registry records SHA-256 digests for public schemas. CI recalculates the registered hashes to catch accidental or unauthorized drift in repository content.

A digest is an integrity mechanism, not a signature. Authenticity of downloaded releases remains a distribution concern.

### Explicit approval

Approval request and decision messages make approval state visible at the protocol level. The protocol does not decide organizational policy; integrations decide when approval is required and must enforce the decision before execution.

### Bounded inputs

Public constants define upper bounds for message size, payload depth, extensions, and artifacts. Integrations should enforce equivalent or stricter limits before expensive processing.

The same limits are published in [`limits/v1/policy.json`](../limits/v1/policy.json) so non-Rust consumers do not have to infer security-sensitive maximums from source code. Repository CI checks exact parity between the machine-readable policy and the Rust constants. See [Public Resource Limits](RESOURCE_LIMITS.md) for the current values, units, counting semantics, and assurance boundary.

These maximums reduce one class of resource-pressure risk but do not provide denial-of-service immunity. Integrations remain responsible for transport framing, rate limiting, concurrency limits, timeouts, memory/process isolation, and stricter local limits where appropriate.

### Traceability

Headers carry message IDs, timestamps, sender identity fields, trace IDs, and span IDs. These fields improve correlation and auditing but do not authenticate a sender by themselves.

## Machine-readable security invariants

The security-sensitive behavioral subset that currently has executable language-neutral regression evidence is also published in [`security/v1/invariants.json`](../security/v1/invariants.json).

Each invariant has a stable `GLM-SEC-*` ID and references exact public vector cases. Repository CI verifies that those references exist, that the catalog's wire version agrees with the vector suite, and that each invariant includes fail-closed evidence.

The current catalog covers incompatible/unadvertised version handling, task capability selection, approval gating/correlation/expiry/denial, evidence closure, and terminal task ordering.

This catalog is **regression assurance**, not formal verification. It does not prove every implementation secure and does not replace authentication, authorization, policy, sandboxing, editor/tool permissions, security review, or external testing. See [Security Invariants](SECURITY_INVARIANTS.md) for the exact assurance boundary and validation workflow.

The invariant catalog and resource-limits policy are both included in the deterministic public contract fingerprint, so changing a cataloged security expectation or public protocol maximum changes the aggregate public-contract SHA-256 used by release-readiness reporting.

## Out of scope / integration responsibilities

The protocol does **not** provide:

- user authentication or authorization;
- transport encryption;
- credential storage;
- process or filesystem sandboxing;
- model-provider security;
- editor-specific permission enforcement;
- malware detection;
- supply-chain signing or release provenance by itself;
- guarantees that a requested editor action is safe simply because its message validates.

An integration must treat successful protocol validation as necessary but insufficient for execution.

## Trust-boundary guidance

A recommended consuming pipeline is:

```text
bytes from transport
  -> size/rate limits
  -> parse
  -> schema + protocol validation
  -> version compatibility
  -> authentication/authorization
  -> policy and risk evaluation
  -> explicit approval when required
  -> sandboxed/editor-specific execution
  -> post-condition validation
  -> evidence + result
```

Skipping later authorization or policy layers because a message is schema-valid is unsafe.

## Vulnerability classes of interest

Security reports are especially useful for issues involving validation bypasses, fail-open behavior, schema/registry mismatch, ambiguous version negotiation, malformed-input crashes, unsafe defaults, bounded-input bypasses, or contracts that allow approval/evidence invariants to be bypassed.

Follow `SECURITY.md` for private reporting. Do not place exploit details or sensitive data in a public issue.
