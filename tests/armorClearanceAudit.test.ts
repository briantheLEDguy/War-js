import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  POLICY_PATH,
  allowedSevereVertices,
  buildBlenderArgs,
  evaluateArmorPairMetric,
  evaluateBodyMetric,
} from "../scripts/blender-character-pipeline/tools/audit-equipped-clearance.mjs";

const policy = JSON.parse(readFileSync(POLICY_PATH, "utf8"));

describe("equipped armor clearance policy", () => {
  it("documents millimeter-scale body thresholds and density-aware tolerance", () => {
    expect(policy.units).toBe("meters");
    expect(policy.bodyPenetration.severeDepthMeters).toBe(0.008);
    expect(policy.bodyPenetration.hardMaxDepthMeters).toBe(0.03);
    expect(allowedSevereVertices(1_000, policy.bodyPenetration)).toBe(24);
    expect(allowedSevereVertices(10_000, policy.bodyPenetration)).toBe(50);
  });

  it("tolerates sparse signed-distance noise but rejects deep or widespread penetration", () => {
    const base = { vertexCount: 2_000, severeVertexCount: 24, maxPenetrationMeters: 0.02 };
    expect(evaluateBodyMetric(base, policy.bodyPenetration)).toBe(true);
    expect(evaluateBodyMetric({ ...base, severeVertexCount: 25 }, policy.bodyPenetration)).toBe(false);
    expect(evaluateBodyMetric({ ...base, maxPenetrationMeters: 0.031 }, policy.bodyPenetration)).toBe(false);
  });

  it("gives named adjacent layers more seam tolerance without exempting them", () => {
    const modestSeam = {
      classification: "intentionalLayer",
      overlapPairCount: 80,
      maxUniqueTriangleRatio: 0.05,
    };
    expect(evaluateArmorPairMetric(modestSeam, policy.armorIntersection)).toBe(true);
    expect(evaluateArmorPairMetric(
      { ...modestSeam, classification: "default" },
      policy.armorIntersection,
    )).toBe(false);
    expect(evaluateArmorPairMetric(
      { ...modestSeam, overlapPairCount: 400 },
      policy.armorIntersection,
    )).toBe(true);
    expect(evaluateArmorPairMetric(
      { ...modestSeam, overlapPairCount: 1_025 },
      policy.armorIntersection,
    )).toBe(false);
    expect(evaluateArmorPairMetric(
      {
        ...modestSeam,
        overlapPairCount: 1_000,
        maxUniqueTriangleRatio: 0.07,
        thresholds: policy.armorIntersection.pairOverrides["back+chest"],
      },
      policy.armorIntersection,
    )).toBe(true);
    expect(evaluateArmorPairMetric(
      {
        ...modestSeam,
        overlapPairCount:
          policy.armorIntersection.pairOverrides["back+chest"].hardMaxOverlapPairs + 1,
        maxUniqueTriangleRatio: 0.01,
        thresholds: policy.armorIntersection.pairOverrides["back+chest"],
      },
      policy.armorIntersection,
    )).toBe(false);
  });

  it("builds a background Blender invocation with explicit model, report, policy, and poses", () => {
    const options = {
      modelPath: "C:/job/model.glb",
      reportPath: "C:/job/model.clearance.json",
      poses: "bind,idle,attack_melee",
    };
    const args = buildBlenderArgs(options);
    expect(args.slice(0, 2)).toEqual(["--background", "--python"]);
    expect(args).toContain(options.modelPath);
    expect(args).toContain(options.reportPath);
    expect(args).toContain(POLICY_PATH);
    expect(args).toContain(options.poses);
  });
});
