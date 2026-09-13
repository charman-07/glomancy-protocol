# What Glomancy Is and Why the Protocol Exists

Glomancy is being built as an AI-assisted editor copilot and automation layer for complex creative and development tools. Its broader product goal is to let a person describe a change in natural language, have the system understand the surrounding project context, turn the request into a structured plan, apply appropriate safety and approval rules, carry out supported editor/tooling operations through explicit integrations, validate the result, and return evidence about what happened.

This repository is **not the commercial Glomancy product**. It is the public, transport-neutral protocol layer that defines the contracts between an AI-originated request and the tooling runtime that may eventually act on that request.

That separation is intentional.

The commercial product can evolve its private user experience, model/provider integrations, planning logic, editor-specific implementation, billing, credentials, orchestration, and proprietary automation while the public protocol remains small, inspectable, testable, and reusable by outside implementers.

## The short version

Think of the broader Glomancy product as the system that helps answer:

> "What change does the user want, how should it be planned, what is allowed, how should the editor perform it, and how do we verify the result?"

Think of Glomancy Protocol as the shared language that helps answer:

> "How do two components communicate that work safely, predictably, and in a way that can be validated?"

The protocol does not make an AI trustworthy by itself. It makes the boundary around AI-originated work **explicit** instead of ad hoc.

## What problem Glomancy is intended to solve

Modern editors and development tools are powerful, but many meaningful changes require a long chain of manual steps. A user may need to inspect project state, decide which objects or assets are affected, choose the right operation, make the change, compile or validate the result, handle errors, and confirm that the intended outcome actually happened.

AI can help with that workflow, but connecting an AI directly to a powerful editor creates a high-trust boundary. A free-form text model response should not automatically become an editor mutation.

A serious AI-to-editor system needs more structure:

- a clear representation of the work being requested;
- compatibility negotiation between components;
- explicit capabilities instead of assumed powers;
- limits on message size and structure;
- human or policy approval for higher-risk operations;
- deterministic error categories;
- progress and cancellation semantics;
- evidence that can be used to verify outcomes;
- tracing and observability;
- fail-closed handling for unknown or unsupported input;
- a way for independent implementations to test whether they follow the same contract.

Glomancy Protocol exists for that boundary.

## What the broader Glomancy product is intended to do

At a high level, Glomancy is intended to act as an in-editor AI copilot that can participate in a structured workflow such as:

1. **Understand the request.** A user describes a desired change in natural language.
2. **Read relevant context.** The product gathers only the project/editor context needed for the task.
3. **Plan the work.** The request is converted into explicit operations rather than treated as an unstructured chat answer.
4. **Check capabilities and policy.** The system determines whether the connected tooling supports the requested behavior and whether the action is allowed.
5. **Request approval when appropriate.** Higher-risk or consequential work can require explicit approval before execution.
6. **Execute through a supported integration.** The private product implementation talks to the editor/tooling runtime using structured operations.
7. **Validate the outcome.** The system checks whether the requested result was actually produced.
8. **Return evidence and status.** The user receives progress, errors, results, and verifiable evidence rather than only a claim that the task succeeded.

The exact private implementation of those steps is outside this repository.

## What Glomancy Protocol does today

The current public protocol provides a compact foundation for that workflow.

### Version negotiation

Peers can advertise and select supported protocol versions instead of silently assuming both sides understand the same wire behavior.

### Capability negotiation

The public capability profile defines exact, conservative negotiation semantics. Unsupported required capabilities fail closed; unsupported optional capabilities are omitted; task-time capability requests must be a subset of the selected session capabilities.

### Task lifecycle

The protocol defines messages for submitting work, reporting progress, returning a result, surfacing an error, and cancelling a task.

### Approval flow

Explicit approval request and decision messages allow an implementation to represent an approval gate instead of hiding that decision inside a private control path.

### Evidence

Result and evidence contracts make it possible to distinguish "the system says this happened" from "the system can reference evidence associated with the outcome."

### Errors

Public error categories and stable protocol error codes provide a common vocabulary for invalid requests, unsupported versions, schema failures, policy denial, approval requirements, execution failures, validation failures, timeouts, conflicts, cancellation, and internal failures.

### Observability

Message identifiers, sender metadata, trace identifiers, span identifiers, timestamps, and correlation fields make protocol activity easier to inspect and debug.

### Bounds and input discipline

The protocol defines limits and strict schemas so integrations do not need to treat arbitrary JSON as valid input.

### Conformance tooling

The repository includes executable validation tooling, valid and invalid fixtures, compatibility cases, a schema registry, and CI checks. An outside implementation can test its payloads without depending on the private Glomancy runtime.

## Why a protocol layer is useful

Without a protocol, an AI integration often becomes a collection of one-off JSON shapes, hidden assumptions, and product-specific callbacks. That can work during a prototype and become increasingly difficult to reason about as the system grows.

A public protocol creates a stable boundary.

### 1. Safety

The protocol encourages a fail-closed model. Unknown message kinds, invalid schemas, incompatible versions, unsupported required capabilities, and non-selected task capabilities should be rejected rather than guessed.

This does not replace authentication, authorization, policy, sandboxing, or approval. It gives those systems a predictable contract to work with.

### 2. Auditability

Structured messages make it easier to answer questions such as:

- What was requested?
- Which component sent it?
- Which capability was selected?
- Was approval required?
- What status was reported?
- What evidence was returned?
- Which error category occurred?
- Which protocol/schema version was involved?

That is much harder when everything is encoded in free-form text.

### 3. Interoperability

The protocol is transport-neutral and provider-neutral. It is not tied to one model vendor, one networking transport, one editor, or one private runtime implementation.

