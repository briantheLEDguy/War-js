import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  statSync,
} from "node:fs";
import path from "node:path";
import {
  APPROVED_ASSET_DIR,
  ASSET_INDEX_PATH,
  BODY_FAMILY_DIR,
  MODEL_DIR,
  PIPELINE_ROOT,
  REPO_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  resolveRepoPath,
  workflowError,
  writeJsonAtomic,
} from "./workspace-paths.mjs";
import {
  REVIEW_RENDER_SCRIPT,
  atomicPublishSet,
  findBlueprint,
  outputPathFor,
  readConfig,
  sha256File,
  sha256Json,
  validateBlueprints,
} from "./pipeline-lib.mjs";
import { modelJobStore, startModelJob } from "./model-jobs.mjs";
import { compileRuntimeRegistry } from "./runtime-registry.mjs";
import { assertJsonSchema } from "./json-schema-validator.mjs";

export const ARMOR_SLOTS = ["head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard"];
export const REQUIRED_CLIPS = ["idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump"];
export const ANIMATION_EVIDENCE_PROFILES = ["midpoint", "locomotion_melee_key_phases"];
const ASSET_ID_PATTERN = /^(chr|body|arm|wep|jwl|prop|terrain)\.[a-z0-9_.-]+$/;
const SAFE_ID_PATTERN = /^[a-z0-9][a-z0-9_.-]*$/;
const CANDIDATE_SCHEMA = readJson(path.join(PIPELINE_ROOT, "data", "model-candidate.schema.json"));
const MPFB_BODY_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_mpfb_body.py");

function requireString(value, name, pattern = null) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw workflowError("INVALID_INPUT", `${name} must be a non-empty string.`);
  }
  if (pattern && !pattern.test(value)) throw workflowError("INVALID_INPUT", `${name} has an invalid format: ${value}`);
  return value;
}

function requireVariant(value) {
  if (!["m", "f"].includes(value)) throw workflowError("INVALID_BODY_VARIANT", "bodyVariant must be m or f.");
  return value;
}

function ensureGlb(value, name = "modelPath") {
  const resolved = resolveRepoPath(requireString(value, name), name);
  if (!existsSync(resolved) || !statSync(resolved).isFile()) throw workflowError("MODEL_SOURCE_MISSING", `${name} does not exist: ${value}`);
  if (path.extname(resolved).toLowerCase() !== ".glb") throw workflowError("MODEL_FORMAT_UNSUPPORTED", `${name} must be a .glb file.`);
  return resolved;
}

function copyInto(source, destination) {
  const safeSource = assertPathWithin(REPO_ROOT, source, "copy source");
  const safeDestination = assertPathWithin(REPO_ROOT, destination, "copy destination");
  mkdirSync(path.dirname(safeDestination), { recursive: true });
  copyFileSync(safeSource, safeDestination);
  return safeDestination;
}

function execFilePromise(executable, args, options) {
  return new Promise((resolve, reject) => {
    execFile(executable, args, options, (error, stdout, stderr) => {
      if (error) {
        if (error.name === "AbortError" || error.code === "ABORT_ERR") return reject(error);
        return reject(workflowError("LOCAL_TOOL_FAILED", `${error.message}\n${String(stderr ?? "").slice(-6000)}`, {
          exitCode: error.code,
        }));
      }
      resolve({ stdout: String(stdout ?? ""), stderr: String(stderr ?? "") });
    });
  });
}

function providerRecord(input) {
  const provider = input.provenance?.provider ?? input.provider ?? {};
  const license = input.provenance?.license ?? input.license ?? {};
  requireString(provider.name, "provenance.provider.name");
  requireString(provider.modelVersion, "provenance.provider.modelVersion");
  requireString(license.name, "provenance.license.name");
  requireString(license.sourceUrl, "provenance.license.sourceUrl");
  return {
    provider: {
      name: provider.name,
      ...(provider.taskId ? { taskId: String(provider.taskId) } : {}),
      modelVersion: provider.modelVersion,
      seed: provider.seed ?? null,
    },
    promptSha256: input.provenance?.promptSha256 ?? input.promptSha256 ?? null,
    referenceSha256: input.provenance?.referenceSha256 ?? input.referenceSha256 ?? [],
    author: input.provenance?.author ?? input.author ?? "local_project_author",
    license: {
      name: license.name,
      sourceUrl: license.sourceUrl,
      ...(license.termsUrl ? { termsUrl: license.termsUrl } : {}),
    },
  };
}

function qcWithBoundHash(qcSource, destination, assetId, modelName, modelHash) {
  const safeQc = resolveRepoPath(qcSource, "qcPath");
  if (!existsSync(safeQc)) throw workflowError("QC_SOURCE_MISSING", `QC file does not exist: ${qcSource}`);
  const qc = readJson(safeQc);
  if (qc.qcPassed !== true) throw workflowError("QC_NOT_PASSED", `QC has not passed for ${assetId}.`);
  qc.assetId = assetId;
  qc.model = modelName;
  qc.modelSha256 = modelHash;
  qc.boundAt = new Date().toISOString();
  writeJsonAtomic(destination, qc);
  return destination;
}

