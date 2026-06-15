import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "fs";
import path from "path";
import {
  ASSET_INDEX_PATH,
  BLUEPRINT_DIR,
  PIPELINE_ROOT,
  REPO_ROOT,
} from "./pipeline-lib.mjs";
import {
  creatureAssetKeyForEnemy,
  enemyProfileInfo,
  npcProfileInfo,
  slug,
  withEnemyVisual,
  withNpcVisual,
} from "../../npc-profile-rules.mjs";

const MAPS_DIR = path.join(REPO_ROOT, "public", "assets", "maps");
const PLAYABLE_ROSTER_PATH = path.join(PIPELINE_ROOT, "data", "playable-character-roster.json");
const NPC_ROSTER_PATH = path.join(PIPELINE_ROOT, "data", "npc-character-roster.json");
const ASSET_VERSION = "2026-06-13-npc-variants";
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
  writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function profileKeyFor(race, klass, variantKey) {
  return `${race.family}_${klass.key}_${variantKey}`;
}

function combinedScale(race, variant) {
  return [
    Number((race.scale[0] * variant.scale[0]).toFixed(3)),
    Number((race.scale[1] * variant.scale[1]).toFixed(3)),
    Number((race.scale[2] * variant.scale[2]).toFixed(3)),
  ];
}

function baseStyleForProfile(roster, profileKey) {
  for (const klass of roster.classes) {
    const race = roster.races[klass.race];
    if (!race) continue;
    for (const [variantKey, variant] of Object.entries(roster.bodyVariants)) {
      if (profileKeyFor(race, klass, variantKey) !== profileKey) continue;
      const colors = klass.colors ?? {};
      return {
        baseProfileKey: profileKey,
        raceKey: klass.race,
        classKey: klass.key,
        className: klass.className,
        variant: variantKey,
        variantLabel: variant.label,
        bodyScale: combinedScale(race, variant),
        skin: race.skin,
        hair: race.hair,
        traits: race.traits ?? [],
        archetype: klass.archetype ?? "fighter",
        animationProfile: klass.animationProfile ?? "sword_shield",
        headgear: klass.headgear ?? "helmet",
        cloth: colors.cloth ?? "#26242a",
        cloth2: colors.cloth2 ?? "#5d4f42",
        metal: colors.metal ?? "#3f464a",
        trim: colors.trim ?? "#a77a34",
        leather: colors.leather ?? "#2f1d12",
        accent: colors.accent ?? colors.trim ?? "#b98a35",
      };
    }
  }
  throw new Error(`Unknown base profile ${profileKey}`);
}

