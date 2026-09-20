import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { loadRegionalNpc } from '../src/world/RegionalNpcPresentation';
import { spawnNpcs } from '../src/world/NpcSpawner';
import type { AssetLoader } from '../src/game/AssetLoader';
import type { Terrain } from '../src/world/Terrain';

function fixture() {
  const rigs: THREE.Group[] = [];
  const loader = {
    resolveApprovedAssetModels: vi.fn(async () => ['close.glb', 'middle.glb', 'far.glb']),
    loadModelFull: vi.fn(async () => {
      const object = new THREE.Group(), mesh = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial());
      mesh.name = 'body'; object.add(mesh); rigs.push(object);
      const clip = new THREE.AnimationClip('idle', 2, [new THREE.NumberKeyframeTrack('body.rotation[y]', [0, 2], [0, 2])]);
      return { object, animations: [clip] };
    }),
  };
  return { rigs, loader };
}

describe('regional local NPC detail and animation', () => {
  test('missing regional art keeps the service available without replacement geometry', async () => {
    const { loader } = fixture(); loader.resolveApprovedAssetModels.mockResolvedValueOnce([]);
    const result = await spawnNpcs(new THREE.Scene(), loader as unknown as AssetLoader,
      { heightAt: () => 0 } as Terrain, [{ id: 'mentor', name: 'Alden Voss', role: 'trainer',
        characterProfileKey: 'npc_frontier_sunmeadow_dwarf_artisan', x: 12, z: 18 }]);
    expect(result.states).toEqual([{ id: 'mentor', name: 'Alden Voss', role: 'trainer',
      position: { x: 12, y: 0, z: 18 } }]);
    expect(result.objects).toHaveLength(0);
    expect(loader.loadModelFull).not.toHaveBeenCalled();
  });

  test('switches all authored LODs without restarting idle, including after visibility culling', async () => {
    const { rigs, loader } = fixture();
    const npc = (await loadRegionalNpc('npc_frontier_sunmeadow_dwarf_artisan', loader, .25))!;
    const camera = new THREE.PerspectiveCamera();
    camera.position.z = 5; npc.update(.1, camera);
    expect(rigs.map(rig => rig.visible)).toEqual([true, false, false]);
    expect(rigs[0].children[0].rotation.y).toBeCloseTo(.6);
    camera.position.z = 40; npc.update(.2, camera);
    expect(rigs.map(rig => rig.visible)).toEqual([false, true, false]);
    expect(rigs[1].children[0].rotation.y).toBeCloseTo(.8);
    expect(rigs[0].children[0].rotation.y).toBeCloseTo(.6);
    camera.position.z = 100; npc.update(.2, camera);
    expect(rigs.map(rig => rig.visible)).toEqual([false, false, true]);
    expect(rigs[2].children[0].rotation.y).toBeCloseTo(1);
    npc.object.visible = false; npc.update(.3, camera);
    expect(rigs[2].children[0].rotation.y).toBeCloseTo(1);
    npc.object.visible = true; camera.position.z = 5; npc.update(.1, camera);
    expect(rigs[0].children[0].rotation.y).toBeCloseTo(1.4);
    npc.dispose(); npc.update(1, camera);
    expect(rigs[0].children[0].rotation.y).toBeCloseTo(0); // Mixer releases its original binding.
  });

  test('skips unavailable levels and does not expose a placeholder when approval is missing', async () => {
    const { loader } = fixture();
    loader.resolveApprovedAssetModels.mockResolvedValueOnce([]);
    expect(await loadRegionalNpc('npc_frontier_missing', loader, 0)).toBeNull();
    expect(loader.loadModelFull).not.toHaveBeenCalled();
    loader.loadModelFull.mockResolvedValueOnce({ object: new THREE.Group(), animations: [] });
    const npc = (await loadRegionalNpc('npc_frontier_available', loader, 0))!;
    expect(npc.object.levels).toHaveLength(2);
    const camera = new THREE.PerspectiveCamera(); npc.update(.1, camera);
    expect(npc.object.levels[0].object.visible).toBe(true);
    npc.dispose();
  });

  test('releases a rig that finishes loading after the game is disposed', async () => {
    const skeleton = new THREE.Skeleton([new THREE.Bone()]);
    const release = vi.spyOn(skeleton, 'dispose');
    const mesh = new THREE.SkinnedMesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial());
    mesh.skeleton = skeleton;
    const object = new THREE.Group(); object.add(mesh);
    let active = true;
    const loader = { resolveApprovedAssetModels: async () => ['close.glb'], loadModelFull: async () => {
      active = false; return { object, animations: [] };
    } };
    expect(await loadRegionalNpc('npc_frontier_available', loader, 0, () => active)).toBeNull();
    expect(release).toHaveBeenCalledOnce();
  });

  test('spawned regional inhabitants retain service identity, floor height and facing', async () => {
    const { loader } = fixture(), scene = new THREE.Scene();
    const spawn = { id: 'regional_craft_mentor', name: 'Alden Voss', title: 'Field Crafting Mentor', role: 'trainer' as const,
      characterProfileKey: 'npc_frontier_sunmeadow_dwarf_artisan', x: 12, y: .6, z: 18, heightMode: 'absolute' as const, rotY: .5 };
    const result = await spawnNpcs(scene, loader as unknown as AssetLoader, { heightAt: () => 42 } as Terrain,
      [spawn], (_x, _z, y) => y!);
    expect(result.states).toEqual([{ id: spawn.id, name: spawn.name, title: spawn.title, role: spawn.role, position: { x: 12, y: .6, z: 18 } }]);
    expect(result.mixers).toHaveLength(0);
    expect(result.presentations).toHaveLength(1);
    expect(result.objects[0]).toBeInstanceOf(THREE.LOD);
    expect(result.objects[0].rotation.y).toBe(.5);
    result.presentations.forEach(npc => npc.dispose());
  });
});