That means an external project can implement the same public contract without needing to reproduce the commercial Glomancy codebase.

### 4. Testability

Versioned JSON Schemas, a canonical registry, valid/invalid fixtures, Rust helpers, machine-readable capability cases, and the public conformance CLI allow behavior to be tested automatically.

A contract that can be executed in CI is more useful than a contract that exists only as prose.

### 5. Safer evolution

Explicit wire versions, schema IDs, registry hashes, compatibility rules, and release discipline make protocol changes visible. Consumers do not have to rely on undocumented assumptions when the public contract evolves.

### 6. Separation of concerns

The protocol deliberately separates **what must be communicated** from **how a private product implements it**.

That allows the OSS boundary to remain useful without publishing private provider logic, credentials, billing systems, proprietary orchestration, editor mutation code, desktop implementation, or signing infrastructure.

## Example workflow

A simplified transport-neutral flow can look like this:

```text
User request
    |
    v
AI / planning layer
    |
    |  structured request
    v
Policy + capability checks
    |
    |  Glomancy Protocol messages
    v
Editor / tooling integration
    |
    |  progress, result, error, evidence
    v
Validation / user-visible outcome
```

For a higher-risk task, an approval step can be inserted before execution:

```text
request -> plan -> capability check -> approval request
                                      |
                                      v
                                approval decision
                                      |
                                      v
                                  execution
                                      |
                                      v
                              validation + evidence
```

These diagrams describe roles, not the private architecture of the commercial product.

## Who can benefit from this public repository

### AI editor/tool developers

Teams building AI-assisted IDE, game-editor, CAD, DCC, automation, or developer-tool integrations can study or implement a small fail-closed message contract instead of inventing every boundary from scratch.

### Plugin and integration authors

An integration author can use the schemas, registry, compatibility rules, capability profile, and conformance fixtures to validate messages at the edge of a tool process.

### Security and platform engineers

The protocol provides explicit places for validation, policy denial, approval, bounded input, traceability, and evidence. That makes threat modeling and review more concrete.

### Test and infrastructure engineers

The public conformance CLI and fixtures can be placed in CI so an implementation can detect contract drift early.

### Researchers and open-source maintainers

The repository is a compact example of treating AI-originated tool actions as a typed protocol boundary rather than a direct text-to-execution channel.

## What this repository is not

This repository is intentionally **not**:

- a hosted AI service;
- a complete autonomous agent runtime;
- the Glomancy desktop/editor UI;
- a model-provider client;
- a credential or BYOK manager;
- a billing or cost-governor implementation;
- a proprietary planner or orchestration engine;
- an editor-specific mutation engine;
- an installer, updater, signing, or trust-distribution system;
- a promise that validation alone makes execution safe;
- a claim that the protocol is already a broadly adopted industry standard.

Those boundaries matter because the public project should remain honest about what it provides today.

## Product versus protocol

| Glomancy product | Glomancy Protocol |
| --- | --- |
| Broader commercial/private AI editor experience | Public OSS contract layer |
| Natural-language user workflow | Structured machine-readable messages |
| Private planning/orchestration implementation | Public task lifecycle semantics |
| Private editor integrations | Transport-neutral boundary contracts |
| Private provider/runtime choices | Provider-neutral schemas and types |
| Product policy and user experience | Approval/capability/error primitives |
| Commercial implementation details | MIT-licensed public protocol code |

The protocol can support the product, but the protocol is independently useful. The product can also evolve internally without requiring those private details to become part of the public standard.

## What "safe AI-to-editor" means here

The phrase does **not** mean that this repository guarantees safe execution.

It means the public contract is designed so an implementation can build a safer boundary with properties such as:

- validation before execution;
- explicit version compatibility;
- explicit capabilities;
- explicit approval state;
- bounded inputs;
- stable error handling;
- cancellation semantics;
- observable task progress;
- traceable messages;
- evidence-oriented results;
- rejection of unknown or unsupported protocol input.

Actual safety still depends on the consuming implementation, authorization model, policy layer, sandboxing, editor permissions, review process, and execution environment.

## Why open-source this part

A protocol becomes more useful when consumers can inspect it, test it, discuss it, implement it independently, and point to a versioned public contract.

Open-sourcing this layer provides several practical benefits:

- external integrations can validate against the same schemas;
- security assumptions can be reviewed publicly;
- compatibility behavior is visible rather than proprietary;
- conformance cases can be shared across implementations;
- contributors can improve edge cases, fixtures, documentation, and interoperability;
- the commercial product does not need to expose private runtime code in order to provide a public integration contract.

## Current maturity

Glomancy Protocol is pre-1.0 and newly public. The repository already contains executable CI, cross-platform Rust tests, JSON Schema validation, public/private boundary checks, capability-negotiation validation, registry hash checks, and a conformance CLI, but it should still be treated as an evolving protocol line.

Real integration feedback, independent implementations, external contributors, and production experience are still important before making stronger stability claims.

## Where to go next

- Start with the [README](../README.md).
- Read the [Integration Guide](INTEGRATION_GUIDE.md) for a consumer-oriented flow.
- Read [Protocol Conformance](CONFORMANCE.md) to validate payloads and fixtures.
- Read [Capability Negotiation](CAPABILITY_NEGOTIATION.md) for exact-match capability semantics.
- Read [Architecture](ARCHITECTURE.md), [Compatibility](COMPATIBILITY.md), and [Security Model](SECURITY_MODEL.md) for design rationale.
- Review [ROADMAP.md](../ROADMAP.md) for planned public work.

The public project should grow by making these contracts clearer, more testable, and more interoperable—not by leaking private product implementation details into the protocol.