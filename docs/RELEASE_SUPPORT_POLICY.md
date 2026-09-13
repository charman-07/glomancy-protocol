# Release and Security Support Policy

Glomancy Protocol is currently a pre-1.0 open-source project. This policy defines the support expectations that public consumers may rely on today without implying long-term-support, service-level, certification, or enterprise-support guarantees that the project does not provide.

The machine-readable companion to this document is `support/v1/policy.json`.

## Current support model

The public project is maintained on a **best-effort** basis.

At present:

- the current supported Rust release line is `0.1.x`;
- the latest published public release in that line is `v0.1.0`;
- the corresponding wire protocol line is `0.4.x`;
- the published schema line represented by the release snapshot is `1.0.0`;
- bug fixes and security fixes are considered on a best-effort basis;
- backports to older patch releases are not guaranteed;
- there is no fixed support window measured in days or months;
- there is no response-time SLA;
- there is no LTS program.

These statements describe the public OSS repository only. They do not define support terms for the separate private/commercial Glomancy product.

## What “supported” means

A release line marked `current` is the line maintainers expect new public integrations to target unless a newer release or migration notice says otherwise.

For the current line, maintainers may:

- investigate reproducible public protocol defects;
- fix validation, compatibility, schema, conformance, or documentation bugs;
- address responsibly reported security issues;
- publish a new patch/minor release when a fix warrants one;
- provide migration guidance when contract behavior changes.

Support does not mean that every issue will receive a patch, that every environment is covered, or that a fix will be backported to every historical release.

## Security fixes

Security reports must follow `SECURITY.md` and should be handled privately when public disclosure could put consumers at risk.

For supported release lines, security fixes are best-effort and prioritized according to practical impact, exploitability, correctness risk, and the safety of maintaining older behavior.

A security-sensitive correction may require:

- a new Rust package release;
- a new wire protocol line;
- a new schema ID/version;
- a capability or error-contract change;
- shortened or skipped deprecation periods when retaining old behavior would be unsafe.

The project does not promise a fixed acknowledgement, remediation, or disclosure timeline.

## Backports

Backports are **not guaranteed** before 1.0.

When a fix is small, safe, and clearly isolated, maintainers may choose to backport it to a still-supported release line. When a fix depends on newer protocol semantics or when supporting two behaviors would increase security/correctness risk, consumers may instead be required to upgrade.

A backport decision should be documented in the relevant issue, security advisory, changelog, or release notes where disclosure is safe.

## End of support

A currently supported release line may move to end-of-support when a newer incompatible line becomes the recommended target or when maintaining the old line is no longer practical or safe.

Before a normal planned transition, maintainers should:

1. announce the new supported line in release notes and this policy;
2. provide migration guidance for observable contract changes;
3. update `support/v1/policy.json`;
4. update compatibility snapshots/conformance data where applicable;
5. avoid silently reclassifying old protocol behavior as supported.

Security emergencies may require a faster transition.

An end-of-support line should not be interpreted as automatically insecure; it means the project no longer commits even on a best-effort basis to maintaining that line.

## Version relationships

Rust package, wire protocol, JSON Schema, capability-profile, conformance-vector, error-catalog, and support-policy versions are separate contracts and may move independently.

A Rust package release can change without a wire-version change. Conversely, a wire or schema change may require coordinated updates across multiple public surfaces. Consumers should use the registry, compatibility data, release snapshots, and machine-readable support policy rather than infer compatibility from a single version number.

## Machine-readable policy

`support/v1/policy.json` records the public support state in a form that automation can consume.

Repository CI validates that the current supported release entry agrees with:

- the published compatibility snapshot for that release;
- the current Rust package release line;
- the current wire protocol line;
- the declared schema line;
- the project’s intentionally non-SLA/non-LTS pre-1.0 stance.

A syntactically valid policy file is not a contract beyond what is documented here. The repository history and published release notes remain important evidence for transitions.

## What this policy does not promise

This policy does not promise:

- production-readiness certification;
- commercial support;
- uptime or response-time SLAs;
- fixed vulnerability remediation deadlines;
- long-term-support releases;
- indefinite maintenance of pre-1.0 lines;
- guaranteed backports;
- compatibility across incompatible pre-1.0 wire minor lines;
- support for private Glomancy runtime/editor/provider/billing implementation details.

Stronger guarantees should only be introduced when the project has the maintainer capacity and real integration evidence to sustain them.

## Related documents

- `SECURITY.md` — vulnerability reporting and disclosure guidance.
- `SUPPORT.md` — public questions and integration-support channels.
- `RELEASING.md` — maintainer release workflow.
- `docs/RELEASE_GATES.md` — release quality requirements.
- `docs/DEPRECATION_POLICY.md` — pre-1.0 contract evolution and removal policy.
- `docs/COMPATIBILITY.md` — wire compatibility semantics.
