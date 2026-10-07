import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment, type SpatialPoint } from '../../shared/worldSpatial';
import { villagePlan } from './t1-modules';

type Part = { assetKey: string; dx: number; dz: number; scale?: number; bounds: [number, number, number] };
type Recipe = { id: string; story: string; anchor: SpatialPoint; parts: Part[] };
export type ScenePlacement = SpatialPoint & {
  id: string; assetKey: string; rotY: number; scale: number;
  reservation: { width: number; depth: number; height: number };
};
export type SceneModule = {
  id: string; story: string; placements: ScenePlacement[]; pending: { id: string; reason: string }[];
  visualApproved: false; combatCoverAccepted: false;
};

const part = (assetKey: string, dx: number, dz: number, bounds: Part['bounds'], scale = 1): Part => ({ assetKey, dx, dz, bounds, scale });
function recipes(zoneId: string): Recipe[] {
  if (zoneId === 'sunmeadow_march') return [
    {
id: 'requisitioned_harvest', story: 'Harvest plots give way to collected army stores', anchor: { x: -455, z: -365 }, parts: [
        ...Array.from({ length: 36 }, (_, i) => part('frontier_sunmeadow_wheat', (i % 6 - 2.5) * 6, (Math.floor(i / 6) - 2.5) * 6, [3, 3, 2])),
        part('frontier_field_supply_chest', 24, 0, [2, 2, 2]), part('frontier_field_supply_chest', 24, 3, [2, 2, 2]),
        part('frontier_sunmeadow_hawthorn', -25, 0, [6, 2, 3]), part('frontier_sunmeadow_hawthorn', -25, 12, [6, 2, 3])]
},
    {
id: 'advance_hedgerow', story: 'The working valley opens between broken hedgerows', anchor: { x: -230, z: 25 }, parts: [
        ...Array.from({ length: 8 }, (_, i) => part('frontier_sunmeadow_oak_hedgerow', (i - 3.5) * 17, i % 2 * 12, [8, 7, 14])),
        ...Array.from({ length: 9 }, (_, i) => part('frontier_sunmeadow_hawthorn', (i - 4) * 14, -12, [6, 2, 3]))]
},
    {
id: 'barrow_ridge', story: 'Old limestone and oak frame the quieter barrow track', anchor: { x: -195, z: 295 }, parts: [
        ...Array.from({ length: 8 }, (_, i) => part('frontier_sunmeadow_oak_hedgerow', (i % 4 - 1.5) * 25, (Math.floor(i / 4) - .5) * 24, [8, 7, 14])),
        ...Array.from({ length: 5 }, (_, i) => part('frontier_sunmeadow_limestone', (i - 2) * 17, -24, [7, 5, 3]))]
},
  ];
  if (zoneId === 'cinderfen_outskirts') return [
    {
id: 'basalt_shelf', story: 'Basalt shoulders shelter the basin route without sealing its counterapproaches', anchor: { x: -230, z: -110 }, parts: [
        ...Array.from({ length: 9 }, (_, i) => part('frontier_cinderfen_basalt_outcrop', (i % 3 - 1) * 17, (Math.floor(i / 3) - 1) * 18, [6, 5, 3], i % 3 === 0 ? 2 : 1)),
        ...Array.from({ length: 5 }, (_, i) => part('frontier_cinderfen_marsh_alder', (i - 2) * 19, 30, [7, 7, 11]))]
},
    {
id: 'peat_dyke', story: 'Reed and sedge islands border the cut peat flank', anchor: { x: 170, z: -360 }, parts: [
        ...Array.from({ length: 16 }, (_, i) => part('frontier_cinderfen_reed_clump', (i % 8 - 3.5) * 10, (Math.floor(i / 8) - .5) * 12, [5, 4, 4])),
        ...Array.from({ length: 20 }, (_, i) => part('frontier_cinderfen_sedge_horsetail', (i % 10 - 4.5) * 8, (Math.floor(i / 10) - .5) * 8 + 20, [3, 3, 2]))]
},
    {
id: 'mineral_rise', story: 'Clustered mineral rock announces the optional lair approach', anchor: { x: -435, z: 230 }, parts: [
        part('frontier_cinderfen_basalt_outcrop', 0, 0, [6, 5, 3], 3), part('frontier_cinderfen_basalt_outcrop', 18, -5, [6, 5, 3], 2),
        part('frontier_cinderfen_basalt_outcrop', -15, 10, [6, 5, 3], 2),
        ...Array.from({ length: 7 }, (_, i) => part('frontier_cinderfen_sedge_horsetail', (i - 3) * 10, -26, [3, 3, 2]))]
},
  ];
  return [];
}

