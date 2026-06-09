import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import path from "path";
import {
  ASSET_INDEX_PATH,
  BLUEPRINT_DIR,
  PIPELINE_ROOT,
  REPO_ROOT,
} from "./pipeline-lib.mjs";

const ROSTER_PATH = path.join(PIPELINE_ROOT, "data", "playable-character-roster.json");
const GENERATED_TS_PATH = path.join(REPO_ROOT, "src", "data", "playableAssets.generated.ts");
const ASSET_VERSION = "2026-06-09-playable-modular-roster";
const REQUIRED_CLIPS = [
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

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

function writeJson(filePath, value) {
  mkdirSync(path.dirname(filePath), { recursive: true });
  writeFileSync(`${filePath}`, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function titleCaseKey(key) {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function combinedScale(race, variant) {
  return [
    Number((race.scale[0] * variant.scale[0]).toFixed(3)),
    Number((race.scale[1] * variant.scale[1]).toFixed(3)),
    Number((race.scale[2] * variant.scale[2]).toFixed(3)),
  ];
}

function profileKeyFor(race, klass, variantKey) {
  return `${race.family}_${klass.key}_${variantKey}`;
}

function bodyFamilyFor(race, klass, variantKey) {
  return `${race.family}_${klass.key}_${variantKey}`;
}

function characterAssetId(race, klass, variantKey) {
  return `chr.${race.family}.${klass.key}.t1.${variantKey}`;
}

function characterModel(race, klass, variantKey) {
  return `chr_${race.family}_${klass.key}_t1_${variantKey}.glb`;
}

function armorAssetId(race, klass, slot, variantKey) {
  return `arm.${race.family}.${klass.key}.${slot}.t1.${variantKey}`;
}

function armorModel(race, klass, slot, variantKey) {
  return `arm_${race.family}_${klass.key}_${slot}_t1_${variantKey}.glb`;
}

function armorItemKey(race, klass, slot, variantKey) {
  return `starter_${race.family}_${klass.key}_${slot}_${variantKey}`;
}

function manifestArtifactDir(model) {
  return `artifacts/blender/manifest/${model.replace(/\.glb$/i, "")}`;
}

function baseSets(klass, specific) {
  return [
    specific,
    "playable_all",
    `playable_${klass.race}`,
    ...(klass.sets ?? []),
  ];
}

function characterBlueprint(roster, raceKey, race, klass, variantKey, variant) {
  const profileKey = profileKeyFor(race, klass, variantKey);
  const bodyFamily = bodyFamilyFor(race, klass, variantKey);
  const scale = combinedScale(race, variant);
  const model = characterModel(race, klass, variantKey);
  return {
    assetId: characterAssetId(race, klass, variantKey),
    displayName: `${race.display} ${titleCaseKey(klass.key)} ${variant.label}`,
    category: "character",
    version: "1.0.0",
    sets: [
      "characters",
      "playable_characters",
      ...baseSets(klass, `playable_${variantKey}`),
    ],
    runtime: { profileKey },
    output: {
      model,
      artifactDir: manifestArtifactDir(model),
    },
    generator: { kind: "characterPreset", preset: profileKey },
    geometry: {
      originRule: "armature_root_grounded",
      upAxis: "+Y",
      forwardAxis: "+Z",
      bodyFamily,
      skeletonId: "humanoid_v1",
      bindPoseId: "a_pose_v1",
      lods: [
        { name: "LOD0", triTarget: 70000, screenCoverageMin: 0.2 },
        { name: "LOD1", triTarget: 42000, screenCoverageMin: 0.1 },
        { name: "LOD2", triTarget: 18000, screenCoverageMin: 0.04 },
      ],
    },
    attachments: [
      { name: "AP_ROOT", type: "root", parent: "root", position: [0, 0, 0] },
      { name: "AP_HAND_WEAPON_R", type: "socket", parent: "hand_r", position: [0, 0, 0] },
      { name: "AP_HAND_SECONDARY_L", type: "socket", parent: "hand_l", position: [0, 0, 0] },
      { name: "AP_BACK", type: "socket", parent: "chest", position: [0, 1.28 * scale[1], -0.12 * scale[2]] },
    ],
    materials: {
      master: "MM_CharacterPbr",
      textureSet: `${profileKey}_t1`,
      channels: ["baseColor", "roughness", "metallic", "normal", "occlusion", "emissive"],
    },
    rigging: {
      skinned: true,
      maxInfluences: 4,
      requiredClips: REQUIRED_CLIPS,
    },
    collision: {
      policy: "inherits_body_capsule",
      primitives: [{ type: "capsule", tag: "character_body" }],
    },
    compatibility: { occupiesSlots: ["character"], requires: [], conflictsWith: [] },
    provenance: {
      createdBy: "procedural_blender_pipeline",
      aiAssisted: true,
      aiStages: ["class_silhouette_seed", "manifest_expansion", "procedural_generation"],
      promptIds: [`playable_roster_${raceKey}_${klass.key}_${variantKey}`],
      referencePackId: "neutral_dark_fantasy_playable_v1",
      similarityReview: "not_required",
    },
    qc: {
      allowNonManifold: false,
      allowUvOverlap: true,
      maxDrawCalls: 14,
      maxFileSizeMb: 12,
      groundToleranceM: 0.03,
      expectedHeightM: Number((1.9 * scale[1]).toFixed(3)),
      maxMeshObjects: 90,
      requiresSkinnedMeshes: true,
      requiresPreview: true,
    },
  };
}

function armorBlueprint(raceKey, race, klass, slotDef, variantKey, variant) {
  const profileKey = profileKeyFor(race, klass, variantKey);
  const bodyFamily = bodyFamilyFor(race, klass, variantKey);
  const model = armorModel(race, klass, slotDef.slot, variantKey);
  const itemKey = armorItemKey(race, klass, slotDef.slot, variantKey);
  return {
    assetId: armorAssetId(race, klass, slotDef.slot, variantKey),
    displayName: `${race.display} ${titleCaseKey(klass.key)} ${slotDef.label} ${variant.label}`,
    category: "armor",
    version: "1.0.0",
    sets: [
      "equipment",
      "playable_armor",
      `playable_armor_${slotDef.slot}`,
      ...baseSets(klass, `playable_${variantKey}`),
    ],
    runtime: { itemKey },
    output: {
      model,
      artifactDir: manifestArtifactDir(model),
    },
    generator: { kind: "armorModule", preset: profileKey },
    geometry: {
      originRule: "same_origin_skinned_overlay_root",
      upAxis: "+Y",
      forwardAxis: "+Z",
      bodyFamily,
      skeletonId: "humanoid_v1",
      bindPoseId: "a_pose_v1",
      lods: [
        { name: "LOD0", triTarget: 9000, screenCoverageMin: 0.2 },
        { name: "LOD1", triTarget: 5200, screenCoverageMin: 0.08 },
        { name: "LOD2", triTarget: 2200, screenCoverageMin: 0.03 },
      ],
    },
    attachments: [
      { name: "AP_ROOT", type: "root", parent: "root", position: [0, 0, 0] },
    ],
    materials: {
      master: "MM_ModularArmorPbr",
      textureSet: `${profileKey}_${slotDef.slot}_t1`,
      channels: ["baseColor", "roughness", "metallic", "normal", "occlusion", "emissive"],
    },
    rigging: { skinned: true, maxInfluences: 4, requiredClips: [] },
    collision: {
      policy: "inherits_body",
      primitives: [{ type: "convexHull", tag: `${slotDef.slot}_clearance` }],
    },
    compatibility: {
      occupiesSlots: [slotDef.slot],
      requires: [characterAssetId(race, klass, variantKey)],
      conflictsWith: [],
    },
    provenance: {
      createdBy: "procedural_blender_pipeline",
      aiAssisted: true,
      aiStages: ["class_silhouette_seed", "manifest_expansion", "procedural_generation"],
      promptIds: [`playable_armor_${raceKey}_${klass.key}_${slotDef.slot}_${variantKey}`],
      referencePackId: "neutral_dark_fantasy_playable_v1",
      similarityReview: "not_required",
    },
    qc: {
      allowNonManifold: false,
      allowUvOverlap: true,
      maxDrawCalls: 8,
      maxFileSizeMb: 6,
      groundToleranceM: 0.03,
      maxMeshObjects: 40,
      requiresSkinnedMeshes: true,
      requiresPreview: false,
    },
  };
}

function generatedTs(roster, profiles, itemCatalog) {
  const profileJson = JSON.stringify(profiles, null, 2);
  const itemJson = JSON.stringify(itemCatalog, null, 2);
  const slotJson = JSON.stringify(roster.armorSlots.map((slot) => slot.slot), null, 2);
  return `// Generated by scripts/blender-character-pipeline/tools/sync-playable-assets.mjs.
// Do not edit by hand.
import type { BodyVariant, PlayableRace } from './careers';
import { normalizeClassName } from './careers';
import type { EquipmentState, EquipSlot, InventoryItem } from '../services/types';

export const PLAYABLE_ASSET_VERSION = '${ASSET_VERSION}';
export const PLAYABLE_ARMOR_SLOTS = ${slotJson} as EquipSlot[];

export interface PlayableArmorProfile {
  slot: EquipSlot;
  itemKey: string;
  model: string;
  assetId: string;
  name: string;
  icon: string;
  coveredRegions: string[];
}

export interface PlayableCharacterProfile {
  race: PlayableRace;
  className: string;
  bodyVariant: BodyVariant;
  profileKey: string;
  assetId: string;
  model: string;
  bodyFamily: string;
  skeletonId: string;
  armor: Record<string, PlayableArmorProfile>;
}

export const PLAYABLE_CHARACTER_PROFILES = ${profileJson} as PlayableCharacterProfile[];

export const PLAYABLE_ARMOR_ITEM_CATALOG = ${itemJson} as const;

export function normalizeBodyVariant(value: string | null | undefined): BodyVariant {
  return value === 'f' ? 'f' : 'm';
}

export function findPlayableCharacterProfile(
  race: PlayableRace | string,
  className: string | null | undefined,
  bodyVariant: BodyVariant | string | null | undefined = 'm',
): PlayableCharacterProfile | null {
  const normalizedClassName = normalizeClassName(className);
  const normalizedVariant = normalizeBodyVariant(bodyVariant);
  return PLAYABLE_CHARACTER_PROFILES.find((profile) =>
    profile.race === race &&
    profile.className === normalizedClassName &&
    profile.bodyVariant === normalizedVariant
  ) ?? null;
}

export function playableCharacterProfileKeyFor(
  race: PlayableRace | string,
  className: string | null | undefined,
  bodyVariant: BodyVariant | string | null | undefined = 'm',
): string {
  return findPlayableCharacterProfile(race, className, bodyVariant)?.profileKey ?? \`\${race}_default\`;
}

export function starterArmorEquipmentFor(
  race: PlayableRace | string,
  className: string | null | undefined,
  bodyVariant: BodyVariant | string | null | undefined = 'm',
): EquipmentState {
  const profile = findPlayableCharacterProfile(race, className, bodyVariant);
  if (!profile) return {};
  const equipment: EquipmentState = {};
  for (const slot of PLAYABLE_ARMOR_SLOTS) {
    const armor = profile.armor[slot];
    if (!armor) continue;
    equipment[slot] = {
      key: armor.itemKey,
      name: armor.name,
      icon: armor.icon,
      kind: 'armor',
      equipSlot: slot,
    };
  }
  return equipment;
}

export function starterArmorInventoryFor(
  race: PlayableRace | string,
  className: string | null | undefined,
  bodyVariant: BodyVariant | string | null | undefined = 'm',
  startSlot = 5,
): InventoryItem[] {
  const profile = findPlayableCharacterProfile(race, className, bodyVariant);
  if (!profile) return [];
  const items: InventoryItem[] = [];
  PLAYABLE_ARMOR_SLOTS.forEach((slot, index) => {
    const armor = profile.armor[slot];
    if (!armor) return;
    items.push({
      slot: startSlot + index,
      key: armor.itemKey,
      name: armor.name,
      qty: 1,
      icon: armor.icon,
      kind: 'armor',
      equipSlot: slot,
    });
  });
  return items;
}
`;
}

const roster = readJson(ROSTER_PATH);
const characterProfiles = [];
const itemCatalog = {};
const index = existsSync(ASSET_INDEX_PATH)
  ? readJson(ASSET_INDEX_PATH)
  : { schemaVersion: 1, generatedFrom: "scripts/blender-character-pipeline/data/asset-blueprints" };

index.schemaVersion = 1;
index.generatedFrom = "scripts/blender-character-pipeline/data/asset-blueprints";
index.assetVersion = ASSET_VERSION;
index.characterProfiles = index.characterProfiles ?? {};
index.baseBodies = index.baseBodies ?? {};
index.equipment = index.equipment ?? {};
index.staticProps = index.staticProps ?? {};

let characterCount = 0;
let armorCount = 0;

for (const klass of roster.classes) {
  const race = roster.races[klass.race];
  if (!race) throw new Error(`Unknown race for ${klass.className}: ${klass.race}`);

  for (const [variantKey, variant] of Object.entries(roster.bodyVariants)) {
    const profileKey = profileKeyFor(race, klass, variantKey);
    const bodyFamily = bodyFamilyFor(race, klass, variantKey);
    const charBlueprint = characterBlueprint(roster, klass.race, race, klass, variantKey, variant);
    const charPath = path.join(BLUEPRINT_DIR, `${charBlueprint.output.model.replace(/\.glb$/i, ".asset.json")}`);
    writeJson(charPath, charBlueprint);
    index.characterProfiles[profileKey] = {
      assetId: charBlueprint.assetId,
      model: charBlueprint.output.model,
      bodyFamily,
      skeletonId: "humanoid_v1",
    };

    const armor = {};
    for (const slotDef of roster.armorSlots) {
      const armorBlueprintRecord = armorBlueprint(klass.race, race, klass, slotDef, variantKey, variant);
      const armorPath = path.join(BLUEPRINT_DIR, `${armorBlueprintRecord.output.model.replace(/\.glb$/i, ".asset.json")}`);
      writeJson(armorPath, armorBlueprintRecord);
      const itemKey = armorBlueprintRecord.runtime.itemKey;
      const name = `${klass.className} ${slotDef.label} (${variant.label})`;
      const armorEntry = {
        slot: slotDef.slot,
        itemKey,
        model: armorBlueprintRecord.output.model,
        assetId: armorBlueprintRecord.assetId,
        name,
        icon: slotDef.icon,
        coveredRegions: slotDef.regions,
      };
      armor[slotDef.slot] = armorEntry;
      itemCatalog[itemKey] = {
        key: itemKey,
        name,
        icon: slotDef.icon,
        kind: "armor",
        equipSlot: slotDef.slot,
        visual: { model: armorBlueprintRecord.output.model, fallback: "overlay" },
      };
      index.equipment[itemKey] = {
        assetId: armorBlueprintRecord.assetId,
        model: armorBlueprintRecord.output.model,
        runtimeReady: true,
        bodyFamily,
        skeletonId: "humanoid_v1",
        skinned: true,
        coveredRegions: slotDef.regions,
      };
      armorCount += 1;
    }

    characterProfiles.push({
      race: klass.race,
      className: klass.className,
      bodyVariant: variantKey,
      profileKey,
      assetId: charBlueprint.assetId,
      model: charBlueprint.output.model,
      bodyFamily,
      skeletonId: "humanoid_v1",
      armor,
    });
    characterCount += 1;
  }
}

writeJson(ASSET_INDEX_PATH, index);
writeFileSync(GENERATED_TS_PATH, generatedTs(roster, characterProfiles, itemCatalog), "utf8");

console.log(`Synced ${characterCount} playable character manifests and ${armorCount} playable armor manifests.`);
console.log(`Updated ${path.relative(REPO_ROOT, ASSET_INDEX_PATH)}`);
console.log(`Updated ${path.relative(REPO_ROOT, GENERATED_TS_PATH)}`);
