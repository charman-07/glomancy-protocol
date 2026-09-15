#!/usr/bin/env python3
"""Validate complete public Glomancy Protocol session transcripts."""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"
REGISTRY = ROOT / "registry" / "v1" / "manifest.json"
CASES = ROOT / "transcripts" / "v1" / "cases.json"


class TranscriptError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TranscriptError(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc


def build_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        schema = load_json(path)
        store[path.name] = schema
        store[path.as_uri()] = schema
        schema_id = schema.get("$id") if isinstance(schema, dict) else None
        if isinstance(schema_id, str) and schema_id:
            store[schema_id] = schema
    return store


def registry_map() -> dict[str, tuple[str, Path]]:
    manifest = load_json(REGISTRY)
    result: dict[str, tuple[str, Path]] = {}
    for entry in manifest.get("message_schemas", []):
        kind = entry.get("message_kind")
        schema_id = entry.get("schema_id")
        file_value = entry.get("file")
        if not all(isinstance(value, str) and value for value in (kind, schema_id, file_value)):
            raise TranscriptError("registry contains an invalid message schema entry")
        path = (REGISTRY.parent / file_value).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError as exc:
            raise TranscriptError(f"registry schema path escapes repository: {file_value}") from exc
        if not path.is_file():
            raise TranscriptError(f"registry schema does not exist: {file_value}")
        result[kind] = (schema_id, path)
    if not result:
        raise TranscriptError("registry contains no message schemas")
    return result


def validator_for(path: Path, store: dict[str, Any]) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        resolver=RefResolver(base_uri=path.as_uri(), referrer=schema, store=store),
        format_checker=FormatChecker(),
    )


