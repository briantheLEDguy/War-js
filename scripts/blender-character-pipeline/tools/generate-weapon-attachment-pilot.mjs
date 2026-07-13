import { execFile } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  JOB_ROOT,
  PIPELINE_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  resolveRepoPath,
  workflowError,
} from "./workspace-paths.mjs";
import { readConfig, sha256File } from "./pipeline-lib.mjs";

const RECIPE_PATH = path.join(PIPELINE_ROOT, "data", "body-families", "weapon-attachment-pilot.recipe.json");
const GENERATOR_PATH = path.join(PIPELINE_ROOT, "blender", "generate_weapon_attachment_pilot.py");
const PILOT_ROOT = path.join(JOB_ROOT, "weapon-attachment-pilot");

function option(name) {
  const prefix = `--${name}=`;
  return process.argv.slice(2).find((argument) => argument.startsWith(prefix))?.slice(prefix.length);
}

function unique(values) {
  return [...new Set(values.filter(Boolean).map((value) => path.resolve(value)))];
}

function blenderVersion(config) {
  return String(config.blenderPath ?? "").match(/Blender[ /\\]([0-9]+\.[0-9]+)/i)?.[1] ?? "5.0";
}

function discoverHammerAssetRoot(explicit, recipe, config) {
  const version = blenderVersion(config);
  const roaming = process.env.APPDATA;
  const candidates = unique([
    explicit,
    process.env.MPFB_ASSET_ROOT,
    roaming && path.join(roaming, "Blender Foundation", "Blender", version, "extensions", ".user", "blender_org", "mpfb", "data"),
    roaming && path.join(roaming, "Blender Foundation", "Blender", version, "extensions", ".user", "blender_org", "mpfb2", "data"),
    roaming && path.join(roaming, "Blender Foundation", "Blender", version, "extensions", ".user", "user_default", "mpfb", "data"),
    roaming && path.join(roaming, "Blender Foundation", "Blender", version, "extensions", ".user", "user_default", "mpfb2", "data"),
    path.join(os.homedir(), "mpfb-data"),
    path.join(os.homedir(), "Documents", "makehuman", "v1py3", "data"),
  ]);
  const marker = recipe.preferredHammerSource.relativeMarker.split("/");
  const found = candidates.find((candidate) => {
    try {
      return existsSync(path.join(candidate, ...marker));
    } catch {
      return false;
    }
  });
  return { found: found ?? null, attempted: candidates };
}

function runBlender(blenderPath, args) {
  return new Promise((resolve, reject) => {
    execFile(
      blenderPath,
      args,
      {
        cwd: PIPELINE_ROOT,
        timeout: 900_000,
        maxBuffer: 32 * 1024 * 1024,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        if (error) {
          reject(workflowError("WEAPON_GENERATION_FAILED", `${error.message}\n${String(stderr).slice(-6000)}`));
          return;
        }
        resolve({ stdout: String(stdout), stderr: String(stderr) });
      },
    );
  });
}

function readGlbJson(filePath) {
  const buffer = readFileSync(filePath);
  if (buffer.length < 20 || buffer.toString("ascii", 0, 4) !== "glTF") {
    throw workflowError("INVALID_GLB", `Invalid GLB header: ${filePath}`);
  }
  const jsonLength = buffer.readUInt32LE(12);
  const chunkType = buffer.toString("ascii", 16, 20);
  if (chunkType !== "JSON") throw workflowError("INVALID_GLB", `First GLB chunk is not JSON: ${filePath}`);
  return JSON.parse(buffer.toString("utf8", 20, 20 + jsonLength).replace(/\u0000+$/g, "").trimEnd());
}

