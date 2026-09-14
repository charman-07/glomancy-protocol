#!/usr/bin/env python3
"""Verify one already-built Glomancy Protocol standalone contract archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from validate_contract_bundle import ValidationError, validate_archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="contract bundle ZIP to verify")
    parser.add_argument("--json", action="store_true", help="print verified metadata as JSON")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    try:
        manifest = validate_archive(args.archive)
        archive_sha256 = sha256_file(args.archive)
        result = {
            "archive": args.archive.name,
            "archive_bytes": args.archive.stat().st_size,
            "archive_sha256": archive_sha256,
            "bundle_format_version": manifest["bundle_format_version"],
            "package_version": manifest["package_version"],
            "wire_protocol_version": manifest["wire_protocol_version"],
            "public_contract_fingerprint": manifest["public_contract_fingerprint"],
            "file_count": manifest["file_count"],
            "assurance_boundary": (
                "Archive integrity verification against the checked-out public contract only; "
                "not a signature, provenance attestation, certification, authorization decision, "
                "or production-adoption claim."
            ),
        }
    except (ValidationError, OSError, KeyError) as exc:
        print(f"contract bundle verification failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "contract bundle verification passed: "
            f"archive={result['archive']} "
            f"files={result['file_count']} "
            f"wire={result['wire_protocol_version']} "
            f"fingerprint={result['public_contract_fingerprint']} "
            f"zip_sha256={result['archive_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
