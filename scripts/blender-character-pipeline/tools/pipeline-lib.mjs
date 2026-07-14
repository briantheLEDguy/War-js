import { execFile } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  statSync,
  unlinkSync,
} from "node:fs";
import path from "node:path";
import {
  APPROVED_ASSET_DIR,
  ASSET_INDEX_PATH,
  BLUEPRINT_DIR,
  JOB_ROOT,
  MODEL_DIR,
  PIPELINE_ROOT,
  REPO_ROOT,
  TOOL_DIR,
  assertPathWithin,
  readJson,
  repoRelative,
  resolveRepoPath,
  workflowError,
  writeJsonAtomic,
} from "./workspace-paths.mjs";
import { modelJobStore } from "./model-jobs.mjs";
import { validateJsonSchema } from "./json-schema-validator.mjs";
import { classifyWearable, socketFor } from "../pipeline-tools/character-contract.mjs";

export {
  APPROVED_ASSET_DIR,
  ASSET_INDEX_PATH,
  BLUEPRINT_DIR,
  JOB_ROOT,
  MODEL_DIR,
  PIPELINE_ROOT,
  REPO_ROOT,
  TOOL_DIR as __dirname,
  assertPathWithin,
  readJson,
  repoRelative,
  resolveRepoPath,
};

export const GENERATOR_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_asset_from_manifest.py");
export const REVIEW_RENDER_SCRIPT = path.join(PIPELINE_ROOT, "blender", "render_model_review.py");
export const CONFIG_PATH = path.join(PIPELINE_ROOT, "config.json");
export const BLUEPRINT_SCHEMA_PATH = path.join(PIPELINE_ROOT, "data", "asset-blueprint.schema.json");
export const COMPATIBILITY_ALLOWLIST_PATH = path.join(PIPELINE_ROOT, "data", "runtime-compatibility-allowlist.json");

export const FORBIDDEN_GENERATED_TERMS = [
  ["war", "rior", " pr", "iest"].join(""),
  ["bright", " wizard"].join(""),
  ["witch", " hunter"].join(""),
  ["knight", " of the blazing sun"].join(""),
  ["sig", "mar"].join(""),
  ["sig", "marite"].join(""),
  ["reik", "guard"].join(""),
  ["karl", " franz"].join(""),
  ["war", "hammer"].join(""),
  ["alt", "dorf"].join(""),
  ["emp", "ire_"].join(""),
  ["war", "career"].join(""),
  ["war", "kit"].join(""),
  ["war", "slot"].join(""),
];

export const SUPPORTED_GENERATOR_KINDS = new Set([
  "staticPreset",
  "weaponModule",
  "jewelModule",
  "copyExisting",
  "externalImport",
  "mpfbBody",
  "localModularSet",
]);

export const RETIRED_GENERATOR_KINDS = new Set(["characterPreset", "armorModule", "bodyModule"]);
const TRANSITIONAL_GENERATOR_KINDS = new Set([...SUPPORTED_GENERATOR_KINDS, ...RETIRED_GENERATOR_KINDS]);
const REVIEWED_CATEGORIES = new Set(["character", "body", "armor"]);
const REQUIRED_PBR_CHANNELS = ["baseColor", "roughness", "metallic", "normal"];

export function sha256File(filePath) {
  const safePath = assertPathWithin(REPO_ROOT, filePath, "hash input");
  return createHash("sha256").update(readFileSync(safePath)).digest("hex");
}

export function sha256Json(value) {
  return createHash("sha256").update(`${JSON.stringify(value)}\n`).digest("hex");
}

export function readConfig() {
  if (!existsSync(CONFIG_PATH)) throw new Error(`Missing pipeline config: ${CONFIG_PATH}`);
  const config = readJson(CONFIG_PATH);
  if (process.env.BLENDER_PATH) return { ...config, blenderPath: process.env.BLENDER_PATH };
  if (process.platform === "win32" && (!config.blenderPath || config.blenderPath === "blender")) {
    const candidates = [
      "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe",
      "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
    ];
    const installed = candidates.find((candidate) => existsSync(candidate));
    if (installed) return { ...config, blenderPath: installed };
  }
  return config;
}

export function listBlueprintFiles() {
  if (!existsSync(BLUEPRINT_DIR)) return [];
  return readdirSync(BLUEPRINT_DIR)
    .filter((file) => file.endsWith(".asset.json"))
    .map((file) => path.join(BLUEPRINT_DIR, file))
    .sort((a, b) => a.localeCompare(b, "en"));
}

