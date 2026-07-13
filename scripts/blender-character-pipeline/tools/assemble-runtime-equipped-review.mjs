import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync } from "node:fs";
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

export const GENERATOR_PATH = path.join(
  PIPELINE_ROOT,
  "blender",
  "assemble_runtime_equipped_review.py",
);
export const MOTION_AUDIT_PATH = path.join(
  PIPELINE_ROOT,
  "blender",
  "audit_canonical_animation_motion.py",
);

export const DEFAULTS = Object.freeze({
  body: "artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/body/body_civic_humanoid_v2_m.glb",
  modules: "artifacts/model-jobs/local-armor-pilot-v18/civic_humanoid_v2_m/modules",
  hammer: "artifacts/model-jobs/weapon-attachment-pilot/run_20260711t141724438z/battle_prelate_hammer/wep_civic_battle_prelate_dawn_maul_draft.glb",
  output: "artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.glb",
  reviewDir: "artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/runtime-assembly-roundtrip",
  report: "artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/battle_preplate_m_runtime_assembled_review.qc.json",
  motionReport: "artifacts/model-jobs/local-armor-pilot-v20/civic_humanoid_v2_m/battle_preplate_m_v20_motion.qc.json",
});

const REQUIRED_CLIPS = [
  "idle",
  "walk",
  "run",
  "combat_idle",
  "attack_melee",
  "attack_ranged",
  "cast",
  "death",
  "jump",
].sort();
const REQUIRED_VIEWS = ["front", "side", "back", "isometric"];
const MODULE_PATTERN = /^arm_civic_humanoid_v2_battle_prelate_v1_(head|shoulders|chest|hands|waist|legs|feet|back|tabard)_m\.glb$/u;

function option(argv, name) {
  const prefix = `--${name}=`;
  return argv.find((argument) => argument.startsWith(prefix))?.slice(prefix.length);
}

function resolveJobOutput(value, label) {
  return assertPathWithin(JOB_ROOT, resolveRepoPath(value, label), label);
}

export function resolveOptions(argv = process.argv.slice(2), environment = process.env) {
  const config = readConfig();
  const output = resolveJobOutput(option(argv, "output") ?? DEFAULTS.output, "assembled review output");
  return {
    blenderPath: option(argv, "blender") ?? environment.BLENDER_PATH ?? config.blenderPath ?? "blender",
    bodyPath: resolveRepoPath(option(argv, "body") ?? DEFAULTS.body, "verified runtime body"),
    modulesDir: resolveRepoPath(option(argv, "modules") ?? DEFAULTS.modules, "armor modules directory"),
    hammerPath: resolveRepoPath(option(argv, "hammer") ?? DEFAULTS.hammer, "draft hammer"),
    outputPath: output,
    reviewDir: resolveJobOutput(option(argv, "review-dir") ?? DEFAULTS.reviewDir, "assembly review directory"),
    reportPath: resolveJobOutput(
      option(argv, "report") ?? (option(argv, "output") ? `${option(argv, "output").replace(/\.glb$/iu, "")}.qc.json` : DEFAULTS.report),
      "assembly QC report",
    ),
    motionReportPath: resolveJobOutput(
      option(argv, "motion-report") ?? DEFAULTS.motionReport,
      "motion QC report",
    ),
    timeoutMs: Number.parseInt(option(argv, "timeout-ms") ?? "900000", 10),
    dryRun: argv.includes("--dry-run"),
    json: argv.includes("--json"),
  };
}

export function validateInputs(options) {
  const errors = [];
  if (!existsSync(GENERATOR_PATH)) errors.push(`assembly generator is missing: ${GENERATOR_PATH}`);
  if (!existsSync(MOTION_AUDIT_PATH)) errors.push(`motion audit is missing: ${MOTION_AUDIT_PATH}`);
  if (!existsSync(options.bodyPath) || path.extname(options.bodyPath).toLowerCase() !== ".glb") {
    errors.push(`verified runtime body GLB is missing: ${options.bodyPath}`);
  }
  if (!existsSync(options.hammerPath) || path.extname(options.hammerPath).toLowerCase() !== ".glb") {
    errors.push(`draft hammer GLB is missing: ${options.hammerPath}`);
  }
  if (path.extname(options.outputPath).toLowerCase() !== ".glb") errors.push("assembled review output must be a .glb file");
  if (!options.reportPath.toLowerCase().endsWith(".qc.json")) errors.push("assembly report must end with .qc.json");
  if (options.outputPath === options.reportPath) errors.push("assembly model and report paths must be different");
  let moduleFiles = [];
  if (!existsSync(options.modulesDir)) errors.push(`armor modules directory is missing: ${options.modulesDir}`);
  else {
    moduleFiles = readdirSync(options.modulesDir).filter((file) => MODULE_PATTERN.test(file)).sort();
    if (moduleFiles.length !== 9) errors.push(`expected nine Battle Prelate module GLBs; found ${moduleFiles.length}`);
  }
  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) errors.push("timeout-ms must be a positive integer");
  if (errors.length) throw workflowError("RUNTIME_ASSEMBLY_INPUT_INVALID", errors.join("; "), { errors });
  return { moduleFiles };
}

