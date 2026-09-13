use core::str::FromStr;

use glomancy_protocol::{
    MessageKind, PROTOCOL_VERSION, ProtocolVersion, VersionCompatibility, is_sha256, schema_for_kind,
};

const ALL_MESSAGE_KINDS: [MessageKind; 11] = [
    MessageKind::HandshakeRequest,
    MessageKind::HandshakeResponse,
    MessageKind::TaskSubmit,
    MessageKind::TaskProgress,
    MessageKind::TaskResult,
    MessageKind::TaskError,
    MessageKind::TaskCancel,
    MessageKind::ApprovalRequest,
    MessageKind::ApprovalDecision,
    MessageKind::EvidenceRecord,
    MessageKind::Heartbeat,
];

#[test]
fn every_public_message_kind_round_trips_through_wire_name() {
    for kind in ALL_MESSAGE_KINDS {
        assert_eq!(MessageKind::from_wire(kind.as_wire()), Some(kind));
    }
}

#[test]
fn every_public_message_kind_has_a_hashed_schema_descriptor() {
    for kind in ALL_MESSAGE_KINDS {
        let descriptor = schema_for_kind(kind).expect("registered schema for public message kind");
        assert!(descriptor.schema_id.starts_with("urn:glomancy:protocol:"));
        assert!(descriptor.relative_path.starts_with("schemas/v1/"));
        assert!(descriptor.relative_path.ends_with(".schema.json"));
        assert!(is_sha256(descriptor.sha256));
    }
}

#[test]
fn unknown_wire_values_remain_fail_closed() {
    for value in ["", "task", "task.execute", "TASK.SUBMIT", "unknown.kind"] {
        assert_eq!(MessageKind::from_wire(value), None, "{value}");
    }
}

#[test]
fn pre_one_version_boundaries_are_conservative() {
    let current = ProtocolVersion::from_str("0.4.0").expect("valid version");
    let patch = ProtocolVersion::from_str("0.4.99").expect("valid version");
    let next_minor = ProtocolVersion::from_str("0.5.0").expect("valid version");

    assert_eq!(current, PROTOCOL_VERSION);
    assert_eq!(
        current.compatibility_with(patch),
        VersionCompatibility::PatchCompatible
    );
    assert_eq!(
        current.compatibility_with(next_minor),
        VersionCompatibility::Incompatible
    );
}

#[test]
fn stable_major_line_is_compatible_but_major_change_is_not() {
    let local = ProtocolVersion::new(1, 2, 0);
    assert_eq!(
        local.compatibility_with(ProtocolVersion::new(1, 9, 7)),
        VersionCompatibility::MajorCompatible
    );
    assert_eq!(
        local.compatibility_with(ProtocolVersion::new(2, 0, 0)),
        VersionCompatibility::Incompatible
    );
}
