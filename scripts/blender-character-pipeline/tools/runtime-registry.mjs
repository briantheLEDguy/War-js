import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import {
  APPROVED_ASSET_DIR,
  ASSET_INDEX_PATH,
  MODEL_DIR,
  readJson,
  readCompatibilityAllowlist,
  sha256Json,
} from "./pipeline-lib.mjs";
import { workflowError, writeJsonAtomic } from "./workspace-paths.mjs";
import { validateJsonSchema } from "./json-schema-validator.mjs";

const APPROVED_SCHEMA = readJson(path.join(path.dirname(APPROVED_ASSET_DIR), "approved-asset.schema.json"));

function sortedObject(value) {
  if (Array.isArray(value)) return value.map(sortedObject);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.keys(value).sort((a, b) => a.localeCompare(b, "en")).map((key) => [key, sortedObject(value[key])]),
  );
}

function validateApprovedManifest(manifest, source = "approved manifest") {
  const errors = validateJsonSchema(APPROVED_SCHEMA, manifest).map((error) => `schema: ${error}`);
  if (manifest.schemaVersion !== 1) errors.push("schemaVersion must be 1");
  if (!manifest.assetId) errors.push("assetId is required");
  if (!manifest.model || !/^[a-z0-9_.-]+\.glb$/.test(manifest.model)) errors.push("model must be a neutral .glb filename");
  if (manifest.approvalState !== "approved") errors.push("approvalState must be approved");
  for (const hash of ["modelSha256", "qcSha256"]) {
    if (!/^[a-f0-9]{64}$/.test(manifest.hashes?.[hash] ?? "")) errors.push(`hashes.${hash} must be sha256`);
  }
  if (!manifest.review?.reviewedBy || !manifest.review?.reviewedAt || !manifest.review?.reviewHash) {
    errors.push("reviewedBy, reviewedAt, and reviewHash are required");
  }
  const runtimeKeys = ["profileKey", "bodyKey", "itemKey", "staticKey"].filter((key) => manifest.runtime?.[key]);
  if (runtimeKeys.length !== 1) errors.push("runtime must contain exactly one of profileKey, bodyKey, itemKey, or staticKey");
  if (errors.length) throw workflowError("APPROVED_MANIFEST_INVALID", `${source} is invalid: ${errors.join("; ")}`, { errors });
  return manifest;
}

export function loadApprovedManifests() {
  if (!existsSync(APPROVED_ASSET_DIR)) return [];
  return readdirSync(APPROVED_ASSET_DIR)
    .filter((file) => file.endsWith(".approved.json"))
    .sort((a, b) => a.localeCompare(b, "en"))
    .map((file) => validateApprovedManifest(readJson(path.join(APPROVED_ASSET_DIR, file)), file));
}

function compatibilityRuntimeRecord(allowed) {
  const runtime = allowed.runtime ?? {};
  const section = runtime.section ?? "staticProps";
  const key = runtime.key ?? allowed.model?.replace(/\.glb$/i, "");
  if (!["equipment", "staticProps"].includes(section)) {
    throw workflowError(
      "COMPATIBILITY_SECTION_INVALID",
      `Compatibility asset ${allowed.model ?? "<unknown>"} has unsupported runtime section ${section}.`,
    );
  }
  if (!key || !/^[a-z0-9_]+$/.test(key)) {
    throw workflowError(
      "COMPATIBILITY_KEY_INVALID",
      `Compatibility asset ${allowed.model ?? "<unknown>"} requires a lowercase runtime key.`,
    );
  }
  return { section, key };
}

function runtimeEntry(manifest) {
  const compatibility = manifest.compatibility ?? {};
  const skinned = manifest.runtime?.skinned
    ?? (manifest.category === "armor" && compatibility.skeletonId ? true : undefined);
  const coveredRegions = manifest.runtime?.coveredRegions
    ?? compatibility.coveredRegions;
  return {
    assetId: manifest.assetId,
    model: manifest.model,
    qc: manifest.qc ?? manifest.model.replace(/\.glb$/i, ".qc.json"),
    bodyFamily: compatibility.bodyFamily,
    bodyVariant: compatibility.bodyVariant,
    skeletonId: compatibility.skeletonId,
    bindPoseId: compatibility.bindPoseId,
    ...(manifest.runtime?.animationPack ? { animationPack: manifest.runtime.animationPack } : {}),
    ...(manifest.runtime?.bodyModel ? { bodyModel: manifest.runtime.bodyModel } : {}),
    ...(skinned === undefined ? {} : { skinned }),
    ...(coveredRegions ? { coveredRegions } : {}),
    approvalState: "approved",
    lifecycleStatus: "approved",
    runtimeReady: true,
    reviewStatus: "approved",
    modelSha256: manifest.hashes.modelSha256,
    qcSha256: manifest.hashes.qcSha256,
    previews: manifest.previews ?? {},
    previewSha256: manifest.hashes.previews ?? {},
  };
}

