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
