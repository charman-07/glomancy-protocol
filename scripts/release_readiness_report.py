#!/usr/bin/env python3
"""Validate and report release-facing Glomancy Protocol metadata.

This script is intentionally dependency-free. It does not publish, tag, sign, or
certify a release; it only validates public metadata consistency and emits a
human-, JSON-, or Markdown-readable summary for release-readiness workflows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
CORE_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ReadinessError(RuntimeError):
    pass


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReadinessError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise ReadinessError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReadinessError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def cargo_package_field(text: str, key: str) -> str:
    package_match = re.search(r"(?ms)^\[package\]\s*(.*?)(?=^\[|\Z)", text)
    if package_match is None:
        raise ReadinessError("Cargo.toml is missing [package]")
    field_match = re.search(
        rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"]+)"\s*$', package_match.group(1)
    )
    if field_match is None:
        raise ReadinessError(f"Cargo.toml [package] is missing {key!r}")
    return field_match.group(1)


def require_semver(label: str, value: object, *, core_only: bool = False) -> str:
    if not isinstance(value, str):
        raise ReadinessError(f"{label} must be a string")
    matcher = CORE_SEMVER_RE if core_only else SEMVER_RE
    if matcher.fullmatch(value) is None:
        raise ReadinessError(f"{label} is not a valid semantic version: {value!r}")
    return value


def rust_protocol_version() -> str:
    text = read_text(ROOT / "src" / "lib.rs")
    match = re.search(
        r"PROTOCOL_VERSION\s*:\s*ProtocolVersion\s*=\s*ProtocolVersion::new\(\s*"
        r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
        text,
    )
    if match is None:
        raise ReadinessError("could not parse PROTOCOL_VERSION from src/lib.rs")
    return ".".join(match.groups())


def schema_versions(registry: dict[str, Any]) -> list[str]:
    versions: set[str] = set()
    for key in ("support_schemas", "message_schemas"):
        entries = registry.get(key)
        if not isinstance(entries, list) or not entries:
            raise ReadinessError(f"registry {key} must be a non-empty array")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ReadinessError(f"registry {key} contains a non-object entry")
            versions.add(require_semver(f"registry {key} version", entry.get("version")))
    return sorted(versions)


def release_heading_exists(version: str) -> bool:
    changelog = read_text(ROOT / "CHANGELOG.md")
    return re.search(rf"(?m)^## \[{re.escape(version)}\](?:\s|—|-|$)", changelog) is not None


def collect(expected_version: str | None) -> dict[str, Any]:
    cargo = read_text(ROOT / "Cargo.toml")
    package_name = cargo_package_field(cargo, "name")
    package_version = require_semver("Rust package version", cargo_package_field(cargo, "version"))
    rust_version = cargo_package_field(cargo, "rust-version")

    if package_name != "glomancy-protocol":
        raise ReadinessError(f"unexpected Rust package name: {package_name!r}")
    if expected_version is not None and package_version != expected_version:
        raise ReadinessError(
            f"expected release version {expected_version!r}, Cargo.toml contains {package_version!r}"
        )

    registry = load_json(ROOT / "registry" / "v1" / "manifest.json")
    capability = load_json(ROOT / "capabilities" / "v1" / "profile.json")
    vectors = load_json(ROOT / "vectors" / "v1" / "manifest.json")
    errors = load_json(ROOT / "errors" / "v1" / "catalog.json")

    registry_wire = require_semver(
        "registry wire_protocol_version", registry.get("wire_protocol_version"), core_only=True
    )
    rust_wire = require_semver("Rust PROTOCOL_VERSION", rust_protocol_version(), core_only=True)
    capability_wire = require_semver(
        "capability wire_protocol_version", capability.get("wire_protocol_version"), core_only=True
    )
    vector_wire = require_semver(
        "vector wire_protocol_version", vectors.get("wire_protocol_version"), core_only=True
    )
    error_wire = require_semver(
        "error catalog wire_protocol_version", errors.get("wire_protocol_version"), core_only=True
    )

    wire_versions = {
        "rust": rust_wire,
        "registry": registry_wire,
        "capability_profile": capability_wire,
        "consumer_vectors": vector_wire,
        "error_catalog": error_wire,
    }
    if len(set(wire_versions.values())) != 1:
        raise ReadinessError(f"wire protocol version drift: {wire_versions}")

    profile_version = require_semver("capability profile_version", capability.get("profile_version"))
    vector_version = require_semver("consumer vector_version", vectors.get("vector_version"))
    catalog_version = require_semver("error catalog_version", errors.get("catalog_version"))
    schemas = schema_versions(registry)

    message_schemas = registry.get("message_schemas")
    support_schemas = registry.get("support_schemas")
    vector_files = vectors.get("files")
    error_codes = errors.get("codes")
    if not isinstance(message_schemas, list):
        raise ReadinessError("registry message_schemas must be an array")
    if not isinstance(support_schemas, list):
        raise ReadinessError("registry support_schemas must be an array")
    if not isinstance(vector_files, list):
        raise ReadinessError("consumer vector files must be an array")
    if not isinstance(error_codes, list):
        raise ReadinessError("error catalog codes must be an array")

    changelog_has_release = release_heading_exists(package_version)
    if expected_version is not None and not changelog_has_release:
        raise ReadinessError(
            f"CHANGELOG.md has no release heading for expected version {package_version}"
        )

    return {
        "status": "metadata-consistent",
        "package": {
            "name": package_name,
            "version": package_version,
            "rust_version": rust_version,
        },
        "wire_protocol_version": registry_wire,
        "schema_versions": schemas,
        "capability_profile_version": profile_version,
        "consumer_vector_version": vector_version,
        "error_catalog_version": catalog_version,
        "counts": {
            "message_schemas": len(message_schemas),
            "support_schemas": len(support_schemas),
            "vector_areas": len(vector_files),
            "protocol_error_codes": len(error_codes),
        },
        "changelog_has_current_package_release": changelog_has_release,
    }


def as_markdown(data: dict[str, Any], ref: str | None, sha: str | None) -> str:
    package = data["package"]
    counts = data["counts"]
    schema_versions_text = ", ".join(data["schema_versions"])
    lines = [
        "# Glomancy Protocol release-readiness metadata",
        "",
        f"- **Audited ref:** `{ref or '<not supplied>'}`",
        f"- **Audited SHA:** `{sha or '<not supplied>'}`",
        f"- **Metadata status:** `{data['status']}`",
        f"- **Rust package:** `{package['name']} {package['version']}`",
        f"- **Minimum Rust:** `{package['rust_version']}`",
        f"- **Wire protocol:** `{data['wire_protocol_version']}`",
        f"- **Public schema versions:** `{schema_versions_text}`",
        f"- **Capability profile:** `{data['capability_profile_version']}`",
        f"- **Consumer vectors:** `{data['consumer_vector_version']}`",
        f"- **Error catalog:** `{data['error_catalog_version']}`",
        f"- **Message schemas:** `{counts['message_schemas']}`",
        f"- **Support schemas:** `{counts['support_schemas']}`",
        f"- **Vector areas:** `{counts['vector_areas']}`",
        f"- **Protocol error codes:** `{counts['protocol_error_codes']}`",
        "",
        "> This report validates release-facing metadata consistency only. The workflow's quality, contract, and portability jobs provide the remaining release-gate evidence. It does not sign, publish, certify, or authorize a release.",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="emit JSON")
    output.add_argument("--markdown", action="store_true", help="emit Markdown")
    parser.add_argument("--expected-version", help="require Cargo.toml to match this release version")
    parser.add_argument("--ref", help="audited ref label for report output")
    parser.add_argument("--sha", help="audited commit SHA for report output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.expected_version is not None:
            require_semver("expected release version", args.expected_version)
        data = collect(args.expected_version)
    except ReadinessError as exc:
        print(f"release-readiness metadata validation failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        report = dict(data)
        report["audited_ref"] = args.ref
        report["audited_sha"] = args.sha
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(as_markdown(data, args.ref, args.sha))
    else:
        print(
            "release-readiness metadata passed: "
            f"crate={data['package']['version']} "
            f"wire={data['wire_protocol_version']} "
            f"schemas={','.join(data['schema_versions'])} "
            f"vectors={data['consumer_vector_version']} "
            f"errors={data['error_catalog_version']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
