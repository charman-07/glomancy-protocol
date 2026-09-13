// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

pub const MAX_MESSAGE_BYTES: usize = 1_048_576;
pub const MAX_PAYLOAD_DEPTH: usize = 32;
pub const MAX_EXTENSIONS: usize = 32;
pub const MAX_ARTIFACTS_PER_MESSAGE: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorCategory {
    InvalidRequest,
    UnsupportedVersion,
    SchemaValidation,
    PolicyDenied,
    ApprovalRequired,
    ExecutionFailed,
    ValidationFailed,
    Conflict,
    NotFound,
    Timeout,
    Cancelled,
    Internal,
}

impl ErrorCategory {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::InvalidRequest => "invalid_request",
            Self::UnsupportedVersion => "unsupported_version",
            Self::SchemaValidation => "schema_validation",
            Self::PolicyDenied => "policy_denied",
            Self::ApprovalRequired => "approval_required",
            Self::ExecutionFailed => "execution_failed",
            Self::ValidationFailed => "validation_failed",
            Self::Conflict => "conflict",
            Self::NotFound => "not_found",
            Self::Timeout => "timeout",
            Self::Cancelled => "cancelled",
            Self::Internal => "internal",
        }
    }

    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match value {
            "invalid_request" => Some(Self::InvalidRequest),
            "unsupported_version" => Some(Self::UnsupportedVersion),
            "schema_validation" => Some(Self::SchemaValidation),
            "policy_denied" => Some(Self::PolicyDenied),
            "approval_required" => Some(Self::ApprovalRequired),
            "execution_failed" => Some(Self::ExecutionFailed),
            "validation_failed" => Some(Self::ValidationFailed),
            "conflict" => Some(Self::Conflict),
            "not_found" => Some(Self::NotFound),
            "timeout" => Some(Self::Timeout),
            "cancelled" => Some(Self::Cancelled),
            "internal" => Some(Self::Internal),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProtocolErrorCode {
    InvalidEnvelope,
    UnsupportedVersion,
    UnknownSchema,
    UnknownMessageKind,
    PolicyDenied,
    MessageTooLarge,
    InvalidIdentifier,
    Internal,
}

impl ProtocolErrorCode {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::InvalidEnvelope => "GLM-PROTO-1001",
            Self::UnsupportedVersion => "GLM-PROTO-1002",
            Self::UnknownSchema => "GLM-PROTO-1003",
            Self::UnknownMessageKind => "GLM-PROTO-1004",
            Self::PolicyDenied => "GLM-PROTO-1005",
            Self::MessageTooLarge => "GLM-PROTO-1006",
            Self::InvalidIdentifier => "GLM-PROTO-1007",
            Self::Internal => "GLM-PROTO-1999",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::ErrorCategory;

    #[test]
    fn error_category_wire_values_round_trip() {
        for value in [
            ErrorCategory::InvalidRequest,
            ErrorCategory::UnsupportedVersion,
            ErrorCategory::SchemaValidation,
            ErrorCategory::PolicyDenied,
            ErrorCategory::ApprovalRequired,
            ErrorCategory::ExecutionFailed,
            ErrorCategory::ValidationFailed,
            ErrorCategory::Conflict,
            ErrorCategory::NotFound,
            ErrorCategory::Timeout,
            ErrorCategory::Cancelled,
            ErrorCategory::Internal,
        ] {
            assert_eq!(ErrorCategory::from_wire(value.as_wire()), Some(value));
        }
    }

    #[test]
    fn unknown_error_category_fails_closed() {
        assert_eq!(ErrorCategory::from_wire("unknown"), None);
    }
}
