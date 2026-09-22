import type { WorldLifeActorSpawn } from './worldLifeTypes';

export const AEGIS_AMBIENT_GUARD_PROFILES = ['standard', 'halberd', 'crossbow', 'captain']
  .map(variant => `npc_aegis_city_guard_${variant}`);
export const AEGIS_AMBIENT_CIVILIAN_PROFILES = ['civilian_male', 'civilian_female']
  .map(variant => `npc_aegis_people_${variant}_walk`);

/** Stable cast choices keep a patrol's appearance consistent across zone reloads. */
export function worldLifeCharacterProfile(spawn: WorldLifeActorSpawn, realm: 'aegis' | 'riftbound'): string | null {
  if (realm !== 'aegis' || (spawn.kind !== 'guard' && spawn.kind !== 'citizen')) return null;
  if (spawn.characterProfileKey) return spawn.characterProfileKey;
  let hash = 2166136261;
  for (const character of spawn.id) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  const variant = Number.isFinite(spawn.variant) ? Math.abs(Math.floor(spawn.variant!)) : hash >>> 0;
  const profiles = spawn.kind === 'guard' ? AEGIS_AMBIENT_GUARD_PROFILES : AEGIS_AMBIENT_CIVILIAN_PROFILES;
  return profiles[variant % profiles.length];
}
