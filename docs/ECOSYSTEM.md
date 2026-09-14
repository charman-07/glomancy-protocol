# Ecosystem and Implementations

This page separates **repository-maintained examples** from **genuine external implementations and integrations**.

The distinction matters: Glomancy Protocol does not treat its own examples, tests, or maintainer-authored consumers as evidence of third-party adoption.

## Repository-maintained implementations

These are maintained inside this repository and exist to demonstrate interoperability and conformance behavior:

| Language / surface | Location | Status |
| --- | --- | --- |
| Rust reference consumer | `examples/reference_consumer.rs` | Maintained in-repo |
| Python independent consumer | `examples/consumers/python/` | Maintained in-repo |
| JavaScript independent consumer | `examples/consumers/javascript/` | Maintained in-repo |
| Public conformance CLI | `scripts/glomancy_conformance.py` | Maintained in-repo |

These examples are useful implementation references, but they are **not external adoption**.

## External implementations and integrations

No external implementation is listed here unless its existence can be verified independently.

A qualifying entry may be:

- a public repository implementing Glomancy Protocol in another language;
- an editor/plugin/tool integration using pinned public contracts;
- a public CI/conformance integration maintained outside this repository;
- a research prototype or OSS project that implements a meaningful protocol subset and documents the supported baseline.

### Listing requirements

A proposed listing should include:

1. a public URL that maintainers can inspect;
2. implementation language/runtime;
3. Glomancy Protocol tag/commit/wire/schema/vector baseline used;
4. which protocol areas are implemented;
5. the relationship of the submitter to the external project;
6. any important limitations or experimental status.

A listing does **not** imply endorsement, certification, security review, compatibility guarantee, production deployment, or commercial relationship.

## How to add an external implementation

If you maintain a real public implementation:

1. open the repository's **Integration feedback** issue form;
2. include the public implementation URL and exact baseline;
3. describe which vector/conformance checks you ran;
4. after maintainers can verify the public evidence, open a small PR adding the entry here or ask a maintainer to do so.

Private implementations may still provide useful integration feedback, but they will not be listed as independently verifiable ecosystem projects unless there is enough public evidence to support the claim.

## What counts as useful feedback even without a public implementation?

You do not need to publish a full project to help the protocol improve. Useful feedback includes:

- a vector case that was ambiguous to implement;
- a schema field whose semantics were unclear;
- a compatibility edge case discovered in another language;
- a CI/conformance friction point;
- a security boundary that was easy to misunderstand;
- a missing error or lifecycle case found during implementation.

Use the **Integration feedback** form for implementation experience and the **Integration question** form for a question before or during integration.

## Maintainer policy

Maintainers should never add fabricated organizations, repositories, contributors, downloads, deployments, stars, forks, benchmarks, or production claims to this page.

If an external project stops being public or the evidence becomes stale, the listing should be updated or removed rather than preserved as historical marketing proof.

The goal is a small, verifiable ecosystem record that becomes more credible as real independent implementations appear.
