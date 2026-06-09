import { execFile } from "child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

export const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PIPELINE_ROOT = path.resolve(__dirname, "..");
export const REPO_ROOT = path.resolve(PIPELINE_ROOT, "..", "..");
export const BLUEPRINT_DIR = path.join(PIPELINE_ROOT, "data", "asset-blueprints");
export const MODEL_DIR = path.join(REPO_ROOT, "public", "assets", "models");
export const ASSET_INDEX_PATH = path.join(MODEL_DIR, "asset-index.json");
export const GENERATOR_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_asset_from_manifest.py");
export const CONFIG_PATH = path.join(PIPELINE_ROOT, "config.json");

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
  ["war", "slot"].join("")
];

export function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

export function readConfig() {
  if (!existsSync(CONFIG_PATH)) {
    throw new Error(`Missing pipeline config: ${CONFIG_PATH}`);
  }
  return readJson(CONFIG_PATH);
}

export function listBlueprintFiles() {
  if (!existsSync(BLUEPRINT_DIR)) return [];
  return readdirSync(BLUEPRINT_DIR)
    .filter((file) => file.endsWith(".asset.json"))
    .map((file) => path.join(BLUEPRINT_DIR, file))
    .sort();
}

export function loadBlueprints() {
  return listBlueprintFiles().map((filePath) => {
    const blueprint = readJson(filePath);
    return { filePath, blueprint };
  });
}

export function findBlueprint(ref) {
  const all = loadBlueprints();
  const normalized = ref?.toLowerCase();
  const match = all.find(({ filePath, blueprint }) => {
    return (
      blueprint.assetId?.toLowerCase() === normalized ||
      path.basename(filePath).toLowerCase() === normalized ||
      blueprint.output?.model?.toLowerCase() === normalized ||
      blueprint.runtime?.profileKey?.toLowerCase() === normalized ||
      blueprint.runtime?.itemKey?.toLowerCase() === normalized ||
      blueprint.runtime?.staticKey?.toLowerCase() === normalized
    );
  });
  if (!match) {
    throw new Error(`Unknown asset blueprint: ${ref}`);
  }
  return match;
}

export function outputPathFor(blueprint) {
  return path.join(MODEL_DIR, blueprint.output.model);
}

export function artifactDirFor(blueprint) {
  const configured = blueprint.output?.artifactDir;
  if (!configured) return null;
  return path.isAbsolute(configured) ? configured : path.join(REPO_ROOT, configured);
}