function hashNumber(value) {
  let hash = 2166136261;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function clamp(value) {
  return Math.max(0, Math.min(255, value));
}

function adjustHex(hex, amount) {
  const value = hex.replace("#", "");
  const channels = [0, 2, 4].map((offset) => parseInt(value.slice(offset, offset + 2), 16));
  return `#${channels.map((channel) => clamp(channel + amount).toString(16).padStart(2, "0")).join("")}`;
}

function variantScale(seed, axis, range) {
  const bucket = ((seed >>> (axis * 5)) & 31) / 31;
  return Number((1 + (bucket - 0.5) * range).toFixed(3));
}

function roleHeadgear(baseHeadgear, accessory, seed) {
  if (accessory === "vendor" || accessory === "banker") return (seed % 2 === 0) ? "hat" : "circlet";
  if (accessory === "trainer" || accessory === "caster") return (seed % 3 === 0) ? "hood" : baseHeadgear;
  if (accessory === "questgiver") return (seed % 2 === 0) ? "hat" : baseHeadgear;
  return baseHeadgear;
}

function roleArchetype(baseArchetype, accessory) {
  if (accessory === "vendor" || accessory === "banker" || accessory === "civilian") return "civilian";
  if (accessory === "questgiver") return "duelist";
  if (accessory === "captain") return "tank";
  if (accessory === "caster" || accessory === "trainer") return baseArchetype;
  return baseArchetype;
}

function styleForProfile(roster, info) {
  const base = baseStyleForProfile(roster, info.baseProfileKey);
  const seed = hashNumber(info.profileKey);
  const brightness = ((seed % 17) - 8);
  const roleBoost = info.accessory === "banker" ? 14 : info.accessory === "guard" || info.accessory === "captain" ? -8 : 0;
  const bodyScale = [
    Number((base.bodyScale[0] * variantScale(seed, 0, 0.10)).toFixed(3)),
    Number((base.bodyScale[1] * variantScale(seed, 1, 0.09)).toFixed(3)),
    Number((base.bodyScale[2] * variantScale(seed, 2, 0.10)).toFixed(3)),
  ];

  return {
    profileKey: info.profileKey,
    source: info.source,
    displayName: info.displayName,
    realm: info.realm,
    role: info.role,
    title: info.title,
    baseProfileKey: info.baseProfileKey,
    raceKey: base.raceKey,
    classKey: base.classKey,
    className: base.className,
    variant: base.variant,
    variantLabel: base.variantLabel,
    bodyScale,
    skin: adjustHex(base.skin, ((seed >>> 8) % 13) - 6),
    hair: adjustHex(base.hair, ((seed >>> 12) % 11) - 5),
    traits: base.traits,
    archetype: roleArchetype(base.archetype, info.accessory),
    animationProfile: base.animationProfile,
    headgear: roleHeadgear(base.headgear, info.accessory, seed),
    cloth: adjustHex(base.cloth, brightness + roleBoost),
    cloth2: adjustHex(base.cloth2, brightness),
    metal: adjustHex(base.metal, info.accessory === "guard" || info.accessory === "captain" ? 10 : brightness),
    trim: adjustHex(base.trim, info.accessory === "banker" ? 18 : brightness),
    leather: adjustHex(base.leather, info.accessory === "vendor" ? 12 : brightness),
    accent: adjustHex(base.accent, info.accessory === "questgiver" ? 18 : brightness),
    npcRole: info.role,
    npcAccessory: info.accessory,
    variationSeed: seed,
  };
}

function manifestArtifactDir(model) {
  return `artifacts/blender/manifest/${model.replace(/\.glb$/i, "")}`;
}

function characterHeightTolerance(profile) {
  if (profile.headgear === "spire") return 0.78;
  if (profile.headgear === "horned") return 0.62;
  if (profile.headgear === "hat") return 0.38;
  return 0.22;
}

function characterBlueprint(profile) {
  const model = `chr_${profile.profileKey}_t1.glb`;
  const heightToleranceM = characterHeightTolerance(profile);
  return {
    assetId: `chr.${profile.profileKey.replace(/_/g, ".")}.t1`,
    displayName: profile.displayName,
    category: "character",
    version: "1.0.0",
    sets: [
      "characters",
      profile.source === "enemy" ? "enemy_characters" : "npc_characters",
      "npc_model_buildout",
    ],
    runtime: { profileKey: profile.profileKey },
    output: {
      model,
      artifactDir: manifestArtifactDir(model),
    },
    generator: { kind: "characterPreset", preset: profile.profileKey },
    geometry: {
      originRule: "armature_root_grounded",
      upAxis: "+Y",
      forwardAxis: "+Z",
      bodyFamily: profile.profileKey,
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
      { name: "AP_BACK", type: "socket", parent: "chest", position: [0, Number((1.28 * profile.bodyScale[1]).toFixed(3)), Number((-0.12 * profile.bodyScale[2]).toFixed(3))] },
    ],
    materials: {
      master: "MM_CharacterPbr",
      textureSet: `${profile.profileKey}_t1`,
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
      aiStages: ["npc_roster_scan", "seeded_feature_variation", "procedural_generation"],
      promptIds: [`npc_profile_${profile.profileKey}`],
      referencePackId: "neutral_dark_fantasy_npc_v1",
      similarityReview: "not_required",
    },
    qc: {
      allowNonManifold: false,
      allowUvOverlap: true,
      maxDrawCalls: 16,
      maxFileSizeMb: 12,
      groundToleranceM: 0.03,
      expectedHeightM: Number((1.9 * profile.bodyScale[1]).toFixed(3)),
      ...(heightToleranceM !== 0.22 ? { heightToleranceM } : {}),
      maxMeshObjects: 110,
      requiresSkinnedMeshes: true,
      requiresPreview: true,
    },
  };
}

function creatureBlueprint(assetKey) {
  const stem = `prop_${assetKey}_t1`;
  return {
    assetId: `prop.creature.${slug(assetKey.replace(/^creature_/, ""))}.t1`,
    displayName: assetKey.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" "),
    category: "prop",
    version: "1.0.0",
    sets: ["enemy_creatures", "npc_model_buildout"],
    runtime: { staticKey: assetKey },
    output: {
      model: `${stem}.glb`,
      artifactDir: manifestArtifactDir(`${stem}.glb`),
    },
    generator: { kind: "staticPreset", preset: assetKey },
    geometry: {
      originRule: "root_grounded",
      upAxis: "+Y",
      forwardAxis: "+Z",
      lods: [
        { name: "LOD0", triTarget: 12000, screenCoverageMin: 0.2 },
        { name: "LOD1", triTarget: 6000, screenCoverageMin: 0.08 },
      ],
    },
    materials: {
      master: "MM_StaticCreaturePbr",
      textureSet: `${assetKey}_t1`,
      channels: ["baseColor", "roughness", "metallic", "normal", "occlusion"],
    },
    collision: {
      policy: "simple_capsule",
      primitives: [{ type: "capsule", tag: "creature_body" }],
    },
    compatibility: { occupiesSlots: ["creature"], requires: [], conflictsWith: [] },
    provenance: {
      createdBy: "procedural_blender_pipeline",
      aiAssisted: true,
      aiStages: ["enemy_roster_scan", "creature_silhouette_preset", "procedural_generation"],
      promptIds: [`creature_${assetKey}`],
      referencePackId: "neutral_dark_fantasy_creatures_v1",
      similarityReview: "not_required",
    },
    qc: {
      allowNonManifold: false,
      allowUvOverlap: true,
      maxDrawCalls: 24,
      maxFileSizeMb: 8,
      maxMeshObjects: 48,
    },
  };
}

