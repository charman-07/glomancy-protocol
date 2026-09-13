# Pull request

## What changes?

<!-- Describe the problem and the smallest useful change. -->

## Protocol impact

- [ ] No wire/schema behavior changes
- [ ] Backward-compatible wire/schema change
- [ ] Potentially breaking change (explain below)

Compatibility notes:

<!-- Mention protocol versions, schema IDs, migration impact, or why none apply. -->

## Security impact

<!-- Describe trust-boundary, validation, approval, evidence, or input-handling impact. Write "None" when genuinely not applicable. -->

## Verification

- [ ] `cargo fmt --check`
- [ ] `cargo clippy --all-targets -- -D warnings`
- [ ] `cargo test --all-targets`
- [ ] `python3 scripts/validate_repository.py`
- [ ] Added/updated tests or fixtures when observable behavior changed
- [ ] Updated documentation/changelog when needed

## Public boundary check

- [ ] No credentials, tokens, private paths, customer data, signing material, proprietary runtime code, provider/billing logic, or private Glomancy implementation details are included.
