# Capability Negotiation Profile v1

This directory is the machine-readable companion to `docs/CAPABILITY_NEGOTIATION.md`.

- `profile.json` declares the normative profile choices for wire protocol `0.4.0`.
- `cases.json` contains positive and negative conformance cases executed in CI.

Profile v1 intentionally uses exact capability `name` + `version` matching. Unsupported required capabilities reject the handshake, unsupported optional capabilities are omitted, duplicate names are rejected as ambiguous, and task-requested capability names must be a subset of the session's selected capability names.

The Rust crate exposes the same public semantics through:

- `Capability`;
- `CapabilityRequirement`;
- `CapabilityNegotiationError`;
- `is_capability_name`;
- `negotiate_capabilities`;
- `task_capabilities_are_selected`.

The Python repository-contract check executes the machine-readable cases:

```bash
python3 scripts/validate_capability_profile.py
```

Capability negotiation is not authorization. A selected capability may still be denied by authentication, policy, risk, approval, or execution-safety checks.

No file in this directory defines or exposes private Glomancy runtime implementation details.
