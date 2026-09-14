#!/usr/bin/env python3
"""Validate deterministic standalone Glomancy Protocol contract bundle generation."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from build_contract_bundle import (
    BUNDLE_FORMAT_VERSION,
    FIXED_ZIP_TIME,
    BundleError,
    build_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must contain a JSON object")
    return value


def parse_checksums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"SHA256SUMS is not UTF-8: {exc}") from exc

    result: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        if "  " not in line:
            raise ValidationError(f"SHA256SUMS line {line_number} has invalid format")
        digest, path = line.split("  ", 1)
        if HASH_RE.fullmatch(digest) is None:
            raise ValidationError(f"SHA256SUMS line {line_number} has invalid digest")
        if not path or path in result:
            raise ValidationError(f"SHA256SUMS line {line_number} has duplicate/empty path")
        result[path] = digest
    return result


def validate_archive(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValidationError("archive contains duplicate member names")
            if "BUNDLE_MANIFEST.json" not in names or "SHA256SUMS" not in names:
                raise ValidationError("archive is missing generated bundle metadata")

            for info in infos:
                if info.date_time != FIXED_ZIP_TIME:
                    raise ValidationError(
                        f"archive member has non-deterministic timestamp: {info.filename}"
                    )
                mode = (info.external_attr >> 16) & 0o777
                if mode != 0o644:
                    raise ValidationError(
                        f"archive member has unexpected permission mode {oct(mode)}: {info.filename}"
                    )

            manifest_bytes = archive.read("BUNDLE_MANIFEST.json")
            manifest = load_json_bytes(manifest_bytes, "BUNDLE_MANIFEST.json")
            if manifest.get("bundle_format_version") != BUNDLE_FORMAT_VERSION:
                raise ValidationError("bundle_format_version mismatch")
            fingerprint = manifest.get("public_contract_fingerprint")
            if not isinstance(fingerprint, str) or HASH_RE.fullmatch(fingerprint) is None:
                raise ValidationError("bundle manifest has invalid public_contract_fingerprint")

            tracked_fingerprint = json.loads(
                (ROOT / "contracts" / "v1" / "fingerprint.json").read_text(encoding="utf-8")
            ).get("aggregate_sha256")
            if fingerprint != tracked_fingerprint:
                raise ValidationError("bundle fingerprint does not match tracked public contract fingerprint")

            files = manifest.get("files")
            if not isinstance(files, list) or not files:
                raise ValidationError("bundle manifest files must be a non-empty array")
            if manifest.get("file_count") != len(files):
                raise ValidationError("bundle manifest file_count mismatch")

            manifest_paths: list[str] = []
            for index, entry in enumerate(files):
                if not isinstance(entry, dict):
                    raise ValidationError(f"bundle manifest file entry {index} must be an object")
                relative = entry.get("path")
                size = entry.get("bytes")
                digest = entry.get("sha256")
                if not isinstance(relative, str) or not relative:
                    raise ValidationError(f"bundle manifest file entry {index} has invalid path")
                if relative.startswith("/") or ".." in Path(relative).parts:
                    raise ValidationError(f"unsafe manifest path: {relative}")
                if not isinstance(size, int) or size < 0:
                    raise ValidationError(f"bundle manifest file entry {index} has invalid byte size")
                if not isinstance(digest, str) or HASH_RE.fullmatch(digest) is None:
                    raise ValidationError(f"bundle manifest file entry {index} has invalid SHA-256")
                if relative not in names:
                    raise ValidationError(f"manifest references missing archive member: {relative}")
                payload = archive.read(relative)
                if len(payload) != size:
                    raise ValidationError(f"byte-size mismatch for {relative}")
                if sha256_bytes(payload) != digest:
                    raise ValidationError(f"SHA-256 mismatch for {relative}")
                manifest_paths.append(relative)

            if len(manifest_paths) != len(set(manifest_paths)):
                raise ValidationError("bundle manifest contains duplicate file paths")
            if manifest_paths != sorted(manifest_paths):
                raise ValidationError("bundle manifest file entries are not sorted by path")

            expected_names = set(manifest_paths) | {"BUNDLE_MANIFEST.json", "SHA256SUMS"}
            if set(names) != expected_names:
                missing = sorted(expected_names - set(names))
                unexpected = sorted(set(names) - expected_names)
                raise ValidationError(
                    f"archive member set mismatch: missing={missing}, unexpected={unexpected}"
                )

            checksums = parse_checksums(archive.read("SHA256SUMS"))
            expected_checksum_paths = set(manifest_paths) | {"BUNDLE_MANIFEST.json"}
            if set(checksums) != expected_checksum_paths:
                raise ValidationError("SHA256SUMS path set does not match payload + manifest set")
            for relative, expected_digest in checksums.items():
                actual_digest = sha256_bytes(archive.read(relative))
                if actual_digest != expected_digest:
                    raise ValidationError(f"SHA256SUMS mismatch for {relative}")

            return manifest
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot validate archive {path}: {exc}") from exc


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="glomancy-contract-bundle-") as temp:
            root = Path(temp)
            first_dir = root / "first"
            second_dir = root / "second"
            first_zip = root / "first.zip"
            second_zip = root / "second.zip"

            first = build_bundle(first_dir, first_zip)
            second = build_bundle(second_dir, second_zip)

            first_bytes = first_zip.read_bytes()
            second_bytes = second_zip.read_bytes()
            if first_bytes != second_bytes:
                raise ValidationError("repeated bundle builds are not byte-identical")
            if first.get("archive_sha256") != second.get("archive_sha256"):
                raise ValidationError("repeated bundle SHA-256 values differ")

            manifest = validate_archive(first_zip)
            if first.get("file_count") != manifest.get("file_count"):
                raise ValidationError("builder metadata and archive manifest file counts differ")

            print(
                "standalone contract bundle validation passed: "
                f"files={manifest['file_count']} "
                f"wire={manifest['wire_protocol_version']} "
                f"zip_sha256={sha256_bytes(first_bytes)}"
            )
        return 0
    except (BundleError, ValidationError, OSError) as exc:
        print(f"standalone contract bundle validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
