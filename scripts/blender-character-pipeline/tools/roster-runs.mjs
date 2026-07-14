import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  renameSync,
  rmSync,
} from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import {
  JOB_ROOT,
  REPO_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  workflowError,
  writeJsonAtomic,
} from "./workspace-paths.mjs";
import { compileRosterSpec } from "./roster-spec.mjs";
import { sha256File, sha256Json } from "./pipeline-lib.mjs";

export const ROSTER_RUN_ROOT = path.join(JOB_ROOT, "roster-runs");
export const MODEL_STAGE_ROOT = path.join(REPO_ROOT, "authoring", "approved", "model-stage");
const SAFE_ID = /^[a-z0-9][a-z0-9_.-]*$/;

function safeId(value, label) {
  if (typeof value !== "string" || !SAFE_ID.test(value)) {
    throw workflowError("INVALID_ROSTER_ID", `${label} must match ${SAFE_ID}.`);
  }
  return value;
}

export function rosterRunDir(runId, root = ROSTER_RUN_ROOT) {
  return assertPathWithin(root, path.join(root, safeId(runId, "runId")), "roster run directory");
}

export function rosterGroupDir(runId, kind, key, root = ROSTER_RUN_ROOT) {
  if (!["playable", "npc", "creature"].includes(kind)) throw workflowError("INVALID_ROSTER_KIND", `Invalid roster kind: ${kind}.`);
  return assertPathWithin(
    rosterRunDir(runId, root),
    path.join(rosterRunDir(runId, root), kind, safeId(key, "key")),
    "roster group directory",
  );
}

export function revisionDir(runId, kind, key, revision, root = ROSTER_RUN_ROOT) {
  if (!Number.isInteger(revision) || revision < 1) throw workflowError("INVALID_REVISION", "revision must be a positive integer.");
  return assertPathWithin(
    rosterGroupDir(runId, kind, key, root),
    path.join(rosterGroupDir(runId, kind, key, root), `revision-${String(revision).padStart(4, "0")}`),
    "roster revision directory",
  );
}

export function listRevisions(runId, kind, key, root = ROSTER_RUN_ROOT) {
  const groupDir = rosterGroupDir(runId, kind, key, root);
  if (!existsSync(groupDir)) return [];
  return readdirSync(groupDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^revision-\d{4}$/.test(entry.name))
    .map((entry) => Number(entry.name.slice("revision-".length)))
    .sort((left, right) => left - right);
}

export function nextRevision(runId, kind, key, root = ROSTER_RUN_ROOT) {
  const revisions = listRevisions(runId, kind, key, root);
  return revisions.length ? revisions.at(-1) + 1 : 1;
}

export function revisionManifestPath(runId, kind, key, revision, root = ROSTER_RUN_ROOT) {
  return path.join(revisionDir(runId, kind, key, revision, root), "revision.json");
}

export function createRevisionManifest({ runId, group, revision, root = ROSTER_RUN_ROOT }) {
  const directory = revisionDir(runId, group.kind, group.key, revision, root);
  const manifestPath = path.join(directory, "revision.json");
  if (existsSync(manifestPath)) return readJson(manifestPath);
  mkdirSync(directory, { recursive: true });
  const now = new Date().toISOString();
  const manifest = {
    schemaVersion: 1,
    runId,
    kind: group.kind,
    key: group.key,
    displayName: group.displayName,
    revision,
    revisionSeed: Number.parseInt(createHash("sha256").update(`${runId}:${group.kind}:${group.key}:${revision}`).digest("hex").slice(0, 8), 16),
    status: "queued",
    modelStage: "pending",
    animationStage: "pending",
    runtimeEligible: false,
    group,
    artifacts: [],
    qc: { passed: false, errors: [] },
    createdAt: now,
    updatedAt: now,
  };
  writeJsonAtomic(manifestPath, manifest);
  return manifest;
}

export function updateRevision(manifestPath, patch) {
  const current = readJson(manifestPath);
  const next = { ...current, ...patch, updatedAt: new Date().toISOString() };
  writeJsonAtomic(manifestPath, next);
  return next;
}

function availableRunIds(root) {
  if (!existsSync(root)) return [];
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && SAFE_ID.test(entry.name))
    .map((entry) => entry.name)
    .sort();
}

export function buildReviewCatalog({ runId, root = ROSTER_RUN_ROOT } = {}) {
  const spec = compileRosterSpec();
  const selectedRunId = runId ?? availableRunIds(root).at(-1) ?? "default";
  return {
    schemaVersion: 1,
    runId: selectedRunId,
    counts: spec.counts,
    items: spec.groups.map((group) => {
      const revisions = listRevisions(selectedRunId, group.kind, group.key, root).map((revision) => {
        const manifestPath = revisionManifestPath(selectedRunId, group.kind, group.key, revision, root);
        return existsSync(manifestPath) ? readJson(manifestPath) : null;
      }).filter(Boolean);
      return { kind: group.kind, key: group.key, displayName: group.displayName, group, revisions };
    }),
  };
}

