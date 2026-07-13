import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  JOB_ROOT,
  PIPELINE_ROOT,
  REPO_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  resolveRepoPath,
  workflowError,
} from "./workspace-paths.mjs";
import { readConfig } from "./pipeline-lib.mjs";

export const AUDITOR_PATH = path.join(PIPELINE_ROOT, "blender", "audit_equipped_clearance.py");
export const POLICY_PATH = path.join(PIPELINE_ROOT, "data", "armor-clearance-policy.json");
export const DEFAULTS = Object.freeze({
  model: "artifacts/model-jobs/local-armor-pilot-v18/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb",
  report: "artifacts/model-jobs/local-armor-pilot-v18/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.clearance.json",
  poses: "bind,idle",
});

function option(argv, name) {
  const prefix = `--${name}=`;
  return argv.find((argument) => argument.startsWith(prefix))?.slice(prefix.length);
}

export function resolveOptions(argv = process.argv.slice(2), environment = process.env) {
  const config = readConfig();
  const modelPath = resolveRepoPath(option(argv, "model") ?? DEFAULTS.model, "equipped model");
  const defaultReport = option(argv, "model")
    ? `${option(argv, "model").replace(/\.glb$/iu, "")}.clearance.json`
    : DEFAULTS.report;
  const reportPath = assertPathWithin(
    JOB_ROOT,
    resolveRepoPath(option(argv, "report") ?? defaultReport, "clearance report"),
    "clearance report",
  );
  return {
    blenderPath: option(argv, "blender") ?? environment.BLENDER_PATH ?? config.blenderPath ?? "blender",
    modelPath,
    reportPath,
    poses: option(argv, "poses") ?? DEFAULTS.poses,
    strict: argv.includes("--strict"),
    dryRun: argv.includes("--dry-run"),
    json: argv.includes("--json"),
    timeoutMs: Number.parseInt(option(argv, "timeout-ms") ?? "900000", 10),
  };
}

export function validateInputs(options) {
  const errors = [];
  if (!existsSync(AUDITOR_PATH)) errors.push(`clearance auditor is missing: ${AUDITOR_PATH}`);
  if (!existsSync(POLICY_PATH)) errors.push(`clearance policy is missing: ${POLICY_PATH}`);
  if (!existsSync(options.modelPath) || path.extname(options.modelPath).toLowerCase() !== ".glb") {
    errors.push(`equipped runtime GLB is missing: ${options.modelPath}`);
  }
  if (!options.reportPath.toLowerCase().endsWith(".clearance.json")) {
    errors.push("clearance report must end with .clearance.json");
  }
  const poses = options.poses.split(",").map((pose) => pose.trim()).filter(Boolean);
  if (!poses.length || new Set(poses).size !== poses.length) errors.push("poses must be a non-empty unique list");
  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) errors.push("timeout-ms must be positive");
  if (errors.length) throw workflowError("CLEARANCE_AUDIT_INPUT_INVALID", errors.join("; "), { errors });
  return { poses };
}

export function buildBlenderArgs(options) {
  return [
    "--background",
    "--python", AUDITOR_PATH,
    "--",
    "--model", options.modelPath,
    "--report", options.reportPath,
    "--policy", POLICY_PATH,
    "--poses", options.poses,
  ];
}

export function allowedSevereVertices(vertexCount, policy) {
  return Math.max(
    policy.allowedSevereVertexCount,
    Math.ceil(vertexCount * policy.allowedSevereVertexRatio),
  );
}

export function evaluateBodyMetric(metric, policy) {
  return metric.severeVertexCount <= allowedSevereVertices(metric.vertexCount, policy)
    && metric.maxPenetrationMeters <= policy.hardMaxDepthMeters;
}

export function evaluateArmorPairMetric(metric, policy) {
  const thresholds = policy[metric.classification];
  if (!thresholds) throw new Error(`Unknown armor pair classification: ${metric.classification}`);
  return metric.overlapPairCount <= thresholds.hardMaxOverlapPairs
    && (
      metric.overlapPairCount <= thresholds.maxOverlapPairs
      || metric.maxUniqueTriangleRatio <= thresholds.maxUniqueTriangleRatio
    );
}

