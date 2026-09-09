/** Marsh colonies follow the reviewed water table, with gaps for travel and combat. */
import { readFileSync } from 'node:fs';
import { reviewedSceneryModelBounds } from './aegis-reviewed-scenery.mjs';

const read = relative => JSON.parse(readFileSync(new URL(relative, import.meta.url), 'utf8'));
const survey = read('../../authoring/blender/cinderfen-terrain/terrain-source.json');
const metadata = read('../../authoring/blender/cinderfen-nature/builder-metadata.json');
const registry = read('../../public/assets/models/asset-index.json').staticProps;
export const CINDERFEN_WETLAND_ASSETS = ['frontier_cinderfen_reed_clump', 'frontier_cinderfen_sedge_horsetail'];
export const CINDERFEN_ALDER = 'frontier_cinderfen_marsh_alder';
export const CINDERFEN_BASALT = 'frontier_cinderfen_basalt_outcrop';
export const CINDERFEN_WATER_LEVEL = survey.waterLevel;
const round = n => Math.round(n * 1000) / 1000;
const readyAsset = key => registry[key]?.runtimeReady && metadata.assets[key]?.runtimeReady
  && registry[key].modelSha256 === metadata.assets[key].modelSha256;

function obstacleEnvelopes(props) {
  return props.map(prop => {
    const model = registry[prop.assetKey ?? prop.kind]?.model ?? prop.model;
    const bounds = model ? reviewedSceneryModelBounds(model) : null, scale = prop.scale ?? 1;
    let radius = bounds ? Math.hypot(Math.max(Math.abs(bounds.min.x), Math.abs(bounds.max.x)) * (prop.scaleX ?? 1),
      Math.max(Math.abs(bounds.min.z), Math.abs(bounds.max.z)) * (prop.scaleZ ?? 1)) * scale : 0;
    for (const c of prop.colliders ?? []) radius = Math.max(radius,
      Math.hypot((Math.abs(c.x ?? 0) + c.width / 2) * (prop.scaleX ?? 1), (Math.abs(c.z ?? 0) + c.depth / 2) * (prop.scaleZ ?? 1)) * scale);
    return { x: prop.x, z: prop.z, radius, foliage: prop.id?.includes('_wetland_') };
  }).filter(p => p.radius > 0);
}

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
  // Clear the previous geological pass before woodland placement so regeneration is stable.
  if (readyAsset(CINDERFEN_BASALT)) {
    const resources = new Set((zone.resourceNodes ?? []).map(p => p.visualPropId));
    zone.props = zone.props.filter(p => resources.has(p.id) || !(p.id?.startsWith(`${zone.id}_basalt_`)
      || (p.kind === 'rock' && new RegExp(`^${zone.id}_(ridge|rock)_\\d+$`).test(p.id ?? ''))));
  }
  const ready = CINDERFEN_WETLAND_ASSETS.filter(key => registry[key]?.runtimeReady && metadata.assets[key]?.runtimeReady
    && registry[key].modelSha256 === metadata.assets[key].modelSha256);
  const prefix = `${zone.id}_wetland_`;
  zone.props = zone.props.filter(p => !p.id?.startsWith(prefix));
  if (!ready.length) return composeCinderfenGeology(composeCinderfenWoodland(zone));
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
  return composeCinderfenGeology(composeCinderfenWoodland(zone));
}

/** Broken stands follow the dry fen margins, leaving the deep basins and campaign routes open. */
export function composeCinderfenWoodland(zone) {
  if (zone.id !== 'cinderfen_outskirts' || !zone.orvrLayout) return zone;
  const definition = metadata.assets[CINDERFEN_ALDER], asset = registry[CINDERFEN_ALDER];
  if (!asset?.runtimeReady || !definition?.runtimeReady || asset.modelSha256 !== definition.modelSha256) return zone;
  const prefix = `${zone.id}_alder_`, resources = new Set((zone.resourceNodes ?? []).map(p => p.visualPropId));
  zone.props = zone.props.filter(p => !p.id?.startsWith(prefix) && (p.kind !== 'tree' || resources.has(p.id)));
  const occupied = obstacleEnvelopes(zone.props);
  const { minimum, maximum } = definition.boundsYUp;
  const crownRadius = Math.hypot(Math.max(Math.abs(minimum[0]), Math.abs(maximum[0])), Math.max(Math.abs(minimum[2]), Math.abs(maximum[2])));
  let seed = 2936417;
  const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  const stands = [
    ['west_inlet', -368, 242, 48, 115, 70], ['west_islet', -180, 285, 25, 24, 10],
    ['west_south', -284, 65, 74, 30, 42], ['north_margin', -100, 380, 80, 35, 55],
    ['east_headland', 350, 238, 52, 125, 85], ['east_south', 216, 50, 87, 30, 45],
    ['east_slope', 335, 370, 55, 55, 50], ['mineral_west', -147, -390, 44, 68, 55],
    ['mineral_east', 286, -372, 40, 87, 65], ['south_toes', 140, -444, 118, 31, 45],
    ['village_margin', 388, -350, 51, 92, 55], ['west_approach', -366, -180, 50, 70, 55],
  ];
  const trees = [];
  for (const [stand, cx, cz, rx, rz, limit] of stands) {
    let count = 0;
    for (let i = 0; i < 4500 && count < limit; i++) {
      const angle = random() * Math.PI * 2, reach = Math.sqrt(random());
      if (random() > 1 - reach * .75) continue;
      const x = round(cx + Math.cos(angle) * rx * reach), z = round(cz + Math.sin(angle) * rz * reach);
      const ground = cinderfenSurveyHeightAt(x, z), scale = round(.72 + random() * .42);
      if (ground < -.14 || ground > 9) continue;
      const rootRadius = 1.25 * scale, radius = crownRadius * scale;
      const around = Array.from({ length: 8 }, (_, j) => cinderfenSurveyHeightAt(x + Math.cos(j * Math.PI / 4) * rootRadius, z + Math.sin(j * Math.PI / 4) * rootRadius));
      if (Math.max(...around) - Math.min(...around) > .28 || Math.min(...around) < -.2) continue;
      if (!cinderfenEcologyClear(zone, { x, z }, radius)) continue;
      if (occupied.some(p => Math.hypot(p.x - x, p.z - z) < p.radius + (p.foliage ? rootRadius : radius) + .3)) continue;
      if (trees.some(p => Math.hypot(p.x - x, p.z - z) < 3.7 * (p.scale + scale) / 2)) continue;
      trees.push({ id: prefix + stand + '_' + i, kind: CINDERFEN_ALDER, assetKey: CINDERFEN_ALDER,
        x, z, y: round(Math.min(ground, ...around) - .02), heightMode: 'absolute', scale, rotY: round(random() * Math.PI * 2),
        colliderSpace: 'model', colliders: structuredClone(definition.colliders), walkableSurfaces: [], cameraSolid: true });
      count++;
    }
  }
  zone.props.push(...trees);
  zone.props.sort((a, b) => (a.id ?? '').localeCompare(b.id ?? ''));
  zone.orvrLayout.biome.vegetationAssetKeys = [...new Set([...zone.orvrLayout.biome.vegetationAssetKeys, CINDERFEN_ALDER])];
  zone.orvrLayout.assetPolicy.optionalAssetKeys = [...new Set([...zone.orvrLayout.assetPolicy.optionalAssetKeys, CINDERFEN_ALDER])];
  return zone;
}

