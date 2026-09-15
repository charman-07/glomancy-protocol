# Public context model and conformance

Glomancy Protocol represents task context as bounded, typed references rather than embedding a private retrieval engine into the wire contract.

This separation is intentional. A product can evolve its editor snapshotting, caching, relevance ranking, retrieval, knowledge graph, memory, or research implementation without forcing every protocol consumer to reproduce those internal algorithms.

## What the public protocol models today

`task.submit.payload.context_refs` is an array of public `source_ref` objects. Each reference has:

- `source_type` — the public category of the referenced context;
- `uri` — a schema-valid URI identifying the reference in the producer's public context namespace;
- optional `revision` — caller/producer metadata that may identify a snapshot, revision, version, or other stable reference point.

The current public source categories are:

| Source type | Public meaning |
| --- | --- |
| `project` | logical project/workspace context |
| `asset` | an asset or editor/tool object represented as a reference |
| `file` | a file-like source |
| `memory` | retained knowledge or memory represented as a source |
| `artifact` | an artifact produced or consumed by a workflow |
| `web` | external web/research context |

These categories identify **what kind of source was referenced**. They do not prescribe how the source was selected, fetched, ranked, cached, summarized, embedded, or supplied to a model/runtime.

## Why context has its own conformance surface

A complete session can be valid at the wire/lifecycle level while still violating an integration's local context policy.

Examples:

- a code-editing integration may require both `project` and `file` context;
- an editor workflow may require `project` plus selected `asset` context;
- an offline or high-control environment may forbid `web` context;
- a privacy-sensitive integration may forbid `memory` while allowing project-local sources;
- an integration that relies on stable project/editor snapshots may require revision metadata on `project` or `asset` references.

Those are integration policies, not universal Glomancy Protocol rules.

The public context-policy tool keeps that distinction explicit:

```bash
python3 scripts/glomancy_context_policy.py path/to/session.json \
  --expect-source project \
  --expect-source asset \
  --forbid-source web
```

An integration may also require revision metadata for selected source categories:

```bash
python3 scripts/glomancy_context_policy.py path/to/session.json \
  --require-revision-source project \
  --require-revision-source asset
```

`--require-revision-source TYPE` means:

1. at least one public context reference of `TYPE` must be present; and
2. every observed reference of that type must carry a non-empty `revision` string.

It does **not** assign meaning to that string beyond its presence. The producer/caller remains responsible for deciding whether a revision is a changelist, content version, editor snapshot identifier, database version, timestamp-like token, or another stable reference label.

Machine-readable output:

```bash
python3 scripts/glomancy_context_policy.py path/to/session.json \
  --expect-source project \
  --require-revision-source project \
  --forbid-source web \
  --json
```

The tool returns:

- exit `0` when the complete public session is conforming and the caller policy passes;
- exit `2` when the session is non-conforming or the context policy fails;
- exit `3` when the input or policy configuration cannot be evaluated.

Before any context policy is checked, the complete transcript is validated through the canonical public session validator. Context policy is therefore not a shortcut around schema, registry, capability, approval, evidence, or lifecycle validation.

## Portable Context Snapshot Descriptor

The optional descriptor at `context/v1/snapshot.schema.json` is a **non-wire tooling artifact** for describing the bounded public context observed at a caller-defined snapshot boundary.

It contains only:

- `snapshot_format_version`;
- `snapshot_id`;
- `captured_at`;
- `sources`, using the existing public `source_ref` contract.

Example:

```json
{
  "snapshot_format_version": "1.0.0",
  "snapshot_id": "77777777-7777-4777-8777-777777777777",
  "captured_at": "2026-09-15T10:00:05Z",
  "sources": [
    {
      "source_type": "project",
      "uri": "glomancy://project/example",
      "revision": "project-r1"
    }
  ]
}
```

Validate a descriptor with:

```bash
python3 scripts/glomancy_context_snapshot.py validate \
  context/v1/examples/context-snapshot.json
```

Compare a descriptor with a complete public session:

```bash
python3 scripts/glomancy_context_snapshot.py compare \
  path/to/snapshot.json \
  path/to/session.json \
  --json
```

Comparison is deliberately structural and fail-closed:

1. the snapshot descriptor must satisfy its Draft 2020-12 schema;
2. the full transcript must satisfy canonical public session conformance;
3. every `task.submit.context_refs` entry must exist in the snapshot by exact public `source_type + uri` identity;
4. when the task context reference carries `revision`, the snapshot reference must carry the same revision;
5. extra sources in the descriptor are allowed and reported as a count, because a producer may capture a broader bounded snapshot than one task ultimately references.

Stable comparison failures include:

- `context-ref-not-in-snapshot`;
- `context-revision-mismatch`;
- `session-conformance-failed`.

The descriptor validator also rejects ambiguous duplicate source identities where two descriptor entries use the same `source_type + uri`, even if their revision labels differ.

Machine-readable snapshot output intentionally does **not** echo context URIs or revision values. It reports bounded structural information such as source counts, source-type counts, task context counts, matched counts, and extra descriptor-source counts.

## Deterministic context summary

Context-policy JSON mode publishes only a bounded structural summary:

