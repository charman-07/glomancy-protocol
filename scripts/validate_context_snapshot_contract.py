#!/usr/bin/env python3
"""Exercise context snapshot validation/comparison and validate JSON output shapes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "glomancy_context_snapshot.py"
OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "context-snapshot-output.schema.json"
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


def write_session(directory: Path, invalid: bool = False) -> Path:
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
            "uri": "glomancy://project/snapshot-demo",
            "revision": "project-r5",
        },
        {
            "source_type": "asset",
            "uri": "glomancy://asset/selected-object",
            "revision": "asset-r9",
        },
        {
            "source_type": "memory",
            "uri": "glomancy://memory/design-note",
        },
    ]

    if invalid:
        response = messages[1]
        if not isinstance(response, dict) or not isinstance(response.get("payload"), dict):
            raise ContractError("accepted session fixture handshake response is malformed")
        response["payload"]["selected_version"] = "9.9.9"

    path = directory / ("invalid-session.json" if invalid else "session.json")
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def snapshot_document() -> dict[str, Any]:
    return {
        "snapshot_format_version": "1.0.0",
        "snapshot_id": "77777777-7777-4777-8777-777777777777",
        "captured_at": "2026-09-15T10:00:05Z",
        "sources": [
            {
                "source_type": "project",
                "uri": "glomancy://project/snapshot-demo",
                "revision": "project-r5",
            },
            {
                "source_type": "asset",
                "uri": "glomancy://asset/selected-object",
                "revision": "asset-r9",
            },
            {
                "source_type": "memory",
                "uri": "glomancy://memory/design-note",
            },
            {
                "source_type": "artifact",
                "uri": "glomancy://artifact/extra-snapshot-source",
                "revision": "artifact-r1",
            },
        ],
    }


def write_snapshot(directory: Path, name: str, document: dict[str, Any]) -> Path:
    path = directory / name
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
        raise ContractError(f"{name}: top-level output must be an object")
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
            raise ContractError("context snapshot output schema must be an object")
        Draft202012Validator.check_schema(output_schema)
        validator = Draft202012Validator(output_schema)

        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            session_path = write_session(directory)
            invalid_session_path = write_session(directory, invalid=True)

            good_snapshot = write_snapshot(directory, "snapshot.json", snapshot_document())

            missing_ref_document = snapshot_document()
            missing_ref_document["sources"] = [
                source
                for source in missing_ref_document["sources"]
                if source.get("source_type") != "asset"
            ]
            missing_ref_snapshot = write_snapshot(
                directory,
                "snapshot-missing-ref.json",
                missing_ref_document,
            )

            revision_mismatch_document = snapshot_document()
            for source in revision_mismatch_document["sources"]:
                if source.get("source_type") == "asset":
                    source["revision"] = "asset-r10"
            revision_mismatch_snapshot = write_snapshot(
                directory,
                "snapshot-revision-mismatch.json",
                revision_mismatch_document,
            )

            duplicate_document = snapshot_document()
            duplicate_document["sources"].append(
                {
                    "source_type": "project",
                    "uri": "glomancy://project/snapshot-demo",
                    "revision": "project-r6",
                }
            )
            duplicate_snapshot = write_snapshot(
                directory,
                "snapshot-duplicate-identity.json",
                duplicate_document,
            )

            invalid_schema_document = snapshot_document()
            invalid_schema_document["captured_at"] = "not-a-timestamp"
            invalid_schema_snapshot = write_snapshot(
                directory,
                "snapshot-invalid-schema.json",
                invalid_schema_document,
            )

            validate_success = run_case(
                validator,
                "validate-success",
                ["validate", str(good_snapshot)],
                0,
            )
            if validate_success.get("source_count") != 4:
                raise ContractError("validate-success: expected source_count=4")
            if validate_success.get("revisioned_source_count") != 3:
                raise ContractError("validate-success: expected revisioned_source_count=3")

            compare_success = run_case(
                validator,
                "compare-success",
                ["compare", str(good_snapshot), str(session_path)],
                0,
            )
            if compare_success.get("task_context_ref_count") != 3:
                raise ContractError("compare-success: expected task_context_ref_count=3")
            if compare_success.get("matched_context_ref_count") != 3:
                raise ContractError("compare-success: expected matched_context_ref_count=3")
            if compare_success.get("extra_snapshot_source_count") != 1:
                raise ContractError("compare-success: expected extra_snapshot_source_count=1")

            run_case(
                validator,
                "context-ref-not-in-snapshot",
                ["compare", str(missing_ref_snapshot), str(session_path)],
                2,
                "context-ref-not-in-snapshot",
            )
            run_case(
                validator,
                "context-revision-mismatch",
                ["compare", str(revision_mismatch_snapshot), str(session_path)],
                2,
                "context-revision-mismatch",
            )
            invalid_session = run_case(
                validator,
                "session-conformance-failed",
                ["compare", str(good_snapshot), str(invalid_session_path)],
                2,
                "session-conformance-failed",
            )
            if invalid_session.get("session_reason") != "unadvertised-selected-version":
                raise ContractError("session failure did not preserve canonical session reason")

            run_case(
                validator,
                "invalid-snapshot-schema",
                ["validate", str(invalid_schema_snapshot)],
                2,
                "snapshot-schema-failed",
            )
            run_case(
                validator,
                "duplicate-snapshot-identity",
                ["validate", str(duplicate_snapshot)],
                2,
                "snapshot-duplicate-source-identity",
            )

            configuration_cases = [
                (
                    "missing-snapshot",
                    ["validate", str(directory / "missing-snapshot.json")],
                ),
                (
                    "missing-transcript",
                    [
                        "compare",
                        str(good_snapshot),
                        str(directory / "missing-transcript.json"),
                    ],
                ),
                (
                    "invalid-snapshot-for-compare",
                    ["compare", str(invalid_schema_snapshot), str(session_path)],
                ),
                (
                    "duplicate-snapshot-for-compare",
                    ["compare", str(duplicate_snapshot), str(session_path)],
                ),
            ]
            for name, arguments in configuration_cases:
                run_case(validator, name, arguments, 3)

        print(
            "context snapshot output contract passed for 7 validation/comparison paths and "
            f"{len(configuration_cases)} configuration paths"
        )
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"context snapshot output contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
