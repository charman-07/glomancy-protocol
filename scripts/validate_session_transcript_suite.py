#!/usr/bin/env python3
"""Run the versioned full-session transcript conformance suite."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import session_transcript_core as core

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPTS_DIR = ROOT / "transcripts" / "v1"
CASES = TRANSCRIPTS_DIR / "cases.json"


def transcript_messages(case: dict[str, Any]) -> list[Any]:
    name = case["name"]
    file_value = case.get("file")
    if not isinstance(file_value, str) or not file_value:
        raise core.TranscriptError(f"{name}: file must be a non-empty string")
    path = (TRANSCRIPTS_DIR / file_value).resolve()
    try:
        path.relative_to(TRANSCRIPTS_DIR.resolve())
    except ValueError as exc:
        raise core.TranscriptError(f"{name}: transcript file escapes transcripts/v1") from exc
    if not path.is_file():
        raise core.TranscriptError(f"{name}: transcript file does not exist: {file_value}")
    transcript = core.load_json(path)
    if not isinstance(transcript, dict) or transcript.get("schema_version") != 1:
        raise core.TranscriptError(f"{name}: unsupported transcript file schema_version")
    if transcript.get("name") != name:
        raise core.TranscriptError(f"{name}: transcript file name does not match manifest")
    messages = transcript.get("messages")
    if not isinstance(messages, list) or not messages:
        raise core.TranscriptError(f"{name}: messages must be a non-empty array")
    return messages


def validate_suite() -> tuple[int, int]:
    suite = core.load_json(CASES)
    if not isinstance(suite, dict) or suite.get("schema_version") != 1:
        raise core.TranscriptError("unsupported transcript suite schema_version")
    if suite.get("suite_version") != "1.0.0":
        raise core.TranscriptError("unsupported transcript suite_version")

    accepted_cases = suite.get("accepted")
    rejected_cases = suite.get("rejected")
    if not isinstance(accepted_cases, list) or not isinstance(rejected_cases, list):
        raise core.TranscriptError("transcript accepted/rejected cases must be arrays")

    registry = core.load_json(core.REGISTRY)
    if suite.get("wire_protocol_version") != registry.get("wire_protocol_version"):
        raise core.TranscriptError(
            "transcript wire_protocol_version does not match canonical registry"
        )

    store = core.build_store()
    validators = {
        kind: (schema_id, core.validator_for(path, store))
        for kind, (schema_id, path) in core.registry_map().items()
    }

    names: set[str] = set()
    accepted_by_name: dict[str, list[Any]] = {}

    for case in accepted_cases:
        if not isinstance(case, dict):
            raise core.TranscriptError("accepted transcript case must be an object")
        name = case.get("name")
        expected = case.get("expected")
        if not isinstance(name, str) or not name:
            raise core.TranscriptError("transcript case name must be a non-empty string")
        if name in names:
            raise core.TranscriptError(f"duplicate transcript case: {name}")
        if not isinstance(expected, dict):
            raise core.TranscriptError(f"{name}: expected must be an object")
        names.add(name)

        messages = transcript_messages(case)
        result = core.validate_transcript(messages, validators)
        core.assert_expected(name, result, expected, True)
        accepted_by_name[name] = copy.deepcopy(messages)
        print(json.dumps({"case": name, **result}, sort_keys=True))

    for case in rejected_cases:
        if not isinstance(case, dict):
            raise core.TranscriptError("rejected transcript case must be an object")
        name = case.get("name")
        expected = case.get("expected")
        if not isinstance(name, str) or not name:
            raise core.TranscriptError("transcript case name must be a non-empty string")
        if name in names:
            raise core.TranscriptError(f"duplicate transcript case: {name}")
        if not isinstance(expected, dict):
            raise core.TranscriptError(f"{name}: expected must be an object")
        names.add(name)

        messages = core.materialize_rejected_case(case, accepted_by_name)
        result = core.validate_transcript(messages, validators)
        core.assert_expected(name, result, expected, False)
        print(json.dumps({"case": name, **result}, sort_keys=True))

    return len(accepted_cases), len(rejected_cases)


def main() -> int:
    try:
        accepted_count, rejected_count = validate_suite()
    except (KeyError, TypeError, core.TranscriptError) as exc:
        print(f"session transcript conformance failed: {exc}", file=sys.stderr)
        return 1

    print(
        "session transcript conformance passed: "
        f"{accepted_count} accepted cases, {rejected_count} rejected cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
