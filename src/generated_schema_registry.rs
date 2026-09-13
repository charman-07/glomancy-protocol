// Copyright (c) 2026 Glomancy
// SPDX-License-Identifier: MIT

// Generated registry snapshot for the standalone open-source package.
// Keep schema hashes in sync with schemas/v1.

pub const GENERATED_SCHEMA_REGISTRY: &[SchemaDescriptor] = &[
    SchemaDescriptor {
        kind: MessageKind::HandshakeRequest,
        schema_id: "urn:glomancy:protocol:handshake.request:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "7b3cc6a4d734ae5627a792cea901a7e65d06b00c1446af237df8a56f823358da",
        relative_path: "schemas/v1/handshake.request.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::HandshakeResponse,
        schema_id: "urn:glomancy:protocol:handshake.response:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "d0c81dc9c26bbcc4d80c01a7a829b9f27762774369ad690a4258861f40125259",
        relative_path: "schemas/v1/handshake.response.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::TaskSubmit,
        schema_id: "urn:glomancy:protocol:task.submit:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "a2ba46e277a00f24e4c1217ae649dee21d71aa245e3d9cf2c0fc13425ef5af18",
        relative_path: "schemas/v1/task.submit.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::TaskProgress,
        schema_id: "urn:glomancy:protocol:task.progress:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "26587e2facbd55e6e04825ef15add3e9ea43f4bfba3e4c9fd3474c105f388cc0",
        relative_path: "schemas/v1/task.progress.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::TaskResult,
        schema_id: "urn:glomancy:protocol:task.result:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "67fc56c85621884daa50a3de1abe51475fc1d02b75fe2f25e1b9710263302edd",
        relative_path: "schemas/v1/task.result.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::TaskError,
        schema_id: "urn:glomancy:protocol:task.error:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "1e5a63f42a38bc976c3a1d3c5871e5afc9c7d98b65a7b9db82bbac305c47e2e2",
        relative_path: "schemas/v1/task.error.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::TaskCancel,
        schema_id: "urn:glomancy:protocol:task.cancel:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "296be64e181f7a33eec6c8715559f3e56b053c57a620cfda3b2c2ee57aec9f66",
        relative_path: "schemas/v1/task.cancel.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::ApprovalRequest,
        schema_id: "urn:glomancy:protocol:approval.request:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "77746ba4d7fd68d232b2ee035daa62b740970374fccd231df244f6f11e5414f1",
        relative_path: "schemas/v1/approval.request.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::ApprovalDecision,
        schema_id: "urn:glomancy:protocol:approval.decision:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "e80af553eccfae239b36192e4c37cd3b87da7754edc5ae484807402a6d3ee9a4",
        relative_path: "schemas/v1/approval.decision.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::EvidenceRecord,
        schema_id: "urn:glomancy:protocol:evidence.record:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "151f5d93b9f1ca7d9b068891503d8f921cdf94b0827725fedb59d6297e0dbbc1",
        relative_path: "schemas/v1/evidence.record.schema.json",
    },
    SchemaDescriptor {
        kind: MessageKind::Heartbeat,
        schema_id: "urn:glomancy:protocol:heartbeat:1.0.0",
        schema_version: ProtocolVersion::new(1, 0, 0),
        sha256: "77b116c96e9b83cdb1ed6c4e3121b68b669d50f23994e5d8635e501a9be658c4",
        relative_path: "schemas/v1/heartbeat.schema.json",
    },
];
