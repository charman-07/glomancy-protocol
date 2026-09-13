# Maintainers

This file records the public maintenance roles for Glomancy Protocol. It is intentionally factual: the project currently has one primary maintainer and does not claim a committee, foundation, steering group, or external governance body that does not exist.

## Current maintainers

| GitHub | Role | Scope |
| --- | --- | --- |
| [@charman-07](https://github.com/charman-07) | Primary maintainer | Repository governance, protocol compatibility, releases, issue/PR triage, public/private boundary, security coordination |

## Maintainer responsibilities

A maintainer is expected to protect the public protocol contract rather than optimize for activity volume. Responsibilities include:

- reviewing protocol, schema, compatibility, capability, approval, evidence, and error-contract changes;
- requiring tests, fixtures, vectors, or other executable evidence for observable behavior changes;
- preserving fail-closed behavior unless a reviewed protocol change explicitly replaces it;
- keeping machine-readable contracts, Rust helpers, documentation, examples, and release notes consistent;
- ensuring public releases pass the documented release gates;
- triaging security reports through the private disclosure path in `SECURITY.md`;
- keeping proprietary Glomancy implementation details, credentials, customer data, signing material, and private infrastructure out of the public repository;
- avoiding unsupported claims about adoption, compatibility, production use, certification, or security guarantees.

## Review expectations

The current primary maintainer may merge changes after the applicable public CI and review requirements are satisfied. Self-authored changes are still expected to use the same issue → branch → pull request → CI flow used for external contributions.

For changes that affect a public contract, the proposal should identify:

1. the contract surface being changed;
2. compatibility and migration impact;
3. security implications;
4. conformance/test changes;
5. release-note implications;
6. alternatives considered.

The formal process is documented in `docs/PROTOCOL_CHANGE_PROCESS.md`.

## Adding maintainers

Maintainer access may be offered after sustained, high-quality public contributions that demonstrate judgment across compatibility, security, testing, documentation, and project scope. Activity count alone is not sufficient.

Signals that may support adding a maintainer include:

- repeated technically sound reviews or contributions;
- correct handling of backward compatibility and migration concerns;
- evidence of understanding fail-closed and authorization boundaries;
- reliable follow-through on CI, fixtures, docs, and release implications;
- constructive participation in issue and proposal discussions.

Adding a maintainer should be recorded in this file through a normal pull request.

## Inactive maintainers

If additional maintainers are added in the future, an inactive maintainer may voluntarily step down or be moved to an emeritus/non-merge role after a documented public governance change. Access should reflect current responsibility, not historical status.

## Conflicts of interest

A maintainer should disclose a material conflict when reviewing a change where personal, employer, customer, or commercial interests could reasonably affect technical judgment.

The existence of the private/commercial Glomancy product is not itself a conflict: this repository intentionally defines an independently usable public protocol layer. The public/private boundary must remain explicit, and proprietary product needs must not silently weaken or redefine the public contract.

## Security exceptions

Security-sensitive work may temporarily occur outside normal public discussion when early disclosure would create avoidable risk. Once disclosure is safe, the public repository should receive the appropriate fix, tests, release notes, and non-sensitive rationale.

## No service-level commitment

Maintainer status does not create a commercial support agreement or SLA for this MIT-licensed repository. Public support expectations are documented in `SUPPORT.md`.
