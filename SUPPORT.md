# Support

Glomancy Protocol is a public open-source protocol project maintained on a best-effort basis. This repository does not provide a commercial SLA, guaranteed response time, guaranteed backport policy, or certification service.

The authoritative pre-1.0 release-maintenance expectations are documented in [`docs/RELEASE_SUPPORT_POLICY.md`](docs/RELEASE_SUPPORT_POLICY.md) and mirrored for automation in `support/v1/policy.json`.

## Questions and integration help

Use GitHub Issues for reproducible protocol questions, compatibility questions, documentation gaps, and integration problems that can be discussed publicly.

Before opening an issue:

- check the README and relevant `docs/` material;
- search existing issues;
- include the Rust crate version when relevant;
- include the wire protocol version;
- include the relevant schema ID/catalog/vector version when applicable;
- provide the smallest public reproduction possible;
- remove credentials, customer data, private paths, and proprietary code.

For genuine independent implementation feedback, use the integration-feedback issue form so the project can distinguish real external evidence from maintainer-derived examples.

## Bugs

Use the bug-report issue form. For validation bugs, include whether the payload was expected to pass or fail and identify the relevant schema, registry entry, conformance case, or Rust helper.

A report is more actionable when it includes an executable or minimal machine-readable reproduction.

## Feature and protocol proposals

Use the feature-request form for ordinary feature ideas that do not redefine a public contract.

For compatibility-sensitive changes to wire behavior, schema identity, capability negotiation, approvals, task lifecycle, evidence rules, public limits, error contracts, or fail-closed semantics, use the dedicated **Protocol change proposal** form and follow `docs/PROTOCOL_CHANGE_PROCESS.md`.

Product-specific features may be declined when they do not belong in a transport-neutral protocol layer.

## Supported release context

The project is pre-1.0 and currently has a small public release history. The latest tagged release is the primary stable reference point for external consumers, while `main` represents active development and may contain unreleased changes documented under `CHANGELOG.md`.

The current supported public release line, security-fix posture, backport posture, and end-of-support transition rules are defined in `docs/RELEASE_SUPPORT_POLICY.md`. The machine-readable policy is validated against real published compatibility snapshots so active development on `main` is not confused with a published supported release.

Questions about older public tags are welcome, but the project does not promise indefinite maintenance or automatic backports for every historical pre-1.0 release. Security/correctness fixes and backports are evaluated case by case based on impact and feasibility.

Consumers that require reproducibility should pin a specific release tag and verify the public registries/hashes described in `docs/ADOPTION_GUIDE.md`.

## Security vulnerabilities

Do **not** open a public issue for a vulnerability that could put users or integrations at risk. Follow `SECURITY.md` and use GitHub's private vulnerability-reporting/security-advisory path when available.

Do not include exploit details in a protocol-change proposal merely to satisfy normal governance process.

## What public support does not mean

A maintainer response, passing conformance test, or accepted integration report does not certify an external product as secure, production-ready, authorized, or officially endorsed.

The protocol does not provide authentication, authorization, transport encryption, sandboxing, editor permissions, or provider-credential security by itself.

## Commercial Glomancy support

This repository covers only the open Glomancy Protocol project. It is not a support channel for the separate commercial/private Glomancy product, private runtime/editor implementation, provider infrastructure, billing systems, or customer-specific deployments.
