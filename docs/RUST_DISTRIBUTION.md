# Rust distribution compatibility

Glomancy Protocol treats source-tree correctness and distributable-package correctness as separate concerns.

The repository therefore tests three Rust-facing boundaries:

1. the library and its normal repository tests;
2. a standalone downstream Rust consumer that imports only the public API;
3. the exact file surface and isolated verification performed by `cargo package`.

## Supported toolchain checks

The `Rust distribution compatibility` workflow runs the public crate and downstream consumer on:

- the documented minimum supported Rust version (MSRV), `1.85.0`;
- the current stable Rust toolchain available to GitHub Actions at workflow runtime.

The MSRV is part of the package metadata in `Cargo.toml`. Raising it should be an explicit compatibility decision rather than an accidental consequence of a new language or standard-library feature.

## Intentional Cargo package surface

`Cargo.toml` uses an explicit `include` list. The crate package contains the Rust source plus the public, language-neutral protocol contracts that define the same public boundary:

- schemas and registry metadata;
- compatibility snapshots;
- capability, error, security, limit, support, and fingerprint contracts;
- conformance-output schema;
- public valid/invalid examples and vectors;
- README and MIT license.

Repository administration, CI implementation, product screenshots, maintainer scripts, downstream smoke projects, and private/commercial Glomancy code are not part of the Cargo package surface.

`python3 scripts/validate_cargo_package.py <file-list>` validates the output of `cargo package --list` against this allowlist and fails closed on missing required files, unsafe paths, duplicate paths, or unexpected repository-only content.

## Isolated package verification

CI also runs:

```text
cargo package --allow-dirty
```

Cargo builds the package archive and verifies the packaged crate from the package context. This can catch cases where the source checkout works but the distributable package is incomplete or references files that were not packaged.

`--allow-dirty` is used only because CI is validating the current checked-out commit/worktree. It does not weaken the package content allowlist and does not publish anything.

## Publication boundary

The crate intentionally remains:

```toml
publish = false
```

These checks improve package readiness and downstream confidence. They do **not** publish to crates.io, reserve a crate name, sign the package, provide provenance, certify production readiness, or demonstrate external adoption.

Any future registry publication would require a separate, explicit maintainer decision and release review.
