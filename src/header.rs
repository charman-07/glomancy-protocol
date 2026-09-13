// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

use crate::identifiers::{is_lower_hex, is_rfc3339_utc_shape, is_schema_urn, is_uuid};
use crate::{Component, MessageKind, ProtocolVersion};

#[derive(Debug, Clone, Copy)]
pub struct MessageHeader<'a> {
    pub schema_id: &'a str,
    pub protocol_version: ProtocolVersion,
    pub message_id: &'a str,
    pub sent_at: &'a str,
    pub sender_component: Component,
    pub sender_instance_id: &'a str,
    pub trace_id: &'a str,
    pub span_id: &'a str,
    pub kind: MessageKind,
}

impl MessageHeader<'_> {
    pub fn validate(self) -> Result<(), HeaderValidationError> {
        if !is_schema_urn(self.schema_id) {
            return Err(HeaderValidationError::InvalidSchemaId);
        }
        if !is_uuid(self.message_id) {
            return Err(HeaderValidationError::InvalidMessageId);
        }
        if !is_rfc3339_utc_shape(self.sent_at) {
            return Err(HeaderValidationError::InvalidTimestamp);
        }
        if self.sender_instance_id.is_empty() || self.sender_instance_id.len() > 128 {
            return Err(HeaderValidationError::InvalidSenderInstance);
        }
        if !is_lower_hex(self.trace_id, 32) {
            return Err(HeaderValidationError::InvalidTraceId);
        }
        if !is_lower_hex(self.span_id, 16) {
            return Err(HeaderValidationError::InvalidSpanId);
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HeaderValidationError {
    InvalidSchemaId,
    InvalidMessageId,
    InvalidTimestamp,
    InvalidSenderInstance,
    InvalidTraceId,
    InvalidSpanId,
}