export function loadBlueprints() {
  return listBlueprintFiles().map((filePath) => ({ filePath, blueprint: readJson(filePath) }));
}

export function findBlueprint(ref) {
  const normalized = String(ref ?? "").toLowerCase();
  const match = loadBlueprints().find(({ filePath, blueprint }) => (
    blueprint.assetId?.toLowerCase() === normalized
    || path.basename(filePath).toLowerCase() === normalized
    || blueprint.output?.model?.toLowerCase() === normalized
    || blueprint.runtime?.profileKey?.toLowerCase() === normalized
    || blueprint.runtime?.itemKey?.toLowerCase() === normalized
    || blueprint.runtime?.staticKey?.toLowerCase() === normalized
  ));
  if (!match) throw workflowError("BLUEPRINT_NOT_FOUND", `Unknown asset blueprint: ${ref}`);
  return match;
}

export function outputPathFor(blueprint) {
  return assertPathWithin(MODEL_DIR, path.join(MODEL_DIR, blueprint.output.model), "model output");
}

export function artifactDirFor(blueprint) {
  const configured = blueprint.output?.artifactDir;
  if (!configured) return null;
  const resolved = path.isAbsolute(configured) ? configured : path.join(REPO_ROOT, configured);
  return assertPathWithin(REPO_ROOT, resolved, "artifact directory");
}

function required(value, name, errors) {
  if (value === undefined || value === null) errors.push(`${name} is required`);
}

function validateLifecycle(lifecycle, errors, strict) {
  if (!lifecycle) {
    if (strict) errors.push("lifecycle is required in strict mode");
    return;
  }
  if (!["draft", "qc_passed", "review_pending", "approved", "rejected", "blocked", "promoted"].includes(lifecycle.status)) {
    errors.push(`unsupported lifecycle.status: ${lifecycle.status}`);
  }
  if (lifecycle.status === "approved" || lifecycle.status === "promoted") {
    if (!lifecycle.reviewedBy) errors.push("approved lifecycle requires reviewedBy");
    if (!lifecycle.reviewedAt) errors.push("approved lifecycle requires reviewedAt");
  }
}

