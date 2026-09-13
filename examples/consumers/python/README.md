# Independent Python Consumer

This directory contains a dependency-free Python reference consumer for the public Glomancy Protocol contract.

It is intentionally independent from:

- the Rust crate;
- `scripts/validate_consumer_vectors.py`;
- the private/commercial Glomancy runtime;
- any model provider, transport, or editor implementation.

The example loads the canonical public registry and the language-neutral vectors under `vectors/v1/`, implements selected consumer decisions itself, and compares its results with the published expected outcomes.

## What it covers

`reference_consumer.py` independently implements:

- advertised wire-version selection;
- exact capability negotiation with required/optional semantics;
- task-time selected-capability gating;
- approval request/decision correlation and expiry handling.

It also checks that the public registry exposes a valid wire version and registered message schemas.

## Run it

From the repository root:

```bash
python3 examples/consumers/python/reference_consumer.py
```

A successful run exits with code `0` and prints a short summary. Any disagreement with the published vectors exits non-zero.

No third-party packages are required.

## Why this example exists

The repository's Rust tests and Python repository validators prove that the source repository is internally consistent. This example checks something different: whether a small consumer written independently in another language can implement the documented decisions and arrive at the same published outcomes.

That makes it useful as an interoperability example and as a starting point for external implementations.

## Not normative

The Python example is **not** a second normative specification. The public schemas, registry, compatibility/capability documentation, and versioned conformance vectors remain the contract.

If this example and the public vectors disagree, treat that as a bug to investigate rather than silently copying the example's behavior.

Passing the example also does not grant authorization to execute work. Authentication, authorization, policy, sandboxing, transport security, and editor/tool permissions remain responsibilities of the integrating system.
