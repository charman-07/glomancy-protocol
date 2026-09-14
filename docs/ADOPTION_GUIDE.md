# External Adoption Guide

This guide is for developers who want to evaluate or integrate **Glomancy Protocol** without depending on the private commercial Glomancy runtime.

The main rule is simple: **pin what you consume**. Do not build an integration against a moving `main` branch and assume that pre-1.0 behavior will never change.

## Choose what you are adopting

Glomancy Protocol has several independently versioned surfaces:

- Rust package version;
- wire protocol version;
- JSON Schema versions and schema IDs;
- capability profile version;
- language-neutral consumer-vector version;
- conformance CLI JSON-output version.

These versions intentionally do not move in lockstep.

For a released baseline, start from an immutable Git tag such as `v0.1.0`. The `v0.1.0` release contains the initial Rust package, wire protocol `0.4.0`, public v1 message schemas, registry hashes, compatibility rules, capability profile, fixtures, and the first public conformance tooling.

Some interoperability tooling on the current repository `main` was added after `v0.1.0`, including language-neutral vectors, independent Python/JavaScript consumers, published compatibility snapshots, versioned CLI JSON-output schema, security/limits catalogs, and the standalone contract-bundle builder. Until those assets are included in a later release, consumers evaluating them should pin an **exact reviewed commit SHA**, not a mutable branch name.

Do not silently combine assets from different baselines. If you use schemas from a release tag and vectors from a later commit, document that choice in your own integration and test it explicitly.

## Rust: pin the public crate by Git tag

The package is intentionally not published to crates.io today (`publish = false`), but Cargo can consume it directly from the public Git repository.

For the released `v0.1.0` baseline:

```toml
[dependencies]
glomancy-protocol = { git = "https://github.com/charman-07/glomancy-protocol", tag = "v0.1.0" }
```

Cargo exposes the package as the Rust crate name `glomancy_protocol`.

A tag is preferable to `branch = "main"` because it gives your build a named immutable release boundary. For even stricter reproducibility, keep the resolved Git commit in `Cargo.lock` and review lockfile changes during upgrades.

## Non-Rust: vendor a release baseline

For C++, C#, Python, TypeScript/JavaScript, Go, Java, or another implementation, clone a named release into a dedicated vendor/test directory:

```bash
git clone --branch v0.1.0 --depth 1 \
  https://github.com/charman-07/glomancy-protocol.git \
  glomancy-protocol-v0.1.0
```

The most important released public assets are:

```text
registry/v1/         canonical schema registry and SHA-256 metadata
schemas/v1/          JSON Schema message contracts
compatibility/v1/    wire compatibility rules and cases
capabilities/v1/     capability profile and conformance cases
examples/v1/         valid and intentionally invalid message fixtures
```

If you intentionally evaluate newer unreleased tooling, replace the tag with an exact reviewed commit SHA:

```bash
git clone https://github.com/charman-07/glomancy-protocol.git
cd glomancy-protocol
git checkout <exact-reviewed-commit-sha>
```

Avoid treating `main` as a stable API version before 1.0.

## Non-Rust: build one deterministic contract package

For current pinned revisions that include the bundle builder, non-Rust consumers can package the language-neutral public contract surface into one deterministic ZIP:

```bash
python3 scripts/build_contract_bundle.py \
  --out-dir dist/glomancy-contracts \
  --archive dist/glomancy-protocol-contracts.zip \
  --json
```

The package includes public schemas, registry, compatibility data, capability profile, consumer vectors, error/security/limits/support policies, the public contract fingerprint, conformance output contract, `BUNDLE_MANIFEST.json`, `SHA256SUMS`, and the MIT license.

Repository CI builds the archive twice and requires byte-identical ZIP output for the same source content. This makes the package useful for vendoring and integrity comparison without requiring the Rust crate.

This does **not** mean every historical GitHub release already contains a downloadable ZIP asset. Generate it from a pinned source revision unless a future release explicitly publishes and verifies the artifact.

See [Standalone Contract Bundle](CONTRACT_BUNDLE.md) for contents, verification, determinism, and assurance boundaries.

## Verify registry hashes before trusting a schema

`registry/v1/manifest.json` maps public schema IDs and message kinds to files and SHA-256 digests. A consumer that vendors schemas should verify those digests as part of its update or build process.

Conceptually:

```text
for each registry entry:
    bytes = read(entry.file)
    actual = sha256(bytes)
    require actual == entry.sha256
```

The repository defines canonical schema bytes as UTF-8, LF line endings, JSON indentation of two spaces, and a trailing newline.

Why this matters:

- a published schema ID should not silently point to different bytes;
- an integration can detect accidental or unauthorized local changes;
- release-to-release compatibility review can distinguish an additive new contract from mutation of an existing identity.

The repository CI performs the same class of registry/hash consistency checks.

