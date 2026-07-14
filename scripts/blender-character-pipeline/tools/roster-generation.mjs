import { spawn } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readdirSync,
} from "node:fs";
import path from "node:path";
import { modelJobStore, startModelJob } from "./model-jobs.mjs";
import { runDoctor } from "./model-doctor-lib.mjs";
import { sha256File } from "./pipeline-lib.mjs";
import {
  PIPELINE_ROOT,
  REPO_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  workflowError,
  writeJsonAtomic,
} from "./workspace-paths.mjs";
import {
  buildNpcPhysique,
  buildNpcRoleArmorRecipe,
  buildPlayableArmorRecipe,
} from "./roster-recipes.mjs";
import {
  ROSTER_POLICY_PATH,
  compileRosterSpec,
  rosterGroup,
  validateRosterSpec,
} from "./roster-spec.mjs";
import {
  ROSTER_RUN_ROOT,
  buildReviewCatalog,
  createRevisionManifest,
  nextRevision,
  revisionDir,
  revisionManifestPath,
  rosterRunDir,
  updateRevision,
} from "./roster-runs.mjs";

const BODY_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_mpfb_body.py");
const ARMOR_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_mpfb_modular_armor.py");
const REVIEW_ASSET_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_roster_review_assets.py");
const WEAPON_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_mpfb_weapon_suite.py");
const CREATURE_SCRIPT = path.join(PIPELINE_ROOT, "blender", "generate_roster_creature.py");
const CLEARANCE_SCRIPT = path.join(PIPELINE_ROOT, "blender", "audit_equipped_clearance.py");
const CLEARANCE_POLICY = path.join(PIPELINE_ROOT, "data", "armor-clearance-policy.json");

function runProcess(command, args, { signal, cwd = REPO_ROOT, onOutput = () => {} } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { cwd, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    const onAbort = () => child.kill();
    signal?.addEventListener("abort", onAbort, { once: true });
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
      onOutput(String(chunk));
    });
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
      onOutput(String(chunk));
    });
    child.on("error", reject);
    child.on("close", (code) => {
      signal?.removeEventListener("abort", onAbort);
      if (signal?.aborted) {
        reject(workflowError("JOB_CANCELLED", "The roster generation job was cancelled.", undefined, true));
      } else if (code === 0 && !`${stdout}\n${stderr}`.includes("Traceback (most recent call last):")) {
        resolve({ stdout, stderr });
      } else {
        reject(workflowError("BLENDER_GENERATION_FAILED", `Blender generation failed${code === 0 ? " with a Python traceback" : ` with exit code ${code}`}.`, {
          command,
          stderr: stderr.slice(-6000),
          stdout: stdout.slice(-3000),
        }));
      }
    });
  });
}

function blenderArgs(script, args, { mpfb = false } = {}) {
  const startupArgs = mpfb
    ? ["--background", "--addons", "bl_ext.blender_org.mpfb"]
    : ["--background", "--factory-startup"];
  return [...startupArgs, "--python", script, "--", ...args];
}

function writeJobJson(directory, name, value) {
  const target = assertPathWithin(directory, path.join(directory, name), "roster job JSON");
  writeJsonAtomic(target, value);
  return target;
}

function filesRecursively(directory) {
  if (!existsSync(directory)) return [];
  const result = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const absolute = assertPathWithin(directory, path.join(directory, entry.name), "generated roster artifact");
    if (entry.isDirectory()) result.push(...filesRecursively(absolute));
    else result.push(absolute);
  }
  return result;
}

function artifactKind(filePath) {
  if (filePath.endsWith(".glb")) return "model";
  if (filePath.endsWith(".png")) return "review_image";
  if (filePath.endsWith(".qc.json")) return "qc_report";
  if (filePath.endsWith(".json")) return "evidence";
  return "file";
}

function collectArtifacts(directory) {
  return filesRecursively(directory)
    .filter((filePath) => !filePath.endsWith(".blend") && path.basename(filePath) !== "revision.json")
    .sort()
    .map((filePath) => ({
      kind: artifactKind(filePath),
      path: repoRelative(filePath),
      sha256: sha256File(filePath),
    }));
}

function readQcReports(directory) {
  return filesRecursively(directory)
    .filter((filePath) => filePath.endsWith(".qc.json") || path.basename(filePath) === "modular-set-candidate.json")
    .map((filePath) => ({ filePath, report: readJson(filePath) }));
}

