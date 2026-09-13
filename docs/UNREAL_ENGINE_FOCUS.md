# Unreal Engine Product Focus

Glomancy is currently being developed primarily as an **AI-assisted copilot and automation layer for Unreal Engine**.

This document explains that concrete product context while keeping a clear boundary between the private commercial Glomancy implementation and the public, editor-agnostic Glomancy Protocol.

For a more technical view of how the public protocol can sit between an AI/planning layer and an Unreal editor integration, see [Unreal Engine Integration Boundary](UNREAL_INTEGRATION_BOUNDARY.md).

## Why Unreal Engine is the first product target

Unreal Engine is a useful proving ground for an AI-to-editor system because meaningful work often spans many kinds of project state at once: Actors, Components, Blueprints, assets, materials, animation systems, AI systems, C++ code, editor state, build/compile results, and validation output.

A useful assistant therefore has to do more than generate a text answer. It needs a disciplined way to understand context, describe intended work, check whether a capability exists, respect approval and policy boundaries, execute through supported editor integrations, detect failure, and verify the resulting state.

Those requirements are exactly the kind of boundary that Glomancy Protocol is intended to make explicit.

## What the broader Glomancy product is intended to do

The private Glomancy product is being built toward workflows in which a user can describe a desired Unreal Engine change in natural language and the system can participate in a structured process such as:

1. **Discover editor and project context.** Understand the active Unreal Engine project and the relevant editor state needed for the requested task.
2. **Interpret the request.** Convert natural-language intent into explicit, inspectable work rather than treating the model response itself as an editor command.
3. **Plan supported operations.** Decide which supported editor/tooling operations are needed and in what order.
4. **Check capabilities and policy.** Confirm that the connected integration supports the required behavior and that policy allows the operation.
5. **Request approval when appropriate.** Higher-risk or consequential changes can require explicit approval before execution.
6. **Execute through supported integrations.** Carry out supported Unreal/editor operations through explicit interfaces rather than relying on unstructured text-to-execution.
7. **Compile or validate where applicable.** Use the available editor/build/validation signals to determine whether the requested change actually succeeded.
8. **Recover from errors.** Surface structured failures and, where appropriate, support a plan/fix/verify loop.
9. **Return evidence.** Report status, results, errors, and evidence so a user can distinguish a verified outcome from an unsupported success claim.

## Example Unreal Engine workflow areas

The broader product direction includes supported workflows around areas such as:

- Actors and Components;
- Blueprint creation, editing, compilation, and validation;
- materials and asset-related editor operations;
- animation and Animation Blueprint workflows;
- AI-oriented editor systems such as behavior-related tooling;
- Sequencer/cinematic-oriented editor workflows;
- C++-backed editor operations and generated code where explicitly supported;
- project/editor context inspection;
- compile, validation, error, and evidence collection;
- safe plan/execute/verify loops around supported editor mutations.

These are product-direction categories, **not a claim that every possible Unreal Engine operation is already implemented or production-ready**. Public documentation should distinguish current protocol behavior from private product capabilities that are still evolving.

## Why this helps the public protocol

A protocol designed only in the abstract can miss constraints that appear in real editor automation. Unreal Engine provides concrete pressure around:

- long-running tasks;
- partial failure;
- compilation and validation;
- capabilities that differ between editor integrations;
- actions that may need approval;
- stateful project changes;
- cancellation and progress reporting;
- evidence that a requested change actually happened;
- compatibility between independently evolving components.

Using a real, complex editor as the first product target helps keep the protocol grounded in practical integration problems.

## Unreal-focused product, editor-agnostic protocol

The distinction is intentional:

| Private Glomancy product | Public Glomancy Protocol |
| --- | --- |
| Currently focused primarily on Unreal Engine | Not tied to Unreal Engine |
| Contains private editor-specific implementation | Contains transport-neutral contracts |
| May use Unreal-specific APIs and workflows | Uses generic task, capability, approval, result, error, and evidence semantics |
| Owns product UX, orchestration, policy, and execution | Defines the public boundary between components |
| Can evolve commercial implementation details privately | Can be implemented independently by outside projects |

An external implementation should be able to use the public protocol without using Glomancy's private Unreal Engine integration.

## What is deliberately not published here

This repository does not expose the private commercial implementation of Glomancy's Unreal Engine integration. In particular, the public protocol repository does not contain proprietary editor mutation code, private orchestration, provider credentials, billing logic, desktop application code, installer/signing infrastructure, or other commercial runtime details.

That separation lets the protocol remain inspectable and reusable without turning the commercial product into an open-source code dump.

## Relationship to safety

Unreal Engine can modify valuable project state, so a protocol message passing validation must never be treated as permission to execute a change.

A consuming implementation still needs its own authentication, authorization, policy, approval, sandboxing or isolation strategy, editor permissions, rollback/recovery decisions, and validation logic.

Glomancy Protocol contributes structure to that boundary; it does not replace those controls.

The [Unreal Engine Integration Boundary](UNREAL_INTEGRATION_BOUNDARY.md) document expands this into a concrete reference flow covering stale editor state, destructive asset mutations, Blueprint/C++ compile failures, partial multi-step changes, long-running operations, verification, and evidence.

## Project maturity

The public protocol is pre-1.0. The public repository was opened after underlying Glomancy/protocol work had already been under active development, testing, debugging, and repeated validation. The project should still be evaluated by what is publicly implemented and tested today, not by future product promises.

Real integrations, independent implementations, external review, and production feedback are expected to shape the protocol before stronger stability claims are made.

---

Unreal Engine is a trademark or registered trademark of Epic Games, Inc. This open-source protocol project is not presented as an official Epic Games project or endorsement.
