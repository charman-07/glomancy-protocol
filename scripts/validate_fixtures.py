#!/usr/bin/env python3
"""Execute the public conformance fixture corpus against local JSON Schemas."""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from jsonschema import Draft202012Validator, FormatChecker, RefResolver

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"
EXAMPLES_DIR = ROOT / "examples" / "v1"
MANIFEST = EXAMPLES_DIR / "manifest.json"


class ConformanceError(RuntimeError):
    pass


def display_path(path: Path) -> str:
    """Render repository paths compactly while supporting external CLI inputs."""
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConformanceError(f"invalid JSON: {display_path(path)}: {exc}") from exc


def build_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        schema = load_json(path)
        store[path.name] = schema
        store[path.as_uri()] = schema
        schema_id = schema.get("$id") if isinstance(schema, dict) else None
        if isinstance(schema_id, str) and schema_id:
            store[schema_id] = schema
    return store


def validator_for(schema_path: Path, store: dict[str, Any]) -> Draft202012Validator:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    resolver = RefResolver(
        base_uri=schema_path.as_uri(),
        referrer=schema,
        store=store,
    )
    return Draft202012Validator(
        schema,
        resolver=resolver,
        format_checker=FormatChecker(),
    )


def fixture_path(value: str) -> Path:
    path = (EXAMPLES_DIR / value).resolve()
    try:
        path.relative_to(EXAMPLES_DIR.resolve())
    except ValueError as exc:
        raise ConformanceError(f"fixture path escapes examples/v1: {value}") from exc
    if not path.is_file():
        raise ConformanceError(f"fixture does not exist: {value}")
    return path


def schema_path(value: str) -> Path:
    path = (EXAMPLES_DIR / value).resolve()
    try:
        path.relative_to(SCHEMA_DIR.resolve())
    except ValueError as exc:
        raise ConformanceError(f"schema path is outside schemas/v1: {value}") from exc
    if not path.is_file():
        raise ConformanceError(f"schema does not exist: {value}")
    return path


def error_keywords(errors: list[Any]) -> set[str]:
    keywords: set[str] = set()

    def visit(error: Any) -> None:
        validator = getattr(error, "validator", None)
        if isinstance(validator, str):
            keywords.add(validator)
        for child in getattr(error, "context", []):
            visit(child)

    for error in errors:
        visit(error)
    return keywords


def validate_manifest() -> tuple[int, int]:
    manifest = load_json(MANIFEST)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ConformanceError("unsupported fixture manifest schema_version")

    valid_entries = manifest.get("valid", [])
    invalid_entries = manifest.get("invalid", [])
    if not isinstance(valid_entries, list) or not isinstance(invalid_entries, list):
        raise ConformanceError("fixture manifest valid/invalid entries must be arrays")

    store = build_store()
    validators: dict[Path, Draft202012Validator] = {}

    def get_validator(path: Path) -> Draft202012Validator:
        if path not in validators:
            validators[path] = validator_for(path, store)
        return validators[path]

    seen: set[str] = set()

    for entry in valid_entries:
        if not isinstance(entry, dict):
            raise ConformanceError("valid fixture entry must be an object")
        fixture = fixture_path(entry["file"])
        schema = schema_path(entry["schema"])
        key = str(fixture.relative_to(ROOT))
        if key in seen:
            raise ConformanceError(f"duplicate fixture entry: {key}")
        seen.add(key)

        instance = load_json(fixture)
        errors = sorted(get_validator(schema).iter_errors(instance), key=lambda error: list(error.path))
        if errors:
            first = errors[0]
            location = "/".join(str(part) for part in first.absolute_path) or "<root>"
            raise ConformanceError(
                f"valid fixture rejected: {key}: keyword={first.validator!r} path={location}: {first.message}"
            )

    for entry in invalid_entries:
        if not isinstance(entry, dict):
            raise ConformanceError("invalid fixture entry must be an object")
        fixture = fixture_path(entry["file"])
        schema = schema_path(entry["schema"])
        expected_keyword = entry.get("expected_keyword")
        if not isinstance(expected_keyword, str) or not expected_keyword:
            raise ConformanceError(f"invalid fixture lacks expected_keyword: {entry.get('file')!r}")

        key = str(fixture.relative_to(ROOT))
        if key in seen:
            raise ConformanceError(f"duplicate fixture entry: {key}")
        seen.add(key)

        instance = load_json(fixture)
        errors = list(get_validator(schema).iter_errors(instance))
        if not errors:
            raise ConformanceError(f"invalid fixture was accepted: {key}")

        observed = error_keywords(errors)
        if expected_keyword not in observed:
            rendered = ", ".join(sorted(observed)) or "<none>"
            raise ConformanceError(
                f"invalid fixture failed for the wrong reason: {key}: "
                f"expected {expected_keyword!r}, observed [{rendered}]"
            )

    return len(valid_entries), len(invalid_entries)


def main() -> int:
    try:
        valid_count, invalid_count = validate_manifest()
    except (KeyError, TypeError, ConformanceError) as exc:
        print(f"fixture conformance failed: {exc}", file=sys.stderr)
        return 1

    print(
        "fixture conformance passed: "
        f"{valid_count} valid fixtures accepted, {invalid_count} invalid fixtures rejected"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
