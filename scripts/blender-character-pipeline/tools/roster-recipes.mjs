import path from "node:path";
import { createHash } from "node:crypto";
import { PIPELINE_ROOT, readJson, workflowError } from "./workspace-paths.mjs";

const PILOT_RECIPE_PATH = path.join(
  PIPELINE_ROOT,
  "data",
  "body-families",
  "armor-sets",
  "free-pilot-armor-sets.json",
);

const REALM_PALETTES = {
  aegis: { metal: "#59666a", cloth: "#5f2020", leather: "#3b281c", accent: "#d3ae58" },
  riftbound: { metal: "#34343b", cloth: "#32172b", leather: "#26191a", accent: "#9a4d72" },
};

const ROLE_PALETTES = {
  ambient: { cloth: "#4b4438", accent: "#8f8064" },
  banker: { cloth: "#263648", accent: "#d2b76b" },
  captain: { cloth: "#681d21", accent: "#e0bc62" },
  caster: { cloth: "#2d284f", accent: "#927ce4" },
  guard: { cloth: "#3f4650", accent: "#c6a85a" },
  questgiver: { cloth: "#394c33", accent: "#d0bc62" },
  raider: { cloth: "#4f241e", accent: "#b7603e" },
  trainer: { cloth: "#4a3327", accent: "#c89354" },
  vendor: { cloth: "#3e4934", accent: "#c3a45c" },
};

// These are fitted CC0 meshes from the installed MakeHuman packs. The mapping
// is deliberately explicit: a class silhouette is art direction, not a random
// choice that can silently collapse the roster back to one outfit.
const CLASS_FIXTURES = {
  ember_arcanist: ["donitz_monk_robe_hood_off", "culturalibre_hero_suit_1", "culturalibre_hero-heroine_gloves_2", "rehmanpolanski_viking_pants", "shoes03"],
  hex_inquisitor: ["grinsegold_corinthian_helmet", "male_elegantsuit01", "toigo_gloves_short", "matcreator_mc-skinsuit_2022", "shoes06"],
  sunfire_templar: ["javherre_casco_caballero_templario_templar_knight_helmet", "rehmanpolanski_viking_tunic", "culturalibre_hero-heroine_gloves_5", "rehmanpolanski_viking_pants", "rehmanpolanski_viking_boots"],
  battle_prelate: ["grinsegold_corinthian_helmet", "male_casualsuit02", "toigo_gloves_medium", "rehmanpolanski_viking_pants", "rehmanpolanski_viking_boots"],
  stoneguard: ["javherre_casco_caballero_templario_templar_knight_helmet", "rehmanpolanski_viking_tunic", "toigo_gloves_short", "rehmanpolanski_viking_pants", "shoes04"],
  doomseeker: ["grinsegold_corinthian_helmet", "culturalibre_hero_suit_3", "learning_mma_fighting_gloves", "rehmanpolanski_viking_pants", "rehmanpolanski_viking_boots"],
  glyphbinder: ["donitz_monk_robe_hood_off", "green_tomato_rei_ayanami", "culturalibre_hero-heroine_gloves_1", "matcreator_mc-skinsuit_2022", "shoes02"],
  siegewright: ["javherre_casco_caballero_templario_templar_knight_helmet", "joachip_cyborg_suit", "toigo_gloves_short", "matcreator_mc-bodysuit-2021", "shoes05"],
  blade_savant: ["grinsegold_corinthian_helmet", "culturalibre_hero_suit_1", "culturalibre_hero-heroine_gloves_3", "matcreator_mc-skinsuit_2022", "shoes01"],
  pride_warden: ["grinsegold_corinthian_helmet", "thegreatengineer_galactic_warrior_uniform", "toigo_gloves_medium", "rehmanpolanski_viking_pants", "shoes04"],
  aether_sage: ["donitz_monk_robe_hood_off", "green_tomato_rei_ayanami", "culturalibre_hero-heroine_gloves_2", "matcreator_mc-skinsuit_2022", "shoes03"],
  veil_ranger: ["donitz_monk_robe_hood_off", "matcreator_mc-bodysuit-2021", "toigo_gloves_short", "rehmanpolanski_viking_pants", "rehmanpolanski_viking_boots"],
  dreadsworn: ["grinsegold_corinthian_helmet", "matcreator_mc-scifi-armor_jupiter7", "culturalibre_hero-heroine_gloves_5", "matcreator_mc-skinsuit_2022", "shoes06"],
  warped_reaver: ["javherre_casco_caballero_templario_templar_knight_helmet", "joachip_cyborg_suit", "learning_mma_fighting_gloves", "matcreator_mc-bodysuit-2021", "shoes05"],
  void_magister: ["donitz_monk_robe_hood_off", "male_casualsuit06", "toigo_gloves_short", "matcreator_mc-skinsuit_2022", "shoes02"],
  ruin_oracle: ["donitz_monk_robe_hood_off", "culturalibre_hero_suit_3", "toigo_gloves_short", "rehmanpolanski_viking_pants", "shoes01"],
  warbrute: ["grinsegold_corinthian_helmet", "rehmanpolanski_viking_tunic", "learning_mma_fighting_gloves", "rehmanpolanski_viking_pants", "rehmanpolanski_viking_boots"],
  fang_herder: ["donitz_monk_robe_hood_off", "male_worksuit01", "toigo_gloves_short", "rehmanpolanski_viking_pants", "shoes04"],
  bog_hexer: ["donitz_monk_robe_hood_off", "male_casualsuit04", "culturalibre_hero-heroine_gloves_1", "matcreator_mc-skinsuit_2022", "shoes03"],
  cleaver: ["grinsegold_corinthian_helmet", "culturalibre_hero_suit_2", "culturalibre_hero-heroine_gloves_3", "rehmanpolanski_viking_pants", "rehmanpolanski_viking_boots"],
  blood_dancer: ["grinsegold_corinthian_helmet", "culturalibre_hero_suit_2", "toigo_gloves_medium", "matcreator_mc-skinsuit_2022", "shoes06"],
  dread_guard: ["javherre_casco_caballero_templario_templar_knight_helmet", "matcreator_mc-scifi-armor_jupiter7", "culturalibre_hero-heroine_gloves_5", "matcreator_mc-bodysuit-2021", "shoes05"],
  dusk_weaver: ["donitz_monk_robe_hood_off", "slayer227_spider-gwen", "culturalibre_hero-heroine_gloves_2", "matcreator_mc-skinsuit_2022", "shoes02"],
  crimson_acolyte: ["donitz_monk_robe_hood_off", "male_elegantsuit01", "toigo_gloves_short", "rehmanpolanski_viking_pants", "shoes01"],
};