function verifyArtifacts(manifest) {
  if (!Array.isArray(manifest.artifacts) || manifest.artifacts.length === 0) {
    throw workflowError("MODEL_STAGE_ARTIFACTS_REQUIRED", "Approval requires generated model-stage artifacts.");
  }
  for (const artifact of manifest.artifacts) {
    const source = assertPathWithin(REPO_ROOT, path.resolve(REPO_ROOT, artifact.path), "review artifact");
    if (!existsSync(source)) throw workflowError("MODEL_STAGE_ARTIFACT_MISSING", `Missing artifact: ${artifact.path}.`);
    if (sha256File(source) !== artifact.sha256) throw workflowError("MODEL_STAGE_HASH_MISMATCH", `Artifact changed: ${artifact.path}.`);
  }
}

function requiredChecks(manifest, policy) {
  return manifest.kind === "creature" ? policy.requiredCreatureChecks : policy.requiredHumanoidChecks;
}

function appendAudit(root, kind, key, record) {
  const auditPath = assertPathWithin(root, path.join(root, "history", `${kind}_${key}.json`), "model-stage audit path");
  const current = existsSync(auditPath) ? readJson(auditPath) : { schemaVersion: 1, entries: [] };
  writeJsonAtomic(auditPath, { ...current, entries: [...current.entries, record] });
}

function freezeAuthoring(manifest, review, authoringRoot) {
  verifyArtifacts(manifest);
  mkdirSync(authoringRoot, { recursive: true });
  const canonical = assertPathWithin(authoringRoot, path.join(authoringRoot, manifest.kind, manifest.key), "canonical authoring bundle");
  const staging = assertPathWithin(authoringRoot, path.join(authoringRoot, ".staging", `${manifest.kind}_${manifest.key}_${Date.now()}`), "authoring staging directory");
  mkdirSync(staging, { recursive: true });
  const frozenArtifacts = [];
  for (const artifact of manifest.artifacts) {
    const source = assertPathWithin(REPO_ROOT, path.resolve(REPO_ROOT, artifact.path), "authoring source");
    const frozenName = `${artifact.kind}_${artifact.sha256.slice(0, 12)}_${path.basename(source)}`;
    const destination = assertPathWithin(staging, path.join(staging, frozenName), "authoring destination");
    copyFileSync(source, destination);
    frozenArtifacts.push({ kind: artifact.kind, file: path.basename(destination), sha256: artifact.sha256 });
  }
  const approved = {
    schemaVersion: 1,
    kind: manifest.kind,
    key: manifest.key,
    displayName: manifest.displayName,
    sourceRunId: manifest.runId,
    sourceRevision: manifest.revision,
    sourceManifestSha256: sha256Json(manifest),
    modelStage: "approved",
    animationStage: "pending",
    runtimeEligible: false,
    reviewer: review.reviewer,
    reviewedAt: review.reviewedAt,
    reviewHash: review.reviewHash,
    artifacts: frozenArtifacts,
  };
  writeJsonAtomic(path.join(staging, "model-stage-approved.json"), approved);
  let backup = null;
  if (existsSync(canonical)) {
    const oldManifestPath = path.join(canonical, "model-stage-approved.json");
    if (existsSync(oldManifestPath)) {
      const old = readJson(oldManifestPath);
      appendAudit(authoringRoot, manifest.kind, manifest.key, {
        replacedAt: review.reviewedAt,
        sourceRunId: old.sourceRunId,
        sourceRevision: old.sourceRevision,
        sourceManifestSha256: old.sourceManifestSha256,
        reviewHash: old.reviewHash,
      });
    }
    backup = assertPathWithin(
      authoringRoot,
      path.join(authoringRoot, ".staging", `${manifest.kind}_${manifest.key}_replaced_${Date.now()}`),
      "replaced authoring bundle",
    );
    renameSync(canonical, backup);
  }
  mkdirSync(path.dirname(canonical), { recursive: true });
  try {
    renameSync(staging, canonical);
    if (backup) rmSync(backup, { recursive: true, force: true });
  } catch (error) {
    if (backup && existsSync(backup) && !existsSync(canonical)) renameSync(backup, canonical);
    throw error;
  }
  return approved;
}

