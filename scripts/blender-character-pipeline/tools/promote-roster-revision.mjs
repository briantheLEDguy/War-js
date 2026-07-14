#!/usr/bin/env node

import { existsSync, mkdirSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  APPROVED_ASSET_DIR,
  MODEL_DIR,
  atomicPublishSet,
  sha256File,
  sha256Json,
} from "./pipeline-lib.mjs";
import {
  JOB_ROOT,
  REPO_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  workflowError,
  writeJsonAtomic,
} from "./workspace-paths.mjs";
import { compileRuntimeRegistry } from "./runtime-registry.mjs";
import { revisionDir, revisionManifestPath, updateRevision } from "./roster-runs.mjs";

const PLAYABLE_ROSTER_PATH = path.join(
  REPO_ROOT,
  "scripts",
  "blender-character-pipeline",
  "data",
  "playable-character-roster.json",
);
const PROMOTER_ID = "codex-user-authorized-bypass";
const SLOT_LABELS = {
  head: "Headgear",
  shoulders: "Shoulders",
  chest: "Chestguard",
  hands: "Handguards",
  waist: "Belt",
  legs: "Legguards",
  feet: "Boots",
  back: "Backpiece",
  tabard: "Tabard",
};
const COVERED_REGIONS = {
  head: ["head"],
  shoulders: ["shoulders"],
  chest: ["torso"],
  hands: ["arms", "hands"],
  waist: ["waist"],
  legs: ["legs"],
  feet: ["feet"],
  back: ["back"],
  tabard: ["tabard"],
};
const REQUIRED_HUMANOID_CLIPS = [
  "idle",
  "walk",
  "run",
  "combat_idle",
  "attack_melee",
  "attack_ranged",
  "cast",
  "death",
  "jump",
];
const NPC_ROLE_MODEL_KEYS = new Set(["ambient", "banker", "captain", "guard", "raider", "trainer", "vendor"]);

function parseArgs(argv) {
  const result = { revision: 1, bypassApproval: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--bypass-approval") {
      result.bypassApproval = true;
      continue;
    }
    if (["--run-id", "--kind", "--key", "--revision", "--reason"].includes(token)) {
      const value = argv[++index];
      if (!value || value.startsWith("--")) throw new Error(`Missing value for ${token}.`);
      result[token.slice(2).replaceAll("-", "_")] = token === "--revision" ? Number(value) : value;
      continue;
    }
    throw new Error(`Unknown argument: ${token}`);
  }
  return result;
}

function filesRecursively(directory) {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const child = assertPathWithin(directory, path.join(directory, entry.name), "promotion source");
    return entry.isDirectory() ? filesRecursively(child) : [child];
  }).sort((left, right) => left.localeCompare(right, "en"));
}

function requireTechnicalQc(modelPath, qcPath) {
  if (!existsSync(modelPath) || !existsSync(qcPath)) {
    throw workflowError("PROMOTION_SOURCE_MISSING", `Missing generated source pair: ${modelPath}`);
  }
  const qc = readJson(qcPath);
  const modelSha256 = sha256File(modelPath);
  if (qc.qcPassed !== true) throw workflowError("PROMOTION_QC_FAILED", `${repoRelative(qcPath)} did not pass technical QC.`);
  const recordedModelSha256 = qc.modelSha256 ?? qc.output?.sha256;
  if (recordedModelSha256 !== modelSha256) throw workflowError("PROMOTION_HASH_MISMATCH", `${repoRelative(qcPath)} does not match its model.`);
  return { qc, modelSha256, qcSha256: sha256File(qcPath) };
}

function sourcePairForQc(qcPath, qc) {
  const modelPath = path.join(path.dirname(qcPath), qc.model);
  return { modelPath, qcPath };
}

export function canonicalPlayableRuntimeIds({ family, key, variant, slot = null }) {
  const suffix = `${family}_${key}_${variant}`;
  return {
    profileKey: `${family}_${key}_${variant}`,
    characterAssetId: `chr.${family}.${key}.t1.${variant}`,
    characterModel: `chr_${family}_${key}_t1_${variant}.glb`,
    armorAssetId: slot ? `arm.${family}.${key}.${slot}.t1.${variant}` : null,
    armorModel: slot ? `arm_${family}_${key}_${slot}_t1_${variant}.glb` : null,
    bodyFamily: suffix,
  };
}

