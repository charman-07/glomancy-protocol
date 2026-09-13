# Protocol Conformance

Glomancy Protocol ships a public fixture corpus, language-neutral expected-outcome vectors, and small validation tools so external implementations can verify protocol behavior without depending on the private commercial Glomancy runtime.

If you are integrating the protocol into another project, start with the [External Adoption Guide](ADOPTION_GUIDE.md). It explains how to pin a released baseline or exact commit, vendor and verify schemas, consume the Rust package by Git tag, and upgrade without silently tracking mutable pre-1.0 `main` state.

## Install the payload validator

From the repository root:

```bash
python3 -m pip install -r requirements-conformance.txt
```

The payload validator uses JSON Schema Draft 2020-12 with format checking enabled. Schema resolution is local to this repository; the CLI does not fetch schemas from the network.

## Validate one payload

If the JSON document contains both `schema_id` and `kind`, the CLI discovers the registered schema automatically:

```bash
python3 scripts/glomancy_conformance.py validate examples/v1/valid/task.submit.json
```

You can also choose a schema explicitly:

```bash
python3 scripts/glomancy_conformance.py validate payload.json \
  --schema-id urn:glomancy:protocol:task.submit:1.0.0
```

or by message kind:

```bash
python3 scripts/glomancy_conformance.py validate payload.json --kind task.submit
```

If `schema_id` and `kind` resolve to different registry entries, validation fails closed rather than guessing.

## Machine-readable JSON output

`validate`, `fixtures`, and `list-schemas` support `--json` for CI systems and other tools that should not parse human terminal text.

Examples:

```bash
python3 scripts/glomancy_conformance.py validate message.json --json
python3 scripts/glomancy_conformance.py fixtures --json
python3 scripts/glomancy_conformance.py list-schemas --json
```

Each invocation emits exactly one JSON object to stdout. The top-level fields are:

| Field | Meaning |
| --- | --- |
| `output_version` | version of the CLI JSON output contract; currently `1.0.0` |
| `command` | `validate`, `fixtures`, or `list-schemas` |
| `ok` | whether the command succeeded for its requested operation |
| `exit_code` | the same stable process exit code returned by the CLI |

Additional fields are command-specific.

### `validate --json`

A valid payload includes its resolved `schema_id`, optional registered `kind`, `valid: true`, and an empty `errors` array.

An invalid payload keeps exit code `2` and returns structured validation errors. Each returned error includes:

- `keyword` — JSON Schema keyword associated with the error where available;
- `path` — payload path as an array of components;
- `path_text` — human-readable slash-joined path;
- `message` — validation message.

`error_count` reports the complete number of validation errors, while `errors` is capped by `--max-errors` and `truncated_error_count` reports how many were omitted.

Configuration/schema-selection failures keep exit code `3` and return an `error` object with `type: "configuration"`.

### `fixtures --json`

A successful run reports:

- `valid_fixtures_accepted`;
- `invalid_fixtures_rejected`;
- `total_fixtures`;
- `passed: true`.

Fixture conformance failure keeps exit code `2` and emits a structured error object.

### `list-schemas --json`

The result contains `schema_count` and a `schemas` array. Each entry includes `kind`, `schema_id`, and `version` from the canonical registry.

### Stability

The `output_version` field allows future tooling to detect incompatible JSON-output changes. Within output version `1.x`, new additive fields may appear, but existing fields should not silently change meaning. A breaking output-shape change requires a new output major version and release notes.

Human-readable output remains the default, and process exit codes are identical in human and JSON modes.

### Published JSON output schema

The machine-readable output contract is published separately from wire-protocol message schemas at:

```text
conformance/v1/cli-output.schema.json
```

It is a JSON Schema Draft 2020-12 document with ID:

```text
urn:glomancy:conformance:cli-output:1.0.0
```

The schema's `1.0.0` contract line corresponds to CLI field `output_version: "1.0.0"`. External automation can vendor this schema and validate CLI results without relying only on prose documentation.

This version is intentionally **independent** from:

- the Rust crate version;
- the Glomancy wire-protocol version;
- individual protocol message-schema versions;
- the language-neutral consumer-vector version.

A CLI-output contract change therefore does not imply a wire-protocol change, and a wire-protocol change does not automatically require a CLI-output major version bump.

Repository CI validates representative real CLI outputs against the published schema with:

```bash
python3 scripts/validate_cli_output_contract.py
```

The contract test exercises successful schema listing, successful payload validation, successful fixture execution, invalid-payload output, and a real configuration-error path. The fixture-conformance failure shape is also schema-checked without deliberately corrupting the repository fixture corpus.

