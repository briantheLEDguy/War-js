import { playerRealmForRace, type PlayableRace } from './careers';

export const PLAYER_MODEL_OVERRIDE_PROFILE_KEY = 'player_strong_knight';
export const PLAYER_MODEL_OVERRIDE_FALLBACK_MODEL = 'chr_player_strong_knight.glb';

export const AEGIS_WARRIOR_GUARD_PROFILE_KEY = 'aegis_warrior_guard';
export const AEGIS_WARRIOR_GUARD_FALLBACK_MODEL = 'chr_external_warrior_guard.glb';

export const AEGIS_SWORDSMAN_NPC_PROFILE_KEY = 'npc_external_swordsman';
export const AEGIS_SWORDSMAN_NPC_FALLBACK_MODEL = 'chr_external_swordsman_npc.glb';

export const AEGIS_MEDIEVAL_CHARACTER_NPC_PROFILE_KEY = 'npc_external_medieval_character';
export const AEGIS_MEDIEVAL_CHARACTER_NPC_FALLBACK_MODEL = 'chr_external_medieval_character_npc.glb';

export const RIFTBOUND_EVIL_GUY_PROFILE_KEY = 'riftbound_evil_guy';
export const RIFTBOUND_EVIL_GUY_FALLBACK_MODEL = 'chr_external_evil_guy.glb';

export interface PlayerModelOverride {
  profileKey: string;
  fallbackModel: string;
}

export interface NpcModelOverride {
  profileKey: string;
  fallbackModel: string;
}

const AEGIS_GUARD_VARIANTS: NpcModelOverride[] = ['standard', 'halberd', 'crossbow', 'captain'].map(variant => ({
  profileKey: `npc_aegis_city_guard_${variant}`,
  fallbackModel: `chr_aegis_city_guard_${variant}.glb`,
}));

type AegisCivilianVariant = 'civilian_male' | 'civilian_female' | 'child' | 'lord' | 'lady' | 'courtier' | 'attendant';

function civilianModel(variant: AegisCivilianVariant): NpcModelOverride {
  return {
    profileKey: `npc_aegis_people_${variant}`,
    // Match the reviewed registry delivery; the full-detail source remains available.
    fallbackModel: `chr_aegis_people_${variant}_lod1.glb`,
  };
}

/** Upgrade retired Aegis service proxies without overriding authored civic cast. */
export function aegisNpcCivilianVariantFor(
  role: string,
  characterProfileKey?: string | null,
  seed = characterProfileKey ?? '',
): NpcModelOverride | null {
  if (role === 'guard' || !characterProfileKey?.startsWith('npc_aegis_')) return null;
  if (characterProfileKey.startsWith('npc_aegis_people_')) return null;
  if (role === 'banker' || role === 'trainer') return civilianModel('attendant');
  if (role === 'questgiver') return civilianModel('courtier');
  return civilianModel(hashString(seed) % 2 ? 'civilian_female' : 'civilian_male');
}

/** Domestic and public-room residents retain their existing identities and roles. */
export function aegisHouseResidentVariantFor(variant: string, index: number): NpcModelOverride {
  if (variant === 'chapel') return civilianModel('attendant');
  if (variant === 'civic') return civilianModel(index ? 'attendant' : 'courtier');
  return civilianModel(index % 2 ? 'civilian_male' : 'civilian_female');
}

export function playerModelOverrideForRace(race: PlayableRace): PlayerModelOverride {
  if (playerRealmForRace(race) === 'riftbound') {
    return {
      profileKey: RIFTBOUND_EVIL_GUY_PROFILE_KEY,
      fallbackModel: RIFTBOUND_EVIL_GUY_FALLBACK_MODEL,
    };
  }

  return {
    profileKey: PLAYER_MODEL_OVERRIDE_PROFILE_KEY,
    fallbackModel: PLAYER_MODEL_OVERRIDE_FALLBACK_MODEL,
  };
}

export function aegisNpcGuardVariantFor(
  role: string,
  characterProfileKey?: string | null,
  seed = characterProfileKey ?? '',
): NpcModelOverride | null {
  if (role !== 'guard' || characterProfileKey?.startsWith('npc_aegis_') !== true) return null;
  return pickAegisGuardVariant(seed);
}

export function aegisEnemyGuardVariantFor(
  archetype: string | undefined,
  characterProfileKey: string | undefined,
  name: string,
  seed = characterProfileKey ?? name,
): NpcModelOverride | null {
  if (archetype !== 'guard') return null;
  if (characterProfileKey?.startsWith('enemy_aegis_') || /\baegis\b/i.test(name)) {
    return pickAegisGuardVariant(seed);
  }
  return null;
}

function pickAegisGuardVariant(seed: string): NpcModelOverride {
  if (/captain|commander|officer/i.test(seed)) return AEGIS_GUARD_VARIANTS[3];
  if (/crossbow|marksman/i.test(seed)) return AEGIS_GUARD_VARIANTS[2];
  if (/halberd/i.test(seed)) return AEGIS_GUARD_VARIANTS[1];
  const hash = hashString(seed);
  return AEGIS_GUARD_VARIANTS[hash % AEGIS_GUARD_VARIANTS.length];
}

function hashString(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}