export function buildBlenderArgs(options) {
  return [
    "--background",
    "--python", GENERATOR_PATH,
    "--",
    "--body-glb", options.bodyPath,
    "--modules-dir", options.modulesDir,
    "--hammer-glb", options.hammerPath,
    "--output", options.outputPath,
    "--review-dir", options.reviewDir,
    "--report", options.reportPath,
  ];
}

export function buildMotionAuditArgs(options) {
  return [
    "--background",
    "--python", MOTION_AUDIT_PATH,
    "--",
    "--model", options.outputPath,
    "--output", options.motionReportPath,
  ];
}

function sha256(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

export function readGlbJson(filePath) {
  const payload = readFileSync(filePath);
  if (payload.length < 20 || payload.toString("ascii", 0, 4) !== "glTF") {
    throw workflowError("RUNTIME_ASSEMBLY_GLB_INVALID", `Invalid GLB header: ${filePath}`);
  }
  let offset = 12;
  while (offset + 8 <= payload.length) {
    const length = payload.readUInt32LE(offset);
    const kind = payload.toString("ascii", offset + 4, offset + 8);
    if (kind === "JSON") {
      return JSON.parse(payload.toString("utf8", offset + 8, offset + 8 + length).replace(/\u0000+$/gu, "").trimEnd());
    }
    offset += 8 + length;
  }
  throw workflowError("RUNTIME_ASSEMBLY_GLB_INVALID", `GLB JSON chunk is missing: ${filePath}`);
}

function everyBooleanTrue(record) {
  return record && Object.values(record).length > 0 && Object.values(record).every((value) => value === true);
}

export function validateOutputs(options) {
  const errors = [];
  if (!existsSync(options.outputPath)) errors.push("combined runtime assembly GLB is missing");
  if (!existsSync(options.reportPath)) errors.push("runtime assembly QC report is missing");
  if (!existsSync(options.motionReportPath)) errors.push("canonical motion QC report is missing");
  if (errors.length) throw workflowError("RUNTIME_ASSEMBLY_OUTPUT_INVALID", errors.join("; "), { errors });
  const report = readJson(options.reportPath);
  const motionReport = readJson(options.motionReportPath);
  const actualHash = sha256(options.outputPath);
  if (report.modelSha256 !== actualHash) errors.push("combined GLB hash does not match its QC report");
  if (report.technicalRoundTripPassed !== true) errors.push("technical GLB round-trip did not pass");
  if (report.promotionEligible !== false || report.lifecycleStatus !== "draft") errors.push("assembly is not draft-only");
  if (!everyBooleanTrue(report.preExportChecks)) errors.push("one or more pre-export checks failed");
  if (report.roundTrip?.passed !== true) errors.push("serialized round-trip audit failed");
  if (report.roundTrip?.moduleMeshCount !== 9) errors.push("serialized assembly does not contain nine modules");
  if (report.roundTrip?.bodyMeshCount !== 4) errors.push("serialized assembly does not contain four body meshes");
  if (report.roundTrip?.weaponMeshCount !== 1) errors.push("serialized assembly does not contain one hammer mesh");
  if (report.roundTrip?.boneCount !== 56) errors.push("serialized assembly does not contain 56 canonical bones");
  if ([...(report.roundTrip?.animationClips ?? [])].sort().join("|") !== REQUIRED_CLIPS.join("|")) {
    errors.push("serialized assembly does not contain the canonical nine clips");
  }
  if (report.roundTrip?.idleDeltaAudit?.passed !== true) errors.push("bind-to-idle center/extent audit failed");
  if (motionReport.modelSha256 !== actualHash) errors.push("motion QC hash does not match the assembled GLB");
  if (motionReport.passed !== true) errors.push("canonical motion ergonomic audit failed");
  if (!everyBooleanTrue(report.roundTrip?.checks) || !everyBooleanTrue(report.roundTrip?.glbJsonChecks)) {
    errors.push("one or more post-import structure checks failed");
  }
  for (const pose of ["bindPose", "idlePose"]) {
    const evidence = report.roundTrip?.[pose]?.previews ?? [];
    for (const view of REQUIRED_VIEWS) {
      const row = evidence.find((candidate) => candidate.view === view);
      let evidencePath = null;
      try {
        evidencePath = row?.path
          ? assertPathWithin(options.reviewDir, row.path, `${pose} ${view} preview`)
          : null;
      } catch (error) {
        errors.push(`${pose} ${view} preview is unsafe: ${error.message}`);
      }
      if (!evidencePath || !existsSync(evidencePath)) errors.push(`${pose} ${view} preview is missing`);
      else if (sha256(evidencePath) !== row.sha256) errors.push(`${pose} ${view} preview hash mismatch`);
    }
  }
  try {
    const document = readGlbJson(options.outputPath);
    if (document.skins?.length !== 1) errors.push(`combined GLB has ${document.skins?.length ?? 0} skins instead of one`);
    const clips = (document.animations ?? []).map((animation) => animation.name).sort();
    if (clips.join("|") !== REQUIRED_CLIPS.join("|")) errors.push("combined GLB JSON animation names are incomplete");
  } catch (error) {
    errors.push(`combined GLB inspection failed: ${error.message}`);
  }
  if (errors.length) throw workflowError("RUNTIME_ASSEMBLY_OUTPUT_INVALID", errors.join("; "), { errors });
  return { report, motionReport, actualHash };
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
        reject(workflowError(
          "RUNTIME_ASSEMBLY_FAILED",
          `${error.message}\n${String(stderr ?? "").slice(-6000)}`,
          { exitCode: error.code },
        ));
        return;
      }
      resolve({ stdout: String(stdout ?? ""), stderr: String(stderr ?? "") });
    });
  });
}

