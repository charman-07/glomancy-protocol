#!/usr/bin/env python3
"""Validate the release-evidence generator and its Draft 2020-12 JSON contract."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from release_evidence_bundle import PAYLOAD_FILES, generate_bundle

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "evidence" / "v1" / "release-evidence.schema.json"
FINGERPRINT = ROOT / "contracts" / "v1" / "fingerprint.json"
SUPPORT = ROOT / "support" / "v1" / "policy.json"


class ValidationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_checksums(bundle: Path) -> None:
    checksum_file = bundle / "SHA256SUMS"
    lines = checksum_file.read_text(encoding="utf-8").splitlines()
    expected_names = sorted(PAYLOAD_FILES)
    if len(lines) != len(expected_names):
        raise ValidationError("SHA256SUMS does not contain exactly one record per payload file")

    parsed: dict[str, str] = {}
    for line in lines:
        try:
            digest, name = line.split("  ", 1)
        except ValueError as exc:
            raise ValidationError(f"malformed SHA256SUMS line: {line!r}") from exc
        if name in parsed:
            raise ValidationError(f"duplicate SHA256SUMS entry: {name}")
        parsed[name] = digest

    if sorted(parsed) != expected_names:
        raise ValidationError(f"SHA256SUMS payload set drift: {sorted(parsed)}")
    for name, digest in parsed.items():
        actual = sha256_file(bundle / name)
        if actual != digest:
            raise ValidationError(f"checksum mismatch for {name}: expected {digest}, got {actual}")


def validate() -> None:
    schema = load_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    with tempfile.TemporaryDirectory(prefix="glomancy-release-evidence-") as temp_root:
        root = Path(temp_root)
        passed_dir = root / "passed"
        passed = generate_bundle(
            passed_dir,
            audited_ref="self-check",
            audited_sha="0" * 40,
            quality_result="success",
            contract_result="success",
            portability_result="success",
            expected_version=None,
        )
        errors = sorted(validator.iter_errors(passed), key=lambda error: list(error.path))
        if errors:
            rendered = "; ".join(error.message for error in errors)
            raise ValidationError(f"generated passing evidence violates schema: {rendered}")
        if passed.get("audit_status") != "passed":
            raise ValidationError("all-success gates did not produce audit_status=passed")
        if (passed_dir / "public-contract-fingerprint.json").read_bytes() != FINGERPRINT.read_bytes():
            raise ValidationError("fingerprint copy is not byte-identical to tracked source")
        if (passed_dir / "release-support-policy.json").read_bytes() != SUPPORT.read_bytes():
            raise ValidationError("support-policy copy is not byte-identical to tracked source")
        validate_checksums(passed_dir)

        failed_dir = root / "failed"
        failed = generate_bundle(
            failed_dir,
            audited_ref="self-check-failure",
            audited_sha="1" * 40,
            quality_result="success",
            contract_result="failure",
            portability_result="success",
            expected_version=None,
        )
        errors = sorted(validator.iter_errors(failed), key=lambda error: list(error.path))
        if errors:
            rendered = "; ".join(error.message for error in errors)
            raise ValidationError(f"generated failed evidence violates schema: {rendered}")
        if failed.get("audit_status") != "failed":
            raise ValidationError("a failed required gate did not produce audit_status=failed")
        validate_checksums(failed_dir)


def main() -> int:
    try:
        validate()
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"release evidence validation failed: {exc}", file=sys.stderr)
        return 1

    print("release evidence validation passed: schema, deterministic copies, gate status, and SHA256SUMS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
