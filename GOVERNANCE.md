# Governance

Glomancy Protocol uses maintainer-led governance with public, reviewable engineering decisions. The project is currently maintained by one primary maintainer; it does not claim a committee, foundation, standards body, or external steering group that does not exist.

The goal is to keep the public protocol independently usable, technically coherent, fail-closed by default, and auditable as it evolves.

## Maintainer register

The current maintainer roles and responsibilities are recorded in [`MAINTAINERS.md`](MAINTAINERS.md).

The current primary maintainer is [@charman-07](https://github.com/charman-07).

Maintainer responsibilities include:

- reviewing and merging pull requests;
- maintaining protocol compatibility and release quality;
- triaging issues and security reports;
- protecting the public/private project boundary;
- documenting meaningful protocol decisions;
- keeping executable contracts, Rust helpers, docs, and releases consistent;
- avoiding claims of adoption, certification, compatibility, or production readiness that have not been demonstrated.

## Decision model

Project decisions are made through evidence-backed GitHub Issues and pull requests.

Small editorial or implementation-neutral fixes may use the normal pull-request path.

Changes that affect public behavior are classified and reviewed under [`docs/PROTOCOL_CHANGE_PROCESS.md`](docs/PROTOCOL_CHANGE_PROCESS.md).

The process distinguishes:

- **Class 0 — editorial / non-contract**;
- **Class 1 — additive compatible**;
- **Class 2 — behavioral / compatibility-sensitive**;
- **Class 3 — breaking or security-sensitive**.

Class 2 and Class 3 changes require a protocol-change proposal before implementation. The repository provides a structured GitHub Issue form for these proposals.

## Required decision evidence

A compatibility-sensitive proposal should make the following visible before merge:

1. the concrete problem;
2. the affected public contract;
3. the proposed observable behavior;
4. compatibility impact;
5. migration requirements;
6. security and trust-boundary impact;
7. conformance/test evidence;
8. alternatives considered;
9. release/versioning implications;
10. confirmation that the public/private boundary remains intact.

A pull request must not silently redefine a materially different protocol decision from the proposal that authorized the work.

## Pull requests

Pull requests should be focused and include tests, fixtures, vectors, parity checks, or other executable evidence when observable behavior changes.

CI must pass before merge. The maintainer may request changes when a proposal:

- weakens fail-closed behavior without explicit justification;
- makes validation equivalent to authorization;
- introduces ambiguous compatibility behavior;
- adds product-specific/private runtime behavior to the neutral protocol layer;
- changes a published contract without migration or release analysis;
- creates unsupported adoption/security/certification claims.

Self-authored maintainer changes are expected to follow the same issue → branch → pull request → CI flow used for external contributions when the change affects a public contract.

## Canonical public contracts

The following machine-readable artifacts carry special authority within their defined scope:

- `registry/` — canonical mapping of public message schema IDs, message kinds, files, versions, and integrity hashes;
- `compatibility/` — canonical compatibility cases/rules for the published wire lines represented there;
- `capabilities/` — machine-readable capability-negotiation profile;
- `vectors/` — language-neutral expected outcomes for consumer conformance behavior;
- `errors/` — versioned machine-readable protocol error-code catalog.

Rust helpers, examples, prose documentation, and release notes must remain consistent with these contracts. CI parity checks should fail when supported machine-readable and code surfaces drift.

## Release authority

The primary maintainer currently creates public tags and GitHub releases after release-readiness review.

A release should satisfy the quality gates in [`docs/RELEASE_GATES.md`](docs/RELEASE_GATES.md) and the operational checklist in [`RELEASING.md`](RELEASING.md).

Project process requirements are not the same as repository-enforced controls. GitHub branch/ruleset protection should additionally require the relevant CI and pull-request flow when administrative configuration is available and verified. Until then, the project must not claim those controls are technically enforced.

## Security decisions

Sensitive vulnerability reports follow [`SECURITY.md`](SECURITY.md), not public issue discussion. Security fixes may be developed privately until disclosure is safe.

Security-sensitive remediation may temporarily bypass public proposal discussion when disclosure would create avoidable risk, but the eventual public release should contain the appropriate fix, tests, migration/release notes, and non-sensitive rationale.

## Adding maintainers

Additional maintainers may be added after sustained, high-quality public contributions and demonstrated understanding of compatibility, security, testing, documentation, and project scope.

Maintainer access is not granted solely for activity volume. Changes to maintainer status should be recorded through `MAINTAINERS.md` in a normal pull request.

## Conflicts of interest

Maintainers should disclose material conflicts that could reasonably affect technical judgment. Commercial interests must not silently weaken or redefine the public contract.

The existence of the private/commercial Glomancy product does not make this repository private infrastructure: Glomancy Protocol is intended to remain an independently usable MIT-licensed public protocol layer.

## Commercial boundary

Governance of this repository does not grant access to, ownership of, or licensing rights over private Glomancy product code.

The public repository may document abstract integration boundaries and Unreal Engine product context without publishing proprietary planner/orchestrator/provider/billing/editor-mutation/runtime implementation details.
