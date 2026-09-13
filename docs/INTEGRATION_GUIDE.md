# Consumer Integration Guide

This guide describes a language-neutral way to consume Glomancy Protocol. It focuses on protocol sequencing and trust boundaries rather than any specific transport, AI provider, editor, or commercial Glomancy implementation.

## 1. Integration boundary

Treat every inbound protocol message as untrusted input.

A safe consumer pipeline is:

```text
transport bytes
  -> transport size/rate limits
  -> parse JSON
  -> resolve schema ID
  -> validate schema + message kind
  -> check protocol compatibility
  -> authenticate the peer
  -> authorize the requested operation
  -> apply local policy / risk rules
  -> obtain explicit approval when required
  -> execute in the integration's own safety boundary
  -> validate post-conditions
  -> emit progress/result/error + evidence
```

**Important:** a schema-valid message is not automatically authorized to execute.

## 2. Handshake and version negotiation

Before task traffic, peers should exchange `handshake.request` and `handshake.response` messages.

A consumer should:

1. validate the handshake envelope against its registered schema;
2. reject an unknown schema ID or message kind;
3. compare supported wire protocol versions;
4. select the highest compatible common version when one exists;
5. reject the handshake when no compatible version exists;
6. record the selected version for the connection/session.

Current compatibility rules are defined by `compatibility/v1/compatibility-matrix.json` and explained in `docs/COMPATIBILITY.md`.

For the current pre-1.0 line, patch differences within the same minor version are compatible, while a different minor version is treated as incompatible.

## 3. Schema resolution

The registry under `registry/v1/manifest.json` is the canonical mapping between public schema identifiers and files.

Consumers should not guess a schema based on payload shape. Resolve the declared schema identifier, verify that it is known, and validate against that contract.

The registry also records SHA-256 digests for schema files. Implementations that vendor the schemas can use these values to detect accidental drift.

Unknown schema IDs should fail closed.

## 4. Task lifecycle

A typical task begins with `task.submit`.

The receiving implementation should validate the message first and then apply its own authentication, authorization, policy, and execution checks.

During work, the execution side can emit `task.progress`. Completion should result in `task.result`, while failures should use `task.error`. A requested or accepted cancellation uses `task.cancel` according to the integrating system's state machine.

A consumer should correlate lifecycle messages using the protocol identifiers and tracing fields rather than relying on arrival order alone.

## 5. Approval flow

High-risk operations may require an explicit approval boundary.

A recommended sequence is:

```text
task.submit
  -> local policy determines approval is required
  -> approval.request
  -> approval.decision
      -> approved: continue only if local authorization still permits execution
      -> denied: do not execute; return an appropriate task outcome
```

The protocol makes approval state explicit, but it does not define an organization's risk policy. Integrations decide which operations require approval and must enforce the decision locally.

Do not interpret the presence of an `approval.decision` message as proof of identity by itself. Authentication and authorization are integration responsibilities.

## 6. Evidence and results

`evidence.record` exists so an integration can attach structured evidence to work outcomes instead of relying only on an unverified textual claim.

Depending on the integration, evidence might reference a validation result, generated artifact, editor state observation, or another verifiable outcome. The protocol contract does not make the referenced artifact trustworthy automatically; the consumer still decides how evidence is stored and verified.

## 7. Errors and fail-closed behavior

Consumers should reject rather than reinterpret:

- unknown message kinds;
- unknown schema IDs;
- malformed identifiers;
- unsupported protocol versions;
- messages that violate the selected schema;
- inputs outside locally enforced protocol/resource limits.

Do not map unknown values to a permissive fallback such as "task.submit" or a generic approved state.

Use the public protocol error categories/codes where they apply, while keeping implementation-sensitive diagnostics out of untrusted responses.

## 8. Tracing and correlation

Protocol headers carry message IDs, sender-instance information, timestamps, trace IDs, and span IDs.

Use these fields to correlate events and build audit trails, but do not treat them as cryptographic authentication. A hostile sender can claim identifiers unless the transport/session identity is authenticated separately.

## 9. Complete happy-path example

A simplified successful flow looks like this:

```text
A -> B  handshake.request
B -> A  handshake.response  (compatible version selected)

A -> B  task.submit
B -> A  approval.request     (only when local policy requires it)
A -> B  approval.decision    (approved)
B -> A  task.progress
B -> A  evidence.record
B -> A  task.result
```

Some tasks will not require the approval messages. Some implementations may emit multiple progress/evidence records.

## 10. Rejection example

A safe incompatible-version path is:

```text
A -> B  handshake.request  (supports only an incompatible line)
B       validates the handshake
B       finds no compatible protocol version
B -> A  handshake rejection / unsupported-version outcome
B       does not accept task traffic for that incompatible session
```

The receiver should not silently choose a version outside the declared compatibility rules.

## 11. Minimal production checklist

Before accepting task execution in a real integration, verify that you have:

- [ ] transport-level size/rate limits;
- [ ] JSON parsing with bounded resource use;
- [ ] known-schema resolution and schema validation;
- [ ] fail-closed message-kind handling;
- [ ] explicit version negotiation;
- [ ] authenticated peer/session identity;
- [ ] authorization independent of schema validity;
- [ ] local risk/policy evaluation;
- [ ] enforceable approval gates for sensitive operations;
- [ ] editor/runtime-specific sandboxing and permission checks;
- [ ] post-condition validation;
- [ ] audit/evidence retention appropriate to your environment;
- [ ] safe handling of errors without leaking secrets.

## 12. What the protocol does not provide

Glomancy Protocol intentionally does not provide transport encryption, user authentication, authorization, credential storage, model-provider security, filesystem/process sandboxing, editor-specific permissions, or proof that an action is safe simply because its message validates.

Those controls belong to the integrating system.

## Related documents

- `docs/ARCHITECTURE.md` — protocol layers and design constraints
- `docs/COMPATIBILITY.md` — wire/schema version rules
- `docs/SECURITY_MODEL.md` — threats, properties, and integration responsibilities
- `SECURITY.md` — responsible vulnerability reporting
- `examples/v1/` — valid and invalid public fixtures
