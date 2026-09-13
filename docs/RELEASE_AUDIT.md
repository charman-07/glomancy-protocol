# Release Readiness Audit

Glomancy Protocol includes a dedicated, manually triggered release-readiness workflow for auditing an exact branch, tag, or commit before a maintainer publishes a release.

## Purpose

Normal pull-request CI answers whether a proposed change satisfies the repository's day-to-day quality and contract checks. The release-readiness audit answers a narrower release-management question: whether one exact ref satisfies the public release gates and has internally consistent release-facing metadata.

The audit does **not** create a tag, publish a GitHub release, sign artifacts, produce provenance attestations, certify the project, or authorize a release automatically. Final release approval remains a maintainer decision under `RELEASING.md`, `GOVERNANCE.md`, and `docs/RELEASE_GATES.md`.

## Running the audit

Open GitHub Actions and run the **Release readiness** workflow manually.

Inputs:

- `ref` — branch, tag, or commit SHA to audit. Defaults to `main`.
- `expected_version` — optional Rust package release version, for example `0.2.0`. When supplied, the audit requires `Cargo.toml` and the changelog release heading to match it.

For a real release candidate, prefer auditing the exact commit SHA rather than a moving branch name after the candidate is frozen.

## Gates executed

The workflow independently checks:

1. Rust formatting, Clippy, tests, executable examples, and Rustdoc.
2. Public/private-boundary and repository-contract validation.
3. Schema-registry, Rust registry, wire-enum, error-catalog, capability-profile, consumer-vector, compatibility-snapshot, fixture, and CLI-output contracts.
4. Independent Python and JavaScript consumer examples.
5. Rust tests on Linux, Windows, and macOS.
6. Release-facing metadata consistency through `scripts/release_readiness_report.py`.

The final job succeeds only when all required quality, contract, and portability jobs succeed.

## Metadata report

The dependency-free report script records the audited public metadata surface, including:

- Rust package and minimum Rust version;
- current wire protocol version;
- public schema versions;
- capability-profile version;
- consumer-vector version;
- protocol error-catalog version;
- counts of registered schemas, vector areas, and public protocol error codes.

The report checks that every public surface that declares the current wire protocol agrees on the same version. It intentionally does not require the Rust package, schema, capability, vector, and catalog versions to be numerically identical because those contracts evolve independently.

## Interpreting a green audit

A successful audit is release-readiness evidence for the exact audited ref and SHA. It is not evidence of production adoption, security certification, formal verification, reproducible builds, signed-release provenance, or compatibility beyond the contracts actually tested by the repository.

The maintainer must still review release notes, compatibility and migration impact, security-sensitive changes, the public/private boundary, and the intended tag target before publication.
