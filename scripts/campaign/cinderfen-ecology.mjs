/** Marsh colonies follow the reviewed water table, with gaps for travel and combat. */
import { readFileSync } from 'node:fs';

const read = relative => JSON.parse(readFileSync(new URL(relative, import.meta.url), 'utf8'));
const survey = read('../../authoring/blender/cinderfen-terrain/terrain-source.json');
const metadata = read('../../authoring/blender/cinderfen-nature/builder-metadata.json');
const registry = read('../../public/assets/models/asset-index.json').staticProps;
export const CINDERFEN_WETLAND_ASSETS = ['frontier_cinderfen_reed_clump', 'frontier_cinderfen_sedge_horsetail'];
export const CINDERFEN_WATER_LEVEL = survey.waterLevel;
const round = n => Math.round(n * 1000) / 1000;

/** Bilinear samples of the exact Float32 grid used to build the retained terrain. */
export function cinderfenSurveyHeightAt(x, z) {
  const n = survey.segments, u = Math.max(0, Math.min(n, (x / survey.size + .5) * n));
  const v = Math.max(0, Math.min(n, (z / survey.size + .5) * n));
  const ix = Math.min(n - 1, Math.floor(u)), iz = Math.min(n - 1, Math.floor(v)), a = u - ix, b = v - iz;
  const at = (i, j) => survey.heights[j * (n + 1) + i];
  return (at(ix, iz) * (1 - a) + at(ix + 1, iz) * a) * (1 - b)
    + (at(ix, iz + 1) * (1 - a) + at(ix + 1, iz + 1) * a) * b;
}

const segmentDistance = (p, a, b) => {
  const dx = b.x - a.x, dz = b.z - a.z, length = dx * dx + dz * dz;
  const t = length ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.z - a.z) * dz) / length)) : 0;
  return Math.hypot(p.x - a.x - dx * t, p.z - a.z - dz * t);
};

export function cinderfenEcologyClear(zone, point, radius) {
  const reserve = [zone.spawnPoint && { ...zone.spawnPoint, radius: 10 },
    ...(zone.npcs ?? []).map(p => ({ ...p, radius: 5 })),
    ...(zone.resourceNodes ?? []).map(p => ({ ...p, radius: 4 })),
    ...(zone.craftingStations ?? []).map(p => ({ ...p, radius: p.radius + 2 })),
    ...(zone.rvrObjectives ?? []).map(p => ({ ...p, radius: p.captureRadius + 5 })),
    ...(zone.zoneTriggers ?? []).map(p => ({ ...p, radius: p.radius + 5 })),
    ...zone.orvrLayout.terrain.flattenAreas].filter(Boolean);
  if (reserve.some(p => Math.hypot(point.x - p.x, point.z - p.z) < p.radius + radius)) return false;
  if (zone.paths.some(path => path.points.slice(1).some((p, i) => segmentDistance(point, path.points[i], p) < path.width / 2 + radius + 2))) return false;
  for (const actor of zone.ambientLife?.actors ?? []) {
    if (actor.kind === 'bird') continue;
    const route = [actor, ...(actor.route ?? []), actor];
    if (route.slice(1).some((p, i) => segmentDistance(point, route[i], p) < radius + 2)) return false;
  }
  return true;
}

