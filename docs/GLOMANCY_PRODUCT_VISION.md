# Glomancy — AI-Native Development Intelligence for Unreal Engine

<p align="center">
  <img src="../assets/glomancy-desktop-preview.webp" alt="Glomancy Desktop connected to an Unreal Engine project" width="100%">
</p>

> **Development preview:** Glomancy Desktop connected to an active Unreal Engine project, with the Bridge authenticated and the AI provider ready. The screenshot represents a real development build; the product remains under active development and its current surface does not represent the full planned system.

Glomancy is being developed as an AI-native desktop development environment for Unreal Engine.

Its goal is not to become another chat window that happens to know programming terminology. The longer-term direction is substantially broader: Glomancy is intended to understand an Unreal project as a connected technical system, reason about the relationships inside that system, plan work across multiple development surfaces, perform supported operations through explicit editor integrations, and verify what actually happened.

The ambition is straightforward:

**Glomancy should not merely tell a developer how to work in Unreal Engine. It should increasingly understand the project well enough to work with the developer inside Unreal Engine.**

## More than a command assistant

A real game-development problem rarely belongs to one file, one Blueprint, or one node.

A character that behaves incorrectly can involve input, a Player Controller, a Character Blueprint, a C++ base class, Components, an Animation Blueprint, a State Machine, a Montage, an Anim Notify, gameplay state, or another system entirely.

An AI that only looks at the currently open asset can miss the real cause.

Glomancy is therefore being designed around a deeper question:

**Why is the system behaving this way?**

And then a second question that matters just as much:

**If this changes, what else can it affect?**

That distinction is central to the product direction. Glomancy is not intended to stop at “find a line and edit it.” The target workflow is closer to:

**understand the project → trace the system → identify the cause → evaluate impact → plan the change → execute supported work → validate the result → preserve evidence**

## Understanding the project as a system

As the product develops, Glomancy is intended to build progressively richer context around the active Unreal project.

That context is not limited to filenames. The system is being developed toward understanding relationships such as:

- Blueprint parent/child structures;
- Blueprint Interfaces and cross-Blueprint communication;
- Actor and Component relationships;
- C++ and Blueprint boundaries;
- event, function, variable, and dependency flows;
- Animation Blueprints and State Machines;
- Montages and Anim Notifies;
- Behavior Trees and Blackboards;
- gameplay AI systems;
- materials and material instances;
- level Actors and scene relationships;
- Sequencer-oriented workflows;
- asset dependencies;
- compile, editor, and runtime state where supported.

These areas should not be treated as isolated features. The real value comes from connecting them.

A Blueprint problem may actually originate in C++. An animation failure may be caused by gameplay timing. A Behavior Tree may be correct while the Blackboard value feeding it is wrong. A base Blueprint change may affect a large inheritance tree.

Glomancy's direction is to reason across those boundaries rather than treating each tool surface as a separate chat topic.

## Deep technical reasoning

A meaningful request to Glomancy should be able to describe the outcome, not every mechanical step required to reach it.

For example:

> “The enemy detects the player in some situations but does not transition into pursuit. Inspect the relevant AI flow, identify the root cause, preserve the existing architecture where possible, and verify the result.”

The useful response to that request is not simply “open the Behavior Tree.”

A capable system may need to inspect the AI Controller, Pawn, Perception configuration, Blackboard values, Behavior Tree transitions, Blueprint events, relevant C++ code, and the live editor/runtime state before it can explain the failure with confidence.

Another example:

> “The combat system has become difficult to maintain as the Blueprint grew. Analyze its current responsibilities, identify the safest separation boundaries, plan a refactor that preserves behavior, and verify that input, animation, damage, and dependent systems still work afterward.”

That is not a node-generation task. It is an engineering task.

The product is being developed toward handling increasingly complex requests in that form: understanding the intent, gathering the right context, constructing a plan, applying supported changes, and evaluating the consequences.

## Technical project memory

Large Unreal projects contain more than code and assets. They also contain history.

Developers need to remember questions such as:

- Why was this system implemented this way?
- Why should this Blueprint not be modified casually?
- Which workaround was added for a previous issue?
- Which architectural decision affects this feature?
- Has this failure happened before?
- Which constraints must remain true after a change?

One of Glomancy's longer-term directions is to retain and retrieve more useful project context over time so that the developer does not have to repeatedly reconstruct the same technical background from scratch.

The goal is not passive note storage. The useful form of project memory is context that can participate in future reasoning: prior technical decisions, project rules, known risks, important constraints, previous failures, planned work, and verified outcomes.

Over time, this can make Glomancy less like a temporary assistant and more like a persistent technical memory for the project.

## Impact-aware changes

Professional development is not difficult only because changes are hard to make. It is difficult because a change can affect systems far away from the place where it was made.

Glomancy is being designed toward impact-aware work.

If a base Blueprint changes, derived Blueprints may need to be considered.

If a C++ interface changes, Blueprint consumers may need review.

If an Anim Notify is removed or renamed, gameplay code waiting for that event may need to be traced.

