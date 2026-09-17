#!/usr/bin/env python3
"""Evaluate a portable task-verification profile against a public session."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import glomancy_conformance as conformance_cli
import glomancy_context_snapshot as snapshot_cli
import session_transcript_core as session_core
from validate_fixtures import ConformanceError, ROOT, build_store, load_json, validator_for

PROFILE_SCHEMA = ROOT / "verification" / "v1" / "profile.schema.json"
EXIT_OK = 0
EXIT_VERIFICATION_FAILED = 2
EXIT_CONFIGURATION_ERROR = 3
OUTPUT_VERSION = "1.0.0"


class VerificationError(RuntimeError):
    """Raised when verification input or configuration cannot be evaluated."""


def emit_json(ok: bool, exit_code: int, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "output_version": OUTPUT_VERSION,
        "command": "verify-task",
        "ok": ok,
        "exit_code": exit_code,
    }
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def emit_configuration_error(json_output: bool, message: str) -> int:
    if json_output:
        emit_json(
            False,
            EXIT_CONFIGURATION_ERROR,
            error={"type": "configuration", "message": message},
        )
    else:
        print(f"configuration error: {message}", file=sys.stderr)
    return EXIT_CONFIGURATION_ERROR


def profile_validator() -> Any:
    return validator_for(PROFILE_SCHEMA, build_store())


def terminal_outcome_requirements(
    profile: dict[str, Any],
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    policy = profile.get("terminal_outcome_policy")
    if not isinstance(policy, dict):
        return [], {}, []

    allowed_statuses = policy.get("allowed_statuses", [])
    if not isinstance(allowed_statuses, list):
        raise VerificationError("terminal outcome allowed_statuses must be an array")

    raw_by_status = policy.get("required_evidence_types_by_status", {})
    if not isinstance(raw_by_status, dict):
        raise VerificationError("terminal outcome evidence requirements must be an object")
    by_status: dict[str, list[str]] = {}
    for status in sorted(raw_by_status):
        values = raw_by_status[status]
        if not isinstance(status, str) or not isinstance(values, list):
            raise VerificationError("terminal outcome evidence requirements are malformed")
        by_status[status] = sorted(str(value) for value in values)

    rollback_statuses = policy.get("require_rollback_attempted_for_statuses", [])
    if not isinstance(rollback_statuses, list):
        raise VerificationError("rollback-attempt status requirements must be an array")

    return sorted(str(value) for value in allowed_statuses), by_status, sorted(
        str(value) for value in rollback_statuses
    )


def evidence_sequence_requirement(profile: dict[str, Any]) -> list[str]:
    policy = profile.get("evidence_sequence")
    if not isinstance(policy, dict):
        return []
    sequence = policy.get("required_terminal_evidence_sequence", [])
    if not isinstance(sequence, list):
        raise VerificationError("required terminal evidence sequence must be an array")
    return [str(value) for value in sequence]


def ordered_subsequence_matches(required: list[str], observed: list[str]) -> bool:
    if not required:
        return True
    required_index = 0
    for evidence_type in observed:
        if evidence_type == required[required_index]:
            required_index += 1
            if required_index == len(required):
                return True
    return False


def validate_profile_semantics(profile: dict[str, Any]) -> None:
    allowed_statuses, _by_status, _rollback_statuses = terminal_outcome_requirements(profile)
    if profile.get("require_success") is True and allowed_statuses and "succeeded" not in allowed_statuses:
        raise VerificationError(
            "require_success=true conflicts with terminal_outcome_policy.allowed_statuses excluding succeeded"
        )
    evidence_sequence_requirement(profile)


def load_profile(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VerificationError(f"profile file does not exist: {path}")
    try:
        value = load_json(path)
    except ConformanceError as exc:
        raise VerificationError(str(exc)) from exc
    if not isinstance(value, dict):
        raise VerificationError("verification profile must be a JSON object")
    errors = sorted(profile_validator().iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise VerificationError(
            f"profile schema validation failed: keyword={first.validator!r} "
            f"path={location}: {first.message}"
        )
    validate_profile_semantics(value)
    return value


def evidence_records(messages: list[Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for message in messages:
        if not isinstance(message, dict) or message.get("kind") != "evidence.record":
            continue
        payload = message.get("payload")
        if not isinstance(payload, dict):
            continue
        evidence_id = payload.get("evidence_id")
        if isinstance(evidence_id, str):
            records[evidence_id] = payload
    return records


def evidence_type_counts(records: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for payload in records.values():
        evidence_type = payload.get("evidence_type")
        if isinstance(evidence_type, str):
            counts[evidence_type] = counts.get(evidence_type, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def evidence_coverage_requirements(
    profile: dict[str, Any],
) -> tuple[int, dict[str, int], int | None]:
    coverage = profile.get("evidence_coverage")
    if not isinstance(coverage, dict):
        return 0, {}, None

    minimum_count = coverage.get("minimum_terminal_referenced_evidence_count", 0)
    if not isinstance(minimum_count, int) or isinstance(minimum_count, bool):
        raise VerificationError("minimum terminal-referenced evidence count must be an integer")

    raw_type_counts = coverage.get("minimum_terminal_referenced_evidence_type_counts", {})
    if not isinstance(raw_type_counts, dict):
        raise VerificationError("minimum terminal-referenced evidence type counts must be an object")
    type_counts: dict[str, int] = {}
    for evidence_type in sorted(raw_type_counts):
        count = raw_type_counts[evidence_type]
        if not isinstance(evidence_type, str) or not isinstance(count, int) or isinstance(count, bool):
            raise VerificationError("evidence coverage type-count requirements are malformed")
        type_counts[evidence_type] = count

    maximum_unreferenced = coverage.get("maximum_unreferenced_evidence_count")
    if maximum_unreferenced is not None and (
        not isinstance(maximum_unreferenced, int) or isinstance(maximum_unreferenced, bool)
    ):
        raise VerificationError("maximum unreferenced evidence count must be an integer")

    return minimum_count, type_counts, maximum_unreferenced


def terminal_message(messages: list[Any]) -> tuple[dict[str, Any] | None, int | None]:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, dict) and message.get("kind") in {"task.result", "task.error"}:
            return message, index
    return None, None


def terminal_referenced_evidence(
    terminal: dict[str, Any],
    records: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    payload = terminal.get("payload")
    if not isinstance(payload, dict):
        return {}, []
    refs = payload.get("evidence_ids")
    if not isinstance(refs, list):
        return {}, []

    referenced: dict[str, dict[str, Any]] = {}
    unknown: list[str] = []
    for evidence_id in refs:
        if not isinstance(evidence_id, str):
            continue
        record = records.get(evidence_id)
        if record is None:
            unknown.append(evidence_id)
        else:
            referenced[evidence_id] = record
    return referenced, unknown


def terminal_referenced_evidence_sequence(
    messages: list[Any], terminal: dict[str, Any] | None
) -> list[str]:
    if terminal is None:
        return []
    payload = terminal.get("payload")
    if not isinstance(payload, dict):
        return []
    refs = payload.get("evidence_ids")
    if not isinstance(refs, list):
        return []
    referenced_ids = {value for value in refs if isinstance(value, str)}
    sequence: list[str] = []
    for message in messages:
        if not isinstance(message, dict) or message.get("kind") != "evidence.record":
            continue
        evidence_payload = message.get("payload")
        if not isinstance(evidence_payload, dict):
            continue
        evidence_id = evidence_payload.get("evidence_id")
        evidence_type = evidence_payload.get("evidence_type")
        if evidence_id in referenced_ids and isinstance(evidence_type, str):
            sequence.append(evidence_type)
    return sequence


def base_result_fields(
    profile_path: Path,
    transcript_path: Path,
    snapshot_path: Path | None,
    profile: dict[str, Any],
    session_accepted: bool,
    messages: list[Any],
    terminal: dict[str, Any] | None,
    records: dict[str, dict[str, Any]],
    referenced: dict[str, dict[str, Any]],
    snapshot_match: bool | None,
) -> dict[str, Any]:
    terminal_kind: str | None = None
    terminal_status: str | None = None
    read_back_verified: bool | None = None
    rollback_attempted: bool | None = None
    if terminal is not None:
        kind = terminal.get("kind")
        payload = terminal.get("payload")
        terminal_kind = kind if isinstance(kind, str) else None
        if isinstance(payload, dict):
            status = payload.get("status")
            terminal_status = status if isinstance(status, str) else None
            flag = payload.get("read_back_verified")
            read_back_verified = flag if isinstance(flag, bool) else None
            rollback_flag = payload.get("rollback_attempted")
            rollback_attempted = rollback_flag if isinstance(rollback_flag, bool) else None

    minimum_count, minimum_type_counts, maximum_unreferenced = evidence_coverage_requirements(profile)
    allowed_statuses, by_status, rollback_statuses = terminal_outcome_requirements(profile)
    status_required_types = by_status.get(terminal_status or "", [])
    rollback_attempt_required = terminal_status in rollback_statuses if terminal_status is not None else False
    required_sequence = evidence_sequence_requirement(profile)
    observed_sequence = terminal_referenced_evidence_sequence(messages, terminal)
    sequence_matched = ordered_subsequence_matches(required_sequence, observed_sequence)
    unreferenced_count = max(len(records) - len(referenced), 0)

    return {
        "profile_path": str(profile_path),
        "transcript_path": str(transcript_path),
        "snapshot_path": str(snapshot_path) if snapshot_path is not None else None,
        "verified": False,
        "reason": None,
        "detail": None,
        "session_accepted": session_accepted,
        "terminal_kind": terminal_kind,
        "terminal_status": terminal_status,
        "read_back_verified": read_back_verified,
        "rollback_attempted": rollback_attempted,
        "snapshot_required": bool(profile["require_context_snapshot_match"]),
        "snapshot_match": snapshot_match,
        "require_success": bool(profile["require_success"]),
        "require_read_back_verified": bool(profile["require_read_back_verified"]),
        "required_evidence_types": sorted(profile["required_evidence_types"]),
        "minimum_terminal_referenced_evidence_count": minimum_count,
        "minimum_terminal_referenced_evidence_type_counts": minimum_type_counts,
        "maximum_unreferenced_evidence_count": maximum_unreferenced,
        "allowed_terminal_statuses": allowed_statuses,
        "terminal_required_evidence_types": status_required_types,
        "rollback_attempt_required": rollback_attempt_required,
        "required_terminal_evidence_sequence": required_sequence,
        "observed_terminal_evidence_sequence": observed_sequence,
        "terminal_evidence_sequence_matched": sequence_matched,
        "observed_evidence_type_counts": evidence_type_counts(records),
        "terminal_referenced_evidence_type_counts": evidence_type_counts(referenced),
        "evidence_count": len(records),
        "terminal_referenced_evidence_count": len(referenced),
        "unreferenced_evidence_count": unreferenced_count,
    }


def fail_result(fields: dict[str, Any], reason: str, detail: str | None = None) -> dict[str, Any]:
    result = dict(fields)
    result["verified"] = False
    result["reason"] = reason
    result["detail"] = detail
    return result


def verify(
    profile: dict[str, Any],
    profile_path: Path,
    transcript_path: Path,
    snapshot_path: Path | None,
) -> tuple[int, dict[str, Any]]:
    if not transcript_path.is_file():
        raise VerificationError(f"transcript file does not exist: {transcript_path}")

    messages = conformance_cli.load_session_document(transcript_path)
    session_result = session_core.validate_transcript(
        messages,
        conformance_cli.session_validators(),
    )

    records = evidence_records(messages)
    terminal, terminal_index = terminal_message(messages)
    referenced: dict[str, dict[str, Any]] = {}
    if terminal is not None:
        referenced, unknown = terminal_referenced_evidence(terminal, records)
        if unknown:
            raise VerificationError("canonical session accepted an unknown terminal evidence reference")

    fields = base_result_fields(
        profile_path,
        transcript_path,
        snapshot_path,
        profile,
        bool(session_result["accepted"]),
        messages,
        terminal,
        records,
        referenced,
        None,
    )

    if not session_result["accepted"]:
        return (
            EXIT_VERIFICATION_FAILED,
            fail_result(
                fields,
                "session-conformance-failed",
                f"session_reason={session_result['reason']} message_index={session_result['message_index']}",
            ),
        )

    if terminal is None or terminal_index is None:
        raise VerificationError("canonical session accepted without a terminal task message")

    if profile["require_context_snapshot_match"]:
        if snapshot_path is None:
            return EXIT_VERIFICATION_FAILED, fail_result(fields, "context-snapshot-required")
        try:
            snapshot_document = snapshot_cli.load_snapshot(snapshot_path)
            snapshot_errors, duplicate_index = snapshot_cli.validate_snapshot_document(snapshot_document)
        except (snapshot_cli.SnapshotError, ConformanceError, OSError, TypeError, ValueError) as exc:
            raise VerificationError(str(exc)) from exc

        if snapshot_errors:
            raise VerificationError(
                f"context snapshot schema validation failed with {len(snapshot_errors)} error(s)"
            )
        if duplicate_index is not None:
            raise VerificationError(
                f"context snapshot contains duplicate source identity at sources/{duplicate_index}"
            )

        _, snapshot_sources, _, _ = snapshot_cli.snapshot_summary(snapshot_document)
        task_refs, _task_index = snapshot_cli.task_context_refs(messages)
        matched, snapshot_reason, snapshot_detail, _matched_count = snapshot_cli.compare_context_refs(
            snapshot_sources,
            task_refs,
        )
        fields["snapshot_match"] = matched
        if not matched:
            safe_detail = snapshot_reason
            if snapshot_detail:
                safe_detail += f" {snapshot_detail}"
            return EXIT_VERIFICATION_FAILED, fail_result(
                fields, "context-snapshot-mismatch", safe_detail
            )
    elif snapshot_path is not None:
        fields["snapshot_match"] = None

    terminal_payload = terminal.get("payload")
    if not isinstance(terminal_payload, dict):
        raise VerificationError("terminal task payload is not an object")

    terminal_status = terminal_payload.get("status")
    if profile["require_success"] and terminal_status != "succeeded":
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "terminal-status-not-succeeded",
            f"terminal_status={terminal_status}",
        )

    allowed_statuses = fields["allowed_terminal_statuses"]
    if allowed_statuses and terminal_status not in allowed_statuses:
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "terminal-status-not-allowed",
            f"terminal_status={terminal_status} allowed={','.join(allowed_statuses)}",
        )

    referenced_counts = evidence_type_counts(referenced)
    missing_types = [
        evidence_type
        for evidence_type in sorted(profile["required_evidence_types"])
        if referenced_counts.get(evidence_type, 0) == 0
    ]
    if missing_types:
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "required-evidence-type-missing",
            "missing_types=" + ",".join(missing_types),
        )

    status_missing_types = [
        evidence_type
        for evidence_type in fields["terminal_required_evidence_types"]
        if referenced_counts.get(evidence_type, 0) == 0
    ]
    if status_missing_types:
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "terminal-status-evidence-type-missing",
            f"terminal_status={terminal_status} missing_types={','.join(status_missing_types)}",
        )

    if fields["rollback_attempt_required"] and terminal_payload.get("rollback_attempted") is not True:
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "rollback-attempt-not-reported",
            f"terminal_status={terminal_status}",
        )

    if fields["required_terminal_evidence_sequence"] and not fields["terminal_evidence_sequence_matched"]:
        required_rendered = ">".join(fields["required_terminal_evidence_sequence"])
        observed_rendered = ">".join(fields["observed_terminal_evidence_sequence"])
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "terminal-evidence-sequence-mismatch",
            f"required={required_rendered} observed={observed_rendered}",
        )

    minimum_count = fields["minimum_terminal_referenced_evidence_count"]
    if len(referenced) < minimum_count:
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "terminal-evidence-count-below-minimum",
            f"required_minimum={minimum_count} observed={len(referenced)}",
        )

    minimum_type_counts = fields["minimum_terminal_referenced_evidence_type_counts"]
    deficient_type_counts = [
        (evidence_type, required_count, referenced_counts.get(evidence_type, 0))
        for evidence_type, required_count in minimum_type_counts.items()
        if referenced_counts.get(evidence_type, 0) < required_count
    ]
    if deficient_type_counts:
        detail = ",".join(
            f"{evidence_type}:required={required_count}:observed={observed_count}"
            for evidence_type, required_count, observed_count in deficient_type_counts
        )
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields, "terminal-evidence-type-count-below-minimum", detail
        )

    maximum_unreferenced = fields["maximum_unreferenced_evidence_count"]
    unreferenced_count = fields["unreferenced_evidence_count"]
    if maximum_unreferenced is not None and unreferenced_count > maximum_unreferenced:
        return EXIT_VERIFICATION_FAILED, fail_result(
            fields,
            "unreferenced-evidence-count-exceeds-maximum",
            f"maximum={maximum_unreferenced} observed={unreferenced_count}",
        )

    if profile["require_read_back_verified"]:
        if terminal.get("kind") != "task.result" or terminal_payload.get("read_back_verified") is not True:
            return EXIT_VERIFICATION_FAILED, fail_result(fields, "read-back-flag-not-set")
        if referenced_counts.get("read-back", 0) == 0:
            return EXIT_VERIFICATION_FAILED, fail_result(
                fields, "read-back-evidence-not-referenced"
            )

    fields["verified"] = True
    fields["reason"] = None
    fields["detail"] = None
    return EXIT_OK, fields


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glomancy-task-verification",
        description=(
            "Evaluate portable structural verification policy across session, context snapshot, "
            "terminal result, and public evidence records."
        ),
    )
    parser.add_argument("profile", help="path to a task verification profile JSON file")
    parser.add_argument("transcript", help="path to a complete public session transcript")
    parser.add_argument(
        "--snapshot",
        help="optional path to a Context Snapshot Descriptor; required by profiles that demand it",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit one machine-readable JSON object to stdout",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    profile_path = Path(args.profile).expanduser().resolve()
    transcript_path = Path(args.transcript).expanduser().resolve()
    snapshot_path = Path(args.snapshot).expanduser().resolve() if args.snapshot else None

    try:
        profile = load_profile(profile_path)
        exit_code, result = verify(profile, profile_path, transcript_path, snapshot_path)
    except (
        VerificationError,
        ConformanceError,
        OSError,
        TypeError,
        ValueError,
        session_core.TranscriptError,
        conformance_cli.ConformanceError,
    ) as exc:
        return emit_configuration_error(args.json_output, str(exc))

    if args.json_output:
        emit_json(exit_code == EXIT_OK, exit_code, **result)
    elif exit_code == EXIT_OK:
        print(
            "task verification passed: "
            f"terminal_status={result['terminal_status']} "
            f"evidence={result['terminal_referenced_evidence_count']} "
            f"unreferenced={result['unreferenced_evidence_count']} "
            f"snapshot_match={result['snapshot_match']}"
        )
    else:
        suffix = f" detail={result['detail']}" if result.get("detail") else ""
        print(
            f"task verification failed: reason={result['reason']}{suffix}",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