export function validateBlueprintRecord(filePath, blueprint, options = {}) {
  const strict = options.strict === true;
  const compatibilityAllowed = options.compatibilityAllowed === true;
  const errors = validateJsonSchema(readJson(BLUEPRINT_SCHEMA_PATH), blueprint).map((error) => `schema: ${error}`);
  for (const field of ["assetId", "displayName", "category", "version", "output", "geometry", "materials", "provenance", "qc"]) {
    required(blueprint[field], field, errors);
  }

  if (blueprint.assetId && !/^(chr|body|arm|wep|jwl|prop|terrain)\.[a-z0-9_.-]+$/.test(blueprint.assetId)) {
    errors.push(`assetId has invalid format: ${blueprint.assetId}`);
  }
  if (blueprint.output?.model && !/^[a-z0-9_.-]+\.glb$/.test(blueprint.output.model)) {
    errors.push(`output.model must be a neutral lowercase .glb filename: ${blueprint.output.model}`);
  }
  if (blueprint.version && !/^[0-9]+\.[0-9]+\.[0-9]+$/.test(blueprint.version)) {
    errors.push(`version must be semver-like x.y.z: ${blueprint.version}`);
  }
  if (!["character", "body", "armor", "weapon", "jewel", "prop", "terrain"].includes(blueprint.category)) {
    errors.push(`unsupported category: ${blueprint.category}`);
  }
  if (blueprint.geometry?.upAxis !== "+Y") errors.push("geometry.upAxis must be +Y");
  if (blueprint.geometry?.forwardAxis !== "+Z") errors.push("geometry.forwardAxis must be +Z");
  if (!Array.isArray(blueprint.geometry?.lods) || blueprint.geometry.lods.length === 0) {
    errors.push("geometry.lods must contain at least one LOD");
  }
  if (!Array.isArray(blueprint.materials?.channels) || blueprint.materials.channels.length === 0) {
    errors.push("materials.channels must contain at least one channel");
  }
  if (strict && REVIEWED_CATEGORIES.has(blueprint.category)) {
    for (const channel of REQUIRED_PBR_CHANNELS) {
      if (!blueprint.materials?.channels?.includes(channel)) errors.push(`materials.channels is missing required PBR channel ${channel}`);
    }
    if (blueprint.rigging?.maxInfluences > 4) errors.push("rigging.maxInfluences must be at most 4");
    if (blueprint.geometry?.skeletonId && blueprint.geometry.skeletonId !== "humanoid_game_v2") {
      errors.push(`reviewed humanoids must use skeletonId humanoid_game_v2, received ${blueprint.geometry.skeletonId}`);
    }
  }
  if (!blueprint.provenance || typeof blueprint.provenance.aiAssisted !== "boolean") {
    errors.push("provenance.aiAssisted must be boolean");
  }
  if (!Array.isArray(blueprint.provenance?.aiStages)) errors.push("provenance.aiStages must be an array");
  if (!["not_required", "pending", "passed", "failed"].includes(blueprint.provenance?.similarityReview)) {
    errors.push("provenance.similarityReview must be not_required, pending, passed, or failed");
  }
  if (typeof blueprint.qc?.allowNonManifold !== "boolean") errors.push("qc.allowNonManifold must be boolean");
  if (typeof blueprint.qc?.allowUvOverlap !== "boolean") errors.push("qc.allowUvOverlap must be boolean");
  if (!Number.isFinite(blueprint.qc?.maxFileSizeMb)) errors.push("qc.maxFileSizeMb must be a number");
  if (!Number.isInteger(blueprint.qc?.maxDrawCalls)) errors.push("qc.maxDrawCalls must be an integer");
  if (blueprint.qc?.maxMeshObjects !== undefined && !Number.isInteger(blueprint.qc.maxMeshObjects)) {
    errors.push("qc.maxMeshObjects must be an integer when provided");
  }
  if (blueprint.qc?.maxTris !== undefined && !Number.isInteger(blueprint.qc.maxTris)) {
    errors.push("qc.maxTris must be an integer when provided");
  }
  if (blueprint.qc?.requiresSkinnedMeshes !== undefined && typeof blueprint.qc.requiresSkinnedMeshes !== "boolean") {
    errors.push("qc.requiresSkinnedMeshes must be boolean when provided");
  }
  if (blueprint.qc?.requiresPreview !== undefined && typeof blueprint.qc.requiresPreview !== "boolean") {
    errors.push("qc.requiresPreview must be boolean when provided");
  }

  if (blueprint.modular) {
    try {
      const classification = classifyWearable({
        slot: blueprint.modular.slot,
        kind: blueprint.modular.kind,
        method: blueprint.modular.fitMethod,
      });
      if (classification.kind === "rigid" && !blueprint.modular.socketId) errors.push("modular rigid assets require socketId");
      if (classification.kind === "rigid" && blueprint.modular.socketId) {
        const socket = socketFor(blueprint.modular.socketId);
        if (!classification.socketIds.includes(socket.name)) errors.push(`modular slot ${classification.slot} cannot use ${socket.name}`);
      }
      if (classification.kind === "skinned" && !blueprint.modular.fitMethod) errors.push("modular skinned assets require fitMethod");
      if (classification.kind === "loose" && !blueprint.modular.fitMethod) errors.push("modular loose assets require fitMethod");
    } catch (error) {
      errors.push(`modular contract: ${error.message}`);
    }
  }

  const generatorKind = blueprint.generator?.kind;
  if (generatorKind && !TRANSITIONAL_GENERATOR_KINDS.has(generatorKind)) {
    errors.push(`unsupported generator.kind: ${generatorKind}`);
  }
  if (strict && RETIRED_GENERATOR_KINDS.has(generatorKind)) {
    errors.push(`retired primitive generator.kind is forbidden in strict mode: ${generatorKind}`);
  }
  if (generatorKind === "externalImport") {
    if (!blueprint.generator?.source) errors.push("externalImport requires generator.source");
    if (!blueprint.generator?.sourceType) errors.push("externalImport requires generator.sourceType");
    if (strict && !compatibilityAllowed) {
      if (!blueprint.provenance?.sourceSha256) errors.push("externalImport provenance requires sourceSha256 in strict mode");
      if (!blueprint.provenance?.license?.name) errors.push("externalImport provenance requires license.name in strict mode");
      if (!blueprint.provenance?.license?.sourceUrl) errors.push("externalImport provenance requires license.sourceUrl in strict mode");
      if (!blueprint.provenance?.author) errors.push("externalImport provenance requires author in strict mode");
    }
  }
  validateLifecycle(blueprint.lifecycle, errors, false);

  const generatedStrings = [
    blueprint.assetId,
    blueprint.displayName,
    blueprint.output?.model,
    blueprint.materials?.master,
    blueprint.materials?.textureSet,
    blueprint.runtime?.profileKey,
    blueprint.runtime?.bodyModel,
    ...(blueprint.sets ?? []),
  ].filter(Boolean);
  for (const value of generatedStrings) {
    const lower = String(value).toLowerCase();
    for (const term of FORBIDDEN_GENERATED_TERMS) {
      if (lower.includes(term)) errors.push(`generated semantic field contains forbidden term "${term}": ${value}`);
    }
  }

  return { ok: errors.length === 0, filePath, assetId: blueprint.assetId ?? path.basename(filePath), errors };
}

