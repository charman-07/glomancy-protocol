#!/usr/bin/env python3
"""Independent, dependency-free Python consumer for public Glomancy Protocol vectors.

This example intentionally does not import the Rust crate or repository validator scripts.
It implements selected public consumer decisions independently and checks them against the
language-neutral vectors under vectors/v1/.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
VECTORS = ROOT / "vectors" / "v1"
REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9.-]{0,127}$")


class ConsumerError(RuntimeError):
    """Raised when the example cannot evaluate the public contract safely."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def semver_tuple(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value)
    if match is None:
        raise ValueError(value)
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def has_duplicates(values: list[str]) -> bool:
    return len(values) != len(set(values))


def select_advertised_version(
    local_supported: list[str], remote_supported: list[str]
) -> dict[str, Any]:
    for value in local_supported:
        try:
            semver_tuple(value)
        except ValueError:
            return {
                "accepted": False,
                "selected_version": None,
                "reason": "invalid-local-version",
            }
    for value in remote_supported:
        try:
            semver_tuple(value)
        except ValueError:
            return {
                "accepted": False,
                "selected_version": None,
                "reason": "invalid-remote-version",
            }

    if has_duplicates(local_supported):
        return {
            "accepted": False,
            "selected_version": None,
            "reason": "duplicate-local-version",
        }
    if has_duplicates(remote_supported):
        return {
            "accepted": False,
            "selected_version": None,
            "reason": "duplicate-remote-version",
        }

    shared = set(local_supported).intersection(remote_supported)
    if not shared:
        return {
            "accepted": False,
            "selected_version": None,
            "reason": "no-shared-advertised-version",
        }

    selected = max(shared, key=semver_tuple)
    return {"accepted": True, "selected_version": selected, "reason": None}


def valid_capability_name(name: str) -> bool:
    return len(name.encode("utf-8")) <= 128 and CAPABILITY_RE.fullmatch(name) is not None


def duplicate_capability_name(entries: list[dict[str, Any]]) -> bool:
    names = [str(entry.get("name", "")) for entry in entries]
    return has_duplicates(names)


def negotiate_capabilities(
    requested: list[dict[str, Any]], available: list[dict[str, Any]]
) -> dict[str, Any]:
    for entry in requested:
        name = str(entry.get("name", ""))
        if not valid_capability_name(name):
            return {"accepted": False, "selected": [], "error": "invalid-remote-name"}
        try:
            semver_tuple(str(entry.get("version", "")))
        except ValueError:
            return {"accepted": False, "selected": [], "error": "invalid-remote-version"}

    for entry in available:
        name = str(entry.get("name", ""))
        if not valid_capability_name(name):
            return {"accepted": False, "selected": [], "error": "invalid-local-name"}
        try:
            semver_tuple(str(entry.get("version", "")))
        except ValueError:
            return {"accepted": False, "selected": [], "error": "invalid-local-version"}

    if duplicate_capability_name(requested):
        return {"accepted": False, "selected": [], "error": "duplicate-remote-name"}
    if duplicate_capability_name(available):
        return {"accepted": False, "selected": [], "error": "duplicate-local-name"}

    available_pairs = {
        (str(entry["name"]), str(entry["version"])) for entry in available
    }
    selected: list[dict[str, str]] = []

    for entry in requested:
        name = str(entry["name"])
        version = str(entry["version"])
        if (name, version) in available_pairs:
            selected.append({"name": name, "version": version})
        elif bool(entry.get("required", False)):
            return {"accepted": False, "selected": [], "error": "unsupported-required"}

    return {"accepted": True, "selected": selected, "error": None}


def task_capability_gate(
    requested_names: list[str], selected: list[dict[str, Any]]
) -> dict[str, bool]:
    selected_names = {str(entry.get("name", "")) for entry in selected}
    accepted = all(
        valid_capability_name(name) and name in selected_names for name in requested_names
    )
    return {"accepted": accepted}


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def evaluate_approval(
    request: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    if decision.get("approval_id") != request.get("approval_id"):
        return {"accepted": False, "authorized": False, "reason": "approval-id-mismatch"}
    if decision.get("task_id") != request.get("task_id"):
        return {"accepted": False, "authorized": False, "reason": "task-id-mismatch"}

    decision_value = decision.get("decision")
    if decision_value not in {"approve", "deny"}:
        return {"accepted": False, "authorized": False, "reason": "invalid-decision"}

    try:
        expires_at = parse_timestamp(str(request.get("expires_at", "")))
        decided_at = parse_timestamp(str(decision.get("decided_at", "")))
    except ValueError:
        return {"accepted": False, "authorized": False, "reason": "invalid-timestamp"}

    if decided_at > expires_at:
        return {"accepted": False, "authorized": False, "reason": "expired"}
    if decision_value == "deny":
        return {"accepted": True, "authorized": False, "reason": "denied"}

    # Here "authorized" means the approval gate is satisfied for this vector only.
    # Authentication, local authorization, policy, sandboxing, and editor permissions
    # remain separate integration responsibilities.
    return {"accepted": True, "authorized": True, "reason": None}


def run_cases(
    filename: str,
    evaluator: Callable[[dict[str, Any]], dict[str, Any]],
) -> int:
    data = load_json(VECTORS / filename)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ConsumerError(f"invalid vector file: {filename}")

    count = 0
    for case in data["cases"]:
        if not isinstance(case, dict):
            raise ConsumerError(f"invalid case in {filename}")
        case_id = str(case.get("id", "<missing-id>"))
        inputs = case.get("input")
        expected = case.get("expected")
        if not isinstance(inputs, dict) or not isinstance(expected, dict):
            raise ConsumerError(f"{filename}:{case_id}: malformed input/expected")
        actual = evaluator(inputs)
        if actual != expected:
            raise ConsumerError(
                f"{filename}:{case_id}: expected {expected!r}, got {actual!r}"
            )
        count += 1
    return count


def version_case(inputs: dict[str, Any]) -> dict[str, Any]:
    return select_advertised_version(
        [str(value) for value in inputs["local_supported"]],
        [str(value) for value in inputs["remote_supported"]],
    )


def capability_case(inputs: dict[str, Any]) -> dict[str, Any]:
    return negotiate_capabilities(inputs["requested"], inputs["available"])


def task_gate_case(inputs: dict[str, Any]) -> dict[str, Any]:
    return task_capability_gate(
        [str(value) for value in inputs["requested_names"]], inputs["selected"]
    )


def approval_case(inputs: dict[str, Any]) -> dict[str, Any]:
    return evaluate_approval(inputs["request"], inputs["decision"])


def main() -> int:
    try:
        registry = load_json(REGISTRY)
        if not isinstance(registry, dict):
            raise ConsumerError("registry manifest must be an object")
        wire_version = registry.get("wire_protocol_version")
        message_schemas = registry.get("message_schemas")
        if not isinstance(wire_version, str) or not SEMVER_RE.fullmatch(wire_version):
            raise ConsumerError("registry wire_protocol_version is invalid")
        if not isinstance(message_schemas, list) or not message_schemas:
            raise ConsumerError("registry has no message schemas")

        suites: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = [
            ("version-negotiation.json", version_case),
            ("capabilities.json", capability_case),
            ("task-capability-gate.json", task_gate_case),
            ("approval-flow.json", approval_case),
        ]

        total = sum(run_cases(filename, evaluator) for filename, evaluator in suites)
        print(
            "independent Python consumer passed "
            f"{total} cases across {len(suites)} vector areas; "
            f"wire={wire_version} schemas={len(message_schemas)}"
        )
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ConsumerError) as exc:
        print(f"independent Python consumer failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
