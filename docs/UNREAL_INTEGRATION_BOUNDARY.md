# Unreal Engine Integration Boundary

This document describes a **non-proprietary reference architecture** for applying Glomancy Protocol at an Unreal Engine editor boundary.

It is intentionally not a dump of the private commercial Glomancy runtime. It does not publish private editor-mutation commands, provider logic, orchestration internals, credentials, billing, installer code, or proprietary implementation details. The goal is to show how the public, editor-agnostic protocol can structure a real high-trust Unreal Engine workflow.

## Why this boundary matters

An AI-assisted Unreal workflow can affect valuable project state: levels, Actors, Components, Blueprints, assets, materials, animation systems, AI systems, Sequencer data, generated C++, build state, and source-controlled files.

That means four questions must remain separate:

1. **Is the message structurally valid?**
2. **Is the requested behavior supported and allowed?**
3. **Did the editor operation execute?**
4. **Did the requested project outcome actually become true?**

Glomancy Protocol helps make those stages explicit. It does not collapse them into a single "the AI said it worked" result.

## Reference flow

```text
User / developer request
        |
        v
AI / planning / orchestration layer
        |
        |  structured protocol message
        v
+--------------------------------------+
| Protocol boundary                    |
|                                      |
|  1. schema + identifier validation   |
|  2. wire-version negotiation         |
|  3. capability negotiation           |
|  4. task capability gate             |
|  5. policy / authorization checks    |
|  6. optional approval correlation    |
+--------------------------------------+
        |
        | accepted + authorized task
        v
Unreal integration / adapter
        |
        v
Supported Unreal Editor APIs / tools
        |
        +---- progress / cancellation ---->
        |
        v
Compile / validate / inspect resulting state
        |
        v
Result + error + evidence
        |
        v
User-visible verified outcome
```

The public protocol describes the contracts crossing the boundary. A consuming Unreal integration owns its editor API calls, permissions, transaction strategy, rollback/recovery choices, project-specific rules, and execution environment.

## Stage 1: validate the message

Before an Unreal integration considers executing anything, it should validate the protocol envelope and message against the registered public contract.

Typical checks include:

- known `schema_id`;
- known message kind;
- matching `schema_id` / kind mapping;
- valid identifiers and timestamps;
- bounded field sizes;
- expected wire version;
- required fields and enum values.

Unknown or malformed input should fail closed.

**Passing this stage does not authorize an Unreal change.** It only establishes that the input matches the expected protocol contract.

## Stage 2: negotiate supported behavior

Two installations may not expose the same editor operations. A lightweight Unreal adapter, a full editor plugin, a commandlet-oriented integration, and a future implementation can all have different capabilities.

The public protocol therefore separates message validity from capability support.

A consumer should determine whether required capabilities were explicitly selected for the session before accepting a task that depends on them. Unsupported required behavior should be rejected rather than approximated silently.

This matters in Unreal because the ability to inspect a project does not imply the ability to mutate it, compile Blueprints, change assets, touch C++, drive Sequencer, or perform another editor operation.

## Stage 3: apply product policy and authorization

Capability negotiation answers **"can this integration represent/support the behavior?"** It does not answer **"may this task execute here?"**

An Unreal consumer can still apply its own controls, for example:

- project or workspace access;
- read-only versus mutation permissions;
- source-control state;
- protected assets or paths;
- operation risk level;
- user/session identity;
- explicit allow/deny policy;
- sandbox or process isolation;
- resource/time budgets;
- editor mode or play-state restrictions.

These controls are implementation responsibilities outside the protocol's authorization scope.

## Stage 4: request approval for consequential work

Some Unreal operations can be consequential even when they are supported and authorized in principle. Examples include destructive asset changes, large multi-Actor edits, generated source changes, or operations with broad project impact.

The protocol's approval request/decision messages allow an implementation to represent an explicit approval gate.

A safe consumer should correlate an approval decision to the outstanding request and task, enforce expiry, and distinguish:

- valid approval;
- valid denial;
- expired decision;
- mismatched task/approval IDs;
- malformed decision.

A valid `approve` decision can satisfy an approval gate. It still does not bypass the consumer's other authorization, policy, capability, editor-permission, or safety checks.

## Stage 5: execute only through supported Unreal interfaces

After validation, capability checks, policy, and approval are satisfied, the Unreal adapter can translate the accepted task into its own supported editor/tool operations.

The private Glomancy implementation may evolve its own Unreal integrations. An independent consumer can use a completely different implementation while speaking the same public protocol at the boundary.

The key design constraint is that free-form model text should not automatically become unrestricted editor execution. The adapter should expose explicit operations with known inputs, outputs, limits, and failure behavior.

## Unreal-specific failure modes

### Stale editor state

A plan can become stale between inspection and execution. An Actor may be renamed or deleted, a Blueprint may change, the current level may switch, or source-control state may move.

A consumer should re-check critical assumptions close to execution time where practical and return a structured error instead of mutating the wrong target.

The protocol can carry task/error/result/evidence semantics, but freshness checks themselves remain an implementation responsibility.

### Destructive asset mutation

Deleting, renaming, overwriting, reparenting, or broadly editing assets can have cascading consequences.

A consumer may choose to require stronger authorization or explicit approval for such operations, use Unreal transaction/undo facilities where appropriate, create backups, or refuse operations that cannot be made acceptably safe.

The protocol provides an approval/result/error boundary; it does not promise rollback.

