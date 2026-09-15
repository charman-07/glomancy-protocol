#!/usr/bin/env python3
"""Public conformance CLI for Glomancy Protocol payloads, fixtures, and sessions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import session_transcript_core as session_core
from validate_fixtures import (
    ConformanceError,
    ROOT,
    build_store,
    load_json,
    validate_manifest,
    validator_for,
)

REGISTRY_MANIFEST = ROOT / "registry" / "v1" / "manifest.json"
EXIT_OK = 0
EXIT_VALIDATION_FAILED = 2
EXIT_CONFIGURATION_ERROR = 3
JSON_OUTPUT_VERSION = "1.0.0"


def load_registry() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    manifest = load_json(REGISTRY_MANIFEST)
    if not isinstance(manifest, dict):
        raise ConformanceError("registry manifest must be an object")

    by_schema_id: dict[str, dict[str, Any]] = {}
    by_kind: dict[str, dict[str, Any]] = {}
    entries = [*manifest.get("support_schemas", []), *manifest.get("message_schemas", [])]

    for entry in entries:
        if not isinstance(entry, dict):
            raise ConformanceError("registry entry must be an object")
        schema_id = entry.get("schema_id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ConformanceError("registry entry is missing schema_id")
        if schema_id in by_schema_id:
            raise ConformanceError(f"duplicate schema_id in registry: {schema_id}")
        by_schema_id[schema_id] = entry

        kind = entry.get("message_kind")
        if kind is not None:
            if not isinstance(kind, str) or not kind:
                raise ConformanceError(f"invalid message_kind for {schema_id}")
            if kind in by_kind:
                raise ConformanceError(f"duplicate message_kind in registry: {kind}")
            by_kind[kind] = entry

    return by_schema_id, by_kind


def resolve_schema_file(entry: dict[str, Any]) -> Path:
    value = entry.get("file")
    if not isinstance(value, str) or not value:
        raise ConformanceError("registry entry is missing file")
    path = (REGISTRY_MANIFEST.parent / value).resolve()
    schema_root = (ROOT / "schemas" / "v1").resolve()
    try:
        path.relative_to(schema_root)
    except ValueError as exc:
        raise ConformanceError(f"registry schema path escapes schemas/v1: {value}") from exc
    if not path.is_file():
        raise ConformanceError(f"registry schema file does not exist: {value}")
    return path


def choose_entry(
    document: Any,
    explicit_schema_id: str | None,
    explicit_kind: str | None,
) -> dict[str, Any]:
    by_schema_id, by_kind = load_registry()

    schema_id = explicit_schema_id
    kind = explicit_kind
    if isinstance(document, dict):
        if schema_id is None and isinstance(document.get("schema_id"), str):
            schema_id = document["schema_id"]
        if kind is None and isinstance(document.get("kind"), str):
            kind = document["kind"]

    schema_entry = by_schema_id.get(schema_id) if schema_id else None
    kind_entry = by_kind.get(kind) if kind else None

    if schema_id and schema_entry is None:
        raise ConformanceError(f"unknown schema_id: {schema_id}")
    if kind and kind_entry is None:
        raise ConformanceError(f"unknown message kind: {kind}")
    if schema_entry is None and kind_entry is None:
        raise ConformanceError(
            "could not select a schema; provide --schema-id/--kind or include schema_id/kind in the document"
        )
    if schema_entry is not None and kind_entry is not None:
        if schema_entry.get("schema_id") != kind_entry.get("schema_id"):
            raise ConformanceError(
                "schema_id and kind resolve to different registry entries; refusing to guess"
            )

    return schema_entry or kind_entry  # type: ignore[return-value]


def error_record(error: Any) -> dict[str, Any]:
    location_parts = [str(part) for part in error.absolute_path]
    return {
        "keyword": str(error.validator) if error.validator is not None else None,
        "path": location_parts,
        "path_text": "/".join(location_parts) or "<root>",
        "message": str(error.message),
    }


def render_error(error: Any) -> str:
    record = error_record(error)
    return f"keyword={record['keyword']!r} path={record['path_text']}: {record['message']}"


def emit_json(command: str, ok: bool, exit_code: int, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "output_version": JSON_OUTPUT_VERSION,
        "command": command,
        "ok": ok,
        "exit_code": exit_code,
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def emit_configuration_error(args: argparse.Namespace, message: str) -> int:
    if args.json_output:
        emit_json(
            str(args.command),
            False,
            EXIT_CONFIGURATION_ERROR,
            error={"type": "configuration", "message": message},
        )
    else:
        print(f"configuration error: {message}", file=sys.stderr)
    return EXIT_CONFIGURATION_ERROR


def command_validate(args: argparse.Namespace) -> int:
    document_path = Path(args.path).expanduser().resolve()
    if not document_path.is_file():
        return emit_configuration_error(args, f"payload file does not exist: {document_path}")

    try:
        document = load_json(document_path)
        entry = choose_entry(document, args.schema_id, args.kind)
        schema_path = resolve_schema_file(entry)
        validator = validator_for(schema_path, build_store())
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    except (KeyError, TypeError, ConformanceError, json.JSONDecodeError, OSError) as exc:
        return emit_configuration_error(args, str(exc))

    schema_id = str(entry.get("schema_id"))
    message_kind = entry.get("message_kind")

    if errors:
        limited_errors = [error_record(error) for error in errors[: args.max_errors]]
        if args.json_output:
            emit_json(
                "validate",
                False,
                EXIT_VALIDATION_FAILED,
                path=str(document_path),
                schema_id=schema_id,
                kind=message_kind,
                valid=False,
                error_count=len(errors),
                errors=limited_errors,
                truncated_error_count=max(0, len(errors) - len(limited_errors)),
            )
        else:
            print(f"invalid: {document_path}: schema={schema_id}", file=sys.stderr)
            for error in errors[: args.max_errors]:
                print(f"  - {render_error(error)}", file=sys.stderr)
            if len(errors) > args.max_errors:
                print(f"  - ... {len(errors) - args.max_errors} more error(s)", file=sys.stderr)
        return EXIT_VALIDATION_FAILED

    if args.json_output:
        emit_json(
            "validate",
            True,
            EXIT_OK,
            path=str(document_path),
            schema_id=schema_id,
            kind=message_kind,
            valid=True,
            error_count=0,
            errors=[],
            truncated_error_count=0,
        )
    else:
        print(
            f"valid: {document_path}: schema={schema_id}"
            + (f" kind={message_kind}" if message_kind else "")
        )
    return EXIT_OK


def command_fixtures(args: argparse.Namespace) -> int:
    try:
        valid_count, invalid_count = validate_manifest()
    except (KeyError, TypeError, ConformanceError, json.JSONDecodeError, OSError) as exc:
        if args.json_output:
            emit_json(
                "fixtures",
                False,
                EXIT_VALIDATION_FAILED,
                passed=False,
                error={"type": "fixture-conformance", "message": str(exc)},
            )
        else:
            print(f"fixture conformance failed: {exc}", file=sys.stderr)
        return EXIT_VALIDATION_FAILED

    if args.json_output:
        emit_json(
            "fixtures",
            True,
            EXIT_OK,
            passed=True,
            valid_fixtures_accepted=valid_count,
            invalid_fixtures_rejected=invalid_count,
            total_fixtures=valid_count + invalid_count,
        )
    else:
        print(
            "fixture conformance passed: "
            f"{valid_count} valid fixtures accepted, {invalid_count} invalid fixtures rejected"
        )
    return EXIT_OK


def parse_sender_expectations(values: list[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for raw in values:
        component, separator, instance_id = raw.partition("=")
        if not separator or not component or not instance_id:
            raise ConformanceError(
                "--expect-sender must use component=instance_id with both values non-empty"
            )
        if component in expected:
            raise ConformanceError(f"duplicate --expect-sender component: {component}")
        expected[component] = instance_id
    return expected


def load_session_document(path: Path) -> list[Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConformanceError(f"cannot read transcript file: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConformanceError(f"invalid transcript JSON: {path}: {exc}") from exc

    if not isinstance(document, dict):
        raise ConformanceError("transcript top level must be an object")
    if document.get("schema_version") != 1:
        raise ConformanceError("transcript schema_version must be 1")
    messages = document.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ConformanceError("transcript messages must be a non-empty array")
    return messages


def session_validators() -> dict[str, tuple[str, Any]]:
    store = session_core.build_store()
    return {
        kind: (schema_id, session_core.validator_for(path, store))
        for kind, (schema_id, path) in session_core.registry_map().items()
    }


def observed_senders(messages: list[Any]) -> dict[str, list[str]]:
    observed: dict[str, set[str]] = {}
    for message in messages:
        if not isinstance(message, dict):
            continue
        sender = message.get("sender")
        if not isinstance(sender, dict):
            continue
        component = sender.get("component")
        instance_id = sender.get("instance_id")
        if isinstance(component, str) and isinstance(instance_id, str):
            observed.setdefault(component, set()).add(instance_id)
    return {component: sorted(instance_ids) for component, instance_ids in sorted(observed.items())}


def apply_sender_expectations(
    messages: list[Any],
    expected: dict[str, str],
) -> dict[str, Any] | None:
    if not expected:
        return None

    seen: set[str] = set()
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        sender = message.get("sender")
        if not isinstance(sender, dict):
            continue
        component = sender.get("component")
        instance_id = sender.get("instance_id")
        if not isinstance(component, str) or component not in expected:
            continue
        seen.add(component)
        expected_instance = expected[component]
        if instance_id != expected_instance:
            return session_core.reject(
                "sender-expectation-mismatch",
                index,
                f"component={component} expected_instance_id={expected_instance} "
                f"actual_instance_id={instance_id}",
            )

    missing = sorted(set(expected) - seen)
    if missing:
        return session_core.reject(
            "sender-expectation-missing",
            None,
            "missing components: " + ",".join(missing),
        )
    return None


def command_session(args: argparse.Namespace) -> int:
    transcript_path = Path(args.path).expanduser().resolve()
    if not transcript_path.is_file():
        return emit_configuration_error(args, f"transcript file does not exist: {transcript_path}")

    try:
        expected = parse_sender_expectations(args.expect_sender)
        messages = load_session_document(transcript_path)
        result = session_core.validate_transcript(messages, session_validators())
    except (KeyError, TypeError, ValueError, ConformanceError, session_core.TranscriptError) as exc:
        return emit_configuration_error(args, str(exc))

    if result["accepted"]:
        sender_failure = apply_sender_expectations(messages, expected)
        if sender_failure is not None:
            result = sender_failure

    senders = observed_senders(messages)
    exit_code = EXIT_OK if result["accepted"] else EXIT_VALIDATION_FAILED

    if args.json_output:
        emit_json(
            "session",
            bool(result["accepted"]),
            exit_code,
            path=str(transcript_path),
            accepted=bool(result["accepted"]),
            terminal_status=result["terminal_status"],
            selected_version=result["selected_version"],
            selected_capabilities=result["selected_capabilities"],
            evidence_count=result["evidence_count"],
            reason=result["reason"],
            message_index=result["message_index"],
            detail=result["detail"],
            expected_senders={key: expected[key] for key in sorted(expected)},
            observed_senders=senders,
        )
    elif result["accepted"]:
        print(
            f"session valid: {transcript_path}: terminal_status={result['terminal_status']} "
            f"selected_version={result['selected_version']} evidence_count={result['evidence_count']}"
        )
    else:
        suffix = ""
        if result["message_index"] is not None:
            suffix += f" message_index={result['message_index']}"
        if result["detail"]:
            suffix += f" detail={result['detail']}"
        print(
            f"session invalid: {transcript_path}: reason={result['reason']}{suffix}",
            file=sys.stderr,
        )

    return exit_code


def command_list(args: argparse.Namespace) -> int:
    try:
        _, by_kind = load_registry()
    except (KeyError, TypeError, ConformanceError, json.JSONDecodeError, OSError) as exc:
        return emit_configuration_error(args, str(exc))

    schemas = [
        {
            "kind": kind,
            "schema_id": str(by_kind[kind]["schema_id"]),
            "version": str(by_kind[kind]["version"]),
        }
        for kind in sorted(by_kind)
    ]

    if args.json_output:
        emit_json(
            "list-schemas",
            True,
            EXIT_OK,
            schema_count=len(schemas),
            schemas=schemas,
        )
    else:
        for entry in schemas:
            print(f"{entry['kind']}\t{entry['schema_id']}\t{entry['version']}")
    return EXIT_OK


def add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit one machine-readable JSON object to stdout",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glomancy-conformance",
        description="Validate Glomancy Protocol payloads, fixtures, and full-session transcripts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate one JSON payload")
    validate_parser.add_argument("path", help="path to a JSON payload")
    validate_parser.add_argument("--schema-id", help="explicit registry schema ID")
    validate_parser.add_argument("--kind", help="explicit protocol message kind")
    validate_parser.add_argument(
        "--max-errors",
        type=int,
        default=10,
        choices=range(1, 51),
        metavar="1-50",
        help="maximum validation errors to print or return (default: 10)",
    )
    add_json_option(validate_parser)
    validate_parser.set_defaults(handler=command_validate)

    fixtures_parser = subparsers.add_parser(
        "fixtures", help="execute all valid/invalid public conformance fixtures"
    )
    add_json_option(fixtures_parser)
    fixtures_parser.set_defaults(handler=command_fixtures)

    session_parser = subparsers.add_parser(
        "session", help="validate and replay one complete public session transcript"
    )
    session_parser.add_argument("path", help="path to a transcript JSON document")
    session_parser.add_argument(
        "--expect-sender",
        action="append",
        default=[],
        metavar="COMPONENT=INSTANCE_ID",
        help=(
            "require messages from COMPONENT to use INSTANCE_ID; repeat for multiple components; "
            "this is a harness assertion, not a wire authentication rule"
        ),
    )
    add_json_option(session_parser)
    session_parser.set_defaults(handler=command_session)

    list_parser = subparsers.add_parser("list-schemas", help="list registered message schemas")
    add_json_option(list_parser)
    list_parser.set_defaults(handler=command_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())