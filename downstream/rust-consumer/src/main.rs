use glomancy_protocol::{
    Capability, CapabilityRequirement, Component, MessageHeader, MessageKind, PROTOCOL_VERSION,
    ProtocolVersion, negotiate_capabilities, schema_for_kind, task_capabilities_are_selected,
};

fn main() {
    assert_eq!(PROTOCOL_VERSION, ProtocolVersion::new(0, 4, 0));

    let heartbeat = schema_for_kind(MessageKind::Heartbeat)
        .expect("heartbeat schema must remain publicly registered");
    assert_eq!(
        heartbeat.schema_id,
        "urn:glomancy:protocol:heartbeat:1.0.0"
    );

    let capability_version = ProtocolVersion::new(1, 0, 0);
    let requested = [CapabilityRequirement::new(
        Capability::new("result.evidence", capability_version),
        true,
    )];
    let available = [
        Capability::new("result.evidence", capability_version),
        Capability::new("asset.read", capability_version),
    ];

    let selected = negotiate_capabilities(&requested, &available)
        .expect("required public capability should negotiate exactly");
    assert_eq!(selected.len(), 1);
    assert!(task_capabilities_are_selected(
        &["result.evidence"],
        &selected
    ));
    assert!(!task_capabilities_are_selected(&["asset.write"], &selected));

    let header = MessageHeader {
        schema_id: heartbeat.schema_id,
        protocol_version: PROTOCOL_VERSION,
        message_id: "11111111-1111-4111-8111-111111111111",
        sent_at: "2026-07-27T09:07:00Z",
        sender_component: Component::Bridge,
        sender_instance_id: "downstream-smoke",
        trace_id: "0123456789abcdef0123456789abcdef",
        span_id: "0123456789abcdef",
        kind: MessageKind::Heartbeat,
    };

    header
        .validate()
        .expect("representative downstream message header should validate");

    println!(
        "downstream Rust consumer passed: protocol={} schema={} selected_capabilities={}",
        PROTOCOL_VERSION,
        heartbeat.schema_id,
        selected.len()
    );
}
