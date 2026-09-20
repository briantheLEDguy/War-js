import fs from 'node:fs';
import { expect, test } from 'vitest';
// @ts-expect-error Campaign authoring source is executable JavaScript.
import { integrateRegionalAssets, SHARED_KEEP_ITEMS } from '../scripts/campaign/regional-asset-integration.mjs';
// @ts-expect-error Campaign authoring source is executable JavaScript.
import { sunmeadowPlacementClear } from '../scripts/campaign/sunmeadow-environment.mjs';
// @ts-expect-error Campaign authoring source is executable JavaScript.
import { sharedKeepItemEnvelopes } from '../scripts/campaign/shared-keep-items.mjs';
// @ts-expect-error Campaign authoring source is executable JavaScript.
import { composeCinderfenEnvironment } from '../scripts/campaign/cinderfen-environment.mjs';
// @ts-expect-error Campaign authoring source is executable JavaScript.
import { composeCinderfenLandscape } from '../scripts/campaign/cinderfen-landscape.mjs';
// @ts-expect-error Campaign authoring source is executable JavaScript.
import { integrateCinderfen } from '../scripts/campaign/cinderfen-integration.mjs';
import { mapPropNavigation } from '../server/mapNavigation';
import { campaignColliderContains, campaignGroundHeight } from '../src/shared/orvr/navigation';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { createKeepEnclosureAudit } from '../scripts/audit-keep-enclosures';
const read = (file: string) => JSON.parse(fs.readFileSync(file, 'utf8'));
const source = read('public/assets/maps/sunmeadow_march.json');
const registry = read('public/assets/models/asset-index.json');

test('delivered cast preserves service identities and wildlife stays off objective/travel corridors', () => {
  const result = integrateRegionalAssets(structuredClone(source), registry);
  expect(integrateRegionalAssets(structuredClone(result), registry)).toEqual(result);
  expect(result.npcs.map((npc: { id: string }) => npc.id)).toEqual(source.npcs.map((npc: { id: string }) => npc.id));
  const mentor = result.npcs.find((npc: { id: string }) => npc.id.endsWith('_craft_mentor'));
  expect(mentor.characterProfileKey).toBe('npc_frontier_sunmeadow_dwarf_artisan');
  expect(result.orvrLayout.populationAssignments.find((a: {entityId: string}) => a.entityId === mentor.id).race).toBe('dwarf');
  const fauna = result.props.filter((prop: {id: string}) => prop.id.includes('_delivered_wildlife_'));
  expect(fauna).toHaveLength(12);
  for(const prop of fauna) {
    expect(registry.staticProps[prop.assetKey].runtimeReady).toBe(true);
    expect(sunmeadowPlacementClear(result, prop, 2)).toBe(true);
  }
});

