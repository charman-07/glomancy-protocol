# Contributing

Thanks for your interest in improving Glomancy Protocol. The project welcomes focused contributions that make the public protocol safer, clearer, more interoperable, or easier to test.

Please read `CODE_OF_CONDUCT.md` and `GOVERNANCE.md` before making a large proposal.

## Scope

Good contributions include:

- validation and compatibility tests;
- valid and invalid protocol fixtures;
- JSON Schema improvements;
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

## Before coding

For a small bug or documentation fix, a pull request is fine.

For a change to wire behavior, schema IDs, compatibility rules, approval semantics, evidence requirements, public limits, or error codes, open an issue first. Explain the problem, compatibility impact, security impact, and alternatives.

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

See `docs/CONFORMANCE.md` for schema selection, exit codes, CI integration, and fail-closed expectations.

CI repeats these checks and also runs Rust tests on Linux, Windows, and macOS.

## Tests and fixtures

Observable protocol behavior should be backed by a test or fixture. If a schema changes, update the registry hash intentionally and explain compatibility impact. If compatibility behavior changes, keep the matrix, cases, Rust behavior, and documentation consistent.

Prefer targeted negative tests for malformed or ambiguous input. Unknown protocol input should remain fail-closed.

Every entry in `examples/v1/manifest.json` is executable conformance evidence. Valid fixtures must pass their declared schemas. Invalid fixtures must fail for their declared `expected_keyword`; do not add an invalid fixture that only happens to fail for an unrelated reason.

## Pull requests

Keep pull requests focused. Complete the pull-request template, especially the compatibility, security, verification, and public-boundary sections.

A pull request should be mergeable only when:

- CI is green;
- tests/fixtures cover changed behavior;
- public documentation is consistent;
- no private/commercial implementation details leaked into the OSS boundary.

## Commit and review quality

Use descriptive commit messages and explain *why* a contract changes, not only what lines changed. Review discussions should stay technical and evidence-driven.

## Good first contributions

Good starter work includes additional boundary fixtures, documentation clarifications, test coverage for public helpers, compatibility cases, and small transport-neutral examples.
