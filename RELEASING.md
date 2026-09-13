# Releasing

This checklist keeps public releases deliberate, auditable, and aligned with the project’s compatibility/security promises.

Read [`docs/RELEASE_GATES.md`](docs/RELEASE_GATES.md) before preparing a release. The gates define the expected quality evidence; this file defines the maintainer workflow.

## 1. Establish the release candidate

1. Select the exact `main` commit intended for release.
2. Confirm the corresponding GitHub Actions run is green.
3. Confirm there are no unresolved known blockers for the release scope.
4. Freeze the intended release candidate while final review is performed; avoid merging unrelated follow-up work into the tag target.

## 2. Verify version metadata

Confirm the intended versions are internally consistent across their own contract surfaces:

- Rust package version in `Cargo.toml`;
- current wire version in Rust and the canonical registry/compatibility data;
- JSON Schema versions/IDs and registry hashes;
- capability-profile version when changed;
- consumer-vector version when changed;
- machine-readable catalog versions when changed.

These version numbers are intentionally independent. Do not bump them mechanically as one bundle.

## 3. Run the release-readiness audit

The preferred pre-tag verification path is the manually triggered **Release readiness** GitHub Actions workflow.

From the repository Actions UI:

1. choose **Release readiness**;
2. run the workflow;
3. set `ref` to the exact branch, tag, or commit SHA being audited;
4. optionally set `expected_version` (for example `0.2.0`) to require `Cargo.toml` and the CHANGELOG release heading to match that version;
5. wait for Rust quality, repository-contract, and Linux/Windows/macOS portability gates to complete;
6. review the generated workflow summary and audited commit SHA before tagging.

The workflow is read-only. It does **not** create a tag, publish a GitHub release, sign artifacts, certify the build, or grant permission to release.

The audit includes a dependency-free metadata report that verifies consistency among the Rust package, Rust `PROTOCOL_VERSION`, canonical registry, capability profile, consumer vectors, error catalog, and public schema-version set.

### Local/manual equivalent

When reproducing the release audit locally, run at minimum:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps
cargo run --example quick_start
cargo run --example reference_consumer
python3 scripts/validate_repository.py
python3 scripts/validate_rust_registry.py
python3 scripts/validate_wire_enums.py
python3 scripts/validate_error_catalog.py
python3 scripts/release_readiness_report.py --json
python3 scripts/validate_capability_profile.py
python3 scripts/validate_consumer_vectors.py
python3 scripts/validate_compatibility_snapshots.py
python3 -m pip install -r requirements-conformance.txt
python3 scripts/validate_fixtures.py
python3 scripts/glomancy_conformance.py fixtures
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json
python3 scripts/validate_cli_output_contract.py
```

Also verify the independent language examples that are part of repository CI.

GitHub Actions remains the canonical cross-platform evidence for Linux, Windows, and macOS.

## 4. Review changes since the previous release

Review every public-contract change for:

- wire compatibility impact;
- schema identifier/version/hash changes;
- capability negotiation changes;
- approval/task-lifecycle/evidence semantics;
- new or changed error codes/categories;
- public limits and malformed-input behavior;
- conformance-vector expectations;
- deprecations/removals;
- security/trust-boundary implications;
- dependency and GitHub Actions changes;
- private/public boundary risk.

For proposal-driven changes, confirm the implementation still matches the accepted public decision or that the proposal issue was updated before merge.

## 5. Supply-chain and public-boundary review

Review `docs/SUPPLY_CHAIN.md` and confirm dependency/Action changes were intentional and passed the applicable CI suite.

Confirm no credentials, private certificates, customer data, signing material, proprietary runtime/provider/billing/editor-mutation code, or sensitive private infrastructure details entered the public history.

## 6. Changelog and release notes

Update `CHANGELOG.md` and prepare release notes that clearly describe:

- user-visible changes;
- compatibility impact;
- migration steps;
- security-relevant behavior changes when safe to disclose;
- maturity/status wording supported by evidence.

Do not describe a release as stable, production-proven, certified, broadly adopted, signed, reproducible, or supply-chain verified unless those properties are actually implemented and demonstrable for that release.

## 7. Tag and GitHub release

Prefer an annotated semantic-version tag such as `v0.2.0` when creating tags through Git tooling. If a GitHub UI workflow creates a lightweight tag instead, record that truthfully rather than claiming the tag is annotated.

The tag must resolve to the reviewed release-candidate commit.

Publish the GitHub release only after the tag target and release notes have been reviewed.

## 8. Post-release verification

After publication:

- verify the tag resolves to the intended commit;
- verify the GitHub release is published with the intended draft/prerelease state;
- verify CI for the tagged commit;
- verify README/documentation links from the tagged source;
- verify key examples and the public conformance CLI against the tagged source;
- verify source/archive links;
- add a compatibility snapshot for the real release when required by the compatibility-snapshot policy;
- open follow-up issues for deferred work rather than silently changing a published historical contract.

## Security releases

For a sensitive vulnerability, coordinate disclosure through `SECURITY.md`. Do not expose exploit details before affected users have a reasonable opportunity to update.

Security urgency may require a shorter public review window, but it does not remove the need for regression tests, compatibility/migration analysis, and accurate release notes once disclosure is safe.

## Repository enforcement

Process compliance and GitHub technical enforcement are distinct. Required checks, pull-request-only changes, force-push blocking, and deletion protection should be configured through repository rules/branch protection when verified administrative access is available.

Do not claim those controls are enforced until they are actually visible in repository settings.
