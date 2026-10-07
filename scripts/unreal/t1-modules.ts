import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { containsSpatialPoint, distanceToSpatialSegment, resolveZoneSpatial, type SpatialPoint } from '../../shared/worldSpatial';

export type VillageRole = 'furnished_home' | 'housing' | 'general_shop' | 'arms_shop' | 'apothecary'
  | 'forge' | 'woodshop' | 'tailor' | 'inn' | 'bakery' | 'granary' | 'warehouse'
  | 'barracks' | 'watchhouse' | 'stables' | 'command_hall';
export type VillageModule = SpatialPoint & {
  id: string; role: VillageRole; rotY: number; assetKey?: string;
  reservation: { width: number; depth: number; height: number };
  entry: SpatialPoint; approach: SpatialPoint[]; interiorRequired: boolean;
  practical?: SpatialPoint & { assetKey: string; rotY: number; y: number; heightAboveFixture: number; lumens: number };
  admission: 'source-review-required'; nativeInteriorAccepted: false;
};
export type VillagePlan = {
  zoneId: string; layout: string; modules: VillageModule[];
  serviceReservations: { id: string; kind: 'npc' | 'crafting'; point: SpatialPoint; radius: number }[];
  arrivalCourt: { point: SpatialPoint; radius: number };
  furnishedHomesTarget: 2; visualApproved: false; traversalAccepted: false;
};

const roles: VillageRole[] = ['furnished_home', 'furnished_home', 'housing', 'housing', 'housing', 'housing',
  'general_shop', 'arms_shop', 'apothecary', 'forge', 'woodshop', 'tailor', 'inn', 'bakery', 'granary', 'warehouse',
  'barracks', 'watchhouse', 'stables', 'command_hall'];
const cultures: Record<string, { layout: string; home?: string; workshop?: string; offset: number; stretch: number }> = {
  sunmeadow_march: { layout: 'Two farm lanes around a market green', home: 'frontier_sunmeadow_farmhouse', workshop: 'frontier_sunmeadow_workshop', offset: 0, stretch: 1 },
  brightfen_approach: { layout: 'Stepped island courts beside a causeway square', offset: .25, stretch: 1.08 },
  cinderfen_outskirts: { layout: 'Timber working courts around a supply compound', home: 'frontier_cinderfen_dwelling', workshop: 'frontier_cinderfen_workshop', offset: .5, stretch: .92 },
  ashen_steppe: { layout: 'Long caravan street between fortified hall yards', offset: .75, stretch: 1.2 },
};
const workshopRoles = new Set<VillageRole>(['forge', 'woodshop', 'tailor', 'warehouse', 'barracks', 'command_hall']);

/** Source yaw rotates source Z towards X, matching native X/Z axis conversion. */
export function moduleLocalPoint(module: Pick<VillageModule, 'x' | 'z' | 'rotY'>, local: SpatialPoint): SpatialPoint {
  const c = Math.cos(module.rotY), s = Math.sin(module.rotY);
  return { x: module.x + local.x * c + local.z * s, z: module.z + local.z * c - local.x * s };
}
function relative(module: VillageModule, p: SpatialPoint): SpatialPoint {
  const c = Math.cos(module.rotY), s = Math.sin(module.rotY), x = p.x - module.x, z = p.z - module.z;
  return { x: x * c - z * s, z: z * c + x * s };
}
/** Slab intersection reserves a capsule around an oriented building envelope. */
export function segmentCrossesModule(a: SpatialPoint, b: SpatialPoint, module: VillageModule, margin = .6): boolean {
  const start = relative(module, a), end = relative(module, b); let low = 0, high = 1;
  for (const [axis, half] of [['x', module.reservation.width / 2 + margin], ['z', module.reservation.depth / 2 + margin]] as const) {
    const delta = end[axis] - start[axis];
    if (Math.abs(delta) < 1e-9) { if (Math.abs(start[axis]) > half) return false; continue; }
    const t1 = (-half - start[axis]) / delta, t2 = (half - start[axis]) / delta;
    low = Math.max(low, Math.min(t1, t2)); high = Math.min(high, Math.max(t1, t2));
    if (low > high) return false;
  }
  return true;
}
function corners(module: VillageModule): SpatialPoint[] {
  return [-1, 1].flatMap(x => [-1, 1].map(z => moduleLocalPoint(module, { x: x * module.reservation.width / 2, z: z * module.reservation.depth / 2 })));
}

