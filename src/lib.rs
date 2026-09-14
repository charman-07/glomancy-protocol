// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

//! Public Rust types and validation helpers for Glomancy Protocol.
//!
//! Glomancy Protocol is intentionally a small, transport-neutral contract layer. This crate
//! exposes protocol-visible identifiers, message metadata, capability negotiation, schema
//! registry lookup, version compatibility, resource limits, and fail-closed validation helpers.
//! It does **not** contain the private Glomancy runtime, model-provider clients, editor mutation
//! implementations, credentials, billing, or authorization policy.
//!
//! # Quick start
//!
//! The example below exercises the canonical consumer path using only public exports:
//!
//! ```rust
//! use glomancy_protocol::{
//!     Capability, CapabilityRequirement, Component, MessageHeader, MessageKind, PROTOCOL_VERSION,
//!     ProtocolVersion, negotiate_capabilities, schema_for_kind, task_capabilities_are_selected,
//! };
//!
//! // Protocol versions use a canonical major.minor.patch representation.
//! let parsed: ProtocolVersion = "0.4.0".parse().expect("valid protocol version");
//! assert_eq!(parsed, PROTOCOL_VERSION);
//! assert_eq!(PROTOCOL_VERSION.to_string(), "0.4.0");
//!
//! // Resolve the public schema identity for a wire-visible message kind.
//! let heartbeat = schema_for_kind(MessageKind::Heartbeat)
//!     .expect("heartbeat must have a registered public schema");
//! assert_eq!(heartbeat.schema_id, "urn:glomancy:protocol:heartbeat:1.0.0");
//!
//! // Negotiate capabilities by exact public name + exact version.
//! let v1 = ProtocolVersion::new(1, 0, 0);
//! let requested = [CapabilityRequirement::new(
//!     Capability::new("result.evidence", v1),
//!     true,
//! )];
//! let available = [
//!     Capability::new("result.evidence", v1),
//!     Capability::new("asset.read", v1),
//! ];
//! let selected = negotiate_capabilities(&requested, &available)
//!     .expect("required capability should negotiate exactly");
//!
//! // Task gating confirms only that the capability was selected for the session.
//! // It is deliberately separate from authorization.
//! assert!(task_capabilities_are_selected(&["result.evidence"], &selected));
//! assert!(!task_capabilities_are_selected(&["asset.write"], &selected));
//!
//! // Validate representative protocol-visible message metadata fail-closed.
//! let header = MessageHeader {
//!     schema_id: heartbeat.schema_id,
//!     protocol_version: PROTOCOL_VERSION,
//!     message_id: "11111111-1111-4111-8111-111111111111",
//!     sent_at: "2026-07-27T09:07:00Z",
//!     sender_component: Component::Bridge,
//!     sender_instance_id: "example-consumer",
//!     trace_id: "0123456789abcdef0123456789abcdef",
//!     span_id: "0123456789abcdef",
//!     kind: MessageKind::Heartbeat,
//! };
//! header.validate().expect("representative header should validate");
//! ```
//!
//! # Important boundary
//!
//! Successful schema lookup, version compatibility, capability selection, or structural message
//! validation does not authorize an editor/tool operation. Consumers remain responsible for
//! higher-layer authentication, policy, approval, execution, and verification decisions.

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
