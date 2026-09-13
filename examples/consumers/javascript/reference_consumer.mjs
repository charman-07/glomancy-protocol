#!/usr/bin/env node
/**
 * Independent, dependency-free JavaScript consumer for public Glomancy Protocol vectors.
 *
 * This example intentionally does not invoke the Rust crate, Python validators, or
 * private Glomancy runtime. It implements selected public consumer decisions itself
 * and checks them against the language-neutral vectors under vectors/v1/.
 */

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "../../..");
const VECTORS = resolve(ROOT, "vectors/v1");
const REGISTRY = resolve(ROOT, "registry/v1/manifest.json");
const SEMVER_RE = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/;
const CAPABILITY_RE = /^[a-z][a-z0-9.-]{0,127}$/;

class ConsumerError extends Error {}

function loadJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function semverTuple(value) {
  const match = SEMVER_RE.exec(value);
  if (!match) {
    throw new Error(`invalid semantic version: ${value}`);
  }
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function compareSemver(left, right) {
  const a = semverTuple(left);
  const b = semverTuple(right);
  for (let index = 0; index < 3; index += 1) {
    if (a[index] !== b[index]) return a[index] - b[index];
  }
  return 0;
}

function hasDuplicates(values) {
  return new Set(values).size !== values.length;
}

function selectAdvertisedVersion(localSupported, remoteSupported) {
  for (const value of localSupported) {
    if (!SEMVER_RE.test(value)) {
      return {
        accepted: false,
        selected_version: null,
        reason: "invalid-local-version",
      };
    }
  }
  for (const value of remoteSupported) {
    if (!SEMVER_RE.test(value)) {
      return {
        accepted: false,
        selected_version: null,
        reason: "invalid-remote-version",
      };
    }
  }

  if (hasDuplicates(localSupported)) {
    return {
      accepted: false,
      selected_version: null,
      reason: "duplicate-local-version",
    };
  }
  if (hasDuplicates(remoteSupported)) {
    return {
      accepted: false,
      selected_version: null,
      reason: "duplicate-remote-version",
    };
  }

  const remoteSet = new Set(remoteSupported);
  const shared = localSupported.filter((value) => remoteSet.has(value));
  if (shared.length === 0) {
    return {
      accepted: false,
      selected_version: null,
      reason: "no-shared-advertised-version",
    };
  }

  shared.sort(compareSemver);
  return {
    accepted: true,
    selected_version: shared.at(-1),
    reason: null,
  };
}

function validCapabilityName(name) {
  return Buffer.byteLength(name, "utf8") <= 128 && CAPABILITY_RE.test(name);
}

function duplicateCapabilityName(entries) {
  return hasDuplicates(entries.map((entry) => String(entry.name ?? "")));
}

function negotiateCapabilities(requested, available) {
  for (const entry of requested) {
    const name = String(entry.name ?? "");
    if (!validCapabilityName(name)) {
      return { accepted: false, selected: [], error: "invalid-remote-name" };
    }
    if (!SEMVER_RE.test(String(entry.version ?? ""))) {
      return { accepted: false, selected: [], error: "invalid-remote-version" };
    }
  }

  for (const entry of available) {
    const name = String(entry.name ?? "");
    if (!validCapabilityName(name)) {
      return { accepted: false, selected: [], error: "invalid-local-name" };
    }
    if (!SEMVER_RE.test(String(entry.version ?? ""))) {
      return { accepted: false, selected: [], error: "invalid-local-version" };
    }
  }

  if (duplicateCapabilityName(requested)) {
    return { accepted: false, selected: [], error: "duplicate-remote-name" };
  }
  if (duplicateCapabilityName(available)) {
    return { accepted: false, selected: [], error: "duplicate-local-name" };
  }

  const availablePairs = new Set(
    available.map((entry) => `${String(entry.name)}\u0000${String(entry.version)}`),
  );
  const selected = [];

  for (const entry of requested) {
    const name = String(entry.name);
    const version = String(entry.version);
    if (availablePairs.has(`${name}\u0000${version}`)) {
      selected.push({ name, version });
    } else if (Boolean(entry.required)) {
      return { accepted: false, selected: [], error: "unsupported-required" };
    }
  }

  return { accepted: true, selected, error: null };
}

function taskCapabilityGate(requestedNames, selected) {
  const selectedNames = new Set(selected.map((entry) => String(entry.name ?? "")));
  const accepted = requestedNames.every(
    (name) => validCapabilityName(name) && selectedNames.has(name),
  );
  return { accepted };
}

function parseTimestamp(value) {
  if (typeof value !== "string" || !/(Z|[+-][0-9]{2}:[0-9]{2})$/.test(value)) {
    throw new Error("timestamp must include a timezone");
  }
  const milliseconds = Date.parse(value);
  if (Number.isNaN(milliseconds)) throw new Error(`invalid timestamp: ${value}`);
  return milliseconds;
}

function evaluateApproval(request, decision) {
  if (decision.approval_id !== request.approval_id) {
    return { accepted: false, authorized: false, reason: "approval-id-mismatch" };
  }
  if (decision.task_id !== request.task_id) {
    return { accepted: false, authorized: false, reason: "task-id-mismatch" };
  }
  if (decision.decision !== "approve" && decision.decision !== "deny") {
    return { accepted: false, authorized: false, reason: "invalid-decision" };
  }

  let expiresAt;
  let decidedAt;
  try {
    expiresAt = parseTimestamp(request.expires_at);
    decidedAt = parseTimestamp(decision.decided_at);
  } catch {
    return { accepted: false, authorized: false, reason: "invalid-timestamp" };
  }

  if (decidedAt > expiresAt) {
    return { accepted: false, authorized: false, reason: "expired" };
  }
  if (decision.decision === "deny") {
    return { accepted: true, authorized: false, reason: "denied" };
  }

  // Here "authorized" means the approval gate is satisfied for this vector only.
  // Authentication, local authorization, policy, sandboxing, and editor permissions
  // remain separate integration responsibilities.
  return { accepted: true, authorized: true, reason: null };
}

function runCases(filename, evaluator) {
  const data = loadJson(resolve(VECTORS, filename));
  if (!data || typeof data !== "object" || !Array.isArray(data.cases)) {
    throw new ConsumerError(`invalid vector file: ${filename}`);
  }

  let count = 0;
  for (const testCase of data.cases) {
    if (!testCase || typeof testCase !== "object") {
      throw new ConsumerError(`invalid case in ${filename}`);
    }
    const caseId = String(testCase.id ?? "<missing-id>");
    const inputs = testCase.input;
    const expected = testCase.expected;
    if (!inputs || typeof inputs !== "object" || !expected || typeof expected !== "object") {
      throw new ConsumerError(`${filename}:${caseId}: malformed input/expected`);
    }
    const actual = evaluator(inputs);
    if (!isDeepStrictEqual(actual, expected)) {
      throw new ConsumerError(
        `${filename}:${caseId}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
      );
    }
    count += 1;
  }
  return count;
}

function main() {
  const registry = loadJson(REGISTRY);
  if (!registry || typeof registry !== "object") {
    throw new ConsumerError("registry manifest must be an object");
  }
  const wireVersion = registry.wire_protocol_version;
  const messageSchemas = registry.message_schemas;
  if (typeof wireVersion !== "string" || !SEMVER_RE.test(wireVersion)) {
    throw new ConsumerError("registry wire_protocol_version is invalid");
  }
  if (!Array.isArray(messageSchemas) || messageSchemas.length === 0) {
    throw new ConsumerError("registry has no message schemas");
  }

  const suites = [
    ["version-negotiation.json", (input) => selectAdvertisedVersion(input.local_supported, input.remote_supported)],
    ["capabilities.json", (input) => negotiateCapabilities(input.requested, input.available)],
    ["task-capability-gate.json", (input) => taskCapabilityGate(input.requested_names, input.selected)],
    ["approval-flow.json", (input) => evaluateApproval(input.request, input.decision)],
  ];

  const total = suites.reduce(
    (sum, [filename, evaluator]) => sum + runCases(filename, evaluator),
    0,
  );
  console.log(
    `independent JavaScript consumer passed ${total} cases across ${suites.length} vector areas; ` +
      `wire=${wireVersion} schemas=${messageSchemas.length}`,
  );
}

try {
  main();
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`independent JavaScript consumer failed: ${message}`);
  process.exitCode = 1;
}
