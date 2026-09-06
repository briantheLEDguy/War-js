import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import { applyBiomeKits } from '../src/world/BiomeKit';
import type { PropSpawn, ZoneDefinition } from '../src/world/ZoneLoader';
// @ts-expect-error Shared native ESM authoring module.
import { AEGIS_REVIEWED_SCENERY } from '../scripts/campaign/aegis-reviewed-scenery.mjs';
import {
  decorateWorldLife,
  WORLD_LIFE_FOOTPRINTS,
  WORLD_LIFE_VERSION,
  WORLD_LIFE_ZONE_IDS,
} from '../scripts/campaign/world-life-source.mjs';

type Point = { x: number; z: number };
const ids = WORLD_LIFE_ZONE_IDS as string[];
const footprint = WORLD_LIFE_FOOTPRINTS as Record<string, number>;
const originalLifeKind = new Map<string, string>(Object.entries(AEGIS_REVIEWED_SCENERY)
  .filter(([kind]) => kind.startsWith('life_'))
  .map(([kind, entry]) => [(entry as { kind: string }).kind, kind]));

function lifeKind(prop: PropSpawn): string {
  return originalLifeKind.get(prop.kind) ?? prop.kind;
}

function lifeRadius(prop: PropSpawn): number {
  return footprint[lifeKind(prop)];
}

function readZone(id: string): ZoneDefinition {
  return JSON.parse(readFileSync(`public/assets/maps/${id}.json`, 'utf8'));
}

function lifeProps(zone: ZoneDefinition): PropSpawn[] {
  return zone.props.filter((prop) => prop.id?.startsWith(`${zone.id}_life_`));
}

function distanceToSegment(point: Point, a: Point, b: Point): number {
  const length = (b.x - a.x) ** 2 + (b.z - a.z) ** 2;
  const t = length ? Math.max(0, Math.min(1, ((point.x - a.x) * (b.x - a.x) + (point.z - a.z) * (b.z - a.z)) / length)) : 0;
  return Math.hypot(point.x - a.x - t * (b.x - a.x), point.z - a.z - t * (b.z - a.z));
}

function samples(points: Point[]): Point[] {
  const result: Point[] = [points[0]];
  for (let i = 1; i < points.length; i += 1) {
    const a = points[i - 1];
    const b = points[i];
    const count = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) * 2));
    for (let step = 1; step <= count; step += 1) {
      result.push({ x: a.x + (b.x - a.x) * step / count, z: a.z + (b.z - a.z) * step / count });
    }
  }
  return result;
}

function expectOutsideColliders(point: Point, radius: number, props: PropSpawn[], context: string): void {
  for (const prop of props) {
    for (const collider of prop.colliders ?? []) {
      const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1);
      const sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
      const yawSign = prop.colliderSpace === 'model' ? -1 : 1;
      const rotation = (prop.rotY ?? 0) * yawSign;
      const localX = (collider.x ?? 0) * sx;
      const localZ = (collider.z ?? 0) * sz;
      const centerX = prop.x + localX * Math.cos(rotation) - localZ * Math.sin(rotation);
      const centerZ = prop.z + localX * Math.sin(rotation) + localZ * Math.cos(rotation);
      const angle = rotation + (collider.rotY ?? 0) * yawSign;
      const dx = (point.x - centerX) * Math.cos(angle) + (point.z - centerZ) * Math.sin(angle);
      const dz = -(point.x - centerX) * Math.sin(angle) + (point.z - centerZ) * Math.cos(angle);
      const edgeDistance = Math.hypot(
        Math.max(0, Math.abs(dx) - collider.width * sx / 2),
        Math.max(0, Math.abs(dz) - collider.depth * sz / 2),
      );
      // Dense cities add many channel and defense colliders. Check every pair,
      // but construct the expensive assertion only when reporting a violation.
      if (edgeDistance < radius) expect(edgeDistance, `${context} intersects ${prop.id}`).toBeGreaterThanOrEqual(radius);
    }
  }
}

