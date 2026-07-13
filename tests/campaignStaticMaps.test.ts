import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, test } from 'vitest';
import {
  CAMPAIGN_GRAPH_EDGES,
  CAMPAIGN_STATIC_MAP_HASHES,
  CAMPAIGN_ZONES,
} from '../src/data/campaign';

interface ZoneFile {
  id: string;
  staticMapVersion?: string;
  staticMapHash?: string;
  terrainModel?: string;
  props: Array<{
    id?: string;
    kind?: string;
    x?: number;
    z?: number;
    model?: string;
    visible?: boolean;
    y?: number;
    rotY?: number;
    scale?: number;
    scaleX?: number;
    scaleZ?: number;
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
    interaction?: { id?: string; type?: string; label?: string };
  }>;
  spawnPoint?: { x: number; y: number; z: number };
  paths?: Array<{ id?: string; points?: Array<{ x: number; z: number }> }>;
  npcs?: Array<{ id?: string; x?: number; z?: number }>;
  craftingStations?: Array<{ id?: string; kind?: string; x?: number; z?: number }>;
  enemies?: Array<{ id?: string; x?: number; z?: number; aggroRange?: number }>;
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
const IMPORTED_AEGIS_CAPITAL_ID = 'aegis_capital';

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

  test('does not ship obsolete Reikland map data', () => {
    expect(existsSync(path.join(mapsDir, 'reikland.json'))).toBe(false);
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
        expect(zone.rvrObjectives?.some((objective) => objective.type === 'city_gate')).toBe(true);
      }
    }
  });

  test('generates keeps as editable modular pieces with animated entrances and exits', () => {
    for (const node of CAMPAIGN_ZONES) {
      if (node.nodeRole !== 'battlefield' && node.nodeRole !== 'fortress') continue;

      const zone = loadZone(node.id);
      const keeps = zone.rvrObjectives?.filter((objective) => objective.type === 'keep') ?? [];
      expect(keeps, node.id).toHaveLength(2);
      expect(zone.props.some((prop) => prop.kind === 'castle' && prop.id?.includes('_keep'))).toBe(false);

      for (const keep of keeps) {
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
    for (const node of CAMPAIGN_ZONES.filter((entry) => entry.nodeRole === 'capital')) {
      if (node.id === IMPORTED_AEGIS_CAPITAL_ID) continue;

      const zone = loadZone(node.id);
      const cityGateObjective = zone.rvrObjectives?.find((objective) => objective.type === 'city_gate');
      expect(cityGateObjective).toBeTruthy();
      const cityGate = zone.props.find((prop) => prop.id === `${cityGateObjective?.id}_gate`);
      expectInteractiveGate(cityGate, 'castle_gate.glb');
    }
  });

  test('capital cities include editable city walls, citadels, and animated entrances', () => {
    for (const node of CAMPAIGN_ZONES.filter((entry) => entry.nodeRole === 'capital')) {
      if (node.id === IMPORTED_AEGIS_CAPITAL_ID) continue;

      const zone = loadZone(node.id);
      const wallPrefix = `${node.id}_city_wall`;
      const citadelPrefix = `${node.id}_capital_citadel`;
      const wallProps = zone.props.filter((prop) => prop.id?.startsWith(wallPrefix));
      const citadelProps = zone.props.filter((prop) => prop.id?.startsWith(citadelPrefix));
      const wallKinds = node.realm === 'riftbound'
        ? { wall: 'rift_wall_segment', tower: 'rift_tower', house: 'rift_house' }
        : { wall: 'wall_segment', tower: 'tower', house: 'building' };

      expect(zone.paths?.length ?? 0, node.id).toBeGreaterThanOrEqual(12);
      expect(zone.paths?.some((pathDef: any) => pathDef.id === `${node.id}_castle_service_lane`), node.id).toBe(true);
      expect(wallProps.filter((prop) => prop.kind === wallKinds.wall).length, node.id).toBeGreaterThanOrEqual(8);
      expect(wallProps.filter((prop) => prop.kind === wallKinds.tower).length, node.id).toBeGreaterThanOrEqual(10);
      expect(zone.props.filter((prop) => prop.id?.startsWith(`${node.id}_capital_house_`) && prop.kind === wallKinds.house).length, node.id)
        .toBeGreaterThanOrEqual(34);
      expect(zone.props.filter((prop) => prop.id?.startsWith(`${node.id}_capital_house_`) && (prop.colliders?.length ?? 0) > 0).length, node.id)
        .toBeGreaterThanOrEqual(34);
      expect(zone.props.some((prop) => prop.kind === 'castle' && prop.id?.includes('capital_citadel'))).toBe(false);

      expectInteractiveGate(zone.props.find((prop) => prop.id === `${node.id}_city_gate_gate`), 'castle_gate.glb');
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${wallPrefix}_west_gate`), 'castle_gate.glb');
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${wallPrefix}_east_gate`), 'castle_gate.glb');
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${wallPrefix}_rear_gate`), 'castle_gate.glb');

      expect(citadelProps.filter((prop) => prop.kind === wallKinds.wall).length, node.id).toBeGreaterThanOrEqual(24);
      expect(citadelProps.filter((prop) => prop.kind === wallKinds.tower).length, node.id).toBeGreaterThanOrEqual(20);
      expect(citadelProps.filter((prop) => prop.kind === 'castle_floor').map((prop) => prop.y)).toEqual([0, 4, 8, 12, 16, 20]);
      expect(citadelProps.filter((prop) => prop.kind === 'castle_floor').every((prop) => (prop.walkableSurfaces?.length ?? 0) > 0)).toBe(true);
      expect(citadelProps.filter((prop) => prop.kind === 'castle_stairs')).toHaveLength(5);
      expect(citadelProps.filter((prop) =>
        (prop.y ?? 0) > 0 &&
        (prop.kind === wallKinds.wall || prop.kind === wallKinds.tower),
      ).every((prop) =>
        prop.colliders?.some((collider) =>
          Number.isFinite(collider.minY) &&
          Number.isFinite(collider.maxY) &&
          (collider.minY ?? 0) <= (collider.maxY ?? 0),
        ),
      )).toBe(true);
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${citadelPrefix}_front_gate`), 'castle_gate.glb');
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${citadelPrefix}_rear_postern`), 'castle_gate.glb');
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${citadelPrefix}_inner_front_door`), 'castle_door.glb');
      expectInteractiveGate(zone.props.find((prop) => prop.id === `${citadelPrefix}_inner_rear_door`), 'castle_door.glb');

      if (node.realm === 'aegis') {
        expect(zone.props.some((prop) => prop.id === `${node.id}_sun_court_temple` && prop.kind === 'temple')).toBe(true);
      } else {
        for (const kind of ['rift_house', 'rift_wall_segment', 'rift_tower', 'rift_obelisk', 'rift_brazier', 'rift_spike_cluster']) {
          expect(zone.props.some((prop) => prop.kind === kind), `${node.id}:${kind}`).toBe(true);
        }
        expect(zone.props.some((prop) => prop.id?.includes('sun_court'))).toBe(false);
        expect(zone.props.some((prop) => prop.id === `${node.id}_central_fountain`)).toBe(false);
      }
    }
  });

  test('imports Bastion of Aegis as terrain and keeps city services accessible', () => {
    const zone = loadZone(IMPORTED_AEGIS_CAPITAL_ID);
    expect(zone.terrainModel).toBe('terrain_aegis_capital_medieval_city.glb');
    expect(zone.props.some((prop) => prop.model === 'terrain_aegis_capital_medieval_city.glb')).toBe(false);

    const proxy = zone.props.find((prop) => prop.id === 'aegis_capital_imported_city_collision_proxy');
    expect(proxy).toBeTruthy();
    expect(proxy?.visible).toBe(false);
    expect(proxy?.colliders?.length ?? 0).toBeGreaterThanOrEqual(20);

    const colliders = proxy?.colliders ?? [];
    const points = [
      ...(zone.npcs ?? []).map((npc) => ({ id: npc.id, kind: 'npc', x: npc.x, z: npc.z })),
      ...(zone.craftingStations ?? []).map((station) => ({ id: station.id, kind: 'crafting', x: station.x, z: station.z })),
      ...(zone.resourceNodes ?? []).map((node) => ({ id: node.id, kind: 'resource', x: node.x, z: node.z })),
    ];

    expect(points.length).toBeGreaterThan(0);
    for (const point of points) {
      expect(Number.isFinite(point.x), `${point.kind}:${point.id}:x`).toBe(true);
      expect(Number.isFinite(point.z), `${point.kind}:${point.id}:z`).toBe(true);
      for (const collider of colliders) {
        expect(pointInsideCollider({ x: point.x!, z: point.z! }, collider), `${point.kind}:${point.id}`).toBe(false);
      }
    }
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
  model: string,
): void {
  expect(prop).toBeTruthy();
  expect(prop?.model).toBe(model);
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
      return { npcs: 6, enemies: 0, stations: 5, resources: 8 };
    case 'fortress':
      return { npcs: 5, enemies: 9, stations: 3, resources: 8 };
    case 'boss_lair':
      return { npcs: 3, enemies: 7, stations: 1, resources: 5 };
    case 'battlefield':
    default:
      return { npcs: 5, enemies: 10, stations: 3, resources: 10 };
  }
}
