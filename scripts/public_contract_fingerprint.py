#!/usr/bin/env python3
"""Generate and verify the deterministic public Glomancy Protocol contract fingerprint.

The fingerprint is integrity metadata only. It is not a signature, authenticity
proof, provenance statement, authorization decision, or certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "contracts" / "v1" / "fingerprint.json"
FORMAT_VERSION = "1.0.0"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

CANONICAL_PATHS = (
    "capabilities/v1/profile.json",
    "compatibility/snapshots/manifest.json",
    "compatibility/v1/compatibility-matrix.json",
    "conformance/v1/cli-output.schema.json",
    "errors/v1/catalog.json",
    "registry/v1/manifest.json",
    "support/v1/policy.json",
    "vectors/v1/manifest.json",
)

AGGREGATE_DESCRIPTION = (
    "SHA-256 of UTF-8 records '<path>\\t<sha256>\\n' for the exact canonical "
    "entry set sorted lexicographically by path"
)


class FingerprintError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise FingerprintError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def aggregate(entries: list[dict[str, str]]) -> str:
    records = "".join(
        f"{entry['path']}\t{entry['sha256']}\n"
        for entry in sorted(entries, key=lambda item: item["path"])
    )
    return hashlib.sha256(records.encode("utf-8")).hexdigest()


def generate() -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    for relative in CANONICAL_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FingerprintError(f"canonical contract file is missing: {relative}")
        entries.append({"path": relative, "sha256": sha256_file(path)})

    entries.sort(key=lambda item: item["path"])
    return {
        "fingerprint_format_version": FORMAT_VERSION,
        "hash_algorithm": "sha256",
        "aggregate_algorithm": AGGREGATE_DESCRIPTION,
        "entries": entries,
        "aggregate_sha256": aggregate(entries),
    }


def load_manifest() -> dict[str, Any]:
    try:
        value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise FingerprintError(f"cannot read {MANIFEST_PATH.relative_to(ROOT)}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise FingerprintError(f"invalid JSON in {MANIFEST_PATH.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise FingerprintError("fingerprint manifest must be a JSON object")
    return value


def validate_shape(manifest: dict[str, Any]) -> None:
    if manifest.get("fingerprint_format_version") != FORMAT_VERSION:
        raise FingerprintError(
            f"fingerprint_format_version must be {FORMAT_VERSION!r}"
        )
    if manifest.get("hash_algorithm") != "sha256":
        raise FingerprintError("hash_algorithm must be 'sha256'")
    if manifest.get("aggregate_algorithm") != AGGREGATE_DESCRIPTION:
        raise FingerprintError("aggregate_algorithm does not match the canonical algorithm")

    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise FingerprintError("entries must be an array")

    paths: list[str] = []
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, dict):
            raise FingerprintError(f"entry {index} must be an object")
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(path, str) or not path:
            raise FingerprintError(f"entry {index} has invalid path")
        if not isinstance(digest, str) or HASH_RE.fullmatch(digest) is None:
            raise FingerprintError(f"entry {index} has invalid sha256")
        paths.append(path)

    if len(paths) != len(set(paths)):
        raise FingerprintError("fingerprint manifest contains duplicate paths")
    if paths != sorted(paths):
        raise FingerprintError("fingerprint entries must be sorted lexicographically by path")
    if tuple(paths) != CANONICAL_PATHS:
        missing = sorted(set(CANONICAL_PATHS) - set(paths))
        unexpected = sorted(set(paths) - set(CANONICAL_PATHS))
        raise FingerprintError(
            f"canonical entry set mismatch: missing={missing}, unexpected={unexpected}"
        )

    aggregate_sha = manifest.get("aggregate_sha256")
    if not isinstance(aggregate_sha, str) or HASH_RE.fullmatch(aggregate_sha) is None:
        raise FingerprintError("aggregate_sha256 must be a lowercase 64-character SHA-256")


def check() -> dict[str, Any]:
    actual = generate()
    tracked = load_manifest()
    try:
        validate_shape(tracked)
    except FingerprintError as exc:
        print("expected canonical fingerprint manifest:", file=sys.stderr)
        print(json.dumps(actual, indent=2) + "\n", file=sys.stderr)
        raise exc

    tracked_entries = tracked["entries"]
    calculated_from_tracked = aggregate(tracked_entries)
    if calculated_from_tracked != tracked["aggregate_sha256"]:
        print("expected canonical fingerprint manifest:", file=sys.stderr)
        print(json.dumps(actual, indent=2) + "\n", file=sys.stderr)
        raise FingerprintError("tracked aggregate_sha256 does not match its entry records")

    if tracked != actual:
        print("expected canonical fingerprint manifest:", file=sys.stderr)
        print(json.dumps(actual, indent=2) + "\n", file=sys.stderr)
        raise FingerprintError("tracked fingerprint does not match canonical repository content")

    return actual


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify the tracked manifest")
    mode.add_argument("--generate", action="store_true", help="print the canonical manifest JSON")
    mode.add_argument("--fingerprint", action="store_true", help="print only aggregate SHA-256")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.check:
            manifest = check()
            print(
                "public contract fingerprint validation passed: "
                f"{manifest['aggregate_sha256']} ({len(manifest['entries'])} canonical files)"
            )
            return 0

        manifest = generate()
        if args.fingerprint:
            print(manifest["aggregate_sha256"])
        else:
            print(json.dumps(manifest, indent=2) + "\n")
        return 0
    except FingerprintError as exc:
        print(f"public contract fingerprint validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