function writeCandidate(ctx, input, sourceModel, options = {}) {
  const assetId = requireString(input.assetId, "assetId", ASSET_ID_PATTERN);
  const bodyVariant = requireVariant(input.bodyVariant);
  const bodyFamily = requireString(input.bodyFamily, "bodyFamily", SAFE_ID_PATTERN);
  const skeletonId = requireString(input.skeletonId ?? "humanoid_game_v2", "skeletonId", SAFE_ID_PATTERN);
  const bindPoseId = requireString(input.bindPoseId ?? "a_pose_v2", "bindPoseId", SAFE_ID_PATTERN);
  const provenance = providerRecord(input);
  const sourceHash = sha256File(sourceModel);
  const candidateId = `candidate_${createHash("sha256").update(`${assetId}:${sourceHash}`).digest("hex").slice(0, 16)}`;
  const candidateDir = path.join(ctx.artifactDir, "candidate");
  mkdirSync(candidateDir, { recursive: true });
  const outputModel = input.outputModel ?? `${assetId.replace(/\./g, "_")}.glb`;
  if (!/^[a-z0-9_.-]+\.glb$/.test(outputModel)) throw workflowError("INVALID_OUTPUT_MODEL", `Invalid output model filename: ${outputModel}`);
  const stagedModel = copyInto(sourceModel, path.join(candidateDir, outputModel));
  let stagedQc = null;
  if (input.qcPath) {
    stagedQc = qcWithBoundHash(
      input.qcPath,
      path.join(candidateDir, outputModel.replace(/\.glb$/i, ".qc.json")),
      assetId,
      outputModel,
      sourceHash,
    );
  }
  const now = new Date().toISOString();
  const candidate = {
    schemaVersion: 1,
    candidateId,
    assetId,
    displayName: input.displayName ?? assetId,
    category: input.category ?? options.category ?? "character",
    source: {
      path: repoRelative(stagedModel),
      sha256: sourceHash,
      format: "glb",
      ...(stagedQc ? { qcPath: repoRelative(stagedQc) } : {}),
    },
    provenance: {
      ...provenance,
      sourceHashes: [sourceHash],
    },
    compatibility: { bodyFamily, bodyVariant, skeletonId, bindPoseId },
    runtime: input.runtime ?? options.runtime ?? {},
    lifecycle: {
      status: stagedQc ? "qc_passed" : "draft",
      createdAt: now,
      updatedAt: now,
    },
  };
  const candidatePath = path.join(candidateDir, "model-candidate.json");
  assertJsonSchema(CANDIDATE_SCHEMA, candidate, "model candidate");
  writeJsonAtomic(candidatePath, candidate);
  ctx.addArtifact(stagedModel, "candidate_model");
  if (stagedQc) ctx.addArtifact(stagedQc, "candidate_qc");
  ctx.addArtifact(candidatePath, "candidate_manifest");

  const bundle = {
    schemaVersion: 1,
    sourceJobId: ctx.jobId,
    bodyFamily,
    bodyVariant,
    skeletonId,
    bindPoseId,
    assets: [{
      assetId,
      displayName: candidate.displayName,
      category: candidate.category,
      sourceModel: repoRelative(stagedModel),
      sourceQc: stagedQc ? repoRelative(stagedQc) : null,
      outputModel,
      modelSha256: sourceHash,
      runtime: candidate.runtime,
      compatibility: candidate.compatibility,
      provenance: candidate.provenance,
    }],
    lifecycle: { status: stagedQc ? "qc_passed" : "draft", updatedAt: now },
  };
  const bundlePath = path.join(ctx.artifactDir, "promotion-bundle.json");
  writeJsonAtomic(bundlePath, bundle);
  ctx.addArtifact(bundlePath, "promotion_bundle");
  return { candidate, candidatePath, bundlePath };
}

function locateFile(directory, basename) {
  if (!existsSync(directory)) return null;
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const child = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      const found = locateFile(child, basename);
      if (found) return found;
    } else if (entry.name === basename) return child;
  }
  return null;
}

function readJobBundle(jobId) {
  const job = modelJobStore.get(jobId);
  if (job.status !== "completed") throw workflowError("SOURCE_JOB_INCOMPLETE", `Source job ${jobId} is ${job.status}.`);
  const bundlePath = locateFile(modelJobStore.jobDir(jobId), "promotion-bundle.json");
  if (!bundlePath) throw workflowError("PROMOTION_BUNDLE_MISSING", `Job ${jobId} has no promotion-bundle.json.`);
  return { bundle: readJson(bundlePath), bundlePath };
}

function reviewedBundleSha256(bundle) {
  const { lifecycle: _lifecycle, ...reviewedContent } = bundle;
  return sha256Json(reviewedContent);
}

