#!/usr/bin/env python3
"""Validate conformance CLI JSON output against its published Draft 2020-12 schema."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "glomancy_conformance.py"
OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "cli-output.schema.json"


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


def main() -> int:
    try:
        schema = load_json(OUTPUT_SCHEMA)
        if not isinstance(schema, dict):
            raise ContractError("CLI output schema must be a JSON object")

        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

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
