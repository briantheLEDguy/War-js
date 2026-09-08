import { afterAll, beforeAll, expect, test } from 'vitest';
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { loadCampaignMapConfigs } from '../server/mapConfig';
import { campaignColliderBlocksHeight, campaignColliderContains, campaignGroundHeight } from '../src/shared/orvr/navigation';
import { defaultZoneConfigs } from '../src/shared/orvr/config';
import type { ZoneConfig } from '../src/shared/orvr/protocol';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
// @ts-expect-error Executable authoring source is intentionally an mjs module.
import { applyOrvrZoneLayout } from '../scripts/campaign/orvr-zone-layouts.mjs';
// @ts-expect-error Executable authoring source is intentionally an mjs module.
import { composeSunmeadowEnvironment } from '../scripts/campaign/sunmeadow-environment.mjs';
// @ts-expect-error Executable authoring source is intentionally an mjs module.
import { composeCinderfenEnvironment } from '../scripts/campaign/cinderfen-environment.mjs';
// @ts-expect-error Executable authoring source is intentionally an mjs module.
import { composeCinderfenLandscape } from '../scripts/campaign/cinderfen-landscape.mjs';
// @ts-expect-error Executable authoring source is intentionally an mjs module.
import { integrateCinderfen } from '../scripts/campaign/cinderfen-integration.mjs';

type Point = { x: number; z: number };
const outdoorIds = defaultZoneConfigs().filter(zone => zone.kind !== 'city').map(zone => zone.id);
const originals = new Map(outdoorIds.map(id => [id, JSON.parse(readFileSync(resolve(`public/assets/maps/${id}.json`), 'utf8')) as ZoneDefinition]));
const composed = new Map<string, ZoneDefinition>();
let configs: Map<string, ZoneConfig>, directory = '';
const key = (point: Point) => `${point.x},${point.z}`;
const edge = (a: Point, b: Point) => [key(a), key(b)].sort().join('|');
const cinderfen = (zone: ZoneDefinition) => integrateCinderfen(composeCinderfenEnvironment(composeCinderfenLandscape(zone, true), { architecture: true }));

beforeAll(async () => {
  directory = mkdtempSync(join(tmpdir(), 'warjs-roads-'));
  for (const config of defaultZoneConfigs()) copyFileSync(resolve(`public/assets/maps/${config.id}.json`), join(directory, `${config.id}.json`));
  for (const [id, source] of originals) {
    const zone = id === 'sunmeadow_march'
      ? composeSunmeadowEnvironment(structuredClone(source), { terrain: true, architecture: true, nature: true })
      : id === 'cinderfen_outskirts' ? cinderfen(structuredClone(source))
      : applyOrvrZoneLayout(structuredClone(source), { id, realm: source.campaign!.realm, nodeRole: source.campaign!.nodeRole });
    composed.set(id, zone);
    writeFileSync(join(directory, `${id}.json`), JSON.stringify(zone));
  }
  configs = new Map((await loadCampaignMapConfigs(directory)).map(config => [config.id, config]));
}, 30_000);

afterAll(() => {
  if (directory && dirname(resolve(directory)) === resolve(tmpdir()) && basename(directory).startsWith('warjs-roads-')) rmSync(directory, { recursive: true, force: true });
});

test('all 108 supply itineraries follow existing road segments with measured natural-road lengths', () => {
  const lengths: number[] = [];
  for (const [id, zone] of composed) {
    const edges = new Set(zone.paths!.flatMap(path => path.points.slice(1).map((p, i) => edge(path.points[i], p))));
    const config = configs.get(id)!;
    expect(zone.orvrLayout!.caravanRoutes).toHaveLength(6);
    for (const route of zone.orvrLayout!.caravanRoutes) {
      const objective = config.objectives.find(objective => objective.id === route.objectiveId)!;
      expect(objective.routes![route.realm]!.map(p => ({ x: p.x, z: p.z }))).toEqual(route.points);
      let length = 0;
      for (let i = 1; i < route.points.length; i++) {
        expect(edges.has(edge(route.points[i - 1], route.points[i])), route.id).toBe(true);
        length += Math.hypot(route.points[i].x - route.points[i - 1].x, route.points[i].z - route.points[i - 1].z);
      }
      expect(route.lengthMetres).toBe(Math.round(length * 100) / 100);
      expect(length).toBeGreaterThanOrEqual(350); expect(length).toBeLessThanOrEqual(750);
      lengths.push(length);
    }
  }
  expect(lengths).toHaveLength(108);
  // The envelope change is supported by measured short center-BO and longer outer-BO trips.
  expect(Math.min(...lengths)).toBeLessThan(400); expect(Math.max(...lengths)).toBeGreaterThan(600);
});

