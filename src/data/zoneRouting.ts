import { CAMPAIGN_ZONE_BY_ID, isCampaignZoneId } from './campaign';
import type { CharacterState } from '../services/types';

type Race = CharacterState['race'];

const LEGACY_ZONE_ALIASES: Record<string, string> = {
  altdorf: 'aegis_capital',
  reikland: 'sunmeadow_march',
  inevitable_city: 'riftspire_capital',
};

export function defaultZoneForRace(race: Race): string {
  switch (race) {
    case 'empire':
    case 'dwarf':
    case 'high_elf':
      return 'aegis_capital';
    case 'chaos':
    case 'greenskin':
    case 'dark_elf':
      return 'riftspire_capital';
    default:
      return 'aegis_capital';
  }
}

export function defaultZoneSpawnPoint(zoneId: string): { x: number; y: number; z: number } {
  const nodeRole = CAMPAIGN_ZONE_BY_ID[zoneId]?.nodeRole;
  if (nodeRole === 'fortress') return { x: 0, y: 0, z: -118 };
  if (nodeRole === 'boss_lair') return { x: 0, y: 0, z: -58 };
  return { x: 0, y: 0, z: -40 };
}

export function normalizePlayableZoneId(
  zoneId: string | null | undefined,
  race: Race,
): string {
  const requested = zoneId?.trim();
  if (!requested) return defaultZoneForRace(race);
  const alias = LEGACY_ZONE_ALIASES[requested.toLowerCase()];
  if (alias) return alias;
  return isCampaignZoneId(requested) ? requested : defaultZoneForRace(race);
}

export function zoneWasNormalized(
  originalZoneId: string | null | undefined,
  normalizedZoneId: string,
): boolean {
  return originalZoneId !== normalizedZoneId;
}
