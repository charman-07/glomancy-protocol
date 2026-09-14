# Contract Bundle Release Distribution

Glomancy Protocol provides a dedicated GitHub Actions workflow for distributing the deterministic standalone public contract bundle without requiring consumers to build the Rust crate.

This distribution path packages only the public contract surfaces already allowlisted by `scripts/build_contract_bundle.py`. It does not include the private Glomancy runtime, editor integrations, provider logic, credentials, signing material, billing logic, proprietary orchestration, or commercial implementation code.

## Candidate distribution

Maintainers can run **Contract distribution** manually from GitHub Actions and provide an exact branch, tag, or commit SHA.

The candidate job:

1. checks out the requested ref;
2. verifies the tracked public-contract fingerprint;
3. runs the deterministic bundle-generation validation;
4. builds a standalone ZIP;
5. verifies that exact ZIP with `scripts/verify_contract_bundle.py`;
6. writes a SHA-256 sidecar plus JSON build/verification metadata;
7. uploads the result as a 30-day GitHub Actions artifact.

Candidate artifacts are intentionally distinct from GitHub release assets. A successful candidate build does not publish a release and does not imply that all release-readiness gates passed. Maintainers should use it together with the separate **Release readiness** audit when preparing a release.

## Published release distribution

For releases published after this workflow exists in the relevant release line, the `release.published` event automatically runs the release-distribution job.

The job fails closed unless:

- the release tag is safe to use in a distribution filename;
- the checked-out commit exactly matches the release event SHA;
- the checked-out commit resolves exactly to the published tag;
- the public-contract fingerprint is current;
- deterministic bundle validation passes;
- the exact generated archive passes archive/manifest/checksum/fingerprint verification.

Only after those checks does the workflow attach release assets.

For a release tag such as `v0.2.0`, the assets are:

```text
glomancy-protocol-contracts-v0.2.0.zip
glomancy-protocol-contracts-v0.2.0.zip.sha256
```

The ZIP contains `BUNDLE_MANIFEST.json` and `SHA256SUMS` internally in addition to the public contract payload.

The sidecar checksum covers the entire ZIP file and is useful before extraction. The internal `SHA256SUMS` file covers the bundle payload and manifest after extraction.

## Verify a downloaded release bundle

On systems with `sha256sum`:

```bash
sha256sum -c glomancy-protocol-contracts-v0.2.0.zip.sha256
```

If you also have a checkout of the exact matching Glomancy Protocol tag, you can verify the full archive structure, embedded manifest, internal checksums, deterministic metadata rules, and public-contract fingerprint with:

```bash
python3 scripts/verify_contract_bundle.py glomancy-protocol-contracts-v0.2.0.zip
```

The verifier intentionally compares the archive's fingerprint with the checked-out source. Run it from the same tag/commit represented by the release bundle.

## Historical releases

Do not assume every historical GitHub release has contract-bundle assets.

In particular, a release created before this distribution workflow existed should not be retrofitted with a bundle built from newer source. Doing so would misrepresent the historical release contents.

When a historical release has no bundle asset, consumers can continue to pin that release/tag and build the deterministic bundle directly from its source if that tagged source contains the bundle tooling, or use the public contract files available in that release according to the documented adoption guidance.

## Permissions and publication boundary

The manual candidate job uses read-only repository contents access.

The automatic release job receives `contents: write` only because GitHub requires that permission to attach files to an already-published GitHub release. Release publication itself remains an explicit maintainer action; this workflow does not create a release or move a tag.

The workflow uses the existing repository bundle builder and verifier rather than maintaining a second packaging implementation.

## Assurance boundary

A deterministic archive and matching SHA-256 checksum provide useful integrity and reproducibility properties. They do **not** by themselves prove:

- publisher identity;
- code signing;
- SLSA provenance;
- security certification;
- formal verification;
- production fitness;
- authorization to execute AI-originated work;
- third-party adoption.

The project should only make stronger supply-chain or adoption claims when those properties are actually implemented and independently supportable.

See [Standalone Contract Bundle](CONTRACT_BUNDLE.md), [External Adoption Guide](ADOPTION_GUIDE.md), and the maintainer [Releasing](../RELEASING.md) checklist for the surrounding workflow.
