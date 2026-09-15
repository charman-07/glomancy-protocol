#!/usr/bin/env python3
"""Exercise deterministic verification bundles and their machine-readable contract."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "glomancy_verification_bundle.py"
OUTPUT_SCHEMA = ROOT / "conformance" / "v1" / "verification-bundle-output.schema.json"
SUCCESS_SESSION = (
    ROOT
    / "transcripts"
    / "v1"
    / "accepted"
    / "approval-gated-success-with-evidence.json"
)


class ContractError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def aggregate_entries(entries: list[dict[str, Any]]) -> str:
    records = "".join(
        f"{entry['name']}\t{entry['sha256']}\n"
        for entry in sorted(entries, key=lambda item: item["name"])
    )
    return hashlib.sha256(records.encode("utf-8")).hexdigest()


def session_document() -> dict[str, Any]:
    document = load_json(SUCCESS_SESSION)
    if not isinstance(document, dict):
        raise ContractError("success session fixture must be an object")
    messages = document.get("messages")
    if not isinstance(messages, list):
        raise ContractError("success session fixture messages must be an array")
    for message in messages:
        if isinstance(message, dict) and message.get("kind") == "task.submit":
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ContractError("task.submit payload must be an object")
            payload["context_refs"] = [
                {
                    "source_type": "project",
                    "uri": "glomancy://project/bundle-demo",
                    "revision": "project-r11",
                },
                {
                    "source_type": "asset",
                    "uri": "glomancy://asset/bundle-selected-object",
                    "revision": "asset-r12",
                },
            ]
            return document
    raise ContractError("success session fixture must contain task.submit")


def snapshot_document() -> dict[str, Any]:
    return {
        "snapshot_format_version": "1.0.0",
        "snapshot_id": "99999999-9999-4999-8999-999999999999",
        "captured_at": "2026-09-15T10:00:02Z",
        "sources": [
            {
                "source_type": "project",
                "uri": "glomancy://project/bundle-demo",
                "revision": "project-r11",
            },
            {
                "source_type": "asset",
                "uri": "glomancy://asset/bundle-selected-object",
                "revision": "asset-r12",
            },
            {
                "source_type": "memory",
                "uri": "glomancy://memory/bundle-extra-context",
            },
        ],
    }


def profile_document(require_snapshot: bool) -> dict[str, Any]:
    return {
        "profile_version": "1.0.0",
        "require_success": True,
        "require_context_snapshot_match": require_snapshot,
        "require_read_back_verified": True,
        "required_evidence_types": ["read-back"],
    }


def schema_errors(validator: Draft202012Validator, payload: Any) -> str:
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    lines: list[str] = []
    for error in errors[:10]:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        lines.append(f"{location}: {error.message}")
    if len(errors) > 10:
        lines.append(f"... {len(errors) - 10} more error(s)")
    return "\n".join(lines)


def run_json(
    validator: Draft202012Validator,
    name: str,
    arguments: list[str],
    expected_exit: int,
    message_contains: str | None = None,
) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(TOOL), *arguments, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != expected_exit:
        raise ContractError(
            f"{name}: expected exit {expected_exit}, got {completed.returncode}; "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    if completed.stderr.strip():
        raise ContractError(f"{name}: JSON mode unexpectedly wrote stderr: {completed.stderr!r}")
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise ContractError(f"{name}: stdout is not one JSON object: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"{name}: output must be a JSON object")
    if payload.get("exit_code") != completed.returncode:
        raise ContractError(f"{name}: JSON exit_code does not match process exit")
    errors = list(validator.iter_errors(payload))
    if errors:
        raise ContractError(f"{name}: output does not match schema:\n{schema_errors(validator, payload)}")
    if message_contains is not None:
        error = payload.get("error")
        message = error.get("message") if isinstance(error, dict) else None
        if not isinstance(message, str) or message_contains not in message:
            raise ContractError(
                f"{name}: expected error message containing {message_contains!r}, got {message!r}"
            )
    return payload


def assert_identical_directories(left: Path, right: Path) -> None:
    left_names = sorted(path.name for path in left.iterdir())
    right_names = sorted(path.name for path in right.iterdir())
    if left_names != right_names:
        raise ContractError(
            f"deterministic bundle file sets differ: left={left_names} right={right_names}"
        )
    for name in left_names:
        if (left / name).read_bytes() != (right / name).read_bytes():
            raise ContractError(f"deterministic bundle bytes differ for {name}")


def rewrite_integrity_metadata(bundle_dir: Path) -> None:
    manifest_path = bundle_dir / "manifest.json"
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ContractError("manifest must be an object")
    payload_files = manifest.get("payload_files")
    if not isinstance(payload_files, list):
        raise ContractError("manifest payload_files must be an array")

    entries: list[dict[str, Any]] = []
    for name in sorted(payload_files):
        path = bundle_dir / name
        entries.append(
            {
                "name": name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest["files"] = entries
    manifest["aggregate_sha256"] = aggregate_entries(entries)
    write_json(manifest_path, manifest)

    checksum_names = sorted([*payload_files, "manifest.json"])
    (bundle_dir / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(bundle_dir / name)}  {name}\n" for name in checksum_names),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    try:
        output_schema = load_json(OUTPUT_SCHEMA)
        if not isinstance(output_schema, dict):
            raise ContractError("verification bundle output schema must be an object")
        Draft202012Validator.check_schema(output_schema)
        validator = Draft202012Validator(output_schema)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            session = root / "input-session.json"
            snapshot = root / "input-snapshot.json"
            strict_profile = root / "strict-profile.json"
            no_snapshot_profile = root / "no-snapshot-profile.json"
            write_json(session, session_document())
            write_json(snapshot, snapshot_document())
            write_json(strict_profile, profile_document(True))
            write_json(no_snapshot_profile, profile_document(False))

            bundle_a = root / "bundle-a"
            bundle_b = root / "bundle-b"
            create_a = run_json(
                validator,
                "create-strict-a",
                [
                    "create",
                    "--profile",
                    str(strict_profile),
                    "--transcript",
                    str(session),
                    "--snapshot",
                    str(snapshot),
                    "--out-dir",
                    str(bundle_a),
                ],
                0,
            )
            create_b = run_json(
                validator,
                "create-strict-b",
                [
                    "create",
                    "--profile",
                    str(strict_profile),
                    "--transcript",
                    str(session),
                    "--snapshot",
                    str(snapshot),
                    "--out-dir",
                    str(bundle_b),
                ],
                0,
            )
            if create_a.get("aggregate_sha256") != create_b.get("aggregate_sha256"):
                raise ContractError("repeated generation produced different aggregate SHA-256")
            assert_identical_directories(bundle_a, bundle_b)

            verify_success = run_json(
                validator,
                "verify-strict",
                ["verify", str(bundle_a)],
                0,
            )
            if verify_success.get("verified") is not True:
                raise ContractError("verify-strict: expected verified=true")
            if verify_success.get("terminal_referenced_evidence_type_counts") != {"read-back": 1}:
                raise ContractError("verify-strict: expected terminal-referenced read-back evidence")

            bundle_without_snapshot = root / "bundle-without-snapshot"
            no_snapshot = run_json(
                validator,
                "create-without-snapshot",
                [
                    "create",
                    "--profile",
                    str(no_snapshot_profile),
                    "--transcript",
                    str(session),
                    "--out-dir",
                    str(bundle_without_snapshot),
                ],
                0,
            )
            if no_snapshot.get("snapshot_included") is not False:
                raise ContractError("create-without-snapshot: snapshot_included must be false")
            run_json(
                validator,
                "verify-without-snapshot",
                ["verify", str(bundle_without_snapshot)],
                0,
            )

            run_json(
                validator,
                "snapshot-required-create-failure",
                [
                    "create",
                    "--profile",
                    str(strict_profile),
                    "--transcript",
                    str(session),
                    "--out-dir",
                    str(root / "missing-required-snapshot-bundle"),
                ],
                2,
                "context-snapshot-required",
            )

            tampered_payload = root / "tampered-payload"
            shutil.copytree(bundle_a, tampered_payload)
            with (tampered_payload / "session.json").open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n")
            run_json(
                validator,
                "tampered-payload",
                ["verify", str(tampered_payload)],
                2,
                "bundle payload size mismatch",
            )

            tampered_manifest = root / "tampered-manifest"
            shutil.copytree(bundle_a, tampered_manifest)
            manifest = load_json(tampered_manifest / "manifest.json")
            manifest["aggregate_sha256"] = "0" * 64
            write_json(tampered_manifest / "manifest.json", manifest)
            run_json(
                validator,
                "tampered-manifest",
                ["verify", str(tampered_manifest)],
                2,
                "aggregate SHA-256 mismatch",
            )

            tampered_checksums = root / "tampered-checksums"
            shutil.copytree(bundle_a, tampered_checksums)
            checksum_lines = (tampered_checksums / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
            checksum_lines[0] = "0" * 64 + checksum_lines[0][64:]
            (tampered_checksums / "SHA256SUMS").write_text(
                "\n".join(checksum_lines) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            run_json(
                validator,
                "tampered-checksums",
                ["verify", str(tampered_checksums)],
                2,
                "SHA256SUMS mismatch",
            )

            replay_tamper = root / "replay-tamper"
            shutil.copytree(bundle_a, replay_tamper)
            result = load_json(replay_tamper / "verification-result.json")
            result["terminal_status"] = "failed"
            write_json(replay_tamper / "verification-result.json", result)
            rewrite_integrity_metadata(replay_tamper)
            run_json(
                validator,
                "replay-tamper",
                ["verify", str(replay_tamper)],
                2,
                "does not match recomputed portable verification result",
            )

            missing_file = root / "missing-file"
            shutil.copytree(bundle_a, missing_file)
            (missing_file / "snapshot.json").unlink()
            run_json(
                validator,
                "missing-file",
                ["verify", str(missing_file)],
                2,
                "bundle file set mismatch",
            )

            extra_file = root / "extra-file"
            shutil.copytree(bundle_a, extra_file)
            (extra_file / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
            run_json(
                validator,
                "extra-file",
                ["verify", str(extra_file)],
                2,
                "bundle file set mismatch",
            )

        print(
            "verification bundle contract passed: deterministic generation, replay verification, "
            "optional/required snapshot behavior, and 6 tamper/file-set rejection paths"
        )
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"verification bundle contract failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