### Blueprint compile failure

A Blueprint edit can be syntactically representable yet leave the asset in a compile-error state.

A stronger workflow separates:

1. requested mutation;
2. editor operation result;
3. Blueprint compile/validation result;
4. final evidence returned to the user.

A mutation API returning success should not automatically be reported as a verified successful task if subsequent compilation fails.

### C++ build or hot-reload failure

Generated or modified C++ can fail to compile, can require a full editor restart, or can interact with build-system state.

An implementation should represent build failures explicitly and avoid treating file generation alone as proof that the requested Unreal behavior is now available.

### Partial multi-step changes

A task may involve several operations where some succeed and a later one fails.

The integration should define its own transactional or recovery strategy and report partial failure honestly. Depending on the operation, that may mean rollback, compensating actions, leaving the editor in a known partial state, or requiring manual review.

The public task/result/error/evidence contracts make it possible to report this distinction; they do not prescribe one universal rollback mechanism.

### Long-running editor operations

Asset scans, compilation, imports, builds, and larger editor operations can take time.

Progress and cancellation messages let an integration expose liveness rather than looking hung. The consumer still decides which Unreal operations are safely cancellable and what cancellation means after side effects have started.

### Editor mode and lifecycle state

An operation that is acceptable while idle may be unsafe or invalid while PIE, simulation, compilation, asset loading, or another editor lifecycle transition is in progress.

A production consumer should include editor-state checks in its local policy/execution layer.

## Verification is a separate stage

For an AI-to-editor system, **execution is not the same as verification**.

Possible Unreal verification signals include, depending on the supported workflow:

- target Actor/Component state after mutation;
- asset existence and metadata;
- Blueprint compile status;
- material or graph validation;
- C++ build result;
- generated diagnostic output;
- expected object/property values;
- editor-reported errors/warnings;
- produced artifact identifiers or hashes.

The protocol's result and evidence concepts allow an implementation to return structured proof references instead of only a natural-language success sentence.

Evidence should be truthful about what was actually checked. A successful API call is evidence of an API call, not automatically evidence that the complete user intent was achieved.

## Mapping public protocol concepts to an Unreal consumer

| Public protocol concept | Example role at an Unreal boundary |
| --- | --- |
| Handshake / wire version | Agree on the protocol line spoken by the planning side and Unreal consumer |
| Capability negotiation | Determine which categories of supported editor behavior are available for the session |
| `task.submit` | Carry structured work intent across the public boundary |
| `task.progress` | Report long-running editor/build/validation progress |
| `task.cancel` | Request cancellation where the local operation supports safe cancellation |
| `approval.request` / `approval.decision` | Represent explicit human/policy gates for consequential work |
| `task.result` | Report completion state and structured output |
| `task.error` | Report validation, policy, editor, compile, build, or execution failure without pretending success |
| `evidence.record` | Reference verifiable artifacts or validation observations associated with the result |
| Heartbeat | Expose liveness for a connected consumer/session |

This table is architectural guidance, not a definition of Unreal-only wire semantics.

## Example decision sequence

A conceptual Unreal consumer can treat an incoming task like this:

```text
receive task
  -> validate envelope/schema
  -> confirm negotiated wire version
  -> confirm task capabilities were selected
  -> resolve current project/editor target
  -> evaluate local policy/authorization
  -> require and correlate approval if policy says so
  -> re-check critical editor state
  -> execute one of the adapter's explicit supported operations
  -> collect progress/errors
  -> compile/validate/inspect resulting state where applicable
  -> emit result + evidence
```

At each arrow, failure should remain distinguishable from later-stage failure. A schema error, authorization denial, stale target, Unreal API failure, Blueprint compile error, and verification mismatch are not the same thing.

## Public/private boundary

This repository can safely document the integration architecture because the contract itself is intended to be public.

It deliberately does **not** publish:

- private Glomancy planner/orchestrator internals;
- proprietary Unreal mutation implementations;
- private provider/model routing;
- credentials or BYOK logic;
- billing/cost-control internals;
- desktop application internals;
- installer/updater/signing infrastructure;
- private project/customer data;
- internal operational evidence or machine-specific paths.

An outside project can therefore implement the public boundary without receiving the private commercial product source.

## Why Unreal is a strong proving ground

Unreal Engine makes protocol mistakes visible because it combines:

- large stateful projects;
- editor mutations with real side effects;
- code and visual scripting;
- compilation and validation;
- long-running operations;
- partial failure;
- user approvals and permissions;
- evidence that can be checked after execution.

That pressure helps keep Glomancy Protocol focused on real AI-to-tool integration problems rather than only abstract message design.

The protocol remains intentionally editor-agnostic. Unreal Engine is the first concrete product target and proving ground, not a requirement for adopting the public contract elsewhere.

## Related documentation

- [Unreal Engine Product Focus](UNREAL_ENGINE_FOCUS.md)
- [Glomancy Overview](GLOMANCY_OVERVIEW.md)
- [Architecture](ARCHITECTURE.md)
- [Security Model](SECURITY_MODEL.md)
- [Capability Negotiation](CAPABILITY_NEGOTIATION.md)
- [Consumer Integration Guide](INTEGRATION_GUIDE.md)
- [External Adoption Guide](ADOPTION_GUIDE.md)

---

Unreal Engine is a trademark or registered trademark of Epic Games, Inc. This open-source protocol project is not presented as an official Epic Games project or endorsement.
