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

const AEGIS_GUARD_VARIANTS: NpcModelOverride[] = [
  { profileKey: AEGIS_WARRIOR_GUARD_PROFILE_KEY, fallbackModel: AEGIS_WARRIOR_GUARD_FALLBACK_MODEL },
  { profileKey: AEGIS_WARRIOR_GUARD_PROFILE_KEY, fallbackModel: AEGIS_WARRIOR_GUARD_FALLBACK_MODEL },
  { profileKey: AEGIS_SWORDSMAN_NPC_PROFILE_KEY, fallbackModel: AEGIS_SWORDSMAN_NPC_FALLBACK_MODEL },
  { profileKey: AEGIS_MEDIEVAL_CHARACTER_NPC_PROFILE_KEY, fallbackModel: AEGIS_MEDIEVAL_CHARACTER_NPC_FALLBACK_MODEL },
];

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