function sha256(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

export function validateReport(options) {
  if (!existsSync(options.reportPath)) {
    throw workflowError("CLEARANCE_AUDIT_OUTPUT_INVALID", "clearance report is missing");
  }
  const report = readJson(options.reportPath);
  const policy = readJson(POLICY_PATH);
  const errors = [];
  if (report.auditKind !== "equipped_character_clearance") errors.push("unexpected audit kind");
  if (report.modelSha256 !== sha256(options.modelPath)) errors.push("model hash mismatch");
  if (report.policy?.sha256 !== sha256(POLICY_PATH)) errors.push("policy hash mismatch");
  const expectedPoses = options.poses.split(",").map((pose) => pose.trim()).filter(Boolean);
  const actualPoses = (report.poses ?? []).map((row) => row.pose?.name);
  if (expectedPoses.join("|") !== actualPoses.join("|")) errors.push("audited poses do not match request");
  for (const pose of report.poses ?? []) {
    if ((pose.bodyPenetration ?? []).length !== 9) errors.push(`${pose.pose?.name}: expected nine body metrics`);
    if ((pose.armorIntersections ?? []).length !== 36) errors.push(`${pose.pose?.name}: expected 36 armor pairs`);
    for (const metric of pose.bodyPenetration ?? []) {
      if (metric.passed !== evaluateBodyMetric(metric, policy.bodyPenetration)) {
        errors.push(`${pose.pose?.name}/${metric.slot}: body threshold evaluation drift`);
      }
    }
    for (const metric of pose.armorIntersections ?? []) {
      if (metric.passed !== evaluateArmorPairMetric(metric, policy.armorIntersection)) {
        errors.push(`${pose.pose?.name}/${metric.slots?.join("+")}: pair threshold evaluation drift`);
      }
    }
    const expectedPosePass = [...pose.bodyPenetration, ...pose.armorIntersections].every((row) => row.passed);
    if (pose.passed !== expectedPosePass) errors.push(`${pose.pose?.name}: pose pass state is inconsistent`);
  }
  const expectedPass = (report.poses ?? []).length > 0 && report.poses.every((row) => row.passed);
  if (report.passed !== expectedPass) errors.push("overall pass state is inconsistent");
  if (errors.length) throw workflowError("CLEARANCE_AUDIT_OUTPUT_INVALID", errors.join("; "), { errors });
  return report;
}

function runBlender(blenderPath, args, timeoutMs) {
  return new Promise((resolve, reject) => {
    execFile(blenderPath, args, {
      cwd: REPO_ROOT,
      timeout: timeoutMs,
      maxBuffer: 32 * 1024 * 1024,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(workflowError("CLEARANCE_AUDIT_FAILED", `${error.message}\n${String(stderr).slice(-6000)}`));
        return;
      }
      resolve({ stdout: String(stdout), stderr: String(stderr) });
    });
  });
}

export async function main(argv = process.argv.slice(2)) {
  const options = resolveOptions(argv);
  const inputs = validateInputs(options);
  const blenderArgs = buildBlenderArgs(options);
  const planned = {
    cost: { currency: 0, networkUsed: false, paidServiceUsed: false },
    model: repoRelative(options.modelPath),
    report: repoRelative(options.reportPath),
    policy: repoRelative(POLICY_PATH),
    poses: inputs.poses,
    commandArgs: blenderArgs,
  };
  if (options.dryRun) {
    console.log(options.json ? JSON.stringify(planned, null, 2) : `READY: ${planned.report}`);
    return planned;
  }
  if (path.isAbsolute(options.blenderPath) && !existsSync(options.blenderPath)) {
    throw workflowError("BLENDER_NOT_FOUND", `Blender not found: ${options.blenderPath}`);
  }
  await runBlender(options.blenderPath, blenderArgs, options.timeoutMs);
  const report = validateReport(options);
  const summary = {
    ...planned,
    passed: report.passed,
    failures: Object.fromEntries(report.poses.map((pose) => [pose.pose.name, pose.summary])),
  };
  if (options.json) console.log(JSON.stringify(summary, null, 2));
  else console.log(`${report.passed ? "PASS" : "FAIL"}: ${planned.report}`);
  if (options.strict && !report.passed) {
    throw workflowError("CLEARANCE_AUDIT_THRESHOLDS_FAILED", "equipped model exceeds clearance thresholds", summary);
  }
  return summary;
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedDirectly) await main();
