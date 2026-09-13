#!/usr/bin/env python3
"""Validate the machine-readable Glomancy Protocol security invariant catalog."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "security" / "v1" / "invariants.json"
VECTORS_MANIFEST = ROOT / "vectors" / "v1" / "manifest.json"
ID_RE = re.compile(r"^GLM-SEC-[0-9]{3}$")
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
ALLOWED_CATEGORIES = {"versioning", "capability", "approval", "evidence", "lifecycle"}
ALLOWED_FAILURE_MODES = {"reject", "withhold-authorization"}


class ValidationError(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def require_nonempty_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{context}.{key} must be a non-empty string")
    return value


def vector_index(manifest: dict[str, Any]) -> tuple[str, dict[str, dict[str, dict[str, Any]]]]:
    wire = require_nonempty_string(manifest, "wire_protocol_version", "vectors manifest")
    if SEMVER_RE.fullmatch(wire) is None:
        raise ValidationError(f"vectors manifest wire_protocol_version is invalid: {wire!r}")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValidationError("vectors manifest files must be a non-empty array")

    areas: dict[str, dict[str, dict[str, Any]]] = {}
    seen_files: set[str] = set()
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            raise ValidationError(f"vectors manifest entry {index} must be an object")
        area = require_nonempty_string(entry, "area", f"vectors manifest entry {index}")
        filename = require_nonempty_string(entry, "file", f"vectors manifest entry {index}")
        if area in areas:
            raise ValidationError(f"duplicate vector area: {area}")
        if filename in seen_files:
            raise ValidationError(f"duplicate vector filename: {filename}")
        seen_files.add(filename)

        vector_path = ROOT / "vectors" / "v1" / filename
        vector_data = load_object(vector_path)
        cases = vector_data.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValidationError(f"vector area {area!r} has no cases")

        case_map: dict[str, dict[str, Any]] = {}
        for case_index, case in enumerate(cases):
            if not isinstance(case, dict):
                raise ValidationError(f"{area} case {case_index} must be an object")
            case_id = require_nonempty_string(case, "id", f"{area} case {case_index}")
            if case_id in case_map:
                raise ValidationError(f"duplicate vector case ID in {area}: {case_id}")
            case_map[case_id] = case
        areas[area] = case_map
    return wire, areas


def is_fail_closed_case(case: dict[str, Any]) -> bool:
    expected = case.get("expected")
    if not isinstance(expected, dict):
        return False
    return expected.get("accepted") is False or expected.get("authorized") is False


def validate() -> tuple[int, int]:
    catalog = load_object(CATALOG)
    manifest = load_object(VECTORS_MANIFEST)
    vector_wire, areas = vector_index(manifest)

    catalog_version = require_nonempty_string(catalog, "catalog_version", "catalog")
    if SEMVER_RE.fullmatch(catalog_version) is None:
        raise ValidationError(f"invalid catalog_version: {catalog_version!r}")

    catalog_wire = require_nonempty_string(catalog, "wire_protocol_version", "catalog")
    if SEMVER_RE.fullmatch(catalog_wire) is None:
        raise ValidationError(f"invalid catalog wire_protocol_version: {catalog_wire!r}")
    if catalog_wire != vector_wire:
        raise ValidationError(
            f"wire protocol drift: security catalog={catalog_wire}, vectors={vector_wire}"
        )

    description = require_nonempty_string(catalog, "description", "catalog")
    if "formal verification" not in description.lower():
        raise ValidationError(
            "catalog description must explicitly distinguish regression evidence from formal verification"
        )

    invariants = catalog.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        raise ValidationError("invariants must be a non-empty array")

    seen_ids: set[str] = set()
    total_evidence = 0
    for index, invariant in enumerate(invariants):
        if not isinstance(invariant, dict):
            raise ValidationError(f"invariant {index} must be an object")
        context = f"invariant {index}"
        invariant_id = require_nonempty_string(invariant, "id", context)
        if ID_RE.fullmatch(invariant_id) is None:
            raise ValidationError(f"invalid invariant ID: {invariant_id!r}")
        if invariant_id in seen_ids:
            raise ValidationError(f"duplicate invariant ID: {invariant_id}")
        seen_ids.add(invariant_id)

        category = require_nonempty_string(invariant, "category", invariant_id)
        if category not in ALLOWED_CATEGORIES:
            raise ValidationError(f"{invariant_id}: unsupported category {category!r}")
        if invariant.get("status") != "enforced":
            raise ValidationError(f"{invariant_id}: status must be 'enforced'")
        require_nonempty_string(invariant, "statement", invariant_id)
        failure_mode = require_nonempty_string(invariant, "failure_mode", invariant_id)
        if failure_mode not in ALLOWED_FAILURE_MODES:
            raise ValidationError(
                f"{invariant_id}: unsupported failure_mode {failure_mode!r}"
            )

        evidence = invariant.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValidationError(f"{invariant_id}: evidence must be a non-empty array")

        seen_refs: set[tuple[str, str]] = set()
        has_fail_closed = False
        for evidence_index, reference in enumerate(evidence):
            if not isinstance(reference, dict):
                raise ValidationError(
                    f"{invariant_id}: evidence entry {evidence_index} must be an object"
                )
            area = require_nonempty_string(
                reference, "area", f"{invariant_id} evidence {evidence_index}"
            )
            case_id = require_nonempty_string(
                reference, "case_id", f"{invariant_id} evidence {evidence_index}"
            )
            key = (area, case_id)
            if key in seen_refs:
                raise ValidationError(
                    f"{invariant_id}: duplicate evidence reference {area}/{case_id}"
                )
            seen_refs.add(key)

            area_cases = areas.get(area)
            if area_cases is None:
                raise ValidationError(f"{invariant_id}: unknown vector area {area!r}")
            case = area_cases.get(case_id)
            if case is None:
                raise ValidationError(
                    f"{invariant_id}: unknown vector case {area}/{case_id}"
                )
            if is_fail_closed_case(case):
                has_fail_closed = True
            total_evidence += 1

        if not has_fail_closed:
            raise ValidationError(
                f"{invariant_id}: at least one evidence case must exercise fail-closed behavior"
            )

    ordered_ids = sorted(seen_ids)
    if ordered_ids != [f"GLM-SEC-{number:03d}" for number in range(1, len(ordered_ids) + 1)]:
        raise ValidationError(
            "security invariant IDs must form a contiguous sequence starting at GLM-SEC-001"
        )

    return len(invariants), total_evidence


def main() -> int:
    try:
        invariant_count, evidence_count = validate()
    except ValidationError as exc:
        print(f"security invariant validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "security invariant validation passed: "
        f"{invariant_count} invariants, {evidence_count} vector evidence references"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