/** A bounded local circulation graph connects planned entrances around all reserved shells.
 * Door sockets are design targets until source geometry and native capsule sweeps verify them. */
function connectEntrances(plan: VillagePlan, center: SpatialPoint, zone: ZoneDefinition): void {
  const step = 3, extent = 46, spatial = resolveZoneSpatial(zone);
  const point = (x: number, z: number) => ({ x: center.x + x * step, z: center.z + z * step });
  const clear = (a: SpatialPoint, b: SpatialPoint) => containsSpatialPoint(spatial, b, 1)
    && !plan.modules.some(module => segmentCrossesModule(a, b, module));
  const key = (x: number, z: number) => `${x},${z}`;
  // One flood from the village green provides every entrance's shortest reserved walk.
  const previous = new Map<string, string | null>([['0,0', null]]), queue: Array<[number, number]> = [[0, 0]];
  for (let index = 0;index < queue.length;index++) {
    const [x, z] = queue[index];
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, nz = z + dz, id = key(nx, nz);
      if (Math.abs(nx) > extent || Math.abs(nz) > extent || previous.has(id) || !clear(point(x, z), point(nx, nz))) continue;
      previous.set(id, key(x, z)); queue.push([nx, nz]);
    }
  }
  for (const module of plan.modules) {
    const x = Math.round((module.entry.x - center.x) / step), z = Math.round((module.entry.z - center.z) / step);
    let node: string | undefined, best = Infinity;
    for (let dx = -3;dx <= 3;dx++)for (let dz = -3;dz <= 3;dz++) {
      const id = key(x + dx, z + dz), p = point(x + dx, z + dz), distance = Math.hypot(p.x - module.entry.x, p.z - module.entry.z);
      if (previous.has(id) && distance < best && clear(module.entry, p)) { node = id; best = distance; }
    }
    if (!node) throw new Error(`Unconnected planned village entry: ${module.id}`);
    const path = [module.entry];
    while (node) { const [nx, nz] = node.split(',').map(Number); path.push(point(nx, nz)); node = previous.get(node) ?? undefined; }
    // Keep bends; remove redundant vertices on the straight grid runs.
    module.approach = path.filter((p, i) => i === 0 || i === path.length - 1
      || Math.abs((p.x - path[i - 1].x) * (path[i + 1].z - p.z) - (p.z - path[i - 1].z) * (path[i + 1].x - p.x)) > 1e-6);
  }
}