function cleanupGeneratedBlueprints() {
  for (const file of readdirSync(BLUEPRINT_DIR)) {
    if (/^(chr_(npc|enemy)_|prop_creature_).+\.asset\.json$/i.test(file)) {
      rmSync(path.join(BLUEPRINT_DIR, file));
    }
  }
}

const roster = readJson(PLAYABLE_ROSTER_PATH);
const profileInfoByKey = new Map();
const creatureKeys = new Set();
let legacyMapWrites = 0;

for (const file of readdirSync(MAPS_DIR).filter((entry) => entry.endsWith(".json")).sort()) {
  const filePath = path.join(MAPS_DIR, file);
  const zone = readJson(filePath);
  let changed = false;

  zone.npcs = (zone.npcs ?? []).map((npc) => {
    const visual = withNpcVisual(zone, npc);
    if (JSON.stringify(visual) !== JSON.stringify(npc)) changed = true;
    const info = npcProfileInfo(zone, visual);
    profileInfoByKey.set(info.profileKey, info);
    return visual;
  });

  zone.enemies = (zone.enemies ?? []).map((enemy) => {
    const visual = withEnemyVisual(zone, enemy);
    if (JSON.stringify(visual) !== JSON.stringify(enemy)) changed = true;
    if (visual.characterProfileKey) {
      const info = enemyProfileInfo(zone, visual);
      profileInfoByKey.set(info.profileKey, info);
    }
    const creatureAssetKey = creatureAssetKeyForEnemy(visual);
    if (visual.assetKey === creatureAssetKey && creatureAssetKey) {
      creatureKeys.add(creatureAssetKey);
    }
    return visual;
  });

  if (changed && !zone.staticMapVersion) {
    writeJson(filePath, zone);
    legacyMapWrites += 1;
  }
}

const profiles = Array.from(profileInfoByKey.values())
  .sort((a, b) => a.profileKey.localeCompare(b.profileKey))
  .map((info) => styleForProfile(roster, info));

cleanupGeneratedBlueprints();

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

for (const key of Object.keys(index.characterProfiles)) {
  const entry = index.characterProfiles[key];
  if ((key.startsWith("npc_") || key.startsWith("enemy_")) && !entry?.assetId?.startsWith("chr.external.")) {
    delete index.characterProfiles[key];
  }
}
for (const key of Object.keys(index.staticProps)) {
  if (key.startsWith("creature_")) delete index.staticProps[key];
}

for (const profile of profiles) {
  const blueprint = characterBlueprint(profile);
  writeJson(path.join(BLUEPRINT_DIR, blueprint.output.model.replace(/\.glb$/i, ".asset.json")), blueprint);
  index.characterProfiles[profile.profileKey] = {
    assetId: blueprint.assetId,
    model: blueprint.output.model,
    bodyFamily: profile.profileKey,
    skeletonId: "humanoid_v1",
  };
}

for (const assetKey of Array.from(creatureKeys).sort()) {
  const blueprint = creatureBlueprint(assetKey);
  writeJson(path.join(BLUEPRINT_DIR, blueprint.output.model.replace(/\.glb$/i, ".asset.json")), blueprint);
  index.staticProps[assetKey] = {
    assetId: blueprint.assetId,
    model: blueprint.output.model,
  };
}

writeJson(NPC_ROSTER_PATH, {
  schemaVersion: 1,
  generatedFrom: "public/assets/maps/*.json",
  assetVersion: ASSET_VERSION,
  profiles,
});
writeJson(ASSET_INDEX_PATH, index);

console.log(`Synced ${profiles.length} NPC/enemy character profile manifest(s).`);
console.log(`Synced ${creatureKeys.size} creature manifest(s).`);
console.log(`Updated ${path.relative(REPO_ROOT, NPC_ROSTER_PATH)}`);
console.log(`Updated ${path.relative(REPO_ROOT, ASSET_INDEX_PATH)}`);
if (legacyMapWrites > 0) console.log(`Updated ${legacyMapWrites} legacy map file(s) with visual keys.`);
