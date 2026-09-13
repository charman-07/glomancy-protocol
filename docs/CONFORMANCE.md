# Protocol Conformance

Glomancy Protocol ships a public fixture corpus and a small validation CLI so external implementations can verify protocol behavior without depending on the private commercial Glomancy runtime.

## Install the validator

From the repository root:

```bash
python3 -m pip install -r requirements-conformance.txt
```

The validator uses JSON Schema Draft 2020-12 with format checking enabled. Schema resolution is local to this repository; the CLI does not fetch schemas from the network.

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

## Execute the fixture corpus

```bash
python3 scripts/glomancy_conformance.py fixtures
```

The manifest at `examples/v1/manifest.json` has two groups:

- `valid`: every fixture must be accepted by its declared schema;
- `invalid`: every fixture must be rejected, and the validator must observe the declared `expected_keyword` such as `required`, `pattern`, `format`, `enum`, or `uniqueItems`.

This catches cases where an invalid fixture still fails, but for a different reason than the contract intended to test.

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

These exit codes are stable for the `0.1.x` public line and are intended for CI usage.

## Example CI usage

A non-Rust consumer can vendor or check out this repository and run:

```bash
python3 -m pip install -r requirements-conformance.txt
python3 scripts/glomancy_conformance.py validate path/to/generated-message.json
```

A failing payload returns exit code `2`, so ordinary CI shells will fail the step automatically.

## Fail-closed expectations

A conforming consumer should not silently accept or downgrade:

- unknown `schema_id` values;
- unknown message kinds;
- mismatched `schema_id` / `kind` pairs;
- unsupported wire-version combinations;
- malformed identifiers, timestamps, URIs, hashes, or bounded fields;
- messages that fail the declared JSON Schema.

Protocol validation is still not authorization. Passing a schema only establishes that the message matches the public wire contract; product policy, user approval, authentication, and execution safety remain separate responsibilities.

## Adding fixtures

When adding a fixture:

1. keep it minimal and focused on one contract rule where practical;
2. add it to `examples/v1/manifest.json`;
3. for an invalid fixture, declare the specific `expected_keyword`;
4. run `python3 scripts/glomancy_conformance.py fixtures`;
5. run the full repository CI before merging.

Do not add fixtures containing credentials, customer data, private infrastructure details, proprietary source, or machine-specific paths.
