import { createHash, randomUUID } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  DEFAULTS,
  buildBlenderArgs,
  validateInputs,
  validateOutputs,
} from "../scripts/blender-character-pipeline/tools/assemble-runtime-equipped-review.mjs";
import {
  JOB_ROOT,
  assertPathWithin,
} from "../scripts/blender-character-pipeline/tools/workspace-paths.mjs";

const roots: string[] = [];
const clips = ["idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump"];
const slots = ["head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard"];

function fixtureRoot(): string {
  const root = path.join(JOB_ROOT, "tests", `runtime-assembly_${randomUUID()}`);
  mkdirSync(root, { recursive: true });
  roots.push(root);
  return root;
}

function writeMinimalGlb(filePath: string): void {
  const document = Buffer.from(JSON.stringify({
    asset: { version: "2.0" },
    scenes: [{ nodes: [] }],
    scene: 0,
    nodes: [],
    skins: [{}],
    animations: clips.map((name) => ({ name, samplers: [], channels: [] })),
  }), "utf8");
  const padding = (4 - (document.length % 4)) % 4;
  const json = Buffer.concat([document, Buffer.alloc(padding, 0x20)]);
  const header = Buffer.alloc(20);
  header.write("glTF", 0, "ascii");
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(20 + json.length, 8);
  header.writeUInt32LE(json.length, 12);
  header.write("JSON", 16, "ascii");
  writeFileSync(filePath, Buffer.concat([header, json]));
}

function sha256(filePath: string): string {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

function options(root: string) {
  const modulesDir = path.join(root, "modules");
  mkdirSync(modulesDir, { recursive: true });
  const bodyPath = path.join(root, "body.glb");
  const hammerPath = path.join(root, "hammer.glb");
  writeFileSync(bodyPath, "body");
  writeFileSync(hammerPath, "hammer");
  for (const slot of slots) {
    writeFileSync(path.join(modulesDir, `arm_civic_humanoid_v2_battle_prelate_v1_${slot}_m.glb`), slot);
  }
  return {
    blenderPath: "blender",
    bodyPath,
    modulesDir,
    hammerPath,
    outputPath: path.join(root, "assembled.glb"),
    reviewDir: path.join(root, "reviews"),
    reportPath: path.join(root, "assembled.qc.json"),
    timeoutMs: 900_000,
    dryRun: true,
    json: false,
  };
}

afterEach(() => {
  for (const root of roots.splice(0)) {
    assertPathWithin(JOB_ROOT, root, "runtime assembly test cleanup");
    if (existsSync(root)) rmSync(root, { recursive: true, force: true });
  }
});

describe("runtime-equipped assembly wrapper", () => {
  it("defaults to the seam-trimmed v18 armor pilot without deleting review history", () => {
    expect(DEFAULTS.modules).toContain("local-armor-pilot-v18");
    expect(DEFAULTS.output).toContain("local-armor-pilot-v18");
    expect(DEFAULTS.reviewDir).toContain("local-armor-pilot-v18");
    expect(DEFAULTS.report).toContain("local-armor-pilot-v18");
  });

  it("requires exactly the canonical nine module inputs and builds the Blender invocation", () => {
    const resolved = options(fixtureRoot());
    expect(validateInputs(resolved).moduleFiles).toHaveLength(9);
    const args = buildBlenderArgs(resolved);
    expect(args).toContain("--body-glb");
    expect(args).toContain(resolved.bodyPath);
    expect(args).toContain("--modules-dir");
    expect(args).toContain(resolved.modulesDir);
    expect(args).toContain("--hammer-glb");
    expect(args).toContain(resolved.hammerPath);

    rmSync(path.join(resolved.modulesDir, "arm_civic_humanoid_v2_battle_prelate_v1_head_m.glb"));
    expect(() => validateInputs(resolved)).toThrow(/expected nine Battle Prelate module GLBs/u);
  });

  it("accepts only hash-bound, draft, single-skin, nine-clip round-trip output", () => {
    const resolved = options(fixtureRoot());
    writeMinimalGlb(resolved.outputPath);
    const previews: Record<string, Array<{ view: string; path: string; sha256: string }>> = {};
    for (const pose of ["bindPose", "idlePose"]) {
      const poseDir = path.join(resolved.reviewDir, pose);
      mkdirSync(poseDir, { recursive: true });
      previews[pose] = slots.slice(0, 4).map((_, index) => {
        const view = ["front", "side", "back", "isometric"][index];
        const filePath = path.join(poseDir, `${view}.png`);
        writeFileSync(filePath, `${pose}:${view}`);
        return { view, path: filePath, sha256: sha256(filePath) };
      });
    }
    const report = {
      lifecycleStatus: "draft",
      promotionEligible: false,
      modelSha256: sha256(resolved.outputPath),
      technicalRoundTripPassed: true,
      preExportChecks: { singleArmature: true, nineModuleMeshes: true },
      roundTrip: {
        passed: true,
        bodyMeshCount: 4,
        moduleMeshCount: 9,
        weaponMeshCount: 1,
        boneCount: 56,
        animationClips: clips,
        checks: { singleArmature: true, allModulesBoundToBodyRig: true },
        glbJsonChecks: { singleSkin: true, nineAnimations: true },
        idleDeltaAudit: { passed: true },
        bindPose: { previews: previews.bindPose },
        idlePose: { previews: previews.idlePose },
      },
    };
    writeFileSync(resolved.reportPath, `${JSON.stringify(report)}\n`);
    expect(validateOutputs(resolved).actualHash).toBe(report.modelSha256);

    report.roundTrip.idleDeltaAudit.passed = false;
    writeFileSync(resolved.reportPath, `${JSON.stringify(report)}\n`);
    expect(() => validateOutputs(resolved)).toThrow(/center\/extent audit failed/u);
  });
});
