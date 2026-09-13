# Capability Negotiation Profile

Status: **Accepted design for the initial public profile; wire-schema changes are intentionally deferred to a follow-up change.**

This document defines the initial transport-neutral rules for advertising and selecting optional capabilities in Glomancy Protocol. It is deliberately conservative: unknown or unsupported required capabilities fail closed, and the profile does not turn capability advertisement into authorization.

## Goals

The profile should let two implementations answer four questions deterministically:

1. What optional protocol-visible behaviors does the initiator advertise?
2. Which advertised behaviors are mandatory for the session to be useful?
3. Which behaviors does the responder actually select?
4. Can a later task request a behavior that was not selected during the handshake?

The answer to the fourth question is **no**.

## Non-goals

Capability negotiation does not:

- grant permission to execute an action;
- replace authentication, policy, approval, or risk checks;
- expose provider credentials, billing state, desktop internals, private tool names, or implementation classes;
- weaken wire-version negotiation;
- infer support from a similar-looking capability name;
- treat unknown capabilities as implicitly supported.

## Existing wire fields

The current public schemas already expose:

- `handshake.request.payload.capabilities`: capability objects with `name`, `version`, and optional `required`;
- `handshake.response.payload.selected_capabilities`: the selected capability objects;
- `task.submit.payload.requested_capabilities`: capability names requested by one task.

This profile defines the semantics of those fields before any structural wire change is considered.

## Capability identifier rules

A capability identifier remains a lowercase dotted/hyphenated token matching the existing public pattern:

```text
^[a-z][a-z0-9.-]*$
```

Identifiers describe **publicly observable behavior**, not private implementation structure.

Good examples:

```text
asset.read
asset.metadata
approval.explicit
result.evidence
```

Poor examples:

```text
my-private-class-v2
provider-secret-mode
billing-enterprise-bypass
internal.desktop.rpc42
```

A capability name alone never implies access to a credential, customer resource, private filesystem location, or privileged mutation path.

## Versioning rule for profile v1

Capability versions use semantic-version strings, but the initial negotiation profile intentionally supports only **exact name + exact version** matching.

For profile v1:

```text
local.name == remote.name
AND
local.version == remote.version
```

is required for a match.

Why exact matching first:

- the wire currently advertises one version per capability object rather than a version range;
- synthesizing a version that neither side explicitly advertised would be ambiguous;
- using ordinary SemVer compatibility without a declared feature contract could silently widen behavior;
- exact matching is easy to test and fail closed.

A later profile may introduce explicit ranges or capability-version compatibility rules, but that requires a new public design decision rather than implicit interpretation.

## Negotiation order

Implementations MUST negotiate the wire protocol before negotiating optional capabilities.

Recommended order:

1. determine whether the two sides have a compatible wire protocol version;
2. if no compatible wire version exists, reject the handshake;
3. evaluate the initiator's advertised capabilities against the responder's local public capability set;
4. reject if any capability marked `required: true` lacks an exact local match;
5. include exact matches in `selected_capabilities`;
6. omit unsupported optional capabilities;
7. apply the negotiated message-size limit;
8. only then accept the session.

Capability negotiation MUST NOT make an otherwise incompatible wire version acceptable.

## Required versus optional capabilities

In the current request/response handshake shape, `required` is meaningful on capabilities advertised by the handshake initiator.

If an initiator advertises:

```json
{
  "name": "result.evidence",
  "version": "1.0.0",
  "required": true
}
```

and the responder does not have an exact `result.evidence@1.0.0` match, the handshake must be rejected.

If the same capability is optional (`required` omitted or `false`), the responder omits it from `selected_capabilities` and may still accept the handshake.

The current wire shape does not provide a separate responder-requirements list. Implementations must not overload `selected_capabilities[].required` to invent that behavior. Symmetric requirement negotiation would require a future explicit schema/profile change.

## Selected capabilities

`handshake.response.payload.selected_capabilities` is the exact intersection chosen by the responder under this profile.

