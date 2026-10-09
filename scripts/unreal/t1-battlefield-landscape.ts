import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { validateTerrainField, type TerrainField, type FieldPoint } from '../../shared/terrainField';
import { spatialSegmentInside } from '../../shared/worldSpatial';
import { validateT1 } from './t1-layouts';

export const BATTLEFIELD_ZONES = ['sunmeadow_march', 'cinderfen_outskirts'] as const;
const points = (rows: number[][]): FieldPoint[] => rows.map(([x, z, width, height]) => ({ x, z, width, height }));
export function battlefieldField(id: string): TerrainField {
  if (id === 'sunmeadow_march') return {
    version: 1, baseHeight: 7, seed: 14713,
    weathering: { warpMetres: 19, warpScale: 93, detailScale: 43, detailAmplitude: 5.5, terraceHeight: 7, terraceStrength: 0 },
    rolls: [{ scale: 175, amplitude: 4 }, { scale: 71, amplitude: 1.4 }, { scale: 27, amplitude: .35 }],
    ridges: [
      { id: 'barrow_limestone_scarp', profile: 'escarpment', points: points([[-225, 65, 27, 29], [-145, 75, 33, 34], [-75, 100, 30, 33]]) },
      { id: 'north_watershed', profile: 'rounded', points: points([[-850, 490, 180, 68], [-520, 510, 210, 101], [-225, 440, 180, 82], [120, 540, 220, 115], [520, 435, 190, 79], [850, 520, 220, 123]]) },
      { id: 'barrow_finger', profile: 'rounded', points: points([[-260, 425, 110, 70], [-220, 280, 100, 49], [-180, 150, 84, 30], [-175, 40, 70, 17]]) },
      { id: 'oak_saddle', profile: 'rounded', points: points([[70, 450, 120, 82], [95, 270, 98, 57], [20, 105, 84, 31], [0, 0, 100, 19]]) },
      { id: 'eastern_shoulder', profile: 'rounded', points: points([[510, 420, 140, 65], [405, 255, 110, 43], [260, 150, 90, 26]]) },
      { id: 'south_watershed', profile: 'rounded', points: points([[-850, -650, 190, 86], [-360, -580, 210, 96], [-50, -530, 180, 72], [330, -580, 205, 118], [850, -450, 185, 85]]) },
      { id: 'field_rise', profile: 'rounded', points: points([[-50, -450, 110, 42], [-10, -295, 105, 29], [60, -155, 80, 17]]) },
      { id: 'east_farmland_fold', profile: 'rounded', points: points([[445, -470, 115, 58], [370, -280, 95, 29], [245, -145, 75, 14]]) },
    ],
    channels: [
      { id: 'meadow_swale', points: points([[-390, -150, 26, 3.4], [-280, -125, 33, 3.8], [-175, -150, 35, 2.6], [-80, -175, 42, 1.2]]) },
      { id: 'barrow_drain', points: points([[-395, 450, 58, 12], [-365, 270, 50, 9], [-305, 55, 62, 6], [-215, -85, 80, 3]]) },
      { id: 'east_drain', points: points([[300, 420, 58, 13], [300, 235, 55, 9], [205, 75, 55, 6], [230, -70, 65, 4]]) },
    ],
  };
  if (id === 'cinderfen_outskirts') return {
    version: 1, baseHeight: 13, seed: 27431,
    weathering: { warpMetres: 26, warpScale: 79, detailScale: 34, detailAmplitude: 8, terraceHeight: 6, terraceStrength: .68 },
    rolls: [{ scale: 150, amplitude: 3 }, { scale: 61, amplitude: 1.8 }, { scale: 23, amplitude: .7 }],
    ridges: [
      { id: 'western_fault_scarp', profile: 'escarpment', points: points([[-225, -35, 26, 28], [-145, -25, 32, 34], [-70, 0, 30, 33]]) },
      { id: 'west_broken_shelf', profile: 'shelf', points: points([[-650, 420, 135, 68], [-470, 375, 110, 98], [-330, 315, 90, 73], [-225, 195, 85, 51], [-205, 25, 70, 28], [-180, -95, 62, 16]]) },
      { id: 'inner_shelf', profile: 'shelf', points: points([[55, 580, 145, 91], [5, 430, 120, 80], [60, 300, 95, 57], [30, 160, 86, 44], [45, 30, 75, 28], [10, -100, 88, 17]]) },
      { id: 'east_basalt_mass', profile: 'shelf', points: points([[650, 540, 140, 106], [415, 395, 120, 88], [345, 235, 100, 57], [250, 70, 85, 33]]) },
      { id: 'south_fractures', profile: 'rounded', points: points([[-620, -650, 135, 79], [-350, -560, 125, 104], [-165, -610, 110, 71], [70, -535, 130, 84], [380, -600, 150, 103], [650, -490, 140, 67]]) },
      { id: 'peat_dyke', profile: 'rounded', points: points([[-75, -490, 95, 29], [-60, -355, 75, 19], [-10, -235, 70, 12]]) },
    ],
    channels: [
      { id: 'basin_runoff', points: points([[-370, -255, 29, 4.5], [-245, -235, 36, 4], [-145, -265, 45, 2.7], [-40, -320, 52, 1.5]]) },
      { id: 'west_vent_cut', points: points([[-365, 445, 52, 19], [-345, 245, 48, 16], [-305, 45, 50, 10], [-260, -140, 65, 5]]) },
      { id: 'east_vent_cut', points: points([[185, 480, 47, 22], [185, 290, 50, 16], [135, 155, 48, 11], [150, -30, 65, 6]]) },
      { id: 'southern_peat_cut', points: points([[-230, -565, 60, 15], [-220, -390, 57, 10], [-155, -235, 66, 5]]) },
    ],
  };
  throw new Error('Battlefield landscape work is restricted to the first pair');
}

