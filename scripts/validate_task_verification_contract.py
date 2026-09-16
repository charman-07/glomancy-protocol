#!/usr/bin/env python3
"""Exercise portable task verification and validate every JSON output shape."""

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
SUCCESS_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "approval-gated-success-with-evidence.json"
)
FAILURE_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "terminal-failure-with-evidence.json"
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


def session_with_context() -> dict[str, Any]:
    document = load_json(SUCCESS_SESSION)
    if not isinstance(document, dict):
        raise ContractError("success session fixture must be an object")
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("success session fixture messages must be an array")

    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "task.submit":
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("task.submit payload must be an object")
            payload["context_refs"] = [
                {
                    "source_type": "project",
                    "uri": "glomancy://project/verification-demo",
                    "revision": "project-r3",
                },
                {
                    "source_type": "asset",
                    "uri": "glomancy://asset/verification-selected-object",
                    "revision": "asset-r8",
                },
            ]
            return document
    raise ContractError("success session fixture must contain task.submit")


def snapshot_document() -> dict[str, Any]:
    return {
        "snapshot_format_version": "1.0.0",
        "snapshot_id": "88888888-8888-4888-8888-888888888888",
        "captured_at": "2026-09-15T10:00:02Z",
        "sources": [
            {
                "source_type": "project",
                "uri": "glomancy://project/verification-demo",
                "revision": "project-r3",
            },
            {
                "source_type": "asset",
                "uri": "glomancy://asset/verification-selected-object",
                "revision": "asset-r8",
            },
            {
                "source_type": "memory",
                "uri": "glomancy://memory/extra-snapshot-context",
            },
        ],
    }


def profile(
    *,
    require_success: bool = True,
    require_snapshot: bool = False,
    require_read_back: bool = False,
    evidence_types: list[str] | None = None,
    evidence_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "profile_version": "1.0.0",
        "require_success": require_success,
        "require_context_snapshot_match": require_snapshot,
        "require_read_back_verified": require_read_back,
        "required_evidence_types": evidence_types or [],
    }
    if evidence_coverage is not None:
        value["evidence_coverage"] = evidence_coverage
    return value


def mutate_terminal_result(document: dict[str, Any], *, read_back_verified: bool | None = None) -> None:
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("session messages must be an array")
    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "task.result":
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("task.result payload must be an object")
            if read_back_verified is not None:
                payload["read_back_verified"] = read_back_verified
            return
    raise ContractError("session must contain task.result")


def mutate_evidence_type(document: dict[str, Any], evidence_type: str) -> None:
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("session messages must be an array")
    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "evidence.record":
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("evidence.record payload must be an object")
            payload["evidence_type"] = evidence_type
            return
    raise ContractError("session must contain evidence.record")


def add_unreferenced_evidence(document: dict[str, Any]) -> None:
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("session messages must be an array")

    source: dict[str, Any] | None = None
    terminal_index: int | None = None
    for index, message in enumerate(messages):
        if isinstance(message, dict) and message.get("kind") == "evidence.record" and source is None:
            source = message
        if isinstance(message, dict) and message.get("kind") in {"task.result", "task.error"}:
            terminal_index = index
            break
    if source is None or terminal_index is None:
        raise ContractError("session must contain evidence and terminal messages")

    extra = copy.deepcopy(source)
    extra["message_id"] = "50000000-0000-4000-8000-000000000099"
    extra["sent_at"] = "2026-09-15T10:00:07Z"
    payload = extra.get("payload")
    if not isinstance(payload, dict):
        raise ContractError("evidence.record payload must be an object")
    payload["evidence_id"] = "50000000-0000-4000-8000-000000000098"
    payload["evidence_type"] = "log"
    payload["captured_at"] = "2026-09-15T10:00:07Z"
    payload["sha256"] = "2" * 64
    payload["claims"] = ["Additional public log evidence."]
    messages.insert(terminal_index, extra)


