# Public Resource Limits

Glomancy Protocol publishes bounded-input limits for message-processing surfaces that can otherwise create avoidable memory, CPU, or validation pressure in consuming integrations.

The canonical machine-readable contract is `limits/v1/policy.json`. The Rust API exports the same values from `src/policy.rs`, and repository CI checks the two surfaces for exact parity.

## Current public limits

| Limit | Value | Meaning |
| --- | ---: | --- |
| `message.max_bytes` | 1,048,576 bytes | Maximum encoded message size accepted by the public protocol policy. |
| `payload.max_depth` | 32 levels | Maximum payload nesting depth allowed by the public protocol policy. |
| `extensions.max_per_message` | 32 entries | Maximum extension entries associated with one message. |
| `artifacts.max_per_message` | 64 entries | Maximum artifacts associated with one message. |

These are protocol maximums, not resource-allocation recommendations.

## Consumer rule

An integration may enforce a **stricter** local limit when its deployment, editor, transport, sandbox, or workload requires it.

An integration must not silently accept values beyond the public maximum and still represent itself as enforcing this protocol policy. Inputs over a supported maximum should fail closed with an appropriate validation/policy error before expensive downstream work whenever practical.

## Units and counting

- `message.max_bytes` uses bytes of the encoded message presented to the protocol boundary. Integrations should define their transport framing clearly so this count is unambiguous.
- `payload.max_depth` counts structural nesting levels in the payload representation. Implementers should apply one stable counting method consistently across accepted input.
- extension and artifact limits count entries, not aggregate byte size. Message-size limits still apply to the whole encoded message.

The machine-readable policy includes a stable ID, matching Rust constant name, numeric value, unit, scope, and `maximum` enforcement direction for every public limit.

## Verification

Run:

```bash
python3 scripts/validate_resource_limits.py
```

The validator checks:

- policy and wire versions;
- the exact required public limit ID set;
- unique IDs and Rust-constant mappings;
- positive integer values;
- supported units, scopes, and enforcement direction;
- exact value parity with the public Rust constants;
- agreement with the Rust `PROTOCOL_VERSION`.

The policy is also part of `contracts/v1/fingerprint.json`, so a change to any public limit changes the deterministic aggregate contract fingerprint.

## Security boundary

Bounded inputs reduce one class of accidental or adversarial resource pressure, but these limits do **not** provide denial-of-service immunity. Integrations remain responsible for transport limits, request rate limits, authentication, authorization, concurrency control, timeouts, memory/process isolation, sandboxing, and editor/tool-specific protection.

The public policy does not prove that a private/commercial runtime enforces a limit unless that runtime independently demonstrates enforcement. It also does not replace schema validation or application-specific policy.

## Changing a limit

Changing a public maximum is a protocol-contract change and should be reviewed for:

- compatibility impact on existing consumers;
- security and resource-pressure consequences;
- migration requirements;
- conformance/vector coverage where applicable;
- public-contract fingerprint change;
- release-note and support-policy impact.

Use the protocol-change process in `docs/PROTOCOL_CHANGE_PROCESS.md` rather than changing the Rust constant or JSON policy independently.