function cleanupUnselectedRevisions(manifest, root) {
  const groupDir = rosterGroupDir(manifest.runId, manifest.kind, manifest.key, root);
  for (const revision of listRevisions(manifest.runId, manifest.kind, manifest.key, root)) {
    if (revision === manifest.revision) continue;
    const target = revisionDir(manifest.runId, manifest.kind, manifest.key, revision, root);
    assertPathWithin(groupDir, target, "unselected revision cleanup");
    rmSync(target, { recursive: true, force: true });
  }
}

export function recordRosterReview(input, options = {}) {
  const root = options.root ?? ROSTER_RUN_ROOT;
  const authoringRoot = options.authoringRoot ?? MODEL_STAGE_ROOT;
  const manifestPath = revisionManifestPath(input.runId, input.kind, input.key, Number(input.revision), root);
  if (!existsSync(manifestPath)) throw workflowError("ROSTER_REVISION_NOT_FOUND", "The selected roster revision does not exist.");
  const manifest = readJson(manifestPath);
  if (!["approved", "rejected"].includes(input.decision)) throw workflowError("INVALID_REVIEW_DECISION", "decision must be approved or rejected.");
  if (typeof input.reviewer !== "string" || input.reviewer.trim().length === 0) throw workflowError("REVIEWER_REQUIRED", "reviewer is required.");
  if (input.decision === "rejected" && (typeof input.notes !== "string" || input.notes.trim().length === 0)) {
    throw workflowError("REJECTION_NOTES_REQUIRED", "Disapproval requires notes.");
  }
  if (manifest.status !== "ready_for_review") {
    throw workflowError("MODEL_STAGE_REVIEW_STATE_INVALID", "Only a ready_for_review revision can receive a decision.");
  }
  const policy = compileRosterSpec().review;
  if (input.decision === "approved") {
    if (manifest.qc?.passed !== true) {
      throw workflowError("MODEL_STAGE_QC_REQUIRED", "Approval requires a ready revision with passing QC.");
    }
    for (const check of requiredChecks(manifest, policy)) {
      if (input.checks?.[check] !== true) throw workflowError("REVIEW_CHECK_INCOMPLETE", `Approval requires checks.${check}: true.`);
    }
    if (manifest.kind === "playable") {
      for (const variant of ["m", "f"]) {
        if (!input.visitedVariants?.includes(variant)) throw workflowError("VARIANT_REVIEW_INCOMPLETE", `Playable approval requires reviewing ${variant}.`);
      }
    }
    if (manifest.kind !== "creature") {
      for (const mode of ["one_handed", "two_handed", "dual_wield"]) {
        if (!input.visitedWeaponModes?.includes(mode)) throw workflowError("WEAPON_REVIEW_INCOMPLETE", `Humanoid approval requires ${mode}.`);
      }
    }
    if (manifest.kind === "npc") {
      for (const profileKey of manifest.qc?.secondaryReviewProfileKeys ?? []) {
        if (!input.reviewedNpcProfiles?.includes(profileKey)) {
          throw workflowError("NPC_SECONDARY_REVIEW_INCOMPLETE", `NPC approval requires secondary review of ${profileKey}.`);
        }
      }
    }
  }
  const reviewedAt = new Date().toISOString();
  const unsigned = {
    schemaVersion: 1,
    runId: manifest.runId,
    kind: manifest.kind,
    key: manifest.key,
    revision: manifest.revision,
    manifestSha256: sha256Json(manifest),
    decision: input.decision,
    reviewer: input.reviewer.trim(),
    reviewedAt,
    notes: input.notes?.trim() ?? "",
    checks: input.checks ?? {},
    visitedVariants: input.visitedVariants ?? [],
    visitedWeaponModes: input.visitedWeaponModes ?? [],
    reviewedNpcProfiles: input.reviewedNpcProfiles ?? [],
  };
  const review = { ...unsigned, reviewHash: sha256Json(unsigned) };
  writeJsonAtomic(path.join(path.dirname(manifestPath), "review.json"), review);
  let approved = null;
  if (input.decision === "approved") {
    approved = freezeAuthoring(manifest, review, authoringRoot);
    appendAudit(authoringRoot, manifest.kind, manifest.key, {
      decision: "approved",
      approvedAt: reviewedAt,
      reviewer: review.reviewer,
      sourceRunId: manifest.runId,
      sourceRevision: manifest.revision,
      sourceManifestSha256: approved.sourceManifestSha256,
      reviewHash: review.reviewHash,
    });
    cleanupUnselectedRevisions(manifest, root);
  }
  updateRevision(manifestPath, {
    modelStage: input.decision,
    status: input.decision === "approved" ? "model_approved" : "rejected",
    runtimeEligible: false,
    review: { decision: input.decision, reviewer: review.reviewer, reviewedAt, reviewHash: review.reviewHash },
  });
  return { review, approved, reviewPath: repoRelative(path.join(path.dirname(manifestPath), "review.json")) };
}