def mutate_invalid_selected_version(document: dict[str, Any]) -> None:
    messages = document.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        raise ContractError("session must contain handshake messages")
    response = messages[1]
    if not isinstance(response, dict) or not isinstance(response.get("payload"), dict):
        raise ContractError("handshake response payload must be an object")
    response["payload"]["selected_version"] = "9.9.9"


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
    arguments: list[str],
    expected_exit: int,
    expected_reason: str | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(TOOL), *arguments, "--json"],
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
        raise ContractError(f"{name}: JSON mode unexpectedly wrote to stderr: {completed.stderr!r}")

    stdout = completed.stdout.strip()
    if not stdout:
        raise ContractError(f"{name}: JSON mode produced no stdout")
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ContractError(f"{name}: stdout is not one JSON object: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"{name}: top-level JSON output must be an object")
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

            base_session_document = session_with_context()
            base_session = write_json(directory, "session.json", base_session_document)
            snapshot = write_json(directory, "snapshot.json", snapshot_document())

            strict_profile = write_json(
                directory,
                "strict-profile.json",
                profile(
                    require_success=True,
                    require_snapshot=True,
                    require_read_back=True,
                    evidence_types=["read-back"],
                ),
            )
            success_only_profile = write_json(
                directory,
                "success-only-profile.json",
                profile(require_success=True),
            )
            test_evidence_profile = write_json(
                directory,
                "test-evidence-profile.json",
                profile(require_success=True, evidence_types=["test"]),
            )
            read_back_profile = write_json(
                directory,
                "read-back-profile.json",
                profile(require_success=True, require_read_back=True),
            )
            coverage_profile = write_json(
                directory,
                "coverage-profile.json",
                profile(
                    require_success=True,
                    require_read_back=True,
                    evidence_types=["read-back"],
                    evidence_coverage={
                        "minimum_terminal_referenced_evidence_count": 1,
                        "minimum_terminal_referenced_evidence_type_counts": {"read-back": 1},
                        "maximum_unreferenced_evidence_count": 0,
                    },
                ),
            )
            coverage_total_profile = write_json(
                directory,
                "coverage-total-profile.json",
                profile(
                    evidence_coverage={"minimum_terminal_referenced_evidence_count": 2},
                ),
            )
            coverage_type_profile = write_json(
                directory,
                "coverage-type-profile.json",
                profile(
                    evidence_coverage={
                        "minimum_terminal_referenced_evidence_type_counts": {"read-back": 2}
                    },
                ),
            )
            coverage_all_referenced_profile = write_json(
                directory,
                "coverage-all-referenced-profile.json",
                profile(
                    evidence_coverage={"maximum_unreferenced_evidence_count": 0},
                ),
            )

            success = run_case(
                validator,
                "verification-success",
                [str(strict_profile), str(base_session), "--snapshot", str(snapshot)],
                0,
            )
            if success.get("snapshot_match") is not True:
                raise ContractError("verification-success: snapshot_match must be true")
            if success.get("terminal_status") != "succeeded":
                raise ContractError("verification-success: terminal status must be succeeded")
            if success.get("read_back_verified") is not True:
                raise ContractError("verification-success: read_back_verified must be true")
            if success.get("terminal_referenced_evidence_type_counts") != {"read-back": 1}:
                raise ContractError(
                    "verification-success: expected one terminal-referenced read-back evidence"
                )
            if success.get("minimum_terminal_referenced_evidence_count") != 0:
                raise ContractError("verification-success: legacy profile must default minimum count to 0")
            if success.get("minimum_terminal_referenced_evidence_type_counts") != {}:
                raise ContractError("verification-success: legacy profile must default type counts to empty")
            if success.get("maximum_unreferenced_evidence_count") is not None:
                raise ContractError("verification-success: legacy profile must default max unreferenced to null")
            if success.get("unreferenced_evidence_count") != 0:
                raise ContractError("verification-success: expected zero unreferenced evidence")

            coverage_success = run_case(
                validator,
                "evidence-coverage-success",
                [str(coverage_profile), str(base_session)],
                0,
            )
            if coverage_success.get("minimum_terminal_referenced_evidence_count") != 1:
                raise ContractError("evidence-coverage-success: minimum count was not preserved")
            if coverage_success.get("minimum_terminal_referenced_evidence_type_counts") != {"read-back": 1}:
                raise ContractError("evidence-coverage-success: type counts were not preserved")
            if coverage_success.get("maximum_unreferenced_evidence_count") != 0:
                raise ContractError("evidence-coverage-success: maximum unreferenced was not preserved")

            run_case(
                validator,
                "evidence-total-below-minimum",
                [str(coverage_total_profile), str(base_session)],
                2,
                "terminal-evidence-count-below-minimum",
            )

            run_case(
                validator,
                "evidence-type-count-below-minimum",
                [str(coverage_type_profile), str(base_session)],
                2,
                "terminal-evidence-type-count-below-minimum",
            )

            unreferenced_document = copy.deepcopy(base_session_document)
            add_unreferenced_evidence(unreferenced_document)
            unreferenced_session = write_json(
                directory,
                "unreferenced-evidence.json",
                unreferenced_document,
            )
            unreferenced_result = run_case(
                validator,
                "unreferenced-evidence-exceeds-maximum",
                [str(coverage_all_referenced_profile), str(unreferenced_session)],
                2,
                "unreferenced-evidence-count-exceeds-maximum",
            )
            if unreferenced_result.get("evidence_count") != 2:
                raise ContractError("unreferenced evidence case must observe two evidence records")
            if unreferenced_result.get("terminal_referenced_evidence_count") != 1:
                raise ContractError("unreferenced evidence case must terminal-reference one evidence record")
            if unreferenced_result.get("unreferenced_evidence_count") != 1:
                raise ContractError("unreferenced evidence case must report one unreferenced record")

            run_case(
                validator,
                "snapshot-required",
                [str(strict_profile), str(base_session)],
                2,
                "context-snapshot-required",
            )

            mismatch_snapshot_document = snapshot_document()
            for source in mismatch_snapshot_document["sources"]:
                if source.get("source_type") == "asset":
                    source["revision"] = "asset-r9"
            mismatch_snapshot = write_json(
                directory,
                "snapshot-mismatch.json",
                mismatch_snapshot_document,
            )
            run_case(
                validator,
                "snapshot-mismatch",
                [
                    str(strict_profile),
                    str(base_session),
                    "--snapshot",
                    str(mismatch_snapshot),
                ],
                2,
                "context-snapshot-mismatch",
            )

            run_case(
                validator,
                "terminal-not-succeeded",
                [str(success_only_profile), str(FAILURE_SESSION)],
                2,
                "terminal-status-not-succeeded",
            )

            run_case(
                validator,
                "required-evidence-missing",
                [str(test_evidence_profile), str(base_session)],
                2,
                "required-evidence-type-missing",
            )

            flag_false_document = copy.deepcopy(base_session_document)
            mutate_terminal_result(flag_false_document, read_back_verified=False)
            flag_false_session = write_json(directory, "read-back-flag-false.json", flag_false_document)
            run_case(
                validator,
                "read-back-flag-not-set",
                [str(read_back_profile), str(flag_false_session)],
                2,
                "read-back-flag-not-set",
            )

            no_read_back_record_document = copy.deepcopy(base_session_document)
            mutate_evidence_type(no_read_back_record_document, "log")
            no_read_back_record_session = write_json(
                directory,
                "read-back-evidence-not-referenced.json",
                no_read_back_record_document,
            )
            run_case(
                validator,
                "read-back-evidence-not-referenced",
                [str(read_back_profile), str(no_read_back_record_session)],
                2,
                "read-back-evidence-not-referenced",
            )

            invalid_session_document = copy.deepcopy(base_session_document)
            mutate_invalid_selected_version(invalid_session_document)
            invalid_session = write_json(directory, "invalid-session.json", invalid_session_document)
            invalid_result = run_case(
                validator,
                "session-conformance-failed",
                [str(success_only_profile), str(invalid_session)],
                2,
                "session-conformance-failed",
            )
            if "unadvertised-selected-version" not in (invalid_result.get("detail") or ""):
                raise ContractError("session failure did not preserve canonical reason in detail")

            invalid_profile_document = profile(require_success=True)
            invalid_profile_document["profile_version"] = "2.0.0"
            invalid_profile = write_json(directory, "invalid-profile.json", invalid_profile_document)

            invalid_coverage_profile_document = profile(
                evidence_coverage={"minimum_terminal_referenced_evidence_count": -1}
            )
            invalid_coverage_profile = write_json(
                directory,
                "invalid-coverage-profile.json",
                invalid_coverage_profile_document,
            )

            invalid_snapshot_document = snapshot_document()
            invalid_snapshot_document["captured_at"] = "not-a-timestamp"
            invalid_snapshot = write_json(directory, "invalid-snapshot.json", invalid_snapshot_document)

            configuration_cases = [
                (
                    "missing-profile",
                    [str(directory / "missing-profile.json"), str(base_session)],
                ),
                (
                    "invalid-profile",
                    [str(invalid_profile), str(base_session)],
                ),
                (
                    "invalid-coverage-profile",
                    [str(invalid_coverage_profile), str(base_session)],
                ),
                (
                    "missing-transcript",
                    [str(success_only_profile), str(directory / "missing-session.json")],
                ),
                (
                    "invalid-required-snapshot",
                    [
                        str(strict_profile),
                        str(base_session),
                        "--snapshot",
                        str(invalid_snapshot),
                    ],
                ),
            ]
            for name, arguments in configuration_cases:
                run_case(validator, name, arguments, 3)

        print(
            "task verification output contract passed for 12 verification paths and "
            f"{len(configuration_cases)} configuration paths"
        )
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"task verification output contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
