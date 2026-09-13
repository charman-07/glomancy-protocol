# Release Readiness Audit

Glomancy Protocol includes a dedicated, manually triggered release-readiness workflow for auditing an exact branch, tag, or commit before a maintainer publishes a release.

## Purpose

Normal pull-request CI answers whether a proposed change satisfies the repository's day-to-day quality and contract checks. The release-readiness audit answers a narrower release-management question: whether one exact ref satisfies the public release gates and has internally consistent release-facing metadata.

The audit does **not** create a tag, publish a GitHub release, sign artifacts, produce provenance attestations, certify the project, formally verify security properties, or authorize a release automatically. Final release approval remains a maintainer decision under `RELEASING.md`, `GOVERNANCE.md`, and `docs/RELEASE_GATES.md`.

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
3. Schema-registry, Rust registry, wire-enum, error-catalog, security-invariant, resource-limit, release-support, public-contract-fingerprint, capability-profile, consumer-vector, compatibility-snapshot, fixture, CLI-output, and release-evidence contracts.
4. Independent Python and JavaScript consumer examples.
5. Rust tests on Linux, Windows, and macOS.
6. Release-facing metadata consistency through `scripts/release_readiness_report.py`.

The security-invariant gate checks that each `GLM-SEC-*` record is structurally valid, agrees with the current wire version, and references existing executable vector cases. This provides regression evidence for documented fail-closed behavior; it is not formal verification of the protocol or consuming integrations.

The resource-limit gate checks that every required public maximum is present, uses a supported unit/scope, agrees with the current wire version, and exactly matches the exported Rust constant. This provides contract parity for bounded inputs; it does not prove denial-of-service immunity or higher-layer runtime enforcement.

The final job succeeds only when all required quality, contract, and portability jobs succeed.

## Metadata report

The dependency-free report script records the audited public metadata surface, including:

- Rust package and minimum Rust version;
- current wire protocol version;
- public schema versions;
- capability-profile version;
- consumer-vector version;
- protocol error-catalog version;
- security-invariant catalog version and invariant count;
- resource-limits policy version and public-limit count;
- release-support policy version and supported published release lines;
- deterministic public-contract aggregate SHA-256;
- counts of registered schemas, vector areas, public protocol error codes, security invariants, resource limits, and supported release lines.

The report checks that every public surface that declares the current wire protocol agrees on the same version. It intentionally does not require the Rust package, schema, capability, vector, error-catalog, security-invariant, resource-limits, support-policy, and fingerprint format versions to be numerically identical because those contracts evolve independently.

## Downloadable release evidence bundle

The summary job generates a `release-evidence-<run-id>-<attempt>` GitHub Actions artifact for the exact audited ref. The artifact is retained for 30 days and contains:

- `evidence.json` — the versioned machine-readable audit record;
- `public-contract-fingerprint.json` — a byte-identical copy of the tracked canonical contract fingerprint from the audited ref;
- `release-support-policy.json` — a byte-identical copy of the tracked public release-support policy from the audited ref;
- `SHA256SUMS` — SHA-256 checksums for the three payload files above.

`evidence.json` records the audited ref/SHA, package and wire versions, aggregate public-contract fingerprint, support-policy version/current published lines, and the Rust-quality, repository-contract, and portability gate outcomes. Security-invariant and resource-limit changes are captured indirectly by the public-contract fingerprint and directly in the release-readiness metadata report. If a required gate fails, the evidence record uses `audit_status: "failed"`; the workflow still attempts to upload the bundle so a failed audit remains diagnosable.

The evidence payload is governed by `evidence/v1/release-evidence.schema.json`. Repository CI generates both passing and failing sample bundles, validates them against that Draft 2020-12 schema, verifies that copied contract files are byte-identical to their tracked sources, and checks `SHA256SUMS`.

### Verify a downloaded bundle

After downloading and extracting the artifact, verify the payload checksums with an appropriate SHA-256 tool. On systems with `sha256sum`:

```bash
cd release-evidence
sha256sum -c SHA256SUMS
```

On other platforms, calculate SHA-256 for each listed file and compare it with `SHA256SUMS`.

The checksum file intentionally covers the bundle payload files and does not recursively hash itself.

## Security and trust boundary

The evidence bundle is **integrity and audit metadata only**. It is not:

- a digital signature;
- proof of artifact or publisher authenticity;
- SLSA provenance;
- a cryptographic attestation;
- a security certification;
- formal verification;
- denial-of-service immunity;
- a release-authorization decision;
- proof of production adoption.

A consumer must establish repository/ref authenticity through its own trusted source before treating the recorded SHA-256 values as meaningful. The bundle does not replace code review, branch protection, signed tags/releases, or any future provenance mechanism.

## Interpreting a green audit

A successful audit is release-readiness evidence for the exact audited ref and SHA. It is not evidence of production adoption, security certification, formal verification, denial-of-service resistance, reproducible builds, signed-release provenance, or compatibility beyond the contracts actually tested by the repository.

The maintainer must still review release notes, compatibility and migration impact, security-sensitive changes, the public/private boundary, the security-invariant catalog, resource-limits policy, the evidence bundle, and the intended tag target before publication.
