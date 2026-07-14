import { createHash, randomUUID } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  JOB_ROOT,
  REPO_ROOT,
  assertPathWithin,
} from "../scripts/blender-character-pipeline/tools/workspace-paths.mjs";
import {
  atomicPublishSet,
  validateBlueprintRecord,
  validateQcForBlueprint,
} from "../scripts/blender-character-pipeline/tools/pipeline-lib.mjs";
import { ModelJobStore } from "../scripts/blender-character-pipeline/tools/model-jobs.mjs";
import {
  ANIMATION_EVIDENCE_PROFILES,
  BODY_ANIMATION_PROFILES,
  evidenceFiles,
  startWorkflowJob,
} from "../scripts/blender-character-pipeline/tools/model-workflow.mjs";
import { compileRuntimeRegistry } from "../scripts/blender-character-pipeline/tools/runtime-registry.mjs";

const testRoots = [];
const reviewRendererSource = readFileSync(
  path.resolve("scripts/blender-character-pipeline/blender/render_model_review.py"),
  "utf8",
);
const modelWorkflowSource = readFileSync(
  path.resolve("scripts/blender-character-pipeline/tools/model-workflow.mjs"),
  "utf8",
);
const mcpServerSource = readFileSync(
  path.resolve("scripts/blender-character-pipeline/mcp-server/server.mjs"),
  "utf8",
);

function testRoot(label) {
  const root = path.join(JOB_ROOT, "tests", `${label}_${randomUUID()}`);
  mkdirSync(root, { recursive: true });
  testRoots.push(root);
  return root;
}

afterEach(() => {
  for (const root of testRoots.splice(0)) {
    assertPathWithin(JOB_ROOT, root, "test cleanup");
    if (existsSync(root)) rmSync(root, { recursive: true, force: true });
  }
});

describe("workspace path safety", () => {
  it("rejects traversal outside the repository", () => {
    expect(() => assertPathWithin(REPO_ROOT, path.resolve(REPO_ROOT, "..", "escape.glb"))).toThrow(/inside/);
  });
});

describe("model review framing", () => {
  it("excludes hidden rig-helper meshes from camera bounds", () => {
    expect(reviewRendererSource).toContain("def visible_review_meshes(");
    expect(reviewRendererSource).toContain("obj.hide_render or obj.hide_get()");
    expect(reviewRendererSource).toContain('"excludedHiddenMeshes": excluded_bounds_meshes');
  });

  it("defines an opt-in deterministic locomotion and melee key-phase profile", () => {
    expect(ANIMATION_EVIDENCE_PROFILES).toContain("locomotion_melee_key_phases");
    expect(reviewRendererSource).toContain('("left_contact", 0.0)');
    expect(reviewRendererSource).toContain('("right_contact", 0.5)');
    expect(reviewRendererSource).toContain('("impact", 14 / 30)');
    expect(reviewRendererSource).toContain('("recovery", 1.0)');
    expect(reviewRendererSource).toContain('for view in ("side", "back")');
    expect(reviewRendererSource).toContain('for view in ("front", "side")');
  });

  it("keeps the primary promotion key and preserves every focused frame", () => {
    const frames = [
      { clip: "walk", view: "side", sampleId: "left_contact", primary: false, frame: 1, path: "walk-left.png", sha256: "1" },
      { clip: "walk", view: "side", sampleId: "right_contact", primary: true, frame: 13, path: "walk-right.png", sha256: "2" },
      { clip: "walk", view: "back", sampleId: "right_contact", primary: false, frame: 13, path: "walk-back.png", sha256: "3" },
      { clip: "attack_melee", view: "front", sampleId: "impact", primary: true, frame: 11, path: "impact.png", sha256: "4" },
      { clip: "attack_melee", view: "side", sampleId: "recovery", primary: false, frame: 21, path: "recovery.png", sha256: "5" },
    ];
    const evidence = evidenceFiles({ animationFrames: frames }, "equipped");
    const keys = evidence.map((entry) => entry.key);

    expect(keys).toContain("animation_walk");
    expect(keys).toContain("animation_attack_melee");
    expect(keys).toContain("animation_walk_side_left_contact");
    expect(keys).toContain("animation_walk_back_right_contact");
    expect(keys).toContain("animation_attack_melee_side_recovery");
    expect(new Set(keys).size).toBe(frames.length);
  });

  it("retains the legacy animation key when a manifest has one unlabelled frame", () => {
    const evidence = evidenceFiles({
      animationFrames: [{ clip: "idle", frame: 12, path: "idle.png", sha256: "a" }],
    }, "equipped");
    expect(evidence).toEqual([{ key: "animation_idle", path: "idle.png", sha256: "a" }]);
  });
});

