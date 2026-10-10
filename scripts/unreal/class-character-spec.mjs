import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { compileRosterSpec } from "../blender-character-pipeline/tools/roster-spec.mjs";

// Class identity comes from equipment; anatomy varies within each race's range.
// These limits prevent the older archetype offsets from saturating MPFB macros.
export const RACE_ANATOMY = Object.freeze({
  empire: { muscle: [0.32, 0.78], weight: [0.38, 0.64], shoulders: [0.18, 0.33] },
  dwarf: { muscle: [0.46, 0.86], weight: [0.50, 0.74], shoulders: [0.22, 0.39] },
  high_elf: { muscle: [0.28, 0.66], weight: [0.30, 0.54], shoulders: [0.16, 0.30] },
  chaos: { muscle: [0.48, 0.88], weight: [0.44, 0.70], shoulders: [0.19, 0.35] },
  greenskin: { muscle: [0.54, 0.90], weight: [0.48, 0.74], shoulders: [0.20, 0.37] },
  dark_elf: { muscle: [0.30, 0.70], weight: [0.32, 0.58], shoulders: [0.16, 0.31] },
});

const clamp = (value, [low, high]) => Math.max(low, Math.min(high, value));
export const digest = (value) => createHash("sha256").update(value).digest("hex");

export function classCharacterSpecs() {
  return compileRosterSpec().groups.filter((group) => group.kind === "playable").flatMap((group) =>
    group.variants.map(({ variant, physique }) => {
      const limits = RACE_ANATOMY[group.race];
      const request = structuredClone(physique);
      request.propertyValues.muscle = clamp(request.propertyValues.muscle, limits.muscle);
      request.propertyValues.weight = clamp(request.propertyValues.weight, limits.weight);
      // Retain human skin detail for Chaos; alien bio-armor is not bare anatomy.
      if (group.race === "chaos") request.skin = {
        assetPack: "makehuman_system_assets", assetName: `middleage_caucasian_${variant === "m" ? "male" : "female"}`,
        tint: variant === "m" ? "#9b8276" : "#ad9084",
      };
      // Short, detachable grooming leaves the neck and shoulder armor envelope clear.
      request.grooming.hair = variant === "f" ? "short02" : "short04";
      request.foundation = {
        schemaVersion: 1, classKey: group.key, className: group.displayName,
        race: group.race, variant, shoulderHeightRatio: [limits.shoulders[0] * (variant === "f" ? .90 : 1), limits.shoulders[1]],
        armorClearanceM: { soft: 0.006, plate: 0.018, joint: 0.025 },
        hairTint: { empire: "#34231b", dwarf: "#784427", high_elf: "#b8a377", chaos: "#282222", greenskin: "#273021", dark_elf: "#24202c" }[group.race],
        motionPolicy: "separate_native_supplied_set", nativeAccepted: false,
      };
      return request;
    }));
}

export function assertDraftReceipt(receipt, request, directory, read = readFileSync) {
  if (receipt.requestSha256 !== digest(JSON.stringify(request))) throw new Error("Character request changed; create a new run.");
  if (receipt.classKey !== request.classKey || receipt.variant !== request.bodyVariant) throw new Error("Character receipt identity mismatch.");
  if (!receipt.technicalPassed || receipt.nativeAccepted !== false || receipt.runtimeEligible !== false) throw new Error("Invalid draft acceptance state.");
  if (!receipt.files?.length) throw new Error("Character receipt has no evidence.");
  for (const file of receipt.files) {
    if (!/^[a-zA-Z0-9_./-]+$/.test(file.path) || file.path.split("/").includes("..") || file.path.startsWith("/")) throw new Error("Unsafe character evidence path.");
    if (digest(read(`${directory}/${file.path}`)) !== file.sha256) throw new Error(`Character evidence changed: ${file.path}`);
  }
  return receipt;
}
