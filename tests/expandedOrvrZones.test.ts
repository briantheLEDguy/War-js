import { describe, expect, test } from 'vitest';
import { Terrain } from '../src/world/Terrain';
import { orvrGridHeightAt, orvrHeightAt } from '../src/shared/orvrTerrain';
import type { AssetLoader } from '../src/game/AssetLoader';
import { readFileSync } from 'node:fs';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
// @ts-expect-error Campaign sources are executable authoring modules.
import { NODES, EDGES } from '../scripts/campaign/static-campaign-source.mjs';
// @ts-expect-error Campaign sources are executable authoring modules.
import { ORVR_ART_DIRECTIONS, ORVR_LAIR_ART_DIRECTIONS, WORLD_ART_DIRECTIONS } from '../scripts/campaign/orvr-art-direction.mjs';
// @ts-expect-error Campaign sources are executable authoring modules.
import { applyOrvrZoneLayout, linkOrvrZoneTravel, ORVR_ZONE_LAYOUTS, ORVR_ZONE_SIZE, routeLength } from '../scripts/campaign/orvr-zone-layouts.mjs';

type Node = { id: string; name: string; realm: string; nodeRole: string };
type Point = { x: number; z: number };
type Layout = (typeof ORVR_ZONE_LAYOUTS)[string];
const nodes = NODES as Node[];
const expanded = nodes.filter((node) => ['battlefield', 'fortress'].includes(node.nodeRole));

function fixture(node: Node) {
  const size = node.nodeRole === 'fortress' ? 340 : node.nodeRole === 'capital' ? 360 : node.nodeRole === 'boss_lair' ? 190 : 300;
  const objectives = ['west', 'central', 'east'].map((name, index) => ({ id: `${node.id}_${name}_objective`, type: 'battle_objective', label: `${name} objective`, x: [-64, 0, 64][index], z: index === 1 ? 6 : -18, captureRadius: 13, defaultRealm: node.realm }));
  objectives.push(...['aegis', 'riftbound'].map((realm, index) => ({ id: `${node.id}_${realm}_keep`, type: 'keep', label: `${realm} keep`, x: index === 0 ? -52 : 52, z: 62, captureRadius: 18, defaultRealm: realm })));
  const neighbors = (EDGES as [string, string][]).flatMap(([a, b]) => a === node.id ? [b] : b === node.id ? [a] : []);
  return {
    id: node.id, name: node.name, size, segments: 96, campaign: { realm: node.realm, nodeRole: node.nodeRole },
    rvrObjectives: objectives,
    zoneTriggers: neighbors.map((targetZoneId, index) => ({
      id: `${node.id}_to_${targetZoneId}`, label: `Travel ${targetZoneId}`, targetZoneId,
      x: Math.cos(index * 2 * Math.PI / neighbors.length) * size * 0.43,
      z: Math.sin(index * 2 * Math.PI / neighbors.length) * size * 0.43,
      radius: 10, targetSpawn: { x: 0, y: 0, z: 0 },
    })),
    spawnPoint: { x: 0, y: 0, z: -40 },
    props: [
      { id: `${node.id}_west_objective_banner`, kind: 'banner', x: -64, z: -18 },
      { id: `${node.id}_aegis_keep_keep_front_gate`, kind: 'gate', x: -52, z: 39.2, interaction: { id: `${node.id}_gate_interaction`, type: 'gate' }, colliders: [{ width: 6, depth: 1 }] },
      { id: `${node.id}_herb_visual`, kind: 'herb', x: -80, z: 20, assetKey: 'existing_herb' },
      { id: `${node.id}_life_market`, kind: 'life_barrels', x: 12, z: -42 },
    ],
    enemies: [
      { id: `${node.id}_west_guard_1`, name: 'Guard', archetype: 'guard', x: -64, z: -18 },
      { id: `${node.id}_aegis_keep_commander`, name: 'Castellan', archetype: 'captain', x: -52, z: 66, encounter: { objectiveId: `${node.id}_aegis_keep`, realm: 'aegis' } },
      { id: `${node.id}_beast_1`, name: 'Wolf', archetype: 'beast', x: -96, z: -74 },
    ],
    npcs: [{ id: `${node.id}_merchant`, name: 'Local Merchant', role: 'vendor', x: 10, z: -40, characterProfileKey: 'npc_existing_merchant' }],
    craftingStations: [{ id: `${node.id}_workbench`, kind: 'forge', label: 'Forge', x: 20, z: -40 }],
    resourceNodes: [{ id: `${node.id}_herb`, kind: 'herb', x: -80, z: 20, visualPropId: `${node.id}_herb_visual`, loot: [{ key: 'existing_herb', qty: 1, chance: 1 }] }],
    ambientLife: { actors: [{ id: `${node.id}_citizen`, kind: 'citizen', x: 10, z: -40, route: [{ x: 20, z: -40 }] }], emitters: [] },
    paths: [], biomeKits: [{ id: `${node.id}_old_kit`, biomeId: 'evergreen_pnw' }],
  };
}