const HAT_ASSETS = new Set([
  "culturalibre_motorcycle_helmet",
  "culturalibre_skull_helmet",
  "culturalibre_warrior_helmet",
  "grinsegold_corinthian_helmet",
  "javherre_casco_caballero_templario_templar_knight_helmet",
  "fedora01",
  "fedora_cocked",
]);
const GLOVE_ASSETS = new Set([
  "culturalibre_hero-heroine_gloves_1", "culturalibre_hero-heroine_gloves_2",
  "culturalibre_hero-heroine_gloves_3", "culturalibre_hero-heroine_gloves_4",
  "culturalibre_hero-heroine_gloves_5", "learning_mma_fighting_gloves",
  "toigo_gloves_long", "toigo_gloves_medium", "toigo_gloves_short",
]);
const NPC_GLOVE_ASSETS = [
  "culturalibre_hero-heroine_gloves_1",
  "culturalibre_hero-heroine_gloves_2",
  "toigo_gloves_medium",
  "toigo_gloves_short",
];
const WINGED_SHOULDER_CLASSES = new Set([
  "ember_arcanist", "glyphbinder", "blade_savant", "aether_sage", "veil_ranger",
  "void_magister", "ruin_oracle", "bog_hexer", "blood_dancer", "dusk_weaver",
]);

