import { afterAll, beforeAll, expect, test } from 'vitest';
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { defaultZoneConfigs } from '../src/shared/orvr/config';
import type { GateKind, ZoneConfig } from '../src/shared/orvr/protocol';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
// @ts-expect-error Executable authoring source deliberately remains an mjs module.
import { composeSunmeadowEnvironment, sunmeadowPlacementClear } from '../scripts/campaign/sunmeadow-environment.mjs';

const release = { terrain: true, architecture: true, nature: true };
const baseline = JSON.parse(readFileSync(resolve('public/assets/maps/sunmeadow_march.json'), 'utf8')) as ZoneDefinition;
const composed = composeSunmeadowEnvironment(structuredClone(baseline), release) as ZoneDefinition;
let directory = '';
let config: ZoneConfig;

beforeAll(async () => {
  directory = mkdtempSync(join(tmpdir(), 'warjs-sunmeadow-'));
  for (const zone of defaultZoneConfigs()) copyFileSync(resolve(`public/assets/maps/${zone.id}.json`), join(directory, `${zone.id}.json`));
  writeFileSync(join(directory, 'sunmeadow_march.json'), JSON.stringify(composed));
  config = (await loadCampaignMapConfigs(directory)).find(zone => zone.id === composed.id)!;
});
afterAll(() => {
  if (directory && dirname(resolve(directory)) === resolve(tmpdir()) && basename(directory).startsWith('warjs-sunmeadow-')) rmSync(directory, { recursive: true, force: true });
});

type Point = { x: number; z: number };
function reachable(bounds: { minX: number; maxX: number; minZ: number; maxZ: number }, start: Point, blockedGates: Array<{ point: Point; width: number; depth: number }> = []) {
  const width = bounds.maxX - bounds.minX + 1, height = bounds.maxZ - bounds.minZ + 1;
  const mask = new Uint8Array(width * height), seen = new Uint8Array(mask.length);
  const boxes = config.collision!.filter(box => box.minX < bounds.maxX + 1 && box.maxX > bounds.minX - 1 && box.minZ < bounds.maxZ + 1 && box.maxZ > bounds.minZ - 1);
  const index = (point: Point) => (Math.round(point.z) - bounds.minZ) * width + Math.round(point.x) - bounds.minX;
  for (let z = bounds.minZ; z <= bounds.maxZ; z++) for (let x = bounds.minX; x <= bounds.maxX; x++) {
    if (boxes.some(box => x >= box.minX - .5 && x <= box.maxX + .5 && z >= box.minZ - .5 && z <= box.maxZ + .5)
      || blockedGates.some(gate => Math.abs(x - gate.point.x) < gate.width / 2 + .5 && Math.abs(z - gate.point.z) < gate.depth / 2 + .5)) mask[index({ x, z })] = 1;
  }
  const queue = [index(start)]; if (!mask[queue[0]]) seen[queue[0]] = 1;
  for (let head = 0; head < queue.length; head++) {
    const current = queue[head]; if (mask[current]) continue;
    const x = current % width, z = Math.floor(current / width);
    for (const next of [x > 0 ? current - 1 : -1, x < width - 1 ? current + 1 : -1, z > 0 ? current - width : -1, z < height - 1 ? current + width : -1]) {
      if (next >= 0 && !seen[next] && !mask[next]) { seen[next] = 1; queue.push(next); }
    }
  }
  return (point: Point) => Boolean(seen[index(point)]);
}

test('composition is deterministic and idempotent without changing service/crafting/gameplay identities', () => {
  const second = composeSunmeadowEnvironment(structuredClone(composed), release);
  expect(second).toEqual(composed);
  expect(composed.props.length).toBeGreaterThan(1000);
  expect(new Set(composed.props.map(prop => prop.id)).size).toBe(composed.props.length);
  expect(composed.npcs?.map(npc => npc.id)).toEqual(baseline.npcs?.map(npc => npc.id));
  expect(composed.craftingStations?.map(station => station.id)).toEqual(baseline.craftingStations?.map(station => station.id));
  expect(composed.resourceNodes?.map(node => node.id)).toEqual(baseline.resourceNodes?.map(node => node.id));
  for (const node of composed.resourceNodes ?? []) expect(composed.props.some(prop => prop.id === node.visualPropId), node.id).toBe(true);
  expect(composeSunmeadowEnvironment({ id: 'other_zone' }, release)).toEqual({ id: 'other_zone' });
});