/** Discontinuous exposures follow the basalt shoulders and headlands, with buried toes. */
export function composeCinderfenGeology(zone) {
  if (zone.id !== 'cinderfen_outskirts' || !zone.orvrLayout || !readyAsset(CINDERFEN_BASALT)) return zone;
  const prefix = `${zone.id}_basalt_`, definition = metadata.assets[CINDERFEN_BASALT];
  zone.props = zone.props.filter(p => !p.id?.startsWith(prefix));
  const occupied = obstacleEnvelopes(zone.props), rocks = [];
  const { minimum, maximum } = definition.boundsYUp;
  const baseRadius = Math.hypot(Math.max(Math.abs(minimum[0]), Math.abs(maximum[0])), Math.max(Math.abs(minimum[2]), Math.abs(maximum[2])));
  const seams = [
    ['north_watershed', [[-400,435],[-300,442],[-200,437],[-65,448],[60,475]], 26],
    ['west_shoulder', [[-490,-450],[-500,-320],[-494,-190],[-520,-95]], 24],
    ['steam_ridge', [[478,86],[473,210],[486,347],[479,447]], 24],
    ['southern_slag', [[-60,-465],[90,-452],[210,-470],[350,-510]], 26],
    ['east_headland', [[265,210],[285,238],[309,234]], 8],
    ['cinder_spit', [[-4,-390],[33,-382],[65,-408]], 8],
    ['west_headland', [[-330,245],[-299,270],[-270,280]], 6],
    ['scout_bank', [[180,392],[240,416],[300,410]], 10],
  ];
  let seed = 581962;
  const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296);
  for (const [name, points, limit] of seams) {
    let count = 0;
    for (let i = 0; i < 1400 && count < limit; i++) {
      const segment = Math.floor(random() * (points.length - 1)), a = points[segment], b = points[segment + 1], t = random();
      const x = round(a[0] + (b[0] - a[0]) * t + (random() - .5) * 26), z = round(a[1] + (b[1] - a[1]) * t + (random() - .5) * 26);
      const scale = round(.65 + random() * .95), radius = baseRadius * scale, ground = cinderfenSurveyHeightAt(x, z);
      if (ground < -.12 || ground > 24 || !cinderfenEcologyClear(zone, { x, z }, radius)) continue;
      if (occupied.some(p => Math.hypot(p.x - x, p.z - z) < p.radius + radius + .4)) continue;
      if (rocks.some(p => Math.hypot(p.x - x, p.z - z) < baseRadius * (p.scale + scale) + 1.5)) continue;
      const around = Array.from({ length: 12 }, (_, j) => cinderfenSurveyHeightAt(x + Math.cos(j * Math.PI / 6) * radius, z + Math.sin(j * Math.PI / 6) * radius));
      if (Math.max(ground, ...around) - Math.min(ground, ...around) > .45 * scale) continue;
      rocks.push({ id: prefix + name + '_' + i, kind: CINDERFEN_BASALT, assetKey: CINDERFEN_BASALT,
        x, z, y: round(Math.min(ground, ...around) - .06 * scale), heightMode: 'absolute', scale, rotY: round(random() * Math.PI * 2),
        colliderSpace: 'model', colliders: structuredClone(definition.colliders), walkableSurfaces: [], cameraSolid: true });
      count++;
    }
  }
  zone.props.push(...rocks);
  zone.props.sort((a, b) => (a.id ?? '').localeCompare(b.id ?? ''));
  zone.orvrLayout.assetPolicy.optionalAssetKeys = [...new Set([...zone.orvrLayout.assetPolicy.optionalAssetKeys, CINDERFEN_BASALT])];
  return zone;
}
