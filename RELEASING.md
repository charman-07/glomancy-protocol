# Releasing

This checklist is intended to keep public releases reproducible and deliberate.

## Before tagging

1. Confirm `main` is green in GitHub Actions.
2. Confirm `Cargo.toml` contains the intended package version.
3. Confirm the wire version in `src/lib.rs`, `registry/v1/manifest.json`, and `compatibility/v1/compatibility-matrix.json` is consistent.
4. Run locally:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps
cargo run --example quick_start
python3 scripts/validate_repository.py
python3 -m pip install -r requirements-conformance.txt
python3 scripts/glomancy_conformance.py fixtures
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json
```

5. Review all changes since the previous release for:
   - wire compatibility impact;
   - schema identifier or hash changes;
   - security implications;
   - dependency and GitHub Actions changes;
   - new public error codes or limits;
   - documentation and fixture coverage.
6. Review `docs/SUPPLY_CHAIN.md` and confirm dependency/Action changes were intentional, reviewed, and passed the full applicable CI suite.
7. Update `CHANGELOG.md`.
8. Confirm no credentials, private infrastructure details, customer data, signing material, or proprietary runtime code entered the public history.

## Tag and GitHub release

Use an annotated semantic-version tag such as `v0.1.0`. The GitHub release notes should summarize user-visible changes, compatibility impact, and any migration steps.

Do not describe a release as stable or production-proven unless there is evidence to support that claim. Do not claim signed-release, reproducible-build, or supply-chain certification properties unless they are implemented and independently verifiable for that release.

## After release

- verify the tag points to the intended `main` commit;
- verify the CI status for that commit;
- verify README links and examples from the tagged source;
- verify the public conformance CLI against the tagged source;
- open follow-up issues for deferred work rather than silently changing a published compatibility promise.

## Security releases

For a sensitive vulnerability, coordinate disclosure through the process in `SECURITY.md`. Do not expose exploit details before affected users have a reasonable opportunity to update.