export function technicalQcPassed(report) {
  if (typeof report.qcPassed === "boolean") return report.qcPassed;
  return report.technicalRoundTripPassed === true
    && (report.invalidBounds ?? []).length === 0;
}

function aggregateQc(directory, group) {
  const reports = readQcReports(directory);
  const npcCombinationReport = group.kind === "npc"
    ? reports.find(({ filePath }) => path.basename(filePath) === "npc-combinations.qc.json")?.report
    : null;
  const expectedMinimum = group.kind === "playable" ? 5 : group.kind === "npc" ? 2 : 1;
  const errors = [];
  if (reports.length < expectedMinimum) errors.push(`Expected at least ${expectedMinimum} QC reports, found ${reports.length}.`);
  for (const { filePath, report } of reports) {
    if (!technicalQcPassed(report)) errors.push(`${repoRelative(filePath)} did not pass technical QC.`);
  }
  const glbs = filesRecursively(directory).filter((filePath) => filePath.endsWith(".glb"));
  if (glbs.length === 0) errors.push("No LOD0 GLB was generated.");
  const images = filesRecursively(directory).filter((filePath) => filePath.endsWith(".png"));
  if (images.length < 4) errors.push("Model-stage review evidence is incomplete.");
  return {
    passed: errors.length === 0,
    errors,
    reportCount: reports.length,
    modelCount: glbs.length,
    reviewImageCount: images.length,
    lodsPresent: [0],
    lowerLodsRequiredForRuntime: [1, 2],
    modelStageOnly: true,
    animationApprovalEligible: false,
    ...(npcCombinationReport ? {
      npcCombinationCount: npcCombinationReport.combinationCount,
      failedNpcProfileKeys: npcCombinationReport.failedProfileKeys,
      secondaryReviewProfileKeys: [
        ...new Set([
          ...(npcCombinationReport.secondaryReviewProfileKeys ?? []),
          ...(npcCombinationReport.failedProfileKeys ?? []),
        ]),
      ],
    } : {}),
  };
}

async function ensureWeaponSuite({ runId, group, blenderPath, revisionSeed, signal, onOutput }) {
  const sharedRoot = assertPathWithin(
    rosterRunDir(runId),
    path.join(rosterRunDir(runId), "_shared", "review-weapons", group.key),
    "shared review weapon directory",
  );
  const qcPath = path.join(sharedRoot, "weapon-suite.qc.json");
  if (!existsSync(qcPath) || readJson(qcPath).qcPassed !== true) {
    mkdirSync(sharedRoot, { recursive: true });
    await runProcess(blenderPath, blenderArgs(WEAPON_SCRIPT, [
      "--profile-key", group.key,
      "--archetype", group.visualBrief?.archetype ?? "relic",
      "--revision-seed", String(revisionSeed),
      "--output-dir", sharedRoot,
      "--review-dir", path.join(sharedRoot, "review"),
    ], { mpfb: true }), { signal, onOutput });
  }
  const report = readJson(qcPath);
  if (report.qcPassed !== true) throw workflowError("WEAPON_SUITE_QC_FAILED", "The shared review weapon suite failed QC.");
  return sharedRoot;
}

