# Contributing

Thanks for your interest in improving Glomancy Protocol. The project welcomes focused contributions that make the public protocol safer, clearer, more interoperable, or easier to test.

Please read `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, and `MAINTAINERS.md` before making a large proposal.

## Scope

Good contributions include:

- validation and compatibility tests;
- valid and invalid protocol fixtures;
- JSON Schema improvements;
- language-neutral conformance vectors;
- transport-neutral integration examples;
- documentation and migration guidance;
- repository tooling that verifies public protocol invariants.

Out of scope:

- proprietary Glomancy Desktop/runtime code;
- model-provider implementations or credentials;
- billing/cost-governor logic;
- private infrastructure or signing systems;
- editor-specific mutation implementations that do not belong in a neutral protocol contract.

## Security and privacy rules

Never include API keys, access tokens, credentials, private certificates, signing material, customer data, private project names, machine-specific private paths, or proprietary source code.

Do not open a public issue or pull request for an exploitable security vulnerability. Follow `SECURITY.md` instead.

## Choose the right change path

Before coding, classify the change using `docs/PROTOCOL_CHANGE_PROCESS.md`.

- **Class 0 — editorial / non-contract:** a normal pull request is sufficient.
- **Class 1 — additive compatible:** open an issue when a public contract surface is affected and explain why existing consumers remain compatible.
- **Class 2 — behavioral / compatibility-sensitive:** open a Protocol change proposal before implementation.
- **Class 3 — breaking or security-sensitive:** open a Protocol change proposal unless the details require private security coordination under `SECURITY.md`.

Examples of changes that normally need a proposal include changes to wire behavior, schema identity, compatibility rules, capability negotiation, approval semantics, evidence requirements, task lifecycle rules, public limits, error contracts, or unknown-input behavior.

A proposal should cover compatibility, migration, security, conformance evidence, alternatives, and release/versioning impact before the implementation PR changes the contract.

## Local verification

Use Rust 1.85 or newer and run:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps
cargo run --example quick_start
python3 scripts/validate_repository.py
```

For schema/fixture or integration changes, also install and run the public conformance tooling:

```bash
python3 -m pip install -r requirements-conformance.txt
python3 scripts/glomancy_conformance.py fixtures
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json
```

Depending on the area changed, run the relevant repository-contract validators as well, including registry parity, wire-enum parity, protocol error-catalog parity, capability/vector checks, compatibility snapshots, and CLI output-contract validation.

See `docs/CONFORMANCE.md` for schema selection, exit codes, CI integration, and fail-closed expectations.

CI repeats these checks and also runs Rust tests on Linux, Windows, and macOS.

## Tests and executable evidence

Observable protocol behavior should be backed by a test, fixture, vector, parity validator, or equivalent executable evidence.

If a schema changes, update the registry hash intentionally and explain compatibility impact. If compatibility behavior changes, keep the matrix, cases, Rust behavior, vectors, and documentation consistent.

Prefer targeted negative tests for malformed or ambiguous input. Unknown protocol input should remain fail-closed unless a reviewed protocol proposal explicitly changes that behavior.

Every entry in `examples/v1/manifest.json` is executable conformance evidence. Valid fixtures must pass their declared schemas. Invalid fixtures must fail for their declared `expected_keyword`; do not add an invalid fixture that only happens to fail for an unrelated reason.

## Pull requests

Keep pull requests focused. Complete the pull-request template, especially the compatibility, security, verification, and public-boundary sections.

For a proposal-driven change, link the accepted proposal issue and ensure the implementation still matches the reviewed design. If the implementation materially changes the proposal, update the issue before merge.

A pull request should be mergeable only when:

- CI is green;
- tests/fixtures/vectors cover changed behavior;
- machine-readable contracts and code remain consistent;
- compatibility and migration impact are documented;
- public documentation is consistent;
- no private/commercial implementation details leaked into the OSS boundary.

## Commit and review quality

Use descriptive commit messages and explain *why* a contract changes, not only what lines changed. Review discussions should stay technical and evidence-driven.

Do not manufacture activity, contributors, adoption, stars, forks, benchmark results, or production claims. Genuine external feedback is more valuable than artificial project signals.

## Release-sensitive changes

Changes intended for a release should consider the gates in `docs/RELEASE_GATES.md` and the checklist in `RELEASING.md` before merge. Version numbers for the Rust crate, wire protocol, schemas, catalogs, and conformance vectors are intentionally independent.

## Good first contributions

Good starter work includes additional boundary fixtures, documentation clarifications, test coverage for public helpers, compatibility cases, and small transport-neutral examples.

Issue #60 (independent Go consumer) is an example of the kind of focused external contribution the project wants to make approachable.
