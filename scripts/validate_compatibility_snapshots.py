#!/usr/bin/env python3
"""Validate published protocol snapshots against the current public contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = ROOT / "compatibility" / "snapshots"
CURRENT_REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
CARGO_TOML = ROOT / "Cargo.toml"
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PACKAGE_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def version_tuple(value: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid semantic version: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def compatibility(local: str, remote: str) -> str:
    local_v = version_tuple(local)
    remote_v = version_tuple(remote)
    if local_v == remote_v:
        return "exact"
    if local_v[0] == 0 or remote_v[0] == 0:
        if local_v[0] == remote_v[0] == 0 and local_v[1] == remote_v[1]:
            return "patch-compatible"
        return "incompatible"
    if local_v[0] == remote_v[0]:
        return "major-compatible"
    return "incompatible"


def current_crate_version() -> str:
    text = CARGO_TOML.read_text(encoding="utf-8")
    match = PACKAGE_VERSION_RE.search(text)
    if match is None:
        raise AssertionError("could not find package version in Cargo.toml")
    value = match.group(1)
    version_tuple(value)
    return value


def as_list(value: object, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be an array")
    result: list[dict[str, object]] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise TypeError(f"{label} entries must be objects")
        result.append(entry)
    return result


def by_schema_id(entries: list[dict[str, object]], label: str) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for entry in entries:
        schema_id = str(entry["schema_id"])
        if schema_id in result:
            raise AssertionError(f"duplicate {label} schema_id: {schema_id}")
        result[schema_id] = entry
    return result


def validate_snapshot(
    metadata: dict[str, object],
    current_registry: dict[str, object],
    crate_version: str,
) -> int:
    snapshot_id = str(metadata["id"])
    filename = str(metadata["file"])
    snapshot_path = SNAPSHOTS / filename
    if not snapshot_path.is_file():
        raise AssertionError(f"{snapshot_id}: missing snapshot file {filename}")

    snapshot = load_json(snapshot_path)
    for key in ("id", "source_tag", "source_commit", "crate_version", "wire_protocol_version"):
        if str(snapshot[key]) != str(metadata[key]):
            raise AssertionError(f"{snapshot_id}: {key} differs between manifest and snapshot")

    source_tag = str(snapshot["source_tag"])
    source_commit = str(snapshot["source_commit"])
    if not source_tag.startswith("v"):
        raise AssertionError(f"{snapshot_id}: source_tag must be a release-style v tag")
    if COMMIT_RE.fullmatch(source_commit) is None:
        raise AssertionError(f"{snapshot_id}: source_commit must be a 40-character lowercase SHA")

    snapshot_crate = str(snapshot["crate_version"])
    if version_tuple(snapshot_crate) > version_tuple(crate_version):
        raise AssertionError(
            f"{snapshot_id}: snapshot crate version {snapshot_crate} is newer than current {crate_version}"
        )

    current_wire = str(current_registry["wire_protocol_version"])
    snapshot_wire = str(snapshot["wire_protocol_version"])
    actual_compatibility = compatibility(current_wire, snapshot_wire)
    expected_compatibility = str(metadata["expected_current_compatibility"])
    if actual_compatibility != expected_compatibility:
        raise AssertionError(
            f"{snapshot_id}: expected compatibility {expected_compatibility}, got {actual_compatibility}"
        )

    if str(snapshot["schema_dialect"]) != str(current_registry["schema_dialect"]):
        raise AssertionError(f"{snapshot_id}: schema dialect changed")

    pinned_support = by_schema_id(as_list(snapshot["support_schemas"], "snapshot support_schemas"), "snapshot support")
    pinned_messages = by_schema_id(as_list(snapshot["message_schemas"], "snapshot message_schemas"), "snapshot message")
    current_support = by_schema_id(as_list(current_registry["support_schemas"], "current support_schemas"), "current support")
    current_messages = by_schema_id(as_list(current_registry["message_schemas"], "current message_schemas"), "current message")

    if actual_compatibility != "incompatible":
        for schema_id, pinned in pinned_support.items():
            current = current_support.get(schema_id)
            if current is None:
                raise AssertionError(f"{snapshot_id}: compatible current contract removed support schema {schema_id}")
            if str(current["sha256"]) != str(pinned["sha256"]):
                raise AssertionError(f"{snapshot_id}: schema content changed without a new schema_id: {schema_id}")

        for schema_id, pinned in pinned_messages.items():
            current = current_messages.get(schema_id)
            if current is None:
                raise AssertionError(f"{snapshot_id}: compatible current contract removed message schema {schema_id}")
            if str(current["sha256"]) != str(pinned["sha256"]):
                raise AssertionError(f"{snapshot_id}: schema content changed without a new schema_id: {schema_id}")
            if str(current["message_kind"]) != str(pinned["message_kind"]):
                raise AssertionError(f"{snapshot_id}: message kind changed for {schema_id}")

    return len(pinned_support) + len(pinned_messages)


def main() -> int:
    try:
        manifest = load_json(SNAPSHOTS / "manifest.json")
        version_tuple(str(manifest["snapshot_format_version"]))
        current_registry = load_json(CURRENT_REGISTRY)
        crate_version = current_crate_version()

        snapshots = as_list(manifest["snapshots"], "snapshots")
        if not snapshots:
            raise AssertionError("snapshot manifest must contain at least one published snapshot")

        seen_ids: set[str] = set()
        seen_tags: set[str] = set()
        total_contracts = 0
        for metadata in snapshots:
            snapshot_id = str(metadata["id"])
            source_tag = str(metadata["source_tag"])
            if snapshot_id in seen_ids:
                raise AssertionError(f"duplicate snapshot id: {snapshot_id}")
            if source_tag in seen_tags:
                raise AssertionError(f"duplicate snapshot source tag: {source_tag}")
            seen_ids.add(snapshot_id)
            seen_tags.add(source_tag)
            total_contracts += validate_snapshot(metadata, current_registry, crate_version)

        print(
            f"compatibility snapshot validation passed for {len(snapshots)} published snapshot(s) "
            f"covering {total_contracts} pinned schema contracts"
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, AssertionError) as exc:
        print(f"compatibility snapshot validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