function runtimeToken(value) {
  return String(value).toLowerCase().replace(/[^a-z0-9_.-]+/g, "_");
}

export function canonicalNpcRuntimeIds({ key, role, variant }) {
  const normalizedRole = runtimeToken(role);
  if (!NPC_ROLE_MODEL_KEYS.has(normalizedRole)) {
    throw workflowError("NPC_ROLE_UNSUPPORTED", `No runtime model mapping exists for NPC role ${role}.`);
  }
  return {
    profileKey: key,
    characterAssetId: `chr.npc.${key.replaceAll("_", ".")}`,
    characterModel: `chr_npc_${runtimeToken(key)}_${normalizedRole}_${runtimeToken(variant)}.glb`,
  };
}

export function canonicalCreatureRuntimeIds({ key }) {
  const normalizedKey = runtimeToken(key);
  return {
    staticKey: `creature_${normalizedKey}`,
    assetId: `creature.${normalizedKey}.t1`,
    model: `prop_creature_${normalizedKey}.glb`,
  };
}

function reviewForAsset({ assetId, sourceManifestSha256, reason, reviewedAt }) {
  const unsigned = {
    assetId,
    sourceManifestSha256,
    reviewer: PROMOTER_ID,
    reviewedAt,
    reason,
    bypassApproval: true,
  };
  return {
    reviewedBy: PROMOTER_ID,
    reviewedAt,
    reviewHash: sha256Json(unsigned),
  };
}

function approvedManifest({
  assetId,
  displayName,
  category,
  model,
  qc,
  runtime,
  compatibility,
  hashes,
  previews,
  previewHashes,
  source,
  review,
  reason,
}) {
  return {
    schemaVersion: 1,
    assetId,
    displayName,
    category,
    model,
    qc,
    runtime,
    compatibility,
    hashes: { ...hashes, previews: previewHashes },
    previews,
    provenance: {
      kind: "roster_direct_promotion",
      sourceRevision: source.revision,
      sourceRunId: source.runId,
      sourceManifest: source.manifest,
      bypassApproval: true,
      bypassReason: reason,
    },
    review,
    approvalState: "approved",
  };
}

function armorSourceRows(variantDir, variant) {
  return filesRecursively(variantDir)
    .filter((filePath) => filePath.endsWith(".qc.json"))
    .map((qcPath) => ({ qcPath, qc: readJson(qcPath) }))
    .filter(({ qc }) => qc.category === "armor" && qc.bodyVariant === variant);
}

function previewPublication(sourcePath, destination) {
  if (!existsSync(sourcePath)) throw workflowError("PROMOTION_PREVIEW_MISSING", `Missing review preview: ${sourcePath}`);
  return {
    previews: { front: destination },
    previewHashes: { front: sha256File(sourcePath) },
    publishFile: { source: sourcePath, destination: path.join(MODEL_DIR, destination), sha256: sha256File(sourcePath) },
  };
}

function previewSourceForQc(qc, fallbackPath) {
  return qc.previews?.find((preview) => preview.view === "front")?.path ?? fallbackPath;
}

function requireNpcTechnicalQc(modelPath, qcPath) {
  if (!existsSync(modelPath) || !existsSync(qcPath)) {
    throw workflowError("PROMOTION_SOURCE_MISSING", `Missing generated source pair: ${modelPath}`);
  }
  const qc = readJson(qcPath);
  const modelSha256 = sha256File(modelPath);
  if (qc.qcPassed !== true && qc.technicalRoundTripPassed !== true) {
    throw workflowError("PROMOTION_QC_FAILED", `${repoRelative(qcPath)} did not pass technical or round-trip QC.`);
  }
  if (qc.modelSha256 !== modelSha256) {
    throw workflowError("PROMOTION_HASH_MISMATCH", `${repoRelative(qcPath)} does not match its model.`);
  }
  const clips = new Set(qc.animationClips ?? []);
  const missingClips = REQUIRED_HUMANOID_CLIPS.filter((clip) => !clips.has(clip));
  if (missingClips.length > 0) {
    throw workflowError(
      "PROMOTION_ANIMATION_FAILED",
      `${repoRelative(qcPath)} is missing required runtime clips: ${missingClips.join(", ")}.`,
    );
  }
  return { qc, modelSha256, qcSha256: sha256File(qcPath) };
}