test('each gate shares exact geometry/collision coordinates with the authoritative dynamic footprint', () => {
  for (const keep of composed.orvrLayout!.keeps) for (const gate of keep.gates) {
    const prop = composed.props.find(prop => prop.id === gate.propId)!;
    const authoritative = config.keeps.find(entry => entry.id === keep.objectiveId)!;
    const point = gate.stage === 'outer' ? authoritative.outerGate : authoritative.innerGate;
    expect(point.x).toBe(prop.x); expect(point.z).toBe(prop.z);
    expect({ x: gate.x, z: gate.z }).toEqual({ x: prop.x, z: prop.z });
    expect(authoritative.gateFootprints![gate.stage]).toEqual({ width: 6, depth: .45, height: 4.8, rotY: -Math.PI });
    expect(prop.interaction?.type).toBe('gate');
    expect(prop.colliders![0].blocksWhen).toBe('closed');
    // The middle of the doorway is never also baked into permanent collision.
    expect(config.collision!.some(box => point.x >= box.minX && point.x <= box.maxX && point.z >= box.minZ && point.z <= box.maxZ)).toBe(false);
  }
});

test('published gatehouse wing geometry joins the curtain walls and keeps ground oil controls in the courtyard gap', () => {
  const bytes = readFileSync(resolve('public/assets/models/frontier_sunmeadow_gatehouse_lod0.glb'));
  const jsonLength = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString('utf8')) as {
    nodes: Array<{ mesh: number; translation?: number[]; rotation?: number[]; scale?: number[] }>;
    meshes: Array<{ primitives: Array<{ attributes: { POSITION: number } }> }>;
    accessors: Array<{ bufferView: number; byteOffset?: number; count: number; componentType: number }>;
    bufferViews: Array<{ byteOffset?: number; byteStride?: number }>;
  };
  expect(gltf.nodes).toHaveLength(1); expect(gltf.nodes[0].translation).toBeUndefined(); expect(gltf.nodes[0].rotation).toBeUndefined();
  const wingZ: number[] = [];
  for (const primitive of gltf.meshes[0].primitives) {
    const accessor = gltf.accessors[primitive.attributes.POSITION], view = gltf.bufferViews[accessor.bufferView];
    expect(accessor.componentType).toBe(5126);
    for (let index = 0; index < accessor.count; index++) {
      const offset = 28 + jsonLength + (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0) + index * (view.byteStride ?? 12);
      const x = bytes.readFloatLE(offset), y = bytes.readFloatLE(offset + 4), z = bytes.readFloatLE(offset + 8);
      if (Math.abs(x) > 13.5 && y > 1 && y < 7) wingZ.push(z);
    }
  }
  expect(wingZ.length).toBeGreaterThan(100);
  const wingCenter = (Math.min(...wingZ) + Math.max(...wingZ)) / 2;
  expect(wingCenter).toBeCloseTo(4.6, 1);
  for (const keep of composed.orvrLayout!.keeps) {
    const outer = composed.props.find(prop => prop.id === `sunmeadow_march_${keep.realm}_keep_outer_gatehouse`)!;
    const inner = composed.props.find(prop => prop.id === `sunmeadow_march_${keep.realm}_keep_inner_gatehouse`)!;
    expect(outer.z - wingCenter).toBeCloseTo(-24, 1);
    expect(inner.z - wingCenter).toBeCloseTo(-7.5, 1);
    expect(outer.rotY).toBe(Math.PI); expect(inner.rotY).toBe(Math.PI);
    expect(inner.z - 6 - (outer.z + 6)).toBeCloseTo(4.5);
    for (const gate of keep.gates) expect(gate.z).toBeCloseTo((gate.stage === 'outer' ? outer.z : inner.z) - 6);
    const controls = keep.siegeSlots.find(slot => slot.kind === 'oil')!.operatorPosition!;
    expect(controls.z - .5).toBeGreaterThan(outer.z + 6);
    expect(controls.z + .5).toBeLessThan(inner.z - 6);
    const standard = composed.props.find(prop => prop.id === `sunmeadow_march_${keep.realm}_keep_realm_standard`)!;
    expect(standard.z).toBeCloseTo(outer.z - 6.2);
  }
});

