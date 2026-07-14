import { existsSync } from "node:fs";
import path from "node:path";
import { startModelJob } from "../tools/model-jobs.mjs";
import { sha256File, sha256Json } from "../tools/pipeline-lib.mjs";
import { repoRelative, writeJsonAtomic, workflowError } from "../tools/workspace-paths.mjs";
import { inspectGlb } from "./inspect-glb.mjs";
import { validateStageRequest } from "./character-contract.mjs";

function sourceHash(modelPath) {
  if (!modelPath) return null;
  if (!existsSync(modelPath)) throw workflowError("MODEL_SOURCE_MISSING", `Stage source model is missing: ${modelPath}`);
  return sha256File(modelPath);
}

export function startCharacterStageJob(stage, input = {}) {
  const contract = validateStageRequest(stage, input);
  const assetKeys = [
    `character-stage:${stage}`,
    contract.archetype ? `body:${contract.archetype.id}` : null,
    contract.assetId ? `asset:${contract.assetId}` : null,
    contract.itemId ? `item:${contract.itemId}` : null,
  ].filter(Boolean);
  return startModelJob(stage, input, async (ctx) => {
    ctx.update(10, `Validated ${stage} contract`);
    const modelPath = contract.modelPath ?? contract.bodyModel ?? contract.sourceModel ?? null;
    const plan = {
      schemaVersion: 1,
      stage,
      contract,
      inputSha256: sha256Json(input),
      sourceModel: modelPath ? { path: repoRelative(modelPath), sha256: sourceHash(modelPath) } : null,
      lifecycle: "draft",
      createdAt: new Date().toISOString(),
    };
    const planPath = path.join(ctx.artifactDir, "character-stage-plan.json");
    writeJsonAtomic(planPath, plan);
    ctx.addArtifact(planPath, "character_stage_plan");
    if (stage === "validate_pose_pack" && modelPath) {
      ctx.update(60, "Inspecting GLB structure against the canonical pose/export contract");
      const inspection = inspectGlb(modelPath, {
        skeletonId: "humanoid_game_v2",
        requiredNodes: ["socket_hand_L", "socket_hand_R", "socket_back"],
        requireSkin: true,
      });
      const report = { ...inspection, posePackId: contract.posePack.id, bvhAudit: "delegated_to_blender_pose_validator" };
      const reportPath = path.join(ctx.artifactDir, "pose-pack-validation.json");
      writeJsonAtomic(reportPath, report);
      ctx.addArtifact(reportPath, "pose_pack_validation");
      if (!inspection.valid) throw workflowError("POSE_PACK_STRUCTURE_FAILED", inspection.errors.join("; "), { report: repoRelative(reportPath) });
      return { stage, valid: true, report: repoRelative(reportPath), inspection };
    }
    ctx.update(85, `${stage} plan is ready for the Blender execution stage`);
    return {
      stage,
      valid: true,
      classification: contract.classification ?? null,
      plan: repoRelative(planPath),
      execution: stage === "export_asset" ? "Blender exporter required" : "Blender stage ready",
    };
  }, { assetKeys });
}
