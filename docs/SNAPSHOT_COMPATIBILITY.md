# Published Compatibility Snapshots

Glomancy Protocol keeps small, machine-readable snapshots of published public contract baselines under `compatibility/snapshots/`.

The goal is not to duplicate the repository or preserve private product history. The goal is to pin the public metadata that matters for compatibility review so a future change cannot silently rewrite a published contract.

## What is pinned

Each published snapshot records:

- the public release tag;
- the reviewed release commit;
- the Rust package version at that release;
- the wire protocol version;
- the JSON Schema dialect;
- public support-schema IDs, versions, and SHA-256 hashes;
- public message kinds, schema IDs, versions, and SHA-256 hashes.

The first baseline is the real published `v0.1.0` release. No fictional historical snapshots are created.

## Why this matters

A schema ID is a public identity. If the bytes behind an existing published schema ID change silently, two consumers can believe they implement the same contract while actually validating different payload shapes.

For a current contract that is still wire-compatible with a published snapshot, the regression validator therefore requires pinned schema IDs to remain present and their pinned hashes/message-kind mappings to remain unchanged.

If a future change intentionally introduces a new schema revision, it should receive a new schema ID/version rather than mutating the content behind a published ID.

## Validator

Run:

```bash
python3 scripts/validate_compatibility_snapshots.py
```

The validator checks every snapshot listed in `compatibility/snapshots/manifest.json` against the current public registry and crate metadata. CI runs this check on every pull request and push.

The check verifies, among other things:

- unique snapshot IDs and source tags;
- valid release-style source metadata;
- semantic version ordering for the crate;
- expected wire compatibility between current and published lines;
- unchanged schema dialect for compatible snapshots;
- presence of pinned schema IDs;
- unchanged SHA-256 content for a published schema ID;
- unchanged message-kind mapping for a published message schema.

## Adding a snapshot

Only add a snapshot after a real public release is published.

1. Copy the public registry metadata from the reviewed release tag.
2. Record the exact release tag and commit SHA.
3. Add a compact snapshot JSON file under `compatibility/snapshots/`.
4. Add the snapshot to `compatibility/snapshots/manifest.json`.
5. Set the expected compatibility relation to the then-current wire protocol deliberately.
6. Run the snapshot validator and the full CI suite.
7. Review any compatibility failure as a protocol-design decision, not as a test to bypass.

Do not add synthetic releases, guessed historical states, or private Glomancy implementation details merely to make the project look more mature.

## Scope

These snapshots cover the public protocol contract only. They do not snapshot the commercial Glomancy runtime, Unreal Engine integration code, model/provider logic, credentials, billing, desktop UI, or proprietary orchestration.

Snapshot compatibility is also not a security guarantee. Authentication, authorization, policy, sandboxing, editor permissions, and execution safety remain responsibilities of the consuming implementation.