## Execute the fixture corpus

```bash
python3 scripts/glomancy_conformance.py fixtures
```

The manifest at `examples/v1/manifest.json` has two groups:

- `valid`: every fixture must be accepted by its declared schema;
- `invalid`: every fixture must be rejected, and the validator must observe the declared `expected_keyword` such as `required`, `pattern`, `format`, `enum`, or `uniqueItems`.

This catches cases where an invalid fixture still fails, but for a different reason than the contract intended to test.

## Language-neutral consumer vectors

JSON Schema answers whether a payload matches a wire contract. Consumer integrations also need deterministic answers for decisions such as version compatibility, explicit advertised-version selection, capability negotiation, approval correlation, message-kind lookup, and task-time capability gating.

Those expected outcomes live under `vectors/v1/` as plain JSON so non-Rust implementations can run the same cases using their own code.

Repository consistency check:

```bash
python3 scripts/validate_consumer_vectors.py
```

External implementations should not copy the Python validator as their production implementation. Instead, implement the documented public rules in the target language and use the JSON vectors as input/expected output. That provides a more meaningful interoperability test.

See `docs/CONSUMER_VECTORS.md` for the layout, versioning rules, covered behavior, and integration guidance.

## Published compatibility snapshots

Real published public contract baselines are pinned under `compatibility/snapshots/` and checked with:

```bash
python3 scripts/validate_compatibility_snapshots.py
```

The suite begins with the actual `v0.1.0` release and checks that a compatible current line does not silently mutate bytes or message-kind mappings behind an already published schema ID. See `docs/SNAPSHOT_COMPATIBILITY.md`.

## List registered message schemas

```bash
python3 scripts/glomancy_conformance.py list-schemas
```

The command prints message kind, schema ID, and schema version from the canonical public registry.

## Exit codes

| Code | Meaning |
| ---: | --- |
| `0` | validation/conformance passed |
| `2` | payload or fixture validation failed |
| `3` | configuration, schema selection, registry, or input-file error |

These exit codes are stable for the `0.1.x` public line and are intended for CI usage. JSON mode preserves the same codes and also includes the code inside the emitted JSON object.

## Example CI usage

A non-Rust consumer can vendor or check out a **pinned release or exact commit** of this repository and run:

```bash
python3 -m pip install -r requirements-conformance.txt
python3 scripts/glomancy_conformance.py validate path/to/generated-message.json --json
python3 scripts/validate_consumer_vectors.py
python3 scripts/validate_compatibility_snapshots.py
python3 scripts/validate_cli_output_contract.py
```

A failing payload returns exit code `2`, while consumer-vector, compatibility-snapshot, or CLI-output-contract consistency failures return non-zero, so ordinary CI shells will fail the step automatically. Automation can parse the CLI JSON object for structured diagnostics and validate that object against the published output schema without changing the process-code contract.

Do not point production CI at mutable `main` and assume pre-1.0 behavior is frozen. The [External Adoption Guide](ADOPTION_GUIDE.md) describes release/tag and exact-commit pinning.

## Fail-closed expectations

A conforming consumer should not silently accept or downgrade:

- unknown `schema_id` values;
- unknown message kinds;
- mismatched `schema_id` / `kind` pairs;
- unsupported or unadvertised wire-version selections;
- unsupported required capabilities;
- task capability names not selected for the session;
- malformed or mis-correlated approval decisions;
- malformed identifiers, timestamps, URIs, hashes, or bounded fields;
- messages that fail the declared JSON Schema.

Protocol validation is still not authorization. Passing a schema, compatibility check, capability gate, or approval-correlation check only establishes agreement with the public protocol contract; product policy, user approval, authentication, authorization, and execution safety remain separate responsibilities.

## Adding fixtures or vectors

When adding a schema fixture:

1. keep it minimal and focused on one contract rule where practical;
2. add it to `examples/v1/manifest.json`;
3. for an invalid fixture, declare the specific `expected_keyword`;
4. run `python3 scripts/glomancy_conformance.py fixtures`;
5. run the full repository CI before merging.

When adding a consumer vector:

1. keep the case transport/provider/editor neutral;
2. add it to the correct `vectors/v1/*.json` file;
3. make the expected decision explicit;
4. run `python3 scripts/validate_consumer_vectors.py`;
5. update normative compatibility/capability/approval documentation if the rule itself changed.

Do not add fixtures, vectors, or CLI output containing credentials, customer data, private infrastructure details, proprietary source, or machine-specific paths.