function buildPlayableManifests({ revision, roster, sourceManifestSha256, reviewedAt, reason }) {
  const group = revision.group;
  const race = roster.races?.[group.race];
  if (!race?.family) throw workflowError("ROSTER_FAMILY_MISSING", `No runtime family mapping exists for ${group.race}.`);

  const manifests = [];
  const publishFiles = [];
  for (const variantRow of group.variants ?? []) {
    const variant = variantRow.variant;
    const ids = canonicalPlayableRuntimeIds({ family: race.family, key: group.key, variant });
    const variantDir = revisionDir(revision.runId, revision.kind, revision.key, revision.revision);
    const bodyModelPath = path.join(variantDir, variant, `body_${group.key}_${variant}.glb`);
    const bodyQcPath = path.join(variantDir, variant, `body_${group.key}_${variant}.qc.json`);
    const body = requireTechnicalQc(bodyModelPath, bodyQcPath);
    if (body.qc.skeletonId !== "humanoid_game_v2" || body.qc.bindPoseId !== "a_pose_v2") {
      throw workflowError("PROMOTION_SKELETON_MISMATCH", `${repoRelative(bodyQcPath)} is not on the canonical runtime skeleton.`);
    }
    const bodyOutputQc = ids.characterModel.replace(/\.glb$/i, ".qc.json");
    const bodyPreview = previewPublication(
      path.join(variantDir, variant, "body-review", "front.png"),
      `reviews/roster-direct/${group.key}/${variant}/body_front.png`,
    );
    const bodyReview = reviewForAsset({
      assetId: ids.characterAssetId,
      sourceManifestSha256,
      reason,
      reviewedAt,
    });
    manifests.push(approvedManifest({
      assetId: ids.characterAssetId,
      displayName: `${group.displayName} ${variant === "m" ? "Male" : "Female"}`,
      category: "character",
      model: ids.characterModel,
      qc: bodyOutputQc,
      runtime: { profileKey: ids.profileKey },
      compatibility: {
        bodyFamily: ids.bodyFamily,
        bodyVariant: variant,
        skeletonId: "humanoid_game_v2",
        bindPoseId: "a_pose_v2",
      },
      hashes: { modelSha256: body.modelSha256, qcSha256: body.qcSha256 },
      previews: bodyPreview.previews,
      previewHashes: bodyPreview.previewHashes,
      source: revision,
      review: bodyReview,
      reason,
    }));
    publishFiles.push({ source: bodyModelPath, destination: path.join(MODEL_DIR, ids.characterModel), sha256: body.modelSha256 });
    publishFiles.push({ source: bodyQcPath, destination: path.join(MODEL_DIR, bodyOutputQc), sha256: body.qcSha256 });
    publishFiles.push(bodyPreview.publishFile);

    const armorRows = armorSourceRows(variantDir, variant);
    for (const module of variantRow.armorModules ?? []) {
      const match = armorRows.find(({ qc }) => qc.assetId === module.assetId);
      if (!match) throw workflowError("PROMOTION_ARMOR_MISSING", `Could not find generated armor QC for ${module.assetId}.`);
      const pair = sourcePairForQc(match.qcPath, match.qc);
      const armor = requireTechnicalQc(pair.modelPath, pair.qcPath);
      const armorIds = canonicalPlayableRuntimeIds({ family: race.family, key: group.key, variant, slot: module.slot });
      const armorOutputQc = armorIds.armorModel.replace(/\.glb$/i, ".qc.json");
      const armorPreview = previewPublication(
        match.qc.previews?.find((preview) => preview.view === "front")?.path
          ?? path.join(variantDir, variant, "armor-review", group.key, "front.png"),
        `reviews/roster-direct/${group.key}/${variant}/${module.slot}_front.png`,
      );
      const armorReview = reviewForAsset({
        assetId: armorIds.armorAssetId,
        sourceManifestSha256,
        reason,
        reviewedAt,
      });
      manifests.push(approvedManifest({
        assetId: armorIds.armorAssetId,
        displayName: `${group.displayName} ${SLOT_LABELS[module.slot] ?? module.slot} ${variant === "m" ? "Male" : "Female"}`,
        category: "armor",
        model: armorIds.armorModel,
        qc: armorOutputQc,
        runtime: { itemKey: module.itemKey, bodyVariant: variant, skinned: true },
        compatibility: {
          bodyFamily: ids.bodyFamily,
          bodyVariant: variant,
          skeletonId: "humanoid_game_v2",
          bindPoseId: "a_pose_v2",
          coveredRegions: COVERED_REGIONS[module.slot] ?? [],
        },
        hashes: { modelSha256: armor.modelSha256, qcSha256: armor.qcSha256 },
        previews: armorPreview.previews,
        previewHashes: armorPreview.previewHashes,
        source: revision,
        review: armorReview,
        reason,
      }));
      publishFiles.push({ source: pair.modelPath, destination: path.join(MODEL_DIR, armorIds.armorModel), sha256: armor.modelSha256 });
      publishFiles.push({ source: pair.qcPath, destination: path.join(MODEL_DIR, armorOutputQc), sha256: armor.qcSha256 });
      publishFiles.push(armorPreview.publishFile);
    }
  }
  return { manifests, publishFiles };
}