- `expected_sources`;
- `forbidden_sources`;
- `revision_required_sources`;
- `observed_source_counts`;
- `observed_revisioned_source_counts`;
- `context_ref_count`;
- `revisioned_context_ref_count`.

The context-policy output intentionally does **not** echo context URIs or revision values. The original transcript already carries those public references; repeating them in derived CI artifacts would unnecessarily multiply project/file/asset identifiers and revision labels.

`observed_revisioned_source_counts` reports how many references of each public source category carry non-empty revision metadata. `revisioned_context_ref_count` is the total across all categories.

These counts establish only metadata coverage. They do not prove that a revision is fresh, immutable, authentic, content-addressed, monotonically increasing, correctly bound to the URI, or still available.

## Fail-closed policy behavior

Allowed values are read from the canonical `common.schema.json` `source_ref.source_type` enum.

The tool rejects configuration when:

- an expected, forbidden, or revision-required source type is not a registered public source category;
- the same expectation is repeated;
- the same prohibition is repeated;
- the same revision requirement is repeated;
- a source category is both expected and forbidden;
- a source category is both revision-required and forbidden.

After a session passes public conformance:

- a missing required source produces `context-source-expectation-missing`;
- an observed forbidden source produces `context-source-forbidden`;
- a revision-required source that is absent or not fully revisioned produces `context-source-revision-missing`.

No source category is globally required, globally forbidden, or globally required to have revision metadata by this tooling. In particular, `web` and `memory` are not inherently trusted or untrusted; the caller chooses policy for its environment.

## How this relates to Glomancy

Glomancy's product architecture increasingly treats context as a first-class input to planning and verification rather than as unstructured prompt text.

At a high level, the product can combine live project/editor state, selected project objects/assets, retained project knowledge, generated artifacts, and external research before planning or execution. Product policy may distinguish newer live/local state from older retained knowledge and may carry snapshot/revision identity internally so later planning or verification can reason about which state was observed.

Those product behaviors are **not** standardized here. The public protocol exposes only the stable interoperability boundary needed to describe context references and to test caller-defined policy around source categories and revision-metadata coverage.

The Context Snapshot Descriptor is the same kind of boundary: it gives external tooling a small portable representation of **which public references belonged to one observed snapshot**, without exposing how the product assembled that snapshot.

A public revision requirement therefore does not encode Glomancy's private rule for deciding which context wins when sources disagree. It only lets an integration require that selected public references carry a producer-defined revision label.

## Future evolution

The public context model is deliberately small enough to survive richer Glomancy capabilities.

Non-normative future directions may include integrations that internally build or use:

- project digital twins;
- semantic project maps;
- custom project knowledge bases;
- dependency/asset relationship indexes;
- measured profiling context;
- automated playtest observations;
- build/package diagnostic context;
- bounded self-repair evidence;
- controlled specialist-agent context views.

A private digital twin or semantic map may internally contain thousands of nodes, dependency edges, editor objects, confidence values, timestamps, cached observations, or product-specific knowledge. The public descriptor does **not** mirror that object graph. A producer can instead expose the bounded public references selected from that richer internal representation for one task/snapshot.

This preserves an important architectural property: Glomancy can evolve toward a much richer project model while the interoperability surface remains small, versioned, provider-neutral, and independently testable.

If the public ecosystem later demonstrates a real interoperability need that cannot be represented safely by existing `source_ref` categories, optional revision labels, and the descriptor boundary, any new normative field or source category should be versioned deliberately and tested for backward compatibility. The protocol should not add fields merely to mirror one private product's internal object graph.

## Assurance boundary

Passing context-policy conformance means only that:

1. the transcript first passed public session conformance; and
2. its public `task.submit.context_refs` categories satisfied the caller's explicit expect/forbid policy; and
3. any caller-selected revision requirements had complete non-empty `revision` coverage for those source categories.

Passing Context Snapshot comparison means only that the task's public context references are structurally represented by the caller-supplied descriptor under the documented identity/revision rules.

Neither result proves:

- that referenced content was fetched;
- that a model or runtime actually consumed it;
- that the referenced content is true or current;
- that `revision` identifies an immutable or authentic snapshot;
- that two equal revision strings identify equal content;
- that a higher/newer-looking revision is actually fresher;
- that `captured_at` proves when a live editor/runtime observation occurred;
- that the descriptor was produced by an intended or authenticated runtime;
- that a URI belongs to the intended project or user;
- that context selection was complete or optimal;
- provenance, authentication, authorization, confidentiality, or certification;
- correctness of private retrieval, ranking, caching, RAG, semantic-map, digital-twin, or snapshot-construction implementations.

Those responsibilities remain outside this public conformance layer.

## Public/private boundary

The following remain private implementation details and are not required for protocol compatibility:

- editor-thread snapshot/caching implementation;
- live-state precedence and conflict-resolution policy;
- relevance-selection and ranking algorithms;
- proprietary project-memory or RAG implementation;
- semantic-map and project-digital-twin object graphs;
- provider prompt construction;
- planner/orchestrator internals;
- private trust/authentication infrastructure;
- credentials, secrets, customer data, and private project paths;
- commercial runtime logic.

The public contract remains transport-neutral, provider-neutral, editor-agnostic, versioned, auditable, and fail-closed where explicit conformance assertions are requested.
