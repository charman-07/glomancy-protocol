#!/usr/bin/env python3
"""Build a deterministic standalone Glomancy Protocol contract bundle.

The bundle contains only public, language-neutral contract assets. It does not
contain private Glomancy runtime/editor/provider code, credentials, signing
material, or a claim of authenticity/provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_FORMAT_VERSION = "1.0.0"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

PUBLIC_GLOBS = (
    "LICENSE",
    "schemas/v1/*.json",
    "registry/v1/*.json",
    "compatibility/v1/*.json",
    "compatibility/snapshots/**/*.json",
    "capabilities/v1/*.json",
    "vectors/v1/*.json",
    "errors/v1/*.json",
    "security/v1/*.json",
    "limits/v1/*.json",
    "support/v1/*.json",
    "contracts/v1/fingerprint.json",
    "conformance/v1/*.json",
    "examples/v1/**/*.json",
)

REQUIRED_FILES = (
    "LICENSE",
    "registry/v1/manifest.json",
    "compatibility/v1/compatibility-matrix.json",
    "compatibility/snapshots/manifest.json",
    "capabilities/v1/profile.json",
    "vectors/v1/manifest.json",
    "errors/v1/catalog.json",
    "security/v1/invariants.json",
    "limits/v1/policy.json",
    "support/v1/policy.json",
    "contracts/v1/fingerprint.json",
    "conformance/v1/cli-output.schema.json",
    "examples/v1/manifest.json",
)

ALLOWED_PREFIXES = (
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
    "examples/v1/",
)


class BundleError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BundleError(f"cannot read {path}: {exc}") from exc


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BundleError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise BundleError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def package_version() -> str:
    text = read_text(ROOT / "Cargo.toml")
    package = re.search(r"(?ms)^\[package\]\s*(.*?)(?=^\[|\Z)", text)
    if package is None:
        raise BundleError("Cargo.toml is missing [package]")
    match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"\s*$', package.group(1))
    if match is None:
        raise BundleError("Cargo.toml [package] is missing version")
    return match.group(1)


def wire_protocol_version() -> str:
    text = read_text(ROOT / "src" / "lib.rs")
    match = re.search(
        r"PROTOCOL_VERSION\s*:\s*ProtocolVersion\s*=\s*ProtocolVersion::new\(\s*"
        r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
        text,
    )
    if match is None:
        raise BundleError("could not parse PROTOCOL_VERSION from src/lib.rs")
    return ".".join(match.groups())


def public_contract_fingerprint() -> str:
    manifest = load_json(ROOT / "contracts" / "v1" / "fingerprint.json")
    value = manifest.get("aggregate_sha256")
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        raise BundleError("contracts/v1/fingerprint.json has invalid aggregate_sha256")
    return value


def is_allowed(relative: str) -> bool:
    if relative == "LICENSE":
        return True
    return any(relative.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def validate_relative_path(relative: str) -> None:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise BundleError(f"unsafe bundle path: {relative!r}")
    normalized = path.as_posix()
    if normalized != relative:
        raise BundleError(f"non-canonical bundle path: {relative!r}")
    if not is_allowed(relative):
        raise BundleError(f"path is outside the public bundle allowlist: {relative}")


def collect_payload_paths() -> list[str]:
    found: set[str] = set()
    for pattern in PUBLIC_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                relative = path.relative_to(ROOT).as_posix()
                validate_relative_path(relative)
                if relative in found:
                    raise BundleError(f"duplicate bundle path selected: {relative}")
                found.add(relative)

    for required in REQUIRED_FILES:
        if required not in found:
            raise BundleError(f"required public contract file is missing from bundle: {required}")

    if not any(path.startswith("schemas/v1/") for path in found):
        raise BundleError("bundle contains no public schemas")
    if not any(path.startswith("examples/v1/valid/") for path in found):
        raise BundleError("bundle contains no valid conformance fixtures")
    if not any(path.startswith("examples/v1/invalid/") for path in found):
        raise BundleError("bundle contains no invalid conformance fixtures")

    return sorted(found)


def manifest_for(paths: list[str]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        entries.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            }
        )

    return {
        "bundle_format_version": BUNDLE_FORMAT_VERSION,
        "package_version": package_version(),
        "wire_protocol_version": wire_protocol_version(),
        "public_contract_fingerprint": public_contract_fingerprint(),
        "file_count": len(entries),
        "files": entries,
        "assurance_boundary": (
            "Integrity metadata for public contract assets only; not a signature, provenance "
            "attestation, certification, authorization decision, or production-adoption claim."
        ),
    }


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def checksum_lines(payloads: dict[str, bytes]) -> bytes:
    lines = [f"{sha256_bytes(data)}  {path}\n" for path, data in sorted(payloads.items())]
    return "".join(lines).encode("utf-8")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (0o100644 & 0xFFFF) << 16
    return info


def ensure_output_dir(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise BundleError(f"output path exists and is not a directory: {path}")
        if any(path.iterdir()):
            raise BundleError(f"output directory must be empty: {path}")
    else:
        path.mkdir(parents=True, exist_ok=False)


def build_bundle(out_dir: Path, archive_path: Path) -> dict[str, Any]:
    paths = collect_payload_paths()
    manifest = manifest_for(paths)

    payloads: dict[str, bytes] = {}
    for relative in paths:
        payloads[relative] = (ROOT / relative).read_bytes()

    manifest_bytes = canonical_json_bytes(manifest)
    payloads_with_manifest = dict(payloads)
    payloads_with_manifest["BUNDLE_MANIFEST.json"] = manifest_bytes
    sums_bytes = checksum_lines(payloads_with_manifest)

    ensure_output_dir(out_dir)
    for relative, data in sorted(payloads.items()):
        destination = out_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (out_dir / "BUNDLE_MANIFEST.json").write_bytes(manifest_bytes)
    (out_dir / "SHA256SUMS").write_bytes(sums_bytes)

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative, data in sorted(payloads.items()):
            archive.writestr(zip_info(relative), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        archive.writestr(
            zip_info("BUNDLE_MANIFEST.json"),
            manifest_bytes,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
        archive.writestr(
            zip_info("SHA256SUMS"),
            sums_bytes,
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )

    result = dict(manifest)
    result["archive_path"] = str(archive_path)
    result["archive_sha256"] = sha256_file(archive_path)
    result["archive_bytes"] = archive_path.stat().st_size
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True, help="empty output directory")
    parser.add_argument("--archive", type=Path, required=True, help="output ZIP path")
    parser.add_argument("--json", action="store_true", help="print build metadata as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_bundle(args.out_dir, args.archive)
    except (BundleError, OSError) as exc:
        print(f"contract bundle build failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            "contract bundle built: "
            f"files={result['file_count']} "
            f"wire={result['wire_protocol_version']} "
            f"fingerprint={result['public_contract_fingerprint']} "
            f"zip_sha256={result['archive_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