describe("MPFB animation profile workflow", () => {
  it("publishes the supported profiles through the MCP create-body schema", () => {
    expect(BODY_ANIMATION_PROFILES).toEqual(["unarmed", "battle_prelate_hammer"]);
    expect(mcpServerSource).toContain('enum: ["unarmed", "battle_prelate_hammer"]');
    expect(mcpServerSource).toContain('default: "unarmed"');
  });

  it("rejects unknown profiles before starting a body-generation job", () => {
    expect(() => startWorkflowJob("create_body_family", {
      bodyFamily: "civic_humanoid_v2",
      bodyVariant: "m",
      animationProfile: "impossible_weapon_pose",
    })).toThrow(/animationProfile must be one of/);
  });

  it("passes the validated profile to Blender and records it in the request", () => {
    expect(modelWorkflowSource).toContain('"--animation-profile", animationProfile');
    expect(modelWorkflowSource).toMatch(/bindPoseId:[\s\S]*animationProfile,[\s\S]*recipeSource:/);
  });
});

describe("strict blueprint validation", () => {
  it("rejects retired generators, incomplete PBR, excess weights, and unlicensed imports", () => {
    const blueprint = {
      assetId: "chr.test.pilot",
      displayName: "Pilot",
      category: "character",
      version: "1.0.0",
      output: { model: "chr_test_pilot.glb" },
      generator: { kind: "externalImport", source: "artifacts/input.glb", sourceType: "glb" },
      geometry: { originRule: "root", upAxis: "+Y", forwardAxis: "+Z", lods: [{ name: "LOD0", triTarget: 10 }] },
      materials: { master: "pbr", channels: ["baseColor"] },
      rigging: { skinned: true, maxInfluences: 8, requiredClips: [] },
      provenance: {
        createdBy: "test",
        aiAssisted: false,
        aiStages: [],
        referencePackId: "test",
        similarityReview: "not_required",
      },
      qc: { allowNonManifold: false, allowUvOverlap: false, maxDrawCalls: 1, maxFileSizeMb: 1 },
    };
    const result = validateBlueprintRecord("fixture.asset.json", blueprint, { strict: true });
    expect(result.ok).toBe(false);
    expect(result.errors.join("\n")).toMatch(/roughness/);
    expect(result.errors.join("\n")).toMatch(/maxInfluences/);
    expect(result.errors.join("\n")).toMatch(/sourceSha256/);
    expect(result.errors.join("\n")).toMatch(/license\.name/);

    blueprint.geometry.skeletonId = "legacy_skeleton";
    const invalidSkeleton = validateBlueprintRecord("fixture.asset.json", blueprint, { strict: true });
    expect(invalidSkeleton.errors.join("\n")).toMatch(/humanoid_game_v2/);

    blueprint.generator.kind = "characterPreset";
    const retired = validateBlueprintRecord("fixture.asset.json", blueprint, { strict: true });
    expect(retired.errors.join("\n")).toMatch(/retired primitive generator/);
  });

  it("detects stale hashes, missing evidence, topology, weights, budgets, and clips", () => {
    const root = testRoot("strict-qc");
    const modelPath = path.join(root, "pilot.glb");
    const qcPath = path.join(root, "pilot.qc.json");
    writeFileSync(modelPath, "synthetic-glb-fixture");
    writeFileSync(qcPath, JSON.stringify({
      assetId: "body.test.m",
      model: "pilot.glb",
      qcPassed: true,
      modelSha256: "0".repeat(64),
      totalTris: 200,
      meshCount: 4,
      missingRequiredClips: ["walk"],
      skeletonId: "wrong_skeleton",
      maxInfluencesObserved: 6,
      pbrChannels: ["baseColor"],
      nonManifoldEdges: 2,
      previewImages: [],
    }));
    const blueprint = {
      assetId: "body.test.m",
      category: "body",
      output: { model: "pilot.glb" },
      geometry: { skeletonId: "humanoid_game_v2", lods: [{ name: "LOD0" }] },
      materials: { channels: ["baseColor", "roughness", "metallic", "normal"] },
      rigging: { requiredClips: ["idle", "walk"] },
      qc: { maxTris: 100, maxDrawCalls: 2, allowNonManifold: false, requiresPreview: true },
    };
    const errors = validateQcForBlueprint(blueprint, modelPath, qcPath, true).join("\n");
    expect(errors).toMatch(/triangle count/);
    expect(errors).toMatch(/draw-call/);
    expect(errors).toMatch(/missing required clips/);
    expect(errors).toMatch(/humanoid_game_v2/);
    expect(errors).toMatch(/bone influences/);
    expect(errors).toMatch(/PBR channel roughness/);
    expect(errors).toMatch(/non-manifold/);
    expect(errors).toMatch(/stale/);
    expect(errors).toMatch(/no preview images/);
  });
});

