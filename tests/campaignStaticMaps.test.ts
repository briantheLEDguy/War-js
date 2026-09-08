import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';
import {
  CAMPAIGN_GRAPH_EDGES,
  CAMPAIGN_STATIC_MAP_HASHES,
  CAMPAIGN_ZONES,
} from '../src/data/campaign';
import type { OrvrKeepLayout, OrvrZoneLayout } from '../src/world/orvrTypes';

interface ZoneFile {
  id: string;
  orvrLayout?: OrvrZoneLayout;
  staticMapVersion?: string;
  staticMapHash?: string;
  terrainModel?: string;
  props: Array<{
    id?: string;
    kind?: string;
    x?: number;
    z?: number;
    model?: string;
    assetKey?: string;
    visible?: boolean;
    y?: number;
    rotY?: number;
    scale?: number;
    scaleX?: number;
    scaleZ?: number;
    colliderSpace?: 'legacy' | 'model';
    colliders?: Array<{
      x?: number;
      z?: number;
      width: number;
      depth: number;
      rotY?: number;
      blocksWhen?: string;
      interactionId?: string;
      minY?: number;
      maxY?: number;
    }>;
    walkableSurfaces?: Array<{ fromY?: number; toY?: number }>;
    interaction?: { id?: string; type?: string; label?: string; interiorVariant?: string; maxDistance?: number };
  }>;
  spawnPoint?: { x: number; y: number; z: number };
  paths?: Array<{ id?: string; points?: Array<{ x: number; z: number }> }>;
  npcs?: Array<{ id?: string; x?: number; z?: number }>;
  craftingStations?: Array<{ id?: string; kind?: string; x?: number; z?: number }>;
  enemies?: Array<{
    id?: string;
    name?: string;
    level?: number;
    x?: number;
    z?: number;
    maxHealth?: number;
    aggroRange?: number;
    assetKey?: string;
  }>;
  resourceNodes?: Array<{
    id?: string;
    label?: string;
    kind?: string;
    professionId?: string;
    x?: number;
    z?: number;
    visualPropId?: string;
    loot?: Array<{ key?: string; qty?: number; chance?: number }>;
  }>;
  rvrObjectives?: Array<{ id?: string; type?: string; x?: number; z?: number; captureRadius?: number }>;
  zoneTriggers?: Array<{
    id?: string;
    x: number;
    z: number;
    radius: number;
    targetZoneId: string;
    targetSpawn?: { x: number; y: number; z: number };
  }>;
}

const mapsDir = path.join(process.cwd(), 'public', 'assets', 'maps');
const GUIDE_EDGES = [
  ['riftspire_capital', 'rift_gate_fortress'],
  ['rift_gate_fortress', 'rift_crownworks'],
  ['rift_crownworks', 'shatterline_expanse'],
  ['shatterline_expanse', 'dawnline_expanse'],
  ['dawnline_expanse', 'aegis_crownworks'],
  ['aegis_crownworks', 'aegis_gate_fortress'],
  ['aegis_gate_fortress', 'aegis_capital'],
  ['aegis_capital', 'sunmeadow_march'],
  ['sunmeadow_march', 'greybrook_crossing'],
  ['greybrook_crossing', 'ironwood_redoubt'],
  ['ironwood_redoubt', 'aegis_crownworks'],
  ['sunmeadow_march', 'wardens_hollow'],
  ['greybrook_crossing', 'briarwatch_den'],
  ['ironwood_redoubt', 'stormbarrow_lair'],
  ['aegis_capital', 'brightfen_approach'],
  ['brightfen_approach', 'glassriver_ford'],
  ['glassriver_ford', 'highvale_rampart'],
  ['highvale_rampart', 'aegis_crownworks'],
  ['brightfen_approach', 'mireglass_den'],
  ['glassriver_ford', 'glassriver_depths'],
  ['highvale_rampart', 'highvale_sanctum'],
  ['riftspire_capital', 'cinderfen_outskirts'],
  ['cinderfen_outskirts', 'bleakroot_causeway'],
  ['bleakroot_causeway', 'vilemere_heights'],
  ['vilemere_heights', 'rift_crownworks'],
  ['cinderfen_outskirts', 'cindermaw_pit'],
  ['bleakroot_causeway', 'rotwreath_nest'],
  ['vilemere_heights', 'nightglass_hollow'],
  ['riftspire_capital', 'ashen_steppe'],
  ['ashen_steppe', 'gorepine_pass'],
  ['gorepine_pass', 'obsidian_scar'],
  ['obsidian_scar', 'rift_crownworks'],
  ['ashen_steppe', 'ashfang_pit'],
  ['gorepine_pass', 'gorepine_warrens'],
  ['obsidian_scar', 'obsidian_maw'],
];