function startCreateBodyFamily(input) {
  const bodyFamily = requireString(input.bodyFamily, "bodyFamily", SAFE_ID_PATTERN);
  const bodyVariant = requireVariant(input.bodyVariant);
  return startModelJob("create_body_family", input, async (ctx) => {
    ctx.update(10, "Loading pinned MPFB body recipe");
    const familyPath = assertPathWithin(BODY_FAMILY_DIR, path.join(BODY_FAMILY_DIR, `${bodyFamily}.body-family.json`), "body family recipe");
    if (!existsSync(familyPath)) throw workflowError("BODY_FAMILY_NOT_FOUND", `Unknown body family: ${bodyFamily}`);
    const family = readJson(familyPath);
    const variant = family.variants?.[bodyVariant];
    if (!variant) throw workflowError("BODY_VARIANT_NOT_FOUND", `${bodyFamily} has no ${bodyVariant} recipe.`);
    const request = {
      schemaVersion: 1,
      bodyFamily,
      bodyVariant,
      mpfbVersion: family.mpfbVersion ?? "2.0.16",
      skeletonId: family.skeletonId ?? "humanoid_game_v2",
      bindPoseId: family.bindPoseId ?? "a_pose_v2",
      recipeSource: repoRelative(familyPath),
      variant,
      requiredAssetPacks: family.requiredAssetPacks ?? [],
      createdAt: new Date().toISOString(),
    };
    const requestPath = path.join(ctx.artifactDir, "body-family-request.json");
    writeJsonAtomic(requestPath, request);
    ctx.addArtifact(requestPath, "mpfb_recipe");
    let sourceModel;
    let sourceQc = input.qcPath;
    if (input.sourceModel) {
      ctx.update(55, "Ingesting locally generated MPFB body");
      sourceModel = ensureGlb(input.sourceModel, "sourceModel");
    } else {
      const config = readConfig();
      const blenderPath = process.env.BLENDER_PATH ?? config.blenderPath ?? "blender";
      if (path.isAbsolute(blenderPath) && !existsSync(blenderPath)) {
        throw workflowError("BLENDER_NOT_FOUND", `Blender not found at ${blenderPath}.`);
      }
      if (!existsSync(MPFB_BODY_SCRIPT)) {
        throw workflowError("MPFB_BODY_GENERATOR_MISSING", `Missing body generator: ${MPFB_BODY_SCRIPT}`);
      }
      const generatedDir = path.join(ctx.artifactDir, "generated-body");
      const outputModel = input.outputModel ?? variant.outputModel;
      sourceModel = path.join(generatedDir, outputModel);
      sourceQc = sourceModel.replace(/\.glb$/i, ".qc.json");
      const reviewDir = path.join(generatedDir, "review");
      mkdirSync(generatedDir, { recursive: true });
      ctx.update(20, "Generating anatomical MPFB body locally");
      const { stdout, stderr } = await execFilePromise(blenderPath, [
        "--background", "--python", MPFB_BODY_SCRIPT, "--",
        "--family", bodyFamily,
        "--variant", bodyVariant,
        "--output", sourceModel,
        "--review-dir", reviewDir,
        "--save-blend", path.join(generatedDir, "source.blend"),
      ], {
        cwd: PIPELINE_ROOT,
        timeout: input.timeoutMs ?? 900_000,
        maxBuffer: 16 * 1024 * 1024,
        signal: ctx.signal,
        windowsHide: true,
      });
      ctx.checkCancelled();
      if (!existsSync(sourceModel) || !existsSync(sourceQc)) {
        throw workflowError("MPFB_BODY_OUTPUT_MISSING", "Blender did not produce a model and QC sidecar.", {
          stdout: stdout.slice(-6000),
          stderr: stderr.slice(-6000),
        });
      }
      if (readJson(sourceQc).qcPassed !== true) {
        throw workflowError("QC_NOT_PASSED", `Generated MPFB body failed QC: ${repoRelative(sourceQc)}`);
      }
      ctx.addArtifact(sourceModel, "generated_body");
      ctx.addArtifact(sourceQc, "generated_body_qc");
      for (const view of ["front", "side", "back", "isometric"]) {
        const preview = path.join(reviewDir, `${view}.png`);
        if (existsSync(preview)) ctx.addArtifact(preview, `review_${view}`);
      }
      ctx.update(70, "MPFB body generated and reviewed locally");
    }
    const runtime = input.runtime ?? { bodyKey: `${bodyFamily}_${bodyVariant}`, bodyVariant };
    const candidateInput = {
      ...input,
      assetId: input.assetId ?? `body.${bodyFamily}.${bodyVariant}`,
      displayName: input.displayName ?? `${family.displayName ?? bodyFamily} ${bodyVariant.toUpperCase()}`,
      category: "body",
      bodyFamily,
      bodyVariant,
      skeletonId: request.skeletonId,
      bindPoseId: request.bindPoseId,
      outputModel: input.outputModel ?? variant.outputModel,
      qcPath: sourceQc,
      provider: input.provider ?? { name: "MPFB", modelVersion: "2.0.16", seed: "deterministic_recipe" },
      license: input.license ?? {
        name: "CC0-1.0",
        sourceUrl: "https://static.makehumancommunity.org/mpfb/faq/build_other_chargen.html",
      },
      runtime,
    };
    const result = writeCandidate(ctx, candidateInput, sourceModel, { category: "body", runtime });
    return { bodyFamily, bodyVariant, candidate: repoRelative(result.candidatePath), requiresLocalGeneration: false, cost: "free_local_only" };
  }, { assetKeys: [`body-family:${bodyFamily}:${bodyVariant}`] });
}

function startIngestCandidate(input) {
  requireString(input.assetId, "assetId", ASSET_ID_PATTERN);
  requireString(input.bodyFamily, "bodyFamily", SAFE_ID_PATTERN);
  requireVariant(input.bodyVariant);
  const sourceModel = ensureGlb(input.sourcePath, "sourcePath");
  providerRecord(input);
  return startModelJob("ingest_generated_candidate", input, async (ctx) => {
    ctx.update(15, "Hashing local candidate");
    ctx.checkCancelled();
    const result = writeCandidate(ctx, input, sourceModel);
    ctx.update(90, "Candidate manifest and promotion bundle written");
    return {
      candidateId: result.candidate.candidateId,
      candidateManifest: repoRelative(result.candidatePath),
      sourceSha256: result.candidate.source.sha256,
      lifecycleStatus: result.candidate.lifecycle.status,
    };
  }, { assetKeys: [`candidate:${input.assetId}`] });
}

