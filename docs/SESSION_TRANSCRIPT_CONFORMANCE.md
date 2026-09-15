# Full-session transcript conformance

Glomancy Protocol includes a versioned, language-neutral full-session transcript suite under `transcripts/v1/`.

The suite tests a property that isolated message validation cannot establish: whether individually schema-valid public protocol envelopes form a coherent session when their correlations, negotiated capabilities, approvals, evidence references, task identity, and terminal ordering are evaluated together.

## Validation order

The runner deliberately validates each message in this order:

1. Parse the transcript JSON.
2. Resolve `kind` through the canonical `registry/v1/manifest.json`.
3. Require the envelope `schema_id` to match that registry entry.
4. Validate the complete public envelope against the registered Draft 2020-12 JSON Schema, including format checks.
5. Only after schema validation succeeds, evaluate cross-message correlation and session-state rules.

A schema-valid message is therefore not automatically a valid session event.

Run the suite with:

```bash
python3 scripts/validate_session_transcript_suite.py
```

The command emits one deterministic JSON object per case and a final summary. Rejections include a stable reason plus the failing message index and diagnostic detail when applicable, making CI failures actionable without changing the wire protocol.

## Corpus layout

`transcripts/v1/cases.json` is the suite manifest. The accepted corpus contains complete full-envelope transcripts in `transcripts/v1/accepted/`.

Rejected cases are defined as deterministic mutations of a named accepted transcript. The runner deep-copies and materializes those mutations into a complete transcript before any schema or lifecycle evaluation. This keeps negative fixtures reviewable without duplicating large sessions while preserving the exact full-envelope validation path.

The initial accepted cases cover:

- approval-gated success with evidence;
- read-only success without approval;
- a cancellation request followed by terminal `cancelled`;
- an approved write followed by reported `rolled_back`;
- terminal failure with evidence.

The initial rejected cases cover unadvertised selected versions/capabilities, task capability drift, approval correlation/order/expiry failures, execution before approval, duplicate or unknown evidence, task-ID drift, events after terminal outcomes, and a malformed message that must fail JSON Schema validation before lifecycle evaluation.

## Session rules exercised

The suite stays within semantics established by the public protocol surface:

- a handshake response correlates to the handshake request;
- selected versions must have been explicitly advertised;
- selected capabilities use exact public name/version pairs and required advertised capabilities cannot silently disappear;
- task-requested capability names must be a subset of the negotiated selected set;
- task identity remains stable across task, approval, evidence, and terminal events;
- approval decisions cannot precede their request, must match approval/task identity, and must not be expired;
- a denial does not open an approval gate;
- evidence IDs are unique and task progress/results/errors cannot reference unseen evidence;
- `task.result` is terminal success and `task.error` reports terminal `failed`, `cancelled`, or `rolled_back` states;
- task events after a terminal result/error are rejected;
- `task.cancel` is a request, not a terminal-state assertion;
- public trace identity is checked consistently across the fixture without inventing private tracing semantics.

## Assurance boundary

This is executable public conformance evidence, not formal verification, certification, authorization, provenance, or proof that a runtime implemented rollback correctly. In particular, a `rolled_back` status is a reported public task outcome; this suite does not certify the underlying rollback implementation.

The transcript suite and its deterministic result objects are test/conformance artifacts. They do not create a new normative wire message or change wire protocol version `0.4.0`, Rust package versioning, or the existing public schema identities.

For that reason the suite is not added to the public-contract fingerprint as a new normative contract surface in this change. Consumers can still replay the corpus directly from the repository, while the fingerprint continues to cover the canonical protocol/policy surfaces it already documents.