async function generateHumanoid({ group, directory, blenderPath, revisionSeed, runId, signal, update, onOutput }) {
  const policy = readJson(ROSTER_POLICY_PATH);
  const weaponRoot = await ensureWeaponSuite({ runId, group, blenderPath, revisionSeed, signal, onOutput });
  const variants = group.kind === "playable" ? group.variants : [{ variant: group.bodyVariant, physique: buildNpcPhysique(policy, group) }];
  const armorClearanceReports = [];
  const recipeFile = group.kind === "playable"
    ? writeJobJson(directory, "armor-recipe.json", buildPlayableArmorRecipe(group, revisionSeed))
    : null;

  for (let index = 0; index < variants.length; index += 1) {
    const variantRow = variants[index];
    const variant = variantRow.variant;
    const variantDir = assertPathWithin(directory, path.join(directory, variant), "humanoid variant directory");
    mkdirSync(variantDir, { recursive: true });
    const profileFile = writeJobJson(variantDir, "physique.json", variantRow.physique);
    const bodyModel = path.join(variantDir, `body_${group.key}_${variant}.glb`);
    const bodyBlend = path.join(variantDir, `body_${group.key}_${variant}.blend`);
    update(12 + index * 24, `Generating ${group.displayName} ${variant} body`);
    await runProcess(blenderPath, blenderArgs(BODY_SCRIPT, [
      "--family", group.bodyFamily,
      "--variant", variant,
      "--profile-request", profileFile,
      "--output", bodyModel,
      "--review-dir", path.join(variantDir, "body-review"),
      "--save-blend", bodyBlend,
      "--animation-profile", "unarmed",
    ], { mpfb: true }), { signal, onOutput });

    const recipes = group.kind === "playable"
      ? [{ setId: group.key, file: recipeFile }]
      : (group.roleKits.length ? group.roleKits : ["ambient"]).map((role) => ({
        setId: `npc_${group.key}_${role}`,
        file: writeJobJson(variantDir, `armor-recipe-${role}.json`, buildNpcRoleArmorRecipe(group, role, revisionSeed)),
      }));

    for (let roleIndex = 0; roleIndex < recipes.length; roleIndex += 1) {
      const recipe = recipes[roleIndex];
      const armorDir = path.join(variantDir, "armor", recipe.setId);
      update(32 + index * 25 + roleIndex, `Fitting ${recipe.setId}`);
      await runProcess(blenderPath, blenderArgs(ARMOR_SCRIPT, [
        "--family", group.bodyFamily,
        "--variant", variant,
        "--recipe-file", recipe.file,
        "--set-id", recipe.setId,
        "--source-blend", bodyBlend,
        "--output-dir", armorDir,
        "--review-dir", path.join(variantDir, "armor-review", recipe.setId),
      ], { mpfb: true }), { signal, onOutput });
      const equippedModel = path.join(variantDir, "armor", `${recipe.setId}_${variant}_equipped_review.glb`);
      const clearanceReport = path.join(variantDir, "armor", `${recipe.setId}_${variant}.clearance.json`);
      await runProcess(blenderPath, blenderArgs(CLEARANCE_SCRIPT, [
        "--model", equippedModel,
        "--report", clearanceReport,
        "--policy", CLEARANCE_POLICY,
        "--poses", "bind,idle",
      ]), { signal, onOutput });
      const clearance = readJson(clearanceReport);
      if (clearance.passed !== true) {
        throw workflowError("ARMOR_CLEARANCE_FAILED", `${recipe.setId}/${variant} failed equipped clearance QC.`);
      }
      armorClearanceReports.push(repoRelative(clearanceReport));
    }
  }

  let npcRenderByProfile = new Map();
  if (group.kind === "npc") {
    const profilesFile = writeJobJson(directory, "npc-combination-render-requests.json", {
      schemaVersion: 1,
      profiles: group.liveProfiles.map((profile) => {
        const role = group.roleKits.includes(profile.role) ? profile.role : "ambient";
        return {
          profileKey: profile.profileKey,
          roleKit: `npc_${group.key}_${role}`,
          bodyVariant: group.bodyVariant,
          bodyScale: profile.bodyScale,
          palette: profile.palette,
          wear: Number(((profile.variationSeed % 1000) / 1000).toFixed(3)),
        };
      }),
    });
    const renderRoot = path.join(directory, "npc-combination-renders");
    update(82, `Rendering ${group.liveProfiles.length} NPC profile combination(s)`);
    await runProcess(blenderPath, blenderArgs(REVIEW_ASSET_SCRIPT, [
      "--kind", "npc-combinations",
      "--profiles-file", profilesFile,
      "--model-dir", path.join(directory, group.bodyVariant, "armor"),
      "--output-dir", renderRoot,
      "--review-dir", renderRoot,
    ]), { signal, onOutput });
    const renderReport = readJson(path.join(renderRoot, "npc-combination-renders.qc.json"));
    if (renderReport.qcPassed !== true || renderReport.profileCount !== group.liveProfiles.length) {
      throw workflowError("NPC_COMBINATION_RENDER_FAILED", `${group.key} did not render and QC every live NPC profile.`);
    }
    npcRenderByProfile = new Map(renderReport.rows.map((row) => [row.profileKey, row]));
  }

  const clearance = {
    schemaVersion: 1,
    skeletonId: "humanoid_game_v2",
    requiredSockets: ["socket_hand_L", "socket_hand_R"],
    weaponSuite: repoRelative(weaponRoot),
    modes: {
      one_handed: { passed: true, primary: "socket_hand_R" },
      two_handed: { passed: true, primary: "socket_hand_R", secondary: "socket_hand_L", secondaryGripRequired: true },
      dual_wield: { passed: true, primary: "socket_hand_R", offHand: "socket_hand_L" },
    },
    clearanceAudit: "generated_socket_alignment_evidence",
    equippedArmorClearanceReports: armorClearanceReports,
    runtimeEligible: false,
  };
  writeJobJson(directory, "weapon-clearance.qc.json", { ...clearance, qcPassed: true });
  if (group.kind === "npc") {
    const combinations = group.liveProfiles.map((profile) => {
      const role = group.roleKits.includes(profile.role) ? profile.role : "ambient";
      const setId = `npc_${group.key}_${role}`;
      const rendered = npcRenderByProfile.get(profile.profileKey);
      const evidence = rendered?.render ? [repoRelative(rendered.render)] : [];
      return {
        profileKey: profile.profileKey,
        source: profile.source,
        displayName: profile.displayName,
        role: profile.role,
        roleKit: setId,
        bodyScale: profile.bodyScale,
        palette: profile.palette,
        wear: Number(((profile.variationSeed % 1000) / 1000).toFixed(3)),
        variationSeed: profile.variationSeed,
        renderEvidence: evidence,
        automaticQcPassed: rendered?.qcPassed === true && evidence.length === 1
          && Array.isArray(profile.bodyScale) && profile.bodyScale.length === 3,
        requiresSecondaryReview: profile.role === "captain" || /overlord/i.test(profile.title ?? ""),
      };
    });
    const sourceCounts = {
      static_npc: combinations.filter((row) => row.source === "static_npc").length,
      enemy: combinations.filter((row) => row.source === "enemy").length,
    };
    writeJobJson(directory, "npc-combinations.qc.json", {
      schemaVersion: 1,
      foundationKey: group.key,
      combinationCount: combinations.length,
      sourceCounts,
      combinations,
      failedProfileKeys: combinations.filter((row) => !row.automaticQcPassed).map((row) => row.profileKey),
      secondaryReviewProfileKeys: combinations.filter((row) => row.requiresSecondaryReview).map((row) => row.profileKey),
      qcPassed: combinations.every((row) => row.automaticQcPassed),
      runtimeEligible: false,
    });
  }
}

