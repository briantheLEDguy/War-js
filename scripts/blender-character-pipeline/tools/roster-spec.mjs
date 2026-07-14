import { createHash } from "node:crypto";
import path from "node:path";
import { PIPELINE_ROOT, readJson, workflowError } from "./workspace-paths.mjs";
import { playableFixtureSignature } from "./roster-recipes.mjs";

export const ROSTER_POLICY_PATH = path.join(PIPELINE_ROOT, "data", "full-roster-policy.json");
export const PLAYABLE_ROSTER_PATH = path.join(PIPELINE_ROOT, "data", "playable-character-roster.json");
export const NPC_ROSTER_PATH = path.join(PIPELINE_ROOT, "data", "npc-character-roster.json");
export const ARMOR_SLOTS = ["head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard"];
export const BODY_VARIANTS = ["m", "f"];

const clamp = (value, minimum = 0, maximum = 1) => Math.min(maximum, Math.max(minimum, value));

function stableUnit(key, channel) {
  const byte = createHash("sha256").update(`${key}:${channel}`).digest()[0];
  return byte / 255;
}

export function classPhysique(policy, klass, variant) {
  const family = policy.bodyFamilies[klass.race];
  const identity = policy.raceIdentity[klass.race];
  if (!family) throw workflowError("UNKNOWN_PLAYABLE_RACE", `No body family is configured for ${klass.race}.`);
  if (!identity) throw workflowError("UNKNOWN_RACE_IDENTITY", `No fixture identity is configured for ${klass.race}.`);
  const base = family.baseMacros[variant];
  const archetype = policy.physiqueArchetypes[klass.archetype] ?? {};
  const jitter = (channel, range) => (stableUnit(klass.key, `${variant}:${channel}`) - 0.5) * range;
  const propertyValues = {
    ...base,
    gender: variant === "m" ? 1 : 0,
    muscle: clamp(base.muscle + (archetype.muscle ?? 0) + jitter("muscle", 0.025)),
    weight: clamp(base.weight + (archetype.weight ?? 0) + jitter("weight", 0.025)),
    height: clamp(base.height + (archetype.height ?? 0) + jitter("height", 0.018)),
    proportions: clamp(base.proportions + (archetype.proportions ?? 0) + jitter("proportions", 0.018)),
  };
  return {
    profileKey: `${family.id}.${klass.key}.${variant}`,
    classKey: klass.key,
    className: klass.className,
    race: klass.race,
    bodyFamily: family.id,
    bodyVariant: variant,
    expectedHeightM: Number((family.expectedHeightM[variant] * (0.985 + stableUnit(klass.key, `${variant}:stature`) * 0.03)).toFixed(4)),
    propertyValues,
    fixtureTargets: identity.fixtureTargets,
    skin: identity.skin[variant],
    grooming: identity.grooming[variant],
  };
}

function buildPlayableGroups(policy, playable) {
  return playable.classes.map((klass) => ({
    kind: "playable",
    key: klass.key,
    displayName: klass.className,
    realm: policy.bodyFamilies[klass.race].realm,
    race: klass.race,
    bodyFamily: policy.bodyFamilies[klass.race].id,
    variants: BODY_VARIANTS.map((variant) => ({
      variant,
      physique: classPhysique(policy, klass, variant),
      armorModules: ARMOR_SLOTS.map((slot) => ({
        slot,
        assetId: `arm.${policy.bodyFamilies[klass.race].id}.${klass.key}.${slot}.${variant}`,
        itemKey: `starter_${policy.bodyFamilies[klass.race].id.replace(/_v\d+$/, "")}_${klass.key}_${slot}_${variant}`,
      })),
    })),
    visualBrief: {
      archetype: klass.archetype,
      animationProfile: klass.animationProfile,
      headgear: klass.headgear,
      colors: klass.colors,
    },
    weaponHandlingModes: [...policy.weaponReview.handlingModes],
    futureAnimationPackId: `class_${klass.key}_v1`,
    futureAnimationClips: [...policy.animationPlan.playable.clips],
  }));
}

function buildNpcGroups(policy, npcRoster) {
  const groups = [];
  for (const [race, family] of Object.entries(policy.bodyFamilies)) {
    for (const variant of BODY_VARIANTS) {
      const matchingProfiles = npcRoster.profiles.filter((profile) => profile.raceKey === race && profile.variant === variant);
      groups.push({
        kind: "npc",
        key: `${race}_${variant}`,
        displayName: `${family.displayName} ${variant === "m" ? "Male" : "Female"} NPC Foundation`,
        realm: family.realm,
        race,
        bodyFamily: family.id,
        bodyVariant: variant,
        liveProfileKeys: matchingProfiles.map((profile) => profile.profileKey).sort(),
        liveProfiles: matchingProfiles
          .map((profile) => ({
            profileKey: profile.profileKey,
            source: profile.source,
            displayName: profile.displayName,
            title: profile.title,
            realm: profile.realm,
            role: profile.role,
            classKey: profile.classKey,
            bodyScale: profile.bodyScale,
            palette: {
              skin: profile.skin,
              hair: profile.hair,
              cloth: profile.cloth,
              cloth2: profile.cloth2,
              metal: profile.metal,
              trim: profile.trim,
              leather: profile.leather,
              accent: profile.accent,
            },
            variationSeed: profile.variationSeed,
          }))
          .sort((left, right) => left.profileKey.localeCompare(right.profileKey)),
        roleKits: [...new Set(matchingProfiles.map((profile) => profile.role))].sort(),
        weaponHandlingModes: [...policy.weaponReview.handlingModes],
        futureAnimationPlan: {
          base: policy.animationPlan.npc.base,
          overlays: [...policy.animationPlan.npc.overlays],
        },
      });
    }
  }
  return groups;
}

