import fs from 'node:fs';
import { sunmeadowPlacementClear } from './sunmeadow-environment.mjs';
import { integrateSharedKeepItems } from './shared-keep-items.mjs';
import { integrateRegionalInhabitants, integrateRegionalServicePresentations } from './regional-inhabitants.mjs';
import { integrateRegionalWorksites, integrateRegionalApothecaries } from './regional-worksites.mjs';

/** Shared siege/interior content is published once; exterior/biome kits remain regional. */
export { SHARED_KEEP_ITEMS } from './shared-keep-items.mjs';
const read = file => JSON.parse(fs.readFileSync(new URL(file, import.meta.url), 'utf8'));
const registry = () => read('../../public/assets/models/asset-index.json');

export function integrateRegionalAssets(zone, assets = registry(), workshopMetadata) {
  if (!zone.orvrLayout) return zone;
  zone.props = zone.props.filter(prop => !prop.id?.startsWith(`${zone.id}_delivered_`));
  const add = (id, key, x, z, extra = {}) => {
    const asset = assets.staticProps[key];
    if (!asset?.runtimeReady) return;
    zone.props.push({ id: `${zone.id}_delivered_${id}`, kind: key, assetKey: key, model: asset.model,
      x, z, rotY: 0, scale: 1, colliderSpace: 'model', ...extra });
  };
  integrateSharedKeepItems(zone, assets, workshopMetadata);
  integrateRegionalInhabitants(zone, assets);
  integrateRegionalServicePresentations(zone, assets);
  integrateRegionalWorksites(zone, assets, workshopMetadata);
  integrateRegionalApothecaries(zone, assets);
  if (zone.id !== 'sunmeadow_march') {
    // Cinderfen's architecture/ecology refreshes use a canonical prop order.
    // Final delivery must retain that order when adding its shared keep contents.
    if (zone.id === 'cinderfen_outskirts') zone.props.sort((a, b) => (a.id ?? '').localeCompare(b.id ?? ''));
    return zone;
  }
  const mentor = zone.npcs?.find(npc => npc.id === 'sunmeadow_march_craft_mentor');
  const artisan = 'npc_frontier_sunmeadow_dwarf_artisan';
  if (mentor && assets.characterProfiles[artisan]?.runtimeReady) {
    mentor.characterProfileKey = artisan;
    const assignment = zone.orvrLayout.populationAssignments.find(entry => entry.entityId === mentor.id);
    if (assignment) Object.assign(assignment, { race: 'dwarf', desiredProfileKey: artisan, status: 'approved' });
  }
  const locations = [
    ['roe_deer_buck', -282, 266], ['roe_deer_buck', 215, 340], ['roe_deer_buck', -182, 425],
    ['red_fox', -345, 200], ['red_fox', 125, -440],
    ['brown_hare', -294, -310], ['brown_hare', -164, 300], ['brown_hare', 290, 210],
    ['barrow_wolf', -405, 465], ['barrow_wolf', -365, 480],
    ['skylark', -293, -300], ['skylark', -120, 318],
  ];
  locations.forEach(([species, x, z], index) => {
    // Resolve a clear patch near the authored habitat without blocking routes,
    // mature trunks, resource rocks or objective approaches.
    for (let attempt = 0; attempt < 80; attempt++) {
      const point = { x: x + (attempt % 9 - 4) * 2.5, z: z + Math.floor(attempt / 9) * 2.5 };
      if (!sunmeadowPlacementClear(zone, point, 2)) continue;
      if (zone.props.some(prop => prop.colliders?.length && Math.hypot(point.x-prop.x, point.z-prop.z) < 5)) continue;
      add(`wildlife_${index}`, `frontier_sunmeadow_${species}`, point.x, point.z,
        { rotY: index * 2.399963, ...(species === 'roe_deer_buck' ? { defaultAnimation: 'idle' } : {}) });
      break;
    }
  });
  return zone;
}
