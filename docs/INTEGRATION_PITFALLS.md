# Integration Pitfalls and Implementation Notes

This document records implementation pitfalls that are already visible from the public Glomancy Protocol contracts, conformance tooling, and maintainer testing.

It does **not** claim external production adoption or third-party feedback that has not happened yet. Real external integration feedback will be added separately when it exists.

## 1. Do not confuse compatibility with version selection

`wire-compatibility` answers whether two concrete wire versions are considered compatible under the public policy.

Handshake version selection is a different decision. Peers advertise exact `supported_versions`, and the current reference vectors select the highest version explicitly advertised by both sides.

Do not silently invent an unadvertised selected version merely because two versions would otherwise be patch- or major-compatible.

## 2. Do not treat protocol validation as authorization

A payload can be valid and still be forbidden to execute.

Schema validation, wire compatibility, capability negotiation, task-capability gating, and approval correlation are all prerequisites or protocol decisions. None of them replaces:

- authentication;
- authorization;
- policy evaluation;
- sandboxing;
- editor/project permissions;
- user or organization controls.

A consumer should keep the execution authorization decision explicit and separate.

## 3. Capability names and versions are exact

The current capability profile uses exact `name + version` matching.

Common mistakes include:

- treating `1.0.0` as automatically compatible with `1.1.0`;
- accepting an unsupported required capability;
- leaving duplicate capability names unresolved;
- allowing a task to request capabilities that were not selected during the session handshake.

Unsupported required capabilities fail closed. Unsupported optional capabilities are omitted.

## 4. Approval decisions must correlate to the outstanding request

An `approval.decision` should not be accepted merely because it contains `decision: approve`.

The reference flow requires:

- matching `approval_id`;
- matching `task_id`;
- a valid `approve` or `deny` decision;
- a decision timestamp that is not later than the request expiry.

A valid `deny` decision is a valid protocol decision but does not authorize execution.

A valid `approve` decision can satisfy the approval gate but still does not bypass authorization, capability, policy, or editor-permission checks.

## 5. Schema IDs are public identities

Do not change the bytes behind an already published schema ID while leaving the ID unchanged.

The compatibility snapshot suite pins SHA-256 hashes from published releases. If a schema contract changes, create an intentional new schema version/ID and document the migration instead of silently mutating a published identity.

## 6. Wire version, crate version, and schema version are independent

The Rust package version, wire protocol version, JSON Schema versions, and consumer-vector version are intentionally separate.

Do not infer wire compatibility from the crate version alone, and do not assume a schema revision requires the same numeric change to the Rust package or wire version.

Read the relevant compatibility/evolution policy for each layer.

## 7. Unknown message kinds should fail closed

A consumer should resolve known message kinds through the public registry and reject unknown kinds.

Falling back to a generic execution path for an unknown message kind defeats the purpose of a typed protocol boundary and can turn unsupported input into unintended behavior.

## 8. Validate before dispatch

Do not route a message to an editor/tool handler before validating its envelope and selected schema.

A safer order is:

1. enforce transport/message-size limits;
2. parse the envelope;
3. resolve `kind` / `schema_id` against the public registry;
4. validate the payload;
5. check wire/session compatibility;
6. check selected capabilities;
7. apply approval/policy/authorization gates;
8. dispatch through the intended tool integration.

The exact private execution architecture remains implementation-specific.

## 9. Evidence is not the same as a success string

A result that says "completed" is not automatically proof that the requested editor state exists.

Consumers should preserve evidence references and, where appropriate, verify them against the actual tool/editor state. The protocol provides evidence-oriented contracts so implementations can distinguish a claim from a verifiable artifact or observation.

## 10. Bound inputs before they reach expensive or privileged code

Protocol limits exist so untrusted input does not become arbitrarily large or deeply nested work for downstream components.

Do not remove or bypass limits merely because an upstream model normally produces well-formed output. Treat every protocol boundary as untrusted input.

## 11. Keep provider and editor details outside portable contracts

Glomancy is currently being developed primarily for Unreal Engine, but the public protocol intentionally remains editor-agnostic and provider-neutral.

Avoid adding private Unreal mutation commands, model-provider credentials, billing behavior, proprietary planner state, or product-specific transport details to the portable protocol unless they are genuinely generic public contract concepts.

## 12. Test your implementation with the public vectors, not by copying the validator

The repository validators are reference consistency checks. External implementations should implement the documented behavior independently and run the JSON vectors as inputs/expected outputs.

Copying the validator implementation into production code can hide interpretation differences instead of testing them.

## Feedback status

### Maintainer-derived notes

The pitfalls above come from protocol design review, fixture work, CI failures, compatibility hardening, and the public reference/conformance implementation maintained in this repository.

### External integration feedback

No external production integration feedback is claimed here yet.

When real feedback arrives, record it with enough context to be useful:

- implementation language/runtime;
- protocol/vector version tested;
- affected message or flow;
- observed ambiguity or failure mode;
- whether the issue was documentation, implementation, or protocol design;
- resulting issue/PR/release when applicable.

Do not add anonymous marketing claims, invented users, fabricated deployment counts, or unverifiable adoption statements.

## Related documents

- [Consumer Integration Guide](INTEGRATION_GUIDE.md)
- [Language-Neutral Consumer Vectors](CONSUMER_VECTORS.md)
- [Compatibility](COMPATIBILITY.md)
- [Capability Negotiation](CAPABILITY_NEGOTIATION.md)
- [Security Model](SECURITY_MODEL.md)
- [Published Compatibility Snapshots](SNAPSHOT_COMPATIBILITY.md)
- [Pre-1.0 Deprecation and Schema Evolution](DEPRECATION_POLICY.md)
