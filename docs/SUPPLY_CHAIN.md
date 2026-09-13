# Supply-Chain Security

Glomancy Protocol keeps its public dependency surface intentionally small and treats build, test, and CI dependencies as part of the repository's security boundary.

This document describes the maintenance policy used for dependencies and GitHub Actions. It is a project policy, not a claim of formal certification.

## Principles

1. **Minimize dependencies.** Add a dependency only when it materially improves correctness, interoperability, security, or maintainability.
2. **Pin security-relevant automation.** Third-party GitHub Actions should be referenced by immutable commit SHA where practical, with the human-readable release line recorded in a comment.
3. **Review updates before merge.** Dependency-update pull requests receive the same CI and public-boundary checks as code changes.
4. **Keep runtime and tooling separate.** CI/conformance tooling dependencies must not silently become Rust runtime dependencies.
5. **No hidden private dependency.** The public package, schemas, fixtures, and conformance tooling must remain usable without the private commercial Glomancy repository.

## Current dependency surface

### Rust package

The Rust crate intentionally has no public runtime dependency section today. New Rust dependencies require a focused pull request that explains why the standard library or existing public code is insufficient.

A dependency proposal should consider:

- maintenance activity and ownership;
- license compatibility;
- transitive dependency growth;
- unsafe-code exposure where relevant;
- parsing/network/file-system attack surface;
- whether the dependency is required at runtime or only for development/tests.

### Python conformance tooling

The public conformance CLI uses a pinned direct dependency declared in `requirements-conformance.txt`. CI consumes the same declaration through `requirements-ci.txt` so local and CI behavior stay aligned.

Direct versions are pinned. Transitive Python packages are not currently hash-locked, so reviewers should treat changes to the direct validator dependency as security-relevant and inspect the resolved dependency changes shown by the package ecosystem before merge.

### GitHub Actions

Workflow actions are pinned to immutable commit SHAs rather than movable tags where practical. The release line is kept in an inline comment for readability.

When updating an Action:

1. confirm the commit belongs to the expected upstream repository/release;
2. review the update notes and permission changes;
3. keep workflow permissions least-privilege;
4. require the full CI suite to pass before merge.

## Automated update cadence

Dependabot monitors:

- GitHub Actions weekly;
- Cargo dependencies monthly;
- Python/pip dependencies monthly.

Dependabot is an update signal, not an auto-approval mechanism. A generated update pull request must still be reviewed and pass the repository checks.

## CI requirements for dependency changes

A dependency or workflow update should not merge unless all applicable checks are green, including:

- public/private boundary guard;
- repository integrity checks;
- executable JSON Schema conformance fixtures;
- public conformance CLI smoke tests;
- Rust formatting, Clippy, tests, example, and Rustdoc;
- Rust tests on Linux, Windows, and macOS.

## Credentials and provenance

The repository must not contain package-registry credentials, GitHub tokens, signing keys, API keys, private certificates, or private infrastructure configuration. CI uses GitHub-provided ephemeral credentials only where GitHub itself supplies them, with workflow permissions restricted to read-only contents for the current CI workflow.

Release signing or stronger provenance mechanisms may be added later, but this document does not claim that tagged releases are currently signed, SLSA-certified, or reproducible bit-for-bit.

## Reporting supply-chain concerns

Potential dependency confusion, compromised upstream releases, malicious package updates, workflow-action compromise, or credential exposure should be treated as security issues. Follow `SECURITY.md` rather than opening a public issue when disclosure could put users at risk.
