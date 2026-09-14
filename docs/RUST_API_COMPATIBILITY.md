# Public Rust API compatibility

Glomancy Protocol treats Rust API compatibility as a separate contract from wire-protocol compatibility, JSON Schema compatibility, and package-file integrity.

A crate can keep passing unit tests while still breaking a downstream Rust consumer by removing or changing a public type, method, field, trait implementation, or function signature. The repository therefore runs a dedicated SemVer compatibility check against the latest published public Rust baseline currently recorded for this project.

## Current baseline and development line

The current published baseline is the Git tag:

```text
v0.1.0
```

The current unreleased Rust package line is:

```text
0.2.0
```

This distinction is deliberate. After `v0.1.0`, the public exhaustive `HeaderValidationError` enum gained additional validation variants for incompatible protocol versions, unknown schema IDs, and schema-kind mismatches. Adding variants to an exhaustive public Rust enum can break downstream exhaustive matches, so the change is represented as a new pre-1.0 package minor line rather than being hidden inside `0.1.x`.

The wire protocol remains independently versioned; advancing the Rust crate to `0.2.0` does not by itself change the wire protocol version.

The check uses `cargo-semver-checks` with:

```bash
cargo semver-checks --baseline-rev v0.1.0
```

The crate intentionally remains `publish = false`, so the baseline is resolved from Git rather than crates.io.

## Supply-chain pin

The workflow does not install an unbounded latest tool from the network.

It currently pins:

```text
cargo-semver-checks v0.50.0
x86_64-unknown-linux-gnu archive SHA-256:
52a65dc88dc53fa8b57d6087954eb52cda149ca03bcfca78ce3fdecd23f893c4
```

CI downloads that exact upstream release archive, verifies the SHA-256 before extraction, and only then runs the tool. The tool version or digest should change only through an explicit repository update.

## What the check protects

The SemVer job is intended to catch many classes of accidental downstream Rust API breakage, including changes that normal repository tests may not exercise from a consumer perspective.

It complements, rather than replaces:

- the standalone downstream Rust consumer;
- MSRV/current-stable compatibility checks;
- the Cargo package-boundary check;
- executable rustdoc examples;
- wire-version compatibility rules;
- schema/registry hash checks;
- language-neutral conformance vectors.

## What it does not prove

No automated SemVer tool can prove behavioral compatibility for every possible consumer. This check is not:

- a formal proof that every downstream program will continue to work;
- a substitute for wire/schema compatibility review;
- a security certification;
- a promise that pre-1.0 APIs can never evolve;
- evidence of third-party adoption.

Before 1.0, intentional breaking Rust API changes may still be necessary. They should be explicit, versioned, documented, and reviewed rather than arriving accidentally.

## Updating the baseline

The baseline should move only after a new real public release is published and the repository's release/compatibility records have been updated consistently.

Do not point this workflow at an unreleased commit merely to make a failing SemVer check disappear. If a public API break is intentional, document the compatibility decision first and handle the release/version change explicitly.
