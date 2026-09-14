# Evaluate Glomancy Protocol in 5 minutes

This page is for developers who want to answer one question quickly: **is Glomancy Protocol relevant to my AI-to-editor or AI-to-tool integration?**

You do not need the private Glomancy product, Unreal Engine, a model-provider account, or any credentials to evaluate the public protocol.

## 1. Clone and run the public checks

Requirements:

- Rust 1.85 or newer;
- Python 3;
- Node.js only if you want to run the independent JavaScript consumer.

```bash
git clone https://github.com/charman-07/glomancy-protocol.git
cd glomancy-protocol
cargo test --all-targets
cargo run --example quick_start
```

Expected outcome: the Rust tests pass and the quick-start example prints valid protocol/version information without contacting a remote service.

## 2. Run an independent consumer

The repository includes implementations that make selected public decisions without importing the Rust crate:

```bash
python3 examples/consumers/python/reference_consumer.py
node examples/consumers/javascript/reference_consumer.mjs
```

These examples read the same public registry and language-neutral vectors and independently exercise version selection, capability negotiation, task-time capability gating, and approval correlation/expiry behavior.

Expected outcome: each consumer exits successfully only when its implementation agrees with the published expected outcomes.

## 3. Validate a real protocol message

Install the public conformance dependency:

```bash
python3 -m pip install -r requirements-conformance.txt
```

Then validate a known-good task submission:

```bash
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json
```

Try a known-bad message:

```bash
python3 scripts/glomancy_conformance.py validate examples/v1/invalid/bad-message-id-format.json
```

The invalid payload should fail with the documented non-zero exit code rather than being accepted permissively.

## 4. Inspect the public contracts

If the project is relevant to your integration, the most useful public surfaces are:

- `registry/v1/manifest.json` — canonical schema registry;
- `schemas/v1/` — Draft 2020-12 message schemas;
- `capabilities/v1/profile.json` — capability-negotiation contract;
- `vectors/v1/` — language-neutral expected-outcome vectors;
- `security/v1/invariants.json` — vector-backed fail-closed security expectations;
- `limits/v1/policy.json` — machine-readable bounded-input limits;
- `errors/v1/catalog.json` — public protocol error codes;
- `compatibility/` — wire compatibility and published snapshots.

## 5. Decide how you want to use it

### Rust consumer

Read [External Adoption Guide](ADOPTION_GUIDE.md) for a pinned Git dependency and release/commit verification guidance.

### Non-Rust consumer

Vendor or pin the public JSON contracts and implement the same decisions in your language. Use the language-neutral vectors and conformance CLI as executable compatibility checks.

### Unreal Engine / editor tooling

Read [Unreal Engine Product Focus](UNREAL_ENGINE_FOCUS.md) and [Unreal Integration Boundary](UNREAL_INTEGRATION_BOUNDARY.md) for the first concrete product context. The public protocol itself remains editor-agnostic.

## If something is unclear

Use the repository's **Integration question** issue form for a concrete technical question, or the **Integration feedback** form if you actually implemented or evaluated the protocol independently.

If you want to contribute rather than integrate, continue with [Contributor Start Here](CONTRIBUTOR_START_HERE.md).

## What this evaluation does not prove

A passing local evaluation does not mean an integration is authorized, production-ready, certified, formally verified, secure against every threat, or endorsed by the Glomancy project. Protocol validation is only one layer of a larger authentication, authorization, policy, sandboxing, and editor/tool-permission boundary.
