import { readFileSync, existsSync } from 'node:fs';
import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { spawnProps } from '../src/world/Props';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Terrain } from '../src/world/Terrain';
// @ts-expect-error Shared native ESM authoring module.
import { AEGIS_REVIEWED_SCENERY, replaceAegisPrimitiveScenery, reviewedSceneryModelBounds, reviewedSceneryFootprint } from '../scripts/campaign/aegis-reviewed-scenery.mjs';

describe('reviewed Aegis scenery conversion', () => {
  test('uses present delivery models, keeps identities and fits existing scenery envelopes', () => {
    const props = Object.keys(AEGIS_REVIEWED_SCENERY).map((kind, i) => ({
      id: `fixture_${i}`, kind, x: 12, z: 30, rotY: .7, scale: .8,
    }));
    const original = structuredClone(props), zone = { id: 'aegis_capital', props };
    replaceAegisPrimitiveScenery(zone);
    for (const [i, prop] of (zone.props as any[]).entries()) {
      const source = original[i], entry = AEGIS_REVIEWED_SCENERY[source.kind];
      expect(prop.id).toBe(source.id); expect(prop.x).toBe(source.x); expect(prop.z).toBe(source.z);
      expect(prop.rotY).toBe(source.rotY); expect(prop.kind).toMatch(/^aegis_/);
      expect(existsSync(`public/assets/models/${prop.model}`)).toBe(true);
      for (const model of prop.lodModels ?? []) expect(existsSync(`public/assets/models/${model}`), model).toBe(true);
      const box = reviewedSceneryModelBounds(prop.model);
      expect(box).not.toBeNull(); expect(reviewedSceneryFootprint(prop)).not.toBeNull();
      expect(prop.y + box.min.y * prop.scale).toBeCloseTo(0, 6);
      if (entry.envelope) {
        expect(2 * Math.max(Math.abs(box.min.x), Math.abs(box.max.x)) * prop.scale).toBeLessThanOrEqual(entry.envelope[0] * source.scale + 1e-6);
        expect(2 * Math.max(Math.abs(box.min.z), Math.abs(box.max.z)) * prop.scale).toBeLessThanOrEqual(entry.envelope[1] * source.scale + 1e-6);
      }
    }
    const once = structuredClone(zone); replaceAegisPrimitiveScenery(zone); expect(zone).toEqual(once);
  });

  test('preserves real runtime collider and walkable world coordinates through fitting', async () => {
    const definitions = ['life_bench', 'life_crate_stack'].map((kind, i) => ({
      id: `fixture_${kind}`, kind, x: 12, z: 30, y: 6, scale: .8,
      scaleX: 1.2, scaleY: .9, scaleZ: 1.1, rotY: .7,
      colliderSpace: i ? 'model' : undefined,
      colliders: [{ id: `collision_${i}`, x: .3, z: -.2, width: 1.3, depth: .8, minY: -.1, maxY: 1.5, rotY: .4, blocksWhen: 'closed', interactionId: `gate_${i}` }],
      walkableSurfaces: [{ id: `walkable_${i}`, x: .4, z: .3, width: .6, depth: .8, fromY: .5, toY: .8, rotY: .2, axis: 'z' }],
      interaction: { id: `gate_${i}`, type: 'gate', label: 'Preserved interaction', startsOpen: false },
    }));
    const converted = { id: 'aegis_capital', props: structuredClone(definitions) };
    replaceAegisPrimitiveScenery(converted);
    const loader = {
      resolveStaticModel: async (_key: string, model: string) => model,
      loadModel: async () => new THREE.Group(),
      loadModelWithAnimations: async () => ({ object: new THREE.Group(), animations: [] }),
    } as unknown as AssetLoader;
    const terrain = { heightAt: () => 37 } as Terrain;
    const before = await spawnProps(new THREE.Scene(), loader, terrain, definitions as any);
    const after = await spawnProps(new THREE.Scene(), loader, terrain, converted.props as any);
    for (const field of ['colliders', 'walkableSurfaces'] as const) {
      expect(after[field]).toHaveLength(before[field].length);
      for (const [i, item] of before[field].entries()) {
        for (const [key, value] of Object.entries(item)) {
          const actual = (after[field][i] as any)[key];
          if (typeof value === 'number') expect(actual, `${field}.${key}`).toBeCloseTo(value, 7);
          else expect(actual, `${field}.${key}`).toEqual(value);
        }
      }
    }
    expect(converted.props.map(p => p.interaction)).toEqual(definitions.map(p => p.interaction));
  });

  test('keeps missing assets, invisible physics and explicit model choices safe', () => {
    expect(reviewedSceneryModelBounds('missing_reviewed_scenery.glb')).toBeNull();
    const zone = { id: 'aegis_capital', props: [
      { id: 'hidden', kind: 'rock', x: 0, z: 0, visible: false },
      { id: 'explicit', kind: 'life_bench', model: 'custom_bench.glb', x: 1, z: 0 },
      { id: 'water', kind: 'city_water_collision', x: 2, z: 0, visible: false },
    ] };
    const original = structuredClone(zone); replaceAegisPrimitiveScenery(zone); expect(zone).toEqual(original);
    const other = { id: 'riftspire_capital', props: [{ kind: 'life_bench', x: 0, z: 0 }] };
    const otherOriginal = structuredClone(other); replaceAegisPrimitiveScenery(other); expect(other).toEqual(otherOriginal);
  });

  test('makes city resource supplies and water sources explicit without changing harvest mechanics', () => {
    const nodes = [
      { id: 'ore', kind: 'ore', label: 'Aegis Ore Vein', visualPropId: 'ore_prop', xp: 10, professionId: 'salvaging', loot: [{ key: 'craft_scrap_iron', qty: 1 }] },
      { id: 'water', kind: 'water', label: 'Aegis Springwater', visualPropId: 'water_prop', xp: 8, professionId: 'cultivation', loot: [{ key: 'craft_clear_water', qty: 1 }] },
    ];
    const original = structuredClone(nodes);
    const zone = { id: 'aegis_capital', resourceNodes: nodes, props: [
      { id: 'ore_prop', kind: 'pnw_mossy_boulder', x: 0, z: 0 },
      { id: 'water_prop', kind: 'pnw_low_shrub', x: 5, z: 0 },
    ] };
    replaceAegisPrimitiveScenery(zone);
    expect(nodes[0]).toEqual({ ...original[0], label: 'Aegis Ore Shipment' });
    expect(nodes[1]).toEqual(original[1]);
    expect(zone.props[0].kind).toBe('aegis_crate_stack');
    expect(zone.props[1].kind).toBe('aegis_fountain');
    const map = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
    const visible = map.props.filter((p: any) => p.visible !== false && !p.kind.startsWith('path_'));
    expect(visible.filter((p: any) => AEGIS_REVIEWED_SCENERY[p.kind])).toEqual([]);
    expect(map.resourceNodes.filter((n: any) => n.kind === 'ore').every((n: any) => n.label === 'Aegis Ore Shipment')).toBe(true);
  });
});