function buildNpcManifests({ revision, sourceManifestSha256, reviewedAt, reason }) {
  const group = revision.group;
  const variant = group.bodyVariant;
  const variantDir = path.join(revisionDir(revision.runId, revision.kind, revision.key, revision.revision), variant, "armor");
  const profiles = group.liveProfiles ?? [];
  if (!variant || !group.bodyFamily || profiles.length === 0) {
    throw workflowError("NPC_PROMOTION_SET_INCOMPLETE", "NPC promotion requires a body variant, body family, and live profiles.");
  }

  const manifests = [];
  const publishFiles = [];
  const roleSources = new Map();
  for (const profile of profiles) {
    const role = runtimeToken(profile.role ?? "ambient");
    const ids = canonicalNpcRuntimeIds({ key: revision.key, role, variant });
    if (!roleSources.has(role)) {
      const sourceModelName = `npc_${revision.key}_${role}_${variant}_equipped_review.glb`;
      const sourceModelPath = path.join(variantDir, sourceModelName);
      const sourceQcPath = sourceModelPath.replace(/\.glb$/i, ".qc.json");
      const sourceQc = requireNpcTechnicalQc(sourceModelPath, sourceQcPath);
      const preview = previewPublication(
        previewSourceForQc(sourceQc.qc, path.join(path.dirname(variantDir), "armor-review", "roundtrip-review", "front.png")),
        `reviews/roster-direct/npc/${revision.key}/${role}_front.png`,
      );
      const outputQc = ids.characterModel.replace(/\.glb$/i, ".qc.json");
      roleSources.set(role, {
        ids,
        modelPath: sourceModelPath,
        qcPath: sourceQcPath,
        modelSha256: sourceQc.modelSha256,
        qcSha256: sourceQc.qcSha256,
        outputQc,
        preview,
      });
      publishFiles.push({ source: sourceModelPath, destination: path.join(MODEL_DIR, ids.characterModel), sha256: sourceQc.modelSha256 });
      publishFiles.push({ source: sourceQcPath, destination: path.join(MODEL_DIR, outputQc), sha256: sourceQc.qcSha256 });
      publishFiles.push(preview.publishFile);
    }

    const source = roleSources.get(role);
    const profileAssetId = `chr.npc.${profile.profileKey.replaceAll("_", ".")}`;
    const review = reviewForAsset({
      assetId: profileAssetId,
      sourceManifestSha256,
      reason,
      reviewedAt,
    });
    manifests.push(approvedManifest({
      assetId: profileAssetId,
      displayName: profile.displayName ?? profile.profileKey,
      category: "character",
      model: source.ids.characterModel,
      qc: source.outputQc,
      runtime: { profileKey: profile.profileKey, skinned: true },
      compatibility: {
        bodyFamily: group.bodyFamily,
        bodyVariant: variant,
        skeletonId: "humanoid_game_v2",
        bindPoseId: "a_pose_v2",
      },
      hashes: { modelSha256: source.modelSha256, qcSha256: source.qcSha256 },
      previews: source.preview.previews,
      previewHashes: source.preview.previewHashes,
      source: revision,
      review,
      reason,
    }));
  }
  return { manifests, publishFiles };
}