function previewPath(value) {
  if (path.isAbsolute(value)) return assertPathWithin(REPO_ROOT, value, "preview image");
  if (/^(artifacts|public|scripts|src)[/\\]/.test(value)) return resolveRepoPath(value, "preview image");
  return assertPathWithin(MODEL_DIR, path.join(MODEL_DIR, value), "preview image");
}

function expectedModelHash(qc) {
  return qc?.modelSha256 ?? qc?.output?.sha256 ?? qc?.hashes?.model ?? qc?.contentHashes?.model ?? null;
}

export function validateQcForBlueprint(blueprint, outPath, qcPath, strict, compatibilityAllowed = false) {
  const errors = [];
  if (!existsSync(qcPath)) {
    errors.push(`generated model is missing QC sidecar: ${qcPath}`);
    return errors;
  }
  const qc = readJson(qcPath);
  if (qc.assetId && qc.assetId !== blueprint.assetId) errors.push(`QC assetId ${qc.assetId} does not match blueprint ${blueprint.assetId}`);
  if (qc.model && qc.model !== blueprint.output.model) errors.push(`QC model ${qc.model} does not match blueprint output ${blueprint.output.model}`);
  if (qc.qcPassed !== true) errors.push(`QC sidecar must report qcPassed: true: ${qcPath}`);
  if (strict && !compatibilityAllowed && Number.isFinite(blueprint.qc?.maxTris) && qc.totalTris > blueprint.qc.maxTris) {
    errors.push(`QC triangle count ${qc.totalTris} exceeds ${blueprint.qc.maxTris}`);
  }
  if (strict && !compatibilityAllowed && Number.isFinite(blueprint.qc?.maxDrawCalls) && qc.meshCount > blueprint.qc.maxDrawCalls) {
    errors.push(`QC draw-call proxy ${qc.meshCount} exceeds ${blueprint.qc.maxDrawCalls}`);
  }
  if (strict && !compatibilityAllowed && blueprint.rigging?.requiredClips?.length && qc.missingRequiredClips?.length) {
    errors.push(`QC is missing required clips: ${qc.missingRequiredClips.join(", ")}`);
  }
  if (strict && !compatibilityAllowed && blueprint.geometry?.lods?.length > 1) {
    const builtLods = new Set((qc.builtLods ?? []).map((entry) => typeof entry === "string" ? entry : entry.name));
    for (const lod of blueprint.geometry.lods) {
      if (!builtLods.has(lod.name)) errors.push(`declared LOD was not built: ${lod.name}`);
    }
  }
  if (strict && !compatibilityAllowed) {
    if (REVIEWED_CATEGORIES.has(blueprint.category)) {
      const observedSkeleton = qc.skeletonId ?? qc.geometry?.skeletonId;
      if (observedSkeleton !== "humanoid_game_v2") errors.push("QC does not prove the humanoid_game_v2 skeleton");
      if (!Number.isInteger(qc.maxInfluencesObserved)) errors.push("QC is missing maxInfluencesObserved");
      else if (qc.maxInfluencesObserved > 4) errors.push(`QC observed ${qc.maxInfluencesObserved} bone influences; maximum is 4`);
      const pbrChannels = qc.pbrChannels ?? qc.materialChannels ?? [];
      for (const channel of REQUIRED_PBR_CHANNELS) {
        if (!pbrChannels.includes(channel)) errors.push(`QC does not prove PBR channel ${channel}`);
      }
      if (qc.maxTextureResolution > 2048) errors.push(`QC texture resolution ${qc.maxTextureResolution} exceeds 2048`);
    }
    if (blueprint.qc?.allowNonManifold === false && !Number.isInteger(qc.nonManifoldEdges)) {
      errors.push("QC is missing nonManifoldEdges");
    } else if (blueprint.qc?.allowNonManifold === false && qc.nonManifoldEdges > 0) {
      errors.push(`QC reports ${qc.nonManifoldEdges} non-manifold edges`);
    }
    const hash = expectedModelHash(qc);
    if (!hash) errors.push("QC sidecar is missing modelSha256");
    else if (hash !== sha256File(outPath)) errors.push("QC modelSha256 is stale or does not match the GLB");
  }
  const requiresPreview = blueprint.qc?.requiresPreview === true || (strict && REVIEWED_CATEGORIES.has(blueprint.category));
  if (requiresPreview) {
    if (!Array.isArray(qc.previewImages) || qc.previewImages.length === 0) {
      errors.push("QC sidecar has no preview images for a preview-required asset");
    } else if (strict) {
      for (const preview of qc.previewImages) {
        try {
          const resolved = previewPath(preview);
          if (!existsSync(resolved)) errors.push(`QC preview image is missing: ${preview}`);
        } catch (error) {
          errors.push(error.message);
        }
      }
    }
  }
  return errors;
}

