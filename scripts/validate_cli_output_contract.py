#!/usr/bin/env python3
"""Validate conformance CLI JSON output against its published Draft 2020-12 schema."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "glomancy_conformance.py"
OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "cli-output.schema.json"
ACCEPTED_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "approval-gated-success-with-evidence.json"
)
PROJECT_URI = "glomancy://project/conformance-demo"


class ContractError(RuntimeError):
    """Raised when the CLI output contract is not satisfied."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_schema_errors(validator: Draft202012Validator, payload: Any) -> str:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    lines: list[str] = []
    for error in errors[:10]:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        lines.append(f"{location}: {error.message}")
    if len(errors) > 10:
        lines.append(f"... {len(errors) - 10} more error(s)")
    return "\n".join(lines)


def validate_payload(
    validator: Draft202012Validator,
    name: str,
    payload: Any,
) -> None:
    errors = list(validator.iter_errors(payload))
    if errors:
        detail = format_schema_errors(validator, payload)
        raise ContractError(f"{name}: output does not match schema:\n{detail}")


def run_cli_case(
    validator: Draft202012Validator,
    name: str,
    arguments: list[str],
    expected_exit: int,
) -> None:
    completed = subprocess.run(
        [sys.executable, str(CLI), *arguments],
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
        raise ContractError(
            f"{name}: JSON exit_code {payload.get('exit_code')!r} "
            f"does not match process exit {completed.returncode}"
        )

    validate_payload(validator, name, payload)


def write_semantically_invalid_session(directory: Path) -> Path:
    document = load_json(ACCEPTED_SESSION)
    if not isinstance(document, dict):
        raise ContractError("accepted session fixture must be an object")
    messages = document.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        raise ContractError("accepted session fixture must contain handshake messages")
    response = messages[1]
    if not isinstance(response, dict) or not isinstance(response.get("payload"), dict):
        raise ContractError("accepted session fixture handshake response is malformed")
    response["payload"]["selected_version"] = "9.9.9"
    path = directory / "unadvertised-version-session.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def write_project_bound_session(directory: Path) -> Path:
    document = load_json(ACCEPTED_SESSION)
    if not isinstance(document, dict):
        raise ContractError("accepted session fixture must be an object")
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("accepted session fixture messages must be an array")

    task_submit: dict[str, Any] | None = None
    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "task.submit":
            task_submit = message
            break
    if task_submit is None or not isinstance(task_submit.get("payload"), dict):
        raise ContractError("accepted session fixture must contain task.submit")

    task_submit["payload"]["context_refs"] = [
        {
            "source_type": "project",
            "uri": PROJECT_URI,
            "revision": "fixture-1",
        }
    ]
    path = directory / "project-bound-session.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    try:
        schema = load_json(OUTPUT_SCHEMA)
        if not isinstance(schema, dict):
            raise ContractError("CLI output schema must be a JSON object")

        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            invalid_session = write_semantically_invalid_session(temporary_path)
            project_session = write_project_bound_session(temporary_path)
            real_cases = [
                (
                    "list-schemas-success",
                    ["list-schemas", "--json"],
                    0,
                ),
                (
                    "validate-success",
                    ["validate", "examples/v1/valid/task.submit.json", "--json"],
                    0,
                ),
                (
                    "fixtures-success",
                    ["fixtures", "--json"],
                    0,
                ),
                (
                    "session-success",
                    [
                        "session",
                        str(project_session),
                        "--expect-sender",
                        "desktop=desktop-session",
                        "--expect-sender",
                        "bridge=bridge-session",
                        "--expect-project",
                        PROJECT_URI,
                        "--expect-evidence-type",
                        "read-back",
                        "--json",
                    ],
                    0,
                ),
                (
                    "session-semantic-failure",
                    ["session", str(invalid_session), "--json"],
                    2,
                ),
                (
                    "session-sender-expectation-failure",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-sender",
                        "bridge=unexpected-bridge",
                        "--json",
                    ],
                    2,
                ),
                (
                    "session-project-expectation-failure",
                    [
                        "session",
                        str(project_session),
                        "--expect-project",
                        "glomancy://project/other",
                        "--json",
                    ],
                    2,
                ),
                (
                    "session-project-expectation-missing",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-project",
                        PROJECT_URI,
                        "--json",
                    ],
                    2,
                ),
                (
                    "session-evidence-expectation-missing",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-evidence-type",
                        "test",
                        "--json",
                    ],
                    2,
                ),
                (
                    "session-sender-configuration-error",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-sender",
                        "missing-separator",
                        "--json",
                    ],
                    3,
                ),
                (
                    "session-project-configuration-error",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-project",
                        "not a valid uri",
                        "--json",
                    ],
                    3,
                ),
                (
                    "session-evidence-duplicate-configuration-error",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-evidence-type",
                        "read-back",
                        "--expect-evidence-type",
                        "read-back",
                        "--json",
                    ],
                    3,
                ),
                (
                    "session-evidence-unsupported-configuration-error",
                    [
                        "session",
                        str(ACCEPTED_SESSION),
                        "--expect-evidence-type",
                        "not-a-public-evidence-type",
                        "--json",
                    ],
                    3,
                ),
                (
                    "validate-payload-failure",
                    [
                        "validate",
                        "examples/v1/invalid/bad-message-id-format.json",
                        "--json",
                    ],
                    2,
                ),
                (
                    "validate-configuration-error",
                    [
                        "validate",
                        "examples/v1/valid/task.submit.json",
                        "--kind",
                        "heartbeat",
                        "--json",
                    ],
                    3,
                ),
            ]

            for name, arguments, expected_exit in real_cases:
                run_cli_case(validator, name, arguments, expected_exit)

        # A fixture-conformance failure requires a deliberately broken fixture corpus,
        # so validate that published failure shape without mutating repository fixtures.
        synthetic_fixture_failure = {
            "output_version": "1.0.0",
            "command": "fixtures",
            "ok": False,
            "exit_code": 2,
            "passed": False,
            "error": {
                "type": "fixture-conformance",
                "message": "representative conformance failure",
            },
        }
        validate_payload(
            validator,
            "fixture-conformance-failure-shape",
            synthetic_fixture_failure,
        )

        print(
            "conformance CLI JSON output contract passed for "
            f"{len(real_cases)} real CLI cases and 1 representative failure shape"
        )
        return 0
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        ContractError,
    ) as exc:
        print(f"conformance CLI JSON output contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
