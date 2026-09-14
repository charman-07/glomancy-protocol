# Contributor Start Here

This page is the shortest path from **“I found the repository”** to **“I can make a useful first contribution.”**

Glomancy Protocol is pre-1.0 and welcomes focused contributions that improve interoperability, validation, documentation, compatibility, or executable conformance without crossing into the private commercial Glomancy runtime.

## Choose a contribution size

### 15–30 minutes

Good choices:

- clarify a confusing paragraph or error message;
- add a narrowly scoped malformed-input fixture;
- improve an existing example README;
- add a missing negative test for a public helper;
- improve a docs link or compatibility explanation.

### 1–2 hours

Good choices:

- add a new boundary fixture plus manifest entry;
- extend a language-neutral vector area with a clearly specified edge case;
- improve a public validator with tests;
- add a small transport-neutral example;
- add a documented CI recipe for an external consumer.

### Larger but still newcomer-friendly

Independent consumer implementations are especially useful because they prove that the public contract can be implemented without depending on the Rust crate or private Glomancy code.

Current newcomer issues:

- [#60 — independent Go consumer](https://github.com/charman-07/glomancy-protocol/issues/60)
- [#81 — independent C# consumer](https://github.com/charman-07/glomancy-protocol/issues/81)
- [#82 — copy-paste GitHub Actions conformance recipe](https://github.com/charman-07/glomancy-protocol/issues/82)

Look for the `good first issue` and `help wanted` labels for the current list.

## Before you code

For a small editorial/test change, you can usually open a focused pull request directly.

For behavior that changes public protocol semantics, first read:

- `CONTRIBUTING.md`;
- `docs/PROTOCOL_CHANGE_PROCESS.md`;
- `docs/COMPATIBILITY.md`;
- `docs/SECURITY_MODEL.md`.

Changes to wire behavior, schema identity, capabilities, approvals, evidence, lifecycle semantics, limits, error contracts, or fail-closed behavior normally require a proposal or explicit maintainer review before implementation.

## Minimal local setup

```bash
git clone https://github.com/charman-07/glomancy-protocol.git
cd glomancy-protocol
rustup toolchain install 1.85.0 --profile minimal --component rustfmt --component clippy
rustup override set 1.85.0
cargo test --all-targets
```

For public conformance tooling:

```bash
python3 -m pip install -r requirements-conformance.txt
python3 scripts/glomancy_conformance.py fixtures
```

## Make one focused change

A strong first PR usually has:

1. one clearly stated problem;
2. the smallest reasonable implementation;
3. executable evidence — a test, fixture, vector, parity validator, or reproducible command;
4. documentation only where behavior or usage changed;
5. no unrelated formatting/refactoring.

If you touch a public contract file, explain compatibility impact explicitly.

## Run the checks that matter

Always run:

```bash
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
python3 scripts/validate_repository.py
```

Then run the validator for the area you changed. Examples:

```bash
python3 scripts/validate_consumer_vectors.py
python3 scripts/validate_capability_profile.py
python3 scripts/validate_security_invariants.py
python3 scripts/validate_resource_limits.py
python3 scripts/public_contract_fingerprint.py --check
```

GitHub Actions will also run cross-platform Rust tests on Linux, Windows, and macOS.

## Open the pull request

Complete the PR template rather than replacing it with a one-line description. Reviewers should be able to see:

- what changed;
- why it changed;
- compatibility impact;
- security/trust-boundary impact;
- what executable evidence proves the intended behavior;
- whether any public contract fingerprint changed.

If CI fails, keep the failure visible and fix the root cause. A real failed check followed by a focused fix is more useful project history than hiding or bypassing the check.

## Public/private boundary

Do not contribute:

- API keys or credentials;
- private Glomancy runtime/provider/billing code;
- proprietary editor mutation implementations;
- customer/project data;
- signing keys or certificates;
- machine-specific private paths.

When in doubt, ask through an issue before posting sensitive implementation details.

## External integration feedback is valuable

If you tried Glomancy Protocol in another repository, language, editor, or tool—even if you found a problem—please use the **Integration feedback** issue form. Genuine implementation feedback is intentionally kept separate from maintainer-authored examples so the project does not manufacture adoption claims.

For a question before implementing, use the **Integration question** form.
