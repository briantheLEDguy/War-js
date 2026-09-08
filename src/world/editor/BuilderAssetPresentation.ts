import * as THREE from 'three';
import type { AssetLoader } from '../../game/AssetLoader';
import type { WorldPropObject } from '../../services/types';
import { frontierPropDistances } from '../FrontierProps';
import { BuilderGroundSurface } from './BuilderGroundSurface';

type Placement = Pick<WorldPropObject, 'assetKey' | 'assetCategory' | 'defaultAnimation' | 'modelOffset' | 'groundSurface'> & {
  interaction?: { type: 'gate' | 'house_portal' };
};
export interface BuilderAssetPresentation {
  object: THREE.LOD;
  animations: THREE.AnimationClip[];
  update(dt: number, camera: THREE.Camera): void;
  groundHeightAt(x: number, z: number, ceiling: number): number | null;
  dispose(): void;
}
const presentations = new WeakMap<THREE.Object3D, BuilderAssetPresentation>();

/** GM stamps use the same hash-verified registry/QC boundary as the completed world. */
export async function loadBuilderAsset(placement: Placement,
  loader: Pick<AssetLoader, 'resolveApprovedAssetModels' | 'loadModelFull'>): Promise<BuilderAssetPresentation | null> {
  if (!placement.assetKey || !placement.assetCategory) return null;
  const models = await loader.resolveApprovedAssetModels(placement.assetKey, placement.assetCategory);
  if (!models.length) return null;
  const object = new THREE.LOD();
  const mixers: Array<THREE.AnimationMixer | null> = [];
  const distances = placement.assetCategory === 'characterProfiles' ? [0, 30, 85] : frontierPropDistances(placement.assetKey).lod;
  let animations: THREE.AnimationClip[] = [];
  let disposed = false;
  let animationTime = 0;
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    for (const mixer of mixers) { mixer?.stopAllAction(); if (mixer) mixer.uncacheRoot(mixer.getRoot()); }
    const skeletons = new Set<THREE.Skeleton>();
    object.traverse(node => { if ((node as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((node as THREE.SkinnedMesh).skeleton); });
    for (const skeleton of skeletons) skeleton.dispose();
    object.removeFromParent();
  };
  try {
    for (const [index, model] of models.entries()) {
      const loaded = await loader.loadModelFull(model, () => new THREE.Group());
      let meshes = 0;
      loaded.object.traverse(node => {
        if (!(node as THREE.Mesh).isMesh) return;
        meshes++;
        node.userData.builderBorrowedResources = true;
      });
      if (!meshes) throw new Error('Reviewed builder model failed to load');
      if (placement.modelOffset) loaded.object.position.add(new THREE.Vector3().copy(placement.modelOffset));
      object.addLevel(loaded.object, distances[Math.min(index, distances.length - 1)], .12);
      if (!index) animations = loaded.animations;
      const clip = !placement.interaction && loaded.animations.find(clip => clip.name === placement.defaultAnimation);
      const mixer = clip ? new THREE.AnimationMixer(loaded.object) : null;
      if (clip && mixer) { mixer.clipAction(clip).play(); mixer.update(0); }
      mixers.push(mixer);
      if (placement.interaction) break;
    }
  } catch { dispose(); return null; }
  object.levels.forEach((level, index) => { level.object.visible = index === 0; });
  const ground = placement.groundSurface === 'mesh' ? new BuilderGroundSurface(object, object.levels[0].object) : null;
  const presentation: BuilderAssetPresentation = { object, animations, dispose,
    groundHeightAt: (x, z, ceiling) => disposed ? null : ground?.heightAt(x, z, ceiling) ?? null,
    update(dt, camera) {
      if (disposed) return;
      animationTime += dt;
      object.update(camera);
      for (const [index, mixer] of mixers.entries()) if (object.levels[index].object.visible) mixer?.setTime(animationTime);
    } };
  object.userData.builderApprovedAsset = placement.assetKey;
  presentations.set(object, presentation);
  return presentation;
}

export function releaseBuilderAssets(root: THREE.Object3D): void {
  const found: BuilderAssetPresentation[] = [];
  root.traverse(node => { const presentation = presentations.get(node); if (presentation) found.push(presentation); });
  for (const presentation of found) presentation.dispose();
}
