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
- a privacy-sensitive integration may forbid `memory` while allowing project-local sources.

Those are integration policies, not universal Glomancy Protocol rules.

The public context-policy tool keeps that distinction explicit:

```bash
python3 scripts/glomancy_context_policy.py path/to/session.json \
  --expect-source project \
  --expect-source asset \
  --forbid-source web
```

Machine-readable output:

```bash
python3 scripts/glomancy_context_policy.py path/to/session.json \
  --expect-source project \
  --forbid-source web \
  --json
```

The tool returns:

- exit `0` when the complete public session is conforming and the caller policy passes;
- exit `2` when the session is non-conforming or the context policy fails;
- exit `3` when the input or policy configuration cannot be evaluated.

Before any context policy is checked, the complete transcript is validated through the canonical public session validator. Context policy is therefore not a shortcut around schema, registry, capability, approval, evidence, or lifecycle validation.

## Deterministic context summary

JSON mode publishes only a bounded structural summary:

- `expected_sources`;
- `forbidden_sources`;
- `observed_source_counts`;
- `context_ref_count`;
- `revisioned_context_ref_count`.

The context-policy output intentionally does **not** echo context URIs. The original transcript already carries those public references; repeating them in derived CI artifacts would unnecessarily multiply project/file/asset identifiers.

`revisioned_context_ref_count` reports only the presence of revision metadata. It does not prove that a revision is fresh, immutable, authentic, content-addressed, or still available.

## Fail-closed policy behavior

Allowed values are read from the canonical `common.schema.json` `source_ref.source_type` enum.

The tool rejects configuration when:

- an expected or forbidden source type is not a registered public source category;
- the same expectation is repeated;
- the same prohibition is repeated;
- a source category is both expected and forbidden.

After a session passes public conformance:

- a missing required source produces `context-source-expectation-missing`;
- an observed forbidden source produces `context-source-forbidden`.

No source category is globally required or globally forbidden by this tooling. In particular, `web` and `memory` are not inherently trusted or untrusted; the caller chooses policy for its environment.

## How this relates to Glomancy

Glomancy's product architecture increasingly treats context as a first-class input to planning and verification rather than as unstructured prompt text.

At a high level, the product can combine live project/editor state, selected project objects/assets, retained project knowledge, generated artifacts, and external research before planning or execution. Product policy can prefer current local project/runtime evidence over stale memory or outside research.

Those product behaviors are **not** standardized here. The public protocol exposes only the stable interoperability boundary needed to describe context references and to test caller-defined policy around those references.

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

A future product may derive one or more ordinary public `project`, `asset`, `file`, `memory`, or `artifact` references from those systems without requiring the private implementation itself to become public.

If the public ecosystem later demonstrates a real interoperability need that cannot be represented safely by existing `source_ref` categories, any new normative field or source category should be versioned deliberately and tested for backward compatibility. The protocol should not add fields merely to mirror one private product's internal object graph.

## Assurance boundary

Passing context-policy conformance means only that:

1. the transcript first passed public session conformance; and
2. its public `task.submit.context_refs` categories satisfied the caller's explicit expect/forbid policy.

It does **not** prove:

- that referenced content was fetched;
- that a model or runtime actually consumed it;
- that the referenced content is true or current;
- that `revision` identifies an immutable snapshot;
- that a URI belongs to the intended project or user;
- that context selection was complete or optimal;
- provenance, authentication, authorization, confidentiality, or certification;
- correctness of private retrieval, ranking, caching, RAG, semantic-map, or digital-twin implementations.

Those responsibilities remain outside this public conformance layer.

## Public/private boundary

The following remain private implementation details and are not required for protocol compatibility:

- editor-thread snapshot/caching implementation;
- relevance-selection and ranking algorithms;
- proprietary project-memory or RAG implementation;
- provider prompt construction;
- planner/orchestrator internals;
- private trust/authentication infrastructure;
- credentials, secrets, customer data, and private project paths;
- commercial runtime logic.

The public contract remains transport-neutral, provider-neutral, editor-agnostic, versioned, auditable, and fail-closed where explicit conformance assertions are requested.
