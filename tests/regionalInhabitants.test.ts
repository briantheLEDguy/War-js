import fs from 'node:fs';
import { expect, test } from 'vitest';
// @ts-expect-error Executable campaign authoring source.
import { integrateRegionalInhabitants, REGIONAL_INHABITANTS } from '../scripts/campaign/regional-inhabitants.mjs';
import { mapPropNavigation } from '../server/mapNavigation';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { campaignColliderContains, campaignColliderBlocksHeight, campaignGroundHeight } from '../src/shared/orvr/navigation';
import { campaignNpcProfile } from '../src/game/network/CampaignCharacterPresentation';
import type { ZoneDefinition, NpcSpawn } from '../src/world/ZoneLoader';

const map = (id: string) => JSON.parse(fs.readFileSync(`public/assets/maps/${id}.json`, 'utf8')) as ZoneDefinition;
const profile = (civilian: { assetId: string }) => ({ runtimeReady: true, assetId: civilian.assetId,
  approvalState: 'approved', lifecycleStatus: 'approved', reviewStatus: 'approved', modelSha256: 'a'.repeat(64) });

test.each(['sunmeadow_march', 'cinderfen_outskirts'])('%s only delivers finished regional civilians and preserves existing services', async id => {
  const civilian = REGIONAL_INHABITANTS[id][0];
  const source = map(id), prefix = `${id}_inhabitant_`;
  const original = source.npcs!.filter(npc => !npc.id.startsWith(prefix));
  const assets = { characterProfiles: { [civilian.profile]: profile(civilian) } };
  const delivered = integrateRegionalInhabitants(structuredClone(source), assets) as ZoneDefinition;
  expect(delivered.npcs!.filter(npc => !npc.id.startsWith(prefix))).toEqual(original);
  expect(integrateRegionalInhabitants(structuredClone(delivered), assets)).toEqual(delivered);
  const residents = delivered.npcs!.filter(npc => npc.id.startsWith(prefix));
  expect(residents).toHaveLength(1);
  const npc = residents[0], assignment = delivered.orvrLayout!.populationAssignments.find(a => a.entityId === npc.id)!;
  expect(npc.approvedOnly).toBe(true);
  expect(assignment).toMatchObject({ race: civilian.race, desiredProfileKey: civilian.profile, status: 'approved' });
  expect(campaignNpcProfile({ id: npc.id, role: npc.role, race: assignment.race, profileKey: npc.characterProfileKey })).toBe(civilian.profile);
  const config = (await loadCampaignMapConfigs()).find(c => c.id === id)!;
  const ground = (x: number, z: number) => campaignGroundHeight(config, { x, y: 0, z });
  const y = ground(npc.x, npc.z), solids = mapPropNavigation(delivered.props!, ground).collision;
  expect(solids.some(s => campaignColliderBlocksHeight(s, y, 1.9) && campaignColliderContains(s, npc, 1.1))).toBe(false);
  for (const dx of [-.45, .45]) for (const dz of [-.45, .45]) expect(Math.abs(ground(npc.x + dx, npc.z + dz) - y)).toBeLessThan(.025);
  const removed = integrateRegionalInhabitants(structuredClone(delivered), { characterProfiles: {} }) as ZoneDefinition;
  expect(removed.npcs).toEqual(original);
  expect(removed.orvrLayout!.populationAssignments.some(a => a.entityId === npc.id)).toBe(false);
});

test('planned, wrong-identity or obstructed characters never add proxy residents', () => {
  const source = map('sunmeadow_march'), civilian = REGIONAL_INHABITANTS.sunmeadow_march[0];
  for (const overrides of [{ runtimeReady: false }, { approvalState: 'pending' }, { assetId: 'chr.other' }, { modelSha256: '' }]) {
    const delivered = integrateRegionalInhabitants(structuredClone(source), { characterProfiles: { [civilian.profile]: { ...profile(civilian), ...overrides } } });
    expect(delivered.npcs.some((npc: NpcSpawn) => npc.id.startsWith('sunmeadow_march_inhabitant_'))).toBe(false);
  }
  source.props.push({ id: 'standing-space-obstruction', kind: 'existing_wall', x: civilian.x, z: civilian.z,
    colliders: [{ width: 2, depth: 2, minY: 0, maxY: 2 }] });
  const blocked = integrateRegionalInhabitants(source, { characterProfiles: { [civilian.profile]: profile(civilian) } });
  expect(blocked.npcs.some((npc: NpcSpawn) => npc.id.startsWith('sunmeadow_march_inhabitant_'))).toBe(false);
});
