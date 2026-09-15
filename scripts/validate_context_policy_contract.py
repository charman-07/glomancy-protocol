#!/usr/bin/env python3
"""Exercise context-policy conformance and validate every JSON result shape."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "glomancy_context_policy.py"
OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "context-policy-output.schema.json"
ACCEPTED_SESSION = (
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


def write_context_session(directory: Path, include_web: bool = False) -> Path:
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

    context_refs: list[dict[str, str]] = [
        {
            "source_type": "project",
            "uri": "glomancy://project/conformance-demo",
            "revision": "project-r1",
        },
        {
            "source_type": "asset",
            "uri": "glomancy://asset/selected-actor",
            "revision": "asset-r7",
        },
        {
            "source_type": "memory",
            "uri": "glomancy://memory/project-note",
        },
    ]
    if include_web:
        context_refs.append(
            {
                "source_type": "web",
                "uri": "https://example.com/reference",
                "revision": "2026-09-15",
            }
        )
    task_submit["payload"]["context_refs"] = context_refs

    name = "context-session-with-web.json" if include_web else "context-session.json"
    path = directory / name
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def write_invalid_session(directory: Path) -> Path:
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
    path = directory / "invalid-session.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


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

    try:
        payload = json.loads(completed.stdout.strip())
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
        schema = load_json(OUTPUT_SCHEMA)
        if not isinstance(schema, dict):
            raise ContractError("context-policy output schema must be a JSON object")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            context_session = write_context_session(directory)
            web_session = write_context_session(directory, include_web=True)
            invalid_session = write_invalid_session(directory)

            success = run_case(
                validator,
                "context-policy-success",
                [
                    str(context_session),
                    "--expect-source",
                    "project",
                    "--expect-source",
                    "asset",
                    "--forbid-source",
                    "web",
                    "--require-revision-source",
                    "project",
                    "--require-revision-source",
                    "asset",
                ],
                0,
            )
            if success.get("context_ref_count") != 3:
                raise ContractError("context-policy-success: expected context_ref_count=3")
            if success.get("revisioned_context_ref_count") != 2:
                raise ContractError(
                    "context-policy-success: expected revisioned_context_ref_count=2"
                )
            if success.get("observed_source_counts") != {
                "asset": 1,
                "memory": 1,
                "project": 1,
            }:
                raise ContractError("context-policy-success: unexpected observed source counts")
            if success.get("observed_revisioned_source_counts") != {
                "asset": 1,
                "project": 1,
            }:
                raise ContractError(
                    "context-policy-success: unexpected observed revisioned source counts"
                )
            if success.get("revision_required_sources") != ["asset", "project"]:
                raise ContractError(
                    "context-policy-success: revision_required_sources must be deterministic"
                )

            run_case(
                validator,
                "missing-expected-source",
                [str(context_session), "--expect-source", "artifact"],
                2,
                "context-source-expectation-missing",
            )
            run_case(
                validator,
                "forbidden-observed-source",
                [str(web_session), "--forbid-source", "web"],
                2,
                "context-source-forbidden",
            )
            run_case(
                validator,
                "missing-required-revision",
                [str(context_session), "--require-revision-source", "memory"],
                2,
                "context-source-revision-missing",
            )
            run_case(
                validator,
                "missing-required-revision-source",
                [str(context_session), "--require-revision-source", "artifact"],
                2,
                "context-source-revision-missing",
            )
            invalid = run_case(
                validator,
                "invalid-session",
                [str(invalid_session), "--expect-source", "project"],
                2,
                "session-conformance-failed",
            )
            if invalid.get("session_reason") != "unadvertised-selected-version":
                raise ContractError("invalid-session: original session reason was not preserved")

            configuration_cases = [
                (
                    "duplicate-expected-source",
                    [
                        str(context_session),
                        "--expect-source",
                        "project",
                        "--expect-source",
                        "project",
                    ],
                ),
                (
                    "duplicate-forbidden-source",
                    [
                        str(context_session),
                        "--forbid-source",
                        "web",
                        "--forbid-source",
                        "web",
                    ],
                ),
                (
                    "duplicate-revision-source",
                    [
                        str(context_session),
                        "--require-revision-source",
                        "project",
                        "--require-revision-source",
                        "project",
                    ],
                ),
                (
                    "unsupported-source",
                    [str(context_session), "--expect-source", "runtime"],
                ),
                (
                    "unsupported-revision-source",
                    [str(context_session), "--require-revision-source", "runtime"],
                ),
                (
                    "expect-forbid-conflict",
                    [
                        str(context_session),
                        "--expect-source",
                        "memory",
                        "--forbid-source",
                        "memory",
                    ],
                ),
                (
                    "revision-forbid-conflict",
                    [
                        str(context_session),
                        "--require-revision-source",
                        "project",
                        "--forbid-source",
                        "project",
                    ],
                ),
                (
                    "missing-transcript",
                    [str(directory / "does-not-exist.json"), "--expect-source", "project"],
                ),
            ]
            for name, arguments in configuration_cases:
                run_case(validator, name, arguments, 3)

        print(
            "context policy output contract passed for 6 conformance paths and "
            f"{len(configuration_cases)} configuration paths"
        )
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"context policy output contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