// Full-outfit fixtures are segmented into the remaining logical armor slots.
// This gives shoulders, belts, capes, and tabards authored source topology and
// texture maps instead of the placeholder body patches used by the first run.
const AUXILIARY_FIXTURE_SETS = [
  {
    shoulders: "matcreator_mc-scifi-armor_helios",
    waist: "rehmanpolanski_viking_tunic",
    back: "donitz_monk_robe",
    tabard: "donitz_monk_robe",
  },
  {
    shoulders: "matcreator_mc-scifi-armor_jupiter7",
    waist: "green_tomato_yoko_tsuno",
    back: "donitz_monk_robe",
    tabard: "rehmanpolanski_viking_tunic",
  },
  {
    shoulders: "matcreator_mc-scifi-armor_helios",
    waist: "culturalibre_hero_suit_3",
    back: "donitz_monk_robe",
    tabard: "green_tomato_yoko_tsuno",
  },
  {
    shoulders: "joachip_cyborg_suit",
    waist: "thegreatengineer_galactic_warrior_uniform",
    back: "donitz_monk_robe",
    tabard: "culturalibre_hero_suit_3",
  },
];

const ROLE_CHEST = {
  ambient: "male_casualsuit03",
  banker: "male_elegantsuit01",
  captain: "rehmanpolanski_viking_tunic",
  caster: "male_casualsuit06",
  guard: "matcreator_mc-scifi-armor_jupiter7",
  questgiver: "male_casualsuit02",
  raider: "culturalibre_hero_suit_3",
  trainer: "male_worksuit01",
  vendor: "male_casualsuit05",
};
const ROLE_HEAD = {
  ambient: "donitz_monk_robe_hood_off",
  banker: "fedora01",
  captain: "grinsegold_corinthian_helmet",
  caster: "donitz_monk_robe_hood_off",
  guard: "javherre_casco_caballero_templario_templar_knight_helmet",
  questgiver: "donitz_monk_robe_hood_off",
  raider: "grinsegold_corinthian_helmet",
  trainer: "fedora_cocked",
  vendor: "fedora01",
};

function stableUnit(key, channel) {
  return createHash("sha256").update(`${key}:${channel}`).digest()[0] / 255;
}

function packForAsset(asset) {
  if (HAT_ASSETS.has(asset)) return "hats02";
  if (GLOVE_ASSETS.has(asset)) return "gloves01";
  return "suits02";
}

function classFixture(key) {
  const fixture = CLASS_FIXTURES[key];
  if (!fixture) throw workflowError("CLASS_FIXTURE_MISSING", `No fitted fixture design exists for ${key}.`);
  return fixture;
}

function modulesFromFixture({ key, realm, revisionSeed, fixture }) {
  const [head, chest, hands, legs, feet] = fixture;
  return {
    head: {
      kind: "mpfbAsset", pack: packForAsset(head), asset: head, materialStyle: "metal",
      faceCoverage: "open", faceOcclusionAllowed: false,
    },
    shoulders: {
      kind: "bodySurface", bones: ["shoulder_L", "shoulder_R", "upper_chest"],
      materialStyle: "metal",
      normalOffsetM: Number((0.022 + stableUnit(`${key}:shoulders`, revisionSeed + 1) * 0.010).toFixed(4)),
      thicknessM: Number((0.008 + stableUnit(`${realm}:shoulders`, revisionSeed + 2) * 0.005).toFixed(4)),
      silhouetteProfile: WINGED_SHOULDER_CLASSES.has(key) ? "winged" : "rounded",
    },
    chest: { kind: "mpfbAsset", pack: packForAsset(chest), asset: chest, materialStyle: "cloth" },
    hands: { kind: "mpfbAsset", pack: packForAsset(hands), asset: hands, materialStyle: "leather" },
    waist: {
      kind: "bodySurface", bones: ["hips", "spine"], materialStyle: "leather",
      normalOffsetM: Number((0.018 + stableUnit(`${key}:waist`, revisionSeed + 2) * 0.012).toFixed(4)),
      thicknessM: Number((0.007 + stableUnit(realm, revisionSeed + 3) * 0.006).toFixed(4)),
    },
    legs: { kind: "mpfbAsset", pack: packForAsset(legs), asset: legs, materialStyle: "cloth" },
    feet: { kind: "mpfbAsset", pack: packForAsset(feet), asset: feet, materialStyle: "leather" },
    back: { kind: "weightedPanel", panel: "back", materialStyle: "cloth", silhouetteProfile: key },
    tabard: { kind: "weightedPanel", panel: "front", materialStyle: "accent", silhouetteProfile: key },
  };
}

export function playableFixtureSignature(group) {
  return classFixture(group.key).join("|");
}