function startBuildModularSet(input) {
  const bodyFamily = requireString(input.bodyFamily, "bodyFamily", SAFE_ID_PATTERN);
  const bodyVariant = requireVariant(input.bodyVariant);
  const setId = requireString(input.setId, "setId", SAFE_ID_PATTERN);
  const provenance = providerRecord({ provenance: input.provenance });
  const bodyModel = requireString(input.bodyModel, "bodyModel");
  const modules = input.modules ?? {};
  const missing = ARMOR_SLOTS.filter((slot) => !modules[slot]);
  const extra = Object.keys(modules).filter((slot) => !ARMOR_SLOTS.includes(slot));
  if (missing.length || extra.length) {
    throw workflowError("UNSEGMENTABLE_CANDIDATE", "A modular set must supply exactly nine independently authored slot GLBs.", { missing, extra });
  }
  const assetKeys = ARMOR_SLOTS.map((slot) => modules[slot].assetId ?? `arm.${bodyFamily}.${setId}.${slot}.${bodyVariant}`);
  return startModelJob("build_modular_set", input, async (ctx) => {
    const skeletonId = input.skeletonId ?? "humanoid_game_v2";
    const bindPoseId = input.bindPoseId ?? "a_pose_v2";
    const assets = [];
    for (const [index, slot] of ARMOR_SLOTS.entries()) {
      ctx.checkCancelled();
      ctx.update(5 + index * 9, `Validating ${slot} module`);
      const module = modules[slot];
      const sourceModel = ensureGlb(module.modelPath, `modules.${slot}.modelPath`);
      if (!module.qcPath) throw workflowError("MODULE_QC_REQUIRED", `Module ${slot} requires a passed QC sidecar.`);
      const assetId = module.assetId ?? `arm.${bodyFamily}.${setId}.${slot}.${bodyVariant}`;
      if (!ASSET_ID_PATTERN.test(assetId) || !assetId.startsWith("arm.")) throw workflowError("INVALID_ASSET_ID", `Invalid armor assetId: ${assetId}`);
      const outputModel = module.outputModel ?? `${assetId.replace(/\./g, "_")}.glb`;
      const moduleDir = path.join(ctx.artifactDir, "modules", slot);
      const stagedModel = copyInto(sourceModel, path.join(moduleDir, outputModel));
      const modelSha256 = sha256File(stagedModel);
      const stagedQc = qcWithBoundHash(
        module.qcPath,
        path.join(moduleDir, outputModel.replace(/\.glb$/i, ".qc.json")),
        assetId,
        outputModel,
        modelSha256,
      );
      const runtime = {
        itemKey: module.itemKey ?? `${setId}_${slot}`,
        bodyVariant,
        bodyModel,
        skinned: module.skinned ?? true,
        coveredRegions: module.coveredRegions ?? [slot],
      };
      assets.push({
        assetId,
        displayName: module.displayName ?? `${setId} ${slot}`,
        category: "armor",
        slot,
        sourceModel: repoRelative(stagedModel),
        sourceQc: repoRelative(stagedQc),
        outputModel,
        modelSha256,
        runtime,
        compatibility: { bodyFamily, bodyVariant, skeletonId, bindPoseId },
        provenance: { ...provenance, sourceHashes: [modelSha256] },
      });
      ctx.addArtifact(stagedModel, `armor_${slot}`);
      ctx.addArtifact(stagedQc, `armor_${slot}_qc`);
    }
    const bundle = {
      schemaVersion: 1,
      sourceJobId: ctx.jobId,
      setId,
      bodyFamily,
      bodyVariant,
      skeletonId,
      bindPoseId,
      assets,
      provenance: { ...provenance, sourceHashes: assets.map((asset) => asset.modelSha256) },
      lifecycle: { status: "qc_passed", updatedAt: new Date().toISOString() },
    };
    const bundlePath = path.join(ctx.artifactDir, "promotion-bundle.json");
    writeJsonAtomic(bundlePath, bundle);
    ctx.addArtifact(bundlePath, "promotion_bundle");
    const candidatePath = path.join(ctx.artifactDir, "modular-set-candidate.json");
    writeJsonAtomic(candidatePath, bundle);
    ctx.addArtifact(candidatePath, "modular_set_candidate");
    return { setId, moduleCount: assets.length, bundle: repoRelative(bundlePath), lifecycleStatus: "qc_passed" };
  }, { assetKeys });
}

function startValidateModel(input) {
  const ref = input.ref ? String(input.ref) : null;
  const modelPath = input.modelPath ? ensureGlb(input.modelPath, "modelPath") : null;
  if (!ref && !modelPath) throw workflowError("INVALID_INPUT", "validate_model_asset requires ref or modelPath.");
  return startModelJob("validate_model_asset", input, async (ctx) => {
    ctx.update(20, "Running strict integrity validation");
    let results;
    if (ref) {
      findBlueprint(ref);
      results = validateBlueprints({ strict: input.strict !== false, refs: [ref] });
    } else {
      const errors = [];
      const actualHash = sha256File(modelPath);
      if (!input.qcPath) errors.push("A QC sidecar is required for strict model validation.");
      else {
        const qcPath = resolveRepoPath(input.qcPath, "qcPath");
        if (!existsSync(qcPath)) errors.push(`QC sidecar is missing: ${input.qcPath}`);
        else {
          const qc = readJson(qcPath);
          if (qc.qcPassed !== true) errors.push("QC sidecar did not pass.");
          if (qc.modelSha256 !== actualHash) errors.push("QC modelSha256 is missing or stale.");
          for (const preview of qc.previewImages ?? []) {
            const previewPath = resolveRepoPath(preview, "QC preview");
            if (!existsSync(previewPath)) errors.push(`QC preview is missing: ${preview}`);
          }
          if (!(qc.previewImages?.length > 0)) errors.push("QC preview evidence is missing.");
        }
      }
      results = [{ ok: errors.length === 0, assetId: input.assetId ?? path.basename(modelPath), filePath: modelPath, errors }];
    }
    const report = {
      schemaVersion: 1,
      strict: input.strict !== false,
      checkedAt: new Date().toISOString(),
      ok: results.every((result) => result.ok),
      results,
    };
    const reportPath = path.join(ctx.artifactDir, "validation-report.json");
    writeJsonAtomic(reportPath, report);
    ctx.addArtifact(reportPath, "validation_report");
    if (!report.ok) {
      throw workflowError("MODEL_VALIDATION_FAILED", `${results.filter((result) => !result.ok).length} validation record(s) failed.`, {
        report: repoRelative(reportPath),
      });
    }
    return { report: repoRelative(reportPath), checkedRecords: results.length };
  }, { assetKeys: ref ? [`validate:${ref}`] : [`validate:${repoRelative(modelPath)}`] });
}

