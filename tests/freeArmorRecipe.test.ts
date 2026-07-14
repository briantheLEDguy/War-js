import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const recipePath = path.resolve(
  "scripts/blender-character-pipeline/data/body-families/armor-sets/free-pilot-armor-sets.json",
);
const recipe = JSON.parse(readFileSync(recipePath, "utf8"));
const generatorSource = readFileSync(
  path.resolve("scripts/blender-character-pipeline/blender/generate_mpfb_modular_armor.py"),
  "utf8",
);
const slots = ["head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard"];

describe("free pilot armor recipes", () => {
  it("defines a review-gated nine-slot set for both pilot families and variants", () => {
    expect(recipe.promotionEligible).toBe(false);
    expect(recipe.license).toBe("CC0-1.0");
    expect(Object.keys(recipe.sets)).toEqual(["civic_humanoid_v2", "mire_brutish_v1"]);

    for (const set of Object.values(recipe.sets) as any[]) {
      expect(set.bodyVariants).toEqual(["m", "f"]);
      expect(Object.keys(set.modules)).toEqual(slots);
      expect(Object.values(set.modules).filter((module: any) => module.kind === "mpfbAsset")).toHaveLength(5);
      expect(Object.values(set.modules).filter((module: any) => module.kind !== "mpfbAsset")).toHaveLength(4);
    }
  });

  it("pins every referenced CC0 source pack by a SHA-256 digest", () => {
    const referencedPacks = new Set<string>();
    for (const set of Object.values(recipe.sets) as any[]) {
      for (const module of Object.values(set.modules) as any[]) {
        if (module.pack) referencedPacks.add(module.pack);
      }
    }

    expect([...referencedPacks].sort()).toEqual(["gloves01", "hats02", "suits02"]);
    for (const packId of referencedPacks) {
      expect(recipe.sourcePacks[packId].sha256).toMatch(/^[a-f0-9]{64}$/u);
      expect(recipe.sourcePacks[packId].sourceUrl).toMatch(/^https:\/\/static\.makehumancommunity\.org\//u);
    }
  });

  it("writes Blender 5 generated-image pixels only after setting color space", () => {
    const createImage = generatorSource.match(
      /def create_image[\s\S]*?\r?\n\r?\ndef gltf_occlusion_group/u,
    )?.[0];
    expect(createImage).toBeDefined();
    expect(createImage!.indexOf("image.colorspace_settings.name = colorspace")).toBeLessThan(
      createImage!.indexOf("image.pixels[:] = pixels"),
    );
    expect(createImage).not.toContain("image.update()");
    expect(createImage).toContain("image.pack()");
    expect(createImage).toContain("lost pixel data");
  });

  it("constructs layered, contoured garments instead of rectangular panels", () => {
    expect(generatorSource).toContain("def create_curved_belt(");
    expect(generatorSource).toContain("def trim_distal_underlap(");
    expect(generatorSource).toContain('trim_distal_underlap(obj, rig, "forearm", "hand", 0.245)');
    expect(generatorSource).toContain('trim_distal_underlap(obj, rig, "shin", "foot", 0.380)');
    expect(generatorSource).toContain("def panel_half_width(");
    expect(generatorSource).toContain("def body_surface_y(");
    expect(generatorSource).toContain("def refine_shoulder_shell(");
    expect(generatorSource).toContain("MINIMUM_BODY_CLEARANCE_M = 0.004");
    expect(generatorSource).toContain('"back": 0.010');
    expect(generatorSource).toContain("center_z = anchor.z + extent.z * 0.010");
    expect(generatorSource).toContain("edge_flutter");
    expect(generatorSource).toContain("collar_profile");
    expect(generatorSource).toContain("belt_window");
    expect(generatorSource).toContain('solidify.offset = 1.0 if panel == "back" else -1.0');
    expect(generatorSource).toContain("SLOT_LAYER_ORDER");
    expect(recipe.sets.civic_humanoid_v2.modules.shoulders.thicknessM).toBe(0.006);
  });
});
