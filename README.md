# Glomancy Protocol

A small, transport-neutral Rust protocol package for building safe AI-to-editor integrations.

Glomancy Protocol provides reusable message contracts and validation helpers without exposing or depending on the commercial Glomancy desktop application, private AI runtime, provider integrations, billing systems, or Unreal mutation toolset.

## What it provides

- Stable message kinds for handshake, task lifecycle, approvals, evidence, and heartbeat flows
- Strict identifier and header validation
- Protocol version compatibility helpers
- JSON Schema registry metadata
- Fail-closed behavior for unknown message kinds
- Compatibility fixtures and example payloads

## Quick start

Clone the repository, then run:

```bash
cargo test
cargo run --example quick_start
```

The example parses a protocol version, checks compatibility, and validates a known message kind.

## Design goals

Glomancy Protocol is intentionally small and transport-neutral. It is designed so editor integrations can share a clear contract while keeping implementation-specific agent logic, credentials, provider code, and product internals outside the protocol layer.

Unknown message kinds and unsupported protocol combinations are rejected rather than silently accepted.

## Project status

The project is beginning at `v0.1.0`. The public API should be treated as early-stage and may evolve based on real integration feedback.

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` before opening a pull request. Small documentation improvements, validation tests, compatibility fixtures, and transport-neutral examples are good places to start.

## Security

Please follow `SECURITY.md` for responsible vulnerability reporting. Do not include credentials, tokens, customer data, signing material, or private infrastructure details in issues or pull requests.

## License

MIT. See `LICENSE`.

The separate commercial Glomancy product is not licensed under this repository's MIT license.
