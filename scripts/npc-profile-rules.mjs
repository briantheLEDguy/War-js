export const CREATURE_ASSET_KEYS = {
  'Ash Hound': 'creature_ash_hound',
  'Barrow Wolf': 'creature_barrow_wolf',
  'Lair Spider': 'creature_lair_spider',
  'Mire Hound': 'creature_mire_hound',
  'Rift Hound': 'creature_rift_hound',
  'War Boar': 'creature_war_boar',
  'Wild Stag': 'creature_wild_stag',
};

const FEMALE_NAME_HINTS = new Set([
  'Brigitte',
  'Elira',
  'Freia',
  'Hannelore',
  'Kara',
  'Mara',
  'Mira',
  'Nyra',
  'Serra',
]);

const CLASS_PROFILE_KEYS = new Map([
  ['Aether Sage', 'aether_aether_sage'],
  ['Battle Prelate', 'civic_battle_prelate'],
  ['Blade Savant', 'aether_blade_savant'],
  ['Blood Dancer', 'umbra_blood_dancer'],
  ['Bog Hexer', 'mire_bog_hexer'],
  ['Cleaver', 'mire_cleaver'],
  ['Crimson Acolyte', 'umbra_crimson_acolyte'],
  ['Doomseeker', 'stone_doomseeker'],
  ['Dread Guard', 'umbra_dread_guard'],
  ['Dreadsworn', 'riven_dreadsworn'],
  ['Dusk Weaver', 'umbra_dusk_weaver'],
  ['Ember Arcanist', 'civic_ember_arcanist'],
  ['Fang Herder', 'mire_fang_herder'],
  ['Glyphbinder', 'stone_glyphbinder'],
  ['Hex Inquisitor', 'civic_hex_inquisitor'],
  ['Pride Warden', 'aether_pride_warden'],
  ['Ruin Oracle', 'riven_ruin_oracle'],
  ['Siegewright', 'stone_siegewright'],
  ['Stoneguard', 'stone_stoneguard'],
  ['Sunfire Templar', 'civic_sunfire_templar'],
  ['Veil Ranger', 'aether_veil_ranger'],
  ['Void Magister', 'riven_void_magister'],
  ['Warbrute', 'mire_warbrute'],
  ['Warped Reaver', 'riven_warped_reaver'],
]);

export function slug(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'unnamed';
}

export function inferZoneRealm(zone) {
  if (zone?.campaign?.realm) return zone.campaign.realm;
  const id = String(zone?.id ?? '');
  if (/(rift|cinder|ash|gore|vile|night|rot|obsidian|bleak)/i.test(id)) return 'riftbound';
  return 'aegis';
}

export function profileKeyForNpc(zone, npc) {
  const realm = inferZoneRealm(zone);
  return `npc_${realm}_${slug(npc.name)}_${slug(npc.title ?? npc.role)}`;
}

export function creatureAssetKeyForEnemy(enemy) {
  if (CREATURE_ASSET_KEYS[enemy.name]) return CREATURE_ASSET_KEYS[enemy.name];
  if (enemy.archetype === 'beast') return `creature_${slug(enemy.name)}`;
  return null;
}

export function isTrainingTarget(enemy) {
  return /dummy|target/i.test(enemy.name ?? '');
}

export function profileKeyForEnemy(zone, enemy) {
  const realm = realmForEnemy(zone, enemy);
  return `enemy_${realm}_${slug(enemy.name)}_${slug(enemy.archetype ?? 'raider')}`;
}

export function withNpcVisual(zone, npc) {
  if (npc.characterProfileKey || npc.model) return npc;
  return {
    ...npc,
    characterProfileKey: profileKeyForNpc(zone, npc),
  };
}

export function withEnemyVisual(zone, enemy) {
  if (enemy.characterProfileKey || enemy.assetKey || enemy.model) return enemy;
  if (isTrainingTarget(enemy)) return { ...enemy, assetKey: 'dummy' };
  const creatureAssetKey = creatureAssetKeyForEnemy(enemy);
  if (creatureAssetKey) return { ...enemy, assetKey: creatureAssetKey };
  return {
    ...enemy,
    characterProfileKey: profileKeyForEnemy(zone, enemy),
  };
}

export function npcProfileInfo(zone, npc) {
  const profileKey = profileKeyForNpc(zone, npc);
  const realm = inferZoneRealm(zone);
  return {
    profileKey,
    source: 'static_npc',
    displayName: `${npc.name} - ${npc.title ?? npc.role}`,
    realm,
    role: npc.role,
    title: npc.title ?? '',
    baseProfileKey: baseProfileForNpc(realm, npc, profileKey),
    variantKey: variantForName(npc.name, profileKey),
    accessory: accessoryForNpc(npc),
  };
}

export function enemyProfileInfo(zone, enemy) {
  const profileKey = profileKeyForEnemy(zone, enemy);
  const realm = realmForEnemy(zone, enemy);
  return {
    profileKey,
    source: 'enemy',
    displayName: enemy.name,
    realm,
    role: enemy.archetype ?? 'raider',
    title: enemy.name,
    baseProfileKey: baseProfileForEnemy(realm, enemy, profileKey),
    variantKey: variantForName(enemy.name, profileKey),
    accessory: accessoryForEnemy(enemy),
  };
}

