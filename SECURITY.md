# Security Policy

Glomancy Protocol sits at a trust boundary between AI-originated instructions and tooling that may eventually act on them. Security reports that affect validation, compatibility, approvals, evidence, or fail-closed behavior are especially important.

## Supported code

The current public release/security support posture is defined in [`docs/RELEASE_SUPPORT_POLICY.md`](docs/RELEASE_SUPPORT_POLICY.md) and mirrored in `support/v1/policy.json`.

Security fixes are developed against the current codebase and are included in an appropriate tagged release when a fix is ready. Because the project is pre-1.0, the currently supported published release line receives security fixes on a best-effort basis; backports to historical tags or superseded lines are not guaranteed unless release notes explicitly say otherwise.

The project does not promise a fixed vulnerability-response SLA, remediation deadline, LTS window, or automatic backport policy.

## Reporting a vulnerability

Please **do not** publish sensitive vulnerability details in a public issue, pull request, discussion, or fixture.

Use GitHub's private vulnerability reporting / security advisory flow for this repository when available. Include:

- affected commit, protocol version, or schema ID;
- a concise description of the impact;
- the smallest safe reproduction you can provide;
- whether the issue can bypass validation, compatibility, approval, evidence, or resource-limit expectations;
- suggested remediation, if known.

Do not include unrelated credentials, customer data, private infrastructure, or proprietary source code in a report.

## Scope

This policy covers the public Glomancy Protocol repository, including:

- Rust protocol types and validation helpers;
- JSON Schemas;
- schema registry and integrity metadata;
- examples and conformance fixtures;
- compatibility rules and cases;
- repository validation and CI logic.

The separate commercial Glomancy product is outside this repository's disclosure scope. This policy does not grant access to private systems or source code.

## Security properties we care about

Examples of useful reports include:

- unknown input being accepted instead of rejected;
- schema-validation bypasses;
- ambiguous or unsafe version negotiation;
- approval/evidence invariants that can be bypassed;
- registry/hash inconsistencies;
- malformed input that causes unexpected behavior;
- unsafe defaults or unexpectedly unbounded processing in the public protocol layer;
- compromised or suspicious dependency/workflow updates.

See `docs/SECURITY_MODEL.md` for the threat model and integration responsibilities. See `docs/SUPPLY_CHAIN.md` for dependency review, update cadence, immutable Action pinning, and CI expectations.

## Supply-chain changes

Dependency, package-tooling, and GitHub Actions updates are treated as security-relevant maintenance. Automated update pull requests are reviewed rather than auto-approved, and the complete applicable CI suite must remain green before merge.

The project does not currently claim signed releases, formal SLSA compliance, or bit-for-bit reproducible builds. Those properties should only be documented if they are actually implemented and verified.

## Secrets and sensitive data

Contributions containing credentials, API keys, access tokens, private certificates, signing material, customer data, or private infrastructure details will be rejected and removed from public history when necessary.

## Disclosure

We prefer coordinated disclosure. Security details should become public only after a fix or mitigation is available when practical. Credit may be given to reporters who want it, subject to their preference and the safety of the disclosure.