export function validateGeneratedQc(options = {}) {
  const strict = options.strict === true;
  const allowedModels = new Set(readCompatibilityAllowlist().assets.map((asset) => asset.model));
  const results = [];
  for (const { blueprint } of loadBlueprints()) {
    const outPath = outputPathFor(blueprint);
    if (!existsSync(outPath)) continue;
    const qcPath = outPath.replace(/\.glb$/i, ".qc.json");
    const errors = validateQcForBlueprint(blueprint, outPath, qcPath, strict, allowedModels.has(blueprint.output.model));
    results.push({ ok: errors.length === 0, filePath: qcPath, assetId: `generated-qc:${blueprint.assetId}`, errors });
  }
  return results;
}

export function readCompatibilityAllowlist() {
  if (!existsSync(COMPATIBILITY_ALLOWLIST_PATH)) return { assets: [] };
  const value = readJson(COMPATIBILITY_ALLOWLIST_PATH);
  return { ...value, assets: Array.isArray(value.assets) ? value.assets : [] };
}

function indexEntries(index) {
  const entries = [];
  for (const section of ["characterProfiles", "baseBodies", "staticProps"]) {
    for (const [key, entry] of Object.entries(index[section] ?? {})) entries.push({ section, key, entry });
  }
  for (const [key, entry] of Object.entries(index.equipment ?? {})) {
    if (entry?.variants && typeof entry.variants === "object") {
      for (const [variant, variantEntry] of Object.entries(entry.variants)) {
        entries.push({ section: "equipment", key: `${key}:${variant}`, entry: variantEntry });
      }
    } else {
      entries.push({ section: "equipment", key, entry });
    }
  }
  return entries;
}