test('siege contents share keys across pairings while existing thematic exteriors stay intact', async () => {
  const configs = await loadCampaignMapConfigs();
  const ready = structuredClone(registry);
  const contracts = read('authoring/blender/frontier-workshop-items/builder-contract.json').assets;
  for(const key of SHARED_KEEP_ITEMS) {
    ready.staticProps[key] = { runtimeReady: true, model: `${key}_lod0.glb`, modelSha256: key };
    Object.assign(contracts[key], { runtimeReady: true, modelSha256: key });
  }
  const maps = fs.readdirSync('public/assets/maps').filter(file => file.endsWith('.json'))
    .map(file => read(`public/assets/maps/${file}`)).filter(map => map.orvrLayout?.keeps?.length);
  expect(maps).toHaveLength(18);
  for(const map of maps) {
    const before = map.props.filter((p: {id: string}) => !p.id.includes('_delivered_'));
    const result = integrateRegionalAssets(map, ready, contracts);
    const config = configs.find(config => config.id === map.id)!;
    const items = result.props.filter((p: {assetKey: string}) => SHARED_KEEP_ITEMS.includes(p.assetKey));
    expect(items, map.id).toHaveLength(4);
    expect(result.props.filter((p: {id: string}) => !p.id.includes('_delivered_'))).toEqual(before);
    expect(integrateRegionalAssets(structuredClone(result), ready, contracts)).toEqual(result);
    const solids = mapPropNavigation(before, () => 0).collision;
    for (const item of items) {
      const contract = contracts[item.assetKey];
      expect(item.colliders).toEqual(contract.colliders);
      const envelopes = sharedKeepItemEnvelopes(item, contract);
      for (const box of envelopes) {
        expect(solids.some(collider => box.minX < collider.maxX && box.maxX > collider.minX
          && box.minZ < collider.maxZ && box.maxZ > collider.minZ), `${item.id} geometry/frontage`).toBe(false);
      }
      const footprint = envelopes[0];
      const baseY = item.heightMode === 'absolute' ? item.y : campaignGroundHeight(config, { ...item, y: 0 });
      for (const x of [footprint.minX, footprint.maxX]) for (const z of [footprint.minZ, footprint.maxZ]) {
        expect(Math.abs(campaignGroundHeight(config, { x, y: 0, z }) - baseY), `${item.id} grounded feet`).toBeLessThan(.025);
      }
      const navigation = mapPropNavigation([item], () => 0);
      const solid = navigation.collision.find(collider => collider.maxY! > .8);
      expect(solid).toBeDefined();
      expect(campaignColliderContains(solid!, solid!.footprint!, .45)).toBe(true);
      const approach = envelopes[1];
      const center = { x: (approach.minX + approach.maxX) / 2, z: (approach.minZ + approach.maxZ) / 2 };
      expect(navigation.collision.some(collider => campaignColliderContains(collider, center, .45)), item.id).toBe(false);
    }
    const collision = [...config.collision ?? [], ...mapPropNavigation(items,
      (x,z) => campaignGroundHeight(config, { x, y: 0, z })).collision];
    for (const keep of config.keeps) {
      const audit = createKeepEnclosureAudit({ ...config, collision }, keep);
      const courtyard = { x: keep.position.x, y: 0, z: (keep.outerGate.z + keep.innerGate.z) / 2 };
      expect(audit().reachable, `${keep.id} remains closed`).toBe(false);
      expect(audit({ breachedGates: ['outer'], target: courtyard }).reachable, `${keep.id} forecourt`).toBe(true);
      expect(audit({ breachedGates: ['outer', 'inner'] }).reachable, `${keep.id} commander access`).toBe(true);
    }
  }
}, 30000);

test('unfinished or stale workshop collision metadata never creates pass-through scenery', () => {
  const ready = structuredClone(registry);
  for (const key of SHARED_KEEP_ITEMS) ready.staticProps[key] = { runtimeReady: true, model: `${key}_lod0.glb`, modelSha256: 'current' };
  const stale = read('authoring/blender/frontier-workshop-items/builder-contract.json').assets;
  for (const contract of Object.values(stale) as Record<string, unknown>[]) Object.assign(contract, { runtimeReady: true, modelSha256: 'old' });
  for (const metadata of [{}, stale]) {
    const result = integrateRegionalAssets(structuredClone(source), ready, metadata);
    expect(result.props.some((p: {assetKey: string}) => SHARED_KEEP_ITEMS.includes(p.assetKey))).toBe(false);
  }
});

test('delivered Cinderfen workshop contents retain order and placement through regional refreshes', () => {
  const ready = structuredClone(registry);
  const contracts = read('authoring/blender/frontier-workshop-items/builder-contract.json').assets;
  for (const key of SHARED_KEEP_ITEMS) {
    ready.staticProps[key] = { runtimeReady: true, model: `${key}_lod0.glb`, modelSha256: key };
    Object.assign(contracts[key], { runtimeReady: true, modelSha256: key });
  }
  const refresh = (zone: unknown) => integrateCinderfen(composeCinderfenEnvironment(
    composeCinderfenLandscape(zone, true), { architecture: true }));
  const prepared = refresh(read('public/assets/maps/cinderfen_outskirts.json'));
  const delivered = integrateRegionalAssets(prepared, ready, contracts);
  const items = delivered.props.filter((prop: { assetKey: string }) => SHARED_KEEP_ITEMS.includes(prop.assetKey));
  expect(items).toHaveLength(4);
  const refreshed = refresh(structuredClone(delivered));
  expect(refreshed.props).toEqual(delivered.props);
  expect(integrateRegionalAssets(refreshed, ready, contracts).props).toEqual(delivered.props);
});