function loadZone(zoneId: string): ZoneFile {
  return JSON.parse(readFileSync(path.join(mapsDir, `${zoneId}.json`), 'utf8')) as ZoneFile;
}

function hashZone(zone: ZoneFile): string {
  const normalized = { ...zone };
  delete normalized.staticMapHash;
  return createHash('sha256').update(JSON.stringify(normalized)).digest('hex').slice(0, 16);
}

describe('static campaign map files', () => {
  test('omits draft vegetation placements from published maps', () => {
    for (const node of CAMPAIGN_ZONES) {
      expect(loadZone(node.id).orvrLayout?.biome.placements, node.id).toBeUndefined();
    }
  });

  test('uses the campaign guide as the exact portal graph', () => {
    expect(undirectedEdges(CAMPAIGN_GRAPH_EDGES)).toEqual(undirectedEdges(
      GUIDE_EDGES.map(([fromZoneId, toZoneId]) => ({ fromZoneId, toZoneId })),
    ));

    for (const node of CAMPAIGN_ZONES) {
      const zone = loadZone(node.id);
      const expectedTargets = expectedGuideTargets(node.id);
      const actualTargets = (zone.zoneTriggers ?? [])
        .map((trigger) => trigger.targetZoneId)
        .sort();
      expect(actualTargets).toEqual(expectedTargets);
    }
  });


  test('exist for every generated campaign zone with stable hashes and objective coordinates', () => {
    for (const node of CAMPAIGN_ZONES) {
      const zone = loadZone(node.id);
      expect(zone.id).toBe(node.id);
      expect(zone.staticMapHash).toBe(CAMPAIGN_STATIC_MAP_HASHES[node.id]);
      expect(hashZone(zone)).toBe(zone.staticMapHash);
      expect(zone.rvrObjectives?.length).toBeGreaterThan(0);
      expect(zone.rvrObjectives?.every((objective) =>
        objective.id &&
        Number.isFinite(objective.x) &&
        Number.isFinite(objective.z) &&
        Number.isFinite(objective.captureRadius),
      )).toBe(true);
      expect(zone.props.every((prop) =>
        prop.id &&
        Number.isFinite(prop.rotY) &&
        Number.isFinite(prop.scale) &&
        (prop.scale ?? 0) > 0,
      )).toBe(true);
    }
  });

  test('populates generated campaign zones with activities and gatherable resources', () => {
    for (const node of CAMPAIGN_ZONES) {
      const zone = loadZone(node.id);
      const propIds = new Set(zone.props.map((prop) => prop.id));
      const minimums = populationMinimums(node.nodeRole);

      expect(zone.npcs?.length ?? 0).toBeGreaterThanOrEqual(minimums.npcs);
      expect(zone.enemies?.length ?? 0).toBeGreaterThanOrEqual(minimums.enemies);
      expect(zone.craftingStations?.length ?? 0).toBeGreaterThanOrEqual(minimums.stations);
      expect(zone.resourceNodes?.length ?? 0).toBeGreaterThanOrEqual(minimums.resources);

      expect(zone.resourceNodes?.every((resource) =>
        resource.id &&
        resource.label &&
        resource.kind &&
        resource.professionId &&
        resource.visualPropId &&
        propIds.has(resource.visualPropId) &&
        (resource.loot?.length ?? 0) > 0 &&
        resource.loot?.every((loot) =>
          loot.key &&
          Number.isFinite(loot.qty) &&
          (loot.qty ?? 0) > 0 &&
          Number.isFinite(loot.chance) &&
          (loot.chance ?? 0) > 0,
        ),
      )).toBe(true);
    }
  });

  test('provides passive indexed training dummies in both capital cities', () => {
    for (const capitalId of ['aegis_capital', 'riftspire_capital']) {
      const dummies = loadZone(capitalId).enemies?.filter((enemy) => ['dummy','riftspire_training_dummy'].includes(enemy.assetKey??'')) ?? [];

      expect(dummies).toHaveLength(3);
      expect(dummies.map((dummy) => dummy.name)).toEqual([
        'Training Dummy',
        'Heavy Training Dummy',
        'Dueling Target',
      ]);
      expect(dummies.every((dummy) =>
        dummy.id?.startsWith(`${capitalId}_training_dummy_`) &&
        dummy.aggroRange === 0 &&
        Number.isFinite(dummy.x) &&
        Number.isFinite(dummy.z) &&
        Number.isFinite(dummy.maxHealth),
      )).toBe(true);
    }
  });

  test('gives RvR zones three battlefield objectives and two faction keeps', () => {
    for (const node of CAMPAIGN_ZONES) {
      const zone = loadZone(node.id);
      const battleObjectives = zone.rvrObjectives?.filter((objective) => objective.type === 'battle_objective') ?? [];
      const keeps = zone.rvrObjectives?.filter((objective) => objective.type === 'keep') ?? [];

      if (node.nodeRole === 'battlefield' || node.nodeRole === 'fortress') {
        expect(battleObjectives, node.id).toHaveLength(3);
        expect(keeps, node.id).toHaveLength(2);
        expect(keeps.map((keep) => keep.id).sort()).toEqual([
          `${node.id}_aegis_keep`,
          `${node.id}_riftbound_keep`,
        ]);
      } else if (node.nodeRole === 'boss_lair') {
        expect(keeps, node.id).toHaveLength(0);
        expect(zone.rvrObjectives?.map((objective) => objective.type)).toEqual(['boss']);
      } else if (node.nodeRole === 'capital') {
        expect(keeps, node.id).toHaveLength(0);
        if (node.id === 'aegis_capital') {
          expect(battleObjectives, node.id).toHaveLength(3);
          expect(zone.rvrObjectives?.map((objective) => objective.id)).toEqual([
            'aegis_capital_courtyard', 'aegis_capital_vault', 'aegis_capital_throne_room',
          ]);
        } else {
          expect(zone.rvrObjectives?.some((objective) => objective.type === 'city_gate')).toBe(true);
        }
      }
    }
  });

  test('generates editable keep defenses with animated gates and protected exits', () => {
    for (const node of CAMPAIGN_ZONES) {
      if (node.nodeRole !== 'battlefield' && node.nodeRole !== 'fortress') continue;

      const zone = loadZone(node.id);
      const keeps = zone.rvrObjectives?.filter((objective) => objective.type === 'keep') ?? [];
      expect(keeps, node.id).toHaveLength(2);
      expect(zone.props.some((prop) => prop.kind === 'castle' && prop.id?.includes('_keep'))).toBe(false);

      for (const keep of keeps) {
        const layout = zone.orvrLayout?.keeps.find(entry => entry.objectiveId === keep.id);
        if (layout?.gates.every(gate => ['frontier_sunmeadow_gate_leaves', 'frontier_cinderfen_gate_leaves'].includes(gate.assetKey))) {
          expectAuthoredKeep(zone, layout);
          continue;
        }
        const keepPrefix = `${keep.id}_keep`;
        const keepProps = zone.props.filter((prop) => prop.id?.startsWith(keepPrefix));
        expect(keepProps.filter((prop) => prop.kind === 'wall_segment').length, keep.id).toBeGreaterThanOrEqual(8);
        expect(keepProps.filter((prop) => prop.kind === 'tower').length, keep.id).toBeGreaterThanOrEqual(8);

        const frontGate = zone.props.find((prop) => prop.id === `${keepPrefix}_front_gate`);
        const rearPostern = zone.props.find((prop) => prop.id === `${keepPrefix}_rear_postern`);
        const innerFrontDoor = zone.props.find((prop) => prop.id === `${keepPrefix}_inner_front_door`);
        const innerRearDoor = zone.props.find((prop) => prop.id === `${keepPrefix}_inner_rear_door`);

        expectInteractiveGate(frontGate, 'castle_gate.glb');
        expectInteractiveGate(rearPostern, 'castle_door.glb');
        expectInteractiveGate(innerFrontDoor, 'castle_door.glb');
        expectInteractiveGate(innerRearDoor, 'castle_door.glb');
      }
    }
  });

  test('capital city gates use closed-only interactive colliders', () => {
    for (const node of CAMPAIGN_ZONES.filter((entry) => entry.nodeRole === 'capital' && entry.id!=='riftspire_capital')) {
      const zone = loadZone(node.id);
      const cityGate = zone.props.find((prop) => prop.id === `${node.id}_city_gate_gate`);
      expectInteractiveGate(cityGate, node.id === 'aegis_capital' ? 'prop_aegis_portcullis.glb' : 'castle_gate.glb');
    }
  });

  test('Riftspire replaces the flat fortress with authored crater districts and permanent crossings', () => {
    const zone = loadZone('riftspire_capital');
    expect(zone.size).toBe(1024);
    expect(zone.cityLayoutVersion).toBe('riftspire-crater-v3');
    expect(zone.craterCity.levels.map((level: any)=>level.y)).toEqual([0,-50,-105,-130,-150,-175,-245]);
    expect(zone.props.filter((p: any)=>p.id?.startsWith('riftspire_rim_gate_'))).toHaveLength(4);
    expect(zone.props.filter((p: any)=>p.id?.startsWith('riftspire_transit_arm_')).every((p: any)=>p.walkableSurfaces[0].width===18)).toBe(true);
    expect(zone.props.every((p: any)=>p.model.startsWith('prop_riftspire_') && p.heightMode==='absolute')).toBe(true);
    expect(zone.cityDistricts.map((d: any)=>d.name)).toEqual(['Ashgate Rim','Blackvein Market','Hollowwall Warrens','Chainwake Commons','Drowned Works','Riftspire Crown']);
  });

  test('has bidirectional portal triggers for every campaign edge', () => {
    for (const edge of CAMPAIGN_GRAPH_EDGES) {
      const from = loadZone(edge.fromZoneId);
      const trigger = from.zoneTriggers?.find((entry) => entry.targetZoneId === edge.toZoneId);
      expect(trigger?.id).toBeTruthy();
      expect(trigger?.targetSpawn).toEqual(expect.objectContaining({
        x: expect.any(Number),
        y: expect.any(Number),
        z: expect.any(Number),
      }));
    }
  });

  test('keeps portal trigger volumes unique and target spawns outside trigger volumes', () => {
    for (const node of CAMPAIGN_ZONES) {
      const zone = loadZone(node.id);
      const triggers = zone.zoneTriggers ?? [];

      for (let i = 0; i < triggers.length; i += 1) {
        const a = triggers[i];
        for (let j = i + 1; j < triggers.length; j += 1) {
          const b = triggers[j];
          expect(distance2d(a, b)).toBeGreaterThan(a.radius + b.radius);
        }
      }

      for (const trigger of triggers) {
        expect(trigger.targetSpawn).toBeTruthy();
        const targetZone = loadZone(trigger.targetZoneId);
        for (const targetTrigger of targetZone.zoneTriggers ?? []) {
          expect(distance2d(trigger.targetSpawn!, targetTrigger)).toBeGreaterThan(targetTrigger.radius);
        }
      }
    }
  });

  test('keeps default and portal spawns outside enemy aggro range', () => {
    const spawnSafetyBuffer = 10;

    for (const node of CAMPAIGN_ZONES) {
      const zone = loadZone(node.id);
      expect(zone.spawnPoint, node.id).toEqual(expect.objectContaining({
        x: expect.any(Number),
        y: expect.any(Number),
        z: expect.any(Number),
      }));

      expectSpawnOutsideEnemyAggro(zone.spawnPoint!, zone, spawnSafetyBuffer);

      for (const trigger of zone.zoneTriggers ?? []) {
        expect(trigger.targetSpawn, trigger.id).toBeTruthy();
        const targetZone = loadZone(trigger.targetZoneId);
        expectSpawnOutsideEnemyAggro(trigger.targetSpawn!, targetZone, spawnSafetyBuffer);
      }
    }
  });
});