function modelForReview(input) {
  if (input.modelPath) return ensureGlb(input.modelPath, "modelPath");
  if (input.ref) {
    const { blueprint } = findBlueprint(input.ref);
    const modelPath = outputPathFor(blueprint);
    if (!existsSync(modelPath)) throw workflowError("MODEL_SOURCE_MISSING", `Generated model is missing: ${blueprint.output.model}`);
    return modelPath;
  }
  if (input.sourceJobId) {
    const { bundle } = readJobBundle(input.sourceJobId);
    const asset = input.assetId ? bundle.assets.find((entry) => entry.assetId === input.assetId) : bundle.assets[0];
    if (!asset) throw workflowError("BUNDLE_ASSET_NOT_FOUND", `No matching asset in ${input.sourceJobId}.`);
    return ensureGlb(asset.sourceModel, "bundle sourceModel");
  }
  throw workflowError("INVALID_INPUT", "render_model_review requires modelPath, ref, or sourceJobId.");
}

function startRenderReview(input) {
  if (!["bare_body", "fully_equipped"].includes(input.reviewType)) {
    throw workflowError("INVALID_REVIEW_TYPE", "reviewType must be bare_body or fully_equipped.");
  }
  const animationEvidenceProfile = input.animationEvidenceProfile ?? "midpoint";
  if (!ANIMATION_EVIDENCE_PROFILES.includes(animationEvidenceProfile)) {
    throw workflowError(
      "INVALID_ANIMATION_EVIDENCE_PROFILE",
      `animationEvidenceProfile must be one of: ${ANIMATION_EVIDENCE_PROFILES.join(", ")}.`,
    );
  }
  const modelPath = modelForReview(input);
  return startModelJob("render_model_review", input, async (ctx) => {
    const config = readConfig();
    const blenderPath = config.blenderPath ?? "blender";
    if (path.isAbsolute(blenderPath) && !existsSync(blenderPath)) throw workflowError("BLENDER_NOT_FOUND", `Blender not found at ${blenderPath}.`);
    if (!existsSync(REVIEW_RENDER_SCRIPT)) throw workflowError("REVIEW_RENDERER_MISSING", `Missing review renderer: ${REVIEW_RENDER_SCRIPT}`);
    const outputDir = path.join(ctx.artifactDir, "review-render");
    mkdirSync(outputDir, { recursive: true });
    const args = [
      "--background", "--python", REVIEW_RENDER_SCRIPT, "--",
      "--model", modelPath,
      "--output-dir", outputDir,
      "--review-type", input.reviewType,
      "--resolution", String(input.resolution ?? 768),
      "--animation-evidence-profile", animationEvidenceProfile,
    ];
    if (input.includeAnimations === true) args.push("--include-animations");
    ctx.update(10, "Starting local Blender review render");
    const { stdout, stderr } = await execFilePromise(blenderPath, args, {
      cwd: PIPELINE_ROOT,
      timeout: input.timeoutMs ?? 900_000,
      maxBuffer: 16 * 1024 * 1024,
      signal: ctx.signal,
      windowsHide: true,
    });
    ctx.checkCancelled();
    const manifestPath = path.join(outputDir, "review-render.json");
    if (!existsSync(manifestPath)) {
      throw workflowError("REVIEW_RENDER_MISSING", "Blender did not write review-render.json.", {
        stdout: stdout.slice(-6000),
        stderr: stderr.slice(-6000),
      });
    }
    const manifest = readJson(manifestPath);
    const viewFiles = Object.fromEntries(Object.entries(manifest.views ?? {}).map(([view, file]) => {
      const resolved = assertPathWithin(outputDir, path.join(outputDir, file), "review view");
      if (!existsSync(resolved)) throw workflowError("REVIEW_VIEW_MISSING", `Review render is missing ${view}.`);
      return [view, { path: repoRelative(resolved), sha256: sha256File(resolved) }];
    }));
    const animationFrames = (manifest.animationFrames ?? []).map((frame) => {
      const resolved = assertPathWithin(outputDir, path.join(outputDir, frame.image), "animation review frame");
      if (!existsSync(resolved)) throw workflowError("ANIMATION_REVIEW_MISSING", `Animation review image is missing: ${frame.image}`);
      return { ...frame, path: repoRelative(resolved), sha256: sha256File(resolved) };
    });
    const requiredClips = input.requiredClips ?? REQUIRED_CLIPS;
    const renderedClips = new Set(animationFrames.map((frame) => frame.clip));
    const missingRequiredClips = input.includeAnimations === true ? requiredClips.filter((clip) => !renderedClips.has(clip)) : requiredClips;
    const review = {
      ...manifest,
      modelPath: repoRelative(modelPath),
      modelSha256: sha256File(modelPath),
      views: viewFiles,
      animationFrames,
      requiredClips,
      missingRequiredClips,
      renderedAt: new Date().toISOString(),
      renderer: { name: "blender_local", version: String(config.blenderVersion ?? "configured") },
      log: { stdout: stdout.slice(-4000), stderr: stderr.slice(-4000) },
    };
    writeJsonAtomic(manifestPath, review);
    ctx.addArtifact(manifestPath, "review_manifest");
    for (const value of Object.values(viewFiles)) ctx.addArtifact(resolveRepoPath(value.path), "review_image");
    for (const frame of animationFrames) ctx.addArtifact(resolveRepoPath(frame.path), "animation_review_image");
    return {
      reviewType: input.reviewType,
      manifest: repoRelative(manifestPath),
      views: Object.keys(viewFiles),
      animationCoveragePassed: missingRequiredClips.length === 0,
      missingRequiredClips,
      animationEvidenceProfile,
      animationFrameCount: animationFrames.length,
    };
  }, { assetKeys: [`review:${repoRelative(modelPath)}`] });
}