function distanceToSegment(position: Point, start: Point, end: Point) {
  const dx = end.x - start.x;
  const dz = end.z - start.z;
  const squared = dx * dx + dz * dz;
  const t = squared ? Math.max(0, Math.min(1, ((position.x - start.x) * dx + (position.z - start.z) * dz) / squared)) : 0;
  return Math.hypot(position.x - start.x - t * dx, position.z - start.z - t * dz);
}

describe('expanded authored ORvR zone contracts', () => {
  test('maps every battlefield and fortress explicitly, and all optional lairs to their parent climate', () => {
    expect(expanded).toHaveLength(18);
    expect(Object.keys(ORVR_ZONE_LAYOUTS).sort()).toEqual(expanded.map((node) => node.id).sort());
    expect(Object.keys(ORVR_ART_DIRECTIONS)).toHaveLength(18);
    expect(Object.keys(ORVR_LAIR_ART_DIRECTIONS)).toHaveLength(12);
    expect(Object.keys(WORLD_ART_DIRECTIONS).sort()).toEqual(nodes.filter((node) => node.nodeRole !== 'capital').map((node) => node.id).sort());
    for (const lair of Object.values(ORVR_LAIR_ART_DIRECTIONS) as Array<{ parentZoneId: string; biomeId: string; optionalCampaignBranch: boolean }>) {
      expect(lair.biomeId).toBe(ORVR_ART_DIRECTIONS[lair.parentZoneId].biomeId);
      expect(lair.optionalCampaignBranch).toBe(true);
    }
  });

  test.each(expanded)('$id has three neutral objectives, two opposed keeps and safe staging', (node) => {
    const layout = ORVR_ZONE_LAYOUTS[node.id];
    expect(layout.size).toBe(1200);
    expect(layout.battlefieldObjectives).toHaveLength(3);
    expect(layout.battlefieldObjectives.every((objective: { initialRealm: string }) => objective.initialRealm === 'neutral')).toBe(true);
    expect(layout.keeps.map((keep: { realm: string }) => keep.realm)).toEqual(['aegis', 'riftbound']);
    expect(Math.hypot(layout.keeps[0].x - layout.keeps[1].x, layout.keeps[0].z - layout.keeps[1].z)).toBe(700);
    for (const camp of layout.stagingCamps) {
      expect(camp.capturable).toBe(false);
      expect(camp.respawnSeconds).toBe(15);
      expect(layout.keeps.every((keep: Point) => Math.hypot(keep.x - camp.x, keep.z - camp.z) > 150)).toBe(true);
    }
  });

  test.each(expanded)('$id has six traversable supply corridors with complete siege positions', (node) => {
    const layout: Layout = ORVR_ZONE_LAYOUTS[node.id];
    expect(layout.caravanRoutes).toHaveLength(6);
    for (const route of layout.caravanRoutes) {
      expect(route.lengthMetres).toBe(routeLength(route.points));
      expect(route.lengthMetres).toBeGreaterThanOrEqual(350);
      expect(route.lengthMetres).toBeLessThanOrEqual(750);
      expect(route.width).toBe(12);
      expect(route.clearanceRadius).toBeGreaterThanOrEqual(route.width / 2 + 3);
      const objective = layout.battlefieldObjectives.find((entry: { objectiveId: string }) => entry.objectiveId === route.objectiveId);
      const keep = layout.keeps.find((entry: { objectiveId: string }) => entry.objectiveId === route.destinationKeepId);
      expect(route.points[0]).toEqual({ x: objective.x, z: objective.z });
      expect(route.points.at(-1)).toEqual(keep.deliveryPoint);
      for (const position of route.points) {
        expect(Math.abs(position.x) + route.clearanceRadius).toBeLessThan(ORVR_ZONE_SIZE / 2);
        expect(Math.abs(position.z) + route.clearanceRadius).toBeLessThan(ORVR_ZONE_SIZE / 2);
      }
    }
    for (const keep of layout.keeps) {
      expect(keep.gates.map((gate: { stage: string }) => gate.stage)).toEqual(['outer', 'inner']);
      expect(keep.siegeSlots.filter((slot: { kind: string }) => slot.kind === 'oil')).toHaveLength(1);
      expect(keep.siegeSlots.filter((slot: { kind: string }) => slot.kind === 'catapult')).toHaveLength(2);
      expect(keep.commander.entityId).toBe(`${node.id}_${keep.realm}_keep_commander`);
      expect(keep.ramSpawn.assetKey).toBe('frontier_battering_ram');
    }
  });

  test('covers the entire terrain without pretending unbuilt assets have passed review', () => {
    for (const layout of Object.values(ORVR_ZONE_LAYOUTS) as Layout[]) {
      expect(layout.terrain.chunks).toHaveLength(16);
      expect(layout.terrain.chunks.reduce((area: number, chunk: { width: number; depth: number }) => area + chunk.width * chunk.depth, 0)).toBe(1200 * 1200);
      expect(new Set(layout.terrain.chunks.map((chunk: { id: string }) => chunk.id)).size).toBe(16);
      expect(layout.terrain.chunks.every((chunk: { status: string }) => chunk.status === 'planned')).toBe(true);
      expect(layout.assetPolicy.mode).toBe('legacy-transition');
      expect(layout.assetPolicy.allowNewPrimitiveModels).toBe(false);
      expect(layout.assetPolicy.requiredAssetKeys).toContain('frontier_keep_gate');
      expect(layout.status).toBe('layout-ready-art-pending');
    }
  });

  test('preserves persistent IDs, source assets, encounters, harvest links, and service assignments', () => {
    const node = expanded.find((entry) => entry.id === 'sunmeadow_march')!;
    const before = fixture(node);
    const result = applyOrvrZoneLayout(structuredClone(before), node);
    for (const collection of ['rvrObjectives', 'enemies', 'npcs', 'props', 'resourceNodes', 'craftingStations', 'zoneTriggers'] as const) {
      expect(result[collection].map((entry: { id: string }) => entry.id)).toEqual(before[collection].map((entry) => entry.id));
    }
    expect(result.enemies[1].encounter).toEqual(before.enemies[1].encounter);
    expect(result.enemies[1]).toMatchObject({ x: -350, z: 4 });
    expect(result.enemies[0]).toMatchObject({ x: 0, z: -260 });
    expect(result.npcs[0].characterProfileKey).toBe('npc_existing_merchant');
    expect(result.props[2].assetKey).toBe('existing_herb');
    expect(result.props[2]).toMatchObject({ x: result.resourceNodes[0].x, z: result.resourceNodes[0].z });
    expect(result.resourceNodes[0].loot).toEqual(before.resourceNodes[0].loot);
    expect(result.props[1].interaction).toEqual(before.props[1].interaction);
    expect(result.props[1].colliders).toEqual(before.props[1].colliders);
    expect(Math.hypot(result.enemies[2].x - result.npcs[0].x, result.enemies[2].z - result.npcs[0].z)).toBeGreaterThan(200);
  });

  test('is deterministic and idempotent while retaining explicit climate palettes', () => {
    for (const node of expanded) {
      const first = applyOrvrZoneLayout(fixture(node), node);
      const second = applyOrvrZoneLayout(fixture(node), node);
      expect(first).toEqual(second);
      expect(applyOrvrZoneLayout(structuredClone(first), node)).toEqual(first);
      expect(first.orvrLayout.biome.placements).toHaveLength(16);
      expect(first.biomeKits).toEqual([]);
      expect(first.orvrLayout.biome.placements.every((patch: { approvedAssetKeys: string[] }) => patch.approvedAssetKeys.length === 0)).toBe(true);
      expect(first.orvrLayout.populationAssignments[0].race).toBe(ORVR_ART_DIRECTIONS[node.id].races[0]);
    }
  });

  test('relinks all original travel edges, including capital and lair return spawns', () => {
    const zones = nodes.map((node) => applyOrvrZoneLayout(fixture(node), node));
    const before = structuredClone(zones);
    linkOrvrZoneTravel(zones);
    for (const source of zones) for (const trigger of source.zoneTriggers) {
      const target = zones.find((candidate) => candidate.id === trigger.targetZoneId)!;
      if (!target.orvrLayout) {
        expect(trigger).toEqual(before.find((entry) => entry.id === source.id)!.zoneTriggers.find((entry: { id: string }) => entry.id === trigger.id));
        continue;
      }
      const reverse = target.zoneTriggers.find((candidate: { targetZoneId: string }) => candidate.targetZoneId === source.id)!;
      expect(Math.hypot(reverse.x, reverse.z)).toBeCloseTo(540, 1);
      expect(Math.hypot(trigger.targetSpawn.x - reverse.x, trigger.targetSpawn.z - reverse.z)).toBeCloseTo(reverse.radius + 10, 1);
      expect(Math.hypot(trigger.targetSpawn.x, trigger.targetSpawn.z)).toBeLessThan(530);
    }
    expect(zones.reduce((count, zone) => count + zone.zoneTriggers.length, 0)).toBe((EDGES as unknown[]).length * 2);
  });

  test('portal roads bypass keep courtyards and all roads reserve vegetation clearances', () => {
    for (const node of expanded) {
      const zone = applyOrvrZoneLayout(fixture(node), node);
      for (const road of zone.paths.filter((path: { id: string }) => path.id.includes('_portal_road_'))) {
        for (const keep of zone.orvrLayout.keeps) {
          for (let index = 1; index < road.points.length; index += 1) {
            expect(distanceToSegment(keep, road.points[index - 1], road.points[index])).toBeGreaterThan(45);
          }
        }
      }
      for (const patch of zone.orvrLayout.biome.placements) {
        expect(patch.excludeCorridors.length).toBeGreaterThanOrEqual(zone.paths.length);
        for (const path of zone.paths) {
          const corridor = patch.excludeCorridors.find((entry: { id: string }) => entry.id === path.id);
          expect(corridor.points).toEqual(path.points);
          expect(corridor.radius).toBeGreaterThanOrEqual(path.width / 2 + 3);
        }
      }
    }
  });

  test('refuses malformed ORvR objective sets instead of dropping identity silently', () => {
    const node = expanded[0];
    const missingKeep = fixture(node);
    missingKeep.rvrObjectives.pop();
    expect(() => applyOrvrZoneLayout(missingKeep, node)).toThrow('exactly three battlefield objectives and two keeps');
    const unknown = fixture(node);
    unknown.rvrObjectives[0].id = 'unmapped_objective';
    expect(() => applyOrvrZoneLayout(unknown, node)).toThrow('Unmapped ORvR objective');
  });

  test('keeps supply roads, objectives and staging level while shaping the surrounding land', () => {
    const node = expanded.find((entry) => entry.id === 'highvale_rampart')!;
    const zone = applyOrvrZoneLayout(fixture(node), node);
    const controls = zone.orvrLayout.terrain;
    for (const area of controls.flattenAreas) {
      expect(orvrHeightAt(controls, area.x, area.z)).toBe(area.height);
    }
    for (const road of zone.paths) for (let index = 1; index < road.points.length; index += 1) {
      const from = road.points[index - 1];
      const to = road.points[index];
      for (let fraction = 0; fraction <= 1; fraction += 0.1) {
        const x = from.x + (to.x - from.x) * fraction;
        const z = from.z + (to.z - from.z) * fraction;
        expect(orvrHeightAt(controls, x, z)).toBe(0);
      }
    }
    expect(orvrHeightAt(controls, -180, 490)).toBeGreaterThan(20);
    expect(orvrHeightAt(controls, 70, -360)).toBeLessThan(0);
    expect(orvrGridHeightAt(controls, 1200, 192, 601, 0)).toBe(0);
    expect(orvrGridHeightAt(controls, 1200, 192, Number.NaN, 0)).toBe(0);
  });

  test('client terrain grounding matches the server grid at slopes, borders and roads', async () => {
    const node = expanded.find((entry) => entry.id === 'sunmeadow_march')!;
    const zone = applyOrvrZoneLayout(fixture(node), node);
    const options = { size: zone.size, segments: zone.segments, orvrTerrain: zone.orvrLayout.terrain, biomePalette: zone.orvrLayout.biome.palette };
    const terrain = new Terrain(options);
    await terrain.build({} as AssetLoader, options);
    for (let index = 0; index < 140; index += 1) {
      const x = -600 + (index * 137 % 1201);
      const z = -600 + (index * 179 % 1201);
      expect(terrain.heightAt(x, z)).toBeCloseTo(orvrGridHeightAt(options.orvrTerrain, options.size, options.segments, x, z), 6);
    }
    expect(terrain.heightAt(-350, 0)).toBe(0);
    expect(terrain.heightAt(350, 0)).toBe(0);
    terrain.mesh.traverse((object) => {
      const mesh = object as import('three').Mesh;
      mesh.geometry?.dispose();
      if (Array.isArray(mesh.material)) mesh.material.forEach((material) => material.dispose());
      else mesh.material?.dispose();
    });
  });

  test('generated supply-road widths clear existing architecture during the asset transition', () => {
    for (const node of expanded) {
      const zone = JSON.parse(readFileSync(`public/assets/maps/${node.id}.json`, 'utf8')) as ZoneDefinition;
      const routes = zone.orvrLayout!.caravanRoutes;
      for (const route of routes) for (const prop of zone.props) for (const collider of prop.colliders ?? []) {
        const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1);
        const sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
        const rotation = (prop.rotY ?? 0) * (prop.colliderSpace === 'model' ? -1 : 1);
        const centerX = prop.x + (collider.x ?? 0) * sx * Math.cos(rotation) - (collider.z ?? 0) * sz * Math.sin(rotation);
        const centerZ = prop.z + (collider.x ?? 0) * sx * Math.sin(rotation) + (collider.z ?? 0) * sz * Math.cos(rotation);
        const yaw = rotation + (collider.rotY ?? 0);
        for (let index = 1; index < route.points.length; index += 1) {
          const start = route.points[index - 1];
          const end = route.points[index];
          const length = Math.hypot(end.x - start.x, end.z - start.z);
          for (let distance = 0; distance <= length; distance += 2) {
            const px = start.x + (end.x - start.x) * distance / length - centerX;
            const pz = start.z + (end.z - start.z) * distance / length - centerZ;
            const dx = px * Math.cos(yaw) + pz * Math.sin(yaw);
            const dz = -px * Math.sin(yaw) + pz * Math.cos(yaw);
            const separation = Math.hypot(Math.max(0, Math.abs(dx) - collider.width * sx / 2), Math.max(0, Math.abs(dz) - collider.depth * sz / 2));
            if (separation < route.width / 2) expect(separation, `${route.id} intersects ${prop.id}`).toBeGreaterThanOrEqual(route.width / 2);
          }
        }
      }
    }
  });
});
