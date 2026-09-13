// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MessageKind {
    HandshakeRequest,
    HandshakeResponse,
    TaskSubmit,
    TaskProgress,
    TaskResult,
    TaskError,
    TaskCancel,
    ApprovalRequest,
    ApprovalDecision,
    EvidenceRecord,
    Heartbeat,
}

impl MessageKind {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::HandshakeRequest => "handshake.request",
            Self::HandshakeResponse => "handshake.response",
            Self::TaskSubmit => "task.submit",
            Self::TaskProgress => "task.progress",
            Self::TaskResult => "task.result",
            Self::TaskError => "task.error",
            Self::TaskCancel => "task.cancel",
            Self::ApprovalRequest => "approval.request",
            Self::ApprovalDecision => "approval.decision",
            Self::EvidenceRecord => "evidence.record",
            Self::Heartbeat => "heartbeat",
        }
    }

    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match value {
            "handshake.request" => Some(Self::HandshakeRequest),
            "handshake.response" => Some(Self::HandshakeResponse),
            "task.submit" => Some(Self::TaskSubmit),
            "task.progress" => Some(Self::TaskProgress),
            "task.result" => Some(Self::TaskResult),
            "task.error" => Some(Self::TaskError),
            "task.cancel" => Some(Self::TaskCancel),
            "approval.request" => Some(Self::ApprovalRequest),
            "approval.decision" => Some(Self::ApprovalDecision),
            "evidence.record" => Some(Self::EvidenceRecord),
            "heartbeat" => Some(Self::Heartbeat),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Component {
    Desktop,
    Bridge,
    AgentRuntime,
    PolicyEngine,
    ValidationEngine,
    Provider,
    TestHarness,
}

impl Component {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::Desktop => "desktop",
            Self::Bridge => "bridge",
            Self::AgentRuntime => "agent-runtime",
            Self::PolicyEngine => "policy-engine",
            Self::ValidationEngine => "validation-engine",
            Self::Provider => "provider",
            Self::TestHarness => "test-harness",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RiskLevel {
    R0,
    R1,
    R2,
    R3,
    R4,
}

impl RiskLevel {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::R0 => "R0",
            Self::R1 => "R1",
            Self::R2 => "R2",
            Self::R3 => "R3",
            Self::R4 => "R4",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExecutionMode {
    DryRun,
    Simulate,
    Execute,
}

impl ExecutionMode {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::DryRun => "dry-run",
            Self::Simulate => "simulate",
            Self::Execute => "execute",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskStatus {
    Accepted,
    Planning,
    AwaitingApproval,
    Running,
    Validating,
    Succeeded,
    Failed,
    Cancelled,
    RolledBack,
}