export interface OffRoadLink { id: string; purpose: string; points: Array<{ x: number; z: number }>; width: number }
function gradedLink(link: OffRoadLink, roads: NonNullable<ZoneDefinition['paths']>, height: (x: number, z: number) => number) {
  const vertices: Array<{ x: number; z: number; y?: number }> = [];
  for (let i = 1; i < link.points.length; i++) {
    const a = link.points[i - 1], b = link.points[i], dx = b.x - a.x, dz = b.z - a.z;
    if (!vertices.length) vertices.push({ ...a, y: height(a.x, a.z) });
    const crossings: Array<{ t: number; x: number; z: number; y: number }> = [];
    for (const path of roads) for (let j = 1; j < path.points.length; j++) {
      const c = path.points[j - 1], d = path.points[j], rx = d.x - c.x, rz = d.z - c.z, denominator = dx * rz - dz * rx;
      if (Math.abs(denominator) < 1e-8) continue;
      const t = ((c.x - a.x) * rz - (c.z - a.z) * rx) / denominator;
      const u = ((c.x - a.x) * dz - (c.z - a.z) * dx) / denominator;
      if (t > .0001 && t < .9999 && u >= 0 && u <= 1) {
        const x = a.x + dx * t, z = a.z + dz * t;
        crossings.push({ t, x, z, y: height(x, z) });
      }
    }
    for (const p of crossings.sort((a, b) => a.t - b.t)) if (Math.hypot(p.x - vertices.at(-1)!.x, p.z - vertices.at(-1)!.z) > .1) vertices.push({ x: p.x, z: p.z, y: p.y });
    vertices.push({ ...b, ...(i === link.points.length - 1 ? { y: height(b.x, b.z) } : {}) });
  }
  const distances = [0];
  for (let i = 1; i < vertices.length; i++) distances.push(distances[i - 1] + Math.hypot(vertices[i].x - vertices[i - 1].x, vertices[i].z - vertices[i - 1].z));
  for (let i = 1; i < vertices.length - 1; i++) if (vertices[i].y === undefined) {
    let a = i - 1, b = i + 1;
    while (vertices[a].y === undefined) a--;
    while (vertices[b].y === undefined) b++;
    vertices[i].y = vertices[a].y! + (vertices[b].y! - vertices[a].y!) * (distances[i] - distances[a]) / (distances[b] - distances[a]);
  }
  return vertices as Array<{ x: number; z: number; y: number }>;
}
export function offRoadLinks(id: string): OffRoadLink[] {
  const rows = id === 'sunmeadow_march' ? [
    ['west_field_counter', 'Screened climb around the western barrow finger', [[-280, -70], [-340, 20], [-310, 130]]],
    ['central_field_cut', 'Open field crossing between lower flank and advance', [[-180, -197], [-155, -130], [-120, -45]]],
    ['east_shoulder_counter', 'Reverse climb onto the eastern shoulder', [[230, -152], [210, -75], [250, 95], [290, 150]]],
  ] : id === 'cinderfen_outskirts' ? [
    ['west_shelf_counter', 'Gully-side bypass onto the basalt flank', [[-280, -190], [-335, -110], [-300, 20]]],
    ['peat_counter', 'Gentle dyke crossing into the first battle space', [[-185, -317], [-170, -245], [-120, -170]]],
    ['east_shelf_counter', 'Back-slope approach to the eastern shelf', [[285, -280], [250, -200], [230, -115], [265, 50], [300, 120]]],
  ] : undefined;
  if (!rows) throw new Error('Off-road links require an admitted first-pair zone');
  return rows.map(([id, purpose, p]) => ({ id: id as string, purpose: purpose as string, points: (p as number[][]).map(([x, z]) => ({ x, z })), width: 12 }));
}

