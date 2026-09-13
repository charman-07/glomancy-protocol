#!/usr/bin/env python3
"""Validate capability-negotiation profile v1 and execute its machine-readable cases."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "capabilities" / "v1" / "profile.json"
CASES_PATH = ROOT / "capabilities" / "v1" / "cases.json"
REGISTRY_PATH = ROOT / "registry" / "v1" / "manifest.json"

CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9.-]*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ProfileError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def require_string(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ProfileError(f"{key} must be a non-empty string")
    return value


def validate_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ProfileError("profile must be an object")
    if profile.get("schema_version") != 1:
        raise ProfileError("unsupported capability profile schema_version")

    expected = {
        "matching": "exact-name-and-version",
        "wire_version_order": "negotiate-first",
        "unsupported_required": "reject-handshake",
        "unsupported_optional": "omit",
        "task_request_policy": "selected-name-subset",
        "duplicate_name_policy": "reject-set",
        "authorization_semantics": "none",
        "responder_requirement_semantics": "not-defined-in-v1",
    }
    for key, expected_value in expected.items():
        actual = profile.get(key)
        if actual != expected_value:
            raise ProfileError(f"{key} must be {expected_value!r}, got {actual!r}")

    profile_id = require_string(profile, "profile_id")
    profile_version = require_string(profile, "profile_version")
    wire_version = require_string(profile, "wire_protocol_version")
    if not SEMVER_RE.fullmatch(profile_version):
        raise ProfileError(f"invalid profile_version: {profile_version}")
    if not SEMVER_RE.fullmatch(wire_version):
        raise ProfileError(f"invalid wire_protocol_version: {wire_version}")
    if profile.get("identifier_pattern") != CAPABILITY_RE.pattern:
        raise ProfileError("identifier_pattern does not match the public capability contract")
    if profile.get("max_identifier_length") != 128:
        raise ProfileError("max_identifier_length must remain aligned with common.schema.json")

    registry = load_json(REGISTRY_PATH)
    if not isinstance(registry, dict):
        raise ProfileError("registry manifest must be an object")
    if registry.get("wire_protocol_version") != wire_version:
        raise ProfileError(
            "capability profile wire_protocol_version disagrees with registry/v1/manifest.json"
        )

    return {
        "profile_id": profile_id,
        "profile_version": profile_version,
        "wire_protocol_version": wire_version,
    }


def validate_name(name: Any) -> str:
    if not isinstance(name, str):
        raise ProfileError("capability name must be a string")
    if not 1 <= len(name) <= 128 or not CAPABILITY_RE.fullmatch(name):
        raise ProfileError(f"invalid capability name: {name!r}")
    return name


def validate_version(version: Any) -> str:
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        raise ProfileError(f"invalid capability version: {version!r}")
    return version


def parse_remote(values: Any) -> list[tuple[str, str, bool]]:
    if not isinstance(values, list):
        raise ProfileError("remote must be an array")
    parsed: list[tuple[str, str, bool]] = []
    seen_names: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise ProfileError("remote capability must be an object")
        name = validate_name(item.get("name"))
        version = validate_version(item.get("version"))
        required = item.get("required", False)
        if not isinstance(required, bool):
            raise ProfileError(f"required must be boolean for {name}")
        if name in seen_names:
            raise ProfileError(f"duplicate-remote-capability-name:{name}")
        seen_names.add(name)
        parsed.append((name, version, required))
    return parsed


def parse_local(values: Any) -> list[tuple[str, str]]:
    if not isinstance(values, list):
        raise ProfileError("local must be an array")
    parsed: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise ProfileError("local capability must be an object")
        name = validate_name(item.get("name"))
        version = validate_version(item.get("version"))
        if name in seen_names:
            raise ProfileError(f"duplicate-local-capability-name:{name}")
        seen_names.add(name)
        parsed.append((name, version))
    return parsed


def negotiate(remote_raw: Any, local_raw: Any) -> dict[str, Any]:
    try:
        remote = parse_remote(remote_raw)
    except ProfileError as exc:
        if str(exc).startswith("duplicate-remote-capability-name:"):
            return {"accepted": False, "error": "duplicate-remote-capability-name"}
        raise

    try:
        local = parse_local(local_raw)
    except ProfileError as exc:
        if str(exc).startswith("duplicate-local-capability-name:"):
            return {"accepted": False, "error": "duplicate-local-capability-name"}
        raise

    available = set(local)
    selected: list[dict[str, str]] = []
    for name, version, required in remote:
        if (name, version) in available:
            selected.append({"name": name, "version": version})
        elif required:
            return {"accepted": False, "error": "unsupported-required-capability"}

    return {"accepted": True, "selected": selected}


def task_gate(selected_raw: Any, requested_raw: Any) -> bool:
    selected = parse_local(selected_raw)
    if not isinstance(requested_raw, list):
        raise ProfileError("task_requested must be an array")

    selected_names = {name for name, _ in selected}
    seen: set[str] = set()
    for raw_name in requested_raw:
        name = validate_name(raw_name)
        if name in seen:
            raise ProfileError(f"duplicate task_requested capability name: {name}")
        seen.add(name)
        if name not in selected_names:
            return False
    return True


def run_cases(profile_metadata: dict[str, Any]) -> int:
    document = load_json(CASES_PATH)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ProfileError("unsupported capability cases schema_version")
    if document.get("profile_id") != profile_metadata["profile_id"]:
        raise ProfileError("cases profile_id does not match capability profile")

    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ProfileError("capability cases must be a non-empty array")

    seen_names: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ProfileError("capability case must be an object")
        case_name = require_string(case, "name")
        if case_name in seen_names:
            raise ProfileError(f"duplicate case name: {case_name}")
        seen_names.add(case_name)

        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ProfileError(f"case {case_name} is missing expected object")

        if "task_requested" in case:
            actual = {
                "task_allowed_by_capability_gate": task_gate(
                    case.get("selected", []), case.get("task_requested")
                )
            }
        else:
            actual = negotiate(case.get("remote", []), case.get("local", []))

        if actual != expected:
            raise ProfileError(
                f"case {case_name} failed: expected {expected!r}, got {actual!r}"
            )

    return len(cases)


def main() -> int:
    try:
        profile_metadata = validate_profile(load_json(PROFILE_PATH))
        case_count = run_cases(profile_metadata)
    except ProfileError as exc:
        print(f"capability profile validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "capability profile validation passed: "
        f"profile={profile_metadata['profile_version']} "
        f"wire={profile_metadata['wire_protocol_version']} cases={case_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
