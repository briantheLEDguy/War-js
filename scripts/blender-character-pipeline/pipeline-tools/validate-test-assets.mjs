#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { validateBytes, version as khronosValidatorVersion } from "gltf-validator";
import { inspectGlb } from "./inspect-glb.mjs";
import { getResource, classifyWearable } from "./character-contract.mjs";
import { PIPELINE_ROOT, resolveRepoPath } from "../tools/workspace-paths.mjs";
import { sha256File } from "../tools/pipeline-lib.mjs";
import { readConfig } from "../tools/pipeline-lib.mjs";

const fixtureRoot = path.join(PIPELINE_ROOT, "test-assets");
const indexPath = path.join(fixtureRoot, "fixture-index.json");
const errors = [];
const warnings = [];
const validatorVersion = typeof khronosValidatorVersion === "function" ? khronosValidatorVersion() : khronosValidatorVersion;
const blender = readConfig().blenderPath ?? "blender";
const poseValidator = path.join(PIPELINE_ROOT, "pipeline-tools", "validate_pose_pack.py");

if (!existsSync(indexPath)) {
  errors.push("test-assets/fixture-index.json is missing; run npm run models:generate:test-assets first");
} else {
  const index = JSON.parse(readFileSync(indexPath, "utf8"));
  const taxonomy = getResource("catalog://wearable-slots");
  for (const asset of index.assets ?? []) {
    const modelPath = resolveRepoPath(asset.model, "test fixture model");
    const qcPath = resolveRepoPath(asset.qc, "test fixture QC");
    if (!existsSync(modelPath) || !existsSync(qcPath)) {
      errors.push(`${asset.assetId}: model or QC sidecar is missing`);
      continue;
    }
    const qc = JSON.parse(readFileSync(qcPath, "utf8"));
    if (qc.modelSha256 !== sha256File(modelPath)) errors.push(`${asset.assetId}: QC modelSha256 is stale`);
    if (qc.qcPassed !== true || qc.runtimeReady !== false || qc.promotionEligible !== false) errors.push(`${asset.assetId}: fixture lifecycle/QC flags are unsafe`);
    const requiredNodes = ["socket_hand_L", "socket_hand_R", "socket_back"];
    if (asset.assetId.startsWith("chr.test")) requiredNodes.push("weapon_grip_socket_hand_R", "weapon_strike_head");
    const inspection = inspectGlb(modelPath, {
      skeletonId: "humanoid_game_v2",
      requiredNodes,
      requiredAnimations: ["idle", "walk", "run", "attack_melee"],
      requireSkin: true,
      minJointCount: 56,
    });
    if (!inspection.valid) errors.push(`${asset.assetId}: ${inspection.errors.join("; ")}`);
    if (inspection.skinCount !== 1) errors.push(`${asset.assetId}: expected exactly one canonical skin, got ${inspection.skinCount}`);
    try {
      const khronos = await validateBytes(new Uint8Array(readFileSync(modelPath)), { uri: path.basename(modelPath), maxIssues: 100 });
      if ((khronos.issues?.numErrors ?? 0) > 0) errors.push(`${asset.assetId}: Khronos glTF validator found ${khronos.issues.numErrors} error(s)`);
      if ((khronos.issues?.numWarnings ?? 0) > 0) warnings.push(`${asset.assetId}: Khronos glTF validator reported ${khronos.issues.numWarnings} warning(s)`);
    } catch (error) {
      errors.push(`${asset.assetId}: Khronos glTF validator failed: ${error}`);
    }
    const poseReportPath = path.join(fixtureRoot, "validation", `${asset.assetId.replace(/[^a-z0-9_.-]/gi, "_")}.pose-pack.json`);
    const poseRun = spawnSync(blender, ["--background", "--python", poseValidator, "--", "--model", modelPath, "--report", poseReportPath], {
      cwd: PIPELINE_ROOT,
      encoding: "utf8",
      windowsHide: true,
      maxBuffer: 16 * 1024 * 1024,
    });
    const poseLine = String(poseRun.stdout ?? "").split(/\r?\n/u).find((line) => line.startsWith("POSE_PACK_RESULT="));
    if (poseRun.status !== 0 || !poseLine) {
      errors.push(`${asset.assetId}: Blender BVHTree pose-pack validation did not complete`);
    } else {
      try {
        const poseResult = JSON.parse(poseLine.slice("POSE_PACK_RESULT=".length));
        if (poseResult.passed !== true) errors.push(`${asset.assetId}: Blender BVHTree pose-pack validation failed`);
        if (!existsSync(poseReportPath)) errors.push(`${asset.assetId}: Blender pose-pack report is missing`);
        else {
          const poseReport = JSON.parse(readFileSync(poseReportPath, "utf8"));
          if (poseReport.posePackId !== "core_v1" || poseReport.poses?.length !== 9) errors.push(`${asset.assetId}: Blender pose-pack report is incomplete`);
        }
      } catch (error) {
        errors.push(`${asset.assetId}: invalid Blender pose-pack result: ${error}`);
      }
    }
    if (qc.poseValidation?.passed !== true) errors.push(`${asset.assetId}: pose-pack validation did not pass`);
    if (asset.assetId.startsWith("chr.test") && qc.socketValidation?.overlapPairs !== 0) errors.push(`${asset.assetId}: rigid socket overlap detected`);
    if (asset.assetId.startsWith("arm.test")) {
      try {
        const classification = classifyWearable({ slot: qc.wearableValidation.slot, kind: qc.wearableValidation.kind, method: qc.wearableValidation.fitMethod });
        if (classification.kind !== "skinned") errors.push(`${asset.assetId}: chest fixture was not classified as skinned`);
      } catch (error) {
        errors.push(`${asset.assetId}: ${error.message}`);
      }
    }
    if (qc.previewImages?.length !== 4) errors.push(`${asset.assetId}: expected four review previews`);
  }
  if ((index.assets ?? []).length < 2) errors.push("at least two typed fixture models are required");
}

if (!getResource("catalog://wearable-slots").classificationOrder.join(",").includes("rigid,skinned,loose")) errors.push("typed classification order is incomplete");
if (getResource("test://pose-packs/core").posePacks?.[0]?.poses?.length !== 9) errors.push("core pose pack is incomplete");
if (getResource("export://profiles").profiles.runtime_glb_v1.maxInfluencesPerVertex !== 4) errors.push("runtime export profile must cap influences at four");

if (errors.length) {
  console.error(`FAIL: ${errors.length} test-asset validation error(s)`);
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log(`OK: test fixtures pass local GLB structural, typed-stage, pose-pack, socket, lifecycle, and Khronos glTF validation (v${validatorVersion}).`);
  if (warnings.length) for (const warning of warnings) console.warn(`WARN: ${warning}`);
}