function readRenderJob(jobId, expectedType) {
  const job = modelJobStore.get(jobId);
  if (job.status !== "completed") throw workflowError("REVIEW_RENDER_INCOMPLETE", `Review render ${jobId} is ${job.status}.`);
  const manifestPath = locateFile(modelJobStore.jobDir(jobId), "review-render.json");
  if (!manifestPath) throw workflowError("REVIEW_RENDER_MISSING", `Review render ${jobId} has no manifest.`);
  const manifest = readJson(manifestPath);
  if (manifest.reviewType !== expectedType) throw workflowError("REVIEW_TYPE_MISMATCH", `Expected ${expectedType} evidence from ${jobId}.`);
  for (const view of ["front", "side", "back", "isometric"]) {
    const evidence = manifest.views?.[view];
    if (!evidence?.path) throw workflowError("REVIEW_VIEW_MISSING", `${expectedType} evidence is missing ${view}.`);
    const filePath = resolveRepoPath(evidence.path, "review evidence");
    if (!existsSync(filePath) || sha256File(filePath) !== evidence.sha256) {
      throw workflowError("REVIEW_HASH_MISMATCH", `${expectedType} ${view} evidence changed after rendering.`);
    }
  }
  return { manifest, manifestPath, manifestSha256: sha256File(manifestPath) };
}

export function recordModelReview(input) {
  const targetJobId = requireString(input.targetJobId, "targetJobId");
  const reviewer = requireString(input.reviewer, "reviewer");
  if (!["approved", "rejected"].includes(input.decision)) throw workflowError("INVALID_REVIEW_DECISION", "decision must be approved or rejected.");
  const { bundle, bundlePath } = readJobBundle(targetJobId);
  let bare = null;
  let equipped = null;
  if (input.decision === "approved") {
    bare = readRenderJob(requireString(input.bareBodyRenderJobId, "bareBodyRenderJobId"), "bare_body");
    equipped = readRenderJob(requireString(input.equippedRenderJobId, "equippedRenderJobId"), "fully_equipped");
    if ((equipped.manifest.missingRequiredClips ?? REQUIRED_CLIPS).length > 0) {
      throw workflowError("ANIMATION_REVIEW_INCOMPLETE", "All required animation clips need review evidence.", {
        missing: equipped.manifest.missingRequiredClips,
      });
    }
    const checks = input.checks ?? {};
    for (const check of ["anatomyNatural", "materialsPbr", "seamsAcceptable", "clippingAcceptable", "animationsAcceptable"]) {
      if (checks[check] !== true) throw workflowError("REVIEW_CHECK_INCOMPLETE", `Approval requires checks.${check}: true.`);
    }
  }
  const now = new Date().toISOString();
  const record = {
    schemaVersion: 1,
    targetJobId,
    bundlePath: repoRelative(bundlePath),
    bundleSha256: reviewedBundleSha256(bundle),
    decision: input.decision,
    reviewer,
    reviewedAt: now,
    checks: input.checks ?? {},
    notes: input.notes ?? "",
    evidence: input.decision === "approved" ? {
      bareBody: { path: repoRelative(bare.manifestPath), sha256: bare.manifestSha256 },
      fullyEquipped: { path: repoRelative(equipped.manifestPath), sha256: equipped.manifestSha256 },
    } : {},
  };
  const reviewHash = sha256Json(record);
  record.reviewHash = reviewHash;
  const targetDir = modelJobStore.jobDir(targetJobId);
  const reviewPath = path.join(targetDir, "artifacts", "review", "review.json");
  writeJsonAtomic(reviewPath, record);
  const jobRecord = modelJobStore.read(targetJobId);
  const artifact = { kind: "human_review", path: repoRelative(reviewPath) };
  modelJobStore.update(targetJobId, {
    artifacts: [...(jobRecord.artifacts ?? []).filter((entry) => entry.path !== artifact.path), artifact],
    review: { decision: input.decision, reviewer, reviewedAt: now, reviewHash },
  });
  bundle.lifecycle = { status: input.decision, updatedAt: now, reviewHash };
  writeJsonAtomic(bundlePath, bundle);
  return { targetJobId, decision: input.decision, reviewHash, reviewPath: repoRelative(reviewPath) };
}

