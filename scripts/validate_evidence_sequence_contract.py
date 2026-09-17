#!/usr/bin/env python3
"""Exercise ordered terminal evidence sequence verification."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "glomancy_task_verification.py"
OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "task-verification-output.schema.json"
PROFILE = ROOT / "verification" / "v1" / "examples" / "strict-restoration-sequence.json"
ROLLED_BACK_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "approved-write-then-rolled-back.json"
)


class ContractError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(directory: Path, name: str, value: Any) -> Path:
    path = directory / name
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def build_sequence_session(
    evidence_types: list[str],
    *,
    terminal_reference_indexes: list[int] | None = None,
) -> dict[str, Any]:
    document = load_json(ROLLED_BACK_SESSION)
    if not isinstance(document, dict):
        raise ContractError("rolled-back transcript must be an object")
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("rolled-back transcript messages must be an array")

    evidence_index = next(
        (index for index, message in enumerate(messages) if isinstance(message, dict) and message.get("kind") == "evidence.record"),
        None,
    )
    terminal_index = next(
        (index for index, message in enumerate(messages) if isinstance(message, dict) and message.get("kind") == "task.error"),
        None,
    )
    if evidence_index is None or terminal_index is None:
        raise ContractError("rolled-back transcript must contain evidence.record and task.error")

    template = messages[evidence_index]
    if not isinstance(template, dict):
        raise ContractError("evidence template must be an object")

    generated: list[dict[str, Any]] = []
    evidence_ids: list[str] = []
    for offset, evidence_type in enumerate(evidence_types, start=1):
        message = copy.deepcopy(template)
        evidence_id = f"51000000-0000-4000-8000-{offset:012d}"
        message_id = f"52000000-0000-4000-8000-{offset:012d}"
        timestamp = f"2026-09-15T10:00:0{5 + offset}Z"
        message["message_id"] = message_id
        message["sent_at"] = timestamp
        payload = message.get("payload")
        if not isinstance(payload, dict):
            raise ContractError("generated evidence payload must be an object")
        payload["evidence_id"] = evidence_id
        payload["evidence_type"] = evidence_type
        payload["captured_at"] = timestamp
        payload["sha256"] = f"{offset:x}" * 64
        payload["claims"] = ["Public structural verification evidence."]
        generated.append(message)
        evidence_ids.append(evidence_id)

    terminal = copy.deepcopy(messages[terminal_index])
    terminal_payload = terminal.get("payload")
    if not isinstance(terminal_payload, dict):
        raise ContractError("task.error payload must be an object")
    if terminal_reference_indexes is None:
        terminal_reference_indexes = list(range(len(evidence_ids)))
    terminal_payload["evidence_ids"] = [evidence_ids[index] for index in terminal_reference_indexes]

    prefix = messages[:evidence_index]
    document["messages"] = [*prefix, *generated, terminal]
    return document


def schema_errors(validator: Draft202012Validator, payload: Any) -> str:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    lines: list[str] = []
    for error in errors[:10]:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        lines.append(f"{location}: {error.message}")
    return "\n".join(lines)


def run_case(
    validator: Draft202012Validator,
    name: str,
    transcript: Path,
    expected_exit: int,
    expected_reason: str | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(TOOL), str(PROFILE), str(transcript), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != expected_exit:
        raise ContractError(
            f"{name}: expected exit {expected_exit}, got {completed.returncode}; "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    if completed.stderr.strip():
        raise ContractError(f"{name}: JSON mode unexpectedly wrote stderr: {completed.stderr!r}")
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise ContractError(f"{name}: stdout is not one JSON object: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"{name}: output must be a JSON object")
    errors = list(validator.iter_errors(payload))
    if errors:
        raise ContractError(f"{name}: output does not match schema:\n{schema_errors(validator, payload)}")
    if expected_reason is not None and payload.get("reason") != expected_reason:
        raise ContractError(
            f"{name}: expected reason={expected_reason!r}, got {payload.get('reason')!r}"
        )
    return payload


def main() -> int:
    try:
        output_schema = load_json(OUTPUT_SCHEMA)
        if not isinstance(output_schema, dict):
            raise ContractError("task verification output schema must be an object")
        Draft202012Validator.check_schema(output_schema)
        validator = Draft202012Validator(output_schema)

        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)

            ordered = write_json(
                directory,
                "ordered.json",
                build_sequence_session(["read-back", "rollback"]),
            )
            ordered_result = run_case(validator, "ordered-sequence", ordered, 0)
            if ordered_result.get("required_terminal_evidence_sequence") != ["read-back", "rollback"]:
                raise ContractError("ordered-sequence: required sequence mismatch")
            if ordered_result.get("observed_terminal_evidence_sequence") != ["read-back", "rollback"]:
                raise ContractError("ordered-sequence: observed sequence mismatch")
            if ordered_result.get("terminal_evidence_sequence_matched") is not True:
                raise ContractError("ordered-sequence: matched must be true")

            reversed_session = write_json(
                directory,
                "reversed.json",
                build_sequence_session(["rollback", "read-back"]),
            )
            reversed_result = run_case(
                validator,
                "reversed-sequence",
                reversed_session,
                2,
                "terminal-evidence-sequence-mismatch",
            )
            if reversed_result.get("terminal_evidence_sequence_matched") is not False:
                raise ContractError("reversed-sequence: matched must be false")

            unlinked = write_json(
                directory,
                "unlinked-read-back.json",
                build_sequence_session(["read-back", "rollback"], terminal_reference_indexes=[1]),
            )
            unlinked_result = run_case(
                validator,
                "unlinked-read-back",
                unlinked,
                2,
                "terminal-evidence-sequence-mismatch",
            )
            if unlinked_result.get("observed_terminal_evidence_sequence") != ["rollback"]:
                raise ContractError("unlinked-read-back: only terminal-linked rollback should be observed")

            subsequence = write_json(
                directory,
                "subsequence.json",
                build_sequence_session(["log", "read-back", "test", "rollback"]),
            )
            subsequence_result = run_case(validator, "ordered-subsequence", subsequence, 0)
            if subsequence_result.get("terminal_evidence_sequence_matched") is not True:
                raise ContractError("ordered-subsequence: required sequence should match")
            if subsequence_result.get("observed_terminal_evidence_sequence") != [
                "log",
                "read-back",
                "test",
                "rollback",
            ]:
                raise ContractError("ordered-subsequence: observed sequence mismatch")

        print(
            "evidence sequence contract passed: ordered match, reversed rejection, "
            "unlinked evidence exclusion, and ordered-subsequence semantics"
        )
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"evidence sequence contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
