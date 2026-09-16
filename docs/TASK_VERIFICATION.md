# Portable task verification profiles

Glomancy Protocol already provides public contracts for task lifecycle, approvals, context references, evidence records, terminal outcomes, full-session conformance, context policy, and Context Snapshot comparison.

Task Verification Profiles combine those existing public surfaces into one **non-wire structural verification layer**.

The purpose is not to certify that a private runtime performed an Unreal compile, PIE run, read-back, rollback, test, build, or editor mutation correctly. The purpose is to let external tooling state and evaluate a small set of explicit, portable conditions around a public task transcript.

## Verification profile

A profile is validated against `verification/v1/profile.schema.json` and is versioned separately from the wire protocol.

Example:

```json
{
  "profile_version": "1.0.0",
  "require_success": true,
  "require_context_snapshot_match": true,
  "require_read_back_verified": true,
  "required_evidence_types": [
    "read-back"
  ]
}
```

Fields:

- `profile_version` — tooling contract version; currently `1.0.0`;
- `require_success` — terminal task status must be `succeeded`;
- `require_context_snapshot_match` — a Context Snapshot Descriptor must be supplied and structurally match the task's public context references;
- `require_read_back_verified` — terminal outcome must be `task.result`, set `read_back_verified: true`, and reference at least one public `evidence.record` whose type is `read-back`;
- `required_evidence_types` — every listed evidence category must be referenced by the terminal outcome's `evidence_ids`;
- `evidence_coverage` — optional fail-closed count/linkage requirements over public evidence records.

Allowed evidence types are taken from the existing public `evidence.record.payload.evidence_type` contract. Profiles do not introduce a second evidence namespace.

## Evidence coverage gates

`required_evidence_types` answers a binary question: did the terminal outcome reference at least one evidence record of each required type?

Some integrations need a stronger structural policy. The optional `evidence_coverage` object can additionally require:

```json
{
  "evidence_coverage": {
    "minimum_terminal_referenced_evidence_count": 2,
    "minimum_terminal_referenced_evidence_type_counts": {
      "read-back": 1,
      "test": 1
    },
    "maximum_unreferenced_evidence_count": 0
  }
}
```

Coverage fields:

- `minimum_terminal_referenced_evidence_count` — minimum total number of public evidence records referenced by the terminal `task.result` or `task.error`;
- `minimum_terminal_referenced_evidence_type_counts` — per-type minimum counts among evidence records referenced by that terminal outcome;
- `maximum_unreferenced_evidence_count` — maximum number of public evidence records present in the session but not linked by the terminal outcome. `0` means every public evidence record in the session must be terminal-linked.

The stricter example profile is published at:

```text
verification/v1/examples/strict-evidence-coverage.json
```

Existing profiles that omit `evidence_coverage` keep their previous behavior. Their normalized defaults are:

- minimum terminal-referenced total: `0`;
- minimum per-type counts: `{}`;
- maximum unreferenced evidence count: `null` (no maximum).

Coverage gates operate only after canonical session conformance has accepted the transcript. They count schema-valid public `evidence.record` messages and the terminal message's already-validated `evidence_ids`; they do not inspect private artifacts or infer evidence truth.

## Evaluate a task

```bash
python3 scripts/glomancy_task_verification.py \
  verification/v1/examples/strict-read-back.json \
  path/to/session.json \
  --snapshot path/to/context-snapshot.json
```

Evidence-coverage example:

```bash
python3 scripts/glomancy_task_verification.py \
  verification/v1/examples/strict-evidence-coverage.json \
  path/to/session.json \
  --snapshot path/to/context-snapshot.json \
  --json
```

Machine-readable output:

```bash
python3 scripts/glomancy_task_verification.py \
  verification/v1/examples/strict-read-back.json \
  path/to/session.json \
  --snapshot path/to/context-snapshot.json \
  --json
```

Exit codes:

- `0` — all profile conditions passed;
- `2` — the public session or one verification condition failed;
- `3` — profile/input/snapshot configuration could not be evaluated.

## Validation order

The evaluator is deliberately ordered so higher-level verification cannot bypass lower-level public conformance:

