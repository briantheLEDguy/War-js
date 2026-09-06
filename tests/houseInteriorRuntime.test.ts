import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { HouseInteriorRuntime } from '../src/game/HouseInteriorRuntime';
import type { AssetLoader } from '../src/game/AssetLoader';
import { prefabHouseInteriorVariantForKind } from '../src/world/editor/PrefabCatalog';

describe('house interior runtime', () => {
  test('loads public rooms once with furniture and unobstructed return positions', async () => {
    const runtime = new HouseInteriorRuntime(new THREE.Scene());
    let loads = 0;
    const loader = {
      loadModel: async () => { loads++; return new THREE.Group(); },
      resolveCharacterModel: async () => null,
      loadModelFull: async () => { loads++; return { object: new THREE.Group(), animations: [] }; },
    } as unknown as AssetLoader;
    await runtime.loadCityRooms(loader);
    const firstLoads = loads;
    await runtime.loadCityRooms(loader);
    expect(loads).toBe(firstLoads);
    for (const variant of ['tavern', 'shop', 'chapel', 'civic'] as const) {
      const room = runtime.enter(variant);
      expect(room.variant).toBe(variant);
      expect(room.colliders.length).toBeGreaterThan(5);
      expect(room.exitPortal.label).toBe('Return to the city');
      for (const c of room.colliders) {
        expect(Math.abs(room.spawn.x - c.x) > c.width / 2 + .4 || Math.abs(room.spawn.z - c.z) > c.depth / 2 + .4).toBe(true);
      }
    }
  });
  test('replaces every city resident without changing identity, placement or adult proportions', async () => {
    const runtime = new HouseInteriorRuntime(new THREE.Scene());
    const original = runtime.enter('large').occupants.map(npc => structuredClone(npc));
    runtime.deactivate();
    const models: string[] = [];
    const loader = {
      loadModel: async () => new THREE.Group(),
      resolveCharacterModel: async () => null,
      loadModelFull: async (model: string) => {
        models.push(model);
        const object = new THREE.Group();
        object.userData.reviewedResident = true;
        return { object, animations: [new THREE.AnimationClip('idle', 2, [
          new THREE.NumberKeyframeTrack('.position[y]', [0, 1, 2], [0, .1, 0]),
        ])] };
      },
    } as unknown as AssetLoader;
    await Promise.all([runtime.loadCityRooms(loader), runtime.loadCityRooms(loader)]);
    expect(models).toHaveLength(13);
    expect(models.every(model => /^chr_aegis_people_.*_lod1\.glb$/.test(model))).toBe(true);
    const large = runtime.enter('large');
    expect(large.occupants).toEqual(original);
    for (const variant of ['small', 'large', 'tavern', 'shop', 'chapel', 'civic'] as const) {
      const room = runtime.enter(variant);
      for (const npc of room.occupants) {
        const person = room.group.getObjectByName(npc.id)!;
        expect(person.userData.reviewedResident).toBe(true);
        expect(person.scale.toArray()).toEqual([1, 1, 1]);
        expect(person.position.x + room.anchor.x).toBe(npc.position.x);
        expect(person.position.z + room.anchor.z).toBe(npc.position.z);
      }
    }
    const person = runtime.enter('small').group.getObjectByName('small-resident-1')!;
    const before = person.position.y;
    runtime.update(.20);
    expect(person.position.y).not.toBe(before);
    runtime.deactivate();
    const hidden = person.position.y;
    runtime.update(.20);
    expect(person.position.y).toBe(hidden);
  });

  test('does not attach resident models after disposal during asynchronous loading', async () => {
    const scene = new THREE.Scene();
    const runtime = new HouseInteriorRuntime(scene);
    let finish: (() => void) | undefined;
    const wait = new Promise<void>(resolve => { finish = resolve; });
    let residentStarted: (() => void) | undefined;
    const started = new Promise<void>(resolve => { residentStarted = resolve; });
    let modelLoads = 0;
    const loader = {
      loadModel: async () => new THREE.Group(),
      resolveCharacterModel: async () => { residentStarted!(); await wait; return null; },
      loadModelFull: async () => { modelLoads++; return { object: new THREE.Group(), animations: [] }; },
    } as unknown as AssetLoader;
    const loading = runtime.loadCityRooms(loader);
    await started;
    runtime.dispose(scene);
    finish!();
    await loading;
    expect(scene.children).toHaveLength(0);
    expect(modelLoads).toBe(0);
  });

  test('releases cloned resident bone textures without disposing cached geometry or materials', async () => {
    const scene = new THREE.Scene(), runtime = new HouseInteriorRuntime(scene);
    const geometry = new THREE.BufferGeometry(), material = new THREE.MeshBasicMaterial();
    const geometryDisposal = vi.spyOn(geometry, 'dispose'), materialDisposal = vi.spyOn(material, 'dispose');
    const skeletons: THREE.Skeleton[] = [];
    const loader = {
      loadModel: async () => new THREE.Group(), resolveCharacterModel: async () => null,
      loadModelFull: async () => {
        const object = new THREE.Group(), bone = new THREE.Bone();
        const mesh = new THREE.SkinnedMesh(geometry, material);
        mesh.add(bone); mesh.bind(new THREE.Skeleton([bone]));
        mesh.skeleton.computeBoneTexture(); skeletons.push(mesh.skeleton); object.add(mesh);
        return { object, animations: [] };
      },
    } as unknown as AssetLoader;
    await runtime.loadCityRooms(loader);
    expect(skeletons).toHaveLength(13);
    runtime.dispose(scene);
    expect(skeletons.every(skeleton => skeleton.boneTexture === null)).toBe(true);
    expect(geometryDisposal).not.toHaveBeenCalled(); expect(materialDisposal).not.toHaveBeenCalled();
  });

  test('releases a late cloned skeleton when disposal happens during model loading', async () => {
    const scene = new THREE.Scene(), runtime = new HouseInteriorRuntime(scene);
    const bone = new THREE.Bone(), mesh = new THREE.SkinnedMesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial());
    mesh.add(bone); mesh.bind(new THREE.Skeleton([bone])); mesh.skeleton.computeBoneTexture();
    let resolveModel: ((value: { object: THREE.Object3D; animations: THREE.AnimationClip[] }) => void) | undefined;
    let markStarted: (() => void) | undefined;
    const started = new Promise<void>(resolve => { markStarted = resolve; });
    const pending = new Promise<{ object: THREE.Object3D; animations: THREE.AnimationClip[] }>(resolve => { resolveModel = resolve; });
    const loader = {
      loadModel: async () => new THREE.Group(), resolveCharacterModel: async () => null,
      loadModelFull: async () => { markStarted!(); return pending; },
    } as unknown as AssetLoader;
    const loading = runtime.loadCityRooms(loader);
    await started; runtime.dispose(scene); resolveModel!({ object: mesh, animations: [] }); await loading;
    expect(mesh.skeleton.boneTexture).toBeNull(); expect(scene.children).toHaveLength(0);
  });
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
