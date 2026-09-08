import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';
import { loadBuilderAsset, releaseBuilderAssets } from '../src/world/editor/BuilderAssetPresentation';

function loader(models = ['actor_lod0.glb','actor_lod1.glb','actor_lod2.glb']) {
  const geometry = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([0,0,0,1,0,0,0,1,0],3));
  const material = new THREE.MeshStandardMaterial();
  return { geometry, material, resolveApprovedAssetModels: vi.fn(async () => models),
    loadModelFull: vi.fn(async () => {
      const mesh = new THREE.Mesh(geometry,material); mesh.name = 'skin';
      const object = new THREE.Group(); object.add(mesh);
      return { object, animations: [new THREE.AnimationClip('idle',1,[new THREE.NumberKeyframeTrack('skin.rotation[y]',[0,1],[0,.5])])] };
    }) };
}

describe('reviewed GM asset presentation', () => {
  it('loads the correct registry category and animates independently through actual LODs', async () => {
    const assets = loader();
    const actor = await loadBuilderAsset({ assetKey: 'npc_frontier_civilian', assetCategory: 'characterProfiles', defaultAnimation: 'idle' },assets);
    expect(assets.resolveApprovedAssetModels).toHaveBeenCalledWith('npc_frontier_civilian','characterProfiles');
    expect(actor!.object.levels).toHaveLength(3);
    const camera = new THREE.PerspectiveCamera(); camera.position.z=5;camera.updateMatrixWorld();
    actor!.update(.5,camera);
    expect(actor!.object.levels[0].object.getObjectByName('skin')!.rotation.y).toBeCloseTo(.25);
    camera.position.z=100;camera.updateMatrixWorld();actor!.update(.2,camera);
    expect(actor!.object.getCurrentLevel()).toBe(2);
    expect(actor!.object.levels[2].object.getObjectByName('skin')!.rotation.y).toBeCloseTo(.35);
    const disposeGeometry=vi.spyOn(assets.geometry,'dispose'),disposeMaterial=vi.spyOn(assets.material,'dispose');
    const wrapper=new THREE.Group();wrapper.add(actor!.object);releaseBuilderAssets(wrapper);
    expect(wrapper.children).toHaveLength(0);
    expect(disposeGeometry).not.toHaveBeenCalled();expect(disposeMaterial).not.toHaveBeenCalled();
  });
  it('does not replace rejected or missing models with primitives and keeps gates on one hierarchy', async () => {
    const rejected = loader([]);
    expect(await loadBuilderAsset({ assetKey:'frontier_draft',assetCategory:'staticProps' },rejected)).toBeNull();
    expect(rejected.loadModelFull).not.toHaveBeenCalled();
    const missing = loader();missing.loadModelFull.mockImplementation(async () => ({ object:new THREE.Group(),animations:[] }));
    expect(await loadBuilderAsset({ assetKey:'frontier_missing',assetCategory:'staticProps' },missing)).toBeNull();
    const assets=loader();
    const gate=await loadBuilderAsset({ assetKey:'frontier_gate',assetCategory:'staticProps',interaction:{type:'gate'} },assets);
    expect(gate!.object.levels).toHaveLength(1);expect(gate!.animations).toHaveLength(1);gate!.dispose();
  });
});
