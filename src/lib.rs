// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

#![forbid(unsafe_code)]

mod capability;
mod header;
mod identifiers;
mod message;
mod policy;
mod registry;
mod version;

pub use capability::{
    Capability, CapabilityNegotiationError, CapabilityRequirement, is_capability_name,
    negotiate_capabilities, task_capabilities_are_selected,
};
pub use header::{HeaderValidationError, MessageHeader};
pub use identifiers::{is_lower_hex, is_rfc3339_utc_shape, is_schema_urn, is_sha256, is_uuid};
pub use message::{Component, ExecutionMode, MessageKind, RiskLevel, TaskStatus};
pub use policy::{
    ErrorCategory, MAX_ARTIFACTS_PER_MESSAGE, MAX_EXTENSIONS, MAX_MESSAGE_BYTES, MAX_PAYLOAD_DEPTH,
    ProtocolErrorCode,
};
pub use registry::{GENERATED_SCHEMA_REGISTRY, SchemaDescriptor, schema_for_id, schema_for_kind};
pub use version::{ProtocolVersion, VersionCompatibility, VersionParseError};

pub const PROTOCOL_VERSION: ProtocolVersion = ProtocolVersion::new(0, 4, 0);

#[cfg(test)]
mod tests {
    use core::str::FromStr;

    use super::*;

    fn valid_header() -> MessageHeader<'static> {
        MessageHeader {
            schema_id: "urn:glomancy:protocol:heartbeat:1.0.0",
            protocol_version: PROTOCOL_VERSION,
            message_id: "11111111-1111-4111-8111-111111111111",
            sent_at: "2026-07-27T09:07:00Z",
            sender_component: Component::Bridge,
            sender_instance_id: "bridge-main",
            trace_id: "0123456789abcdef0123456789abcdef",
            span_id: "0123456789abcdef",
            kind: MessageKind::Heartbeat,
        }
    }

    #[test]
    fn current_protocol_version_is_phase_four_version() {
        assert_eq!(PROTOCOL_VERSION, ProtocolVersion::new(0, 4, 0));
    }

    #[test]
    fn semantic_version_parser_accepts_core_version() {
        assert_eq!(
            ProtocolVersion::from_str("0.4.0"),
            Ok(ProtocolVersion::new(0, 4, 0))
        );
    }

    #[test]
    fn semantic_version_parser_rejects_leading_zero() {
        assert_eq!(
            ProtocolVersion::from_str("00.4.0"),
            Err(VersionParseError::LeadingZero)
        );
    }

    #[test]
    fn pre_one_minor_change_is_incompatible() {
        assert_eq!(
            PROTOCOL_VERSION.compatibility_with(ProtocolVersion::new(0, 5, 0)),
            VersionCompatibility::Incompatible
        );
    }

    #[test]
    fn pre_one_patch_change_is_compatible() {
        assert!(
            PROTOCOL_VERSION
                .compatibility_with(ProtocolVersion::new(0, 4, 9))
                .is_compatible()
        );
    }

    #[test]
    fn stable_minor_change_is_compatible() {
        assert_eq!(
            ProtocolVersion::new(1, 2, 0).compatibility_with(ProtocolVersion::new(1, 9, 0)),
            VersionCompatibility::MajorCompatible
        );
    }

    #[test]
    fn unknown_message_kind_fails_closed() {
        assert_eq!(MessageKind::from_wire("unknown.kind"), None);
    }

    #[test]
    fn every_message_kind_has_a_registered_schema() {
        for kind in [
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
        ] {
            assert!(schema_for_kind(kind).is_some(), "{}", kind.as_wire());
        }
    }

    #[test]
    fn protocol_error_codes_are_stable() {
        assert_eq!(
            ProtocolErrorCode::InvalidEnvelope.as_wire(),
            "GLM-PROTO-1001"
        );
        assert_eq!(ProtocolErrorCode::Internal.as_wire(), "GLM-PROTO-1999");
    }

    #[test]
    fn valid_header_passes() {
        assert_eq!(valid_header().validate(), Ok(()));
    }

    #[test]
    fn compatible_patch_header_passes() {
        let mut header = valid_header();
        header.protocol_version = ProtocolVersion::new(0, 4, 9);
        assert_eq!(header.validate(), Ok(()));
    }

    #[test]
    fn incompatible_protocol_version_fails_closed() {
        let mut header = valid_header();
        header.protocol_version = ProtocolVersion::new(0, 5, 0);
        assert_eq!(
            header.validate(),
            Err(HeaderValidationError::IncompatibleProtocolVersion)
        );
    }

    #[test]
    fn unknown_registered_schema_fails_closed() {
        let mut header = valid_header();
        header.schema_id = "urn:glomancy:protocol:unknown:1.0.0";
        assert_eq!(
            header.validate(),
            Err(HeaderValidationError::UnknownSchemaId)
        );
    }

    #[test]
    fn schema_kind_mismatch_fails_closed() {
        let mut header = valid_header();
        header.kind = MessageKind::TaskSubmit;
        assert_eq!(
            header.validate(),
            Err(HeaderValidationError::SchemaKindMismatch)
        );
    }

    #[test]
    fn invalid_header_message_id_fails() {
        let mut header = valid_header();
        header.message_id = "bad-id";
        assert_eq!(
            header.validate(),
            Err(HeaderValidationError::InvalidMessageId)
        );
    }

    #[test]
    fn identifiers_are_strict() {
        assert!(is_uuid("11111111-1111-4111-8111-111111111111"));
        assert!(is_sha256(&"a".repeat(64)));
        assert!(!is_sha256(&"A".repeat(64)));
        assert!(is_schema_urn("urn:glomancy:protocol:task.submit:1.0.0"));
    }
}