test.each(outdoorIds)('%s keeps every full road lane clear of authoritative permanent collision', id => {
  const zone = composed.get(id)!, config = configs.get(id)!;
  for (const path of zone.paths!) {
    for (let i = 1; i < path.points.length; i++) {
      const a = path.points[i - 1], b = path.points[i], steps = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) * 2));
      for (let step = 0; step <= steps; step++) {
        const x = a.x + (b.x - a.x) * step / steps, z = a.z + (b.z - a.z) * step / steps;
        const position = { x, y: campaignGroundHeight(config, { x, y: 0, z }), z };
        const collision = config.collision!.find(box => campaignColliderBlocksHeight(box, position.y)
          && campaignColliderContains(box, position, path.width / 2 - .001));
        expect(collision, `${path.id} at ${x},${z}`).toBeUndefined();
      }
    }
  }
});

test.each(outdoorIds.filter(id => id !== 'sunmeadow_march'))('%s connects its road hierarchy and retains every existing portal/service identity', id => {
  const zone = composed.get(id)!, source = originals.get(id)!;
  expect(zone.zoneTriggers).toEqual(source.zoneTriggers);
  expect(zone.npcs).toEqual(source.npcs); expect(zone.craftingStations).toEqual(source.craftingStations);
  expect(zone.props.map(prop => prop.id)).toEqual(source.props.map(prop => prop.id));
  expect(zone.resourceNodes!.map(node => node.id)).toEqual(source.resourceNodes!.map(node => node.id));
  for (const node of zone.resourceNodes!) {
    const visual = zone.props.find(prop => prop.id === node.visualPropId)!;
    expect({ x: visual.x, z: visual.z }).toEqual({ x: node.x, z: node.z });
  }
  const adjacency = new Map<string, Set<string>>(), physicalEdges = new Set<string>();
  for (const path of zone.paths!) {
    expect(path.autoConnect).toBe(false);
    for (let i = 1; i < path.points.length; i++) {
      const a = key(path.points[i - 1]), b = key(path.points[i]);
      expect(physicalEdges.has(edge(path.points[i - 1], path.points[i])), `duplicated physical road in ${path.id}`).toBe(false);
      physicalEdges.add(edge(path.points[i - 1], path.points[i]));
      if (!adjacency.has(a)) adjacency.set(a, new Set()); if (!adjacency.has(b)) adjacency.set(b, new Set());
      adjacency.get(a)!.add(b); adjacency.get(b)!.add(a);
    }
  }
  const queue = ['0,0'], reached = new Set(queue);
  for (let index = 0; index < queue.length; index++) for (const next of adjacency.get(queue[index]) ?? []) if (!reached.has(next)) { reached.add(next); queue.push(next); }
  expect(reached.size).toBe(adjacency.size);
  for (const trigger of zone.zoneTriggers!) expect(reached.has(key(trigger)), trigger.id).toBe(true);
  for (const road of zone.paths!.filter(path => path.id!.includes('_portal_road_'))) {
    for (const point of road.points) for (const keep of zone.orvrLayout!.keeps) expect(Math.hypot(point.x - keep.x, point.z - keep.z)).toBeGreaterThan(90);
  }
});

test('reapplying regional road composition is deterministic, idempotent and refreshes vegetation exclusions', () => {
  for (const [id, zone] of composed) {
    if (id === 'sunmeadow_march') continue;
    const node = { id, realm: zone.campaign!.realm, nodeRole: zone.campaign!.nodeRole };
    const compose = id === 'cinderfen_outskirts' ? cinderfen : (source: ZoneDefinition) => applyOrvrZoneLayout(source, node);
    expect(compose(structuredClone(originals.get(id)!))).toEqual(zone);
    expect(compose(structuredClone(zone))).toEqual(zone);
    for (const patch of zone.orvrLayout!.biome.placements!) for (const road of zone.paths!) {
      const exclusion = patch.excludeCorridors!.find(corridor => corridor.id === road.id)!;
      expect(exclusion.points).toEqual(road.points); expect(exclusion.radius).toBeGreaterThanOrEqual(road.width / 2 + 3);
    }
  }
}, 30_000);