export function buildPlayableArmorRecipe(group, revisionSeed) {
  const pilot = readJson(PILOT_RECIPE_PATH);
  const fixture = classFixture(group.key);
  const palette = {
    metal: group.visualBrief.colors.metal,
    cloth: group.visualBrief.colors.cloth,
    leather: group.visualBrief.colors.leather,
    accent: group.visualBrief.colors.accent,
  };
  return {
    schemaVersion: 1,
    generatorKind: "mpfbFittedModularArmor",
    generatorVersion: "3.0.0-fixture-roster",
    license: "CC0-1.0",
    promotionEligible: false,
    sourcePacks: pilot.sourcePacks,
    fixtureCoverage: ["suits02", "hats02", "gloves01"],
    sets: {
      [group.key]: {
        setId: group.key,
        bodyFamily: group.bodyFamily,
        displayName: `${group.displayName} T1 Signature Set`,
        bodyVariants: ["m", "f"],
        palette,
        silhouetteSeed: `${group.key}:${revisionSeed}`,
        designSignature: playableFixtureSignature(group),
        revisionSeed,
        modules: modulesFromFixture({
          key: group.key,
          realm: group.realm,
          revisionSeed,
          fixture,
        }),
      },
    },
  };
}

export function buildNpcRoleArmorRecipe(group, role, revisionSeed) {
  const pilot = readJson(PILOT_RECIPE_PATH);
  const base = REALM_PALETTES[group.realm];
  const rolePalette = ROLE_PALETTES[role] ?? ROLE_PALETTES.ambient;
  const setId = `npc_${group.key}_${role}`;
  const head = ROLE_HEAD[role] ?? ROLE_HEAD.ambient;
  const chest = ROLE_CHEST[role] ?? ROLE_CHEST.ambient;
  const gloves = NPC_GLOVE_ASSETS[Math.floor(stableUnit(setId, revisionSeed) * NPC_GLOVE_ASSETS.length) % NPC_GLOVE_ASSETS.length];
  const legs = stableUnit(setId, "legs") > 0.45 ? "rehmanpolanski_viking_pants" : "matcreator_mc-skinsuit_2022";
  const feet = stableUnit(setId, "feet") > 0.5 ? "rehmanpolanski_viking_boots" : `shoes0${1 + Math.floor(stableUnit(setId, "shoe-index") * 6)}`;
  const fixture = [head, chest, gloves, legs, feet];
  return {
    schemaVersion: 1,
    generatorKind: "mpfbFittedModularArmor",
    generatorVersion: "3.0.0-fixture-roster",
    license: "CC0-1.0",
    promotionEligible: false,
    sourcePacks: pilot.sourcePacks,
    fixtureCoverage: ["suits02", "hats02", "gloves01"],
    sets: {
      [setId]: {
        setId,
        bodyFamily: group.bodyFamily,
        displayName: `${group.displayName} ${role} kit`,
        bodyVariants: [group.bodyVariant],
        palette: { ...base, ...rolePalette },
        silhouetteSeed: `${setId}:${revisionSeed}`,
        designSignature: fixture.join("|"),
        revisionSeed,
        modules: modulesFromFixture({ key: setId, realm: group.realm, revisionSeed, fixture }),
      },
    },
  };
}

export function buildNpcPhysique(policy, group) {
  const family = policy.bodyFamilies[group.race];
  return {
    profileKey: `npc.${group.race}.${group.bodyVariant}`,
    race: group.race,
    bodyFamily: group.bodyFamily,
    bodyVariant: group.bodyVariant,
    expectedHeightM: family.expectedHeightM[group.bodyVariant],
    propertyValues: {
      ...family.baseMacros[group.bodyVariant],
      gender: group.bodyVariant === "m" ? 1 : 0,
    },
    fixtureTargets: policy.raceIdentity[group.race].fixtureTargets,
    skin: policy.raceIdentity[group.race].skin[group.bodyVariant],
    grooming: policy.raceIdentity[group.race].grooming[group.bodyVariant],
  };
}

export const FIXTURE_PACK_CONTRACT = Object.freeze([
  "makehuman_system_assets", "skins03", "ears01", "hands01", "nose01",
  "cheek01", "faceunits01", "suits02", "hats02", "gloves01", "equipment01",
]);
