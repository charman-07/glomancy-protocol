# Ordered terminal evidence sequence verification

Task Verification Profiles can require more than evidence presence and count. Some workflows also need a public structural ordering between evidence categories.

The optional `evidence_sequence` policy verifies that selected terminal-linked public evidence types appear in transcript order as an ordered subsequence.

## Example

```json
{
  "evidence_sequence": {
    "required_terminal_evidence_sequence": [
      "read-back",
      "rollback"
    ]
  }
}
```

The repository publishes a stricter restoration-oriented example at:

```text
verification/v1/examples/strict-restoration-sequence.json
```

That profile combines:

- terminal status `rolled_back`;
- terminal-linked `read-back` and `rollback` evidence;
- zero unreferenced public evidence;
- `rollback_attempted: true`;
- ordered `read-back -> rollback` evidence.

## Semantics

The verifier first runs canonical full-session conformance and resolves the terminal outcome's `evidence_ids`.

It then walks the complete transcript in message order and builds `observed_terminal_evidence_sequence` from only those `evidence.record` messages whose evidence IDs are referenced by the terminal outcome.

The configured `required_terminal_evidence_sequence` must appear as an ordered subsequence of that observed terminal-linked sequence.

For example:

```text
required: read-back -> rollback
observed: log -> read-back -> test -> rollback
result:   pass
```

But:

```text
required: read-back -> rollback
observed: rollback -> read-back
result:   fail
```

And evidence that exists in the session but is not referenced by the terminal outcome is excluded from the observed terminal sequence.

Repeated evidence types are allowed in the required sequence, so a future integration can express policies such as:

```text
read-back -> test -> read-back
```

without adding new wire fields.

## Failure reason

A required sequence that is not an ordered subsequence of the terminal-linked evidence sequence fails closed with:

```text
terminal-evidence-sequence-mismatch
```

The derived detail reports evidence type names only. It does not echo evidence IDs, evidence claims, hashes, artifact URIs, project paths, or private runtime state.

## Machine-readable output

The existing task-verification output contract publishes:

- `required_terminal_evidence_sequence`;
- `observed_terminal_evidence_sequence`;
- `terminal_evidence_sequence_matched`.

Existing profiles that omit `evidence_sequence` keep their previous behavior. Their required sequence is empty and `terminal_evidence_sequence_matched` is `true`.

## Deterministic Verification Bundle replay

A successful sequence-aware Task Verification result can be placed in the existing deterministic Verification Bundle.

Bundle verification re-runs Task Verification from the bundled profile and transcript. The recomputed normalized result must match `verification-result.json` exactly, including the required and observed evidence sequences.

This prevents a bundle from passing merely because someone edited sequence-related result fields and recomputed ordinary checksums.

## Relationship to private Glomancy execution

A private editor/runtime workflow may internally perform steps such as grounding, dry-run/preflight, before-state capture, mutation, read-back, rollback/restore, and final verification.

Those implementation details remain private.

The public sequence policy exposes only a portable structural requirement over already-public evidence categories. It does not standardize how a product executes, retries, restores, selects changesets, resolves objects, or builds its private evidence ledger.

## Assurance boundary

Passing ordered evidence sequence verification proves only that the terminal-linked public evidence records appear in the supplied transcript in an order compatible with the caller's configured evidence-type subsequence.

It does **not** prove:

- actual runtime or wall-clock execution order;
- that evidence content is true;
- that a mutation occurred;
- that read-back was technically correct;
- that rollback or restore reconstructed the correct before-state;
- that unrelated project state was untouched;
- producer identity, provenance, authentication, or authorization;
- correctness of private changeset selection, evidence-ledger logic, self-repair, planner, or orchestrator behavior;
- certification or production readiness.

## Compatibility

This is a non-wire tooling/conformance feature.

It does not change:

- wire protocol version `0.4.0`;
- existing message schema IDs;
- public Rust wire API versioning;
- private Glomancy runtime behavior.
