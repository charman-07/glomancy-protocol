# Downstream Rust Consumer Smoke Test

Glomancy Protocol includes a tiny standalone Rust crate under `downstream/rust-consumer/` that is compiled and executed in CI as a consumer-shaped compatibility check.

The downstream crate is deliberately separate from the root package workspace. It depends on `glomancy-protocol` only through the crate's public API and exercises representative consumer operations:

- reading the current public protocol version;
- resolving a registered schema by message kind;
- exact capability negotiation;
- task-time selected-capability gating;
- construction and validation of a public `MessageHeader`.

Run it from the repository root with Rust 1.85 or newer:

```bash
cargo run --manifest-path downstream/rust-consumer/Cargo.toml
```

## Why this exists

Unit tests inside the protocol crate can prove internal behavior while still missing consumer-facing problems such as an accidental export regression or an example that no longer compiles from another crate.

The downstream smoke test adds a second boundary: CI must compile and run a separate crate that imports Glomancy Protocol the same way a normal Rust project would import a dependency from a local checkout.

## What this proves

A passing test demonstrates that, for the tested revision:

- the representative public Rust symbols remain importable;
- the standalone consumer crate builds on the documented Rust 1.85 baseline;
- the exercised public APIs compose successfully from outside the root crate;
- the representative runtime assertions agree with the public protocol behavior.

## What this does not prove

This repository-maintained smoke test is **not** evidence of third-party adoption, production deployment, broad ecosystem usage, certification, API stability beyond the documented compatibility policy, or correctness of an external product's authorization/sandbox/editor integration.

Real external implementation feedback remains tracked separately through the integration-feedback path.
