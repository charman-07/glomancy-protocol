#!/usr/bin/env python3
"""Validate the intentional Cargo package file boundary for Glomancy Protocol."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REQUIRED = {
    "Cargo.toml",
    "README.md",
    "LICENSE",
    "src/lib.rs",
    "src/version.rs",
    "registry/v1/manifest.json",
    "contracts/v1/fingerprint.json",
}

OPTIONAL_GENERATED = {
    ".cargo_vcs_info.json",
    "Cargo.lock",
    "Cargo.toml.orig",
}

ALLOWED_EXACT = {
    "Cargo.toml",
    "README.md",
    "LICENSE",
    *OPTIONAL_GENERATED,
}

ALLOWED_PREFIXES = (
    "src/",
    "examples/",
    "schemas/v1/",
    "registry/v1/",
    "compatibility/v1/",
    "compatibility/snapshots/",
    "capabilities/v1/",
    "vectors/v1/",
    "errors/v1/",
    "security/v1/",
    "limits/v1/",
    "support/v1/",
    "contracts/v1/",
    "conformance/v1/",
)

FORBIDDEN_PREFIXES = (
    ".github/",
    "assets/",
    "docs/",
    "downstream/",
    "scripts/",
    "target/",
)


class ValidationError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file_list", type=Path, help="newline-delimited output of cargo package --list")
    return parser.parse_args()


def normalize(line: str) -> str:
    value = line.strip().replace("\\", "/")
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValidationError(f"unsafe package path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise ValidationError(f"non-canonical package path: {value!r}")
    return value


def validate(paths: list[str]) -> None:
    if not paths:
        raise ValidationError("cargo package file list is empty")
    if len(paths) != len(set(paths)):
        raise ValidationError("cargo package file list contains duplicate paths")

    selected = set(paths)
    missing = sorted(REQUIRED - selected)
    if missing:
        raise ValidationError(f"required package files are missing: {missing}")

    for path in paths:
        if path.startswith(FORBIDDEN_PREFIXES):
            raise ValidationError(f"repository-only path leaked into Cargo package: {path}")
        if path in ALLOWED_EXACT:
            continue
        if any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            continue
        raise ValidationError(f"unexpected Cargo package path outside allowlist: {path}")

    if not any(path.startswith("schemas/v1/") for path in paths):
        raise ValidationError("Cargo package contains no public v1 schemas")
    if not any(path.startswith("examples/v1/valid/") for path in paths):
        raise ValidationError("Cargo package contains no valid public conformance examples")
    if not any(path.startswith("examples/v1/invalid/") for path in paths):
        raise ValidationError("Cargo package contains no invalid public conformance examples")


def main() -> int:
    args = parse_args()
    try:
        raw = args.file_list.read_text(encoding="utf-8").splitlines()
        paths = [value for line in raw if (value := normalize(line))]
        validate(paths)
    except (OSError, ValidationError) as exc:
        print(f"Cargo package boundary validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Cargo package boundary validation passed: files={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
