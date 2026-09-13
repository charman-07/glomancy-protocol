# Governance

Glomancy Protocol uses lightweight maintainer-led governance while the project is young. The goal is to keep technical decisions public, reviewable, and focused on interoperability and safety.

## Maintainer

The current primary maintainer is [@charman-07](https://github.com/charman-07).

The maintainer is responsible for:

- reviewing and merging pull requests;
- maintaining protocol compatibility and release quality;
- triaging issues and security reports;
- keeping the public/private project boundary clean;
- documenting meaningful protocol decisions;
- avoiding claims of adoption or compatibility that have not been demonstrated.

## Decision process

Small, backward-compatible fixes can be handled through normal pull requests.

Changes that affect wire behavior, compatibility, schema identifiers, risk/approval semantics, or public error codes should begin with a GitHub Issue that describes:

1. the problem being solved;
2. the proposed contract change;
3. compatibility and migration impact;
4. security implications;
5. alternatives considered.

For pre-1.0 releases, breaking changes are possible, but they must be explicit and documented. Silent weakening of fail-closed behavior is not acceptable.

## Pull requests

Pull requests should be focused and include tests or fixtures when they alter observable behavior. CI must pass before merge. The maintainer may request changes when a proposal adds product-specific behavior, weakens validation, or expands the protocol beyond its transport-neutral scope.

## Compatibility authority

The machine-readable compatibility matrix under `compatibility/` is the canonical source for negotiation rules. Documentation and Rust helpers should remain consistent with that matrix.

The schema registry under `registry/` is the canonical mapping of public schema IDs to files and integrity hashes.

## Security decisions

Sensitive vulnerability reports should follow `SECURITY.md`, not public issue discussion. Security fixes may be developed privately until disclosure is safe.

## Adding maintainers

Additional maintainers may be added after sustained, high-quality public contributions and demonstrated understanding of the project's compatibility and security principles. Maintainer access is not granted solely for activity volume.

## Commercial boundary

This repository is independently usable open-source protocol infrastructure. Governance of this repository does not grant access to, ownership of, or licensing rights over private Glomancy product code.