/** Unpainted walking climbs shape the backs of the exposed scarps; existing vehicle links stay separate. */
export function scarpClimbs(id: string): OffRoadLink[] {
  const rows: Array<[string, number[][]]> | undefined = id === 'sunmeadow_march' ? [
    ['west', [[-275, 137], [-240, 120], [-200, 105], [-145, 75]]],
    ['east', [[-100, 172], [-110, 135], [-120, 100], [-145, 75]]],
  ] : id === 'cinderfen_outskirts' ? [
    ['west', [[-240, 30], [-225, 15], [-190, -5], [-145, -25]]],
    ['east', [[-105, 52.5], [-110, 25], [-120, 0], [-145, -25]]],
  ] : undefined;
  if (!rows) throw new Error('Scarp climbs require a first-pair region');
  return rows.map(([side, points]) => ({ id: id + '_scarp_' + side + '_climb', purpose: 'Unpainted back climb',
    width: 12, points: points.map(([x, z]) => ({ x, z })) }));
}

/** Fresh source candidate, retaining XY identities and moving complete keeps vertically together. */
export function battlefieldLandscape(source: ZoneDefinition, homeApproaches: Array<{ id: string; points: Array<{ x: number; z: number; y: number }> }> = []): ZoneDefinition {
  const field = battlefieldField(source.id); validateTerrainField(field);
  if (!source.spatial || !source.orvrLayout || !source.paths) throw new Error('Battlefield pass requires the retained T1 plan');
  const zone = structuredClone(source), layout = zone.orvrLayout!, terrain = layout.terrain;
  const bounds = zone.spatial!.bounds;
  zone.segments = Math.ceil(zone.size / 4);
  zone.spatial!.terrainGrid = { segmentsX: Math.ceil((bounds.maxX - bounds.minX) / 4), segmentsZ: Math.ceil((bounds.maxZ - bounds.minZ) / 4) };
  layout.spatial = zone.spatial;
  const oldHeight = createOrvrGridHeightSampler(source.orvrLayout.terrain, source.size, source.segments, source.spatial);
  const targets = source.id === 'sunmeadow_march'
    ? [[12, 15, 15, 21, 27, 24, 18, 16, 12], [12, 15, 29, 36, 36, 32, 16, 12], [12, 11, 14, 17, 13, 12]]
    : [[18, 21, 21, 27, 32, 29, 24, 15, 20], [18, 21, 34, 40, 40, 38, 15, 20], [18, 17, 23, 25, 21, 20]];
  const key = (p: { x: number; z: number }) => `${p.x},${p.z}`;
  const heights = new Map<string, number>();
  zone.paths!.slice(0, 3).forEach((path, i) => {
    if (path.points.length !== targets[i].length) throw new Error('Retained vehicle route vertices changed');
    path.points.forEach((p, j) => heights.set(key(p), targets[i][j]));
  });
  const moveAssembly = (value: unknown, delta: number): void => {
    if (Array.isArray(value)) { value.forEach(v => moveAssembly(v, delta)); return; }
    if (!value || typeof value !== 'object') return;
    const row = value as Record<string, unknown>;
    if (typeof row.x === 'number' && typeof row.z === 'number' && typeof row.y === 'number') row.y += delta;
    Object.values(row).forEach(v => { if (v && typeof v === 'object') moveAssembly(v, delta); });
  };
  for (const [i, keep] of layout.keeps.entries()) {
    const target = targets[0][i === 0 ? 0 : 8], delta = target - (keep.y ?? 0);
    moveAssembly(keep, delta);
    for (const p of zone.paths!.find(p => p.id === `${keep.objectiveId}_approach`)!.points) heights.set(key(p), target);
    terrain.flattenAreas.find(a => a.id === keep.objectiveId)!.height = target;
  }
  for (const [i, camp] of layout.stagingCamps.entries()) {
    const y = targets[0][i === 0 ? 0 : 8]; camp.y = y;
    heights.set(key(camp), y);
    for (const p of zone.paths!.find(p => p.id === `${camp.id}_road`)!.points) heights.set(key(p), y);
    terrain.flattenAreas.find(a => a.id === camp.id)!.height = y;
  }
  for (const [i, bo] of layout.battlefieldObjectives.entries()) {
    bo.y = targets[0][[2, 4, 6][i]];
    terrain.flattenAreas.find(a => a.id === ['west_objective', 'central_objective', 'east_objective'][i])!.height = bo.y;
  }
  for (const p of zone.paths!.flatMap(p => p.points)) if (heights.has(key(p))) p.y = heights.get(key(p));
  for (const route of layout.caravanRoutes) for (const p of route.points) if (heights.has(key(p))) p.y = heights.get(key(p));
  terrain.naturalField = field; terrain.landforms = []; terrain.sourceVersion = 't1-battlefield-landscape-v11';
  for (const area of terrain.flattenAreas) if (area.id === 'village' || area.id.includes('_village_')) {
    area.preserveFooting = true;
    area.feather = area.id === 'village' ? 120 : Math.max(area.feather, 72);
  }
  for (const area of terrain.flattenAreas) if (!area.preserveFooting) area.feather = Math.max(area.feather, area.id.includes('objective') ? 60 : 50);
  layout.version = terrain.sourceVersion;
  terrain.clearCorridors = zone.paths!.map(p => ({ id: p.id, points: p.points.map(p => ({ ...p })), radius: p.width / 2 + 7, height: 0, feather: 72 }));
  for (const home of homeApproaches) {
    if (!home.id.startsWith(zone.id + '_village_furnished_home_') || home.points.length < 2 || home.points.length > 40
      || home.points.some((p, i) => !Number.isFinite(p.y) || i && !spatialSegmentInside(zone.spatial!, home.points[i - 1], p, 7))) throw new Error('Invalid retained home footing');
    terrain.clearCorridors.push({ id: home.id + '_ground_entry', points: home.points, radius: 7, height: 0, feather: 16 });
  }
  // Optional cross-country links receive gentle ground grading without painted roads.
  for (const link of offRoadLinks(zone.id)) {
    if (link.points.some((p, i) => i && !spatialSegmentInside(zone.spatial!, link.points[i - 1], p, 9))) throw new Error('Unsupported off-road link');
    const h = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
    terrain.clearCorridors.push({ id: link.id, points: gradedLink(link, zone.paths!, h), radius: link.width / 2 + 7, height: 0, feather: 40 });
  }
  const climbs = scarpClimbs(zone.id), crest=climbs[0].points.at(-1)!;
  terrain.flattenAreas.push({ id: zone.id + '_scarp_overlook', ...crest, radius: 10, feather: 24, height: 44 });
  for (const climb of climbs) {
    if (climb.points.some((p,i) => i && !spatialSegmentInside(zone.spatial!,climb.points[i-1],p,9))) throw new Error('Unsupported scarp climb');
    const h = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
    terrain.clearCorridors.push({ id: climb.id, points: gradedLink(climb, zone.paths!, h), radius: 12, height: 0, feather: zone.id === 'cinderfen_outskirts' ? 20 : 40 });
  }
  const height = createOrvrGridHeightSampler(terrain, zone.size, zone.segments, zone.spatial);
  for (const prop of zone.props ?? []) if (prop.heightMode === 'absolute') prop.y = (prop.y ?? 0) + height(prop.x, prop.z) - oldHeight(prop.x, prop.z);
  zone.spawnPoint!.y = height(zone.spawnPoint!.x, zone.spawnPoint!.z);
  for (const trigger of zone.zoneTriggers ?? []) {
    trigger.y = height(trigger.x, trigger.z); trigger.arrivalPoint!.y = height(trigger.arrivalPoint!.x, trigger.arrivalPoint!.z);
  }
  validateT1(zone);
  return zone;
}
