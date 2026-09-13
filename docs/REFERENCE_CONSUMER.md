# Reference Consumer

This document accompanies `examples/reference_consumer.rs` and shows how an external implementation can consume Glomancy Protocol without depending on the private commercial Glomancy runtime.

The example is intentionally small and transport-neutral. It demonstrates protocol decisions that should happen before an integration performs editor- or tool-specific work.

## What it demonstrates

The executable example walks through five public contract checks:

1. **Wire compatibility** — parse the remote wire version and reject an incompatible protocol line.
2. **Capability negotiation** — select exact name/version matches, reject unsupported required capabilities, and omit unsupported optional capabilities.
3. **Task capability gating** — accept only capability names selected for the current session.
4. **Message/schema resolution** — resolve a known message kind to its canonical registered schema rather than guessing from payload shape.
5. **Authorization boundary** — finish by making it explicit that successful protocol validation and capability negotiation do not authorize execution.

Run it with:

```bash
cargo run --example reference_consumer
```

The example should end with output indicating that the wire versions are compatible, a known schema was resolved, an unsupported required capability was rejected, and authorization is still required.

## Why this matters

An AI-to-tool integration crosses a high-trust boundary. A weak implementation may accept free-form instructions, assume both sides support the same behavior, and execute immediately. The public protocol is designed to make those assumptions explicit and testable.

A safer integration pipeline is:

```text
transport/session input
    |
    v
parse + bounded resource checks
    |
    v
known schema + message-kind validation
    |
    v
wire-version compatibility
    |
    v
capability negotiation
    |
    v
authentication + authorization + local policy
    |
    v
approval when required
    |
    v
editor/tool-specific execution
    |
    v
post-condition validation + result/evidence
```

The reference consumer implements only the public protocol-facing portion of that flow. Authentication, authorization, sandboxing, editor permissions, credentials, transport security, and actual tool execution remain responsibilities of the integrating system.

## Capability names in the example

The example uses illustrative names such as `editor.read`, `editor.write`, and `result.evidence`. Capability identifiers are opaque public names governed by the capability profile; these example names do not expose or require any private Glomancy editor implementation.

The important behavior is:

- exact name + exact version matching;
- required capabilities fail closed when unsupported;
- optional unsupported capabilities may be omitted;
- task requests must stay inside the selected session capability set.

See `docs/CAPABILITY_NEGOTIATION.md` for the complete profile.

## Schema lookup

The example resolves `task.submit` through the public generated schema registry. Consumers should use the declared schema ID and known message kind rather than infer a contract from payload shape.

The registry contains the canonical schema identifier, schema version, relative path, and SHA-256 digest. The digest helps consumers that vendor schema files detect accidental drift.

## What this example deliberately does not do

It does not:

- connect to Unreal Engine or another editor;
- invoke model providers;
- execute filesystem, process, asset, Blueprint, or editor mutations;
- contain credentials, API keys, billing logic, or proprietary Glomancy runtime code;
- treat protocol validity as permission to execute.

Those concerns are intentionally outside this OSS protocol boundary.

## Extending the pattern

A real consumer can place these checks behind WebSocket, IPC, HTTP, named pipes, message queues, or another transport. The protocol does not require one transport.

After the protocol checks pass, the host implementation should independently authenticate the peer, authorize the requested operation, evaluate local risk policy, request approval when needed, execute inside its own safety boundary, validate post-conditions, and return structured progress/result/error/evidence messages.

For the full sequence, read `docs/INTEGRATION_GUIDE.md` and `docs/SECURITY_MODEL.md`.