function validateRun(outputDir) {
  const manifestPath = path.join(outputDir, "run-manifest.json");
  if (!existsSync(manifestPath)) throw workflowError("WEAPON_MANIFEST_MISSING", "Blender exited without writing run-manifest.json.");
  const manifest = readJson(manifestPath);
  const errors = [];
  if (manifest.lifecycleStatus !== "draft" || manifest.runtimeReady !== false || manifest.promotionEligible !== false) {
    errors.push("run manifest is not draft-only");
  }
  if (manifest.cost?.currency !== 0 || manifest.cost?.networkUsed !== false || manifest.cost?.paidServiceUsed !== false) {
    errors.push("run manifest violates the zero-cost policy");
  }
  for (const weapon of manifest.weapons ?? []) {
    const modelPath = assertPathWithin(outputDir, path.join(outputDir, weapon.model), "draft weapon model");
    const qcPath = assertPathWithin(outputDir, path.join(outputDir, weapon.qc), "draft weapon QC");
    const reviewPath = assertPathWithin(outputDir, path.join(outputDir, weapon.review), "draft weapon review");
    if (!existsSync(modelPath) || sha256File(modelPath) !== weapon.modelSha256) errors.push(`${weapon.assetId}: model hash mismatch`);
    if (existsSync(modelPath)) {
      try {
        const glb = readGlbJson(modelPath);
        const gripNode = glb.nodes?.find((node) => node.name === "weapon_grip_socket_hand_R");
        const socketNode = glb.nodes?.find((node) => node.extras?.targetSocket === "socket_hand_R");
        if (!gripNode || gripNode.extras?.targetSocket !== "socket_hand_R") errors.push(`${weapon.assetId}: serialized grip socket metadata missing`);
        if (!socketNode || socketNode.extras?.skeletonId !== "humanoid_game_v2") errors.push(`${weapon.assetId}: serialized canonical skeleton metadata missing`);
        if (socketNode?.extras?.runtimeReady !== false || socketNode?.extras?.promotionEligible !== false) {
          errors.push(`${weapon.assetId}: serialized GLB is not draft-only`);
        }
      } catch (error) {
        errors.push(`${weapon.assetId}: GLB metadata inspection failed (${error.message})`);
      }
    }
    if (!existsSync(qcPath)) errors.push(`${weapon.assetId}: QC missing`);
    if (!existsSync(reviewPath)) errors.push(`${weapon.assetId}: review missing`);
    if (existsSync(qcPath)) {
      const qc = readJson(qcPath);
      if (qc.qcPassed !== true) errors.push(`${weapon.assetId}: QC did not pass`);
      if (qc.modelSha256 !== weapon.modelSha256) errors.push(`${weapon.assetId}: QC model hash mismatch`);
      if (qc.attachmentBinding?.targetSocket !== "socket_hand_R" || qc.attachmentBinding?.gripNode !== "weapon_grip_socket_hand_R") {
        errors.push(`${weapon.assetId}: canonical socket metadata missing`);
      }
      if (qc.runtimeReady !== false || qc.promotionEligible !== false) errors.push(`${weapon.assetId}: QC is not draft-only`);
      if (qc.roundTrip?.reviewedSerializedGlb !== true || qc.roundTrip?.serializedModelSha256 !== weapon.modelSha256) {
        errors.push(`${weapon.assetId}: GLB round-trip evidence missing`);
      }
    }
    if (existsSync(reviewPath)) {
      const review = readJson(reviewPath);
      if (review.evidenceSource !== "serialized_glb_roundtrip_reimport") errors.push(`${weapon.assetId}: review is not based on GLB round-trip evidence`);
      for (const view of ["front", "side", "back", "isometric", "socket_alignment"]) {
        const evidence = review.evidence?.[view];
        const evidencePath = evidence?.path
          ? assertPathWithin(path.dirname(reviewPath), path.join(path.dirname(reviewPath), "review", evidence.path), "review image")
          : null;
        if (!evidencePath || !existsSync(evidencePath)) errors.push(`${weapon.assetId}: ${view} review image missing`);
        else if (sha256File(evidencePath) !== evidence.sha256) errors.push(`${weapon.assetId}: ${view} review hash mismatch`);
      }
    }
  }
  if (errors.length) throw workflowError("WEAPON_PILOT_VALIDATION_FAILED", errors.join("; "), { errors });
  return { manifest, manifestPath };
}

const config = readConfig();
const blenderPath = config.blenderPath ?? "blender";
if (path.isAbsolute(blenderPath) && !existsSync(blenderPath)) throw workflowError("BLENDER_NOT_FOUND", `Blender not found: ${blenderPath}`);
if (!existsSync(RECIPE_PATH) || !existsSync(GENERATOR_PATH)) throw workflowError("WEAPON_PILOT_SOURCE_MISSING", "Weapon pilot recipe or Blender generator is missing.");

const recipe = readJson(RECIPE_PATH);
const explicitAssetRoot = option("asset-root");
const discovered = discoverHammerAssetRoot(explicitAssetRoot, recipe, config);
const requestedOutput = option("output");
const runName = `run_${new Date().toISOString().replace(/[-:.]/g, "").toLowerCase()}`;
const outputDir = requestedOutput
  ? assertPathWithin(PILOT_ROOT, resolveRepoPath(requestedOutput, "weapon pilot output"), "weapon pilot output")
  : assertPathWithin(PILOT_ROOT, path.join(PILOT_ROOT, runName), "weapon pilot output");
if (existsSync(outputDir)) throw workflowError("WEAPON_OUTPUT_EXISTS", `Refusing to overwrite an existing draft run: ${outputDir}`);

const blenderArgs = [
  "--background",
  "--python", GENERATOR_PATH,
  "--",
  "--recipe", RECIPE_PATH,
  "--output-dir", outputDir,
  "--resolution", String(Number.parseInt(option("resolution") ?? "640", 10)),
];
if (discovered.found) blenderArgs.push("--asset-root", discovered.found);
if (process.argv.includes("--require-preferred-hammer")) blenderArgs.push("--require-preferred-hammer");

const execution = await runBlender(blenderPath, blenderArgs);
const { manifest, manifestPath } = validateRun(outputDir);
const summary = {
  outputDir: repoRelative(outputDir),
  manifest: repoRelative(manifestPath),
  preferredHammerSourceFound: Boolean(discovered.found),
  preferredHammerAssetRoot: discovered.found,
  attemptedAssetRoots: discovered.attempted,
  weapons: manifest.weapons.map((weapon) => ({
    assetId: weapon.assetId,
    model: `${repoRelative(outputDir)}/${weapon.model}`,
    modelSha256: weapon.modelSha256,
    qcPassed: weapon.qcPassed,
    sourceUsed: weapon.source.sourceUsed,
    runtimeReady: weapon.runtimeReady,
    promotionEligible: weapon.promotionEligible,
  })),
};

if (process.argv.includes("--json")) {
  console.log(JSON.stringify(summary, null, 2));
} else {
  console.log(`OK: generated two draft socketed weapons at ${summary.outputDir}`);
  console.log(`preferredHammerSource=${summary.preferredHammerSourceFound ? "culturalibre CC0 equipment01" : "unavailable; original project fallback used"}`);
  for (const weapon of summary.weapons) console.log(`${weapon.assetId} -> ${weapon.model} sha256=${weapon.modelSha256}`);
  const important = execution.stdout.split(/\r?\n/).filter((line) => line.startsWith("[weapon-pilot]"));
  if (important.length) console.log(important.join("\n"));
}