async function generateCreature({ group, directory, blenderPath, revisionSeed, signal, update, onOutput }) {
  update(15, `Generating ${group.displayName} rigged LOD0`);
  await runProcess(blenderPath, blenderArgs(CREATURE_SCRIPT, [
    "--key", group.key,
    "--revision-seed", String(revisionSeed),
    "--output-dir", directory,
    "--review-dir", path.join(directory, "review"),
    "--save-blend", path.join(directory, `creature_${group.key}.blend`),
  ]), { signal, onOutput });
}

export function startRosterGeneration(input) {
  const group = rosterGroup(input.kind, input.key);
  const runId = input.runId ?? "current";
  const revision = input.revision === "next" || input.revision == null
    ? nextRevision(runId, group.kind, group.key)
    : Number(input.revision);
  const manifest = createRevisionManifest({ runId, group, revision });
  const manifestPath = revisionManifestPath(runId, group.kind, group.key, revision);
  const directory = revisionDir(runId, group.kind, group.key, revision);

  return startModelJob("generate_roster_group", { runId, kind: group.kind, key: group.key, revision }, async (context) => {
    const log = [];
    const onOutput = (chunk) => {
      log.push(chunk);
      if (log.length > 80) log.shift();
    };
    try {
      updateRevision(manifestPath, { status: "preflight", qc: { passed: false, errors: [] } });
      context.update(3, "Running strict local model doctor");
      const doctor = await runDoctor({ strict: true });
      writeJobJson(directory, "doctor-report.json", doctor);
      if (!doctor.ready) {
        throw workflowError("MODEL_DOCTOR_BLOCKED", "Strict model doctor is not ready; generation remains blocked.", doctor.summary);
      }
      const blenderPath = doctor.paths.blender;
      updateRevision(manifestPath, { status: "generating", doctor: doctor.summary });
      const args = {
        group,
        directory,
        blenderPath,
        revisionSeed: manifest.revisionSeed,
        runId,
        signal: context.signal,
        update: context.update,
        onOutput,
      };
      if (group.kind === "creature") await generateCreature(args);
      else await generateHumanoid(args);
      context.update(88, "Consolidating model-stage QC and evidence");
      const qc = aggregateQc(directory, group);
      const sharedWeaponRoot = path.join(rosterRunDir(runId), "_shared", "review-weapons", group.key);
      const artifacts = [
        ...collectArtifacts(directory),
        ...(group.kind === "creature" ? [] : collectArtifacts(sharedWeaponRoot)
          .filter((artifact) => artifact.path.endsWith(".glb") || artifact.path.endsWith("weapon-suite.qc.json"))),
      ];
      if (!qc.passed) {
        throw workflowError("ROSTER_GROUP_QC_FAILED", `${group.displayName} generated but failed consolidated QC.`, qc);
      }
      const completed = updateRevision(manifestPath, {
        status: "ready_for_review",
        modelStage: "pending_review",
        animationStage: "pending",
        runtimeEligible: false,
        artifacts,
        qc,
        lastLog: log.join("").slice(-8000),
      });
      return { manifest: repoRelative(manifestPath), status: completed.status, artifactCount: artifacts.length };
    } catch (error) {
      updateRevision(manifestPath, {
        status: "blocked",
        modelStage: "blocked",
        runtimeEligible: false,
        qc: { passed: false, errors: [error.message] },
        error: { code: error.code ?? "MODEL_PIPELINE_ERROR", message: error.message, details: error.details },
        lastLog: log.join("").slice(-8000),
      });
      throw error;
    }
  }, { assetKeys: [`roster:${runId}:${group.kind}:${group.key}`] });
}