1. validate the Verification Profile;
2. validate the complete transcript through canonical full-session conformance;
3. if the profile requires it, validate and compare the Context Snapshot Descriptor;
4. evaluate the terminal success requirement;
5. resolve the terminal outcome's `evidence_ids` to already-seen public evidence records;
6. require the profile's binary `required_evidence_types` categories;
7. require the minimum terminal-referenced evidence total, when configured;
8. require each configured per-type minimum count;
9. enforce the configured maximum unreferenced evidence count;
10. when read-back verification is required, require both the terminal `read_back_verified` flag and terminal-referenced `read-back` evidence.

This means an evidence record that merely appears somewhere in a conforming transcript does not satisfy a terminal coverage requirement unless the terminal outcome actually references it.

## Fail-closed reasons

Stable verification failures include:

- `session-conformance-failed`;
- `context-snapshot-required`;
- `context-snapshot-mismatch`;
- `terminal-status-not-succeeded`;
- `required-evidence-type-missing`;
- `terminal-evidence-count-below-minimum`;
- `terminal-evidence-type-count-below-minimum`;
- `unreferenced-evidence-count-exceeds-maximum`;
- `read-back-flag-not-set`;
- `read-back-evidence-not-referenced`.

Malformed profiles, invalid required snapshots, missing files, and other configuration/input errors use exit code `3`.

## Machine-readable report

The published output schema is:

```text
conformance/v1/task-verification-output.schema.json
```

The report includes structural fields such as:

- terminal kind/status;
- whether the session passed canonical conformance;
- whether a required snapshot matched;
- whether `read_back_verified` was set;
- required evidence categories;
- configured minimum terminal-referenced evidence total;
- configured per-type evidence minimums;
- configured maximum unreferenced evidence count;
- evidence-type counts across the session;
- evidence-type counts referenced by the terminal outcome;
- total evidence count;
- terminal-referenced evidence count;
- unreferenced evidence count.

The report intentionally does **not** copy evidence claims, evidence hashes, artifact URIs, context URIs, context revision values, user instructions, project paths, or private runtime state into the derived summary.

## Why the read-back rule uses two signals

`task.result.read_back_verified` is a public terminal assertion. `evidence.record` is a public evidence envelope. Either one alone is weaker as an interoperability signal than requiring both to agree structurally.

A profile with `require_read_back_verified: true` therefore requires:

1. terminal kind `task.result`;
2. `read_back_verified: true`;
3. at least one `read-back` evidence record referenced by that same terminal result.

This is a correlation rule for public protocol data. It still does not prove that the underlying read-back was technically correct.

## Relationship to Glomancy

Glomancy's product-side architecture is moving toward a chain like:

```text
observed context
  -> planning/policy
  -> execution
  -> validation/read-back
  -> evidence
  -> terminal outcome
```

Private implementations may perform Unreal-specific compile checks, editor read-back, PIE observations, build/test diagnostics, rollback checks, restore validation, or bounded self-repair. Those mechanisms can evolve independently.

The public profile captures only the stable interoperability boundary: **which public conditions must be present, linked, and counted before an external consumer treats a task transcript as structurally verified under that chosen profile**.

Coverage gates are useful for future Glomancy flows where one task may emit several classes of evidence — for example read-back plus test/build evidence — while keeping the private validation engine and repair logic private.

## Assurance boundary

Passing a Task Verification Profile means only that the supplied public artifacts satisfy the profile's structural conditions.

Evidence coverage additionally proves only that configured public evidence count/linkage thresholds were met.

It does **not** prove:

- that evidence content is true;
- that an evidence hash was recomputed by this tool;
- provenance or producer authenticity;
- that a referenced artifact exists or is unchanged;
- that context was fresh, complete, or actually consumed by a model/runtime;
- that Unreal compilation, PIE, read-back, rollback, restore, build, test, or mutation logic was correct;
- that a private validation engine ran the intended algorithm;
- authentication, authorization, sandboxing, confidentiality, certification, or production readiness;
- correctness of self-repair or planner/orchestrator decisions.

Those responsibilities remain outside this public conformance layer.

## Compatibility

Task Verification Profiles and their report schema are tooling/conformance contracts, not new wire messages.

The new `evidence_coverage` object and report fields are additive within the existing tooling contract. Existing profiles without coverage requirements remain valid.

This feature does not change:

- wire protocol version `0.4.0`;
- existing message schema IDs;
- Rust package/API versioning;
- private Glomancy runtime behavior.

A future breaking profile/report change must version its own tooling contract deliberately rather than silently changing the wire protocol.