/** Small source-derived assemblies are individually editable, and can later become instance batches.
 * Bounds are conservative measured reservations; the strict importer verifies the actual source mesh. */
export function regionalSceneModules(zone: ZoneDefinition): SceneModule[] {
  if (!zone.spatial || !zone.orvrLayout) throw new Error('Regional scene modules require T1 ground');
  const village = villagePlan(zone), occupied: ScenePlacement[] = [];
  const modules: SceneModule[] = [];
  const radius = (p: ScenePlacement) => Math.hypot(p.reservation.width, p.reservation.depth) / 2;
  const clear = (p: ScenePlacement) => containsSpatialPoint(zone.spatial!, p, radius(p) + 2)
    && !(zone.paths ?? []).some(path => path.points.slice(1).some((end, i) => distanceToSpatialSegment(p, path.points[i], end) < radius(p) + path.width / 2 + 3))
    && !zone.orvrLayout!.keeps.some(k => Math.hypot(p.x - k.x, p.z - k.z) < 62 + radius(p))
    && !zone.orvrLayout!.battlefieldObjectives.some(k => Math.hypot(p.x - k.x, p.z - k.z) < 28 + radius(p))
    && !zone.orvrLayout!.stagingCamps.some(k => Math.hypot(p.x - k.x, p.z - k.z) < 38 + radius(p))
    && !village.modules.some(m => Math.hypot(p.x - m.x, p.z - m.z) < radius(p) + Math.hypot(m.reservation.width, m.reservation.depth) / 2 + 3)
    && Math.hypot(p.x - village.arrivalCourt.point.x, p.z - village.arrivalCourt.point.z) > village.arrivalCourt.radius + radius(p) + 3
    && !occupied.some(m => Math.hypot(p.x - m.x, p.z - m.z) < radius(p) + radius(m) + 1);
  for (const recipe of recipes(zone.id)) {
    const scene: SceneModule = { id: zone.id + '_' + recipe.id, story: recipe.story, placements: [], pending: [], visualApproved: false, combatCoverAccepted: false };
    for (const [index, component] of recipe.parts.entries()) {
      const scale = component.scale ?? 1, original = { x: recipe.anchor.x + component.dx, z: recipe.anchor.z + component.dz };
      const placement: ScenePlacement = {
...original, id: `${scene.id}_${index}`, assetKey: component.assetKey,
        rotY: index * 2.3999632297, scale, reservation: { width: component.bounds[0] * scale, depth: component.bounds[1] * scale, height: component.bounds[2] * scale }
};
      let placed = clear(placement);
      for (let offset = 8;offset <= 64 && !placed;offset += 8)for (let angle = 0;angle < 16 && !placed;angle++) {
        placement.x = original.x + Math.cos(angle * Math.PI / 8) * offset; placement.z = original.z + Math.sin(angle * Math.PI / 8) * offset; placed = clear(placement);
      }
      if (!placed) { scene.pending.push({ id: placement.id, reason: 'no-clear-scene-reservation' }); continue; }
      scene.placements.push(placement); occupied.push(placement);
    }
    modules.push(scene);
  }
  return modules;
}