export function validateBlueprintRecord(filePath, blueprint) {
  const errors = [];
  const requireField = (name) => {
    if (blueprint[name] === undefined || blueprint[name] === null) {
      errors.push(`${name} is required`);
    }
  };
  for (const field of ["assetId", "displayName", "category", "version", "output", "geometry", "materials", "provenance", "qc"]) {
    requireField(field);
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
  if (!blueprint.provenance || typeof blueprint.provenance.aiAssisted !== "boolean") {
    errors.push("provenance.aiAssisted must be boolean");
  }
  if (!Array.isArray(blueprint.provenance?.aiStages)) {
    errors.push("provenance.aiStages must be an array");
  }
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
  if (blueprint.qc?.requiresSkinnedMeshes !== undefined && typeof blueprint.qc.requiresSkinnedMeshes !== "boolean") {
    errors.push("qc.requiresSkinnedMeshes must be boolean when provided");
  }
  if (blueprint.qc?.requiresPreview !== undefined && typeof blueprint.qc.requiresPreview !== "boolean") {
    errors.push("qc.requiresPreview must be boolean when provided");
  }

  const generatedStrings = [
    blueprint.assetId,
    blueprint.displayName,
    blueprint.output?.model,
    blueprint.materials?.master,
    blueprint.materials?.textureSet,
    blueprint.runtime?.profileKey,
    blueprint.runtime?.bodyModel,
    ...(blueprint.sets ?? [])
  ].filter(Boolean);
  for (const value of generatedStrings) {
    const lower = String(value).toLowerCase();
    for (const term of FORBIDDEN_GENERATED_TERMS) {
      if (lower.includes(term)) {
        errors.push(`generated semantic field contains forbidden term "${term}": ${value}`);
      }
    }
  }

  if (blueprint.generator) {
    const allowed = ["characterPreset", "staticPreset", "armorModule", "bodyModule", "weaponModule", "jewelModule", "copyExisting"];
    if (!allowed.includes(blueprint.generator.kind)) {
      errors.push(`unsupported generator.kind: ${blueprint.generator.kind}`);
    }
  }

  return {
    ok: errors.length === 0,
    filePath,
    assetId: blueprint.assetId ?? path.basename(filePath),
    errors
  };
}

export function validateBlueprints() {
  const seenAssetIds = new Set();
  const seenOutputs = new Set();
  const results = loadBlueprints().map(({ filePath, blueprint }) => {
    const result = validateBlueprintRecord(filePath, blueprint);
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

  if (existsSync(ASSET_INDEX_PATH)) {
    results.push(...validateAssetIndex());
  }
  results.push(...validateGeneratedQc());

  return results;
}

export function validateGeneratedQc() {
  const results = [];
  for (const { blueprint } of loadBlueprints()) {
    const outPath = outputPathFor(blueprint);
    const qcPath = outPath.replace(/\.glb$/i, ".qc.json");
    if (!existsSync(outPath)) continue;
    const errors = [];
    if (!existsSync(qcPath)) {
      errors.push(`generated model is missing QC sidecar: ${qcPath}`);
    } else {
      const qc = readJson(qcPath);
      if (qc.assetId && qc.assetId !== blueprint.assetId) {
        errors.push(`QC assetId ${qc.assetId} does not match blueprint ${blueprint.assetId}`);
      }
      if (qc.qcPassed !== true) {
        errors.push(`QC sidecar must report qcPassed: true: ${qcPath}`);
      }
      if (blueprint.qc?.requiresPreview && (!Array.isArray(qc.previewImages) || qc.previewImages.length === 0)) {
        errors.push(`QC sidecar has no preview images for preview-required asset`);
      }
    }
    results.push({
      ok: errors.length === 0,
      filePath: qcPath,
      assetId: `generated-qc:${blueprint.assetId}`,
      errors
    });
  }
  return results;
}

export function validateAssetIndex() {
  const index = readJson(ASSET_INDEX_PATH);
  const blueprints = loadBlueprints().map(({ blueprint }) => blueprint);
  const byAssetId = new Map(blueprints.map((blueprint) => [blueprint.assetId, blueprint]));
  const results = [];

  const checkEntry = (label, entry) => {
    const errors = [];
    const blueprint = byAssetId.get(entry.assetId);
    if (!blueprint) {
      errors.push(`asset-index references unknown assetId ${entry.assetId}`);
    } else if (entry.model !== blueprint.output.model) {
      errors.push(`asset-index model ${entry.model} does not match blueprint output ${blueprint.output.model}`);
    }
    if (entry.bodyModel) {
      const bodyExists = blueprints.some((blueprint) => blueprint.output.model === entry.bodyModel);
      if (!bodyExists) errors.push(`asset-index bodyModel has no matching blueprint output: ${entry.bodyModel}`);
    }
    if (entry.runtimeReady === false && !entry.reviewStatus) {
      errors.push("asset-index entries blocked from runtime must include reviewStatus");
    }
    results.push({
      ok: errors.length === 0,
      filePath: ASSET_INDEX_PATH,
      assetId: `asset-index:${label}`,
      errors
    });
  };

  for (const [key, entry] of Object.entries(index.characterProfiles ?? {})) checkEntry(`character:${key}`, entry);
  for (const [key, entry] of Object.entries(index.baseBodies ?? {})) checkEntry(`body:${key}`, entry);
  for (const [key, entry] of Object.entries(index.equipment ?? {})) checkEntry(`equipment:${key}`, entry);
  for (const [key, entry] of Object.entries(index.staticProps ?? {})) checkEntry(`static:${key}`, entry);

  return results;
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
      qcPassed: existsSync(qcPath) ? readJson(qcPath).qcPassed === true : null
    };
  });
}

export function runBlenderForBlueprint(ref) {
  const { filePath, blueprint } = findBlueprint(ref);
  const config = readConfig();
  const blenderPath = config.blenderPath ?? "blender";
  if (!existsSync(blenderPath)) {
    throw new Error(`Blender not found at ${blenderPath}. Update ${CONFIG_PATH}.`);
  }
  if (!existsSync(GENERATOR_SCRIPT)) {
    throw new Error(`Missing generator entrypoint: ${GENERATOR_SCRIPT}`);
  }

  mkdirSync(MODEL_DIR, { recursive: true });
  const outPath = outputPathFor(blueprint);
  if (existsSync(outPath)) rmSync(outPath);
  const artifactDir = artifactDirFor(blueprint);
  if (artifactDir) mkdirSync(artifactDir, { recursive: true });

  const args = [
    "--background",
    "--python", GENERATOR_SCRIPT,
    "--",
    "--manifest", filePath,
    "--output", outPath
  ];
  if (artifactDir) args.push("--artifact-dir", artifactDir);

  return new Promise((resolve, reject) => {
    execFile(blenderPath, args, { cwd: PIPELINE_ROOT, timeout: 600_000 }, (err, stdout, stderr) => {
      if (err) {
        reject(new Error(`${err.message}\n${stderr}`));
        return;
      }
      if (!existsSync(outPath)) {
        reject(new Error(`Generation finished without creating ${outPath}\n${stderr}`));
        return;
      }
      resolve({ blueprint, outPath, stdout, stderr });
    });
  });
}
