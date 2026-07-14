import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { PIPELINE_ROOT, REPO_ROOT, resolveRepoPath, workflowError } from "../tools/workspace-paths.mjs";

export const PIPELINE_DATA_DIR = path.join(PIPELINE_ROOT, "pipeline-data");
export const RESOURCE_FILES = {
  "catalog://classes": "class-catalog.json",
  "catalog://body-archetypes": "body-archetypes.json",
  "rig://humanoid-v1/sockets": "socket-map.json",
  "rig://humanoid-v1/body-masks": "body-masks.json",
  "catalog://wearable-slots": "slot-taxonomy.json",
  "test://pose-packs/core": "pose-packs.json",
  "export://profiles": "export-profiles.json",
  "catalog://item-offset-presets": "item-offset-presets.json",
};

const TAXONOMY = readResource("catalog://wearable-slots");
const ARCHETYPES = readResource("catalog://body-archetypes");
const POSE_PACKS = readResource("test://pose-packs/core");
const EXPORT_PROFILES = readResource("export://profiles");

function requireString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw workflowError("INVALID_CHARACTER_CONTRACT", `${field} must be a non-empty string.`);
  }
  return value.trim();
}

function readResource(uri) {
  const relative = RESOURCE_FILES[uri];
  if (!relative) throw workflowError("RESOURCE_NOT_FOUND", `Unknown character-pipeline resource: ${uri}`);
  const resourcePath = path.resolve(PIPELINE_DATA_DIR, relative);
  if (!existsSync(resourcePath)) throw workflowError("RESOURCE_FILE_MISSING", `Resource file is missing: ${resourcePath}`);
  return JSON.parse(readFileSync(resourcePath, "utf8"));
}

