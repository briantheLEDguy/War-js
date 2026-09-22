import { aegisNpcCivilianVariantFor, aegisNpcGuardVariantFor } from '../data/modelOverrides';
export interface CampaignNpcPresentation {
  id: string;
  role: string;
  race?: string;
  realm?: 'aegis' | 'riftbound' | null;
  profileKey?: string;
}
const riftRaces = new Set(['chaos', 'greenskin', 'dark_elf']);
const regionalInhabitants = new Map<string, string>([
  ['npc_frontier_sunmeadow_dwarf_artisan', 'dwarf'],
  ['npc_frontier_sunmeadow_empire_farmer', 'empire'],
  ['npc_frontier_sunmeadow_empire_herbalist', 'empire'],
  ['npc_frontier_sunmeadow_high_elf_scout', 'high_elf'],
  ['npc_frontier_cinderfen_greenskin_peat_worker', 'greenskin'],
  ['npc_frontier_cinderfen_dark_elf_supply_officer', 'dark_elf'],
  ['npc_frontier_cinderfen_greenskin_quartermaster', 'greenskin'],
]);

/** Preserve authored race/role and reviewed city variants; unbuilt racial sets stay unavailable. */
export function campaignNpcProfile(npc: CampaignNpcPresentation): string | undefined {
  if (npc.profileKey?.startsWith('npc_frontier_')) {
    const race = regionalInhabitants.get(npc.profileKey);
    if (!race || (npc.race && npc.race !== race)) return undefined;
    if (npc.realm && (riftRaces.has(race) ? 'riftbound' : 'aegis') !== npc.realm) return undefined;
    // Preserve the authored regional cast. The loader still requires a matching
    // approved registry entry; naming a planned profile does not publish it.
    return npc.profileKey;
  }
  let race = npc.race;
  if (npc.realm && race && (riftRaces.has(race) ? 'riftbound' : 'aegis') !== npc.realm) race = undefined;
  if (!race) {
    const authored = npc.profileKey?.startsWith('npc_riftspire_') ? npc.profileKey.slice('npc_riftspire_'.length) : undefined;
    race = npc.realm === 'aegis' ? 'empire' : authored ?? (npc.realm === 'riftbound' ? 'chaos' : 'empire');
  }
  if (riftRaces.has(race)) return `npc_riftspire_${race}`;
  if (race !== 'empire') return undefined;
  const explicit = npc.profileKey;
  if (explicit === 'civic_battle_prelate_m' || explicit?.startsWith('npc_aegis_city_guard_') || explicit?.startsWith('npc_aegis_people_')) return explicit;
  const military = /guard|captain|commander|raider|caster/.test(npc.role);
  const seed = /captain|commander/.test(npc.role) ? `${npc.id}_captain` : npc.id;
  return (military
    ? aegisNpcGuardVariantFor('guard', 'npc_aegis_guard', seed)
    : aegisNpcCivilianVariantFor(npc.role, 'npc_aegis_civilian', seed))?.profileKey;
}