export async function main(argv = process.argv.slice(2)) {
  const options = resolveOptions(argv);
  const inputs = validateInputs(options);
  const blenderArgs = buildBlenderArgs(options);
  const planned = {
    cost: { currency: 0, networkUsed: false, paidServiceUsed: false },
    blenderPath: options.blenderPath,
    generator: repoRelative(GENERATOR_PATH),
    inputs: {
      body: repoRelative(options.bodyPath),
      modules: repoRelative(options.modulesDir),
      moduleFiles: inputs.moduleFiles,
      hammer: repoRelative(options.hammerPath),
    },
    outputs: {
      model: repoRelative(options.outputPath),
      report: repoRelative(options.reportPath),
      motionReport: repoRelative(options.motionReportPath),
      reviewDir: repoRelative(options.reviewDir),
    },
    commandArgs: blenderArgs,
    motionAuditArgs: buildMotionAuditArgs(options),
  };
  if (options.dryRun) {
    console.log(options.json ? JSON.stringify(planned, null, 2) : `READY: ${planned.outputs.model}`);
    return planned;
  }
  if (path.isAbsolute(options.blenderPath) && !existsSync(options.blenderPath)) {
    throw workflowError("BLENDER_NOT_FOUND", `Blender not found: ${options.blenderPath}`);
  }
  const execution = await runBlender(options.blenderPath, blenderArgs, options.timeoutMs);
  await runBlender(options.blenderPath, buildMotionAuditArgs(options), options.timeoutMs);
  const validated = validateOutputs(options);
  const summary = {
    ...planned,
    modelSha256: validated.actualHash,
    technicalRoundTripPassed: validated.report.technicalRoundTripPassed,
    idleDeltaPassed: validated.report.roundTrip.idleDeltaAudit.passed,
    promotionEligible: validated.report.promotionEligible,
  };
  if (options.json) console.log(JSON.stringify(summary, null, 2));
  else {
    console.log(`OK: runtime-equipped review assembled at ${summary.outputs.model}`);
    console.log(`sha256=${summary.modelSha256}`);
    console.log("technicalRoundTripPassed=true idleDeltaPassed=true promotionEligible=false");
    const important = execution.stdout.split(/\r?\n/u).filter((line) => line.startsWith("[runtime-equipped-assembly]"));
    if (important.length) console.log(important.join("\n"));
  }
  return summary;
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (invokedDirectly) await main();
