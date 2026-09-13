#!/usr/bin/env python3
"""Validate parity between the canonical JSON registry and Rust registry snapshot."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
MESSAGE_RS = ROOT / "src" / "message.rs"
RUST_REGISTRY = ROOT / "src" / "generated_schema_registry.rs"


class ValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RustDescriptor:
    variant: str
    schema_id: str
    version: tuple[int, int, int]
    sha256: str
    relative_path: str


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def parse_version(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValidationError(f"unsupported schema version format: {value!r}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def parse_message_kind_map() -> dict[str, str]:
    try:
        text = MESSAGE_RS.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {MESSAGE_RS.relative_to(ROOT)}: {exc}") from exc

    try:
        start = text.index("pub const fn as_wire")
        end = text.index("pub fn from_wire", start)
    except ValueError as exc:
        raise ValidationError("could not locate MessageKind::as_wire/from_wire implementation") from exc

    body = text[start:end]
    pairs = re.findall(r'Self::([A-Za-z0-9_]+)\s*=>\s*"([^"]+)"', body)
    if not pairs:
        raise ValidationError("MessageKind::as_wire contains no parseable variants")

    result: dict[str, str] = {}
    seen_wire: set[str] = set()
    for variant, wire in pairs:
        if variant in result:
            raise ValidationError(f"duplicate MessageKind variant in as_wire: {variant}")
        if wire in seen_wire:
            raise ValidationError(f"duplicate MessageKind wire value in as_wire: {wire}")
        result[variant] = wire
        seen_wire.add(wire)
    return result


def parse_rust_registry() -> list[RustDescriptor]:
    try:
        text = RUST_REGISTRY.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {RUST_REGISTRY.relative_to(ROOT)}: {exc}") from exc

    pattern = re.compile(
        r"SchemaDescriptor\s*\{\s*"
        r"kind:\s*MessageKind::([A-Za-z0-9_]+),\s*"
        r"schema_id:\s*\"([^\"]+)\",\s*"
        r"schema_version:\s*ProtocolVersion::new\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\),\s*"
        r"sha256:\s*\"([0-9a-f]{64})\",\s*"
        r"relative_path:\s*\"([^\"]+)\",\s*"
        r"\},",
        re.MULTILINE,
    )

    matches = pattern.findall(text)
    descriptor_count = text.count("SchemaDescriptor {")
    if descriptor_count != len(matches):
        raise ValidationError(
            "generated Rust registry contains an unparseable descriptor: "
            f"found {descriptor_count}, parsed {len(matches)}"
        )

    descriptors = [
        RustDescriptor(
            variant=variant,
            schema_id=schema_id,
            version=(int(major), int(minor), int(patch)),
            sha256=sha256,
            relative_path=relative_path,
        )
        for variant, schema_id, major, minor, patch, sha256, relative_path in matches
    ]
    if not descriptors:
        raise ValidationError("generated Rust registry is empty")
    return descriptors


def canonical_repo_path(registry_relative_path: str) -> str:
    target = (JSON_REGISTRY.parent / registry_relative_path).resolve()
    try:
        return target.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ValidationError(f"registry path escapes repository root: {registry_relative_path}") from exc


def validate() -> int:
    manifest = load_json(JSON_REGISTRY)
    message_entries = manifest.get("message_schemas")
    support_entries = manifest.get("support_schemas")
    if not isinstance(message_entries, list) or not message_entries:
        raise ValidationError("canonical JSON registry has no message_schemas")
    if not isinstance(support_entries, list):
        raise ValidationError("canonical JSON registry support_schemas must be a list")

    kind_map = parse_message_kind_map()
    wire_to_variant = {wire: variant for variant, wire in kind_map.items()}
    rust_descriptors = parse_rust_registry()

    rust_by_variant: dict[str, RustDescriptor] = {}
    for descriptor in rust_descriptors:
        if descriptor.variant in rust_by_variant:
            raise ValidationError(f"duplicate Rust registry variant: {descriptor.variant}")
        rust_by_variant[descriptor.variant] = descriptor

    json_by_variant: dict[str, dict] = {}
    seen_schema_ids: set[str] = set()
    for entry in message_entries:
        if not isinstance(entry, dict):
            raise ValidationError("message_schemas contains a non-object entry")
        kind = entry.get("message_kind")
        if not isinstance(kind, str) or kind not in wire_to_variant:
            raise ValidationError(f"JSON registry message kind is not represented by MessageKind: {kind!r}")
        variant = wire_to_variant[kind]
        if variant in json_by_variant:
            raise ValidationError(f"duplicate JSON registry message kind: {kind}")
        schema_id = entry.get("schema_id")
        if not isinstance(schema_id, str) or schema_id in seen_schema_ids:
            raise ValidationError(f"invalid or duplicate JSON registry schema_id: {schema_id!r}")
        seen_schema_ids.add(schema_id)
        json_by_variant[variant] = entry

    expected_variants = set(kind_map)
    json_variants = set(json_by_variant)
    rust_variants = set(rust_by_variant)

    if json_variants != expected_variants:
        missing = sorted(expected_variants - json_variants)
        extra = sorted(json_variants - expected_variants)
        raise ValidationError(f"JSON registry / MessageKind mismatch: missing={missing}, extra={extra}")
    if rust_variants != expected_variants:
        missing = sorted(expected_variants - rust_variants)
        extra = sorted(rust_variants - expected_variants)
        raise ValidationError(f"Rust registry / MessageKind mismatch: missing={missing}, extra={extra}")

    for variant in sorted(expected_variants):
        entry = json_by_variant[variant]
        rust = rust_by_variant[variant]
        expected = {
            "schema_id": entry.get("schema_id"),
            "version": parse_version(str(entry.get("version"))),
            "sha256": entry.get("sha256"),
            "relative_path": canonical_repo_path(str(entry.get("file"))),
        }
        actual = {
            "schema_id": rust.schema_id,
            "version": rust.version,
            "sha256": rust.sha256,
            "relative_path": rust.relative_path,
        }
        if actual != expected:
            differences = [
                f"{field}: JSON={expected[field]!r}, Rust={actual[field]!r}"
                for field in expected
                if expected[field] != actual[field]
            ]
            raise ValidationError(
                f"Rust registry drift for {kind_map[variant]} ({variant}): " + "; ".join(differences)
            )

    support_ids = {entry.get("schema_id") for entry in support_entries if isinstance(entry, dict)}
    rust_schema_ids = {descriptor.schema_id for descriptor in rust_descriptors}
    leaked_support_ids = sorted(schema_id for schema_id in support_ids if schema_id in rust_schema_ids)
    if leaked_support_ids:
        raise ValidationError(
            "support-only schemas unexpectedly appear in the message-kind Rust registry: "
            + ", ".join(leaked_support_ids)
        )

    return len(rust_descriptors)


def main() -> int:
    try:
        count = validate()
    except (KeyError, TypeError, ValidationError) as exc:
        print(f"Rust/JSON registry parity failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Rust/JSON registry parity passed: "
        f"{count} message kinds match schema IDs, versions, hashes, and paths"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