export function listResources() {
  return Object.entries(RESOURCE_FILES).map(([uri, relative]) => ({
    uri,
    name: uri.replace(/^[^:]+:\/\//, ""),
    mimeType: "application/json",
    description: `Stable character-pipeline contract: ${relative}`,
  }));
}

export function getResource(uri) {
  return readResource(uri);
}

export function archetypeFor(bodyFamily, bodyVariant) {
  const id = `${requireString(bodyFamily, "bodyFamily")}.${requireString(bodyVariant, "bodyVariant")}`;
  const archetype = ARCHETYPES.archetypes.find((entry) => entry.id === id);
  if (!archetype) throw workflowError("BODY_ARCHETYPE_NOT_FOUND", `No canonical body archetype exists for ${id}.`);
  return archetype;
}

export function socketFor(socketId) {
  const requestedId = requireString(socketId, "socketId");
  const socketMap = getResource("rig://humanoid-v1/sockets");
  const id = socketMap.semanticAliases?.[requestedId] ?? requestedId;
  const socket = socketMap.sockets?.find((entry) => entry.name === id);
  if (!socket) throw workflowError("SOCKET_NOT_FOUND", `Unknown canonical socket: ${requestedId}.`);
  return socket;
}

export function slotFor(slot) {
  const id = requireString(slot, "slot");
  const definition = TAXONOMY.slots?.[id];
  if (!definition) throw workflowError("WEARABLE_SLOT_NOT_FOUND", `Unknown typed wearable slot: ${id}.`);
  return { slot: id, ...definition };
}

export function classifyWearable({ slot, kind, method } = {}) {
  const definition = slotFor(slot);
  if (kind !== undefined && kind !== definition.kind) {
    throw workflowError("WEARABLE_KIND_MISMATCH", `${slot} is classified as ${definition.kind}, not ${kind}.`);
  }
  const policy = TAXONOMY[definition.kind];
  if (method !== undefined && !policy.allowedMethods.includes(method)) {
    throw workflowError("WEARABLE_METHOD_UNSUPPORTED", `${definition.kind} slot ${slot} does not allow ${method}.`, {
      allowedMethods: policy.allowedMethods,
    });
  }
  return {
    kind: definition.kind,
    slot: definition.slot,
    allowedMethods: policy.allowedMethods,
    ...definition,
  };
}

export function validateStageRequest(stage, input = {}) {
  const value = input ?? {};
  if (stage === "assemble_base_character") {
    const archetype = archetypeFor(value.bodyFamily, value.bodyVariant);
    return {
      stage,
      operation: "assemble_base_character",
      archetype,
      skeletonId: ARCHETYPES.canonicalSkeletonId,
      bindPoseId: ARCHETYPES.canonicalBindPoseId,
      bodyModel: value.bodyModel ? resolveRepoPath(value.bodyModel, "bodyModel") : null,
    };
  }
  if (stage === "fit_wearable") {
    const classification = classifyWearable({ slot: value.slot, kind: value.kind, method: value.method });
    if (classification.kind === "rigid") {
      throw workflowError("RIGID_REQUIRES_SOCKET_PATH", "Rigid equipment must use attach_rigid_item, never fit_wearable.");
    }
    return {
      stage,
      operation: "fit_wearable",
      assetId: requireString(value.assetId, "assetId"),
      classification,
      sourceModel: value.sourceModel ? resolveRepoPath(value.sourceModel, "sourceModel") : null,
      bodyFamily: value.bodyFamily ?? null,
      bodyVariant: value.bodyVariant ?? null,
      skeletonId: ARCHETYPES.canonicalSkeletonId,
      bindPoseId: ARCHETYPES.canonicalBindPoseId,
    };
  }
  if (stage === "apply_body_mask") {
    const maskId = requireString(value.maskId, "maskId");
    const mask = getResource("rig://humanoid-v1/body-masks").masks?.find((entry) => entry.id === maskId);
    if (!mask) throw workflowError("BODY_MASK_NOT_FOUND", `Unknown body-region mask: ${maskId}.`);
    return { stage, operation: "apply_body_mask", mask };
  }
  if (stage === "attach_rigid_item") {
    const classification = classifyWearable({ slot: value.slot ?? "weapon", kind: "rigid", method: value.method ?? "bone_parent" });
    const socket = socketFor(value.socketId);
    if (!classification.socketIds.includes(socket.name)) {
      throw workflowError("SOCKET_SLOT_MISMATCH", `${classification.slot} cannot attach to ${socket.name}.`);
    }
    return {
      stage,
      operation: "attach_rigid_item",
      itemId: requireString(value.itemId, "itemId"),
      classification,
      socket,
      offsetProfile: value.offsetProfile ?? null,
    };
  }
  if (stage === "validate_pose_pack") {
    const posePackId = value.posePackId ?? "core_v1";
    const posePack = POSE_PACKS.posePacks?.find((entry) => entry.id === posePackId);
    if (!posePack) throw workflowError("POSE_PACK_NOT_FOUND", `Unknown pose pack: ${posePackId}.`);
    return {
      stage,
      operation: "validate_pose_pack",
      posePack,
      modelPath: value.modelPath ? resolveRepoPath(value.modelPath, "modelPath") : null,
      exportProfile: EXPORT_PROFILES.profiles.runtime_glb_v1,
    };
  }
  if (stage === "render_turntable") {
    return {
      stage,
      operation: "render_turntable",
      modelPath: resolveRepoPath(requireString(value.modelPath, "modelPath"), "modelPath"),
      preset: value.preset ?? "four_view_orthographic",
      posePackId: value.posePackId ?? "core_v1",
    };
  }
  if (stage === "export_asset") {
    const target = value.target ?? "glb";
    if (target !== "glb") throw workflowError("EXPORT_TARGET_UNSUPPORTED", "The reviewed pipeline currently exports GLB only.");
    return {
      stage,
      operation: "export_asset",
      modelPath: resolveRepoPath(requireString(value.modelPath, "modelPath"), "modelPath"),
      target,
      profileId: value.profileId ?? "runtime_glb_v1",
      exportProfile: EXPORT_PROFILES.profiles[value.profileId ?? "runtime_glb_v1"] ?? EXPORT_PROFILES.profiles.runtime_glb_v1,
    };
  }
  throw workflowError("UNKNOWN_CHARACTER_STAGE", `Unknown character pipeline stage: ${stage}.`);
}

export function pipelineContractSummary() {
  return {
    taxonomyId: TAXONOMY.taxonomyId,
    canonicalSkeletonId: ARCHETYPES.canonicalSkeletonId,
    canonicalBindPoseId: ARCHETYPES.canonicalBindPoseId,
    posePacks: POSE_PACKS.posePacks.map((pack) => pack.id),
    exportProfiles: Object.keys(EXPORT_PROFILES.profiles),
    resourceCount: Object.keys(RESOURCE_FILES).length,
    repositoryRoot: REPO_ROOT,
  };
}