function expectInteractiveGate(
  prop: ZoneFile['props'][number] | undefined,
  model: string | { assetKey: string },
): void {
  expect(prop).toBeTruthy();
  if (typeof model === 'string') expect(prop?.model).toBe(model);
  else expect(prop?.assetKey).toBe(model.assetKey);
  expect(prop?.interaction).toEqual(expect.objectContaining({
    id: expect.any(String),
    type: 'gate',
    label: expect.any(String),
  }));
  expect(prop?.colliders?.some((collider) =>
    collider.blocksWhen === 'closed' &&
    collider.interactionId === prop?.interaction?.id,
  )).toBe(true);
}

function expectAuthoredKeep(zone: ZoneFile, keep: OrvrKeepLayout): void {
  const cinderfen = zone.id === 'cinderfen_outskirts';
  const prefix = cinderfen ? 'frontier_cinderfen' : 'frontier_sunmeadow';
  expect([...zone.orvrLayout!.assetPolicy.requiredAssetKeys, ...(zone.orvrLayout!.assetPolicy.optionalAssetKeys ?? [])]).toContain(`${prefix}_gate_leaves`);
  const props = zone.props.filter(prop => prop.id?.startsWith(`${keep.objectiveId}_`));
  const curtains = props.filter(prop => prop.assetKey === `${prefix}_${cinderfen ? 'curtain_walk' : 'curtain_wall'}`);
  const gatehouses = props.filter(prop => prop.assetKey === `${prefix}_gatehouse`);
  expect(curtains.length, keep.objectiveId).toBeGreaterThanOrEqual(32);
  expect(gatehouses, keep.objectiveId).toHaveLength(2);
  expect(curtains.every(prop => prop.colliders?.some(box => box.width > 0 && box.depth > 0))).toBe(true);
  expect(gatehouses.every(prop => (prop.colliders?.length ?? 0) >= 2)).toBe(true);
  expect(keep.gates.map(gate => gate.stage).sort()).toEqual(['inner', 'outer']);
  for (const gate of keep.gates) {
    const prop = zone.props.find(prop => prop.id === gate.propId);
    expectInteractiveGate(prop, { assetKey: gate.assetKey });
    expect(prop!.interaction).toMatchObject({ openClip: 'gate_open', closeClip: 'gate_close' });
    expect({ x: prop!.x, z: prop!.z }).toEqual({ x: gate.x, z: gate.z });
    expect(prop!.colliders!.some(box => box.width === gate.width && box.depth === gate.depth)).toBe(true);
  }
  expect(zone.props.find(prop => prop.id === keep.postern?.propId)?.assetKey).toBe(`${prefix}_gate_leaves`);
  expect(distance2d(keep.postern!.inside, keep.postern!.outside)).toBeGreaterThan(4);

  // Actual transformed collision must seal both defensive rings. Opening the
  // outer gate grants courtyard access; the commander still needs the inner gate.
  const closed = keepReachability(props, keep, new Set());
  const outerBreached = keepReachability(props, keep, new Set([keep.gates.find(gate => gate.stage === 'outer')!.propId]));
  const bothBreached = keepReachability(props, keep, new Set(keep.gates.map(gate => gate.propId)));
  expect(closed(keep.commander), `${keep.objectiveId} closed enclosure`).toBe(false);
  expect(outerBreached(keep.commander), `${keep.objectiveId} inner enclosure`).toBe(false);
  for (const slot of keep.siegeSlots.filter(slot => slot.kind === 'catapult')) {
    expect(closed(slot), `${keep.objectiveId} sealed courtyard`).toBe(false);
    expect(outerBreached(slot), `${keep.objectiveId} reachable courtyard`).toBe(true);
  }
  expect(bothBreached(keep.commander), `${keep.objectiveId} reachable commander`).toBe(true);
}