test('rear postern markers retain fixed nearby landings without opening a hole in the curtain collision', () => {
  for (const keep of composed.orvrLayout!.keeps) {
    const postern = keep.postern!;
    const marker = composed.props.find(prop => prop.id === postern.propId)!;
    expect(marker.scale).toBe(.5); expect(marker.interaction).toBeUndefined(); expect(marker.colliders).toBeUndefined();
    expect(marker.assetKey).toBe('frontier_sunmeadow_gate_leaves');
    expect(config.keeps.find(entry => entry.id === keep.objectiveId)!.postern).toEqual({ outside: postern.outside, inside: postern.inside, interactionRadius: 3 });
    const middle = { x: keep.x + 24, z: 32 };
    expect(config.collision!.some(box => middle.x >= box.minX && middle.x <= box.maxX && middle.z >= box.minZ && middle.z <= box.maxZ)).toBe(true);
    const courtyard = reachable({ minX: keep.x - 45, maxX: keep.x + 45, minZ: -85, maxZ: 45 }, postern.inside,
      keep.gates.map(gate => ({ point: gate, width: gate.width, depth: gate.depth })));
    for (const catapult of keep.siegeSlots.filter(slot => slot.kind === 'catapult')) expect(courtyard(catapult)).toBe(true);
    const oil = keep.siegeSlots.find(slot => slot.kind === 'oil')!;
    expect(oil.y).toBe(7.5);
    expect(oil.operatorPosition).toEqual({ x: keep.x + 8, y: 0, z: -11.9 });
    expect(courtyard(oil.operatorPosition!), `${keep.realm} oil controls`).toBe(true);
    expect(config.keeps.find(entry => entry.id === keep.objectiveId)!.siegeOperatorPositions!.oil).toEqual([oil.operatorPosition]);
    const console = composed.props.find(prop => prop.id === `sunmeadow_march_${keep.realm}_keep_oil_console`)!;
    expect(console.assetKey).toBe('riftspire_chain_winch'); expect(console.scale).toBe(.5);
    expect(console.x).toBe(keep.x + 10); expect(console.z).toBe(-11.9);
  }
});

test.each(['aegis', 'riftbound'])('%s keep has a sealed outer curtain and a second independent commander barrier', realm => {
  const keep = config.keeps.find(keep => keep.realm === realm)!;
  const bounds = { minX: keep.position.x - 45, maxX: keep.position.x + 45, minZ: -85, maxZ: 45 };
  const gate = (stage: GateKind) => ({ point: stage === 'outer' ? keep.outerGate : keep.innerGate, ...keep.gateFootprints![stage] });
  const closed = reachable(bounds, keep.deliveryPoint!, [gate('outer'), gate('inner')]);
  expect(closed(keep.position)).toBe(false);
  expect(closed(keep.quartermaster), `${realm} quartermaster`).toBe(true);
  const outerBreached = reachable(bounds, keep.deliveryPoint!, [gate('inner')]);
  expect(outerBreached(keep.position)).toBe(false);
  for (const position of keep.siegePositions!.catapult!) expect(outerBreached(position), `${realm} courtyard catapult`).toBe(true);
  const bothBreached = reachable(bounds, keep.deliveryPoint!);
  expect(bothBreached(keep.position), `${realm} commander chamber`).toBe(true);
  expect(bothBreached(keep.siegePositions!.ram![0]), `${realm} ram yard`).toBe(true);
});

test('settlement services and crafting remain reachable around the new building walls', () => {
  const canReach = reachable({ minX: -510, maxX: -370, minZ: -315, maxZ: -190 }, { x: -435, z: -245 });
  for (const npc of composed.npcs ?? []) expect(canReach(npc), npc.id).toBe(true);
  for (const station of composed.craftingStations ?? []) expect(canReach(station), station.id).toBe(true);
});

test('all supply shelters have their authored side/rear walls and the apothecary stays accessible beside the road', () => {
  const shelters = composed.props.filter(prop => prop.assetKey === 'frontier_sunmeadow_supply_post');
  expect(shelters).toHaveLength(8);
  for (const shelter of shelters) {
    expect(shelter.colliderSpace).toBe('model');
    expect(shelter.colliders!.map(({ x, z, width, depth, maxY }) => ({ x, z, width, depth, maxY }))).toEqual([
      { x: -4, z: 0, width: .5, depth: 5, maxY: 1.5 },
      { x: 4, z: 0, width: .5, depth: 5, maxY: 1.5 },
      { x: 0, z: -2.5, width: 8, depth: .5, maxY: 1.5 },
    ]);
  }
  const station = composed.craftingStations!.find(station => station.id === 'sunmeadow_march_apothecary_station')!;
  const shelter = shelters.find(shelter => shelter.id === `${station.id}_visual`)!;
  expect({ x: station.x, z: station.z }).toEqual({ x: -448, z: -266 });
  expect({ x: shelter.x, z: shelter.z, rotY: shelter.rotY }).toEqual({ x: station.x, z: station.z, rotY: 0 });
  for (const npc of composed.npcs!) expect(config.collision!.some(box => npc.x >= box.minX - .5 && npc.x <= box.maxX + .5 && npc.z >= box.minZ - .5 && npc.z <= box.maxZ + .5), npc.id).toBe(false);
});