describe("atomic publication", () => {
  it("restores the last good file if a later rename fails", () => {
    const root = testRoot("rollback");
    const oldDestination = path.join(root, "published.glb");
    const first = path.join(root, "first.glb");
    const second = path.join(root, "second.glb");
    writeFileSync(oldDestination, "last-good");
    writeFileSync(first, "first-new");
    writeFileSync(second, "second-new");

    expect(() => atomicPublishSet([
      { source: first, destination: oldDestination },
      { source: second, destination: oldDestination },
    ], { transactionDir: path.join(root, "transaction") })).toThrow(/rolled back/);
    expect(readFileSync(oldDestination, "utf8")).toBe("last-good");
  });
});

describe("model jobs", () => {
  it("locks concurrent writes to the same asset", async () => {
    const root = testRoot("locks");
    const store = new ModelJobStore(root);
    let releaseFirst;
    const gate = new Promise((resolve) => { releaseFirst = resolve; });
    const first = store.start("test", {}, async () => {
      await gate;
      return { ok: true };
    }, { assetKeys: ["body.test.m"] });
    await new Promise((resolve) => setTimeout(resolve, 20));
    const second = store.start("test", {}, async () => ({ ok: true }), { assetKeys: ["body.test.m"] });
    const secondResult = await store.wait(second.jobId);
    expect(secondResult.status).toBe("failed");
    expect(secondResult.error.code).toBe("ASSET_LOCKED");
    releaseFirst();
    expect((await store.wait(first.jobId)).status).toBe("completed");
  });

  it("persists cancellation as a structured terminal state", async () => {
    const root = testRoot("cancel");
    const store = new ModelJobStore(root);
    const job = store.start("test", {}, ({ signal }) => new Promise((resolve, reject) => {
      signal.addEventListener("abort", () => {
        const error = new Error("aborted");
        error.name = "AbortError";
        reject(error);
      }, { once: true });
    }), { assetKeys: ["body.cancel.m"] });
    await new Promise((resolve) => setTimeout(resolve, 20));
    store.cancel(job.jobId);
    const result = await store.wait(job.jobId);
    expect(result.status).toBe("cancelled");
    expect(result.error.code).toBe("JOB_CANCELLED");
  });

  it("recovers an owned lock immediately when its process is gone", async () => {
    const root = testRoot("dead-owner-lock");
    const assetKey = "body.interrupted.m";
    const readable = assetKey.toLowerCase().replace(/[^a-z0-9_.-]+/g, "_").slice(0, 64);
    const suffix = createHash("sha256").update(assetKey).digest("hex").slice(0, 12);
    const lockRoot = path.join(root, ".locks");
    mkdirSync(lockRoot, { recursive: true });
    writeFileSync(path.join(lockRoot, `${readable}.${suffix}.lock`), JSON.stringify({
      jobId: "job_20000101t000000z_deadbeef0000",
      assetKey,
      pid: 2_147_483_647,
      createdAt: new Date().toISOString(),
    }));
    const store = new ModelJobStore(root);
    const job = store.start("test", {}, async () => ({ ok: true }), { assetKeys: [assetKey] });
    expect((await store.wait(job.jobId)).status).toBe("completed");
  });
});

describe("runtime registry compiler", () => {
  it("is deterministic and groups equipment by body variant", () => {
    const base = {
      schemaVersion: 1,
      category: "armor",
      displayName: "Pilot chest",
      model: "arm_pilot_chest_m.glb",
      qc: "arm_pilot_chest_m.qc.json",
      runtime: { itemKey: "pilot_chest", bodyVariant: "m" },
      compatibility: { bodyFamily: "civic_humanoid_v2", bodyVariant: "m", skeletonId: "humanoid_game_v2", bindPoseId: "a_pose_v2" },
      hashes: { modelSha256: "a".repeat(64), qcSha256: "b".repeat(64), previews: { front: "c".repeat(64) } },
      previews: { front: "reviews/test/front.png" },
      review: { reviewedBy: "tester", reviewedAt: "2026-01-01T00:00:00.000Z", reviewHash: "d".repeat(64) },
      approvalState: "approved",
    };
    const male = { ...base, assetId: "arm.test.chest.m" };
    const female = {
      ...base,
      assetId: "arm.test.chest.f",
      model: "arm_pilot_chest_f.glb",
      qc: "arm_pilot_chest_f.qc.json",
      runtime: { ...base.runtime, bodyVariant: "f" },
      compatibility: { ...base.compatibility, bodyVariant: "f" },
    };
    const first = compileRuntimeRegistry({ additionalManifests: [male, female] });
    const second = compileRuntimeRegistry({ additionalManifests: [female, male] });
    expect(first).toEqual(second);
    expect(first.equipment.pilot_chest.variants.m.assetId).toBe(male.assetId);
    expect(first.equipment.pilot_chest.variants.f.assetId).toBe(female.assetId);
    expect(first.staticProps.dummy.model).toBe("prop_training_dummy_t1.glb");
    expect(first.equipment.weapon_hammer_reliquary_2h.runtimeReady).toBe(false);
    expect(first.equipment.weapon_hammer_reliquary_2h.reviewStatus).toBe("blocked_socket_attachment_pending");
  });
});
