# Standalone Contract Bundle

Glomancy Protocol can be consumed without the Rust crate. The repository provides a deterministic standalone bundle builder for non-Rust integrations that want to vendor or pin the public JSON contract surface as one verified package.

The bundle contains public protocol assets only. It does not include the private Glomancy runtime, editor integrations, provider logic, credentials, signing material, or proprietary implementation code.

## Build the bundle

From a pinned tag or commit:

```bash
python3 scripts/build_contract_bundle.py \
  --out-dir dist/glomancy-contracts \
  --archive dist/glomancy-protocol-contracts.zip \
  --json
```

The output directory contains the exact public assets plus:

- `BUNDLE_MANIFEST.json` — bundle format version, package/wire metadata, public-contract fingerprint, and per-file SHA-256/byte size;
- `SHA256SUMS` — SHA-256 for every payload file plus `BUNDLE_MANIFEST.json`.

The ZIP archive contains the same files with normalized timestamps and permissions.

## Determinism

The builder intentionally excludes clocks, machine paths, random values, filesystem mtimes, and environment-specific metadata from the archive.

For the same repository content, repeated builds must produce byte-identical ZIP bytes. Repository CI verifies this using:

```bash
python3 scripts/validate_contract_bundle.py
```

A deterministic archive helps a consumer compare a vendored contract package with another build of the same pinned source. It is an integrity property, not authenticity or provenance.

## Included public surfaces

The bundle includes:

- `schemas/v1/` — public Draft 2020-12 schemas;
- `registry/v1/` — canonical schema registry;
- `compatibility/v1/` and published snapshot JSON;
- `capabilities/v1/` — capability profile;
- `vectors/v1/` — language-neutral conformance vectors;
- `examples/v1/` — valid and intentionally invalid conformance fixtures plus their manifest;
- `errors/v1/` — public protocol error catalog;
- `security/v1/` — vector-backed security invariant catalog;
- `limits/v1/` — public resource-limit policy;
- `support/v1/` — release/security support policy;
- `contracts/v1/fingerprint.json` — deterministic public-contract fingerprint;
- `conformance/v1/` — machine-readable conformance-tool output contract;
- `LICENSE`.

The builder uses an explicit allowlist and rejects missing required contract surfaces, missing valid/invalid fixture sets, or unsafe archive paths.

## Verify the extracted bundle

Use an appropriate SHA-256 tool to verify `SHA256SUMS` after extraction.

On systems with `sha256sum`:

```bash
cd dist/glomancy-contracts
sha256sum -c SHA256SUMS
```

You can also compare `BUNDLE_MANIFEST.json` with the exact pinned source revision used to build the package.

## Verify an already-built ZIP

When you have the exact matching source checkout, the repository can verify a distributed archive directly:

```bash
python3 scripts/verify_contract_bundle.py dist/glomancy-protocol-contracts.zip
```

Machine-readable verification output is available with:

```bash
python3 scripts/verify_contract_bundle.py dist/glomancy-protocol-contracts.zip --json
```

The verifier checks archive structure, duplicate members, normalized timestamps/permissions, `BUNDLE_MANIFEST.json`, internal `SHA256SUMS`, payload byte sizes and SHA-256 values, and the public-contract fingerprint against the checked-out source.

Run this verifier from the same pinned tag/commit represented by the archive. A newer or different checkout is expected to fail when the public-contract fingerprint differs.

## Pin before vendoring

Do not generate a production dependency from a moving `main` branch and then assume it will remain unchanged.

Prefer:

1. a published release tag;
2. an exact reviewed commit SHA;
3. the bundle's public-contract fingerprint recorded alongside your integration.

See [External Adoption Guide](ADOPTION_GUIDE.md) for the broader pinning and upgrade process.

## Suggested non-Rust workflow

A non-Rust consumer can:

1. pin a Glomancy Protocol tag/commit;
2. obtain the published release bundle when that release provides one, or generate the standalone bundle from the pinned source;
3. verify the whole-ZIP SHA-256 sidecar when using a published release asset;
4. vendor the extracted public files into its repository or build system;
5. verify internal `SHA256SUMS` in CI;
6. implement behavior against the JSON Schemas and language-neutral vectors;
7. validate its parser/validator against the bundled valid and invalid fixtures;
8. run the public conformance CLI or its own independent vector runner;
9. review compatibility/release notes before updating the pinned baseline.

## Candidate and release distribution

The repository includes a dedicated **Contract distribution** GitHub Actions workflow.

In manual mode it can package an exact branch, tag, or commit SHA as a 30-day candidate artifact. This is useful for inspecting the exact deterministic ZIP that would be distributed, but it is not a published release and does not replace the separate Release Readiness quality audit.

For future GitHub releases, the release-published mode checks out the exact release tag, verifies the release event SHA/tag identity, validates the tracked fingerprint and deterministic bundle generation, verifies the exact generated ZIP, and then attaches:

```text
glomancy-protocol-contracts-<tag>.zip
glomancy-protocol-contracts-<tag>.zip.sha256
```

The release workflow does not create releases or move tags. Publication remains an explicit maintainer action.

Do not assume historical releases contain these assets. A release created before this workflow existed must not be retrofitted with a bundle built from newer source, because that would misrepresent the historical release contents.

See [Contract Bundle Release Distribution](RELEASE_DISTRIBUTION.md) for the complete publication, verification, permission, and historical-release rules.

## Assurance boundary

A matching checksum or byte-identical bundle does not prove:

- source/repository authenticity;
- publisher identity;
- SLSA provenance;
- code signing;
- security certification;
- authorization to execute AI-originated work;
- production adoption;
- correctness of a consumer's surrounding authentication, policy, sandbox, or editor permissions.

Use the bundle as a reproducible public-contract packaging mechanism, not as a replacement for a trusted distribution chain or security review.