## Recommended implementation sequence

A practical external implementation should adopt the protocol in this order:

1. **Pin a baseline.** Use a release tag, or an exact reviewed commit for unreleased evaluation.
2. **Load and verify the registry.** Reject unknown schema IDs and message kinds rather than guessing.
3. **Implement wire-version handling.** Follow the published compatibility and advertised-version selection rules.
4. **Implement capability negotiation.** Match exact capability name + version and reject unsupported required capabilities.
5. **Keep task capabilities session-bound.** A task may request only capabilities selected for that session.
6. **Implement approval correlation carefully.** Correlate approval and task IDs, enforce expiry, and distinguish `deny` from malformed/expired decisions.
7. **Validate payloads before execution.** JSON Schema validation is a prerequisite, not permission to act.
8. **Keep authorization separate.** Authentication, authorization, product policy, sandboxing, editor permissions, and user consent remain consumer responsibilities.
9. **Run conformance fixtures/vectors.** Compare your implementation with the public expected outcomes.
10. **Record evidence and failures explicitly.** Do not collapse protocol rejection, authorization denial, tool failure, and successful execution into one generic result.

## Conformance paths

### Released fixture corpus

From a checked-out baseline:

```bash
python3 -m pip install -r requirements-conformance.txt
python3 scripts/glomancy_conformance.py fixtures
```

To validate one payload:

```bash
python3 scripts/glomancy_conformance.py validate path/to/message.json
```

### Machine-readable diagnostics

Current conformance tooling supports a versioned JSON mode:

```bash
python3 scripts/glomancy_conformance.py validate path/to/message.json --json
```

The current `1.0.0` JSON-output contract is described by:

```text
conformance/v1/cli-output.schema.json
```

If you consume unreleased tooling before it appears in a tagged release, pin the exact commit containing both the CLI and its output schema.

### Language-neutral decision vectors

Current repository versions include plain-JSON vectors for deterministic decisions such as:

- message-kind lookup;
- wire compatibility;
- explicit advertised-version selection;
- capability negotiation;
- task capability gating;
- approval correlation and expiry.

They live under `vectors/v1/` and are designed so a consumer can implement the rules independently rather than importing Glomancy's validator code.

The repository also contains independent Python and JavaScript examples that execute these vectors. They are maintained interoperability examples, not evidence of third-party adoption.

## Upgrade discipline

When a new Glomancy Protocol release appears:

1. read `CHANGELOG.md` and the release notes;
2. compare crate, wire, schema, vector, capability, and tooling versions independently;
3. review new/changed registry entries and SHA-256 values;
4. run your existing conformance suite against the new baseline;
5. review deprecations and migration guidance;
6. update your pinned tag/commit only after your implementation passes its own tests.

Do not infer compatibility only from the Rust package version. The wire protocol and message schemas have their own explicit identities and compatibility rules.

For pre-1.0 behavior, read [Pre-1.0 Deprecation and Schema Evolution Policy](DEPRECATION_POLICY.md) before upgrading.

## Security boundary

Passing Glomancy Protocol validation does **not** authorize an editor/tool action.

A consumer must still enforce, as appropriate:

- authenticated caller/session identity;
- user/project permissions;
- risk policy and human approval;
- sandbox or process isolation;
- editor/plugin capability and permission checks;
- resource/time limits;
- provider or infrastructure credentials outside protocol messages.

Do not put API keys, access tokens, customer data, proprietary source, machine-private paths, or sensitive infrastructure details into protocol fixtures or public integration reports.

## Report genuine integration results

If you actually implement or evaluate the protocol independently, use the repository's **Integration feedback** issue form. Useful reports include:

- language and runtime;
- pinned release/tag or exact commit;
- wire/vector/schema versions tested;
- which conformance areas passed or disagreed;
- ambiguity or friction you encountered;
- an optional public implementation link.

Maintainer-authored examples and notes are intentionally kept separate from external feedback. The project does not claim external production adoption that has not been demonstrated.

## Related documentation

- [Evaluate in 5 minutes](EVALUATE_IN_5_MINUTES.md)
- [Standalone Contract Bundle](CONTRACT_BUNDLE.md)
- [Ecosystem and Implementations](ECOSYSTEM.md)
- [Protocol Conformance](CONFORMANCE.md)
- [Consumer Integration Guide](INTEGRATION_GUIDE.md)
- [Consumer Conformance Vectors](CONSUMER_VECTORS.md)
- [Compatibility](COMPATIBILITY.md)
- [Capability Negotiation](CAPABILITY_NEGOTIATION.md)
- [Snapshot Compatibility](SNAPSHOT_COMPATIBILITY.md)
- [Security Model](SECURITY_MODEL.md)
- [Integration Pitfalls](INTEGRATION_PITFALLS.md)