test('supply routes reuse exact curved road segments and portal markers sit beside their travel lanes', () => {
  const paths = new Map(composed.paths!.map(path => [path.id.replace('sunmeadow_march_', ''), path]));
  expect(paths.size).toBe(15);
  for (const route of composed.orvrLayout!.caravanRoutes) {
    const prefix = route.objectiveId.endsWith('_west_objective') ? paths.get('march_road_south')!.points
      : route.objectiveId.endsWith('_east_objective') ? [...paths.get('march_road_north')!.points].reverse() : [{ x: 0, z: 0 }];
    expect(route.points).toEqual([...prefix, ...paths.get(`${route.realm}_keep_road`)!.points.slice(1)]);
  }
  const exits = { aegis_capital: { x: -570, z: -380 }, greybrook_crossing: { x: 120, z: 570 }, wardens_hollow: { x: -570, z: 220 } };
  for (const [destination, point] of Object.entries(exits)) {
    const trigger = composed.zoneTriggers!.find(trigger => trigger.targetZoneId === destination)!;
    expect({ x: trigger.x, z: trigger.z }).toEqual(point);
    const marker = composed.props.find(prop => prop.id === `sunmeadow_march_portal_${destination}`)!;
    expect(Math.hypot(marker.x - point.x, marker.z - point.z)).toBeGreaterThan(3.9);
    expect(marker.colliders![0].width).toBe(.76);
  }
  for (const objective of composed.orvrLayout!.battlefieldObjectives) {
    const marker = composed.props.find(prop => prop.id === `${objective.objectiveId}_banner`)!;
    expect(Math.hypot(marker.x - objective.x, marker.z - objective.z)).toBeLessThan(objective.captureRadius);
    expect(marker.colliders![0].width).toBe(.76);
  }
});

test('the curved roads retain full lane clearance from settlement buildings and incidental props', () => {
  for (const path of composed.paths!) {
    for (let i = 1; i < path.points.length; i++) {
      const a = path.points[i - 1], b = path.points[i], steps = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z));
      for (let step = 0; step <= steps; step++) {
        const x = a.x + (b.x - a.x) * step / steps, z = a.z + (b.z - a.z) * step / steps;
        const obstructed = config.collision!.some(box => Math.hypot(Math.max(0, box.minX - x, x - box.maxX), Math.max(0, box.minZ - z, z - box.maxZ)) < path.width / 2);
        expect(obstructed, `${path.id} at ${x},${z}`).toBe(false);
      }
    }
  }
});

test('authored vegetation keeps road, supply corridor, staging and objective clearances after rounding', () => {
  const nature = composed.props.filter(prop => /^frontier_sunmeadow_(oak|ash|hawthorn|wheat|meadow|limestone)/.test(prop.assetKey ?? ''));
  expect(nature.length).toBeGreaterThan(1000);
  for (const prop of nature) {
    const key = prop.assetKey!;
    const radius = /oak|ash/.test(key) ? 5.5 : /hawthorn/.test(key) ? 2.6 : /wheat/.test(key) ? 1 : /meadow/.test(key) ? 1.4 : 4;
    expect(sunmeadowPlacementClear(composed, prop, radius * (prop.scale ?? 1) - .003), prop.id).toBe(true);
  }
  for (const route of composed.orvrLayout!.caravanRoutes) {
    const keep = composed.orvrLayout!.keeps.find(keep => keep.objectiveId === route.destinationKeepId)!;
    expect(route.points.at(-1)).toEqual(keep.deliveryPoint);
    for (let segment = 1; segment < route.points.length; segment++) {
      const a = route.points[segment - 1], b = route.points[segment], steps = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z));
      for (let step = 0; step <= steps; step++) {
        const x = a.x + (b.x - a.x) * step / steps, z = a.z + (b.z - a.z) * step / steps;
        expect(config.collision!.some(box => x >= box.minX - .6 && x <= box.maxX + .6 && z >= box.minZ - .6 && z <= box.maxZ + .6), `${route.id} at ${x},${z}`).toBe(false);
      }
    }
  }
});
