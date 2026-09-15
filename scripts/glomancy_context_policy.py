#!/usr/bin/env python3
"""Validate caller-supplied context-source policy against a complete public session."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import glomancy_conformance as conformance_cli
import session_transcript_core as session_core

ROOT = Path(__file__).resolve().parents[1]
COMMON_SCHEMA = ROOT / "schemas" / "v1" / "common.schema.json"
EXIT_OK = 0
EXIT_POLICY_FAILED = 2
EXIT_CONFIGURATION_ERROR = 3
OUTPUT_VERSION = "1.0.0"


class ContextPolicyError(RuntimeError):
    """Raised when context-policy configuration cannot be evaluated."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContextPolicyError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContextPolicyError(f"invalid JSON in {path}: {exc}") from exc


def source_type_values() -> set[str]:
    schema = load_json(COMMON_SCHEMA)
    try:
        values = schema["$defs"]["source_ref"]["properties"]["source_type"]["enum"]
    except (KeyError, TypeError) as exc:
        raise ContextPolicyError(
            "common.schema.json does not expose the expected source_ref source_type enum"
        ) from exc

    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(value, str) or not value for value in values)
        or len(set(values)) != len(values)
    ):
        raise ContextPolicyError("source_ref source_type enum is invalid")
    return set(values)


def parse_source_list(flag: str, values: list[str], allowed: set[str]) -> list[str]:
    parsed: set[str] = set()
    for value in values:
        if not value:
            raise ContextPolicyError(f"{flag} must be non-empty")
        if value not in allowed:
            supported = ",".join(sorted(allowed))
            raise ContextPolicyError(f"unsupported {flag}: {value}; supported: {supported}")
        if value in parsed:
            raise ContextPolicyError(f"duplicate {flag}: {value}")
        parsed.add(value)
    return sorted(parsed)


def parse_policy(
    expect_values: list[str],
    forbid_values: list[str],
    revision_values: list[str],
) -> tuple[list[str], list[str], list[str]]:
    allowed = source_type_values()
    expected = parse_source_list("--expect-source", expect_values, allowed)
    forbidden = parse_source_list("--forbid-source", forbid_values, allowed)
    revision_required = parse_source_list("--require-revision-source", revision_values, allowed)

    conflicts = sorted(set(expected) & set(forbidden))
    if conflicts:
        raise ContextPolicyError(
            "context source cannot be both expected and forbidden: " + ",".join(conflicts)
        )

    revision_conflicts = sorted(set(revision_required) & set(forbidden))
    if revision_conflicts:
        raise ContextPolicyError(
            "context source cannot require revision metadata while forbidden: "
            + ",".join(revision_conflicts)
        )

    return expected, forbidden, revision_required


def task_submit_index(messages: list[Any]) -> int | None:
    for index, message in enumerate(messages):
        if isinstance(message, dict) and message.get("kind") == "task.submit":
            return index
    return None


def context_summary(
    messages: list[Any],
) -> tuple[dict[str, int], dict[str, int], int, int]:
    counts: dict[str, int] = {}
    revision_counts: dict[str, int] = {}
    total = 0
    revisioned = 0

    for message in messages:
        if not isinstance(message, dict) or message.get("kind") != "task.submit":
            continue
        payload = message.get("payload")
        if not isinstance(payload, dict):
            continue
        refs = payload.get("context_refs")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            source_type = ref.get("source_type")
            if not isinstance(source_type, str):
                continue
            total += 1
            counts[source_type] = counts.get(source_type, 0) + 1
            revision = ref.get("revision")
            if isinstance(revision, str) and revision:
                revisioned += 1
                revision_counts[source_type] = revision_counts.get(source_type, 0) + 1

    return (
        {key: counts[key] for key in sorted(counts)},
        {key: revision_counts[key] for key in sorted(revision_counts)},
        total,
        revisioned,
    )


