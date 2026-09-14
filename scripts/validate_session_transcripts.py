#!/usr/bin/env python3
"""Validate full-session Glomancy Protocol transcript conformance.

This validator deliberately operates above individual JSON Schema validation. Every
message template is first validated against the canonical public schema registry;
then ordered transcript cases are checked for transport-neutral cross-message
invariants such as negotiation, correlation, approval, evidence closure, and
terminal task behavior.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from glomancy_conformance import choose_entry, resolve_schema_file
from validate_fixtures import ConformanceError, ROOT, build_store, load_json, validator_for

TRANSCRIPTS = ROOT / "transcripts" / "v1"
MANIFEST = TRANSCRIPTS / "manifest.json"
MESSAGES = TRANSCRIPTS / "messages.json"
CASES = TRANSCRIPTS / "cases.json"


class TranscriptError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise TranscriptError(f"timestamp must include a timezone: {value!r}")
    return parsed


def capability_pair(entry: dict[str, Any]) -> str:
    return f"{entry['name']}@{entry['version']}"


def selected_names(selected: set[str]) -> set[str]:
    return {value.split("@", 1)[0] for value in selected}


def outcome(
    *,
    accepted: bool,
    selected_version: str | None,
    selected_capabilities: set[str],
    task_id: str | None,
    terminal_status: str | None,
    evidence_count: int,
    cancel_requested: bool,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "accepted": accepted,
        "selected_version": selected_version,
        "selected_capabilities": sorted(selected_capabilities),
        "task_id": task_id,
        "terminal_status": terminal_status,
        "evidence_count": evidence_count,
        "cancel_requested": cancel_requested,
        "reason": reason,
    }


def validate_manifest() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = load_json(MANIFEST)
    messages = load_json(MESSAGES)
    cases = load_json(CASES)
    if not isinstance(manifest, dict) or not isinstance(messages, dict) or not isinstance(cases, dict):
        raise TranscriptError("transcript manifest/messages/cases must be JSON objects")

    transcript_version = manifest.get("transcript_version")
    wire_version = manifest.get("wire_protocol_version")
    if transcript_version != messages.get("transcript_message_set_version"):
        raise TranscriptError("transcript message-set version does not match manifest")
    if transcript_version != cases.get("transcript_version"):
        raise TranscriptError("transcript case version does not match manifest")
    if wire_version != messages.get("wire_protocol_version") or wire_version != cases.get("wire_protocol_version"):
        raise TranscriptError("transcript wire protocol versions do not match")

    files = manifest.get("files")
    if not isinstance(files, list):
        raise TranscriptError("transcript manifest files must be an array")
    expected = {"messages": MESSAGES, "cases": CASES}
    seen: set[str] = set()
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            raise TranscriptError(f"manifest file entry {index} must be an object")
        role = entry.get("role")
        filename = entry.get("file")
        digest = entry.get("sha256")
        if role not in expected:
            raise TranscriptError(f"unknown transcript manifest role: {role!r}")
        if role in seen:
            raise TranscriptError(f"duplicate transcript manifest role: {role}")
        path = expected[role]
        if filename != path.name:
            raise TranscriptError(f"manifest role {role} must point to {path.name}")
        actual_digest = sha256_file(path)
        if digest != actual_digest:
            raise TranscriptError(
                f"transcript manifest SHA-256 mismatch for {filename}: expected {actual_digest}, got {digest}"
            )
        seen.add(str(role))
    if seen != set(expected):
        raise TranscriptError(f"transcript manifest roles mismatch: {sorted(seen)}")

    return manifest, messages, cases


def validate_message_templates(messages_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_messages = messages_doc.get("messages")
    if not isinstance(raw_messages, dict) or not raw_messages:
        raise TranscriptError("messages.json must contain a non-empty messages object")

    store = build_store()
    validated: dict[str, dict[str, Any]] = {}
    for key, message in raw_messages.items():
        if not isinstance(key, str) or not key:
            raise TranscriptError("message template keys must be non-empty strings")
        if not isinstance(message, dict):
            raise TranscriptError(f"message template {key} must be an object")
        try:
            entry = choose_entry(message, None, None)
            schema_path = resolve_schema_file(entry)
            validator = validator_for(schema_path, store)
            errors = sorted(validator.iter_errors(message), key=lambda error: list(error.path))
        except (KeyError, TypeError, ConformanceError, json.JSONDecodeError, OSError) as exc:
            raise TranscriptError(f"cannot validate message template {key}: {exc}") from exc
        if errors:
            error = errors[0]
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            raise TranscriptError(
                f"message template {key} violates {entry.get('schema_id')}: path={location}: {error.message}"
            )
        validated[key] = message
    return validated


def reject(
    reason: str,
    *,
    selected_version: str | None,
    selected_capabilities: set[str],
    task_id: str | None,
    terminal_status: str | None,
    evidence_ids: set[str],
    cancel_requested: bool,
) -> dict[str, Any]:
    return outcome(
        accepted=False,
        selected_version=selected_version,
        selected_capabilities=selected_capabilities,
        task_id=task_id,
        terminal_status=terminal_status,
        evidence_count=len(evidence_ids),
        cancel_requested=cancel_requested,
        reason=reason,
    )


def evaluate(sequence: list[str], templates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    handshake_request: dict[str, Any] | None = None
    handshake_response_seen = False
    selected_version: str | None = None
    selected_capabilities: set[str] = set()
    task_id: str | None = None
    approval_request: dict[str, Any] | None = None
    approval_state = "none"  # none | pending | approved | denied
    evidence_ids: set[str] = set()
    terminal_status: str | None = None
    cancel_requested = False

    for position, key in enumerate(sequence):
        message = templates[key]
        kind = str(message["kind"])
        payload = message["payload"]
        if not isinstance(payload, dict):
            raise TranscriptError(f"{key}: payload must be an object")

        if terminal_status is not None and kind != "heartbeat":
            return reject(
                "event-after-terminal",
                selected_version=selected_version,
                selected_capabilities=selected_capabilities,
                task_id=task_id,
                terminal_status=terminal_status,
                evidence_ids=evidence_ids,
                cancel_requested=cancel_requested,
            )

        if position == 0 and kind != "handshake.request":
            return reject(
                "handshake-request-required",
                selected_version=None,
                selected_capabilities=set(),
                task_id=None,
                terminal_status=None,
                evidence_ids=set(),
                cancel_requested=False,
            )

        if kind == "handshake.request":
            if handshake_request is not None or position != 0:
                return reject(
                    "duplicate-handshake-request",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            handshake_request = message
            continue

        if kind == "handshake.response":
            if handshake_request is None or handshake_response_seen:
                return reject(
                    "unexpected-handshake-response",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            if message.get("correlation_id") != handshake_request.get("message_id"):
                return reject(
                    "handshake-correlation-mismatch",
                    selected_version=None,
                    selected_capabilities=set(),
                    task_id=None,
                    terminal_status=None,
                    evidence_ids=set(),
                    cancel_requested=False,
                )
            if payload.get("accepted") is not True:
                return reject(
                    "handshake-rejected",
                    selected_version=None,
                    selected_capabilities=set(),
                    task_id=None,
                    terminal_status=None,
                    evidence_ids=set(),
                    cancel_requested=False,
                )
            requested_versions = set(str(value) for value in handshake_request["payload"]["supported_versions"])
            candidate_version = str(payload.get("selected_version"))
            if candidate_version not in requested_versions:
                return reject(
                    "unadvertised-selected-version",
                    selected_version=None,
                    selected_capabilities=set(),
                    task_id=None,
                    terminal_status=None,
                    evidence_ids=set(),
                    cancel_requested=False,
                )
            requested_pairs = {
                capability_pair(entry)
                for entry in handshake_request["payload"]["capabilities"]
            }
            candidate_pairs = {
                capability_pair(entry)
                for entry in payload.get("selected_capabilities", [])
            }
            if not candidate_pairs.issubset(requested_pairs):
                return reject(
                    "unrequested-selected-capability",
                    selected_version=None,
                    selected_capabilities=set(),
                    task_id=None,
                    terminal_status=None,
                    evidence_ids=set(),
                    cancel_requested=False,
                )
            selected_version = candidate_version
            selected_capabilities = candidate_pairs
            handshake_response_seen = True
            continue

        if not handshake_response_seen or selected_version is None:
            return reject(
                "handshake-incomplete",
                selected_version=selected_version,
                selected_capabilities=selected_capabilities,
                task_id=task_id,
                terminal_status=terminal_status,
                evidence_ids=evidence_ids,
                cancel_requested=cancel_requested,
            )

        if str(message.get("protocol_version")) != selected_version:
            return reject(
                "session-wire-version-mismatch",
                selected_version=selected_version,
                selected_capabilities=selected_capabilities,
                task_id=task_id,
                terminal_status=terminal_status,
                evidence_ids=evidence_ids,
                cancel_requested=cancel_requested,
            )

        if kind == "heartbeat":
            continue

        if kind == "task.submit":
            if task_id is not None:
                return reject(
                    "multiple-tasks-not-supported-by-transcript-v1",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            task_id = str(payload["task_id"])
            requested_names = {str(value) for value in payload["requested_capabilities"]}
            if not requested_names.issubset(selected_names(selected_capabilities)):
                return reject(
                    "unselected-task-capability",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            continue

        if task_id is None:
            return reject(
                "task-submit-required",
                selected_version=selected_version,
                selected_capabilities=selected_capabilities,
                task_id=None,
                terminal_status=terminal_status,
                evidence_ids=evidence_ids,
                cancel_requested=cancel_requested,
            )

        event_task_id = payload.get("task_id")
        if event_task_id is not None and str(event_task_id) != task_id:
            return reject(
                "task-id-mismatch",
                selected_version=selected_version,
                selected_capabilities=selected_capabilities,
                task_id=task_id,
                terminal_status=terminal_status,
                evidence_ids=evidence_ids,
                cancel_requested=cancel_requested,
            )

        if kind == "approval.request":
            if approval_request is not None:
                return reject(
                    "duplicate-approval-request",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            approval_request = payload
            approval_state = "pending"
            continue

        if kind == "approval.decision":
            if approval_request is None:
                return reject(
                    "approval-not-requested",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            if payload.get("approval_id") != approval_request.get("approval_id"):
                return reject(
                    "approval-id-mismatch",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            if timestamp(str(payload["decided_at"])) > timestamp(str(approval_request["expires_at"])):
                return reject(
                    "approval-expired",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            approval_state = "approved" if payload.get("decision") == "approve" else "denied"
            continue

        if kind == "task.cancel":
            cancel_requested = True
            continue

        if kind == "evidence.record":
            evidence_id = str(payload["evidence_id"])
            if evidence_id in evidence_ids:
                return reject(
                    "duplicate-evidence-id",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            evidence_ids.add(evidence_id)
            continue

        referenced = {str(value) for value in payload.get("evidence_ids", [])}
        if not referenced.issubset(evidence_ids):
            return reject(
                "missing-evidence",
                selected_version=selected_version,
                selected_capabilities=selected_capabilities,
                task_id=task_id,
                terminal_status=terminal_status,
                evidence_ids=evidence_ids,
                cancel_requested=cancel_requested,
            )

        if kind == "task.progress":
            status = str(payload.get("status"))
            if status in {"running", "validating"}:
                if approval_state == "pending":
                    return reject(
                        "approval-required",
                        selected_version=selected_version,
                        selected_capabilities=selected_capabilities,
                        task_id=task_id,
                        terminal_status=terminal_status,
                        evidence_ids=evidence_ids,
                        cancel_requested=cancel_requested,
                    )
                if approval_state == "denied":
                    return reject(
                        "approval-denied",
                        selected_version=selected_version,
                        selected_capabilities=selected_capabilities,
                        task_id=task_id,
                        terminal_status=terminal_status,
                        evidence_ids=evidence_ids,
                        cancel_requested=cancel_requested,
                    )
            continue

        if kind == "task.result":
            if approval_state == "pending":
                return reject(
                    "approval-required",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            if approval_state == "denied":
                return reject(
                    "approval-denied",
                    selected_version=selected_version,
                    selected_capabilities=selected_capabilities,
                    task_id=task_id,
                    terminal_status=terminal_status,
                    evidence_ids=evidence_ids,
                    cancel_requested=cancel_requested,
                )
            terminal_status = "succeeded"
            continue

        if kind == "task.error":
            terminal_status = str(payload.get("status"))
            continue

        return reject(
            "unsupported-session-message-kind",
            selected_version=selected_version,
            selected_capabilities=selected_capabilities,
            task_id=task_id,
            terminal_status=terminal_status,
            evidence_ids=evidence_ids,
            cancel_requested=cancel_requested,
        )

    return outcome(
        accepted=True,
        selected_version=selected_version,
        selected_capabilities=selected_capabilities,
        task_id=task_id,
        terminal_status=terminal_status,
        evidence_count=len(evidence_ids),
        cancel_requested=cancel_requested,
        reason=None,
    )


def validate_cases(cases_doc: dict[str, Any], templates: dict[str, dict[str, Any]]) -> int:
    raw_cases = cases_doc.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise TranscriptError("cases.json must contain a non-empty cases array")
    seen_ids: set[str] = set()
    for index, case in enumerate(raw_cases):
        if not isinstance(case, dict):
            raise TranscriptError(f"case {index} must be an object")
        case_id = str(case.get("id", ""))
        if not case_id or case_id in seen_ids:
            raise TranscriptError(f"invalid or duplicate transcript case id: {case_id!r}")
        seen_ids.add(case_id)
        sequence = case.get("sequence")
        expected = case.get("expected")
        if not isinstance(sequence, list) or not sequence:
            raise TranscriptError(f"{case_id}: sequence must be a non-empty array")
        if not isinstance(expected, dict):
            raise TranscriptError(f"{case_id}: expected must be an object")
        keys = [str(value) for value in sequence]
        missing = [value for value in keys if value not in templates]
        if missing:
            raise TranscriptError(f"{case_id}: unknown message template(s): {missing}")
        actual = evaluate(keys, templates)
        if actual != expected:
            raise TranscriptError(f"{case_id}: expected {expected!r}, got {actual!r}")
    return len(raw_cases)


def main() -> int:
    try:
        manifest, messages_doc, cases_doc = validate_manifest()
        templates = validate_message_templates(messages_doc)
        case_count = validate_cases(cases_doc, templates)
        print(
            "session transcript conformance passed: "
            f"version={manifest['transcript_version']} "
            f"wire={manifest['wire_protocol_version']} "
            f"messages={len(templates)} cases={case_count}"
        )
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, TranscriptError) as exc:
        print(f"session transcript conformance failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