/** Compile the runtime index from approved manifests only plus the explicit legacy allowlist. */
export function compileRuntimeRegistry(options = {}) {
  const byAssetId = new Map();
  for (const manifest of [...loadApprovedManifests(), ...(options.additionalManifests ?? [])]) {
    validateApprovedManifest(manifest);
    byAssetId.set(manifest.assetId, manifest);
  }
  const manifests = [...byAssetId.values()].sort((a, b) => a.assetId.localeCompare(b.assetId, "en"));
  const compatibilityAssets = readCompatibilityAllowlist().assets
    .slice()
    .sort((a, b) => String(a.model ?? "").localeCompare(String(b.model ?? ""), "en"));
  const registry = {
    schemaVersion: 2,
    generatedFrom: "scripts/blender-character-pipeline/data/approved-assets",
    assetVersion: `approved-${sha256Json(sortedObject({ manifests, compatibilityAssets })).slice(0, 16)}`,
    characterProfiles: {},
    baseBodies: {},
    equipment: {},
    staticProps: {},
  };

  const seenRuntimeKeys = new Set();
  for (const manifest of manifests) {
    const runtime = manifest.runtime ?? {};
    const entry = runtimeEntry(manifest);
    const keyRecord = runtime.profileKey
      ? ["characterProfiles", runtime.profileKey]
      : runtime.bodyKey
        ? ["baseBodies", runtime.bodyKey]
        : runtime.itemKey
          ? ["equipment", runtime.itemKey]
          : ["staticProps", runtime.staticKey];
    const uniqueKey = `${keyRecord[0]}:${keyRecord[1]}:${runtime.bodyVariant ?? manifest.compatibility?.bodyVariant ?? "_"}`;
    if (seenRuntimeKeys.has(uniqueKey)) throw workflowError("DUPLICATE_RUNTIME_KEY", `Duplicate approved runtime key: ${uniqueKey}`);
    seenRuntimeKeys.add(uniqueKey);

    if (keyRecord[0] === "equipment") {
      const variant = runtime.bodyVariant ?? manifest.compatibility?.bodyVariant;
      if (!variant || !["m", "f"].includes(variant)) {
        throw workflowError("EQUIPMENT_VARIANT_REQUIRED", `Approved equipment ${manifest.assetId} requires bodyVariant m or f.`);
      }
      const logical = registry.equipment[keyRecord[1]] ?? { variants: {} };
      logical.variants[variant] = entry;
      registry.equipment[keyRecord[1]] = logical;
    } else {
      registry[keyRecord[0]][keyRecord[1]] = entry;
    }
  }

  const seenCompatibilityModels = new Set();
  for (const allowed of compatibilityAssets) {
    if (!allowed.model || !/^[a-z0-9_.-]+\.glb$/.test(allowed.model)) {
      throw workflowError("COMPATIBILITY_MODEL_INVALID", "Compatibility assets require a neutral lowercase .glb filename.");
    }
    if (seenCompatibilityModels.has(allowed.model)) {
      throw workflowError("COMPATIBILITY_MODEL_DUPLICATE", `Duplicate compatibility model: ${allowed.model}`);
    }
    seenCompatibilityModels.add(allowed.model);
    if (!existsSync(path.join(MODEL_DIR, allowed.model))) continue;
    const { section, key } = compatibilityRuntimeRecord(allowed);
    // A reviewed asset supersedes its legacy compatibility entry during promotion.
    if (registry[section][key]) continue;
    registry[section][key] = {
      ...(allowed.assetId ? { assetId: allowed.assetId } : {}),
      model: allowed.model,
      lifecycleStatus: "compatibility_allowed",
      runtimeReady: allowed.runtimeReady ?? true,
      reviewStatus: allowed.reviewStatus ?? "compatibility_allowed",
      reason: allowed.reason,
    };
  }
  return sortedObject(registry);
}

export function writeRuntimeRegistry(options = {}) {
  const outputPath = options.outputPath ?? ASSET_INDEX_PATH;
  const registry = compileRuntimeRegistry(options);
  writeJsonAtomic(outputPath, registry);
  return registry;
}

export { validateApprovedManifest };