/** Produces deterministic, separately editable assemblies without granting asset/interior approval. */
export function villagePlan(zone: ZoneDefinition): VillagePlan {
  const culture = cultures[zone.id], center = zone.spawnPoint;
  if (!culture || !center || !zone.spatial) throw new Error('T1 village requires authored spatial ground');
  const portal = zone.zoneTriggers?.find(row => row.targetZoneId.endsWith('_capital'));
  if (!portal) throw new Error('Village has no capital courtyard');
  const plan: VillagePlan = {
zoneId: zone.id, layout: culture.layout, modules: [],
    serviceReservations: [...(zone.npcs ?? []).filter(p => Math.hypot(p.x - center.x, p.z - center.z) < 75).map(p => ({ id: p.id, kind: 'npc' as const, point: { x: p.x, z: p.z }, radius: 3 })),
    ...(zone.craftingStations ?? []).map(p => ({ id: p.id, kind: 'crafting' as const, point: { x: p.x, z: p.z }, radius: 4 }))],
    arrivalCourt: { point: { x: portal.x, z: portal.z }, radius: 29 }, furnishedHomesTarget: 2, visualApproved: false, traversalAccepted: false
};
  const spatial = resolveZoneSpatial(zone), slots: SpatialPoint[] = [];
  const frontage = zone.paths?.find(p => p.id === `${zone.id}_village_road`)?.points[1];
  if (!frontage) throw new Error('Village has no connected military frontage');
  const distance = Math.hypot(frontage.x - center.x, frontage.z - center.z), forward = { x: (frontage.x - center.x) / distance, z: (frontage.z - center.z) / distance };
  const relativeTarget = (advance: number, lateral: number) => ({ x: center.x + forward.x * advance + forward.z * lateral, z: center.z + forward.z * advance - forward.x * lateral });
  for (let row = -3;row <= 3;row++)for (let column = -3;column <= 3;column++) {
    const x = column * 30 * culture.stretch + ((row % 2) ? culture.offset * 15 : 0), z = row * 30 / culture.stretch;
    if (Math.hypot(x, z) < 132) slots.push({ x: center.x + x, z: center.z + z });
  }
  const order = [16, 17, 18, 19, ...Array.from({ length: 16 }, (_, i) => i)];
  for (const index of order) {
    const role = roles[index];
    // Reserve military frontage first, then rear civilian lanes and the working courts.
    const angle = (index * .61803398875 + culture.offset) * Math.PI * 2, radius = index < 6 ? 94 : 67;
    const desired = index >= 16 ? relativeTarget(94, (index - 17.5) * 32) : index < 6 ? relativeTarget(-82, (index - 2.5) * 29)
      : { x: center.x + Math.cos(angle) * radius, z: center.z + Math.sin(angle) * radius };
    const ordered = [...slots].sort((a, b) => Math.hypot(a.x - desired.x, a.z - desired.z) - Math.hypot(b.x - desired.x, b.z - desired.z));
    let placed: VillageModule | undefined;
    for (const slot of ordered) {
      const module: VillageModule = {
...slot, id: `${zone.id}_village_${role}_${index}`, role,
        rotY: Math.atan2(slot.x - center.x, slot.z - center.z), assetKey: workshopRoles.has(role) ? culture.workshop : culture.home,
        reservation: { width: 14, depth: 16, height: 10 }, entry: { x: 0, z: 0 }, approach: [], interiorRequired: role === 'furnished_home',
        admission: 'source-review-required', nativeInteriorAccepted: false
};
      const envelope = Math.hypot(7, 8);
      if (!corners(module).every(p => containsSpatialPoint(spatial, p, 2)) || Math.hypot(slot.x - center.x, slot.z - center.z) < 24) continue;
      if (Math.hypot(slot.x - portal.x, slot.z - portal.z) < plan.arrivalCourt.radius + envelope + 3) continue;
      if (plan.modules.some(p => Math.hypot(slot.x - p.x, slot.z - p.z) < envelope * 2 + 4)) continue;
      if (plan.serviceReservations.some(p => Math.hypot(slot.x - p.point.x, slot.z - p.point.z) < p.radius + envelope + 2)) continue;
      if ((zone.paths ?? []).some(path => path.points.slice(1).some((p, i) => distanceToSpatialSegment(slot, path.points[i], p) < path.width / 2 + envelope + 3))) continue;
      module.entry = moduleLocalPoint(module, { x: 0, z: -10 });
      if (culture.home) {
        const empire = zone.id === 'sunmeadow_march';
        module.practical = {
...moduleLocalPoint(module, { x: 2, z: empire ? -8 : -11 }),
          assetKey: empire ? 'aegis_civic_wall_lantern' : 'riftspire_lantern', rotY: module.rotY + (empire ? Math.PI : 0),
          y: empire ? 2.3 : 0, heightAboveFixture: empire ? .45 : 2.6, lumens: 900
};
      }
      placed = module; break;
    }
    if (!placed) throw new Error(`No clear village assembly reservation: ${zone.id}/${role}/${index}`);
    plan.modules.push(placed);
  }
  plan.modules.sort((a, b) => Number(a.id.split('_').at(-1)) - Number(b.id.split('_').at(-1)));
  connectEntrances(plan, center, zone); validateVillagePlan(plan, zone); return plan;
}

export function validateVillagePlan(plan: VillagePlan, zone: ZoneDefinition): void {
  if (plan.zoneId !== zone.id || plan.modules.length !== 20 || plan.modules.filter(m => m.interiorRequired).length !== 2) throw new Error('Village composition changed');
  const ids = new Set<string>(), spatial = resolveZoneSpatial(zone);
  for (const module of plan.modules) {
    if (ids.has(module.id) || ![module.x, module.z, module.rotY].every(Number.isFinite)) throw new Error('Invalid module identity/transform');
    ids.add(module.id);
    if (!corners(module).every(p => containsSpatialPoint(spatial, p, 2))) throw new Error('Assembly leaves playable ground');
    if (module.approach.length < 2) throw new Error('Assembly has no reserved approach');
    for (let i = 1;i < module.approach.length;i++)if (plan.modules.some(other => segmentCrossesModule(module.approach[i - 1], module.approach[i], other))) throw new Error('Assembly blocks village circulation');
  }
}