function buildCreatureManifests({ revision, sourceManifestSha256, reviewedAt, reason }) {
  const group = revision.group;
  const revisionRoot = revisionDir(revision.runId, revision.kind, revision.key, revision.revision);
  const ids = canonicalCreatureRuntimeIds({ key: revision.key });
  const modelPath = path.join(revisionRoot, `creature_${revision.key}_lod0.glb`);
  const qcPath = modelPath.replace(/\.glb$/i, ".qc.json");
  const source = requireTechnicalQc(modelPath, qcPath);
  if (source.qc.creatureKey !== revision.key || source.qc.skeletonId !== group.skeletonId) {
    throw workflowError("PROMOTION_CREATURE_MISMATCH", `${repoRelative(qcPath)} does not match creature ${revision.key}.`);
  }
  const preview = previewPublication(
    previewSourceForQc(source.qc, path.join(revisionRoot, "review", "front.png")),
    `reviews/roster-direct/creature/${revision.key}/front.png`,
  );
  const outputQc = ids.model.replace(/\.glb$/i, ".qc.json");
  const assetId = ids.assetId;
  const review = reviewForAsset({ assetId, sourceManifestSha256, reason, reviewedAt });
  return {
    manifests: [approvedManifest({
      assetId,
      displayName: group.displayName,
      category: "prop",
      model: ids.model,
      qc: outputQc,
      runtime: { staticKey: ids.staticKey },
      compatibility: {
        bodyFamily: `creature_${group.bodyPlan}_v1`,
        bodyVariant: "neutral",
        skeletonId: group.skeletonId,
        bindPoseId: "grounded_v1",
        markers: group.requiredMarkers ?? source.qc.markers ?? [],
      },
      hashes: { modelSha256: source.modelSha256, qcSha256: source.qcSha256 },
      previews: preview.previews,
      previewHashes: preview.previewHashes,
      source: revision,
      review,
      reason,
    })],
    publishFiles: [
      { source: modelPath, destination: path.join(MODEL_DIR, ids.model), sha256: source.modelSha256 },
      { source: qcPath, destination: path.join(MODEL_DIR, outputQc), sha256: source.qcSha256 },
      preview.publishFile,
    ],
  };
}

