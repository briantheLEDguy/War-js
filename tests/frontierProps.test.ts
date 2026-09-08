import { afterEach, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { AssetLoader } from '../src/game/AssetLoader';
import { FrontierInstances, loadApprovedFrontierProp } from '../src/world/FrontierProps';
import { spawnProps } from '../src/world/Props';
import { Terrain } from '../src/world/Terrain';
import type { PropSpawn } from '../src/world/ZoneLoader';

afterEach(() => vi.restoreAllMocks());
const terrain = new Terrain({ size: 1200, segments: 16, flatTerrain: true });
const tree: PropSpawn = { id: 'oak_1', kind: 'tree', assetKey: 'frontier_sunmeadow_oak_pasture', x: 12, z: -20,
  colliders: [{ width: 2, depth: 2 }], walkableSurfaces: [{ width: 2, depth: 2, fromY: 1, toY: 1, axis: 'x' }] };
function mesh() {
  return new THREE.Mesh(new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, 2, 0, 0, 0, 8, 0], 3)), new THREE.MeshStandardMaterial());
}
function loader(models = ['oak0.glb', 'oak1.glb', 'oak2.glb']) {
  const result = new AssetLoader();
  vi.spyOn(result, 'resolveApprovedAssetModels').mockResolvedValue(models);
  vi.spyOn(result, 'loadModelFull').mockImplementation(async () => ({ object: mesh(), animations: [] }));
  return result;
}

test('frontier props load only approved LODs, preserve editor IDs, transforms and authored collision', async () => {
  const assets = loader(); const scene = new THREE.Scene();
  const result = await spawnProps(scene, assets, terrain, [tree]);
  expect(assets.resolveApprovedAssetModels).toHaveBeenCalledWith(tree.assetKey, 'staticProps');
  expect(result.objects).toHaveLength(1); expect(result.colliders).toHaveLength(1); expect(result.walkableSurfaces).toHaveLength(1);
  const root = result.objects[0].object as THREE.LOD;
  expect(root.isLOD).toBe(true); expect(root.autoUpdate).toBe(false);
  expect(root.levels.map(level => level.distance)).toEqual([0, 30, 90]);
  expect(root.position.toArray()).toEqual([12, 0, -20]); expect(root.rotation.y).toBe(0);
  root.traverse(node => expect(node.userData.worldEditObjectId).toBe('oak_1'));
  assets.dispose(scene);
});

test.each(['unapproved', 'missing-mesh', 'hidden', 'filename-only'])('unavailable %s frontier art creates no fallback, colliders, walkable surfaces or editor objects', async condition => {
  const assets = loader(condition === 'unapproved' ? [] : undefined);
  const fallback = vi.spyOn(AssetLoader.primitives, 'tree');
  if (condition === 'missing-mesh') vi.mocked(assets.loadModelFull).mockImplementation(async (_model, fallback) => ({ object: fallback(), animations: [] }));
  const prop = condition === 'hidden' ? { ...tree, visible: false } : condition === 'filename-only' ? { ...tree, assetKey: undefined, model: 'frontier_unregistered_tree.glb' } : tree;
  const scene = new THREE.Scene(); const result = await spawnProps(scene, assets, terrain, [prop]);
  expect(result.objects).toHaveLength(0); expect(result.colliders).toHaveLength(0);
  expect(result.cameraColliders).toHaveLength(0); expect(result.walkableSurfaces).toHaveLength(0);
  expect(fallback).not.toHaveBeenCalled(); assets.dispose(scene);
});

test('interactive frontier gates retain one authored animation hierarchy', async () => {
  const assets = loader();
  const clip = new THREE.AnimationClip('open', 1, []);
  vi.mocked(assets.loadModelFull).mockImplementation(async () => ({ object: mesh(), animations: [clip] }));
  const loaded = await loadApprovedFrontierProp({ ...tree, interaction: { type: 'gate', id: 'gate' } }, assets);
  expect(loaded?.object.levels).toHaveLength(1); expect(loaded?.animations).toEqual([clip]);
  expect(assets.loadModelFull).toHaveBeenCalledTimes(1); assets.dispose();
});

test('local frontier batches switch LODs, cull distance, restore editing sources and honor suppressed objects', async () => {
  const assets = loader(); const scene = new THREE.Scene();
  const result = await spawnProps(scene, assets, terrain, [{ ...tree, x: 0, z: -10 }]);
  const root = result.objects[0].object as THREE.LOD;
  const instances = new FrontierInstances(scene, result.objects);
  const camera = new THREE.PerspectiveCamera(); camera.position.set(0, 2, 0); camera.updateMatrixWorld(true);
  const batches = () => { const result: THREE.InstancedMesh[] = []; scene.traverse(node => { if ((node as THREE.InstancedMesh).isInstancedMesh) result.push(node as THREE.InstancedMesh); }); return result; };
  instances.update(camera, true, () => false, .25);
  expect(root.visible).toBe(false); expect(batches()).toHaveLength(1);
  expect(root.getCurrentLevel()).toBe(0);
  camera.position.z = 160; camera.updateMatrixWorld(true); instances.update(camera, true, () => false, .25);
  expect(root.getCurrentLevel()).toBe(2); expect(batches()).toHaveLength(1);
  camera.position.z = 1000; camera.updateMatrixWorld(true); instances.update(camera, true, () => false, .25);
  expect(batches()).toHaveLength(0); expect(root.visible).toBe(false);
  instances.update(camera, false, () => false, 0);
  expect(root.visible).toBe(true); expect(root.parent).toBe(scene); expect(root.userData.worldEditObjectId).toBe(tree.id);
  instances.update(camera, false, () => true, .25);
  expect(root.visible).toBe(false); expect(result.colliders[0].sourceObjectId).toBe(tree.id);
  instances.dispose(); assets.dispose(scene);
});
