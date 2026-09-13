# Security Invariants

Glomancy Protocol publishes a machine-readable catalog of core fail-closed security invariants at [`security/v1/invariants.json`](../security/v1/invariants.json).

The catalog gives security-sensitive behavior stable identifiers and connects each invariant to executable, language-neutral conformance cases. Its purpose is to make security regressions easier to review, test, and discuss across implementations.

## Assurance boundary

An invariant marked `enforced` means the public repository currently has executable vector evidence for the stated fail-closed behavior and CI verifies that the referenced evidence still exists.

It does **not** mean:

- formal verification;
- a mathematical proof that every implementation is secure;
- authentication or authorization;
- a security certification;
- penetration-test coverage;
- production adoption;
- proof that an external consumer actually runs the conformance suite.

The vector suite is regression evidence for public contract behavior. A consuming integration remains responsible for authentication, authorization, transport security, policy, sandboxing, editor/tool permissions, and safe execution.

## Stable invariant IDs

Current IDs use the form `GLM-SEC-NNN`. IDs are not silently reused for unrelated meanings.

The initial catalog covers:

| ID | Category | Invariant |
| --- | --- | --- |
| `GLM-SEC-001` | Versioning | Incompatible wire protocol lines fail closed. |
| `GLM-SEC-002` | Versioning | Negotiation selects only an exact version explicitly advertised by both peers. |
| `GLM-SEC-003` | Capability | A task may request only session-selected capabilities. |
| `GLM-SEC-004` | Approval | Approval-gated execution cannot begin before a valid approval. |
| `GLM-SEC-005` | Approval | Denied or expired approval never authorizes execution. |
| `GLM-SEC-006` | Approval | Approval decisions must correlate to the correct request and task. |
| `GLM-SEC-007` | Evidence | Referenced evidence must exist and evidence identifiers cannot be duplicated within a task lifecycle. |
| `GLM-SEC-008` | Lifecycle | A terminal task result closes the lifecycle; later events are rejected. |

The JSON catalog is authoritative for exact wording, failure mode, status, and evidence references.

## Evidence links

Each catalog entry includes one or more references of the form:

```json
{
  "area": "approval-flow",
  "case_id": "decision-after-expiry"
}
```

`area` resolves through [`vectors/v1/manifest.json`](../vectors/v1/manifest.json). `case_id` must exist in that vector file.

The validator requires every invariant to contain at least one referenced vector whose expected result is fail closed (`accepted: false` or `authorized: false`). This prevents a security invariant from being recorded only against a happy-path case.

## Validation

Run:

```bash
python3 scripts/validate_security_invariants.py
```

The validator fails when it finds, among other things:

- malformed or duplicate `GLM-SEC-*` IDs;
- gaps in the current invariant-ID sequence;
- unsupported categories, statuses, or failure modes;
- wire-version drift between the invariant catalog and consumer vectors;
- duplicate evidence references;
- unknown vector areas;
- missing vector case IDs;
- an invariant with no fail-closed evidence.

Normal repository CI and the manual Release Readiness audit run the validator.

## Public contract fingerprint

The security invariant catalog is part of the deterministic public contract fingerprint. Therefore, changing the catalog changes the aggregate public-contract SHA-256 and becomes visible in release-readiness metadata.

The fingerprint is an integrity comparison mechanism, not a signature or proof of authenticity. See [Public Contract Fingerprint](PUBLIC_CONTRACT_FINGERPRINT.md).

## Changing an invariant

A change to an invariant can alter a security-sensitive public expectation. Follow [Protocol Change Process](PROTOCOL_CHANGE_PROCESS.md) when a proposal changes what peers accept, reject, authorize, or require.

When changing the catalog:

1. explain the compatibility and security impact;
2. update/add executable vectors first or in the same change;
3. update the catalog evidence references;
4. run the invariant validator;
5. regenerate the public contract fingerprint;
6. update migration/release notes when external consumers may be affected.

Do not weaken an invariant merely to make a failing implementation pass its tests. If the intended protocol behavior is changing, make that change explicit and versioned where required.
