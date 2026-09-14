#!/usr/bin/env python3
"""Runnable, dependency-free public Glomancy Protocol flow demo.

This demo intentionally uses only the public registry, language-neutral vectors,
and the independent Python consumer decisions. It does not import private
Glomancy runtime/editor/provider code and it does not execute editor mutations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from reference_consumer import (
    REGISTRY,
    VECTORS,
    evaluate_approval,
    load_json,
    negotiate_capabilities,
    select_advertised_version,
    task_capability_gate,
)

DEMO_OUTPUT_VERSION = "1.0.0"


class DemoError(RuntimeError):
    pass


def case_by_id(filename: str, case_id: str) -> dict[str, Any]:
    data = load_json(VECTORS / filename)
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise DemoError(f"invalid vector file: {filename}")
    for case in data["cases"]:
        if isinstance(case, dict) and case.get("id") == case_id:
            return case
    raise DemoError(f"missing vector case: {filename}:{case_id}")


def evaluate_case(
    filename: str,
    case_id: str,
    evaluator: Callable[[dict[str, Any]], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    case = case_by_id(filename, case_id)
    inputs = case.get("input")
    expected = case.get("expected")
    if not isinstance(inputs, dict) or not isinstance(expected, dict):
        raise DemoError(f"malformed vector case: {filename}:{case_id}")
    actual = evaluator(inputs)
    if actual != expected:
        raise DemoError(
            f"vector disagreement for {filename}:{case_id}: expected {expected!r}, got {actual!r}"
        )
    return inputs, actual


def evidence_schema() -> dict[str, Any]:
    registry = load_json(REGISTRY)
    schemas = registry.get("message_schemas") if isinstance(registry, dict) else None
    if not isinstance(schemas, list):
        raise DemoError("registry has no message_schemas")
    for schema in schemas:
        if isinstance(schema, dict) and schema.get("message_kind") == "evidence.record":
            return schema
    raise DemoError("registry has no evidence.record schema")


def run_demo() -> dict[str, Any]:
    version_input, version_result = evaluate_case(
        "version-negotiation.json",
        "single-shared-version",
        lambda inputs: select_advertised_version(
            [str(value) for value in inputs["local_supported"]],
            [str(value) for value in inputs["remote_supported"]],
        ),
    )

    capability_input, capability_result = evaluate_case(
        "capabilities.json",
        "required-and-optional-selected",
        lambda inputs: negotiate_capabilities(inputs["requested"], inputs["available"]),
    )

    task_input, task_result = evaluate_case(
        "task-capability-gate.json",
        "multiple-selected-capabilities-accepted",
        lambda inputs: task_capability_gate(
            [str(value) for value in inputs["requested_names"]], inputs["selected"]
        ),
    )

    approval_input, approval_result = evaluate_case(
        "approval-flow.json",
        "approve-matching-request",
        lambda inputs: evaluate_approval(inputs["request"], inputs["decision"]),
    )

    evidence = evidence_schema()

    return {
        "demo_output_version": DEMO_OUTPUT_VERSION,
        "ok": True,
        "steps": [
            {
                "step": "advertised-version-selection",
                "source": "vectors/v1/version-negotiation.json#single-shared-version",
                "input": version_input,
                "result": version_result,
            },
            {
                "step": "capability-negotiation",
                "source": "vectors/v1/capabilities.json#required-and-optional-selected",
                "input": capability_input,
                "result": capability_result,
            },
            {
                "step": "task-capability-gate",
                "source": "vectors/v1/task-capability-gate.json#multiple-selected-capabilities-accepted",
                "input": task_input,
                "result": task_result,
            },
            {
                "step": "approval-correlation",
                "source": "vectors/v1/approval-flow.json#approve-matching-request",
                "input": approval_input,
                "result": approval_result,
            },
            {
                "step": "evidence-contract-resolution",
                "source": "registry/v1/manifest.json",
                "result": {
                    "message_kind": evidence["message_kind"],
                    "schema_id": evidence["schema_id"],
                    "schema_version": evidence["version"],
                    "sha256": evidence["sha256"],
                },
            },
        ],
        "boundary": (
            "The public protocol gates are satisfied for this deterministic demo. "
            "Authentication, local policy, editor authorization, execution, sandboxing, "
            "and verification of a real editor change remain integration responsibilities."
        ),
    }


def print_human(result: dict[str, Any]) -> None:
    steps = result["steps"]
    selected_version = steps[0]["result"]["selected_version"]
    selected_caps = ", ".join(
        f"{entry['name']}@{entry['version']}" for entry in steps[1]["result"]["selected"]
    )
    task_accepted = steps[2]["result"]["accepted"]
    approval = steps[3]["result"]
    evidence = steps[4]["result"]

    print("Glomancy Protocol — runnable public flow")
    print(f"1. handshake       PASS  selected wire version: {selected_version}")
    print(f"2. capabilities    PASS  selected: {selected_caps}")
    print(f"3. task gate       PASS  accepted: {str(task_accepted).lower()}")
    print(
        "4. approval        PASS  "
        f"accepted={str(approval['accepted']).lower()} "
        f"authorized={str(approval['authorized']).lower()}"
    )
    print(
        "5. evidence        PASS  "
        f"{evidence['message_kind']} -> {evidence['schema_id']}"
    )
    print()
    print("Boundary: protocol validation/capability selection is not editor authorization.")
    print("A real integration must still enforce authentication, local policy, execution, and verification.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit stable machine-readable demo output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_demo()
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_human(result)
        return 0
    except (DemoError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"public protocol demo failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
