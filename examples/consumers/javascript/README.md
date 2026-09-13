# Independent JavaScript Consumer

This directory contains a dependency-free Node.js reference consumer for the public Glomancy Protocol contract.

It is intentionally independent from:

- the Rust crate;
- the Python repository validators;
- the private/commercial Glomancy runtime;
- any model provider, transport, or editor implementation.

The example loads the canonical public registry and language-neutral vectors under `vectors/v1/`, implements selected consumer decisions itself, and compares its results with the published expected outcomes.

## What it covers

`reference_consumer.mjs` independently implements:

- advertised wire-version selection;
- exact capability negotiation with required/optional semantics;
- task-time selected-capability gating;
- approval request/decision correlation and expiry handling.

It also verifies that the public registry exposes a valid wire version and registered message schemas.

## Run it

From the repository root:

```bash
node examples/consumers/javascript/reference_consumer.mjs
```

A successful run exits with code `0` and prints a short summary. Any disagreement with the published vectors exits non-zero.

No npm install, package manifest, or third-party dependency is required.

## Why this example exists

Having both Python and JavaScript examples helps demonstrate that the language-neutral vectors are useful outside the Rust implementation and repository validation tooling. Each example implements the same published decisions independently rather than delegating to another language.

## Not normative

This example is **not** a second specification. The public schemas, registry, compatibility/capability documentation, and versioned conformance vectors remain the contract.

Passing this example does not prove an integration is secure or authorize execution. Authentication, authorization, local policy, sandboxing, transport security, and editor/tool permissions remain responsibilities of the integrating system.
