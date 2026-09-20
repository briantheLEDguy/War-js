import * as THREE from 'three';
import { expect, test } from 'vitest';
import { CharacterVisibility } from '../src/game/CharacterVisibility';
import { loadRegionalNpc } from '../src/world/RegionalNpcPresentation';

function skinnedCharacter() {
  const object = new THREE.Group(), bone = new THREE.Bone(); bone.name = 'root_bone';
  const geometry = new THREE.BoxGeometry(1, 2, 1);
  geometry.translate(0, 1, 0);
  const vertices = geometry.attributes.position.count;
  geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(new Uint16Array(vertices * 4), 4));
  const weights = new Float32Array(vertices * 4);
  for (let i = 0; i < vertices; i++) weights[i * 4] = 1;
  geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(weights, 4));
  const mesh = new THREE.SkinnedMesh(geometry, new THREE.MeshBasicMaterial());
  mesh.name = 'body'; object.add(bone, mesh); object.updateMatrixWorld(true);
  mesh.bind(new THREE.Skeleton([bone]));
  const idle = new THREE.AnimationClip('idle', 2,
    [new THREE.NumberKeyframeTrack('root_bone.rotation[y]', [0, 1, 2], [0, .05, 0])]);
  return { object, mesh, animations: [idle] };
}

test('offscreen NPCs are hidden unless a shadow camera needs them; turning restores them', () => {
  const scene = new THREE.Scene();
  const actor = new THREE.Mesh(new THREE.BoxGeometry(1, 2, 1), new THREE.MeshBasicMaterial());
  actor.position.set(0, 0, 30); actor.frustumCulled = false;
  scene.add(actor);
  const camera = new THREE.PerspectiveCamera(60, 1, .1, 100);
  const visibility = new CharacterVisibility(scene, [actor]);
  visibility.update(camera); expect(actor.visible).toBe(false);
  camera.rotation.y = Math.PI;
  visibility.update(camera); expect(actor.visible).toBe(true);
  visibility.dispose(); expect(actor.visible).toBe(true);
  camera.rotation.y = 0;
  const light = new THREE.DirectionalLight(); light.castShadow = true;
  light.position.set(0, 10, 30); light.target.position.set(0, 0, 30);
  scene.add(light, light.target);
  const shadows = new CharacterVisibility(scene, [actor]);
  shadows.update(camera); expect(actor.visible).toBe(true);
  const frustum = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4()
    .multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
  expect(actor.frustumCulled).toBe(true);
  expect(frustum.intersectsObject(actor)).toBe(false);
  expect(light.shadow.getFrustum().intersectsObject(actor)).toBe(true);
  shadows.dispose(); expect(actor.frustumCulled).toBe(false);
  expect(actor).not.toHaveProperty('boundingSphere');
});

test('translated animated regional skins retain correct world bounds and switch LOD before their first render', async () => {
  const rigs: ReturnType<typeof skinnedCharacter>[] = [];
  const npc = (await loadRegionalNpc('npc_frontier_test', {
    resolveApprovedAssetModels: async () => ['near.glb', 'middle.glb', 'far.glb'],
    loadModelFull: async () => { const rig = skinnedCharacter(); rigs.push(rig); return rig; },
  }, .25))!;
  const scene = new THREE.Scene(); npc.object.position.set(-413, 0, -257); scene.add(npc.object);
  const camera = new THREE.PerspectiveCamera(60, 1, .1, 1200);
  camera.position.set(-413, 2, -212); camera.lookAt(-413, 1, -257);
  const visibility = new CharacterVisibility(scene, [npc.object]);
  for (const rig of rigs) {
    const world = rig.mesh.boundingSphere!.clone().applyMatrix4(rig.mesh.matrixWorld);
    expect(world.center.x).toBeCloseTo(-413);
    expect(world.center.y).toBeCloseTo(1);
    expect(world.center.z).toBeCloseTo(-257);
  }
  visibility.update(camera); npc.update(.1, camera);
  expect(npc.object.visible).toBe(true);
  expect(npc.object.getCurrentLevel()).toBe(1);
  expect(rigs.map(rig => rig.object.visible)).toEqual([false, true, false]);
  camera.position.z = -157;
  visibility.update(camera); npc.update(.1, camera);
  expect(npc.object.getCurrentLevel()).toBe(2);
  camera.rotation.y = Math.PI;
  visibility.update(camera); npc.update(.1, camera);
  expect(npc.object.visible).toBe(false);
  camera.lookAt(-413, 1, -257); camera.position.z = -252;
  visibility.update(camera); npc.update(.1, camera);
  expect(npc.object.visible).toBe(true);
  expect(npc.object.getCurrentLevel()).toBe(0);
  visibility.dispose(); npc.dispose();
});

test('preexisting stale skin bounds are recomputed after parenting and placement', () => {
  const { object, mesh } = skinnedCharacter();
  const parent = new THREE.Group(), scene = new THREE.Scene();
  parent.position.set(100, 0, -200); object.position.set(12, 0, -18);
  scene.add(parent); parent.add(object);
  // Reproduce an earlier bounds query through the incorrect Object3D-only path.
  object.updateWorldMatrix(true, true);
  mesh.computeBoundingBox();
  const stale = mesh.boundingBox!.clone().applyMatrix4(mesh.matrixWorld).getCenter(new THREE.Vector3());
  expect(stale.x).toBeCloseTo(224);
  expect(stale.z).toBeCloseTo(-436);
  const visibility = new CharacterVisibility(scene, [object]);
  const center = mesh.boundingSphere!.clone().applyMatrix4(mesh.matrixWorld).center;
  expect(center.x).toBeCloseTo(112);
  expect(center.z).toBeCloseTo(-218);
  visibility.dispose(); mesh.skeleton.dispose();
});
