#!/usr/bin/env python3
"""Validate repository-level protocol invariants using only the Python stdlib."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "registry" / "v1"
EXAMPLES_DIR = ROOT / "examples" / "v1"
COMPATIBILITY_DIR = ROOT / "compatibility" / "v1"


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc


def resolve_repo_path(base: Path, value: str) -> Path:
    target = (base / value).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError as exc:
        raise ValidationError(f"path escapes repository root: {value}") from exc
    if not target.is_file():
        raise ValidationError(f"referenced file does not exist: {target.relative_to(ROOT)}")
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_all_json() -> int:
    count = 0
    for path in sorted(ROOT.rglob("*.json")):
        load_json(path)
        count += 1
    return count


def validate_registry() -> tuple[int, str]:
    manifest = load_json(REGISTRY_DIR / "manifest.json")
    entries = [*manifest.get("support_schemas", []), *manifest.get("message_schemas", [])]
    if not entries:
        raise ValidationError("schema registry is empty")

    schema_ids: set[str] = set()
    message_kinds: set[str] = set()

    for entry in entries:
        schema_id = entry.get("schema_id")
        if not isinstance(schema_id, str) or not schema_id.startswith("urn:glomancy:protocol:"):
            raise ValidationError(f"invalid schema_id in registry: {schema_id!r}")
        if schema_id in schema_ids:
            raise ValidationError(f"duplicate schema_id in registry: {schema_id}")
        schema_ids.add(schema_id)

        message_kind = entry.get("message_kind")
        if message_kind is not None:
            if not isinstance(message_kind, str) or not message_kind:
                raise ValidationError(f"invalid message_kind in registry: {message_kind!r}")
            if message_kind in message_kinds:
                raise ValidationError(f"duplicate message_kind in registry: {message_kind}")
            message_kinds.add(message_kind)

        target = resolve_repo_path(REGISTRY_DIR, entry["file"])
        actual_hash = sha256(target)
        expected_hash = entry.get("sha256")
        if actual_hash != expected_hash:
            raise ValidationError(
                f"schema hash mismatch for {target.relative_to(ROOT)}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    wire_version = manifest.get("wire_protocol_version")
    if not isinstance(wire_version, str) or not wire_version:
        raise ValidationError("registry wire_protocol_version is missing")

    return len(entries), wire_version


def validate_examples() -> int:
    manifest = load_json(EXAMPLES_DIR / "manifest.json")
    entries = [*manifest.get("valid", []), *manifest.get("invalid", [])]
    if not entries:
        raise ValidationError("example manifest is empty")

    seen: set[str] = set()
    for entry in entries:
        fixture = resolve_repo_path(EXAMPLES_DIR, entry["file"])
        schema = resolve_repo_path(EXAMPLES_DIR, entry["schema"])
        relative_fixture = str(fixture.relative_to(ROOT))
        if relative_fixture in seen:
            raise ValidationError(f"duplicate fixture in example manifest: {relative_fixture}")
        seen.add(relative_fixture)
        load_json(fixture)
        load_json(schema)

    return len(entries)


def validate_compatibility(expected_wire_version: str) -> int:
    matrix = load_json(COMPATIBILITY_DIR / "compatibility-matrix.json")
    cases = load_json(COMPATIBILITY_DIR / "cases.json")

    matrix_version = matrix.get("current_protocol_version")
    if matrix_version != expected_wire_version:
        raise ValidationError(
            "wire protocol version mismatch: "
            f"registry={expected_wire_version}, compatibility={matrix_version}"
        )

    rules = matrix.get("rules", [])
    if not rules:
        raise ValidationError("compatibility matrix has no rules")

    rule_ids = [rule.get("id") for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValidationError("compatibility matrix contains duplicate rule IDs")

    if not isinstance(cases, dict) or cases.get("schema_version") != 1:
        raise ValidationError("compatibility cases have an unsupported schema_version")

    return len(rules)


def main() -> int:
    try:
        json_count = validate_all_json()
        registry_count, wire_version = validate_registry()
        fixture_count = validate_examples()
        rule_count = validate_compatibility(wire_version)
    except (KeyError, TypeError, ValidationError) as exc:
        print(f"repository validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "repository validation passed: "
        f"{json_count} JSON files, {registry_count} registry entries, "
        f"{fixture_count} fixtures, {rule_count} compatibility rules, "
        f"wire protocol {wire_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
