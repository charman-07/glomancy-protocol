<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/glomancy-mark-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/glomancy-mark-light.svg">
    <img alt="Glomancy" src="./assets/glomancy-mark-light.svg" width="110">
  </picture>
</p>

# Glomancy Protocol

[![CI](https://github.com/charman-07/glomancy-protocol/actions/workflows/ci.yml/badge.svg)](https://github.com/charman-07/glomancy-protocol/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust 1.85+](https://img.shields.io/badge/rust-1.85%2B-orange.svg)](rust-toolchain.toml)

**Transport-neutral, fail-closed protocol contracts for safe AI-to-editor integrations.**

Glomancy Protocol is a small Rust library plus versioned JSON Schemas for the boundary between AI systems and editor/tooling runtimes. It defines how integrations negotiate versions and capabilities, submit work, request approvals, report progress, return evidence, surface errors, and stay observable without coupling the protocol to one transport, model provider, or editor implementation.

> New here? Read **[What Glomancy Is and Why the Protocol Exists](docs/GLOMANCY_OVERVIEW.md)** for the product vision, concrete benefits, example workflows, intended audiences, current maturity, and the public/private boundary.
>
> Integrating it into another project? Read **[External Adoption Guide](docs/ADOPTION_GUIDE.md)** for release/commit pinning, Rust Git dependencies, schema/hash verification, non-Rust vendoring, conformance, and upgrade discipline.

## Glomancy in one minute

The broader **Glomancy product is currently being developed primarily for Unreal Engine** as an AI-assisted editor copilot and automation layer. Its high-level goal is to help turn a natural-language change request into a structured workflow: understand the active project/editor context, plan work, check capabilities and policy, request approval when appropriate, execute through supported Unreal/editor integrations, validate the result, and return status/evidence.

For Unreal Engine, the product direction includes assisting with supported editor workflows around project context, Actors and Components, Blueprints, materials, animation and AI systems, Sequencer-style workflows, and C++-backed editor operations as those integrations mature. The goal is not merely to generate text or code, but to make supported changes through explicit editor/tool interfaces and then verify what actually happened.

**Unreal Engine is the first concrete product target, not a limitation of the protocol.** Glomancy Protocol remains deliberately editor-agnostic, transport-neutral, and provider-neutral so the same public contract can be implemented by other editor/tool integrations without depending on the private commercial Glomancy runtime.

See [Unreal Engine Product Focus](docs/UNREAL_ENGINE_FOCUS.md) for the concrete product context and why Unreal Engine is a useful proving ground for this protocol design.

**Glomancy Protocol** is the public OSS contract layer for that boundary. It does not contain the commercial Glomancy runtime or editor implementation. Instead, it makes AI-originated work easier to validate, test, audit, negotiate, and integrate safely.

| Problem | Protocol response |
| --- | --- |
| Two components may support different versions | Explicit wire-version negotiation |
| A peer may not support a requested behavior | Exact, fail-closed capability negotiation |
| Free-form AI text is ambiguous | Typed, versioned message schemas |
| Higher-risk work may need review | Explicit approval request/decision messages |
| Long-running work needs status | Progress and cancellation semantics |
| "It worked" is not enough | Result and evidence contracts |
| Integrations drift over time | Registry hashes, compatibility rules, fixtures, snapshots, and CI |
| External tools need structured diagnostics | Versioned conformance CLI JSON output with a published JSON Schema contract |
| Unknown input can be dangerous | Conservative fail-closed validation |

## Why this exists

AI-assisted developer tools increasingly need to cross a high-trust boundary: an AI proposes work and another process may execute it. Ad-hoc JSON messages and direct text-to-tool execution make compatibility, auditing, approval gates, capability checks, and failure behavior difficult to reason about.

Glomancy Protocol makes that boundary explicit with:

- versioned handshake and compatibility rules;
- machine-readable capability negotiation with required/optional semantics;
- stable task lifecycle messages (`submit`, `progress`, `result`, `error`, `cancel`);
- explicit approval request/decision messages for risk-aware workflows;
- evidence records for verifiable outcomes;
- strict identifiers, trace/span metadata, and bounded protocol limits;
- a SHA-256-backed schema registry;
- fail-closed handling for unknown message kinds, schemas, incompatible versions, and unsupported required capabilities;
- valid and intentionally invalid fixtures for conformance testing;
- language-neutral consumer vectors for deterministic protocol decisions;
- published compatibility snapshots for released public contracts;
- a public conformance CLI with human-readable and versioned machine-readable JSON output;
- a Draft 2020-12 JSON Schema for the CLI JSON-output contract;
- executable Rust, independent Python, and independent JavaScript consumer examples.

## What benefit does it provide?

### Safer boundaries

Validation, compatibility, capabilities, approvals, and errors are explicit protocol concepts rather than hidden assumptions. The protocol does not replace authorization or sandboxing, but it gives those systems a predictable contract.

### Better auditability

Structured messages make it easier to answer what was requested, which component sent it, which version/capability was selected, whether approval was involved, what result was reported, and what evidence was returned.

### Interoperability

The public contract is transport-neutral and provider-neutral. An outside implementation can speak the protocol without adopting the private commercial Glomancy runtime. Language-neutral vectors and independently implemented Python and JavaScript examples demonstrate how the same published decisions can be consumed outside the Rust crate.

### Testability

Schemas, registry hashes, compatibility cases, capability cases, language-neutral vectors, published snapshots, Rust tests, valid/invalid fixtures, repository validators, the public conformance CLI, its JSON-output schema, and independent consumer examples can all run in CI.

### Safer evolution

Wire versions, schema IDs, compatibility rules, snapshot regression checks, changelog discipline, and conformance checks make contract changes visible instead of silently changing behavior underneath consumers. The [Pre-1.0 Deprecation and Schema Evolution Policy](docs/DEPRECATION_POLICY.md) defines how public contracts are proposed, deprecated, migrated, and removed while the project is still evolving.

## Example high-level flow

```text
User request
    |
    v
AI / planning layer
    |
    v
Policy + capability checks
    |
    |  Glomancy Protocol
    v
Editor / tooling integration
    |
    v
Progress / result / error / evidence
    |
    v
Validation and user-visible outcome
```

For consequential work, an implementation can insert an explicit approval step before execution. Passing protocol validation or capability negotiation is **not** authorization by itself.

## Quick start

Requirements: Rust 1.85 or newer. Python is used for the public repository/conformance tooling. Node.js is optional and is only needed for the independent JavaScript consumer example.

```bash
git clone https://github.com/charman-07/glomancy-protocol.git
cd glomancy-protocol
cargo test --all-targets
cargo run --example quick_start
cargo run --example reference_consumer
python3 scripts/validate_repository.py
```

`quick_start` shows basic version and message-kind handling. The Rust `reference_consumer` demonstrates a fuller consumer boundary: version compatibility, exact capability negotiation, task capability gating, schema resolution, fail-closed required-capability rejection, and the explicit fact that authorization is still required. See [Reference Consumer](docs/REFERENCE_CONSUMER.md) for the annotated walkthrough.

The repository validator checks JSON integrity, schema-registry hashes, fixture references, and protocol-version consistency.

For an integration that should survive repository changes, do **not** copy commands from mutable `main` without pinning a baseline first. See the [External Adoption Guide](docs/ADOPTION_GUIDE.md).

### Interoperability quick start

The repository also contains independent, dependency-free consumer examples that implement selected public decisions without importing the Rust crate or the repository vector validator:

```bash
python3 examples/consumers/python/reference_consumer.py
node examples/consumers/javascript/reference_consumer.mjs
```

Both consumers load the same public registry and `vectors/v1/` cases and independently exercise advertised-version selection, exact capability negotiation, task-time capability gating, and approval correlation/expiry behavior. CI runs both examples and fails if either disagrees with the published expected outcomes.

Run the language-neutral repository consistency suite directly with:

```bash
python3 scripts/validate_consumer_vectors.py
python3 scripts/validate_compatibility_snapshots.py
```

These maintained examples demonstrate implementability across languages; they are **not** claims of third-party adoption or production deployment.

### Validate protocol messages

Install the public conformance validator:

```bash
python3 -m pip install -r requirements-conformance.txt
```

Validate a message using its embedded `schema_id` / `kind`:

```bash
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json
```

Execute the entire public fixture corpus:

```bash
python3 scripts/glomancy_conformance.py fixtures
```

List the registered message schemas:

```bash
python3 scripts/glomancy_conformance.py list-schemas
```

For automation, add `--json`:

```bash
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json --json
python3 scripts/glomancy_conformance.py list-schemas --json
```

The JSON interface carries `output_version: "1.0.0"`. Its Draft 2020-12 machine-readable contract is published at [`conformance/v1/cli-output.schema.json`](conformance/v1/cli-output.schema.json), and repository CI checks representative real CLI outputs against it with:

```bash
python3 scripts/validate_cli_output_contract.py
```

See [Protocol Conformance](docs/CONFORMANCE.md) for exit codes, explicit schema selection, JSON-output fields, CI usage, and fail-closed expectations.

## Protocol surface

Current wire protocol: **0.4.0**. Initial public crate line: **0.1.x**.

The v1 schema set covers:

| Area | Message kinds / contract |
| --- | --- |
| Negotiation | `handshake.request`, `handshake.response`, capability profile |
| Task lifecycle | `task.submit`, `task.progress`, `task.result`, `task.error`, `task.cancel` |
| Human/policy approval | `approval.request`, `approval.decision` |
| Verification | `evidence.record` |
| Liveness | `heartbeat` |

See the [External Adoption Guide](docs/ADOPTION_GUIDE.md) for pinned consumption and upgrade guidance, the [Consumer Integration Guide](docs/INTEGRATION_GUIDE.md) for an end-to-end language-neutral flow, and [Consumer Conformance Vectors](docs/CONSUMER_VECTORS.md) for independent implementation guidance. [Capability Negotiation](docs/CAPABILITY_NEGOTIATION.md), [Protocol Conformance](docs/CONFORMANCE.md), [Architecture](docs/ARCHITECTURE.md), [Compatibility](docs/COMPATIBILITY.md), [Snapshot Compatibility](docs/SNAPSHOT_COMPATIBILITY.md), [Pre-1.0 Deprecation Policy](docs/DEPRECATION_POLICY.md), and [Security Model](docs/SECURITY_MODEL.md) document the executable contract, design rationale, evolution rules, and trust boundaries.

## Capability negotiation

The initial public capability profile intentionally starts conservative:

- matching is exact `name + version`;
- unsupported required capabilities reject the handshake;
- unsupported optional capabilities are omitted;
- duplicate capability names are rejected by the profile helper;
- a task may request only capability names selected for that session;
- capability negotiation never grants authorization by itself.

This behavior is backed by a machine-readable profile, conformance cases, Rust helpers/tests, language-neutral vectors, independent consumer examples, and CI validation.

## Security principles

Glomancy Protocol treats the message boundary as untrusted input.

1. **Fail closed.** Unknown kinds, unknown schemas, unsupported protocol combinations, and unsupported required capabilities are rejected.
2. **Validate before execution.** Protocol validation is a prerequisite, not authorization to perform an action.
3. **Keep policy explicit.** Risk level and approval state belong in explicit contracts rather than hidden implementation behavior.
4. **Preserve evidence.** Results can reference evidence so consumers can distinguish claims from verifiable artifacts.
5. **Bound inputs.** Public constants define message, nesting, extension, and artifact limits.
6. **Keep secrets out of the protocol.** Credentials and provider-specific authentication are out of scope.
7. **Keep capabilities narrow.** Negotiated support does not imply trust, permission, or successful execution.

For vulnerability reporting, read [SECURITY.md](SECURITY.md). Please do not disclose sensitive vulnerabilities in public issues.

## Product vs. protocol

| Broader Glomancy product | Glomancy Protocol |
| --- | --- |
| Commercial/private AI editor experience, currently focused primarily on Unreal Engine | Public MIT-licensed contract layer that remains editor-agnostic |
| Natural-language Unreal/editor workflow | Structured machine-readable messages |
| Private planning/orchestration implementation | Public task lifecycle semantics |
| Private Unreal/editor integrations and mutation implementations | Transport-neutral boundary contracts |
| Private model/provider/runtime choices | Provider-neutral schemas and types |
| Product policy and UX | Approval/capability/error primitives |

This repository intentionally contains **no provider credentials, billing logic, private agent runtime, desktop application, proprietary planner/orchestrator, Unreal Engine mutation implementation, installer/updater, or signing infrastructure**.

## Who is this for?

- Unreal Engine plugin/editor-tooling developers interested in structured AI-to-editor boundaries;
- AI editor/tool developers building structured AI-to-tool boundaries in other environments;
- plugin and integration authors that need versioned schemas and compatibility rules;
- security/platform engineers reviewing validation, approval, capability, and evidence flows;
- test/infrastructure engineers that want executable conformance in CI;
- researchers and OSS maintainers exploring typed alternatives to direct text-to-execution pipelines.

The protocol is not presented as a broadly adopted industry standard today. It is a pre-1.0 public project intended to become more useful through real integrations, independent implementations, review, and feedback.

## Repository layout

```text
src/                         Rust protocol types and validation helpers
schemas/v1/                  Wire-message JSON Schema contracts
registry/v1/                 Canonical schema registry and SHA-256 metadata
conformance/v1/              Versioned contracts for public conformance tooling output
vectors/v1/                  Language-neutral expected-outcome vectors
examples/                    Runnable Rust examples plus public protocol fixtures
examples/v1/                 Valid and invalid protocol fixtures
examples/consumers/python/   Independent dependency-free Python consumer
examples/consumers/javascript/ Independent dependency-free JavaScript consumer
compatibility/v1/            Version compatibility rules and cases
compatibility/snapshots/     Pinned real public-release compatibility baselines
capabilities/v1/             Machine-readable capability profile and cases
docs/                        Product context, adoption, architecture, conformance, compatibility, evolution, security, integration guides
scripts/                     Repository integrity, boundary, interoperability, fixture, and conformance tools
tests/                       Public contract regression tests
.github/                     CI and contribution / feedback workflow templates
```

## Compatibility and versioning

Before 1.0, a patch change within the same protocol minor line is compatible; a different minor line is treated as incompatible. At 1.0 and later, versions with the same major version are considered protocol-compatible. Exact rules and negotiation behavior live in `compatibility/v1/compatibility-matrix.json` and are documented in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

Schema versions and wire-protocol versions are separate on purpose: a schema can evolve independently while negotiation remains explicit. CLI JSON-output versions and consumer-vector versions are separate again. Changes that deprecate or remove public behavior must follow [docs/DEPRECATION_POLICY.md](docs/DEPRECATION_POLICY.md) rather than silently mutating the contract.

## Project status

This public repository is newly open-sourced, but the underlying protocol work had already been under active development, testing, debugging, and repeated validation before the public repository was opened. The current public focus is a small, auditable protocol core with executable conformance behavior rather than a large framework.

The broader private Glomancy product is being developed with Unreal Engine as its first primary editor target. That concrete product work gives the protocol a real high-trust editor environment to design against, while the public protocol intentionally avoids depending on Unreal-specific implementation details.

The repository includes cross-platform Rust tests, JSON Schema validation, public/private boundary checks, capability-negotiation validation, language-neutral expected-outcome vectors, independent Python and JavaScript consumer examples, published compatibility snapshots, registry hash checks, supply-chain maintenance rules, a public conformance CLI, versioned machine-readable CLI output, and a published schema for that output. It is still pre-1.0; **genuine external integration feedback and independent usage remain important before stronger stability or adoption claims are appropriate.**

If you have actually implemented or evaluated the public protocol independently, use the dedicated [Integration feedback issue form](https://github.com/charman-07/glomancy-protocol/issues/new?template=integration_feedback.yml). Maintainer-derived implementation notes live separately in [Integration Pitfalls and Implementation Notes](docs/INTEGRATION_PITFALLS.md); the project does not treat those notes as external adoption evidence.

Planned work is tracked in [ROADMAP.md](ROADMAP.md) and GitHub Issues. Roadmap items are direction, not promises or fabricated adoption claims.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before opening a pull request. Good first contributions include additional fixtures, validation tests, documentation, interoperability examples, and edge cases that remain inside the public protocol boundary.

If you built an independent consumer, proof of concept, editor/tool integration, or conformance implementation, genuine test results are also useful through the [Integration feedback issue form](https://github.com/charman-07/glomancy-protocol/issues/new?template=integration_feedback.yml). Do not include credentials, customer data, private source code, or sensitive infrastructure details.

Project decisions and maintainer responsibilities are described in [GOVERNANCE.md](GOVERNANCE.md). Support guidance is in [SUPPORT.md](SUPPORT.md).

## Release discipline

Every release should pass formatting, Clippy, tests, documentation checks, cross-platform test jobs, repository integrity validation, capability-profile validation, independent consumer examples, compatibility-snapshot checks, executable examples, and executable conformance checks. Public deprecations/removals must also carry explicit migration notes under [docs/DEPRECATION_POLICY.md](docs/DEPRECATION_POLICY.md). The release checklist is documented in [RELEASING.md](RELEASING.md), and notable changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## License

Glomancy Protocol is licensed under the [MIT License](LICENSE).

The separate commercial Glomancy product and its private implementation are **not** licensed under this repository's MIT license.
