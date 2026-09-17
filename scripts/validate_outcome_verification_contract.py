#!/usr/bin/env python3
"""Exercise outcome-specific task verification and validate JSON output shapes."""

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
STRICT_ROLLBACK_PROFILE = ROOT / "verification" / "v1" / "examples" / "strict-rollback.json"
ROLLED_BACK_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "approved-write-then-rolled-back.json"
)
SUCCESS_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "approval-gated-success-with-evidence.json"
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


def profile(
    *,
    require_success: bool = False,
    allowed_statuses: list[str] | None = None,
    evidence_by_status: dict[str, list[str]] | None = None,
    rollback_attempt_statuses: list[str] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "profile_version": "1.0.0",
        "require_success": require_success,
        "require_context_snapshot_match": False,
        "require_read_back_verified": False,
        "required_evidence_types": [],
    }
    policy: dict[str, Any] = {}
    if allowed_statuses is not None:
        policy["allowed_statuses"] = allowed_statuses
    if evidence_by_status is not None:
        policy["required_evidence_types_by_status"] = evidence_by_status
    if rollback_attempt_statuses is not None:
        policy["require_rollback_attempted_for_statuses"] = rollback_attempt_statuses
    if policy:
        value["terminal_outcome_policy"] = policy
    return value


def mutate_first_evidence_type(document: dict[str, Any], evidence_type: str) -> None:
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("transcript messages must be an array")
    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "evidence.record":
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("evidence.record payload must be an object")
            payload["evidence_type"] = evidence_type
            return
    raise ContractError("transcript must contain evidence.record")


def mutate_rollback_attempted(document: dict[str, Any], value: bool) -> None:
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("transcript messages must be an array")
    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "task.error":
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("task.error payload must be an object")
            payload["rollback_attempted"] = value
            return
    raise ContractError("transcript must contain task.error")


def schema_errors(validator: Draft202012Validator, payload: Any) -> str:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    lines: list[str] = []
    for error in errors[:10]:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        lines.append(f"{location}: {error.message}")
    if len(errors) > 10:
        lines.append(f"... {len(errors) - 10} more error(s)")
    return "\n".join(lines)


def run_case(
    validator: Draft202012Validator,
    name: str,
    profile_path: Path,
    transcript_path: Path,
    expected_exit: int,
    expected_reason: str | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(TOOL), str(profile_path), str(transcript_path), "--json"],
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
    if payload.get("exit_code") != completed.returncode:
        raise ContractError(f"{name}: JSON exit_code does not match process exit")

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
            rolled_back_document = load_json(ROLLED_BACK_SESSION)
            if not isinstance(rolled_back_document, dict):
                raise ContractError("rolled-back transcript must be an object")

            success = run_case(
                validator,
                "strict-rollback-success",
                STRICT_ROLLBACK_PROFILE,
                ROLLED_BACK_SESSION,
                0,
            )
            if success.get("terminal_status") != "rolled_back":
                raise ContractError("strict rollback must observe rolled_back status")
            if success.get("terminal_kind") != "task.error":
                raise ContractError("strict rollback must terminate as task.error")
            if success.get("rollback_attempted") is not True:
                raise ContractError("strict rollback must report rollback_attempted=true")
            if success.get("rollback_attempt_required") is not True:
                raise ContractError("strict rollback policy must require rollback attempt")
            if success.get("allowed_terminal_statuses") != ["rolled_back"]:
                raise ContractError("strict rollback allowed statuses must be deterministic")
            if success.get("terminal_required_evidence_types") != ["rollback"]:
                raise ContractError("strict rollback must require rollback evidence")

            status_reject_profile = write_json(
                directory,
                "status-reject-profile.json",
                profile(allowed_statuses=["succeeded"]),
            )
            run_case(
                validator,
                "terminal-status-not-allowed",
                status_reject_profile,
                ROLLED_BACK_SESSION,
                2,
                "terminal-status-not-allowed",
            )

            missing_evidence_document = copy.deepcopy(rolled_back_document)
            mutate_first_evidence_type(missing_evidence_document, "log")
            missing_evidence_session = write_json(
                directory,
                "rollback-evidence-missing.json",
                missing_evidence_document,
            )
            status_evidence_profile = write_json(
                directory,
                "status-evidence-profile.json",
                profile(
                    allowed_statuses=["rolled_back"],
                    evidence_by_status={"rolled_back": ["rollback"]},
                ),
            )
            run_case(
                validator,
                "terminal-status-evidence-type-missing",
                status_evidence_profile,
                missing_evidence_session,
                2,
                "terminal-status-evidence-type-missing",
            )

            rollback_false_document = copy.deepcopy(rolled_back_document)
            mutate_rollback_attempted(rollback_false_document, False)
            rollback_false_session = write_json(
                directory,
                "rollback-attempt-false.json",
                rollback_false_document,
            )
            rollback_required_profile = write_json(
                directory,
                "rollback-required-profile.json",
                profile(
                    allowed_statuses=["rolled_back"],
                    rollback_attempt_statuses=["rolled_back"],
                ),
            )
            run_case(
                validator,
                "rollback-attempt-not-reported",
                rollback_required_profile,
                rollback_false_session,
                2,
                "rollback-attempt-not-reported",
            )

            contradiction_profile = write_json(
                directory,
                "contradiction-profile.json",
                profile(require_success=True, allowed_statuses=["rolled_back"]),
            )
            run_case(
                validator,
                "require-success-allowed-status-conflict",
                contradiction_profile,
                SUCCESS_SESSION,
                3,
            )

            legacy_profile = write_json(directory, "legacy-profile.json", profile(require_success=True))
            legacy_success = run_case(
                validator,
                "legacy-success-defaults",
                legacy_profile,
                SUCCESS_SESSION,
                0,
            )
            if legacy_success.get("allowed_terminal_statuses") != []:
                raise ContractError("legacy profile must default allowed statuses to empty")
            if legacy_success.get("terminal_required_evidence_types") != []:
                raise ContractError("legacy profile must default status evidence requirements to empty")
            if legacy_success.get("rollback_attempt_required") is not False:
                raise ContractError("legacy profile must not require rollback attempt")
            if legacy_success.get("rollback_attempted") is not None:
                raise ContractError("successful task.result must report rollback_attempted=null")

        print(
            "outcome verification contract passed: strict rollback, status rejection, "
            "status-specific evidence, rollback-attempt reporting, config conflict, and legacy defaults"
        )
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"outcome verification contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
