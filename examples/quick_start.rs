use core::str::FromStr;

use glomancy_protocol::{MessageKind, PROTOCOL_VERSION, ProtocolVersion};

fn main() {
    let remote = ProtocolVersion::from_str("0.4.1").expect("valid protocol version");
    let compatibility = PROTOCOL_VERSION.compatibility_with(remote);

    let kind = MessageKind::from_wire("task.submit").expect("known message kind");

    println!("local={PROTOCOL_VERSION:?}");
    println!("remote={remote:?}");
    println!("compatible={}", compatibility.is_compatible());
    println!("message_kind={}", kind.as_wire());
}