export function promoteRosterRevision({ runId, kind, key, revision, reason }) {
  if (!["playable", "npc", "creature"].includes(kind)) {
    throw workflowError("DIRECT_PROMOTION_KIND_UNSUPPORTED", `Direct promotion does not support roster kind ${kind}.`);
  }
  const manifestPath = revisionManifestPath(runId, kind, key, revision);
  if (!existsSync(manifestPath)) throw workflowError("ROSTER_REVISION_NOT_FOUND", `Roster revision does not exist: ${repoRelative(manifestPath)}.`);
  const revisionManifest = readJson(manifestPath);
  const directPromotionResume = revisionManifest.status === "model_approved"
    && revisionManifest.runtimePromotion?.bypassedApproval === true;
  if ((!directPromotionResume && revisionManifest.status !== "ready_for_review") || revisionManifest.qc?.passed !== true) {
    throw workflowError("DIRECT_PROMOTION_QC_REQUIRED", "Direct promotion requires a ready revision with passing consolidated QC.");
  }
  const sourceManifestSha256 = sha256File(manifestPath);
  const reviewedAt = new Date().toISOString();
  const promotionReason = reason?.trim() || "User-authorized production bypass for the roster pilot.";
  const built = kind === "playable"
    ? buildPlayableManifests({
      revision: revisionManifest,
      roster: readJson(PLAYABLE_ROSTER_PATH),
      sourceManifestSha256,
      reviewedAt,
      reason: promotionReason,
    })
    : kind === "npc"
      ? buildNpcManifests({ revision: revisionManifest, sourceManifestSha256, reviewedAt, reason: promotionReason })
      : buildCreatureManifests({ revision: revisionManifest, sourceManifestSha256, reviewedAt, reason: promotionReason });
  const { manifests, publishFiles } = built;
  const expectedCount = kind === "playable" ? 20 : kind === "npc" ? revisionManifest.group.liveProfiles?.length ?? 0 : 1;
  if (manifests.length !== expectedCount) {
    throw workflowError("DIRECT_PROMOTION_SET_INCOMPLETE", `Expected ${expectedCount} ${kind} manifests, found ${manifests.length}.`);
  }

  const transactionRoot = assertPathWithin(
    JOB_ROOT,
    path.join(JOB_ROOT, "direct-promotions", `${runId}_${kind}_${key}_revision-${String(revision).padStart(4, "0")}`),
    "direct promotion transaction root",
  );
  const stagingRoot = path.join(transactionRoot, "staging");
  const stagedApprovedDir = path.join(stagingRoot, "approved-assets");
  mkdirSync(stagedApprovedDir, { recursive: true });
  const manifestFiles = [];
  for (const approved of manifests) {
    const fileName = `${approved.assetId.replaceAll(".", "_")}.approved.json`;
    const source = path.join(stagedApprovedDir, fileName);
    writeJsonAtomic(source, approved);
    manifestFiles.push({
      source,
      destination: path.join(APPROVED_ASSET_DIR, fileName),
      sha256: sha256File(source),
    });
  }
  const registry = compileRuntimeRegistry({ additionalManifests: manifests });
  const registrySource = path.join(stagingRoot, "asset-index.json");
  writeJsonAtomic(registrySource, registry);
  const publishEntries = [
    ...publishFiles,
    ...manifestFiles,
    { source: registrySource, destination: path.join(MODEL_DIR, "asset-index.json"), sha256: sha256File(registrySource) },
  ];
  const published = atomicPublishSet(publishEntries, { transactionDir: path.join(transactionRoot, "publish") });
  const runtimePromotion = {
    status: "promoted",
    kind,
    bypassedApproval: true,
    authorizedBy: PROMOTER_ID,
    reason: promotionReason,
    promotedAt: reviewedAt,
    manifestSha256: sourceManifestSha256,
    manifestCount: manifests.length,
    publishedFileCount: published.length,
    assetVersion: registry.assetVersion,
  };
  writeJsonAtomic(path.join(transactionRoot, "promotion.json"), runtimePromotion);
  updateRevision(manifestPath, {
    status: "model_approved",
    modelStage: "approved",
    ...(kind === "npc" ? { animationStage: "approved" } : {}),
    runtimeEligible: true,
    runtimePromotion,
  });
  return {
    kind,
    key,
    revision,
    assetVersion: registry.assetVersion,
    manifests: manifests.map((asset) => asset.assetId),
    publishedFileCount: published.length,
    promotion: repoRelative(path.join(transactionRoot, "promotion.json")),
  };
}

function main(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (!args.run_id || !args.kind || !args.key) throw new Error("--run-id, --kind, and --key are required.");
  if (!Number.isInteger(args.revision) || args.revision < 1) throw new Error("--revision must be a positive integer.");
  if (!args.bypassApproval) throw new Error("Direct promotion requires explicit --bypass-approval.");
  console.log(JSON.stringify(promoteRosterRevision({
    runId: args.run_id,
    kind: args.kind,
    key: args.key,
    revision: args.revision,
    reason: args.reason,
  }), null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