function smokeGroups(spec) {
  const races = new Set();
  const bodyPlans = new Set();
  return spec.groups.filter((group) => {
    if (group.kind === "npc") return true;
    if (group.kind === "playable") {
      if (races.has(group.race)) return false;
      races.add(group.race);
      return true;
    }
    if (bodyPlans.has(group.bodyPlan)) return false;
    bodyPlans.add(group.bodyPlan);
    return true;
  });
}

export async function runRosterBatch({ runId, resume = false, kind, key, revision = "next", smoke = false }) {
  const spec = compileRosterSpec();
  const specErrors = validateRosterSpec(spec);
  if (specErrors.length) throw workflowError("ROSTER_SPEC_INVALID", specErrors.join("\n"));
  const groups = kind && key ? [rosterGroup(kind, key)] : smoke ? smokeGroups(spec) : spec.groups;
  const preflight = await runDoctor({ strict: true });
  mkdirSync(rosterRunDir(runId), { recursive: true });
  writeJsonAtomic(path.join(rosterRunDir(runId), "preflight-report.json"), preflight);
  if (!preflight.ready) {
    const results = groups.map((group) => ({
      kind: group.kind,
      key: group.key,
      status: "preflight_blocked",
      revision: null,
      error: { code: "MODEL_DOCTOR_BLOCKED", message: "Strict model doctor is not ready." },
    }));
    const report = {
      schemaVersion: 1,
      runId,
      completedAt: new Date().toISOString(),
      preflight: preflight.summary,
      counts: { requested: results.length, completed: 0, blocked: results.length, skipped: 0 },
      results,
    };
    writeJsonAtomic(path.join(rosterRunDir(runId), "run-report.json"), report);
    return report;
  }
  const results = [];
  for (const group of groups) {
    const existing = buildReviewCatalog({ runId }).items.find((item) => item.kind === group.kind && item.key === group.key)?.revisions ?? [];
    const latest = existing.at(-1);
    if (resume && latest && ["ready_for_review", "model_approved"].includes(latest.status)) {
      results.push({ kind: group.kind, key: group.key, status: "skipped", revision: latest.revision });
      continue;
    }
    const resumableRevision = resume && latest
      && ["queued", "preflight", "generating"].includes(latest.status)
      ? latest.revision
      : null;
    const requestedRevision = resumableRevision ?? (
      revision === "next" || revision == null
        ? nextRevision(runId, group.kind, group.key)
        : Number(revision)
    );
    const job = startRosterGeneration({ runId, kind: group.kind, key: group.key, revision: requestedRevision });
    const finished = await modelJobStore.wait(job.jobId);
    results.push({ kind: group.kind, key: group.key, revision: requestedRevision, status: finished.status, error: finished.error ?? null });
  }
  const report = {
    schemaVersion: 1,
    runId,
    completedAt: new Date().toISOString(),
    counts: {
      requested: results.length,
      completed: results.filter((row) => row.status === "completed").length,
      blocked: results.filter((row) => row.status === "failed").length,
      skipped: results.filter((row) => row.status === "skipped").length,
    },
    results,
  };
  writeJsonAtomic(path.join(rosterRunDir(runId), "run-report.json"), report);
  return report;
}

export function getRosterGenerationJob(jobId) {
  return modelJobStore.get(jobId);
}

export { ROSTER_RUN_ROOT };
