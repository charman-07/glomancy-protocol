#!/usr/bin/env python3
"""Generate a deterministic release-readiness evidence bundle.

The bundle is audit evidence only. It is not a signature, provenance attestation,
certification, or release authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from release_readiness_report import ReadinessError, collect

ROOT = Path(__file__).resolve().parents[1]
FINGERPRINT = ROOT / "contracts" / "v1" / "fingerprint.json"
SUPPORT_POLICY = ROOT / "support" / "v1" / "policy.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_GATE_RESULTS = {
    "success",
    "failure",
    "cancelled",
    "skipped",
    "timed_out",
    "action_required",
    "neutral",
    "unknown",
}
PAYLOAD_FILES = (
    "evidence.json",
    "public-contract-fingerprint.json",
    "release-support-policy.json",
)


class EvidenceError(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def require_nonempty_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"{key} must be a non-empty string")
    return value


def normalize_gate(label: str, value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_GATE_RESULTS:
        raise EvidenceError(f"unsupported {label} gate result: {value!r}")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_output_dir(out_dir: Path) -> None:
    if out_dir.exists():
        if not out_dir.is_dir():
            raise EvidenceError(f"output path exists and is not a directory: {out_dir}")
        unexpected = sorted(path.name for path in out_dir.iterdir())
        if unexpected:
            raise EvidenceError(
                f"output directory must be empty before generation: {out_dir} contains {unexpected}"
            )
    else:
        out_dir.mkdir(parents=True, exist_ok=False)


def build_evidence(
    *,
    audited_ref: str,
    audited_sha: str,
    quality_result: str,
    contract_result: str,
    portability_result: str,
    expected_version: str | None,
) -> dict[str, Any]:
    if not audited_ref:
        raise EvidenceError("audited ref must be non-empty")
    audited_sha = audited_sha.lower()
    if SHA_RE.fullmatch(audited_sha) is None:
        raise EvidenceError("audited SHA must be a 40-character lowercase hexadecimal Git SHA")

    quality = normalize_gate("Rust quality", quality_result)
    contract = normalize_gate("repository contract", contract_result)
    portability = normalize_gate("portability", portability_result)

    try:
        metadata = collect(expected_version)
    except ReadinessError as exc:
        raise EvidenceError(str(exc)) from exc

    fingerprint = load_object(FINGERPRINT)
    fingerprint_version = require_nonempty_string(fingerprint, "fingerprint_format_version")
    aggregate = require_nonempty_string(fingerprint, "aggregate_sha256")
    if SHA256_RE.fullmatch(aggregate) is None:
        raise EvidenceError("public contract fingerprint aggregate_sha256 is malformed")

    support = load_object(SUPPORT_POLICY)
    support_policy_version = require_nonempty_string(support, "policy_version")

    release_lines = metadata.get("supported_release_lines")
    if not isinstance(release_lines, list) or not release_lines:
        raise EvidenceError("release metadata has no supported release lines")

    gates = {
        "rust_quality": quality,
        "repository_contract": contract,
        "portability": portability,
    }
    audit_status = "passed" if all(result == "success" for result in gates.values()) else "failed"

    package = metadata.get("package")
    if not isinstance(package, dict):
        raise EvidenceError("release metadata package is missing")

    return {
        "evidence_format_version": "1.0.0",
        "project": "glomancy-protocol",
        "audited_ref": audited_ref,
        "audited_sha": audited_sha,
        "audit_status": audit_status,
        "gates": gates,
        "package": {
            "name": package.get("name"),
            "version": package.get("version"),
            "rust_version": package.get("rust_version"),
        },
        "wire_protocol_version": metadata.get("wire_protocol_version"),
        "public_contract_fingerprint": {
            "format_version": fingerprint_version,
            "aggregate_sha256": aggregate,
            "source_file": "public-contract-fingerprint.json",
        },
        "support": {
            "policy_version": support_policy_version,
            "release_lines": release_lines,
            "source_file": "release-support-policy.json",
        },
        "bundle": {
            "checksum_file": "SHA256SUMS",
            "checksum_algorithm": "sha256",
            "payload_files": list(PAYLOAD_FILES),
        },
        "claims": {
            "signed": False,
            "provenance": False,
            "attestation": False,
            "certification": False,
            "release_authorization": False,
        },
    }


def generate_bundle(
    out_dir: Path,
    *,
    audited_ref: str,
    audited_sha: str,
    quality_result: str,
    contract_result: str,
    portability_result: str,
    expected_version: str | None,
) -> dict[str, Any]:
    ensure_output_dir(out_dir)
    evidence = build_evidence(
        audited_ref=audited_ref,
        audited_sha=audited_sha,
        quality_result=quality_result,
        contract_result=contract_result,
        portability_result=portability_result,
        expected_version=expected_version,
    )

    evidence_path = out_dir / "evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    shutil.copyfile(FINGERPRINT, out_dir / "public-contract-fingerprint.json")
    shutil.copyfile(SUPPORT_POLICY, out_dir / "release-support-policy.json")

    checksum_lines = []
    for name in sorted(PAYLOAD_FILES):
        checksum_lines.append(f"{sha256_file(out_dir / name)}  {name}\n")
    (out_dir / "SHA256SUMS").write_text("".join(checksum_lines), encoding="utf-8", newline="\n")
    return evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--ref", required=True, dest="audited_ref")
    parser.add_argument("--sha", required=True, dest="audited_sha")
    parser.add_argument("--quality-result", required=True)
    parser.add_argument("--contract-result", required=True)
    parser.add_argument("--portability-result", required=True)
    parser.add_argument("--expected-version")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        evidence = generate_bundle(
            args.out_dir,
            audited_ref=args.audited_ref,
            audited_sha=args.audited_sha,
            quality_result=args.quality_result,
            contract_result=args.contract_result,
            portability_result=args.portability_result,
            expected_version=args.expected_version,
        )
    except EvidenceError as exc:
        print(f"release evidence generation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "release evidence bundle generated: "
        f"status={evidence['audit_status']} "
        f"sha={evidence['audited_sha']} "
        f"fingerprint={evidence['public_contract_fingerprint']['aggregate_sha256']} "
        f"path={args.out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
