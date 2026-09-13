#!/usr/bin/env python3
"""Fail CI when tracked files cross obvious public/private repository boundaries."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

FORBIDDEN_SUFFIXES = {".pem", ".p12", ".pfx"}

PATTERNS = [
    (
        "API token-like value",
        re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "GitHub token-like value",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "AWS access-key-like value",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "PEM private key material",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "developer-specific Windows home path",
        re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\r\n]+\\\\"),
    ),
    (
        "developer-specific Unix home path",
        re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    ),
    (
        "direct reference to the private commercial repository",
        re.compile(r"github\.com/charman-07/Glomancy(?:\.git)?(?:\b|/)"),
    ),
]


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if raw:
            paths.append(ROOT / raw.decode("utf-8", errors="strict"))
    return paths


def path_violation(path: Path) -> str | None:
    name = path.name.lower()
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "tracked environment file"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return f"tracked credential/key container ({path.suffix})"
    if path.suffix.lower() == ".key" and "public" not in name:
        return "tracked private-key-like file"
    return None


def main() -> int:
    violations: list[tuple[str, str]] = []

    try:
        files = tracked_files()
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        print(f"public-boundary check could not list tracked files: {exc}", file=sys.stderr)
        return 2

    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        reason = path_violation(path)
        if reason:
            violations.append((relative, reason))

        if path.resolve() == SELF or not path.is_file():
            continue

        try:
            raw = path.read_bytes()
        except OSError as exc:
            print(f"public-boundary check could not read {relative}: {exc}", file=sys.stderr)
            return 2

        if b"\0" in raw:
            continue

        text = raw.decode("utf-8", errors="ignore")
        for label, pattern in PATTERNS:
            if pattern.search(text):
                violations.append((relative, label))

    if violations:
        print("public-boundary check failed; review these tracked files:", file=sys.stderr)
        for relative, reason in sorted(set(violations)):
            print(f"- {relative}: {reason}", file=sys.stderr)
        print("No matched secret or sensitive value is printed by this check.", file=sys.stderr)
        return 1

    print(f"public-boundary check passed for {len(files)} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