function keepReachability(props: ZoneFile['props'], keep: OrvrKeepLayout, openGates: Set<string>) {
  const minX = Math.floor(keep.x - 45), maxX = Math.ceil(keep.x + 45);
  const minZ = Math.floor(keep.z - 85), maxZ = Math.ceil(keep.z + 65);
  const width = maxX - minX + 1, height = maxZ - minZ + 1;
  const blocked = new Uint8Array(width * height), visited = new Uint8Array(blocked.length);
  const boxes = props.flatMap(prop => (prop.colliders ?? [])
    // Ground flood-fill must pass below overhead lintels and wall walks.
    .filter(box => (box.minY ?? -Infinity) + (prop.y ?? 0) < 1.8 && (box.maxY ?? Infinity) + (prop.y ?? 0) > .01)
    .filter(box => !(box.blocksWhen === 'closed' && openGates.has(prop.id!)))
    .map(box => {
      const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1), sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
      const sign = prop.colliderSpace === 'model' ? -1 : 1, angle = (prop.rotY ?? 0) * sign;
      return { x: prop.x! + (box.x ?? 0) * sx * Math.cos(angle) - (box.z ?? 0) * sz * Math.sin(angle),
        z: prop.z! + (box.x ?? 0) * sx * Math.sin(angle) + (box.z ?? 0) * sz * Math.cos(angle),
        rotY: angle + (box.rotY ?? 0) * sign, width: box.width * sx + 1, depth: box.depth * sz + 1 };
    }));
  const index = (point: { x: number; z: number }) => (Math.round(point.z) - minZ) * width + Math.round(point.x) - minX;
  for (let z = minZ; z <= maxZ; z++) for (let x = minX; x <= maxX; x++) {
    if (boxes.some(box => pointInsideCollider({ x, z }, box))) blocked[index({ x, z })] = 1;
  }
  const start = index(keep.deliveryPoint), queue = [start];
  expect(blocked[start], `${keep.objectiveId} delivery approach`).toBe(0);
  visited[start] = 1;
  for (let head = 0; head < queue.length; head++) {
    const current = queue[head], x = current % width, z = Math.floor(current / width);
    for (const next of [x > 0 ? current - 1 : -1, x < width - 1 ? current + 1 : -1,
      z > 0 ? current - width : -1, z < height - 1 ? current + width : -1]) {
      if (next >= 0 && !visited[next] && !blocked[next]) { visited[next] = 1; queue.push(next); }
    }
  }
  return (point: { x: number; z: number }) => Boolean(visited[index(point)]);
}

