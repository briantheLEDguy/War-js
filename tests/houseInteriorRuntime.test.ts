import * as THREE from 'three';
import { describe, expect, test } from 'vitest';
import { HouseInteriorRuntime } from '../src/game/HouseInteriorRuntime';
import { prefabHouseInteriorVariantForKind } from '../src/world/editor/PrefabCatalog';

describe('house interior runtime', () => {
  test('builds footprint-matched furnished rooms with residents and safe exit portals', () => {
    const scene = new THREE.Scene();
    const runtime = new HouseInteriorRuntime(scene);

    expect(scene.children.filter((child) => child.name.startsWith('house-interior-'))).toHaveLength(2);
    expect(runtime.isActive).toBe(false);

    const small = runtime.enter('small');
    expect(small.width).toBeCloseTo(8.8);
    expect(small.depth).toBeCloseTo(6.4);
    expect(small.group.visible).toBe(true);
    expect(small.colliders).toHaveLength(5);
    expect(small.occupants).toHaveLength(2);
    expect(small.exitPortal).toEqual(expect.objectContaining({
      direction: 'exit',
      interiorVariant: 'small',
      label: 'Leave House',
    }));
    expect(small.group.getObjectByName('plank-floor')).toBeTruthy();
    expect(small.group.getObjectByName('table-top')).toBeTruthy();
    expect(small.group.getObjectByName('bed-frame')).toBeTruthy();
    expect(small.group.getObjectByName('hearth-base')).toBeTruthy();
    expect(small.spawn.x).toBeGreaterThan(small.anchor.x - small.width / 2);
    expect(small.spawn.x).toBeLessThan(small.anchor.x + small.width / 2);
    expect(small.spawn.z).toBeGreaterThan(small.anchor.z - small.depth / 2);
    expect(small.spawn.z).toBeLessThan(small.anchor.z + small.depth / 2);

    const large = runtime.enter('large');
    expect(small.group.visible).toBe(false);
    expect(large.width).toBeCloseTo(11);
    expect(large.depth).toBeCloseTo(7.8);
    expect(large.occupants).toHaveLength(3);
    expect(large.group.getObjectByName('writing-desk')).toBeTruthy();

    runtime.deactivate();
    expect(runtime.isActive).toBe(false);
    expect(large.group.visible).toBe(false);
    runtime.dispose(scene);
    expect(scene.children.filter((child) => child.name.startsWith('house-interior-'))).toHaveLength(0);
  });

  test('maps generated and GM house kinds onto matching interior sizes', () => {
    expect(prefabHouseInteriorVariantForKind('building')).toBe('small');
    expect(prefabHouseInteriorVariantForKind('town_house_1')).toBe('small');
    expect(prefabHouseInteriorVariantForKind('rift_house')).toBe('large');
    expect(prefabHouseInteriorVariantForKind('town_house_2')).toBe('large');
    expect(prefabHouseInteriorVariantForKind('town_roof')).toBeUndefined();
  });
});