function buildCreatureGroups(policy) {
  return policy.creatures.map((creature) => ({
    kind: "creature",
    key: creature.key,
    displayName: creature.name,
    realm: creature.realm,
    bodyPlan: creature.bodyPlan,
    skeletonId: `creature_${creature.bodyPlan}_v1`,
    requiredMarkers: ["root", "ground_contact", "attack_origin", "hit_center"],
    futureAnimationPackId: `creature_${creature.key}_v1`,
  }));
}

export function compileRosterSpec() {
  const policy = readJson(ROSTER_POLICY_PATH);
  const playable = readJson(PLAYABLE_ROSTER_PATH);
  const npcRoster = readJson(NPC_ROSTER_PATH);
  const playableGroups = buildPlayableGroups(policy, playable);
  const npcGroups = buildNpcGroups(policy, npcRoster);
  const creatureGroups = buildCreatureGroups(policy);
  const groups = [...playableGroups, ...npcGroups, ...creatureGroups];
  return {
    schemaVersion: 1,
    policyId: policy.policyId,
    counts: {
      generationGroups: groups.length,
      playableGroups: playableGroups.length,
      playableAppearances: playableGroups.reduce((sum, group) => sum + group.variants.length, 0),
      armorModules: playableGroups.reduce((sum, group) => sum + group.variants.reduce((variantSum, variant) => variantSum + variant.armorModules.length, 0), 0),
      npcFoundations: npcGroups.length,
      liveNpcProfiles: npcRoster.profiles.length,
      creatureSpecies: creatureGroups.length,
    },
    weaponReview: policy.weaponReview,
    review: policy.review,
    groups,
  };
}

export function rosterGroup(kind, key) {
  const group = compileRosterSpec().groups.find((candidate) => candidate.kind === kind && candidate.key === key);
  if (!group) throw workflowError("ROSTER_GROUP_NOT_FOUND", `Unknown ${kind} roster group: ${key}.`);
  return group;
}

export function validateRosterSpec(spec = compileRosterSpec()) {
  const errors = [];
  if (spec.counts.generationGroups !== 48) errors.push(`Expected 48 generation groups, found ${spec.counts.generationGroups}.`);
  if (spec.counts.playableGroups !== 24) errors.push(`Expected 24 playable groups, found ${spec.counts.playableGroups}.`);
  if (spec.counts.playableAppearances !== 48) errors.push(`Expected 48 playable appearances, found ${spec.counts.playableAppearances}.`);
  if (spec.counts.armorModules !== 432) errors.push(`Expected 432 armor modules, found ${spec.counts.armorModules}.`);
  if (spec.counts.npcFoundations !== 12) errors.push(`Expected 12 NPC foundations, found ${spec.counts.npcFoundations}.`);
  if (spec.counts.liveNpcProfiles !== 106) errors.push(`Expected 106 live NPC profiles, found ${spec.counts.liveNpcProfiles}.`);
  if (spec.counts.creatureSpecies !== 12) errors.push(`Expected 12 creatures, found ${spec.counts.creatureSpecies}.`);
  const npcSources = spec.groups
    .filter((candidate) => candidate.kind === "npc")
    .flatMap((group) => group.liveProfiles);
  if (npcSources.filter((profile) => profile.source === "static_npc").length !== 74) errors.push("Expected 74 static NPC combinations.");
  if (npcSources.filter((profile) => profile.source === "enemy").length !== 32) errors.push("Expected 32 humanoid enemy combinations.");
  const realmRoles = new Set(npcSources.map((profile) => `${profile.realm}:${profile.role}`));
  if (realmRoles.size !== 17) errors.push(`Expected 17 realm/role combinations, found ${realmRoles.size}.`);
  for (const group of spec.groups.filter((candidate) => candidate.kind !== "creature")) {
    if (group.weaponHandlingModes.join(",") !== "one_handed,two_handed,dual_wield") {
      errors.push(`${group.kind}:${group.key} does not support all humanoid weapon modes.`);
    }
  }
  const physiqueSignatures = new Set();
  const fixtureSignatures = new Set();
  for (const group of spec.groups.filter((candidate) => candidate.kind === "playable")) {
    const fixtureSignature = playableFixtureSignature(group);
    if (fixtureSignatures.has(fixtureSignature)) errors.push(`Duplicate class fixture design: ${group.key}.`);
    fixtureSignatures.add(fixtureSignature);
    for (const variant of group.variants) {
      const signature = JSON.stringify(variant.physique.propertyValues);
      if (physiqueSignatures.has(signature)) errors.push(`Duplicate class physique: ${group.key}/${variant.variant}.`);
      physiqueSignatures.add(signature);
    }
  }
  if (fixtureSignatures.size !== 24) errors.push(`Expected 24 distinct class fixture designs, found ${fixtureSignatures.size}.`);
  const classAnimationPacks = spec.groups
    .filter((candidate) => candidate.kind === "playable")
    .map((group) => group.futureAnimationPackId);
  if (new Set(classAnimationPacks).size !== 24) errors.push("Each playable class requires a unique future animation pack.");
  const creatureAnimationPacks = spec.groups
    .filter((candidate) => candidate.kind === "creature")
    .map((group) => group.futureAnimationPackId);
  if (new Set(creatureAnimationPacks).size !== 12) errors.push("Each creature species requires a unique future animation pack.");
  return errors;
}
