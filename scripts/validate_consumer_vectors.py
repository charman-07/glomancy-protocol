#!/usr/bin/env python3
"""Validate the language-neutral consumer vectors against public protocol rules."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "vectors" / "v1"
REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9.-]{0,127}$")


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def version_tuple(value: str) -> tuple[int, int, int]:
    match = VERSION_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid semantic version: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def compatibility(local: str, remote: str) -> tuple[str, bool]:
    local_v = version_tuple(local)
    remote_v = version_tuple(remote)
    if local_v == remote_v:
        return "exact", True
    if local_v[0] == 0 or remote_v[0] == 0:
        if local_v[0] == remote_v[0] == 0 and local_v[1] == remote_v[1]:
            return "patch-compatible", True
        return "incompatible", False
    if local_v[0] == remote_v[0]:
        return "major-compatible", True
    return "incompatible", False


def select_version(local_supported: list[str], remote_supported: list[str]) -> tuple[bool, str | None, str | None]:
    if not local_supported:
        return False, None, "empty-local-version-set"
    if not remote_supported:
        return False, None, "empty-remote-version-set"

    for value in local_supported:
        try:
            version_tuple(value)
        except ValueError:
            return False, None, "invalid-local-version"
    for value in remote_supported:
        try:
            version_tuple(value)
        except ValueError:
            return False, None, "invalid-remote-version"

    if len(set(local_supported)) != len(local_supported):
        return False, None, "duplicate-local-version"
    if len(set(remote_supported)) != len(remote_supported):
        return False, None, "duplicate-remote-version"

    shared = set(local_supported).intersection(remote_supported)
    if not shared:
        return False, None, "no-shared-advertised-version"

    selected = max(shared, key=version_tuple)
    return True, selected, None


def parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value}")
    return parsed


def evaluate_approval(
    request: dict[str, object], decision: dict[str, object]
) -> tuple[bool, bool, str | None]:
    if str(request["approval_id"]) != str(decision["approval_id"]):
        return False, False, "approval-id-mismatch"
    if str(request["task_id"]) != str(decision["task_id"]):
        return False, False, "task-id-mismatch"

    decision_value = str(decision["decision"])
    if decision_value not in {"approve", "deny"}:
        return False, False, "invalid-decision"

    expires_at = parse_timestamp(str(request["expires_at"]))
    decided_at = parse_timestamp(str(decision["decided_at"]))
    if decided_at > expires_at:
        return False, False, "expired"

    if decision_value == "deny":
        return True, False, "denied"
    return True, True, None


def valid_capability_name(name: str) -> bool:
    return len(name.encode("utf-8")) <= 128 and CAPABILITY_RE.fullmatch(name) is not None


def duplicate_name(entries: list[dict[str, object]]) -> str | None:
    seen: set[str] = set()
    for entry in entries:
        name = str(entry["name"])
        if name in seen:
            return name
        seen.add(name)
    return None


def negotiate(
    requested: list[dict[str, object]], available: list[dict[str, object]]
) -> tuple[bool, list[dict[str, str]], str | None]:
    for entry in requested:
        if not valid_capability_name(str(entry["name"])):
            return False, [], "invalid-remote-name"
    for entry in available:
        if not valid_capability_name(str(entry["name"])):
            return False, [], "invalid-local-name"
    if duplicate_name(requested) is not None:
        return False, [], "duplicate-remote-name"
    if duplicate_name(available) is not None:
        return False, [], "duplicate-local-name"

    available_pairs = {(str(entry["name"]), str(entry["version"])) for entry in available}
    selected: list[dict[str, str]] = []
    for entry in requested:
        name = str(entry["name"])
        version = str(entry["version"])
        version_tuple(version)
        if (name, version) in available_pairs:
            selected.append({"name": name, "version": version})
        elif bool(entry["required"]):
            return False, [], "unsupported-required"
    return True, selected, None


def task_gate(requested_names: list[str], selected: list[dict[str, object]]) -> bool:
    selected_names = {str(entry["name"]) for entry in selected}
    return all(valid_capability_name(name) and name in selected_names for name in requested_names)


def lifecycle_outcome(
    accepted: bool,
    terminal_status: str | None,
    evidence_count: int,
    reason: str | None,
) -> dict[str, object]:
    return {
        "accepted": accepted,
        "terminal_status": terminal_status,
        "evidence_count": evidence_count,
        "reason": reason,
    }


def evaluate_task_lifecycle(inputs: dict[str, object]) -> dict[str, object]:
    selected = inputs["selected_capabilities"]
    task = inputs["task"]
    events = inputs["events"]
    if not isinstance(selected, list) or not isinstance(task, dict) or not isinstance(events, list):
        raise TypeError("task lifecycle input has invalid shape")

    task_id = str(task["task_id"])
    requested_capabilities = [str(value) for value in task["requested_capabilities"]]
    approval_required = bool(task["approval_required"])

    if not task_gate(requested_capabilities, selected):
        return lifecycle_outcome(False, None, 0, "unselected-capability")

    approval_request: dict[str, object] | None = None
    approval_granted = not approval_required
    approval_denied = False
    evidence_ids: set[str] = set()
    terminal_status: str | None = None

    for raw_event in events:
        if not isinstance(raw_event, dict):
            raise TypeError("task lifecycle event must be an object")
        event = raw_event

        if terminal_status is not None:
            return lifecycle_outcome(
                False, terminal_status, len(evidence_ids), "event-after-terminal"
            )

        kind = str(event.get("kind", ""))
        if kind not in {
            "approval.request",
            "approval.decision",
            "task.progress",
            "evidence.record",
            "task.result",
        }:
            return lifecycle_outcome(False, None, len(evidence_ids), "unknown-event-kind")

        if str(event.get("task_id", "")) != task_id:
            return lifecycle_outcome(False, None, len(evidence_ids), "task-id-mismatch")

        if kind == "approval.request":
            if approval_request is not None:
                return lifecycle_outcome(
                    False, None, len(evidence_ids), "duplicate-approval-request"
                )
            approval_request = {
                "approval_id": event["approval_id"],
                "task_id": event["task_id"],
                "expires_at": event["expires_at"],
            }
            continue

        if kind == "approval.decision":
            if approval_request is None:
                return lifecycle_outcome(
                    False, None, len(evidence_ids), "approval-not-requested"
                )
            decision_accepted, gate_satisfied, reason = evaluate_approval(
                approval_request, event
            )
            if not decision_accepted:
                return lifecycle_outcome(False, None, len(evidence_ids), reason)
            approval_granted = gate_satisfied
            approval_denied = reason == "denied"
            continue

        if kind == "evidence.record":
            evidence_id = str(event["evidence_id"])
            if evidence_id in evidence_ids:
                return lifecycle_outcome(
                    False, None, len(evidence_ids), "duplicate-evidence-id"
                )
            evidence_ids.add(evidence_id)
            continue

        referenced_evidence = [str(value) for value in event.get("evidence_ids", [])]
        if any(value not in evidence_ids for value in referenced_evidence):
            return lifecycle_outcome(False, None, len(evidence_ids), "missing-evidence")

        if kind == "task.progress":
            status = str(event.get("status", ""))
            if status in {"running", "validating"} and approval_required and not approval_granted:
                reason = "approval-denied" if approval_denied else "approval-required"
                return lifecycle_outcome(False, None, len(evidence_ids), reason)
            continue

        if kind == "task.result":
            if str(event.get("status", "")) != "succeeded":
                return lifecycle_outcome(
                    False, None, len(evidence_ids), "invalid-result-status"
                )
            if approval_required and not approval_granted:
                reason = "approval-denied" if approval_denied else "approval-required"
                return lifecycle_outcome(False, None, len(evidence_ids), reason)
            terminal_status = "succeeded"

    return lifecycle_outcome(True, terminal_status, len(evidence_ids), None)


def require_equal(case_id: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(f"{case_id}: expected {expected!r}, got {actual!r}")


def validate_message_kinds(path: Path, registry: dict[str, object]) -> int:
    kind_to_schema = {
        str(entry["message_kind"]): str(entry["schema_id"])
        for entry in registry["message_schemas"]  # type: ignore[index]
    }
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        kind = str(case["input"]["kind"])
        schema_id = kind_to_schema.get(kind)
        actual = {"accepted": schema_id is not None, "schema_id": schema_id}
        require_equal(str(case["id"]), actual, case["expected"])
    return len(cases)


def validate_wire(path: Path) -> int:
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        result, accepted = compatibility(
            str(case["input"]["local"]), str(case["input"]["remote"])
        )
        require_equal(
            str(case["id"]),
            {"result": result, "accepted": accepted},
            case["expected"],
        )
    return len(cases)


def validate_version_negotiation(path: Path) -> int:
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        accepted, selected_version, reason = select_version(
            [str(value) for value in case["input"]["local_supported"]],
            [str(value) for value in case["input"]["remote_supported"]],
        )
        require_equal(
            str(case["id"]),
            {
                "accepted": accepted,
                "selected_version": selected_version,
                "reason": reason,
            },
            case["expected"],
        )
    return len(cases)


def validate_capabilities(path: Path) -> int:
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        accepted, selected, error = negotiate(
            case["input"]["requested"], case["input"]["available"]
        )
        require_equal(
            str(case["id"]),
            {"accepted": accepted, "selected": selected, "error": error},
            case["expected"],
        )
    return len(cases)


def validate_task_gate(path: Path) -> int:
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        accepted = task_gate(
            [str(name) for name in case["input"]["requested_names"]],
            case["input"]["selected"],
        )
        require_equal(str(case["id"]), {"accepted": accepted}, case["expected"])
    return len(cases)


def validate_approval_flow(path: Path) -> int:
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        accepted, authorized, reason = evaluate_approval(
            case["input"]["request"], case["input"]["decision"]
        )
        require_equal(
            str(case["id"]),
            {"accepted": accepted, "authorized": authorized, "reason": reason},
            case["expected"],
        )
    return len(cases)


def validate_task_lifecycle(path: Path) -> int:
    data = load_json(path)
    cases = data["cases"]  # type: ignore[index]
    for case in cases:
        actual = evaluate_task_lifecycle(case["input"])
        require_equal(str(case["id"]), actual, case["expected"])
    return len(cases)


def main() -> int:
    try:
        manifest = load_json(VECTORS / "manifest.json")
        registry = load_json(REGISTRY)
        require_equal(
            "wire_protocol_version",
            manifest["wire_protocol_version"],  # type: ignore[index]
            registry["wire_protocol_version"],  # type: ignore[index]
        )

        expected_areas = {
            "message-kind-lookup": validate_message_kinds,
            "wire-compatibility": validate_wire,
            "version-negotiation": validate_version_negotiation,
            "capability-negotiation": validate_capabilities,
            "task-capability-gate": validate_task_gate,
            "approval-flow": validate_approval_flow,
            "task-lifecycle": validate_task_lifecycle,
        }
        seen: set[str] = set()
        total = 0
        for entry in manifest["files"]:  # type: ignore[index]
            area = str(entry["area"])
            filename = str(entry["file"])
            if area in seen:
                raise AssertionError(f"duplicate vector area: {area}")
            if area not in expected_areas:
                raise AssertionError(f"unknown vector area: {area}")
            path = VECTORS / filename
            if not path.is_file():
                raise AssertionError(f"missing vector file: {filename}")
            validator = expected_areas[area]
            total += validator(path, registry) if area == "message-kind-lookup" else validator(path)
            seen.add(area)

        require_equal("vector areas", seen, set(expected_areas))
        print(f"consumer vector validation passed for {total} cases across {len(seen)} areas")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, AssertionError) as exc:
        print(f"consumer vector validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