If a Blackboard key changes, Behavior Tree nodes and supporting logic may need to be checked.

If an asset dependency changes, downstream content can become invalid even when the edited asset itself looks correct.

The direction is therefore not merely to perform modifications, but to reason about their likely blast radius before and after execution.

## Plan. Execute. Verify.

Glomancy is not being designed around uncontrolled direct execution.

For non-trivial work, the intended high-level pattern is:

**collect context → understand the problem → form a plan → check capabilities and policy → request approval when appropriate → execute supported operations → validate post-conditions → return result and evidence**

A single Unreal task can require several distinct stages.

For example:

**Blueprint change → compile → dependent asset check → PIE/runtime validation → observation → final verification**

The value of an integrated system is that the developer should not need to manually coordinate every low-level step when Glomancy has enough context and supported tooling to manage the workflow safely.

This is also why evidence matters. Glomancy is designed around the principle that it should not fabricate Bridge state, provider state, compile success, PIE success, editor state, or visual success when that result has not been verified.

The system should distinguish between:

- what was requested;
- what was planned;
- what was attempted;
- what actually changed;
- what was verified;
- what remains uncertain.

## A force multiplier for game developers

The long-term role of Glomancy is not to replace the game developer.

It is to expand what one developer can understand and accomplish without losing control of the project.

Game development contains a large amount of cognitive and operational overhead: tracing dependencies, navigating Blueprints, following event chains, checking inheritance, investigating compile failures, repeating editor operations, correlating runtime behavior with project structure, and remembering why systems were built the way they were.

Glomancy is being developed to absorb more of that burden while leaving creative and technical authority with the developer.

The intended destination is not a passive assistant sitting beside Unreal Engine.

It is a system that can become a **technical co-pilot for the entire development environment** — one that understands context, follows relationships, helps reason through architecture, performs supported work, and reports the result with evidence.

A useful way to describe the ambition is:

**Glomancy is being built to become a second technical mind inside an Unreal project.**

## Unreal Engine is the first proving ground

Glomancy is currently being developed primarily for Unreal Engine.

Unreal is not simply a visual demo target. It is the first serious proving ground for the product because it combines many forms of development context in one environment: C++, Blueprints, assets, animation, AI, materials, levels, editor state, runtime state, and complex dependency relationships.

That makes Unreal an effective environment for testing whether an AI system can move beyond code generation and reason about real development workflows.

The broader product direction includes progressively richer support across Unreal-oriented areas such as project context, Actors and Components, Blueprints, materials, animation systems, gameplay AI, Sequencer-style workflows, C++-backed editor operations, validation, and other supported editor surfaces as those integrations mature.

These are development directions, not a claim that every possible Unreal operation is already available in the current build.

## Current development state

The current Glomancy Desktop development build already demonstrates several pieces of the intended architecture working together:

- detection of the active Unreal Engine project and engine version;
- a live Desktop ↔ Unreal Bridge connection;
- authenticated Bridge state;
- an initialized AI-provider session;
- natural-language task input;
- supported Unreal/editor operation paths;
- task/evidence-oriented product surfaces;
- a verification-first product philosophy.

The current UI and capability set should be understood as one development stage of a much larger system.

Glomancy remains under active development.

## Where the product is going

The roadmap is not primarily about adding a longer list of buttons.

The larger objective is to increase the depth of understanding and the amount of useful context Glomancy can connect at once.

Future development is aimed at progressively improving areas such as:

- deeper project-wide context;
- richer dependency and relationship understanding;
- broader Unreal Editor connectivity;
- stronger multi-step planning and execution;
- more capable verification and evidence workflows;
- safer handling of consequential changes;
- better continuity across development sessions;
- wider automation coverage while preserving explicit boundaries and user control.

The internal implementation will continue to evolve, but the product principle is stable: more automation should come with more context, more verification, and clearer boundaries — not with less visibility into what the AI actually did.

## Product and protocol

The public **Glomancy Protocol** repository is the open contract layer for this broader product direction.

The private commercial Glomancy implementation contains product/runtime behavior that is intentionally not published here. The protocol remains editor-agnostic, transport-neutral, and provider-neutral so that its validation, capability, approval, lifecycle, evidence, and interoperability contracts can be evaluated independently of the private product.

Unreal Engine is the first concrete product target, while Glomancy Protocol is intentionally designed so that the public contract itself is not restricted to Unreal Engine.

That separation is deliberate: the public project can remain auditable and reusable without exposing proprietary editor automation, runtime, provider, orchestration, credential, billing, or other commercial implementation details.

---

## The product thesis

A conventional AI assistant can explain Unreal Engine.

Glomancy is being built toward something more demanding:

> **The developer states the outcome. Glomancy understands the project, investigates the system, connects the relevant context, plans the work, performs supported changes, verifies the result, and shows the evidence.**

**The goal is not to build an AI that merely uses Unreal Engine. The goal is to build an AI system that increasingly understands Unreal Engine development itself.**
