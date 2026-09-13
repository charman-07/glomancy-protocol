# Public / Private Boundary

Glomancy Protocol is intentionally a narrow open-source project. The commercial Glomancy product can consume this protocol, but its implementation is not part of this repository.

## Allowed in this repository

- transport-neutral protocol types;
- public JSON Schemas;
- compatibility rules and conformance fixtures;
- validation helpers and protocol limits;
- public examples and integration documentation;
- OSS governance, security, contribution, and release tooling;
- tests and CI needed to verify the public contracts.

## Not allowed in this repository

- provider API keys, tokens, credentials, or private certificates;
- customer data or private project data;
- billing, cost-governor, or commercial entitlement logic;
- private AI/provider gateway implementations;
- private agent/autonomy/runtime implementation details;
- desktop application source that is not part of this protocol package;
- Unreal/editor mutation implementations that are proprietary to the product;
- installer, signing, trust, or private release infrastructure;
- developer-specific filesystem paths or internal machine details;
- direct links that expose private repository locations unnecessarily.

## Automated guard

`scripts/check_public_boundary.py` runs in CI and scans tracked files for a deliberately small set of high-signal problems, including common token shapes, private-key material, tracked environment/key containers, developer home paths, and a direct private-repository reference.

The check intentionally reports only the file and violation category. It does not echo the matched value into CI logs.

## What the guard does not prove

This script is a guardrail, not a complete secret scanner or source-review replacement. A credential can use an unfamiliar format, a document can contain proprietary information without matching a pattern, and Git history requires separate review.

Maintainers should therefore also:

- use GitHub/native secret scanning where available;
- review every public diff for proprietary or sensitive content;
- keep the release checklist in `RELEASING.md`;
- rotate any credential immediately if it is ever exposed;
- avoid copying private history into the public repository.

The safest rule is simple: when information is not necessary to implement or understand the reusable public protocol, keep it out of this repository.
