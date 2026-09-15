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
6. Only after the public session itself is accepted may caller-supplied replay assertions such as sender-instance or project-context expectations be evaluated.

A schema-valid message is therefore not automatically a valid session event, and a valid public session does not automatically satisfy an integration's out-of-band rendezvous or project expectations.

Run the repository suite with:

```bash
python3 scripts/validate_session_transcript_suite.py
```

The command emits one deterministic JSON object per case and a final summary. Rejections include a stable reason plus the failing message index and diagnostic detail when applicable, making CI failures actionable without changing the wire protocol.

## Replay one complete transcript

External integrations can validate one complete transcript through the canonical public conformance CLI:

```bash
python3 scripts/glomancy_conformance.py session path/to/session.json
```

For machine-readable output:

```bash
python3 scripts/glomancy_conformance.py session path/to/session.json --json
```

The command preserves the public CLI exit-code model:

- `0` — the transcript satisfies public session conformance and any explicitly requested replay assertions;
- `2` — a message/session rule or explicit replay assertion fails;
- `3` — the transcript file or CLI configuration cannot be evaluated.

The JSON result includes the terminal status, selected version/capabilities, evidence count, stable rejection reason/index/detail, observed sender instances, and observed project context URIs.

## Optional sender-instance pinning

An integration may already know a peer instance identity from a rendezvous, launcher, process boundary, test harness, or another out-of-band mechanism. It can ask the replay CLI to require that messages from a component use that expected public `sender.instance_id`:

```bash
python3 scripts/glomancy_conformance.py session path/to/session.json \
  --expect-sender bridge=bridge-session \
  --expect-sender desktop=desktop-session \
  --json
```

`--expect-sender` is repeatable and uses `component=instance_id`.

This is deliberately an **explicit conformance-harness assertion**, not an implicit protocol topology rule. The protocol does not assume there can only be one instance of a component category in every session. If no sender expectation is supplied, replay does not invent one.

Sender pinning also is **not** authentication, authorization, credential validation, provenance, a cryptographic identity proof, or proof that a process is the intended runtime. It only compares caller-provided expectations with the public sender identity already present in the replayed envelopes.

## Optional project-context binding

A consumer may also know which logical project a captured or generated session is supposed to operate on. The existing `task.submit.payload.context_refs` contract already supports public context references with `source_type: "project"` and a schema-valid URI.

Replay can require an exact project URI with:

```bash
python3 scripts/glomancy_conformance.py session path/to/session.json \
  --expect-project glomancy://project/example \
  --json
```

When `--expect-project` is provided, the transcript must first pass normal schema and session conformance. The replay harness then inspects project context references carried by `task.submit`:

- if no project context URI is present, replay rejects with `project-expectation-missing`;
- if project context exists but none exactly matches the caller-provided URI, replay rejects with `project-expectation-mismatch`;
- if the expected URI is malformed, the command returns configuration exit code `3` before treating it as a conformance assertion.

This does **not** standardize how a product derives a project ID, canonicalizes a filesystem path, discovers a project, authenticates a process, or proves ownership/provenance. The caller chooses the schema-valid URI it can bind consistently. No private project-ID derivation or runtime rendezvous mechanism is part of this public conformance feature.

`--expect-sender` and `--expect-project` may be used together when an integration wants to assert both a known peer instance and a known project context.

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

This is executable public conformance evidence, not formal verification, certification, authorization, provenance, authentication, or proof that a runtime implemented rollback correctly. In particular, a `rolled_back` status is a reported public task outcome; this suite does not certify the underlying rollback implementation.

The transcript suite, replay CLI, sender expectations, project expectations, and deterministic result objects are test/conformance artifacts. They do not create a new normative wire message or change wire protocol version `0.4.0`, Rust package versioning, or the existing public schema identities.

The transcript corpus itself remains outside the public-contract fingerprint as a test/conformance artifact. The canonical CLI JSON output schema remains fingerprinted because it is a published tooling contract. Consumers should pin a release or exact commit when relying on a particular replay/output shape.