def iso(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def reject(reason: str, index: int | None = None, detail: str | None = None) -> dict[str, Any]:
    return {
        "accepted": False,
        "terminal_status": None,
        "selected_version": None,
        "selected_capabilities": [],
        "evidence_count": 0,
        "reason": reason,
        "message_index": index,
        "detail": detail,
    }


def validate_transcript(messages: list[Any], validators: dict[str, tuple[str, Draft202012Validator]]) -> dict[str, Any]:
    handshake_request: dict[str, Any] | None = None
    selected_version: str | None = None
    selected_caps: set[str] = set()
    task_id: str | None = None
    approvals: dict[str, dict[str, Any]] = {}
    approved_ids: set[str] = set()
    evidence_ids: set[str] = set()
    terminal_status: str | None = None
    trace_id: str | None = None

    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            return reject("schema-validation", index, "message is not an object")

        kind = message.get("kind")
        if not isinstance(kind, str) or kind not in validators:
            return reject("schema-resolution", index, f"unregistered kind: {kind!r}")

        expected_schema_id, validator = validators[kind]
        if message.get("schema_id") != expected_schema_id:
            return reject("schema-resolution", index, f"schema_id does not match registry for {kind}")

        errors = sorted(validator.iter_errors(message), key=lambda error: list(error.absolute_path))
        if errors:
            first = errors[0]
            location = "/".join(str(part) for part in first.absolute_path) or "<root>"
            return reject(
                "schema-validation",
                index,
                f"kind={kind} keyword={first.validator!r} path={location}: {first.message}",
            )

        current_trace = message["trace"]["trace_id"]
        if trace_id is None:
            trace_id = current_trace
        elif current_trace != trace_id:
            return reject("trace-id-mismatch", index)

        payload = message["payload"]

        task_event = kind in {
            "task.progress",
            "task.result",
            "task.error",
            "task.cancel",
            "approval.request",
            "approval.decision",
            "evidence.record",
        }
        if terminal_status is not None and task_event:
            return reject("event-after-terminal", index)

        if kind == "handshake.request":
            if handshake_request is not None:
                return reject("duplicate-handshake-request", index)
            handshake_request = message
            continue

        if kind == "handshake.response":
            if handshake_request is None:
                return reject("handshake-response-before-request", index)
            if message.get("correlation_id") != handshake_request["message_id"]:
                return reject("handshake-correlation-mismatch", index)
            if not payload["accepted"]:
                return reject("handshake-rejected", index)
            advertised_versions = set(handshake_request["payload"]["supported_versions"])
            if payload["selected_version"] not in advertised_versions:
                return reject("unadvertised-selected-version", index)
            advertised_caps = {
                (cap["name"], cap["version"]): cap
                for cap in handshake_request["payload"]["capabilities"]
            }
            selected_keys: set[tuple[str, str]] = set()
            for capability in payload["selected_capabilities"]:
                key = (capability["name"], capability["version"])
                if key not in advertised_caps:
                    return reject("unadvertised-selected-capability", index)
                if key in selected_keys:
                    return reject("duplicate-selected-capability", index)
                selected_keys.add(key)
            required_keys = {
                key for key, cap in advertised_caps.items() if cap.get("required") is True
            }
            if not required_keys.issubset(selected_keys):
                return reject("missing-required-selected-capability", index)
            selected_version = payload["selected_version"]
            selected_caps = {name for name, _version in selected_keys}
            continue

        if kind == "task.submit":
            if selected_version is None:
                return reject("task-before-handshake", index)
            if task_id is not None:
                return reject("duplicate-task-submit", index)
            task_id = payload["task_id"]
            requested = set(payload["requested_capabilities"])
            if not requested.issubset(selected_caps):
                return reject("task-requests-unselected-capability", index)
            continue

        if kind == "heartbeat":
            continue

        if task_id is None:
            return reject("task-event-before-submit", index)

        if payload.get("task_id") != task_id:
            if kind in {"approval.request", "approval.decision"}:
                return reject("approval-task-id-mismatch", index)
            return reject("task-id-mismatch", index)

        if kind == "approval.request":
            approval_id = payload["approval_id"]
            if approval_id in approvals:
                return reject("duplicate-approval-request", index)
            approvals[approval_id] = {
                "message_id": message["message_id"],
                "expires_at": payload["expires_at"],
            }
            continue

        if kind == "approval.decision":
            approval_id = payload["approval_id"]
            request = approvals.get(approval_id)
            if request is None:
                if approvals:
                    return reject("approval-id-mismatch", index)
                return reject("approval-decision-before-request", index)
            correlation_id = message.get("correlation_id")
            if correlation_id is not None and correlation_id != request["message_id"]:
                return reject("approval-correlation-mismatch", index)
            try:
                if iso(payload["decided_at"]) > iso(request["expires_at"]):
                    return reject("expired-approval", index)
            except ValueError:
                return reject("schema-validation", index, "invalid approval timestamp")
            if payload["decision"] == "approve":
                approved_ids.add(approval_id)
            else:
                approved_ids.discard(approval_id)
            continue

        if kind == "task.cancel":
            continue

        if kind == "evidence.record":
            evidence_id = payload["evidence_id"]
            if evidence_id in evidence_ids:
                return reject("duplicate-evidence", index)
            evidence_ids.add(evidence_id)
            continue

        refs = payload.get("evidence_ids", [])
        unknown = [evidence_id for evidence_id in refs if evidence_id not in evidence_ids]
        if unknown:
            return reject("unknown-evidence-reference", index, ",".join(unknown))

        if kind == "task.progress":
            if payload["status"] in {"running", "validating"} and approvals and not approved_ids:
                return reject("running-before-required-approval", index)
            continue

        if kind == "task.result":
            if approvals and not approved_ids:
                return reject("running-before-required-approval", index)
            terminal_status = payload["status"]
            continue

        if kind == "task.error":
            terminal_status = payload["status"]
            continue

    if handshake_request is None or selected_version is None:
        return reject("incomplete-handshake")
    if task_id is None:
        return reject("missing-task")
    if terminal_status is None:
        return reject("missing-terminal-outcome")

    return {
        "accepted": True,
        "terminal_status": terminal_status,
        "selected_version": selected_version,
        "selected_capabilities": sorted(selected_caps),
        "evidence_count": len(evidence_ids),
        "reason": None,
        "message_index": None,
        "detail": None,
    }


def validate_suite() -> tuple[int, int]:
    suite = load_json(CASES)
    if not isinstance(suite, dict) or suite.get("schema_version") != 1:
        raise TranscriptError("unsupported transcript suite schema_version")
    accepted_cases = suite.get("accepted")
    rejected_cases = suite.get("rejected")
    if not isinstance(accepted_cases, list) or not isinstance(rejected_cases, list):
        raise TranscriptError("transcript accepted/rejected cases must be arrays")

    store = build_store()
    mapping = registry_map()
    validators = {
        kind: (schema_id, validator_for(path, store))
        for kind, (schema_id, path) in mapping.items()
    }

    names: set[str] = set()
    for expected_acceptance, cases in ((True, accepted_cases), (False, rejected_cases)):
        for case in cases:
            if not isinstance(case, dict):
                raise TranscriptError("transcript case must be an object")
            name = case.get("name")
            if not isinstance(name, str) or not name:
                raise TranscriptError("transcript case name must be a non-empty string")
            if name in names:
                raise TranscriptError(f"duplicate transcript case: {name}")
            names.add(name)

            messages = case.get("messages")
            expected = case.get("expected")
            if not isinstance(messages, list) or not messages:
                raise TranscriptError(f"{name}: messages must be a non-empty array")
            if not isinstance(expected, dict):
                raise TranscriptError(f"{name}: expected must be an object")

            result = validate_transcript(messages, validators)
            if result["accepted"] is not expected_acceptance:
                raise TranscriptError(
                    f"{name}: acceptance mismatch: expected={expected_acceptance} "
                    f"actual={result['accepted']} reason={result['reason']} "
                    f"message_index={result['message_index']} detail={result['detail']}"
                )
            for key in ("accepted", "terminal_status", "reason"):
                if result.get(key) != expected.get(key):
                    raise TranscriptError(
                        f"{name}: expected {key}={expected.get(key)!r}, got {result.get(key)!r}; "
                        f"message_index={result['message_index']} detail={result['detail']}"
                    )

            print(json.dumps({"case": name, **result}, sort_keys=True))

    return len(accepted_cases), len(rejected_cases)


def main() -> int:
    try:
        accepted_count, rejected_count = validate_suite()
    except (KeyError, TypeError, TranscriptError) as exc:
        print(f"session transcript conformance failed: {exc}", file=sys.stderr)
        return 1

    print(
        "session transcript conformance passed: "
        f"{accepted_count} accepted cases, {rejected_count} rejected cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
