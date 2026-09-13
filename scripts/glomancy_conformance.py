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


def render_error(error: Any) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "<root>"
    return f"keyword={error.validator!r} path={location}: {error.message}"


def command_validate(args: argparse.Namespace) -> int:
    document_path = Path(args.path).expanduser().resolve()
    if not document_path.is_file():
        print(f"configuration error: payload file does not exist: {document_path}", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR

    try:
        document = load_json(document_path)
        entry = choose_entry(document, args.schema_id, args.kind)
        schema_path = resolve_schema_file(entry)
        validator = validator_for(schema_path, build_store())
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    except (KeyError, TypeError, ConformanceError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR

    if errors:
        schema_id = entry.get("schema_id", "<unknown>")
        print(f"invalid: {document_path}: schema={schema_id}", file=sys.stderr)
        for error in errors[: args.max_errors]:
            print(f"  - {render_error(error)}", file=sys.stderr)
        if len(errors) > args.max_errors:
            print(f"  - ... {len(errors) - args.max_errors} more error(s)", file=sys.stderr)
        return EXIT_VALIDATION_FAILED

    print(
        f"valid: {document_path}: schema={entry.get('schema_id')}"
        + (f" kind={entry.get('message_kind')}" if entry.get("message_kind") else "")
    )
    return EXIT_OK


def command_fixtures(_: argparse.Namespace) -> int:
    try:
        valid_count, invalid_count = validate_manifest()
    except (KeyError, TypeError, ConformanceError) as exc:
        print(f"fixture conformance failed: {exc}", file=sys.stderr)
        return EXIT_VALIDATION_FAILED

    print(
        "fixture conformance passed: "
        f"{valid_count} valid fixtures accepted, {invalid_count} invalid fixtures rejected"
    )
    return EXIT_OK


def command_list(_: argparse.Namespace) -> int:
    try:
        _, by_kind = load_registry()
    except (KeyError, TypeError, ConformanceError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIGURATION_ERROR

    for kind in sorted(by_kind):
        entry = by_kind[kind]
        print(f"{kind}\t{entry['schema_id']}\t{entry['version']}")
    return EXIT_OK


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
        help="maximum validation errors to print (default: 10)",
    )
    validate_parser.set_defaults(handler=command_validate)

    fixtures_parser = subparsers.add_parser(
        "fixtures", help="execute all valid/invalid public conformance fixtures"
    )
    fixtures_parser.set_defaults(handler=command_fixtures)

    list_parser = subparsers.add_parser("list-schemas", help="list registered message schemas")
    list_parser.set_defaults(handler=command_list)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