Each selected entry must correspond to an identical `name` + `version` pair advertised by the initiator and supported locally by the responder.

A responder must not:

- invent an unadvertised capability;
- change the capability version;
- select an unsupported capability because its name shares a prefix with a supported one;
- silently substitute a provider/editor-specific implementation for a different public capability.

## Task-time enforcement

A task's `requested_capabilities` is a set of capability **names**. Every requested name must have been selected during the session handshake.

For example, if the selected session set is:

```json
[
  {"name": "asset.read", "version": "1.0.0"},
  {"name": "result.evidence", "version": "1.0.0"}
]
```

then this task request is allowed to proceed to the next policy layer:

```json
{
  "requested_capabilities": ["asset.read"]
}
```

while this request must fail closed before execution:

```json
{
  "requested_capabilities": ["asset.write"]
}
```

because `asset.write` was not selected.

Passing this check still does **not** authorize the task. Authentication, risk ceilings, approval requirements, product policy, and execution validation remain separate gates.

## Deterministic algorithm

Given:

- `remote`: the initiator's capability advertisements;
- `local`: the responder's supported public capabilities;

profile v1 uses the following algorithm:

```text
selected = []

for each capability R in remote:
    L = exact local entry where L.name == R.name and L.version == R.version

    if L exists:
        append R.name + R.version to selected
    else if R.required == true:
        reject handshake as unsupported required capability
    else:
        omit R

accept capability negotiation with selected
```

Duplicate capability objects remain invalid at the schema layer where `uniqueItems` applies. Implementations should also avoid advertising the same name with multiple versions in profile v1 because the initial profile intentionally has no version-range negotiation semantics.

## Error behavior

A failed required capability should surface as a normal public protocol rejection rather than a transport error or private implementation exception.

The rejection should communicate, without leaking private internals:

- that a required capability is unsupported;
- the public capability name and requested version when safe;
- that retry is only useful if capability requirements or the peer implementation change.

The profile does not reserve a new error code in this design-only change. A follow-up implementation should reuse or extend public error codes explicitly and test the choice before changing wire behavior.

## Security implications

Capability negotiation is a declaration of supported behavior, not a grant of trust.

Implementations must assume:

- a peer may falsely advertise capabilities;
- a negotiated capability may still be denied by policy;
- a task may attempt to request a capability that was never negotiated;
- similarly named capabilities may have different semantics;
- unknown capability names are untrusted input.

Fail-closed requirements:

- unsupported required capability -> reject handshake;
- unsupported optional capability -> omit;
- task requests non-selected capability -> reject task before execution;
- malformed capability identifier/version -> schema validation failure;
- wire-version incompatibility -> reject before capability negotiation.

## Compatibility implications

This profile does not change wire protocol `0.4.0` by itself. It specifies conservative semantics for fields that already exist.

Any future structural schema change must:

- receive its own schema/version compatibility analysis;
- update fixtures and registry hashes intentionally;
- preserve or explicitly supersede these fail-closed semantics;
- document migration behavior for existing `0.4.x` consumers.

## Public/private boundary

Core protocol documentation may define generic capability semantics, but it must not publish private Glomancy runtime architecture simply to explain how a capability is implemented.

A public capability may describe **what is observable**. Private code decides **how it is implemented**.

For example, `asset.read` can describe a public read capability without documenting private editor bridges, provider routing, proprietary agent orchestration, billing logic, or credential handling.

## Follow-up implementation plan

After this design is accepted, the implementation phase should add:

1. a machine-readable profile describing exact-match and fail-closed rules;
2. positive and negative negotiation fixtures;
3. Rust helpers/tests for exact matching and required-capability failure;
4. task-time selected-capability subset tests;
5. conformance validation for the machine-readable profile;
6. documentation links from compatibility/security guidance.

The implementation phase should avoid changing handshake schemas unless tests demonstrate that the existing fields are insufficient.
