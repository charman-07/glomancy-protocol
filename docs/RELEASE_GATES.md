# Release Quality Gates

A tagged Glomancy Protocol release should represent a reviewed public contract snapshot, not merely a commit that builds.

This document defines the quality gates expected before a maintainer creates a public release. It complements `RELEASING.md`; it does not replace GitHub branch protection or repository rules.

## Gate 1 — Source quality

The release candidate must pass the Rust quality job, including:

- `cargo fmt --check`;
- `cargo clippy --all-targets -- -D warnings`;
- `cargo test --all-targets`;
- executable Rust examples;
- Rustdoc with warnings denied.

A formatting-only or documentation-only change does not justify ignoring a failing source-quality job on the release candidate.

## Gate 2 — Cross-platform portability

The public Rust package must pass its test suite on the supported CI matrix:

- Linux;
- Windows;
- macOS.

A release must not be described as portable beyond environments actually covered by evidence.

## Gate 3 — Repository contract integrity

The repository-contract job must pass every enabled invariant check, including as applicable:

- public/private boundary checks;
- JSON and repository consistency validation;
- schema-registry SHA-256 verification;
- Rust/JSON registry parity;
- Rust/common-schema wire-enum parity;
- protocol error-code catalog parity;
- capability-negotiation profile validation;
- language-neutral consumer-vector validation;
- independent Python consumer example;
- independent JavaScript consumer example;
- published compatibility snapshot validation;
- executable JSON Schema fixture conformance;
- public conformance CLI smoke tests;
- conformance CLI machine-readable output contract validation.

New public machine-readable contracts should normally gain an executable repository invariant rather than relying only on prose review.

## Gate 4 — Compatibility review

Before tagging, the maintainer must review changes since the previous public release for:

- wire protocol behavior;
- schema IDs, versions, content, and registry hashes;
- capability negotiation;
- approval and task-lifecycle semantics;
- error codes and categories;
- public limits;
- conformance-vector expectations;
- deprecations and removals.

If an observable contract changed, the release notes must state whether it is additive, behaviorally significant, or breaking and provide migration guidance where needed.

## Gate 5 — Security and trust-boundary review

The release candidate must be checked for changes affecting:

- fail-closed behavior;
- malformed/unknown input handling;
- version negotiation;
- schema identity;
- approval/evidence correlation;
- resource limits;
- dependency/supply-chain changes;
- accidental secrets or proprietary implementation leakage.

Protocol validation must not be presented as authentication, authorization, sandboxing, or editor permission enforcement.

Security-sensitive releases follow `SECURITY.md` and may use a private remediation process until disclosure is safe.

## Gate 6 — Documentation and adoption surface

User-visible behavior must agree across:

- README and integration documentation;
- machine-readable registries/catalogs/vectors;
- Rust public APIs/helpers;
- examples;
- CHANGELOG;
- release notes.

A release should not claim production adoption, certification, stability, support guarantees, or broad ecosystem usage without evidence.

## Gate 7 — Public/private boundary

Before release, verify that the public history does not contain:

- API keys, tokens, credentials, or private certificates;
- customer or private project data;
- private machine paths that reveal sensitive infrastructure;
- proprietary Glomancy planner/runtime/provider/billing/editor mutation implementation;
- private signing or installer infrastructure.

The public protocol may document abstract integration boundaries without publishing the private commercial implementation.

## Gate 8 — Release metadata

The release candidate must have deliberate, internally consistent metadata:

- intended Rust package version;
- intended wire protocol version;
- intended schema/catalog/vector versions;
- updated CHANGELOG/release notes;
- intended tag target commit;
- release maturity wording consistent with evidence.

Version numbers for the Rust package, wire protocol, JSON Schemas, catalogs, and conformance vectors are independent and should only change when their own contract requires it.

## Gate 9 — Tag and post-release verification

After publication:

- verify the tag resolves to the intended reviewed commit;
- verify the GitHub release is not accidentally draft/prerelease unless intended;
- verify source/archive links;
- verify CI for the tagged commit;
- verify key README/document links from the tag;
- record follow-up work as issues instead of silently rewriting a published historical contract.

## Governance note

These gates are project process requirements. Repository-level enforcement such as required status checks, pull-request-only changes, force-push blocking, and branch deletion protection should additionally be configured through GitHub rules/branch protection when administrative access permits it.

Until those controls are verified, the project must not claim that GitHub technically enforces every gate.
