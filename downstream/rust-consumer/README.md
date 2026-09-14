# Downstream Rust consumer

This is a repository-maintained smoke-test crate that consumes `glomancy-protocol` only through its public Rust API.

Run from the repository root:

```bash
cargo run --manifest-path downstream/rust-consumer/Cargo.toml
```

The crate intentionally lives outside the root package workspace so CI exercises a consumer-shaped compile/run boundary.

It is not evidence of third-party adoption or production usage. See [`docs/DOWNSTREAM_RUST_CONSUMER.md`](../../docs/DOWNSTREAM_RUST_CONSUMER.md) for scope and assurance boundaries.
