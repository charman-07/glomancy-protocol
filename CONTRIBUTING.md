# Contributing

Thanks for your interest in improving Glomancy Protocol.

## Ground rules

- Keep changes focused on the public protocol package.
- Do not submit proprietary Glomancy Desktop, provider, billing, agent-runtime, or Unreal mutation-tool code.
- Never include API keys, credentials, private project names, machine-specific paths, customer data, or signing material.
- Prefer small pull requests with tests.
- Preserve fail-closed behavior for unknown or invalid protocol input.

## Before opening a pull request

Run:

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-targets --all-features
```

## Good first contributions

Good starter work includes documentation improvements, additional validation tests, examples, compatibility fixtures, and schema tooling that does not depend on commercial Glomancy internals.