function expectedGuideTargets(zoneId: string): string[] {
  return GUIDE_EDGES
    .flatMap(([a, b]) => (a === zoneId ? [b] : b === zoneId ? [a] : []))
    .sort();
}

function undirectedEdges(edges: Array<{ fromZoneId: string; toZoneId: string }>): string[] {
  return Array.from(new Set(
    edges.map((edge) => [edge.fromZoneId, edge.toZoneId].sort().join('<->')),
  )).sort();
}

function distance2d(
  a: { x: number; z: number },
  b: { x: number; z: number },
): number {
  return Math.hypot(a.x - b.x, a.z - b.z);
}

function pointInsideCollider(
  point: { x: number; z: number },
  collider: { x?: number; z?: number; width: number; depth: number; rotY?: number },
): boolean {
  const dx = point.x - (collider.x ?? 0);
  const dz = point.z - (collider.z ?? 0);
  const rotY = collider.rotY ?? 0;
  const cos = Math.cos(rotY);
  const sin = Math.sin(rotY);
  const localX = dx * cos + dz * sin;
  const localZ = -dx * sin + dz * cos;
  return Math.abs(localX) <= collider.width / 2 && Math.abs(localZ) <= collider.depth / 2;
}

function expectSpawnOutsideEnemyAggro(
  spawn: { x: number; z: number },
  zone: ZoneFile,
  buffer: number,
): void {
  for (const enemy of zone.enemies ?? []) {
    if (!Number.isFinite(enemy.x) || !Number.isFinite(enemy.z)) {
      throw new Error(`${zone.id} has enemy ${enemy.id ?? '(unknown)'} without finite coordinates`);
    }
    const aggroRange = enemy.aggroRange ?? 0;
    if (aggroRange <= 0) continue;

    expect(distance2d(spawn, { x: enemy.x!, z: enemy.z! }), `${zone.id}:${enemy.id}`).toBeGreaterThan(
      aggroRange + buffer,
    );
  }
}

function populationMinimums(role: string): {
  npcs: number;
  enemies: number;
  stations: number;
  resources: number;
} {
  switch (role) {
    case 'capital':
      return { npcs: 6, enemies: 3, stations: 5, resources: 8 };
    case 'fortress':
      return { npcs: 5, enemies: 9, stations: 3, resources: 8 };
    case 'boss_lair':
      return { npcs: 3, enemies: 7, stations: 1, resources: 5 };
    case 'battlefield':
    default:
      return { npcs: 5, enemies: 10, stations: 3, resources: 10 };
  }
}