describe('authored world life', () => {
  test('has a versioned, original six-zone scope', () => {
    expect(WORLD_LIFE_VERSION).toBeTruthy();
    expect(ids).toHaveLength(6);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids.every((id) => /^[a-z]+(?:_[a-z]+)+$/.test(id))).toBe(true);
    const untouched = readZone('dawnline_expanse');
    const before = structuredClone(untouched);
    expect(decorateWorldLife(untouched)).toBe(untouched);
    expect(untouched).toEqual(before);
  });

  test.each(ids)('%s stays deterministic and preserves gameplay authoring', (id) => {
    const zone = readZone(id);
    const original = structuredClone(zone);
    decorateWorldLife(zone);
    const first = structuredClone(zone);
    decorateWorldLife(zone);
    expect(zone).toEqual(first);
    const separateRun = readZone(id);
    decorateWorldLife(separateRun);
    expect(separateRun).toEqual(first);

    for (const key of ['spawnPoint', 'npcs', 'enemies', 'zoneTriggers', 'rvrObjectives', 'resourceNodes', 'craftingStations', 'paths'] as const) {
      expect(zone[key], key).toEqual(original[key]);
    }
    expect(zone.props.filter((prop) => !prop.id?.startsWith(`${id}_life_`)))
      .toEqual(original.props.filter((prop) => !prop.id?.startsWith(`${id}_life_`)));
  });

  test.each(ids)('%s has useful population and bounded scene budgets', (id) => {
    const zone = readZone(id);
    decorateWorldLife(zone);
    const props = lifeProps(zone);
    const capital = zone.campaign?.nodeRole === 'capital';
    const actors = zone.ambientLife!.actors!;
    const emitters = zone.ambientLife!.emitters!;
    expect(props.length).toBeGreaterThanOrEqual(capital ? 50 : 25);
    expect(props.length).toBeLessThanOrEqual(capital ? 80 : 40);
    expect(actors.length).toBeGreaterThanOrEqual(capital ? 12 : 8);
    expect(actors.length).toBeLessThanOrEqual(capital ? 20 : 14);
    expect(actors.filter((actor) => actor.kind !== 'bird' && actor.route?.length).length).toBeGreaterThanOrEqual(5);
    expect(new Set(props.map((prop) => prop.kind)).size).toBeGreaterThanOrEqual(8);
    expect(new Set(actors.map((actor) => actor.kind))).toEqual(new Set(capital ? ['citizen', 'guard', 'bird'] : ['citizen', 'guard', 'deer', 'bird']));
    expect(emitters.reduce((sum, emitter) => sum + (emitter.count ?? 0), 0)).toBeLessThanOrEqual(100);
    const allIds = [...props, ...actors, ...emitters].map((entry) => entry.id);
    expect(new Set(allIds).size).toBe(allIds.length);
    for (const point of [...props, ...actors, ...emitters, ...actors.flatMap((actor) => actor.route ?? [])]) {
      expect(Number.isFinite(point.x) && Number.isFinite(point.z)).toBe(true);
      expect(Math.max(Math.abs(point.x), Math.abs(point.z))).toBeLessThan(zone.size / 2 - 8);
    }
    expect(props.some((prop) => Math.hypot(prop.x - zone.spawnPoint!.x, prop.z - zone.spawnPoint!.z) < 30)).toBe(true);
    for (const fire of props.filter((prop) => lifeKind(prop) === 'life_campfire')) {
      expect(emitters.filter((emitter) => emitter.x === fire.x && emitter.z === fire.z).map((entry) => entry.kind)).toEqual(['smoke', 'embers']);
    }
  });

  test.each(ids)('%s keeps road widths and gameplay interactions clear', (id) => {
    const zone = readZone(id);
    decorateWorldLife(zone);
    const protectedPoints = [
      { ...zone.spawnPoint!, radius: 8 },
      ...zone.npcs!.map((entry) => ({ ...entry, radius: 4 })),
      ...zone.rvrObjectives!.map((entry) => ({ ...entry, radius: entry.captureRadius + 1 })),
      ...zone.zoneTriggers!.map((entry) => ({ ...entry, radius: entry.radius + 5 })),
      ...zone.craftingStations!.map((entry) => ({ ...entry, radius: entry.radius + 1 })),
      ...zone.resourceNodes!.map((entry) => ({ ...entry, radius: 3 })),
    ];
    const props = lifeProps(zone);
    for (const prop of props) {
      const radius = lifeRadius(prop);
      for (const point of protectedPoints) {
        expect(Math.hypot(prop.x - point.x, prop.z - point.z), prop.id).toBeGreaterThanOrEqual(point.radius + radius);
      }
      for (const road of zone.paths!) {
        for (let i = 1; i < road.points.length; i += 1) {
          expect(distanceToSegment(prop, road.points[i - 1], road.points[i]), `${prop.id} blocks ${road.id}`)
            .toBeGreaterThanOrEqual(road.width / 2 + radius + 0.75);
        }
      }
      expectOutsideColliders(prop, radius, zone.props.filter((entry) => entry.id !== prop.id), prop.id!);
      for (const other of props.filter((entry) => entry.id !== prop.id)) {
        expect(Math.hypot(prop.x - other.x, prop.z - other.z), `${prop.id} overlaps ${other.id}`)
          .toBeGreaterThanOrEqual(radius + lifeRadius(other));
      }
    }
  });

  test.each(ids)('%s ground actors have unobstructed complete patrol loops', (id) => {
    const zone = readZone(id);
    decorateWorldLife(zone);
    for (const actor of zone.ambientLife!.actors!.filter((entry) => entry.kind !== 'bird')) {
      const radius = actor.kind === 'deer' ? 1.15 : 0.75;
      const route = [actor, ...(actor.route ?? []), actor];
      for (const point of samples(route)) {
        expectOutsideColliders(point, radius, zone.props, actor.id);
        for (const prop of lifeProps(zone)) {
          const distance = Math.hypot(point.x - prop.x, point.z - prop.z);
          if (distance < radius + lifeRadius(prop)) expect(distance, `${actor.id} crosses ${prop.id}`).toBeGreaterThanOrEqual(radius + lifeRadius(prop));
        }
        for (const enemy of zone.enemies) {
          const distance = Math.hypot(point.x - enemy.x, point.z - enemy.z);
          if (distance < radius + Math.max(4, enemy.aggroRange ?? 0)) expect(distance, `${actor.id} enters ${enemy.id}`).toBeGreaterThanOrEqual(radius + Math.max(4, enemy.aggroRange ?? 0));
        }
      }
    }
  }, 30000);

  test('scene clearings survive runtime biome expansion', () => {
    const zone = readZone('brightfen_approach');
    decorateWorldLife(zone);
    const expanded = applyBiomeKits(zone);
    const originalIds = new Set(zone.props.map((prop) => prop.id));
    const vegetation = expanded.props.filter((prop) => !originalIds.has(prop.id));
    expect(vegetation.length).toBeGreaterThan(0);
    for (const kit of zone.biomeKits!) {
      expect(kit.excludeCorridors!.some((entry) => entry.id.includes('_life_'))).toBe(true);
    }
    for (const plant of vegetation) {
      for (const prop of lifeProps(zone)) {
        expect(Math.hypot(plant.x - prop.x, plant.z - prop.z), prop.id).toBeGreaterThan(lifeRadius(prop) + 3);
      }
    }
  });

  test('solid scene furniture has bounded collision while hanging decorations remain passable', () => {
    const zone = readZone('aegis_capital');
    decorateWorldLife(zone);
    const solidKinds = new Set(['life_crate_stack', 'life_barrels', 'life_handcart', 'life_bench', 'life_supply_tent']);
    for (const prop of lifeProps(zone)) {
      expect(Boolean(prop.colliders?.length), prop.kind).toBe(solidKinds.has(lifeKind(prop)));
      const sx = (prop.scale ?? 1) * (prop.scaleX ?? 1);
      const sy = (prop.scale ?? 1) * (prop.scaleY ?? 1);
      const sz = (prop.scale ?? 1) * (prop.scaleZ ?? 1);
      for (const collider of prop.colliders ?? []) {
        expect(collider.minY).toBeDefined();
        expect(collider.maxY).toBeGreaterThan(collider.minY!);
        // Models use fitted local units; the preserved physical height is in world units.
        expect((collider.maxY! - collider.minY!) * sy).toBeLessThanOrEqual(2.5);
        expect(collider.width).toBeGreaterThan(0);
        expect(collider.depth).toBeGreaterThan(0);
        const cornerRadius = Math.hypot((Math.abs(collider.x ?? 0) + collider.width / 2) * sx,
          (Math.abs(collider.z ?? 0) + collider.depth / 2) * sz);
        expect(cornerRadius, prop.kind).toBeLessThan(lifeRadius(prop));
      }
    }
  });
});
