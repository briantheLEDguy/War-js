import { describe, expect, it } from "vitest";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { assertDraftReceipt, classCharacterSpecs, digest, RACE_ANATOMY } from "../scripts/unreal/class-character-spec.mjs";

describe("class-character foundations", () => {
  it("keeps anatomical-region tuning tied to real character identities", () => {
    const recipes = JSON.parse(readFileSync(new URL("../scripts/unreal/class-character-skin-recipes.json", import.meta.url), "utf8"));
    const identities = new Set(classCharacterSpecs().map((request) => `${request.classKey}_${request.bodyVariant}`));
    expect(recipes.schemaVersion).toBe(1);
    for (const identity of Object.keys(recipes.characters)) expect(identities.has(identity)).toBe(true);
    for (const recipe of [recipes.defaults, ...Object.values(recipes.characters)] as Array<{ hipIterations: number; shoulderIterations: number }>) {
      for (const count of [recipe.hipIterations, recipe.shoulderIterations]) {
        expect(Number.isInteger(count)).toBe(true);
        expect(count).toBeGreaterThan(0);
        expect(count).toBeLessThanOrEqual(256);
      }
    }
    for (const override of Object.values(recipes.characters)) {
      const width = { ...recipes.defaults, ...override as object }.trunkAnchorWidth;
      expect(Number.isFinite(width)).toBe(true);
      expect(width).toBeGreaterThanOrEqual(.2);
      expect(width).toBeLessThanOrEqual(.8);
    }
    for (const [identity, recipe] of Object.entries(recipes.characters) as Array<[string, { correction?: string }]>) {
      if (!recipe.correction) continue;
      expect(recipe.correction).toBe(`${identity}.json`);
      const correction = JSON.parse(readFileSync(new URL(`../scripts/unreal/class-character-skin-corrections/${recipe.correction}`, import.meta.url), "utf8"));
      expect(correction.identity).toBe(identity);
      expect(correction.solver.maxExtensionScore).toBeLessThanOrEqual(1);
      expect(correction.solver.baselineLbsErrorM).toBeLessThan(1e-5);
      expect(correction.solver.poseCount).toBe(107);
      expect(correction.solver.toolSha256).toBe(digest(readFileSync(new URL("../scripts/unreal/fit-class-character-skin.py", import.meta.url))));
    }
  });
  it("covers all 24 classes and both variants without extreme macro saturation", () => {
    const requests = classCharacterSpecs();
    expect(requests).toHaveLength(48);
    expect(new Set(requests.map((request) => request.classKey)).size).toBe(24);
    expect(new Set(requests.map((request) => request.race)).size).toBe(6);
    expect(new Set(requests.map((request) => `${request.classKey}:${request.bodyVariant}`)).size).toBe(48);
    for (const request of requests) {
      const limits = RACE_ANATOMY[request.race];
      expect(request.propertyValues.muscle).toBeGreaterThanOrEqual(limits.muscle[0]);
      expect(request.propertyValues.muscle).toBeLessThanOrEqual(limits.muscle[1]);
      expect(request.propertyValues.weight).toBeGreaterThanOrEqual(limits.weight[0]);
      expect(request.propertyValues.weight).toBeLessThanOrEqual(limits.weight[1]);
      expect(request.foundation.armorClearanceM.joint).toBeGreaterThan(request.foundation.armorClearanceM.plate);
      expect(request.foundation.nativeAccepted).toBe(false);
      if (request.race === "chaos") expect(request.skin.assetPack).toBe("makehuman_system_assets");
    }
  });

  it("rejects changed anatomy requests, model bytes, evidence paths and false acceptance", () => {
    const request = classCharacterSpecs()[0];
    const bytes = Buffer.from("bound-model-fixture");
    const receipt = { requestSha256: digest(JSON.stringify(request)), classKey: request.classKey,
      variant: request.bodyVariant, technicalPassed: true, nativeAccepted: false, runtimeEligible: false,
      files: [{ path: "body.glb", sha256: digest(bytes) }] };
    expect(assertDraftReceipt(receipt, request, "/draft", () => bytes)).toBe(receipt);
    expect(() => assertDraftReceipt(receipt, { ...request, expectedHeightM: 9 }, "/draft", () => bytes)).toThrow(/request changed/);
    expect(() => assertDraftReceipt(receipt, request, "/draft", () => Buffer.from("changed"))).toThrow(/evidence changed/);
    for (const path of ["../body.glb", "/body.glb", "C:/body.glb", "..\\body.glb"]) {
      expect(() => assertDraftReceipt({ ...receipt, files: [{ path, sha256: digest(bytes) }] }, request, "/draft", () => bytes)).toThrow(/Unsafe/);
    }
    expect(() => assertDraftReceipt({ ...receipt, nativeAccepted: true }, request, "/draft", () => bytes)).toThrow(/acceptance state/);
    expect(() => assertDraftReceipt({ ...receipt, classKey: "another_class" }, request, "/draft", () => bytes)).toThrow(/identity/);
    expect(() => assertDraftReceipt({ ...receipt, files: [] }, request, "/draft", () => bytes)).toThrow(/no evidence/);
  });

  it("checks measured symmetry, skin weights and density-independent deformation limits", () => {
    const run = spawnSync("python", ["-B", "tests/unrealClassCharacters.test.py"], { encoding: "utf8", windowsHide: true });
    expect(run.error, String(run.error)).toBeUndefined();
    expect(run.status, run.stdout + run.stderr).toBe(0);
  });
});
