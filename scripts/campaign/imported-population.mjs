import { readFileSync } from 'node:fs';

export const importedPopulation = JSON.parse(readFileSync(new URL('../../shared/data/importedPopulation.json', import.meta.url), 'utf8'));

/** Add authoritative camp identities without changing retained encounters or services. */
export function applyImportedCamps(zone) {
  const profiles = new Map(importedPopulation.models.map(row => [row.key, row.profile]));
  for (const camp of importedPopulation.camps.filter(row => row.zone === zone.id)) {
    for (const member of camp.members) {
      const list = camp.allegiance === 'hostile' ? zone.enemies : zone.npcs;
      const existing = list.find(row => row.id === member.id);
      const base = { id: member.id, name: member.name, x: member.x, z: member.z,
        characterProfileKey: profiles.get(member.model) };
      const row = camp.allegiance === 'hostile'
        ? { ...base, level: 3, maxHealth: 150, archetype: 'raider', aggroRange: 15,
          attackRange: 2.8, preferredRange: 2.2, attackDamage: 13, moveSpeed: 3.25 }
        : { ...base, role: member.role === 'guard' ? 'guard' : 'ambient', rotY: member.yaw * Math.PI / 180 };
      if (existing && JSON.stringify(existing) !== JSON.stringify(row)) {
        throw new Error(`Imported camp identity was edited; reconcile before regeneration: ${member.id}`);
      }
      if (!existing) list.push(row);
    }
  }
  return zone;
}