function promotionEvidence(targetJobId) {
  const reviewPath = path.join(modelJobStore.jobDir(targetJobId), "artifacts", "review", "review.json");
  if (!existsSync(reviewPath)) throw workflowError("REVIEW_REQUIRED", `Job ${targetJobId} has no recorded review.`);
  const review = readJson(reviewPath);
  if (review.decision !== "approved") throw workflowError("APPROVAL_REQUIRED", `Job ${targetJobId} is not approved.`);
  const { reviewHash, ...unsignedReview } = review;
  if (sha256Json(unsignedReview) !== reviewHash) throw workflowError("REVIEW_HASH_MISMATCH", "The recorded review changed after approval.");
  const barePath = resolveRepoPath(review.evidence.bareBody?.path, "bare-body review manifest");
  const equippedPath = resolveRepoPath(review.evidence.fullyEquipped?.path, "equipped review manifest");
  if (sha256File(barePath) !== review.evidence.bareBody.sha256 || sha256File(equippedPath) !== review.evidence.fullyEquipped.sha256) {
    throw workflowError("REVIEW_HASH_MISMATCH", "A review render manifest changed after approval.");
  }
  const bare = readJson(barePath);
  const equipped = readJson(equippedPath);
  return { review, reviewPath, bare, equipped };
}

function safeEvidenceKeyPart(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, "_")
    .replace(/^_+|_+$/g, "") || "sample";
}

export function evidenceFiles(manifest, prefix) {
  const values = [];
  for (const [view, evidence] of Object.entries(manifest.views ?? {})) values.push({ key: `${prefix}_${view}`, ...evidence });
  const frames = manifest.animationFrames ?? [];
  const clipsWithPrimary = new Set(frames.filter((frame) => frame.primary === true).map((frame) => frame.clip));
  const seenClips = new Set();
  const usedKeys = new Set(values.map((value) => value.key));
  for (const [index, frame] of frames.entries()) {
    const baseKey = `animation_${safeEvidenceKeyPart(frame.clip)}`;
    const firstLegacySample = !clipsWithPrimary.has(frame.clip) && !seenClips.has(frame.clip);
    const useBaseKey = (frame.primary === true || firstLegacySample) && !usedKeys.has(baseKey);
    const suffix = [frame.view, frame.sampleId]
      .filter((value) => value !== undefined && value !== null && value !== "")
      .map(safeEvidenceKeyPart)
      .join("_") || `frame_${safeEvidenceKeyPart(frame.frame ?? index)}`;
    const preferredKey = useBaseKey ? baseKey : `${baseKey}_${suffix}`;
    let key = preferredKey;
    let collision = 2;
    while (usedKeys.has(key)) key = `${preferredKey}_${collision++}`;
    values.push({ key, path: frame.path, sha256: frame.sha256 });
    usedKeys.add(key);
    seenClips.add(frame.clip);
  }
  return values;
}

function promotionQcErrors(asset, qc) {
  const errors = [];
  if (qc.qcPassed !== true) errors.push("qcPassed is not true");
  if (qc.modelSha256 !== asset.modelSha256) errors.push("modelSha256 is stale");
  if (["character", "body", "armor"].includes(asset.category)) {
    if ((asset.compatibility?.skeletonId ?? "") !== "humanoid_game_v2") errors.push("asset skeleton is not humanoid_game_v2");
    if ((qc.skeletonId ?? qc.geometry?.skeletonId) !== "humanoid_game_v2") errors.push("QC does not prove humanoid_game_v2");
    if (!Number.isInteger(qc.maxInfluencesObserved) || qc.maxInfluencesObserved > 4) errors.push("QC does not prove a maximum of four bone influences");
    const channels = qc.pbrChannels ?? qc.materialChannels ?? [];
    for (const channel of ["baseColor", "roughness", "metallic", "normal"]) {
      if (!channels.includes(channel)) errors.push(`QC does not prove ${channel}`);
    }
    if (!Number.isInteger(qc.nonManifoldEdges) || qc.nonManifoldEdges > 0) errors.push("QC does not prove manifold topology");
    if (qc.maxTextureResolution > 2048) errors.push("texture resolution exceeds 2K");
  }
  return errors;
}

