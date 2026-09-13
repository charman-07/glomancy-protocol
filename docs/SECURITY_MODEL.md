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

### Schema integrity

The registry records SHA-256 digests for public schemas. CI recalculates the registered hashes to catch accidental or unauthorized drift in repository content.

A digest is an integrity mechanism, not a signature. Authenticity of downloaded releases remains a distribution concern.

### Explicit approval

Approval request and decision messages make approval state visible at the protocol level. The protocol does not decide organizational policy; integrations decide when approval is required and must enforce the decision before execution.

### Bounded inputs

Public constants define upper bounds for message size, payload depth, extensions, and artifacts. Integrations should enforce equivalent or stricter limits before expensive processing.

### Traceability

Headers carry message IDs, timestamps, sender identity fields, trace IDs, and span IDs. These fields improve correlation and auditing but do not authenticate a sender by themselves.

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

Security reports are especially useful for issues involving validation bypasses, fail-open behavior, schema/registry mismatch, ambiguous version negotiation, malformed-input crashes, unsafe defaults, or contracts that allow approval/evidence invariants to be bypassed.

Follow `SECURITY.md` for private reporting. Do not place exploit details or sensitive data in a public issue.