export function validateAssetIndex(options = {}) {
  const strict = options.strict === true;
  if (!existsSync(ASSET_INDEX_PATH)) return [];
  const index = readJson(ASSET_INDEX_PATH);
  const blueprints = loadBlueprints().map(({ blueprint }) => blueprint);
  const approvedManifests = existsSync(APPROVED_ASSET_DIR)
    ? readdirSync(APPROVED_ASSET_DIR)
      .filter((file) => file.endsWith(".approved.json"))
      .map((file) => readJson(path.join(APPROVED_ASSET_DIR, file)))
    : [];
  const byAssetId = new Map([
    ...blueprints.map((blueprint) => [blueprint.assetId, blueprint]),
    ...approvedManifests.map((manifest) => [manifest.assetId, manifest]),
  ]);
  const allowedModels = new Set(readCompatibilityAllowlist().assets.map((asset) => asset.model));
  const results = [];

  for (const { section, key, entry } of indexEntries(index)) {
    const errors = [];
    const compatibilityAllowed = allowedModels.has(entry.model);
    const sourceRecord = entry.assetId ? byAssetId.get(entry.assetId) : null;
    if (entry.assetId && !sourceRecord && !compatibilityAllowed) errors.push(`asset-index references unknown assetId ${entry.assetId}`);
    const expectedModel = sourceRecord?.output?.model ?? sourceRecord?.model;
    if (expectedModel && entry.model !== expectedModel) {
      errors.push(`asset-index model ${entry.model} does not match approved/blueprint output ${expectedModel}`);
    }
    if (!entry.model) errors.push("asset-index entry is missing model");

    let modelPath = null;
    if (entry.model) {
      try {
        modelPath = assertPathWithin(MODEL_DIR, path.join(MODEL_DIR, entry.model), "indexed model");
      } catch (error) {
        errors.push(error.message);
      }
    }
    if (strict && modelPath && !existsSync(modelPath)) errors.push(`indexed model file is missing: ${entry.model}`);
    if (entry.bodyModel) {
      try {
        const bodyPath = assertPathWithin(MODEL_DIR, path.join(MODEL_DIR, entry.bodyModel), "indexed body model");
        if (strict && !existsSync(bodyPath)) errors.push(`indexed bodyModel file is missing: ${entry.bodyModel}`);
      } catch (error) {
        errors.push(error.message);
      }
    }
    if (entry.runtimeReady === false && !entry.reviewStatus) errors.push("asset-index entries blocked from runtime must include reviewStatus");

    if (strict && !compatibilityAllowed) {
      if (entry.runtimeReady !== true) errors.push("strict runtime entry must set runtimeReady: true");
      if (!["approved", "promoted"].includes(entry.approvalState ?? entry.lifecycleStatus)) {
        errors.push("strict runtime entry is not approved");
      }
      if (!["approved", "promoted"].includes(entry.reviewStatus)) errors.push("strict runtime entry has no approved reviewStatus");
      if (modelPath && existsSync(modelPath)) {
        const actualModelHash = sha256File(modelPath);
        if (!entry.modelSha256) errors.push("strict runtime entry is missing modelSha256");
        else if (entry.modelSha256 !== actualModelHash) errors.push("runtime modelSha256 does not match the indexed GLB");
        try {
          const qcPath = assertPathWithin(MODEL_DIR, path.join(MODEL_DIR, entry.qc ?? entry.model.replace(/\.glb$/i, ".qc.json")), "indexed QC");
          if (!existsSync(qcPath)) {
            errors.push(`indexed QC file is missing: ${path.basename(qcPath)}`);
          } else {
            const qcHash = sha256File(qcPath);
            const qc = readJson(qcPath);
            if (!entry.qcSha256) errors.push("strict runtime entry is missing qcSha256");
            else if (entry.qcSha256 !== qcHash) errors.push("runtime qcSha256 does not match the indexed QC file");
            if (expectedModelHash(qc) !== actualModelHash) errors.push("indexed QC contains a stale model hash");
            const bypassedTechnicalQc = sourceRecord?.provenance?.bypassApproval === true && qc.technicalRoundTripPassed === true;
            if (qc.qcPassed !== true && !bypassedTechnicalQc) errors.push("indexed QC did not pass");
          }
        } catch (error) {
          errors.push(error.message);
        }
      }
      const previews = entry.previews && typeof entry.previews === "object" ? Object.entries(entry.previews) : [];
      if (previews.length === 0) errors.push("strict runtime entry is missing review previews");
      for (const [view, preview] of previews) {
        try {
          const previewFile = previewPath(preview);
          if (!existsSync(previewFile)) {
            errors.push(`runtime review preview is missing: ${preview}`);
          } else if (!entry.previewSha256?.[view]) {
            errors.push(`strict runtime entry is missing previewSha256 for ${view}`);
          } else if (entry.previewSha256[view] !== sha256File(previewFile)) {
            errors.push(`runtime previewSha256 does not match ${view}`);
          }
        } catch (error) {
          errors.push(error.message);
        }
      }
    }
    results.push({ ok: errors.length === 0, filePath: ASSET_INDEX_PATH, assetId: `asset-index:${section}:${key}`, errors });
  }
  return results;
}

export function validateBlueprints(options = {}) {
  const strict = options.strict === true;
  const allowedModels = new Set(readCompatibilityAllowlist().assets.map((asset) => asset.model));
  const refs = options.refs ? new Set(options.refs.map(String)) : null;
  const seenAssetIds = new Set();
  const seenOutputs = new Set();
  const results = loadBlueprints().map(({ filePath, blueprint }) => {
    const result = validateBlueprintRecord(filePath, blueprint, {
      strict,
      compatibilityAllowed: allowedModels.has(blueprint.output?.model),
    });
    if (blueprint.assetId) {
      if (seenAssetIds.has(blueprint.assetId)) result.errors.push(`duplicate assetId: ${blueprint.assetId}`);
      seenAssetIds.add(blueprint.assetId);
    }
    if (blueprint.output?.model) {
      if (seenOutputs.has(blueprint.output.model)) result.errors.push(`duplicate output.model: ${blueprint.output.model}`);
      seenOutputs.add(blueprint.output.model);
    }
    result.ok = result.errors.length === 0;
    return result;
  });
  if (existsSync(ASSET_INDEX_PATH)) results.push(...validateAssetIndex({ strict }));
  results.push(...validateGeneratedQc({ strict }));
  if (!refs) return results;
  const filtered = results.filter((result) => refs.has(result.assetId) || [...refs].some((ref) => result.assetId.includes(ref)));
  for (const ref of refs) {
    if (!filtered.some((result) => result.assetId === ref || result.assetId.includes(ref))) {
      filtered.push({
        ok: false,
        filePath: BLUEPRINT_DIR,
        assetId: `validation-ref:${ref}`,
        errors: [`No blueprint or runtime index record matched ${ref}`],
      });
    }
  }
  return filtered;
}

