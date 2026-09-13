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

    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match value {
            "desktop" => Some(Self::Desktop),
            "bridge" => Some(Self::Bridge),
            "agent-runtime" => Some(Self::AgentRuntime),
            "policy-engine" => Some(Self::PolicyEngine),
            "validation-engine" => Some(Self::ValidationEngine),
            "provider" => Some(Self::Provider),
            "test-harness" => Some(Self::TestHarness),
            _ => None,
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

    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match value {
            "R0" => Some(Self::R0),
            "R1" => Some(Self::R1),
            "R2" => Some(Self::R2),
            "R3" => Some(Self::R3),
            "R4" => Some(Self::R4),
            _ => None,
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

    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match value {
            "dry-run" => Some(Self::DryRun),
            "simulate" => Some(Self::Simulate),
            "execute" => Some(Self::Execute),
            _ => None,
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

impl TaskStatus {
    #[must_use]
    pub const fn as_wire(self) -> &'static str {
        match self {
            Self::Accepted => "accepted",
            Self::Planning => "planning",
            Self::AwaitingApproval => "awaiting_approval",
            Self::Running => "running",
            Self::Validating => "validating",
            Self::Succeeded => "succeeded",
            Self::Failed => "failed",
            Self::Cancelled => "cancelled",
            Self::RolledBack => "rolled_back",
        }
    }

    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match value {
            "accepted" => Some(Self::Accepted),
            "planning" => Some(Self::Planning),
            "awaiting_approval" => Some(Self::AwaitingApproval),
            "running" => Some(Self::Running),
            "validating" => Some(Self::Validating),
            "succeeded" => Some(Self::Succeeded),
            "failed" => Some(Self::Failed),
            "cancelled" => Some(Self::Cancelled),
            "rolled_back" => Some(Self::RolledBack),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{Component, ExecutionMode, RiskLevel, TaskStatus};

    #[test]
    fn component_wire_values_round_trip() {
        for value in [
            Component::Desktop,
            Component::Bridge,
            Component::AgentRuntime,
            Component::PolicyEngine,
            Component::ValidationEngine,
            Component::Provider,
            Component::TestHarness,
        ] {
            assert_eq!(Component::from_wire(value.as_wire()), Some(value));
        }
    }

    #[test]
    fn risk_level_wire_values_round_trip() {
        for value in [
            RiskLevel::R0,
            RiskLevel::R1,
            RiskLevel::R2,
            RiskLevel::R3,
            RiskLevel::R4,
        ] {
            assert_eq!(RiskLevel::from_wire(value.as_wire()), Some(value));
        }
    }

    #[test]
    fn execution_mode_wire_values_round_trip() {
        for value in [
            ExecutionMode::DryRun,
            ExecutionMode::Simulate,
            ExecutionMode::Execute,
        ] {
            assert_eq!(ExecutionMode::from_wire(value.as_wire()), Some(value));
        }
    }

    #[test]
    fn task_status_wire_values_round_trip() {
        for value in [
            TaskStatus::Accepted,
            TaskStatus::Planning,
            TaskStatus::AwaitingApproval,
            TaskStatus::Running,
            TaskStatus::Validating,
            TaskStatus::Succeeded,
            TaskStatus::Failed,
            TaskStatus::Cancelled,
            TaskStatus::RolledBack,
        ] {
            assert_eq!(TaskStatus::from_wire(value.as_wire()), Some(value));
        }
    }

    #[test]
    fn unknown_wire_enum_values_fail_closed() {
        assert_eq!(Component::from_wire("unknown"), None);
        assert_eq!(RiskLevel::from_wire("R5"), None);
        assert_eq!(ExecutionMode::from_wire("unsafe-execute"), None);
        assert_eq!(TaskStatus::from_wire("done"), None);
    }
}
