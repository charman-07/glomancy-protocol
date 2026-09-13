#!/usr/bin/env python3
"""Validate Rust wire-enum mappings against common.schema.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMON_SCHEMA = ROOT / "schemas" / "v1" / "common.schema.json"

ENUM_SOURCES: dict[str, tuple[Path, str]] = {
    "component": (ROOT / "src" / "message.rs", "Component"),
    "risk_level": (ROOT / "src" / "message.rs", "RiskLevel"),
    "execution_mode": (ROOT / "src" / "message.rs", "ExecutionMode"),
    "task_status": (ROOT / "src" / "message.rs", "TaskStatus"),
    "error_category": (ROOT / "src" / "policy.rs", "ErrorCategory"),
}


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def impl_body(path: Path, type_name: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc

    pattern = re.compile(
        rf"impl\s+{re.escape(type_name)}\s*\{{(?P<body>.*?)^\}}",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise ValidationError(
            f"could not locate impl {type_name} in {path.relative_to(ROOT)}"
        )
    return match.group("body")


def parse_as_wire(path: Path, type_name: str) -> dict[str, str]:
    body = impl_body(path, type_name)
    try:
        start = body.index("pub const fn as_wire")
    except ValueError as exc:
        raise ValidationError(f"{type_name} is missing as_wire") from exc

    end = body.find("pub fn from_wire", start)
    section = body[start:] if end == -1 else body[start:end]
    pairs = re.findall(r'Self::([A-Za-z0-9_]+)\s*=>\s*"([^"]+)"', section)
    if not pairs:
        raise ValidationError(f"{type_name}::as_wire has no parseable mappings")

    result: dict[str, str] = {}
    seen_wire: set[str] = set()
    for variant, wire in pairs:
        if variant in result:
            raise ValidationError(f"duplicate {type_name} variant in as_wire: {variant}")
        if wire in seen_wire:
            raise ValidationError(f"duplicate {type_name} wire value in as_wire: {wire}")
        result[variant] = wire
        seen_wire.add(wire)
    return result


def parse_from_wire(path: Path, type_name: str) -> dict[str, str]:
    body = impl_body(path, type_name)
    try:
        start = body.index("pub fn from_wire")
    except ValueError as exc:
        raise ValidationError(f"{type_name} is missing from_wire") from exc

    section = body[start:]
    pairs = re.findall(
        r'"([^"]+)"\s*=>\s*Some\(Self::([A-Za-z0-9_]+)\)', section
    )
    if not pairs:
        raise ValidationError(f"{type_name}::from_wire has no parseable mappings")

    result: dict[str, str] = {}
    seen_variants: set[str] = set()
    for wire, variant in pairs:
        if wire in result:
            raise ValidationError(f"duplicate {type_name} wire value in from_wire: {wire}")
        if variant in seen_variants:
            raise ValidationError(f"duplicate {type_name} variant in from_wire: {variant}")
        result[wire] = variant
        seen_variants.add(variant)
    return result


def schema_enum_values(schema: dict, definition: str) -> list[str]:
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        raise ValidationError("common schema is missing $defs")
    entry = defs.get(definition)
    if not isinstance(entry, dict):
        raise ValidationError(f"common schema is missing $defs.{definition}")
    values = entry.get("enum")
    if not isinstance(values, list) or not values:
        raise ValidationError(f"$defs.{definition}.enum must be a non-empty array")
    if any(not isinstance(value, str) or not value for value in values):
        raise ValidationError(f"$defs.{definition}.enum contains a non-string value")
    if len(values) != len(set(values)):
        raise ValidationError(f"$defs.{definition}.enum contains duplicate values")
    return values


def validate() -> tuple[int, int]:
    schema = load_json(COMMON_SCHEMA)
    enum_count = 0
    wire_value_count = 0

    for definition, (path, type_name) in ENUM_SOURCES.items():
        expected_values = schema_enum_values(schema, definition)
        as_wire = parse_as_wire(path, type_name)
        from_wire = parse_from_wire(path, type_name)

        rust_values = list(as_wire.values())
        if set(rust_values) != set(expected_values):
            missing = sorted(set(expected_values) - set(rust_values))
            extra = sorted(set(rust_values) - set(expected_values))
            raise ValidationError(
                f"{type_name} / $defs.{definition} drift: missing={missing}, extra={extra}"
            )

        expected_reverse = {wire: variant for variant, wire in as_wire.items()}
        if from_wire != expected_reverse:
            missing = sorted(set(expected_reverse) - set(from_wire))
            extra = sorted(set(from_wire) - set(expected_reverse))
            wrong = sorted(
                wire
                for wire in set(expected_reverse) & set(from_wire)
                if expected_reverse[wire] != from_wire[wire]
            )
            raise ValidationError(
                f"{type_name} as_wire/from_wire mismatch: "
                f"missing={missing}, extra={extra}, wrong_variant={wrong}"
            )

        enum_count += 1
        wire_value_count += len(expected_values)

    return enum_count, wire_value_count


def main() -> int:
    try:
        enum_count, wire_value_count = validate()
    except (KeyError, TypeError, ValidationError) as exc:
        print(f"wire enum parity failed: {exc}", file=sys.stderr)
        return 1

    print(
        "wire enum parity passed: "
        f"{enum_count} Rust enums match {wire_value_count} common-schema wire values"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