export function composeCinderfenEcology(zone) {
  if (zone.id !== 'cinderfen_outskirts' || !zone.orvrLayout) return zone;
  for (const field of ['landforms', 'flattenAreas', 'clearCorridors']) {
    if (JSON.stringify(zone.orvrLayout.terrain[field]) !== JSON.stringify(survey.terrain[field]))
      throw Error(`Cinderfen ecology needs a current retained terrain survey: ${field}`);
  }
  if (zone.size !== survey.size || zone.segments !== survey.segments) throw Error('Cinderfen ecology terrain grid changed.');
  const ready = CINDERFEN_WETLAND_ASSETS.filter(key => registry[key]?.runtimeReady && metadata.assets[key]?.runtimeReady
    && registry[key].modelSha256 === metadata.assets[key].modelSha256);
  const prefix = `${zone.id}_wetland_`;
  zone.props = zone.props.filter(p => !p.id?.startsWith(prefix));
  if (!ready.length) return zone;
  let seed = 824731;
  const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  const entries = [];
  // Separate colonies leave open mud and shallow-water breaks between inlet stands.
  const colonies = [
    ['west_north', -266, 358, 75, 65], ['west_south', -258, 143, 68, 58],
    ['west_headland', -308, 236, 68, 64], ['west_east', -96, 216, 64, 55],
    ['west_islet', -180, 281, 58, 44], ['east_north', 169, 290, 82, 64],
    ['east_south', 235, 116, 80, 52], ['east_headland', 290, 218, 74, 59],
    ['east_islet', 170, 195, 51, 61], ['mineral_west', -88, -350, 108, 48],
    ['mineral_south', 109, -403, 110, 47], ['mineral_spit', 22, -390, 62, 52],
  ];
  for (const [colony, cx, cz, rx, rz] of colonies) {
    for (let i = 0; i < 1100; i++) {
      const angle = random() * Math.PI * 2, reach = Math.sqrt(random());
      const x = round(cx + Math.cos(angle) * rx * reach), z = round(cz + Math.sin(angle) * rz * reach);
      const height = cinderfenSurveyHeightAt(x, z);
      const reed = height < survey.waterLevel + .15;
      const key = CINDERFEN_WETLAND_ASSETS[reed ? 0 : 1];
      if (!ready.includes(key) || height < survey.waterLevel - .38 || height > .18) continue;
      if (!reed && !Array.from({ length: 8 }, (_, j) => cinderfenSurveyHeightAt(x + Math.cos(j * Math.PI / 4) * 12, z + Math.sin(j * Math.PI / 4) * 12)).some(h => h < survey.waterLevel)) continue;
      const scale = round(.82 + random() * .28), bounds = metadata.assets[key].boundsYUp;
      const radius = Math.hypot(Math.max(...[bounds.minimum[0], bounds.maximum[0]].map(Math.abs)),
        Math.max(...[bounds.minimum[2], bounds.maximum[2]].map(Math.abs))) * scale;
      if (!cinderfenEcologyClear(zone, { x, z }, radius)) continue;
      if (entries.some(p => Math.hypot(p.x - x, p.z - z) < (radius + p.radius) * .78)) continue;
      const ground = Array.from({ length: 8 }, (_, j) => cinderfenSurveyHeightAt(x + Math.cos(j * Math.PI / 4) * radius, z + Math.sin(j * Math.PI / 4) * radius));
      if (Math.max(...ground) - Math.min(...ground) > (reed ? .18 : .09)) continue;
      entries.push({ id: prefix + colony + '_' + i, kind: key, assetKey: key, x, z,
        y: round(Math.min(height, ...ground) - .01), heightMode: 'absolute', rotY: round(random() * Math.PI * 2),
        scale, colliderSpace: 'model', colliders: [], walkableSurfaces: [], cameraSolid: false, radius });
    }
  }
  // Retain gathering visuals and larger ecology until their replacements are accepted.
  const resources = new Set((zone.resourceNodes ?? []).map(p => p.visualPropId));
  zone.props = zone.props.filter(p => resources.has(p.id) || !['pnw_grass_clump', 'pnw_wildflower_clump'].includes(p.kind));
  zone.props.push(...entries.map(({ radius, ...p }) => p));
  zone.props.sort((a, b) => (a.id ?? '').localeCompare(b.id ?? ''));
  zone.orvrLayout.biome.vegetationAssetKeys = [...new Set([...zone.orvrLayout.biome.vegetationAssetKeys, ...ready])];
  zone.orvrLayout.assetPolicy.optionalAssetKeys = [...new Set([...zone.orvrLayout.assetPolicy.optionalAssetKeys, ...ready])];
  return zone;
}
