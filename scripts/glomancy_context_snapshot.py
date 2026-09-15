#!/usr/bin/env python3
"""Validate portable context snapshot descriptors and compare them with public sessions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import glomancy_conformance as conformance_cli
import session_transcript_core as session_core
from validate_fixtures import ConformanceError, ROOT, build_store, load_json, validator_for

SNAPSHOT_SCHEMA = ROOT / "context" / "v1" / "snapshot.schema.json"
EXIT_OK = 0
EXIT_VALIDATION_FAILED = 2
EXIT_CONFIGURATION_ERROR = 3
OUTPUT_VERSION = "1.0.0"


class SnapshotError(RuntimeError):
    """Raised when a snapshot operation cannot be evaluated."""


def emit_json(command: str, ok: bool, exit_code: int, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "output_version": OUTPUT_VERSION,
        "command": command,
        "ok": ok,
        "exit_code": exit_code,
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def emit_configuration_error(command: str, json_output: bool, message: str) -> int:
    if json_output:
        emit_json(
            command,
            False,
            EXIT_CONFIGURATION_ERROR,
            error={"type": "configuration", "message": message},
        )
    else:
        print(f"configuration error: {message}", file=sys.stderr)
    return EXIT_CONFIGURATION_ERROR


def snapshot_validator() -> Any:
    return validator_for(SNAPSHOT_SCHEMA, build_store())


def load_snapshot(path: Path) -> Any:
    if not path.is_file():
        raise SnapshotError(f"snapshot file does not exist: {path}")
    try:
        return load_json(path)
    except ConformanceError as exc:
        raise SnapshotError(str(exc)) from exc


def snapshot_schema_errors(document: Any) -> list[Any]:
    return sorted(snapshot_validator().iter_errors(document), key=lambda error: list(error.path))


def source_type_counts(refs: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        source_type = ref.get("source_type")
        if isinstance(source_type, str):
            counts[source_type] = counts.get(source_type, 0) + 1
    return {source_type: counts[source_type] for source_type in sorted(counts)}


def revisioned_source_count(refs: list[Any]) -> int:
    total = 0
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        revision = ref.get("revision")
        if isinstance(revision, str) and revision:
            total += 1
    return total


def duplicate_source_identity_index(refs: list[Any]) -> int | None:
    seen: set[tuple[str, str]] = set()
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            continue
        source_type = ref.get("source_type")
        uri = ref.get("uri")
        if not isinstance(source_type, str) or not isinstance(uri, str):
            continue
        key = (source_type, uri)
        if key in seen:
            return index
        seen.add(key)
    return None


def snapshot_summary(document: Any) -> tuple[str | None, list[Any], dict[str, int], int]:
    if not isinstance(document, dict):
        return None, [], {}, 0
    snapshot_id = document.get("snapshot_id")
    sources = document.get("sources")
    if not isinstance(sources, list):
        sources = []
    return (
        snapshot_id if isinstance(snapshot_id, str) else None,
        sources,
        source_type_counts(sources),
        revisioned_source_count(sources),
    )


def first_schema_error_record(errors: list[Any]) -> tuple[str | None, list[str]]:
    if not errors:
        return None, []
    error = errors[0]
    keyword = str(error.validator) if error.validator is not None else None
    path = [str(part) for part in error.absolute_path]
    return keyword, path


def task_context_refs(messages: list[Any]) -> tuple[list[Any], int | None]:
    for message_index, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("kind") != "task.submit":
            continue
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return [], message_index
        refs = payload.get("context_refs")
        if isinstance(refs, list):
            return refs, message_index
        return [], message_index
    return [], None


def snapshot_source_map(refs: list[Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        source_type = ref.get("source_type")
        uri = ref.get("uri")
        if isinstance(source_type, str) and isinstance(uri, str):
            result[(source_type, uri)] = ref
    return result


def compare_context_refs(
    snapshot_sources: list[Any],
    task_refs: list[Any],
) -> tuple[bool, str | None, str | None, int]:
    snapshot_map = snapshot_source_map(snapshot_sources)
    matched = 0

    for index, ref in enumerate(task_refs):
        if not isinstance(ref, dict):
            continue
        source_type = ref.get("source_type")
        uri = ref.get("uri")
        if not isinstance(source_type, str) or not isinstance(uri, str):
            continue

        snapshot_ref = snapshot_map.get((source_type, uri))
        if snapshot_ref is None:
            return (
                False,
                "context-ref-not-in-snapshot",
                f"task_context_index={index} source_type={source_type}",
                matched,
            )

        task_revision = ref.get("revision")
        if isinstance(task_revision, str):
            snapshot_revision = snapshot_ref.get("revision")
            if snapshot_revision != task_revision:
                return (
                    False,
                    "context-revision-mismatch",
                    f"task_context_index={index} source_type={source_type}",
                    matched,
                )

        matched += 1

    return True, None, None, matched


def validate_snapshot_document(document: Any) -> tuple[list[Any], int | None]:
    errors = snapshot_schema_errors(document)
    if errors:
        return errors, None
    _, sources, _, _ = snapshot_summary(document)
    duplicate_index = duplicate_source_identity_index(sources)
    return [], duplicate_index


def command_validate(args: argparse.Namespace) -> int:
    path = Path(args.snapshot).expanduser().resolve()
    try:
        document = load_snapshot(path)
        errors, duplicate_index = validate_snapshot_document(document)
    except (SnapshotError, ConformanceError, OSError, TypeError, ValueError) as exc:
        return emit_configuration_error("validate", args.json_output, str(exc))

    snapshot_id, sources, counts, revisioned = snapshot_summary(document)

    if errors:
        keyword, error_path = first_schema_error_record(errors)
        if args.json_output:
            emit_json(
                "validate",
                False,
                EXIT_VALIDATION_FAILED,
                path=str(path),
                valid=False,
                reason="snapshot-schema-failed",
                snapshot_id=snapshot_id,
                source_count=len(sources),
                source_type_counts=counts,
                revisioned_source_count=revisioned,
                error_count=len(errors),
                first_error_keyword=keyword,
                first_error_path=error_path,
            )
        else:
            print(
                f"snapshot invalid: {path}: reason=snapshot-schema-failed error_count={len(errors)}",
                file=sys.stderr,
            )
        return EXIT_VALIDATION_FAILED

    if duplicate_index is not None:
        if args.json_output:
            emit_json(
                "validate",
                False,
                EXIT_VALIDATION_FAILED,
                path=str(path),
                valid=False,
                reason="snapshot-duplicate-source-identity",
                snapshot_id=snapshot_id,
                source_count=len(sources),
                source_type_counts=counts,
                revisioned_source_count=revisioned,
                error_count=1,
                first_error_keyword="unique-source-identity",
                first_error_path=["sources", str(duplicate_index)],
            )
        else:
            print(
                f"snapshot invalid: {path}: reason=snapshot-duplicate-source-identity",
                file=sys.stderr,
            )
        return EXIT_VALIDATION_FAILED

    if args.json_output:
        emit_json(
            "validate",
            True,
            EXIT_OK,
            path=str(path),
            valid=True,
            reason=None,
            snapshot_id=snapshot_id,
            source_count=len(sources),
            source_type_counts=counts,
            revisioned_source_count=revisioned,
            error_count=0,
            first_error_keyword=None,
            first_error_path=[],
        )
    else:
        print(
            f"snapshot valid: {path}: sources={len(sources)} revisioned={revisioned}"
        )
    return EXIT_OK


def command_compare(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot).expanduser().resolve()
    transcript_path = Path(args.transcript).expanduser().resolve()

    try:
        document = load_snapshot(snapshot_path)
        errors, duplicate_index = validate_snapshot_document(document)
        if errors:
            raise SnapshotError(f"snapshot schema validation failed with {len(errors)} error(s)")
        if duplicate_index is not None:
            raise SnapshotError(
                f"snapshot contains duplicate source identity at sources/{duplicate_index}"
            )
        if not transcript_path.is_file():
            raise SnapshotError(f"transcript file does not exist: {transcript_path}")
        messages = conformance_cli.load_session_document(transcript_path)
        session_result = session_core.validate_transcript(
            messages,
            conformance_cli.session_validators(),
        )
    except (
        SnapshotError,
        ConformanceError,
        OSError,
        TypeError,
        ValueError,
        session_core.TranscriptError,
    ) as exc:
        return emit_configuration_error("compare", args.json_output, str(exc))

    snapshot_id, snapshot_sources, snapshot_counts, snapshot_revisioned = snapshot_summary(document)
    refs, task_message_index = task_context_refs(messages)
    task_counts = source_type_counts(refs)

    if not session_result["accepted"]:
        if args.json_output:
            emit_json(
                "compare",
                False,
                EXIT_VALIDATION_FAILED,
                snapshot_path=str(snapshot_path),
                transcript_path=str(transcript_path),
                snapshot_id=snapshot_id,
                session_accepted=False,
                matched=False,
                reason="session-conformance-failed",
                session_reason=session_result["reason"],
                message_index=session_result["message_index"],
                detail=session_result["detail"],
                snapshot_source_count=len(snapshot_sources),
                task_context_ref_count=len(refs),
                matched_context_ref_count=0,
                extra_snapshot_source_count=len(snapshot_sources),
                snapshot_revisioned_source_count=snapshot_revisioned,
                snapshot_source_type_counts=snapshot_counts,
                task_source_type_counts=task_counts,
            )
        else:
            print(
                f"snapshot compare failed: reason=session-conformance-failed "
                f"session_reason={session_result['reason']}",
                file=sys.stderr,
            )
        return EXIT_VALIDATION_FAILED

    matched, reason, detail, matched_count = compare_context_refs(snapshot_sources, refs)
    extra_count = max(0, len(snapshot_sources) - matched_count)
    exit_code = EXIT_OK if matched else EXIT_VALIDATION_FAILED

    if args.json_output:
        emit_json(
            "compare",
            matched,
            exit_code,
            snapshot_path=str(snapshot_path),
            transcript_path=str(transcript_path),
            snapshot_id=snapshot_id,
            session_accepted=True,
            matched=matched,
            reason=reason,
            session_reason=None,
            message_index=task_message_index if not matched else None,
            detail=detail,
            snapshot_source_count=len(snapshot_sources),
            task_context_ref_count=len(refs),
            matched_context_ref_count=matched_count,
            extra_snapshot_source_count=extra_count,
            snapshot_revisioned_source_count=snapshot_revisioned,
            snapshot_source_type_counts=snapshot_counts,
            task_source_type_counts=task_counts,
        )
    elif matched:
        print(
            f"snapshot compare passed: snapshot_sources={len(snapshot_sources)} "
            f"task_context_refs={len(refs)} matched={matched_count} extras={extra_count}"
        )
    else:
        print(f"snapshot compare failed: reason={reason} detail={detail}", file=sys.stderr)

    return exit_code


def add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit one machine-readable JSON object to stdout",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glomancy-context-snapshot",
        description="Validate portable context snapshot descriptors and compare them with sessions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate one context snapshot descriptor")
    validate_parser.add_argument("snapshot", help="path to a context snapshot descriptor JSON file")
    add_json_option(validate_parser)
    validate_parser.set_defaults(handler=command_validate)

    compare_parser = subparsers.add_parser(
        "compare",
        help="compare a valid context snapshot descriptor with task context in a full session",
    )
    compare_parser.add_argument("snapshot", help="path to a context snapshot descriptor JSON file")
    compare_parser.add_argument("transcript", help="path to a complete public session transcript")
    add_json_option(compare_parser)
    compare_parser.set_defaults(handler=command_compare)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
