// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

use crate::{MessageKind, ProtocolVersion};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SchemaDescriptor {
    pub kind: MessageKind,
    pub schema_id: &'static str,
    pub schema_version: ProtocolVersion,
    pub sha256: &'static str,
    pub relative_path: &'static str,
}

include!("generated_schema_registry.rs");

#[must_use]
pub fn schema_for_kind(kind: MessageKind) -> Option<&'static SchemaDescriptor> {
    GENERATED_SCHEMA_REGISTRY
        .iter()
        .find(|entry| entry.kind == kind)
}

#[must_use]
pub fn schema_for_id(schema_id: &str) -> Option<&'static SchemaDescriptor> {
    GENERATED_SCHEMA_REGISTRY
        .iter()
        .find(|entry| entry.schema_id == schema_id)
}