export function listGeneratedAssets() {
  return loadBlueprints().map(({ filePath, blueprint }) => {
    const outPath = outputPathFor(blueprint);
    const qcPath = outPath.replace(/\.glb$/i, ".qc.json");
    return {
      filePath,
      assetId: blueprint.assetId,
      category: blueprint.category,
      model: blueprint.output.model,
      generated: existsSync(outPath),
      sizeMb: existsSync(outPath) ? statSync(outPath).size / (1024 * 1024) : null,
      qc: existsSync(qcPath),
      qcPassed: existsSync(qcPath) ? readJson(qcPath).qcPassed === true : null,
    };
  });
}

function cleanupFile(filePath) {
  if (existsSync(filePath)) unlinkSync(filePath);
}

/**
 * Publishes a set of files as one transaction. Existing files are moved to the
 * transaction backup first and restored if any later rename fails.
 */
export function atomicPublishSet(entries, options = {}) {
  if (!Array.isArray(entries) || entries.length === 0) throw workflowError("EMPTY_PUBLISH_SET", "No files were supplied for promotion.");
  mkdirSync(JOB_ROOT, { recursive: true });
  const transactionDir = assertPathWithin(
    JOB_ROOT,
    options.transactionDir ?? path.join(JOB_ROOT, "transactions", `publish_${randomUUID()}`),
    "publish transaction directory",
  );
  mkdirSync(path.join(transactionDir, "backups"), { recursive: true });
  const prepared = entries.map((entry, index) => {
    const source = assertPathWithin(REPO_ROOT, path.resolve(entry.source), "publish source");
    const destination = assertPathWithin(REPO_ROOT, path.resolve(entry.destination), "publish destination");
    if (!existsSync(source) || !statSync(source).isFile()) {
      throw workflowError("PUBLISH_SOURCE_MISSING", `Publish source does not exist: ${source}`);
    }
    if (entry.sha256 && sha256File(source) !== entry.sha256) {
      throw workflowError("PUBLISH_HASH_MISMATCH", `Publish source hash changed: ${source}`);
    }
    mkdirSync(path.dirname(destination), { recursive: true });
    const temporary = `${destination}.${path.basename(transactionDir)}.new`;
    const backup = path.join(transactionDir, "backups", `${String(index).padStart(4, "0")}_${path.basename(destination)}`);
    cleanupFile(temporary);
    copyFileSync(source, temporary);
    return { source, destination, temporary, backup, hadExisting: existsSync(destination), published: false };
  });

  try {
    for (const item of prepared) {
      if (item.hadExisting) renameSync(item.destination, item.backup);
      renameSync(item.temporary, item.destination);
      item.published = true;
    }
    return prepared.map((item) => ({ path: item.destination, replaced: item.hadExisting }));
  } catch (error) {
    for (const item of [...prepared].reverse()) {
      try {
        if (item.published && existsSync(item.destination)) unlinkSync(item.destination);
        if (item.hadExisting && existsSync(item.backup)) renameSync(item.backup, item.destination);
        cleanupFile(item.temporary);
      } catch {
        // Continue attempting every rollback; the original failure remains primary.
      }
    }
    throw workflowError("ATOMIC_PUBLISH_FAILED", `Atomic publish failed and was rolled back: ${error.message}`, { cause: error.message });
  }
}

function execFilePromise(executable, args, options) {
  return new Promise((resolve, reject) => {
    execFile(executable, args, options, (error, stdout, stderr) => {
      if (error) {
        error.details = { stderr: String(stderr ?? "").slice(-8000) };
        reject(error);
      } else resolve({ stdout: String(stdout ?? ""), stderr: String(stderr ?? "") });
    });
  });
}

