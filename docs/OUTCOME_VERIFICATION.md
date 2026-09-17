# Outcome-specific task verification

Glomancy Protocol models four public terminal task statuses:

- `succeeded` through `task.result`;
- `failed` through `task.error`;
- `cancelled` through `task.error`;
- `rolled_back` through `task.error`.

Task Verification Profiles can optionally apply structural verification rules to those outcomes without changing the wire protocol or exposing private runtime behavior.

## Why outcome-specific verification exists

A truthful automation system should be able to verify more than successful completion. A failed, cancelled, or rolled-back task can still have a well-formed, auditable public outcome.

For example, a public transcript that reports `rolled_back` may be required to satisfy all of these structural conditions:

1. the complete transcript passes canonical session conformance;
2. the terminal status is exactly `rolled_back`;
3. the terminal `task.error.evidence_ids` references at least one public `rollback` evidence record;
4. `task.error.payload.rollback_attempted` is `true`;
5. any configured evidence coverage thresholds also pass.

These conditions do not prove that a private restore implementation actually reconstructed the correct before-state. They only verify that the public protocol data is structurally consistent with the chosen policy.

## Profile shape

The optional profile field is `terminal_outcome_policy`:

```json
{
  "terminal_outcome_policy": {
    "allowed_statuses": [
      "rolled_back"
    ],
    "required_evidence_types_by_status": {
      "rolled_back": [
        "rollback"
      ]
    },
    "require_rollback_attempted_for_statuses": [
      "rolled_back"
    ]
  }
}
```

### `allowed_statuses`

When present, the actual terminal status must be one of the configured values:

```text
succeeded
failed
cancelled
rolled_back
```

When omitted, no additional status whitelist is applied beyond the existing profile rules.

`require_success: true` continues to mean the terminal status must be `succeeded`. A profile is rejected as configuration error when it simultaneously sets `require_success: true` and an `allowed_statuses` list that excludes `succeeded`.

### `required_evidence_types_by_status`

This object maps a terminal status to public evidence categories that must be referenced by that terminal outcome.

Example:

```json
{
  "required_evidence_types_by_status": {
    "succeeded": ["read-back", "test"],
    "rolled_back": ["rollback"]
  }
}
```

Evidence merely present somewhere else in the session does not satisfy the rule. It must be linked by the terminal message's `evidence_ids`.

### `require_rollback_attempted_for_statuses`

This list applies only to `task.error` statuses:

```text
failed
cancelled
rolled_back
```

When the actual terminal status appears in this list, `task.error.payload.rollback_attempted` must be `true`.

This field reports only the public boolean claim already present in `task.error`. It does not prove restore correctness.

## Strict rollback profile

The repository includes:

```text
verification/v1/examples/strict-rollback.json
```

It requires:

- `rolled_back` as the only accepted terminal status;
- at least one terminal-linked evidence record;
- at least one terminal-linked `rollback` evidence record;
- zero unreferenced public evidence records;
- `rollback_attempted: true`.

Run it with:

```bash
python3 scripts/glomancy_task_verification.py \
  verification/v1/examples/strict-rollback.json \
  transcripts/v1/accepted/approved-write-then-rolled-back.json \
  --json
```

The same profile/session pair can be placed in a deterministic Verification Bundle. Bundle verification re-runs the expanded Task Verification result, so outcome-specific requirements cannot be bypassed by editing and re-hashing only `verification-result.json`.

## Fail-closed reasons

Outcome-specific policy adds three stable verification failures:

- `terminal-status-not-allowed` — the actual terminal status is outside the configured whitelist;
- `terminal-status-evidence-type-missing` — the terminal outcome does not reference a required evidence category for its status;
- `rollback-attempt-not-reported` — policy requires a rollback attempt for the actual task-error status but `rollback_attempted` is not `true`.

Profile/schema/input problems remain configuration errors with exit code `3`.

## Machine-readable output

The existing output contract remains:

```text
conformance/v1/task-verification-output.schema.json
```

Outcome-aware verification adds normalized report fields:

- `allowed_terminal_statuses`;
- `terminal_required_evidence_types` for the actual terminal status;
- `rollback_attempt_required`;
- observed `rollback_attempted` (`null` for `task.result`).

Existing profiles that omit `terminal_outcome_policy` keep their previous behavior. Their normalized defaults are an empty status whitelist, no status-specific evidence requirements, and no rollback-attempt requirement.

## Relationship to private Glomancy restore and self-repair

Glomancy may privately perform before-state capture, dry-run checks, editor mutations, compile/read-back validation, rollback/restore, and bounded self-repair.

Those algorithms and implementation details remain private.

The public protocol exposes only a small interoperability boundary: a terminal status, terminal-linked public evidence records, and an existing rollback-attempt boolean. Outcome-specific verification lets an external consumer apply deterministic policy to those public facts without learning how the private runtime produced them.

## Assurance boundary

Passing an outcome-specific verification profile proves only structural consistency of the supplied public protocol data under that profile.

It does **not** prove:

- that rollback or restore reconstructed the correct before-state;
- that a private mutation actually occurred;
- that evidence content is true;
- that an artifact exists or is correct;
- provenance, producer identity, authentication, or authorization;
- Unreal compile, PIE, read-back, rollback, restore, build, or test correctness;
- correctness of self-repair, planning, or orchestration;
- certification or production readiness.

The feature is intentionally provider-neutral, editor-agnostic, transport-neutral, additive, and fail-closed.

## Compatibility

Outcome-specific verification is a tooling/conformance feature only.

It does not change:

- wire protocol version `0.4.0`;
- existing wire message fields;
- existing message schema IDs;
- Rust wire API versioning;
- private Glomancy runtime behavior.
