#!/usr/bin/env python3
"""Validate the public protocol error-code catalog against the Rust API."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "errors" / "v1" / "catalog.json"
POLICY_RS = ROOT / "src" / "policy.rs"
REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
CODE_RE = re.compile(r"^GLM-PROTO-[0-9]{4}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


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


def impl_body() -> str:
    try:
        text = POLICY_RS.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {POLICY_RS.relative_to(ROOT)}: {exc}") from exc

    match = re.search(
        r"impl\s+ProtocolErrorCode\s*\{(?P<body>.*?)^\}",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValidationError("could not locate impl ProtocolErrorCode")
    return match.group("body")


def parse_as_wire(body: str) -> dict[str, str]:
    try:
        start = body.index("pub const fn as_wire")
        end = body.index("pub fn from_wire", start)
    except ValueError as exc:
        raise ValidationError("ProtocolErrorCode must expose both as_wire and from_wire") from exc

    pairs = re.findall(
        r'Self::([A-Za-z0-9_]+)\s*=>\s*"(GLM-PROTO-[0-9]{4})"',
        body[start:end],
    )
    if not pairs:
        raise ValidationError("ProtocolErrorCode::as_wire has no parseable mappings")

    result: dict[str, str] = {}
    seen_codes: set[str] = set()
    for variant, code in pairs:
        if variant in result:
            raise ValidationError(f"duplicate Rust ProtocolErrorCode variant: {variant}")
        if code in seen_codes:
            raise ValidationError(f"duplicate Rust protocol error code: {code}")
        result[variant] = code
        seen_codes.add(code)
    return result


def parse_from_wire(body: str) -> dict[str, str]:
    try:
        start = body.index("pub fn from_wire")
    except ValueError as exc:
        raise ValidationError("ProtocolErrorCode is missing from_wire") from exc

    pairs = re.findall(
        r'"(GLM-PROTO-[0-9]{4})"\s*=>\s*Some\(Self::([A-Za-z0-9_]+)\)',
        body[start:],
    )
    if not pairs:
        raise ValidationError("ProtocolErrorCode::from_wire has no parseable mappings")

    result: dict[str, str] = {}
    seen_variants: set[str] = set()
    for code, variant in pairs:
        if code in result:
            raise ValidationError(f"duplicate from_wire protocol error code: {code}")
        if variant in seen_variants:
            raise ValidationError(f"duplicate from_wire ProtocolErrorCode variant: {variant}")
        result[code] = variant
        seen_variants.add(variant)
    return result


def snake_case(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


def validate() -> int:
    catalog = load_json(CATALOG)
    registry = load_json(REGISTRY)

    catalog_version = catalog.get("catalog_version")
    if not isinstance(catalog_version, str) or SEMVER_RE.fullmatch(catalog_version) is None:
        raise ValidationError("error catalog has invalid catalog_version")

    wire_version = catalog.get("wire_protocol_version")
    if wire_version != registry.get("wire_protocol_version"):
        raise ValidationError(
            "error catalog wire protocol version does not match the canonical registry: "
            f"catalog={wire_version!r}, registry={registry.get('wire_protocol_version')!r}"
        )

    entries = catalog.get("codes")
    if not isinstance(entries, list) or not entries:
        raise ValidationError("error catalog codes must be a non-empty array")

    catalog_mapping: dict[str, str] = {}
    seen_codes: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("error catalog contains a non-object entry")
        name = entry.get("name")
        code = entry.get("code")
        description = entry.get("description")
        if not isinstance(name, str) or NAME_RE.fullmatch(name) is None:
            raise ValidationError(f"invalid error catalog name: {name!r}")
        if not isinstance(code, str) or CODE_RE.fullmatch(code) is None:
            raise ValidationError(f"invalid protocol error code: {code!r}")
        if not isinstance(description, str) or not description.strip():
            raise ValidationError(f"missing description for protocol error code: {code}")
        if name in catalog_mapping:
            raise ValidationError(f"duplicate error catalog name: {name}")
        if code in seen_codes:
            raise ValidationError(f"duplicate error catalog code: {code}")
        catalog_mapping[name] = code
        seen_codes.add(code)

    body = impl_body()
    as_wire = parse_as_wire(body)
    from_wire = parse_from_wire(body)

    expected_reverse = {code: variant for variant, code in as_wire.items()}
    if from_wire != expected_reverse:
        missing = sorted(set(expected_reverse) - set(from_wire))
        extra = sorted(set(from_wire) - set(expected_reverse))
        wrong = sorted(
            code
            for code in set(expected_reverse) & set(from_wire)
            if expected_reverse[code] != from_wire[code]
        )
        raise ValidationError(
            "ProtocolErrorCode as_wire/from_wire mismatch: "
            f"missing={missing}, extra={extra}, wrong_variant={wrong}"
        )

    rust_mapping = {snake_case(variant): code for variant, code in as_wire.items()}
    if catalog_mapping != rust_mapping:
        missing_names = sorted(set(rust_mapping) - set(catalog_mapping))
        extra_names = sorted(set(catalog_mapping) - set(rust_mapping))
        wrong_codes = sorted(
            name
            for name in set(rust_mapping) & set(catalog_mapping)
            if rust_mapping[name] != catalog_mapping[name]
        )
        raise ValidationError(
            "Rust / error catalog drift: "
            f"missing={missing_names}, extra={extra_names}, wrong_code={wrong_codes}"
        )

    return len(entries)


def main() -> int:
    try:
        count = validate()
    except (KeyError, TypeError, ValidationError) as exc:
        print(f"protocol error catalog validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"protocol error catalog validation passed: {count} public codes match Rust")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
