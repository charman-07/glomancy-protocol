#!/usr/bin/env python3
"""Create and verify deterministic portable Glomancy task-verification bundles.

Bundles provide byte-integrity and reproducible public verification metadata only.
They are not signatures, provenance attestations, authorization decisions,
certifications, or proof that private editor/runtime operations were correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import glomancy_task_verification as task_verification
from validate_fixtures import ConformanceError, ROOT, load_json, validator_for, build_store

MANIFEST_SCHEMA = ROOT / "verification" / "v1" / "bundle-manifest.schema.json"
VERIFICATION_OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "task-verification-output.schema.json"
BUNDLE_FORMAT_VERSION = "1.0.0"
OUTPUT_VERSION = "1.0.0"
PROFILE_NAME = "profile.json"
SESSION_NAME = "session.json"
SNAPSHOT_NAME = "snapshot.json"
RESULT_NAME = "verification-result.json"
MANIFEST_NAME = "manifest.json"
CHECKSUM_NAME = "SHA256SUMS"
BASE_PAYLOAD_NAMES = (PROFILE_NAME, SESSION_NAME, RESULT_NAME)
EXIT_OK = 0
EXIT_FAILED = 2
EXIT_CONFIGURATION_ERROR = 3


class BundleError(RuntimeError):
    """Raised when a verification bundle cannot be created or verified."""


def json_validator(path: Path) -> Any:
    return validator_for(path, build_store())


def load_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise BundleError(f"{label} file does not exist: {path}")
    try:
        value = load_json(path)
    except ConformanceError as exc:
        raise BundleError(str(exc)) from exc
    if not isinstance(value, dict):
        raise BundleError(f"{label} must be a JSON object: {path}")
    return value


def validate_object(path: Path, schema_path: Path, label: str) -> dict[str, Any]:
    value = load_object(path, label)
    errors = sorted(
        json_validator(schema_path).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise BundleError(
            f"{label} schema validation failed: keyword={first.validator!r} "
            f"path={location}: {first.message}"
        )
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_entries(entries: list[dict[str, Any]]) -> str:
    records = "".join(
        f"{entry['name']}\t{entry['sha256']}\n"
        for entry in sorted(entries, key=lambda item: item["name"])
    )
    return hashlib.sha256(records.encode("utf-8")).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def ensure_empty_output_dir(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise BundleError(f"output path exists and is not a directory: {path}")
        existing = sorted(item.name for item in path.iterdir())
        if existing:
            raise BundleError(
                f"output directory must be empty before generation: {path} contains {existing}"
            )
    else:
        path.mkdir(parents=True, exist_ok=False)


def portable_verification_result(
    exit_code: int,
    result: dict[str, Any],
    snapshot_included: bool,
) -> dict[str, Any]:
    portable = dict(result)
    portable["profile_path"] = PROFILE_NAME
    portable["transcript_path"] = SESSION_NAME
    portable["snapshot_path"] = SNAPSHOT_NAME if snapshot_included else None
    return {
        "output_version": task_verification.OUTPUT_VERSION,
        "command": "verify-task",
        "ok": exit_code == task_verification.EXIT_OK,
        "exit_code": exit_code,
        **portable,
    }


def validate_portable_verification_result(value: dict[str, Any]) -> None:
    errors = sorted(
        json_validator(VERIFICATION_OUTPUT_SCHEMA).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise BundleError(
            "verification-result.json does not satisfy the published task verification output "
            f"contract: keyword={first.validator!r} path={location}: {first.message}"
        )


def expected_payload_names(snapshot_included: bool) -> list[str]:
    names = list(BASE_PAYLOAD_NAMES)
    if snapshot_included:
        names.append(SNAPSHOT_NAME)
    return sorted(names)


def build_file_entries(out_dir: Path, names: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name in sorted(names):
        path = out_dir / name
        if not path.is_file():
            raise BundleError(f"bundle payload is missing: {name}")
        size = path.stat().st_size
        if size <= 0:
            raise BundleError(f"bundle payload is empty: {name}")
        entries.append({"name": name, "sha256": sha256_file(path), "bytes": size})
    return entries


def build_manifest(out_dir: Path, snapshot_included: bool) -> dict[str, Any]:
    payload_names = expected_payload_names(snapshot_included)
    entries = build_file_entries(out_dir, payload_names)
    return {
        "bundle_format_version": BUNDLE_FORMAT_VERSION,
        "verification_output_version": task_verification.OUTPUT_VERSION,
        "verification_status": "verified",
        "snapshot_included": snapshot_included,
        "payload_files": payload_names,
        "files": entries,
        "aggregate_sha256": aggregate_entries(entries),
        "claims": {
            "signed": False,
            "provenance": False,
            "attestation": False,
            "producer_authentication": False,
            "authorization": False,
            "certification": False,
            "execution_correctness": False,
        },
    }


def checksum_records(out_dir: Path, names: list[str]) -> str:
    return "".join(
        f"{sha256_file(out_dir / name)}  {name}\n"
        for name in sorted(names)
    )


def create_bundle(
    *,
    profile_path: Path,
    transcript_path: Path,
    snapshot_path: Path | None,
    out_dir: Path,
) -> dict[str, Any]:
    profile_path = profile_path.expanduser().resolve()
    transcript_path = transcript_path.expanduser().resolve()
    snapshot_path = snapshot_path.expanduser().resolve() if snapshot_path is not None else None
    out_dir = out_dir.expanduser().resolve()

    try:
        profile = task_verification.load_profile(profile_path)
        exit_code, result = task_verification.verify(
            profile,
            profile_path,
            transcript_path,
            snapshot_path,
        )
    except (
        task_verification.VerificationError,
        ConformanceError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise BundleError(str(exc)) from exc

    if exit_code != task_verification.EXIT_OK or result.get("verified") is not True:
        reason = result.get("reason") or "verification-failed"
        detail = result.get("detail")
        suffix = f" detail={detail}" if detail else ""
        raise BundleError(f"task verification must pass before bundling: reason={reason}{suffix}")

    snapshot_included = snapshot_path is not None
    portable_result = portable_verification_result(exit_code, result, snapshot_included)
    validate_portable_verification_result(portable_result)

    ensure_empty_output_dir(out_dir)
    shutil.copyfile(profile_path, out_dir / PROFILE_NAME)
    shutil.copyfile(transcript_path, out_dir / SESSION_NAME)
    if snapshot_path is not None:
        if not snapshot_path.is_file():
            raise BundleError(f"snapshot file does not exist: {snapshot_path}")
        shutil.copyfile(snapshot_path, out_dir / SNAPSHOT_NAME)
    write_json(out_dir / RESULT_NAME, portable_result)

    manifest = build_manifest(out_dir, snapshot_included)
    write_json(out_dir / MANIFEST_NAME, manifest)
    validate_object(out_dir / MANIFEST_NAME, MANIFEST_SCHEMA, "bundle manifest")

    checksum_names = expected_payload_names(snapshot_included) + [MANIFEST_NAME]
    (out_dir / CHECKSUM_NAME).write_text(
        checksum_records(out_dir, checksum_names),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def parse_checksum_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise BundleError(f"bundle checksum file is missing: {CHECKSUM_NAME}")
    records: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise BundleError(f"cannot read {CHECKSUM_NAME}: {exc}") from exc
    if not lines:
        raise BundleError(f"{CHECKSUM_NAME} must not be empty")
    for line in lines:
        parts = line.split("  ", 1)
        if len(parts) != 2:
            raise BundleError(f"malformed checksum record: {line!r}")
        digest, name = parts
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise BundleError(f"malformed SHA-256 digest for {name!r}")
        if not name or "/" in name or "\\" in name:
            raise BundleError(f"invalid checksum filename: {name!r}")
        if name in records:
            raise BundleError(f"duplicate checksum filename: {name}")
        records[name] = digest
    return records


def verify_manifest_consistency(bundle_dir: Path, manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    snapshot_included = manifest.get("snapshot_included") is True
    expected_payloads = expected_payload_names(snapshot_included)
    payload_files = manifest.get("payload_files")
    if payload_files != expected_payloads:
        raise BundleError(
            f"manifest payload_files must equal deterministic payload set: {expected_payloads}"
        )

    files = manifest.get("files")
    if not isinstance(files, list):
        raise BundleError("manifest files must be an array")
    names = [entry.get("name") for entry in files if isinstance(entry, dict)]
    if names != expected_payloads:
        raise BundleError(f"manifest files must be sorted and match payload_files: {expected_payloads}")
    if len(names) != len(set(names)):
        raise BundleError("manifest contains duplicate file entries")

    allowed_names = set(expected_payloads + [MANIFEST_NAME, CHECKSUM_NAME])
    actual_names = {item.name for item in bundle_dir.iterdir()}
    if actual_names != allowed_names:
        missing = sorted(allowed_names - actual_names)
        unexpected = sorted(actual_names - allowed_names)
        raise BundleError(f"bundle file set mismatch: missing={missing} unexpected={unexpected}")

    for entry in files:
        if not isinstance(entry, dict):
            raise BundleError("manifest file entry must be an object")
        name = entry["name"]
        path = bundle_dir / name
        actual_size = path.stat().st_size
        if actual_size != entry["bytes"]:
            raise BundleError(
                f"bundle payload size mismatch for {name}: expected={entry['bytes']} actual={actual_size}"
            )
        actual_hash = sha256_file(path)
        if actual_hash != entry["sha256"]:
            raise BundleError(
                f"bundle payload SHA-256 mismatch for {name}: expected={entry['sha256']} actual={actual_hash}"
            )

    actual_aggregate = aggregate_entries(files)
    if actual_aggregate != manifest.get("aggregate_sha256"):
        raise BundleError(
            "bundle aggregate SHA-256 mismatch: "
            f"expected={manifest.get('aggregate_sha256')} actual={actual_aggregate}"
        )

    checksums = parse_checksum_file(bundle_dir / CHECKSUM_NAME)
    expected_checksum_names = sorted(expected_payloads + [MANIFEST_NAME])
    if sorted(checksums) != expected_checksum_names:
        raise BundleError(
            f"{CHECKSUM_NAME} file set mismatch: expected={expected_checksum_names} "
            f"actual={sorted(checksums)}"
        )
    for name in expected_checksum_names:
        actual_hash = sha256_file(bundle_dir / name)
        if checksums[name] != actual_hash:
            raise BundleError(
                f"{CHECKSUM_NAME} mismatch for {name}: expected={checksums[name]} actual={actual_hash}"
            )

    return snapshot_included, expected_payloads


def verify_bundle(bundle_dir: Path) -> dict[str, Any]:
    bundle_dir = bundle_dir.expanduser().resolve()
    if not bundle_dir.is_dir():
        raise BundleError(f"bundle directory does not exist: {bundle_dir}")

    manifest = validate_object(bundle_dir / MANIFEST_NAME, MANIFEST_SCHEMA, "bundle manifest")
    snapshot_included, payload_names = verify_manifest_consistency(bundle_dir, manifest)

    portable_result = validate_object(
        bundle_dir / RESULT_NAME,
        VERIFICATION_OUTPUT_SCHEMA,
        "verification result",
    )
    if portable_result.get("verified") is not True or portable_result.get("exit_code") != 0:
        raise BundleError("bundled verification result must represent a successful verification")
    if portable_result.get("profile_path") != PROFILE_NAME:
        raise BundleError("bundled verification result profile_path must be profile.json")
    if portable_result.get("transcript_path") != SESSION_NAME:
        raise BundleError("bundled verification result transcript_path must be session.json")
    expected_snapshot_path = SNAPSHOT_NAME if snapshot_included else None
    if portable_result.get("snapshot_path") != expected_snapshot_path:
        raise BundleError(
            "bundled verification result snapshot_path does not match manifest snapshot_included"
        )

    profile_path = bundle_dir / PROFILE_NAME
    transcript_path = bundle_dir / SESSION_NAME
    snapshot_path = bundle_dir / SNAPSHOT_NAME if snapshot_included else None
    try:
        profile = task_verification.load_profile(profile_path)
        exit_code, result = task_verification.verify(
            profile,
            profile_path,
            transcript_path,
            snapshot_path,
        )
    except (
        task_verification.VerificationError,
        ConformanceError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise BundleError(f"bundled task verification could not be re-evaluated: {exc}") from exc

    if exit_code != task_verification.EXIT_OK or result.get("verified") is not True:
        reason = result.get("reason") or "verification-failed"
        raise BundleError(f"bundled task verification no longer passes: reason={reason}")

    recomputed = portable_verification_result(exit_code, result, snapshot_included)
    validate_portable_verification_result(recomputed)
    if recomputed != portable_result:
        raise BundleError("verification-result.json does not match recomputed portable verification result")

    return {
        "bundle_format_version": manifest["bundle_format_version"],
        "verified": True,
        "snapshot_included": snapshot_included,
        "payload_files": payload_names,
        "aggregate_sha256": manifest["aggregate_sha256"],
        "terminal_status": portable_result.get("terminal_status"),
        "read_back_verified": portable_result.get("read_back_verified"),
        "terminal_referenced_evidence_type_counts": portable_result.get(
            "terminal_referenced_evidence_type_counts", {}
        ),
        "claims": manifest["claims"],
    }


def emit_json(command: str, ok: bool, exit_code: int, **fields: Any) -> None:
    payload = {
        "output_version": OUTPUT_VERSION,
        "command": command,
        "ok": ok,
        "exit_code": exit_code,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="create a deterministic verification bundle")
    create_parser.add_argument("--profile", required=True, type=Path)
    create_parser.add_argument("--transcript", required=True, type=Path)
    create_parser.add_argument("--snapshot", type=Path)
    create_parser.add_argument("--out-dir", required=True, type=Path)
    create_parser.add_argument("--json", action="store_true", dest="json_output")

    verify_parser = subparsers.add_parser("verify", help="verify and replay a verification bundle")
    verify_parser.add_argument("bundle_dir", type=Path)
    verify_parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "create":
            manifest = create_bundle(
                profile_path=args.profile,
                transcript_path=args.transcript,
                snapshot_path=args.snapshot,
                out_dir=args.out_dir,
            )
            fields = {
                "bundle_dir": str(args.out_dir.expanduser().resolve()),
                "bundle_format_version": manifest["bundle_format_version"],
                "snapshot_included": manifest["snapshot_included"],
                "payload_files": manifest["payload_files"],
                "aggregate_sha256": manifest["aggregate_sha256"],
            }
            if args.json_output:
                emit_json("create", True, EXIT_OK, **fields)
            else:
                print(
                    "verification bundle created: "
                    f"aggregate={manifest['aggregate_sha256']} path={fields['bundle_dir']}"
                )
            return EXIT_OK

        result = verify_bundle(args.bundle_dir)
        fields = {"bundle_dir": str(args.bundle_dir.expanduser().resolve()), **result}
        if args.json_output:
            emit_json("verify", True, EXIT_OK, **fields)
        else:
            print(
                "verification bundle passed: "
                f"aggregate={result['aggregate_sha256']} "
                f"terminal_status={result['terminal_status']}"
            )
        return EXIT_OK
    except BundleError as exc:
        if getattr(args, "json_output", False):
            emit_json(
                args.command,
                False,
                EXIT_FAILED,
                error={"type": "bundle", "message": str(exc)},
            )
        else:
            print(f"verification bundle {args.command} failed: {exc}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
