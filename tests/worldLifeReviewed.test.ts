import { afterEach, describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { clone as cloneSkeleton } from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { AssetLoader } from '../src/game/AssetLoader';
import { WorldLife, WORLD_LIFE_LIMITS } from '../src/world/WorldLife';
import { AEGIS_AMBIENT_GUARD_PROFILES, worldLifeCharacterProfile } from '../src/world/worldLifeModels';
import type { WorldLifeActorSpawn } from '../src/world/worldLifeTypes';

const lives: WorldLife[] = [];
const templates: THREE.Group[] = [];
function fixture() {
  const group = new THREE.Group();
  const root = new THREE.Bone(); root.name = 'root';
  const leg = new THREE.Bone(); leg.name = 'thigh_L'; root.add(leg);
  const geometry = new THREE.BoxGeometry(.2, 1, .2);
  const joints = new Uint16Array(geometry.attributes.position.count * 4);
  const weights = new Float32Array(joints.length);
  for (let i = 0; i < weights.length; i += 4) weights[i] = 1;
  geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(joints, 4));
  geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(weights, 4));
  const mesh = new THREE.SkinnedMesh(geometry, new THREE.MeshBasicMaterial());
  group.add(root, mesh); mesh.bind(new THREE.Skeleton([leg]));
  templates.push(group);
  const frames = (amount: number) => [0, amount, -amount, 0].flatMap(x => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), x).toArray());
  return { group, clips: [new THREE.AnimationClip('idle', 1, [new THREE.QuaternionKeyframeTrack('thigh_L.quaternion', [0, .3, .7, 1], frames(.02))]),
    new THREE.AnimationClip('walk', 1, [new THREE.QuaternionKeyframeTrack('thigh_L.quaternion', [0, .3, .7, 1], frames(.6))])] };
}
function create(actors: WorldLifeActorSpawn[], loader: Partial<AssetLoader>, realm: 'aegis' | 'riftbound' = 'aegis') {
  const life = new WorldLife(new THREE.Scene(), { actors, emitters: [] }, realm, () => 0, [], loader as AssetLoader);
  lives.push(life); return life;
}
const guard = (id = 'patrol', variant = 0): WorldLifeActorSpawn => ({ id, kind: 'guard', variant, x: 0, z: 0,
  route: [{ x: 0, z: 40 }], pauseSeconds: 0, speed: 1 });

afterEach(() => {
  for (const life of lives.splice(0)) life.dispose();
  for (const root of templates.splice(0)) root.traverse(node => {
    if (node instanceof THREE.SkinnedMesh) { node.geometry.dispose(); (node.material as THREE.Material).dispose(); node.skeleton.dispose(); }
  });
  vi.restoreAllMocks();
});