function realmForEnemy(zone, enemy) {
  const name = String(enemy.name ?? '');
  if (/aegis/i.test(name)) return 'aegis';
  if (/riftbound|rift |greenskin/i.test(name)) return 'riftbound';
  return inferZoneRealm(zone);
}

function variantForName(name, key) {
  const first = String(name ?? '').split(/\s+/)[0];
  if (FEMALE_NAME_HINTS.has(first)) return 'f';
  return hashNumber(key) % 5 === 0 ? 'f' : 'm';
}

function baseProfileForNpc(realm, npc, key) {
  const title = String(npc.title ?? '');
  for (const [className, familyKey] of CLASS_PROFILE_KEYS.entries()) {
    if (title.includes(className)) return `${familyKey}_${variantForName(npc.name, key)}`;
  }

  if (title.includes('Class Trainer')) {
    return realm === 'aegis'
      ? `aether_aether_sage_${variantForName(npc.name, key)}`
      : `riven_void_magister_${variantForName(npc.name, key)}`;
  }

  if (realm === 'aegis') {
    if (npc.role === 'guard' || /marshal|captain|guard/i.test(title)) {
      return choose(key, ['civic_sunfire_templar_m', 'stone_stoneguard_m', 'aether_pride_warden_m']);
    }
    if (npc.role === 'trainer' || /mentor|engineer/i.test(title)) {
      return choose(key, ['stone_siegewright_m', 'civic_battle_prelate_m', 'aether_aether_sage_f']);
    }
    if (npc.role === 'questgiver') return 'civic_hex_inquisitor_f';
    if (npc.role === 'banker') return choose(key, ['civic_battle_prelate_m', 'stone_glyphbinder_f']);
    if (npc.role === 'ambient') return choose(key, ['civic_ember_arcanist_f', 'aether_veil_ranger_m']);
    return choose(key, ['civic_hex_inquisitor_m', 'civic_ember_arcanist_f', 'stone_siegewright_m']);
  }

  if (npc.role === 'guard' || /marshal|captain|guard/i.test(title)) {
    return choose(key, ['riven_dreadsworn_m', 'umbra_dread_guard_m', 'mire_warbrute_m']);
  }
  if (npc.role === 'trainer' || /mentor|engineer/i.test(title)) {
    return choose(key, ['riven_void_magister_f', 'mire_bog_hexer_m', 'umbra_dusk_weaver_f']);
  }
  if (npc.role === 'banker') return choose(key, ['umbra_crimson_acolyte_f', 'riven_ruin_oracle_m']);
  if (npc.role === 'ambient') return choose(key, ['mire_fang_herder_m', 'umbra_blood_dancer_f']);
  return choose(key, ['riven_warped_reaver_m', 'mire_fang_herder_m', 'umbra_blood_dancer_f']);
}

function baseProfileForEnemy(realm, enemy, key) {
  const name = String(enemy.name ?? '');
  if (/Greenskin Brute/i.test(name)) return 'mire_warbrute_m';
  if (/Greenskin Ruffian/i.test(name)) return 'mire_cleaver_m';

  if (realm === 'aegis') {
    if (enemy.archetype === 'caster') return choose(key, ['civic_ember_arcanist_m', 'aether_aether_sage_f', 'stone_glyphbinder_m']);
    if (enemy.archetype === 'captain') return choose(key, ['civic_sunfire_templar_m', 'stone_stoneguard_m']);
    if (enemy.archetype === 'guard') return choose(key, ['civic_sunfire_templar_m', 'stone_stoneguard_m', 'aether_pride_warden_m']);
    return choose(key, ['civic_hex_inquisitor_m', 'aether_blade_savant_m', 'stone_doomseeker_m']);
  }

  if (enemy.archetype === 'caster') return choose(key, ['riven_void_magister_m', 'riven_ruin_oracle_f', 'umbra_dusk_weaver_f', 'mire_bog_hexer_m']);
  if (enemy.archetype === 'captain') return choose(key, ['riven_dreadsworn_m', 'umbra_dread_guard_m', 'mire_warbrute_m']);
  if (enemy.archetype === 'guard') return choose(key, ['riven_dreadsworn_m', 'umbra_dread_guard_m', 'mire_warbrute_m']);
  return choose(key, ['riven_warped_reaver_m', 'umbra_blood_dancer_f', 'mire_cleaver_m']);
}

function accessoryForNpc(npc) {
  const title = String(npc.title ?? '');
  if (npc.role === 'guard' || /marshal|captain|guard/i.test(title)) return 'guard';
  if (npc.role === 'trainer' || /mentor|engineer/i.test(title)) return 'trainer';
  if (npc.role === 'banker') return 'banker';
  if (npc.role === 'questgiver') return 'questgiver';
  if (npc.role === 'ambient') return /scout|warden|guide/i.test(title) ? 'scout' : 'civilian';
  return 'vendor';
}

function accessoryForEnemy(enemy) {
  if (enemy.archetype === 'caster') return 'caster';
  if (enemy.archetype === 'captain') return 'captain';
  if (enemy.archetype === 'guard') return 'guard';
  return 'raider';
}

function choose(key, values) {
  return values[hashNumber(key) % values.length];
}

function hashNumber(value) {
  let hash = 2166136261;
  for (const char of String(value)) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}