def emit_json(ok: bool, exit_code: int, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "output_version": OUTPUT_VERSION,
        "command": "context-policy",
        "ok": ok,
        "exit_code": exit_code,
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def emit_configuration_error(json_output: bool, message: str) -> int:
    if json_output:
        emit_json(
            False,
            EXIT_CONFIGURATION_ERROR,
            error={"type": "configuration", "message": message},
        )
    else:
        print(f"configuration error: {message}", file=sys.stderr)
    return EXIT_CONFIGURATION_ERROR


def evaluate_policy(
    messages: list[Any],
    expected: list[str],
    forbidden: list[str],
    revision_required: list[str],
) -> tuple[
    str | None,
    int | None,
    str | None,
    dict[str, int],
    dict[str, int],
    int,
    int,
]:
    counts, revision_counts, total, revisioned = context_summary(messages)

    missing = [source for source in expected if counts.get(source, 0) == 0]
    if missing:
        observed_text = ",".join(f"{key}:{value}" for key, value in counts.items()) or "<none>"
        return (
            "context-source-expectation-missing",
            task_submit_index(messages),
            f"missing_sources={','.join(missing)} observed_sources={observed_text}",
            counts,
            revision_counts,
            total,
            revisioned,
        )

    present_forbidden = [source for source in forbidden if counts.get(source, 0) > 0]
    if present_forbidden:
        observed_text = ",".join(f"{key}:{value}" for key, value in counts.items()) or "<none>"
        return (
            "context-source-forbidden",
            task_submit_index(messages),
            f"forbidden_sources={','.join(present_forbidden)} observed_sources={observed_text}",
            counts,
            revision_counts,
            total,
            revisioned,
        )

    incomplete_revision_sources: list[str] = []
    for source in revision_required:
        observed_count = counts.get(source, 0)
        revision_count = revision_counts.get(source, 0)
        if observed_count == 0 or revision_count != observed_count:
            incomplete_revision_sources.append(f"{source}:{revision_count}/{observed_count}")
    if incomplete_revision_sources:
        return (
            "context-source-revision-missing",
            task_submit_index(messages),
            "revision_coverage=" + ",".join(incomplete_revision_sources),
            counts,
            revision_counts,
            total,
            revisioned,
        )

    return None, None, None, counts, revision_counts, total, revisioned


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glomancy-context-policy",
        description=(
            "Validate a complete public Glomancy Protocol session, then enforce caller-supplied "
            "context-source expectations without exposing private context-selection semantics."
        ),
    )
    parser.add_argument("path", help="path to a complete transcript JSON document")
    parser.add_argument(
        "--expect-source",
        action="append",
        default=[],
        metavar="TYPE",
        help="require at least one task context reference with TYPE; repeat for multiple types",
    )
    parser.add_argument(
        "--forbid-source",
        action="append",
        default=[],
        metavar="TYPE",
        help="reject any task context reference with TYPE; repeat for multiple types",
    )
    parser.add_argument(
        "--require-revision-source",
        action="append",
        default=[],
        metavar="TYPE",
        help=(
            "require TYPE to be present and every reference of TYPE to carry non-empty revision "
            "metadata; repeat for multiple types"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit one machine-readable JSON object to stdout",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    transcript_path = Path(args.path).expanduser().resolve()
    if not transcript_path.is_file():
        return emit_configuration_error(
            args.json_output, f"transcript file does not exist: {transcript_path}"
        )

    try:
        expected, forbidden, revision_required = parse_policy(
            args.expect_source,
            args.forbid_source,
            args.require_revision_source,
        )
        messages = conformance_cli.load_session_document(transcript_path)
        session_result = session_core.validate_transcript(
            messages,
            conformance_cli.session_validators(),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        ContextPolicyError,
        session_core.TranscriptError,
        conformance_cli.ConformanceError,
    ) as exc:
        return emit_configuration_error(args.json_output, str(exc))

    if not session_result["accepted"]:
        if args.json_output:
            emit_json(
                False,
                EXIT_POLICY_FAILED,
                path=str(transcript_path),
                session_accepted=False,
                policy_passed=False,
                reason="session-conformance-failed",
                session_reason=session_result["reason"],
                message_index=session_result["message_index"],
                detail=session_result["detail"],
                expected_sources=expected,
                forbidden_sources=forbidden,
                revision_required_sources=revision_required,
                observed_source_counts={},
                observed_revisioned_source_counts={},
                context_ref_count=0,
                revisioned_context_ref_count=0,
            )
        else:
            suffix = ""
            if session_result["message_index"] is not None:
                suffix += f" message_index={session_result['message_index']}"
            if session_result["detail"]:
                suffix += f" detail={session_result['detail']}"
            print(
                f"context policy not evaluated: session invalid: "
                f"reason={session_result['reason']}{suffix}",
                file=sys.stderr,
            )
        return EXIT_POLICY_FAILED

    (
        reason,
        message_index,
        detail,
        counts,
        revision_counts,
        total,
        revisioned,
    ) = evaluate_policy(messages, expected, forbidden, revision_required)
    policy_passed = reason is None
    exit_code = EXIT_OK if policy_passed else EXIT_POLICY_FAILED

    if args.json_output:
        emit_json(
            policy_passed,
            exit_code,
            path=str(transcript_path),
            session_accepted=True,
            policy_passed=policy_passed,
            reason=reason,
            session_reason=None,
            message_index=message_index,
            detail=detail,
            expected_sources=expected,
            forbidden_sources=forbidden,
            revision_required_sources=revision_required,
            observed_source_counts=counts,
            observed_revisioned_source_counts=revision_counts,
            context_ref_count=total,
            revisioned_context_ref_count=revisioned,
        )
    elif policy_passed:
        observed_text = ",".join(f"{key}:{value}" for key, value in counts.items()) or "<none>"
        print(
            f"context policy passed: {transcript_path}: refs={total} "
            f"revisioned={revisioned} observed={observed_text}"
        )
    else:
        suffix = f" message_index={message_index}" if message_index is not None else ""
        if detail:
            suffix += f" detail={detail}"
        print(
            f"context policy failed: {transcript_path}: reason={reason}{suffix}",
            file=sys.stderr,
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