describe('reviewed ambient humanoids', () => {
  test('uses all four reviewed patrol profiles, two civilian profiles and no Aegis override for wildlife or Riftbound', () => {
    expect([0, 1, 2, 3].map(variant => worldLifeCharacterProfile(guard('patrol', variant), 'aegis'))).toEqual(AEGIS_AMBIENT_GUARD_PROFILES);
    expect(worldLifeCharacterProfile({ ...guard(), kind: 'citizen', variant: 0 }, 'aegis')).toBe('npc_aegis_people_civilian_male_walk');
    expect(worldLifeCharacterProfile({ ...guard(), kind: 'citizen', variant: 1 }, 'aegis')).toBe('npc_aegis_people_civilian_female_walk');
    expect(worldLifeCharacterProfile({ ...guard(), kind: 'bird' }, 'aegis')).toBeNull();
    expect(worldLifeCharacterProfile(guard(), 'riftbound')).toBeNull();
  });

  test('loads reviewed models without flashing a primitive, animates walking and skips distant rig updates', async () => {
    const { group, clips } = fixture();
    const loader = {
      resolveCharacterAsset: vi.fn(async (profile: string) => ({ model: `${profile}.glb` })),
      loadModelWithAnimations: vi.fn(async () => ({ object: cloneSkeleton(group), animations: clips })),
    };
    const life = create([guard()], loader);
    const patrol = life.group.getObjectByName('patrol')!;
    expect(patrol.children).toHaveLength(0);
    await life.ready;
    expect(patrol.userData.characterModel).toBe('npc_aegis_city_guard_standard.glb');
    expect(patrol.getObjectByName('leg-left')).toBeUndefined();
    const bone = patrol.getObjectByName('thigh_L')!;
    life.update(.1, { x: 0, z: 0 }, 100);
    life.update(.3, { x: 0, z: 0 }, 100);
    const moving = bone.quaternion.clone();
    life.update(.2, { x: 0, z: 0 }, 100);
    expect(bone.quaternion.angleTo(moving)).toBeGreaterThan(.05);
    const nearby = bone.quaternion.clone();
    life.update(.001, { x: 0, z: 0 }, 100);
    expect(bone.quaternion.equals(nearby)).toBe(true);
    life.update(1, { x: 1000, z: 0 }, 100);
    expect(patrol.visible).toBe(false);
    expect(bone.quaternion.equals(nearby)).toBe(true);
    life.update(0, { x: 0, z: 0 }, 100);
    expect(bone.quaternion.angleTo(nearby)).toBeGreaterThan(.01);
  });

  test('keeps missing or rejected assets playable through the local fallback without bypassing registry approval', async () => {
    const load = vi.fn(async () => { throw new Error('unavailable'); });
    const rejected = create([guard('rejected')], { resolveCharacterAsset: async () => null, loadModelWithAnimations: load });
    await rejected.ready;
    expect(load).not.toHaveBeenCalled();
    expect(rejected.group.getObjectByName('leg-left')).toBeDefined();
    const missing = create([guard('missing')], { resolveCharacterAsset: async () => ({ model: 'missing.glb' }), loadModelWithAnimations: load });
    await missing.ready;
    expect(missing.group.getObjectByName('leg-left')).toBeDefined();
    expect(() => missing.update(1, { x: 0, z: 0 }, 100)).not.toThrow();
  });

  test('does not slide a reviewed idle-only resident whose leg bones have no usable skin weights', async () => {
    const { group, clips } = fixture();
    const life = create([{ ...guard('idle-only'), kind: 'citizen', x: 7, z: 9 }], {
      resolveCharacterAsset: async () => ({ model: 'idle-only.glb', skeletonId: 'aegis_people_v1' }),
      loadModelWithAnimations: async () => ({ object: cloneSkeleton(group), animations: clips.slice(0, 1) }),
    });
    await life.ready;
    life.update(10, { x: 7, z: 9 }, 100);
    const actor = life.group.getObjectByName('idle-only')!;
    expect(actor.userData.characterModel).toBe('idle-only.glb');
    expect([actor.position.x, actor.position.z]).toEqual([7, 9]);
  });

  test('limits concurrent loads and ignores pending replacements after disposal', async () => {
    const { group, clips } = fixture();
    const pending: Array<() => void> = [];
    const skeletonDisposals: ReturnType<typeof vi.spyOn>[] = [];
    const load = vi.fn(() => new Promise<{ object: THREE.Object3D; animations: THREE.AnimationClip[] }>(resolve => {
      const object = cloneSkeleton(group);
      object.traverse(node => { if (node instanceof THREE.SkinnedMesh) skeletonDisposals.push(vi.spyOn(node.skeleton, 'dispose')); });
      pending.push(() => resolve({ object, animations: clips }));
    }));
    const life = create(Array.from({ length: 8 }, (_, i) => guard(`patrol-${i}`, i)), {
      resolveCharacterAsset: async () => ({ model: 'shared.glb' }), loadModelWithAnimations: load,
    });
    await vi.waitFor(() => expect(load).toHaveBeenCalledTimes(WORLD_LIFE_LIMITS.concurrentModelLoads));
    life.dispose();
    pending.forEach(resolve => resolve());
    await life.ready;
    expect(load).toHaveBeenCalledTimes(WORLD_LIFE_LIMITS.concurrentModelLoads);
    expect(life.group.children).toHaveLength(0);
    skeletonDisposals.forEach(dispose => expect(dispose).toHaveBeenCalledTimes(1));
  });

  test('disposes private rigs once while preserving loader-shared geometry and materials for other consumers', async () => {
    const { group, clips } = fixture();
    const mesh = group.children.find(node => node instanceof THREE.SkinnedMesh) as THREE.SkinnedMesh;
    const geometryDispose = vi.spyOn(mesh.geometry, 'dispose');
    const materialDispose = vi.spyOn(mesh.material as THREE.Material, 'dispose');
    const life = create([guard('first'), guard('second')], {
      resolveCharacterAsset: async () => ({ model: 'shared.glb' }),
      loadModelWithAnimations: async () => ({ object: cloneSkeleton(group), animations: clips }),
    });
    await life.ready;
    const skeletons = new Set<THREE.Skeleton>();
    life.group.traverse(node => { if (node instanceof THREE.SkinnedMesh) skeletons.add(node.skeleton); });
    expect(skeletons.size).toBe(2);
    const disposals = [...skeletons].map(skeleton => vi.spyOn(skeleton, 'dispose'));
    life.dispose(); life.dispose();
    disposals.forEach(dispose => expect(dispose).toHaveBeenCalledTimes(1));
    expect(geometryDispose).not.toHaveBeenCalled();
    expect(materialDispose).not.toHaveBeenCalled();
  });
});
