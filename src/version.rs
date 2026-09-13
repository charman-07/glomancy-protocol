// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

use core::str::FromStr;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ProtocolVersion {
    pub major: u16,
    pub minor: u16,
    pub patch: u16,
}

impl ProtocolVersion {
    #[must_use]
    pub const fn new(major: u16, minor: u16, patch: u16) -> Self {
        Self {
            major,
            minor,
            patch,
        }
    }

    #[must_use]
    pub const fn compatibility_with(self, other: Self) -> VersionCompatibility {
        if self.major == other.major && self.minor == other.minor && self.patch == other.patch {
            return VersionCompatibility::Exact;
        }
        if self.major != other.major {
            return VersionCompatibility::Incompatible;
        }
        if self.major == 0 {
            if self.minor == other.minor {
                VersionCompatibility::PatchCompatible
            } else {
                VersionCompatibility::Incompatible
            }
        } else {
            VersionCompatibility::MajorCompatible
        }
    }
}

impl FromStr for ProtocolVersion {
    type Err = VersionParseError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let mut parts = value.split('.');
        let major = parse_component(parts.next().ok_or(VersionParseError::MissingComponent)?)?;
        let minor = parse_component(parts.next().ok_or(VersionParseError::MissingComponent)?)?;
        let patch = parse_component(parts.next().ok_or(VersionParseError::MissingComponent)?)?;
        if parts.next().is_some() {
            return Err(VersionParseError::TooManyComponents);
        }
        Ok(Self::new(major, minor, patch))
    }
}

fn parse_component(value: &str) -> Result<u16, VersionParseError> {
    if value.is_empty() {
        return Err(VersionParseError::MissingComponent);
    }
    if value.len() > 1 && value.starts_with('0') {
        return Err(VersionParseError::LeadingZero);
    }
    value
        .parse::<u16>()
        .map_err(|_| VersionParseError::InvalidNumber)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VersionCompatibility {
    Exact,
    PatchCompatible,
    MajorCompatible,
    Incompatible,
}

impl VersionCompatibility {
    #[must_use]
    pub const fn is_compatible(self) -> bool {
        !matches!(self, Self::Incompatible)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VersionParseError {
    MissingComponent,
    TooManyComponents,
    LeadingZero,
    InvalidNumber,
}
