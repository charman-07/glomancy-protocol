# Public Contract Fingerprint

Glomancy Protocol publishes a deterministic SHA-256 fingerprint for a small set of canonical public contract surfaces.

The goal is simple: a consumer, maintainer, or release audit should be able to answer **“does this ref expose the same reviewed public contract set?”** without comparing each file manually.

This fingerprint is **integrity metadata only**. It is not a digital signature, authenticity proof, provenance statement, authorization decision, certification, endorsement, or guarantee that an integration is secure.

## Canonical contract set

`contracts/v1/fingerprint.json` covers exactly these public files:

- `registry/v1/manifest.json` — schema registry and schema hashes;
- `compatibility/v1/compatibility-matrix.json` — wire compatibility rules;
- `capabilities/v1/profile.json` — capability negotiation profile;
- `vectors/v1/manifest.json` — language-neutral consumer-vector suite manifest;
- `errors/v1/catalog.json` — public protocol error-code catalog;
- `support/v1/policy.json` — public release/security support policy;
- `compatibility/snapshots/manifest.json` — published release compatibility snapshots;
- `conformance/v1/cli-output.schema.json` — machine-readable conformance CLI output contract.

The set is intentionally explicit. Adding or removing a canonical surface requires updating the fingerprint tooling and reviewing the contract impact rather than silently changing the meaning of the aggregate hash.

## Per-file digest

Each entry records the lowercase hexadecimal SHA-256 digest of the exact file bytes stored in the repository.

No JSON reformatting, semantic normalization, key sorting, or line-ending conversion is performed before hashing. The tracked repository bytes are the input.

## Aggregate algorithm

The aggregate fingerprint is deterministic and independent of manifest entry order.

1. Sort entries lexicographically by repository-relative `path`.
2. For each entry, create this UTF-8 record:

```text
<path>\t<sha256>\n
```

3. Concatenate the records with no additional separators or prefix.
4. Compute SHA-256 over the resulting UTF-8 bytes.
5. Store the lowercase hexadecimal digest as `aggregate_sha256`.

The exact algorithm description is also stored in the machine-readable manifest and checked by CI.

## Verify a checkout

From the repository root:

```bash
python3 scripts/public_contract_fingerprint.py --check
```

On success the command prints the aggregate fingerprint and number of canonical files.

To print the fingerprint only:

```bash
python3 scripts/public_contract_fingerprint.py --fingerprint
```

To generate the canonical manifest representation without modifying files:

```bash
python3 scripts/public_contract_fingerprint.py --generate
```

Maintainers should regenerate the tracked manifest whenever a canonical contract file changes, then review the fingerprint change together with the compatibility/security implications of the underlying contract change.

## Using a pinned tag or commit

A consumer can check out a specific public tag or commit and run `--check`. If it passes, the tracked fingerprint manifest and the canonical files at that ref agree byte-for-byte according to the published algorithm.

Comparing aggregate hashes is useful for determining whether two refs expose the same canonical contract set. A different fingerprint means at least one covered canonical file changed; it does **not** by itself classify whether the change is compatible, breaking, safe, or malicious.

Use the compatibility matrix, release notes, protocol-change records, and migration guidance to understand the meaning of a changed fingerprint.

## Security boundary

The fingerprint does not replace:

- Git commit/tag authenticity;
- artifact signing;
- trusted distribution;
- transport security;
- authentication or authorization;
- sandboxing/editor permissions;
- dependency provenance;
- security review.

A hostile party that can replace both contract files and the fingerprint manifest can recompute matching hashes. Consumers that require authenticity need an independently trusted source or future signing/provenance mechanism.

## Release-readiness integration

Normal repository CI verifies the tracked fingerprint on every change. The manual Release Readiness audit performs the same verification and includes the aggregate fingerprint in its metadata summary.

This makes the fingerprint a reviewable release property without claiming signed releases or certification.
