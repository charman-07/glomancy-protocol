#!/usr/bin/env python3
"""Validate the machine-readable public resource limits against the Rust API."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "limits" / "v1" / "policy.json"
RUST_POLICY_PATH = ROOT / "src" / "policy.rs"
RUST_LIB_PATH = ROOT / "src" / "lib.rs"

SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
LIMIT_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$")
RUST_CONST_RE = re.compile(r"^MAX_[A-Z0-9_]+$")

REQUIRED_LIMITS = {
    "message.max_bytes": ("MAX_MESSAGE_BYTES", "bytes", "encoded_message"),
    "payload.max_depth": ("MAX_PAYLOAD_DEPTH", "levels", "payload_structure"),
    "extensions.max_per_message": ("MAX_EXTENSIONS", "entries", "message_extensions"),
    "artifacts.max_per_message": ("MAX_ARTIFACTS_PER_MESSAGE", "entries", "message_artifacts"),
}
ALLOWED_UNITS = {"bytes", "levels", "entries"}
ALLOWED_ENFORCEMENT = {"maximum"}
ALLOWED_SCOPES = {value[2] for value in REQUIRED_LIMITS.values()}


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValidationError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError("resource limits policy must be a JSON object")
    return value


def rust_protocol_version() -> str:
    text = RUST_LIB_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"PROTOCOL_VERSION\s*:\s*ProtocolVersion\s*=\s*ProtocolVersion::new\(\s*"
        r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
        text,
    )
    if match is None:
        raise ValidationError("could not parse PROTOCOL_VERSION from src/lib.rs")
    return ".".join(match.groups())


def rust_constants() -> dict[str, int]:
    text = RUST_POLICY_PATH.read_text(encoding="utf-8")
    result: dict[str, int] = {}
    for name in {value[0] for value in REQUIRED_LIMITS.values()}:
        match = re.search(rf"pub const {re.escape(name)}: usize = ([0-9_]+);", text)
        if match is None:
            raise ValidationError(f"missing Rust constant {name}")
        result[name] = int(match.group(1).replace("_", ""))
    return result


def validate(policy: dict[str, Any]) -> tuple[str, int]:
    policy_version = policy.get("policy_version")
    if not isinstance(policy_version, str) or SEMVER_RE.fullmatch(policy_version) is None:
        raise ValidationError("policy_version must be a core semantic version")

    wire_version = policy.get("wire_protocol_version")
    if not isinstance(wire_version, str) or SEMVER_RE.fullmatch(wire_version) is None:
        raise ValidationError("wire_protocol_version must be a core semantic version")
    rust_wire = rust_protocol_version()
    if wire_version != rust_wire:
        raise ValidationError(
            f"wire protocol version drift: limits={wire_version}, rust={rust_wire}"
        )

    description = policy.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValidationError("description must be a non-empty string")

    limits = policy.get("limits")
    if not isinstance(limits, list) or not limits:
        raise ValidationError("limits must be a non-empty array")

    seen_ids: set[str] = set()
    seen_constants: set[str] = set()
    parsed: dict[str, tuple[str, int, str, str, str]] = {}

    for index, entry in enumerate(limits):
        if not isinstance(entry, dict):
            raise ValidationError(f"limit {index} must be an object")

        limit_id = entry.get("id")
        rust_constant = entry.get("rust_constant")
        value = entry.get("value")
        unit = entry.get("unit")
        scope = entry.get("scope")
        enforcement = entry.get("enforcement")

        if not isinstance(limit_id, str) or LIMIT_ID_RE.fullmatch(limit_id) is None:
            raise ValidationError(f"limit {index} has invalid id")
        if limit_id in seen_ids:
            raise ValidationError(f"duplicate limit id: {limit_id}")
        seen_ids.add(limit_id)

        if not isinstance(rust_constant, str) or RUST_CONST_RE.fullmatch(rust_constant) is None:
            raise ValidationError(f"limit {limit_id} has invalid rust_constant")
        if rust_constant in seen_constants:
            raise ValidationError(f"duplicate rust_constant mapping: {rust_constant}")
        seen_constants.add(rust_constant)

        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValidationError(f"limit {limit_id} value must be a positive integer")
        if unit not in ALLOWED_UNITS:
            raise ValidationError(f"limit {limit_id} has unsupported unit: {unit!r}")
        if scope not in ALLOWED_SCOPES:
            raise ValidationError(f"limit {limit_id} has unsupported scope: {scope!r}")
        if enforcement not in ALLOWED_ENFORCEMENT:
            raise ValidationError(
                f"limit {limit_id} has unsupported enforcement: {enforcement!r}"
            )

        parsed[limit_id] = (rust_constant, value, unit, scope, enforcement)

    if set(parsed) != set(REQUIRED_LIMITS):
        missing = sorted(set(REQUIRED_LIMITS) - set(parsed))
        unexpected = sorted(set(parsed) - set(REQUIRED_LIMITS))
        raise ValidationError(
            f"public limit set mismatch: missing={missing}, unexpected={unexpected}"
        )

    constants = rust_constants()
    for limit_id, (expected_constant, expected_unit, expected_scope) in REQUIRED_LIMITS.items():
        rust_constant, value, unit, scope, enforcement = parsed[limit_id]
        if rust_constant != expected_constant:
            raise ValidationError(
                f"limit {limit_id} must map to {expected_constant}, got {rust_constant}"
            )
        if unit != expected_unit:
            raise ValidationError(
                f"limit {limit_id} unit must be {expected_unit}, got {unit}"
            )
        if scope != expected_scope:
            raise ValidationError(
                f"limit {limit_id} scope must be {expected_scope}, got {scope}"
            )
        if enforcement != "maximum":
            raise ValidationError(f"limit {limit_id} must use maximum enforcement")
        rust_value = constants[rust_constant]
        if value != rust_value:
            raise ValidationError(
                f"limit drift for {limit_id}: policy={value}, Rust {rust_constant}={rust_value}"
            )

    return policy_version, len(parsed)


def main() -> int:
    try:
        policy = load_json(POLICY_PATH)
        policy_version, count = validate(policy)
    except (ValidationError, OSError) as exc:
        print(f"resource limits validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "resource limits validation passed: "
        f"policy={policy_version}, limits={count}, wire={policy['wire_protocol_version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
