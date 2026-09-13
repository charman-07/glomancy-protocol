#!/usr/bin/env python3
"""Validate the public release/security support policy against release metadata."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "support" / "v1" / "policy.json"
SNAPSHOTS = ROOT / "compatibility" / "snapshots" / "manifest.json"
REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
CARGO = ROOT / "Cargo.toml"
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
LINE_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.x$")
SCHEMA_LINE_RE = SEMVER_RE


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def cargo_package_version() -> str:
    try:
        text = CARGO.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read Cargo.toml: {exc}") from exc
    package = re.search(r"(?ms)^\[package\]\s*(.*?)(?=^\[|\Z)", text)
    if package is None:
        raise ValidationError("Cargo.toml is missing [package]")
    match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', package.group(1))
    if match is None:
        raise ValidationError("Cargo.toml [package] is missing version")
    version = match.group(1)
    if SEMVER_RE.fullmatch(version) is None:
        raise ValidationError(f"Cargo.toml package version is not core semver: {version!r}")
    return version


def release_line(version: str) -> str:
    match = SEMVER_RE.fullmatch(version)
    if match is None:
        raise ValidationError(f"not a core semantic version: {version!r}")
    return f"{match.group(1)}.{match.group(2)}.x"


def require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{key} must be a non-empty string")
    return value


def validate() -> int:
    policy = load_json(POLICY)
    snapshots = load_json(SNAPSHOTS)
    registry = load_json(REGISTRY)

    policy_version = require_string(policy, "policy_version")
    if SEMVER_RE.fullmatch(policy_version) is None:
        raise ValidationError(f"invalid policy_version: {policy_version!r}")

    if policy.get("project_maturity") != "pre-1.0":
        raise ValidationError("project_maturity must remain 'pre-1.0' until an explicit 1.0 transition")
    if policy.get("support_model") != "best-effort":
        raise ValidationError("current support_model must be 'best-effort'")
    if policy.get("response_time_sla") is not None:
        raise ValidationError("pre-1.0 public OSS policy must not claim a response-time SLA")
    if policy.get("fixed_support_window_days") is not None:
        raise ValidationError("pre-1.0 public OSS policy must not claim a fixed support window")
    if policy.get("lts_program") is not False:
        raise ValidationError("pre-1.0 public OSS policy must not claim an LTS program")
    if policy.get("backport_policy") != "not-guaranteed":
        raise ValidationError("current backport_policy must be 'not-guaranteed'")
    if policy.get("security_reporting") != "private-first":
        raise ValidationError("security_reporting must be 'private-first'")

    entries = policy.get("supported_releases")
    if not isinstance(entries, list) or not entries:
        raise ValidationError("supported_releases must be a non-empty array")

    snapshot_entries = snapshots.get("snapshots")
    if not isinstance(snapshot_entries, list) or not snapshot_entries:
        raise ValidationError("compatibility snapshot manifest must contain snapshots")
    snapshots_by_tag: dict[str, dict[str, Any]] = {}
    for raw in snapshot_entries:
        if not isinstance(raw, dict):
            raise ValidationError("snapshot manifest contains a non-object entry")
        tag = raw.get("source_tag")
        if not isinstance(tag, str) or not tag:
            raise ValidationError("snapshot entry is missing source_tag")
        if tag in snapshots_by_tag:
            raise ValidationError(f"duplicate snapshot source_tag: {tag}")
        snapshots_by_tag[tag] = raw

    cargo_version = cargo_package_version()
    cargo_line = release_line(cargo_version)
    registry_wire = registry.get("wire_protocol_version")
    if not isinstance(registry_wire, str) or SEMVER_RE.fullmatch(registry_wire) is None:
        raise ValidationError("registry wire_protocol_version is invalid")
    registry_wire_line = release_line(registry_wire)

    seen_crate_lines: set[str] = set()
    seen_tags: set[str] = set()
    current_entries = 0

    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError("supported_releases contains a non-object entry")

        crate_line = require_string(entry, "crate_line")
        wire_line = require_string(entry, "wire_line")
        latest_release = require_string(entry, "latest_release")
        source_tag = require_string(entry, "source_tag")
        schema_line = require_string(entry, "schema_line")
        status = require_string(entry, "status")

        if LINE_RE.fullmatch(crate_line) is None:
            raise ValidationError(f"invalid crate_line: {crate_line!r}")
        if LINE_RE.fullmatch(wire_line) is None:
            raise ValidationError(f"invalid wire_line: {wire_line!r}")
        if SEMVER_RE.fullmatch(latest_release) is None:
            raise ValidationError(f"invalid latest_release: {latest_release!r}")
        if SCHEMA_LINE_RE.fullmatch(schema_line) is None:
            raise ValidationError(f"invalid schema_line: {schema_line!r}")
        if source_tag != f"v{latest_release}":
            raise ValidationError(
                f"source_tag/latest_release mismatch: tag={source_tag!r}, release={latest_release!r}"
            )
        if release_line(latest_release) != crate_line:
            raise ValidationError(
                f"latest_release {latest_release} does not belong to crate_line {crate_line}"
            )
        if status not in {"current", "maintenance"}:
            raise ValidationError(f"unsupported supported-release status: {status!r}")
        if entry.get("bug_fixes") != "best-effort":
            raise ValidationError(f"{crate_line}: bug_fixes must be 'best-effort'")
        if entry.get("security_fixes") != "best-effort":
            raise ValidationError(f"{crate_line}: security_fixes must be 'best-effort'")
        if entry.get("backports") != "not-guaranteed":
            raise ValidationError(f"{crate_line}: backports must be 'not-guaranteed'")

        if crate_line in seen_crate_lines:
            raise ValidationError(f"duplicate supported crate_line: {crate_line}")
        if source_tag in seen_tags:
            raise ValidationError(f"duplicate supported source_tag: {source_tag}")
        seen_crate_lines.add(crate_line)
        seen_tags.add(source_tag)

        snapshot = snapshots_by_tag.get(source_tag)
        if snapshot is None:
            raise ValidationError(f"support policy references unknown release snapshot: {source_tag}")
        if snapshot.get("crate_version") != latest_release:
            raise ValidationError(f"{source_tag}: snapshot crate_version drift")
        snapshot_wire = snapshot.get("wire_protocol_version")
        if not isinstance(snapshot_wire, str) or release_line(snapshot_wire) != wire_line:
            raise ValidationError(f"{source_tag}: snapshot wire protocol does not match {wire_line}")
        if snapshot.get("schema_line") != schema_line:
            raise ValidationError(f"{source_tag}: snapshot schema_line drift")

        if status == "current":
            current_entries += 1
            if crate_line != cargo_line:
                raise ValidationError(
                    f"current support crate_line {crate_line} does not match Cargo.toml line {cargo_line}"
                )
            if wire_line != registry_wire_line:
                raise ValidationError(
                    f"current support wire_line {wire_line} does not match registry line {registry_wire_line}"
                )

    if current_entries != 1:
        raise ValidationError(f"exactly one supported release entry must be current, got {current_entries}")

    return len(entries)


def main() -> int:
    try:
        count = validate()
    except (KeyError, TypeError, ValidationError) as exc:
        print(f"release support policy validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"release support policy validation passed: {count} supported release line(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