function startPromoteModelSet(input) {
  const targetJobId = requireString(input.targetJobId, "targetJobId");
  const { bundle } = readJobBundle(targetJobId);
  const assetKeys = bundle.assets.map((asset) => asset.assetId);
  return startModelJob("promote_model_set", input, async (ctx) => {
    ctx.update(5, "Revalidating approval and content hashes");
    const { bundle: freshBundle, bundlePath } = readJobBundle(targetJobId);
    const evidence = promotionEvidence(targetJobId);
    if (evidence.review.bundleSha256 !== reviewedBundleSha256(freshBundle)) {
      throw workflowError("BUNDLE_CHANGED_AFTER_REVIEW", "The promotion bundle changed after human review.");
    }
    const allEvidence = [...evidenceFiles(evidence.bare, "bare"), ...evidenceFiles(evidence.equipped, "equipped")];
    const uniqueEvidence = new Map();
    for (const item of allEvidence) {
      const source = resolveRepoPath(item.path, "review evidence");
      if (!existsSync(source) || sha256File(source) !== item.sha256) throw workflowError("REVIEW_HASH_MISMATCH", `Review evidence changed: ${item.path}`);
      uniqueEvidence.set(item.key, { ...item, source });
    }
    for (const clip of REQUIRED_CLIPS) {
      if (!uniqueEvidence.has(`animation_${clip}`)) throw workflowError("ANIMATION_REVIEW_INCOMPLETE", `Missing approved animation review for ${clip}.`);
    }

    const reviewDirName = targetJobId;
    const finalEvidence = Object.fromEntries([...uniqueEvidence.entries()].map(([key, item]) => {
      const extension = path.extname(item.source).toLowerCase();
      return [key, `reviews/${reviewDirName}/${key}${extension}`];
    }));
    const finalEvidenceHashes = Object.fromEntries([...uniqueEvidence.entries()].map(([key, item]) => [key, item.sha256]));
    const approvedManifests = [];
    const publishEntries = [];
    let equippedTriangles = 0;
    let equippedDrawCalls = 0;
    const stagedApprovedDir = path.join(ctx.stagingDir, "approved-assets");
    mkdirSync(stagedApprovedDir, { recursive: true });

    for (const [index, asset] of freshBundle.assets.entries()) {
      ctx.checkCancelled();
      ctx.update(10 + index * (55 / freshBundle.assets.length), `Verifying ${asset.assetId}`);
      const sourceModel = ensureGlb(asset.sourceModel, "bundle sourceModel");
      if (sha256File(sourceModel) !== asset.modelSha256) throw workflowError("MODEL_HASH_MISMATCH", `${asset.assetId} changed after QC.`);
      if (!asset.sourceQc) throw workflowError("QC_REQUIRED", `${asset.assetId} has no QC sidecar.`);
      const sourceQc = resolveRepoPath(asset.sourceQc, "bundle QC");
      if (!existsSync(sourceQc)) throw workflowError("QC_SOURCE_MISSING", `${asset.assetId} QC is missing.`);
      const qc = readJson(sourceQc);
      const qcErrors = promotionQcErrors(asset, qc);
      if (qcErrors.length) throw workflowError("QC_POLICY_FAILED", `${asset.assetId} is not promotion eligible: ${qcErrors.join("; ")}`, { errors: qcErrors });
      equippedTriangles += Number(qc.totalTris ?? 0);
      equippedDrawCalls += Number(qc.drawCalls ?? qc.meshCount ?? 0);
      const outputModel = asset.outputModel;
      if (!/^[a-z0-9_.-]+\.glb$/.test(outputModel)) throw workflowError("INVALID_OUTPUT_MODEL", `Invalid model output: ${outputModel}`);
      const outputQc = outputModel.replace(/\.glb$/i, ".qc.json");
      const approved = {
        schemaVersion: 1,
        assetId: asset.assetId,
        displayName: asset.displayName ?? asset.assetId,
        category: asset.category,
        model: outputModel,
        qc: outputQc,
        runtime: asset.runtime,
        compatibility: asset.compatibility,
        hashes: {
          modelSha256: asset.modelSha256,
          qcSha256: sha256File(sourceQc),
          previews: finalEvidenceHashes,
        },
        previews: finalEvidence,
        provenance: asset.provenance ?? {},
        review: {
          reviewedBy: evidence.review.reviewer,
          reviewedAt: evidence.review.reviewedAt,
          reviewHash: evidence.review.reviewHash,
        },
        approvalState: "approved",
      };
      approvedManifests.push(approved);
      const approvedPath = path.join(stagedApprovedDir, `${asset.assetId.replace(/\./g, "_")}.approved.json`);
      writeJsonAtomic(approvedPath, approved);
      publishEntries.push(
        { source: sourceModel, destination: path.join(MODEL_DIR, outputModel), sha256: asset.modelSha256 },
        { source: sourceQc, destination: path.join(MODEL_DIR, outputQc), sha256: approved.hashes.qcSha256 },
        { source: approvedPath, destination: path.join(APPROVED_ASSET_DIR, path.basename(approvedPath)), sha256: sha256File(approvedPath) },
      );
    }
    if (equippedTriangles > 120_000) {
      throw workflowError("TRIANGLE_BUDGET_EXCEEDED", `Equipped set has ${equippedTriangles} triangles; maximum is 120000.`);
    }
    if (equippedDrawCalls > 16) {
      throw workflowError("DRAW_CALL_BUDGET_EXCEEDED", `Equipped set has ${equippedDrawCalls} draw calls; maximum is 16.`);
    }
    for (const [key, item] of uniqueEvidence) {
      publishEntries.push({
        source: item.source,
        destination: path.join(MODEL_DIR, finalEvidence[key]),
        sha256: item.sha256,
      });
    }
    ctx.update(72, "Compiling deterministic approved-only runtime registry");
    const registry = compileRuntimeRegistry({ additionalManifests: approvedManifests });
    const registryPath = path.join(ctx.stagingDir, "asset-index.json");
    writeJsonAtomic(registryPath, registry);
    publishEntries.push({ source: registryPath, destination: ASSET_INDEX_PATH, sha256: sha256File(registryPath) });
    ctx.update(82, "Publishing approved files atomically");
    freshBundle.lifecycle = {
      status: "promoted",
      updatedAt: new Date().toISOString(),
      reviewHash: evidence.review.reviewHash,
      promotionJobId: ctx.jobId,
    };
    const promotedBundlePath = path.join(ctx.stagingDir, "promoted-bundle.json");
    writeJsonAtomic(promotedBundlePath, freshBundle);
    publishEntries.push({ source: promotedBundlePath, destination: bundlePath, sha256: sha256File(promotedBundlePath) });
    atomicPublishSet(publishEntries, { transactionDir: path.join(ctx.jobDir, "publish") });
    return {
      promotedAssetIds: freshBundle.assets.map((asset) => asset.assetId),
      registry: repoRelative(ASSET_INDEX_PATH),
      assetVersion: registry.assetVersion,
    };
  }, { assetKeys: [...assetKeys, "runtime-registry"] });
}

export function startWorkflowJob(kind, input = {}) {
  switch (kind) {
    case "create_body_family": return startCreateBodyFamily(input);
    case "ingest_generated_candidate": return startIngestCandidate(input);
    case "build_modular_set": return startBuildModularSet(input);
    case "validate_model_asset": return startValidateModel(input);
    case "render_model_review": return startRenderReview(input);
    case "promote_model_set": return startPromoteModelSet(input);
    default: throw workflowError("UNKNOWN_WORKFLOW", `Unknown model workflow: ${kind}`);
  }
}
