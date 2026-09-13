use core::str::FromStr;

use glomancy_protocol::{
    Capability, CapabilityNegotiationError, CapabilityRequirement, MessageKind, PROTOCOL_VERSION,
    ProtocolVersion, negotiate_capabilities, schema_for_kind, task_capabilities_are_selected,
};

fn main() {
    const CAPABILITY_V1: ProtocolVersion = ProtocolVersion::new(1, 0, 0);

    // 1. A consumer first establishes that the peer speaks a compatible wire line.
    let remote_version = ProtocolVersion::from_str("0.4.1").expect("valid remote protocol version");
    let compatibility = PROTOCOL_VERSION.compatibility_with(remote_version);
    assert!(compatibility.is_compatible());

    // 2. Capabilities are negotiated explicitly. Required capabilities fail closed;
    // optional capabilities may be omitted when unsupported.
    let requested = [
        CapabilityRequirement::new(Capability::new("editor.read", CAPABILITY_V1), true),
        CapabilityRequirement::new(Capability::new("result.evidence", CAPABILITY_V1), false),
    ];
    let available = [
        Capability::new("editor.read", CAPABILITY_V1),
        Capability::new("result.evidence", CAPABILITY_V1),
    ];
    let selected = negotiate_capabilities(&requested, &available)
        .expect("all required capabilities are supported exactly");

    // 3. A task may only request names that were selected for the session.
    assert!(task_capabilities_are_selected(&["editor.read"], &selected));
    assert!(!task_capabilities_are_selected(&["editor.write"], &selected));

    // 4. Message kinds resolve to a known, registered schema. Unknown kinds must not
    // be reinterpreted as a permissive fallback.
    let kind = MessageKind::from_wire("task.submit").expect("known public message kind");
    let schema = schema_for_kind(kind).expect("registered schema for known public kind");

    // 5. Required capability mismatches are rejected rather than silently degraded.
    let unsupported_required = [CapabilityRequirement::new(
        Capability::new("editor.write", CAPABILITY_V1),
        true,
    )];
    let rejection = negotiate_capabilities(&unsupported_required, &available);
    assert!(matches!(
        rejection,
        Err(CapabilityNegotiationError::UnsupportedRequired { .. })
    ));

    println!("local_protocol={PROTOCOL_VERSION:?}");
    println!("remote_protocol={remote_version:?}");
    println!("wire_compatible={}", compatibility.is_compatible());
    println!("selected_capabilities={}", selected.len());
    println!("message_kind={}", kind.as_wire());
    println!("schema_id={}", schema.schema_id);
    println!("schema_sha256={}", schema.sha256);
    println!("unsupported_required_capability_rejected=true");
    println!("authorization_still_required=true");
}
