// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

use crate::ProtocolVersion;

/// A public capability identified by an opaque, protocol-visible name and exact version.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Capability<'a> {
    pub name: &'a str,
    pub version: ProtocolVersion,
}

impl<'a> Capability<'a> {
    #[must_use]
    pub const fn new(name: &'a str, version: ProtocolVersion) -> Self {
        Self { name, version }
    }
}

/// A capability advertised by a handshake initiator.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CapabilityRequirement<'a> {
    pub capability: Capability<'a>,
    pub required: bool,
}

impl<'a> CapabilityRequirement<'a> {
    #[must_use]
    pub const fn new(capability: Capability<'a>, required: bool) -> Self {
        Self {
            capability,
            required,
        }
    }
}

/// Fail-closed errors defined by capability-negotiation profile v1.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CapabilityNegotiationError<'a> {
    InvalidRemoteName(&'a str),
    InvalidLocalName(&'a str),
    DuplicateRemoteName(&'a str),
    DuplicateLocalName(&'a str),
    UnsupportedRequired {
        name: &'a str,
        version: ProtocolVersion,
    },
}

/// Returns true when `value` matches the public capability identifier contract.
#[must_use]
pub fn is_capability_name(value: &str) -> bool {
    if value.is_empty() || value.len() > 128 {
        return false;
    }

    let mut bytes = value.bytes();
    let Some(first) = bytes.next() else {
        return false;
    };

    if !first.is_ascii_lowercase() {
        return false;
    }

    bytes.all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || matches!(byte, b'.' | b'-'))
}

/// Negotiates profile-v1 capabilities using exact name + exact version matching.
///
/// Unsupported optional capabilities are omitted. An unsupported required capability
/// rejects negotiation. Duplicate names are rejected because profile v1 does not
/// define version-range negotiation for multiple versions of one capability name.
pub fn negotiate_capabilities<'a>(
    remote: &[CapabilityRequirement<'a>],
    local: &[Capability<'a>],
) -> Result<Vec<Capability<'a>>, CapabilityNegotiationError<'a>> {
    for requirement in remote {
        if !is_capability_name(requirement.capability.name) {
            return Err(CapabilityNegotiationError::InvalidRemoteName(
                requirement.capability.name,
            ));
        }
    }

    for capability in local {
        if !is_capability_name(capability.name) {
            return Err(CapabilityNegotiationError::InvalidLocalName(capability.name));
        }
    }

    if let Some(name) = first_duplicate_remote_name(remote) {
        return Err(CapabilityNegotiationError::DuplicateRemoteName(name));
    }

    if let Some(name) = first_duplicate_local_name(local) {
        return Err(CapabilityNegotiationError::DuplicateLocalName(name));
    }

    let mut selected = Vec::new();

    for requirement in remote {
        let requested = requirement.capability;
        let exact = local
            .iter()
            .any(|available| available.name == requested.name && available.version == requested.version);

        if exact {
            selected.push(requested);
        } else if requirement.required {
            return Err(CapabilityNegotiationError::UnsupportedRequired {
                name: requested.name,
                version: requested.version,
            });
        }
    }

    Ok(selected)
}

/// Returns true when every task-requested capability name was selected for the session.
///
/// This is a capability gate only; `true` does not authorize execution.
#[must_use]
pub fn task_capabilities_are_selected(requested: &[&str], selected: &[Capability<'_>]) -> bool {
    requested.iter().all(|name| {
        is_capability_name(name) && selected.iter().any(|capability| capability.name == *name)
    })
}

fn first_duplicate_remote_name<'a>(
    capabilities: &[CapabilityRequirement<'a>],
) -> Option<&'a str> {
    for (index, capability) in capabilities.iter().enumerate() {
        if capabilities[..index]
            .iter()
            .any(|previous| previous.capability.name == capability.capability.name)
        {
            return Some(capability.capability.name);
        }
    }
    None
}

fn first_duplicate_local_name<'a>(capabilities: &[Capability<'a>]) -> Option<&'a str> {
    for (index, capability) in capabilities.iter().enumerate() {
        if capabilities[..index]
            .iter()
            .any(|previous| previous.name == capability.name)
        {
            return Some(capability.name);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    const V1: ProtocolVersion = ProtocolVersion::new(1, 0, 0);
    const V1_1: ProtocolVersion = ProtocolVersion::new(1, 1, 0);

    #[test]
    fn capability_name_matches_public_schema_shape() {
        assert!(is_capability_name("asset.read"));
        assert!(is_capability_name("result.evidence-v2"));
        assert!(!is_capability_name("Asset.Read"));
        assert!(!is_capability_name("1asset.read"));
        assert!(!is_capability_name("asset_read"));
        assert!(!is_capability_name(""));
    }

    #[test]
    fn required_exact_match_is_selected() {
        let remote = [CapabilityRequirement::new(
            Capability::new("result.evidence", V1),
            true,
        )];
        let local = [
            Capability::new("result.evidence", V1),
            Capability::new("asset.read", V1),
        ];

        assert_eq!(
            negotiate_capabilities(&remote, &local),
            Ok(vec![Capability::new("result.evidence", V1)])
        );
    }

    #[test]
    fn unsupported_optional_capability_is_omitted() {
        let remote = [
            CapabilityRequirement::new(Capability::new("asset.read", V1), false),
            CapabilityRequirement::new(Capability::new("result.evidence", V1), false),
        ];
        let local = [Capability::new("result.evidence", V1)];

        assert_eq!(
            negotiate_capabilities(&remote, &local),
            Ok(vec![Capability::new("result.evidence", V1)])
        );
    }

    #[test]
    fn unsupported_required_capability_fails_closed() {
        let remote = [CapabilityRequirement::new(
            Capability::new("asset.write", V1),
            true,
        )];
        let local = [Capability::new("asset.read", V1)];

        assert_eq!(
            negotiate_capabilities(&remote, &local),
            Err(CapabilityNegotiationError::UnsupportedRequired {
                name: "asset.write",
                version: V1,
            })
        );
    }

    #[test]
    fn same_name_different_version_is_not_an_exact_match() {
        let remote = [CapabilityRequirement::new(
            Capability::new("result.evidence", V1_1),
            false,
        )];
        let local = [Capability::new("result.evidence", V1)];

        assert_eq!(negotiate_capabilities(&remote, &local), Ok(vec![]));
    }

    #[test]
    fn duplicate_remote_capability_name_is_rejected() {
        let remote = [
            CapabilityRequirement::new(Capability::new("asset.read", V1), false),
            CapabilityRequirement::new(Capability::new("asset.read", V1_1), false),
        ];
        let local = [Capability::new("asset.read", V1)];

        assert_eq!(
            negotiate_capabilities(&remote, &local),
            Err(CapabilityNegotiationError::DuplicateRemoteName("asset.read"))
        );
    }

    #[test]
    fn duplicate_local_capability_name_is_rejected() {
        let remote = [CapabilityRequirement::new(
            Capability::new("asset.read", V1),
            false,
        )];
        let local = [
            Capability::new("asset.read", V1),
            Capability::new("asset.read", V1_1),
        ];

        assert_eq!(
            negotiate_capabilities(&remote, &local),
            Err(CapabilityNegotiationError::DuplicateLocalName("asset.read"))
        );
    }

    #[test]
    fn task_capability_gate_requires_selected_name() {
        let selected = [
            Capability::new("asset.read", V1),
            Capability::new("result.evidence", V1),
        ];

        assert!(task_capabilities_are_selected(&["asset.read"], &selected));
        assert!(!task_capabilities_are_selected(&["asset.write"], &selected));
    }
}
