#!/usr/bin/env python3
"""Public conformance CLI for Glomancy Protocol payloads and fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

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
        description="Validate Glomancy Protocol payloads and the public fixture corpus.",
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