function filesRecursive(directory) {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const child = path.join(directory, entry.name);
    return entry.isDirectory() ? filesRecursive(child) : [child];
  }).sort((a, b) => a.localeCompare(b, "en"));
}

export async function runBlenderForBlueprint(ref, options = {}) {
  const { filePath, blueprint } = findBlueprint(ref);
  if (RETIRED_GENERATOR_KINDS.has(blueprint.generator?.kind)) {
    throw workflowError(
      "RETIRED_PRIMITIVE_GENERATOR",
      `${blueprint.generator.kind} is retired. Use MPFB/local authored bodies or an externalImport candidate.`,
    );
  }
  const config = readConfig();
  const blenderPath = config.blenderPath ?? "blender";
  if (path.isAbsolute(blenderPath) && !existsSync(blenderPath)) {
    throw workflowError("BLENDER_NOT_FOUND", `Blender not found at ${blenderPath}. Update ${CONFIG_PATH}.`);
  }
  if (!existsSync(GENERATOR_SCRIPT)) throw workflowError("GENERATOR_NOT_FOUND", `Missing generator entrypoint: ${GENERATOR_SCRIPT}`);

  const standaloneId = `standalone_${randomUUID()}`;
  const jobDir = options.jobDir
    ? assertPathWithin(JOB_ROOT, options.jobDir, "generation job directory")
    : assertPathWithin(JOB_ROOT, path.join(JOB_ROOT, standaloneId), "generation job directory");
  const stagingDir = path.join(jobDir, "staging", "generation");
  const stageArtifactDir = path.join(jobDir, "artifacts", "generated-previews");
  mkdirSync(stagingDir, { recursive: true });
  mkdirSync(stageArtifactDir, { recursive: true });
  const stagedModel = path.join(stagingDir, blueprint.output.model);
  const stagedQc = stagedModel.replace(/\.glb$/i, ".qc.json");
  const release = options.skipLock
    ? () => {}
    : await modelJobStore.acquireLocks(standaloneId, [blueprint.assetId]);

  try {
    const args = [
      "--background",
      "--python", GENERATOR_SCRIPT,
      "--",
      "--manifest", filePath,
      "--output", stagedModel,
      "--artifact-dir", stageArtifactDir,
    ];
    const { stdout, stderr } = await execFilePromise(blenderPath, args, {
      cwd: PIPELINE_ROOT,
      timeout: options.timeout ?? 600_000,
      maxBuffer: 32 * 1024 * 1024,
      signal: options.signal,
      windowsHide: true,
    });
    if (!existsSync(stagedModel)) throw workflowError("GENERATION_OUTPUT_MISSING", `Generation finished without creating ${stagedModel}`);
    if (!existsSync(stagedQc)) throw workflowError("GENERATION_QC_MISSING", `Generation finished without creating ${stagedQc}`);

    const finalModel = outputPathFor(blueprint);
    const finalQc = finalModel.replace(/\.glb$/i, ".qc.json");
    const finalArtifactDir = artifactDirFor(blueprint);
    const qc = readJson(stagedQc);
    qc.modelSha256 = sha256File(stagedModel);
    qc.generatedAt = new Date().toISOString();
    const previewFiles = filesRecursive(stageArtifactDir);
    if (finalArtifactDir) {
      qc.previewImages = previewFiles
        .filter((value) => /\.(png|jpe?g|webp)$/i.test(value))
        .map((value) => repoRelative(path.join(finalArtifactDir, path.relative(stageArtifactDir, value))));
    }
    writeJsonAtomic(stagedQc, qc);
    const qcErrors = validateQcForBlueprint(blueprint, stagedModel, stagedQc, false);
    if (qcErrors.length) throw workflowError("GENERATION_QC_FAILED", `Generated asset failed QC: ${qcErrors.join("; ")}`, { errors: qcErrors });

    const publish = [
      { source: stagedModel, destination: finalModel, sha256: qc.modelSha256 },
      { source: stagedQc, destination: finalQc, sha256: sha256File(stagedQc) },
    ];
    if (finalArtifactDir) {
      for (const source of previewFiles) {
        publish.push({ source, destination: path.join(finalArtifactDir, path.relative(stageArtifactDir, source)), sha256: sha256File(source) });
      }
    }
    atomicPublishSet(publish, { transactionDir: path.join(jobDir, "publish") });
    return { blueprint, outPath: finalModel, qcPath: finalQc, jobDir, stdout, stderr };
  } finally {
    release();
  }
}
