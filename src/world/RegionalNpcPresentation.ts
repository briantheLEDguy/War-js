import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';

export interface RegionalNpcPresentation {
  object: THREE.LOD;
  update(dt: number, camera: THREE.Camera): void;
  dispose(): void;
}

/** Regional inhabitants retain their own fitted outfit, skeleton and embedded idle at each LOD. */
export async function loadRegionalNpc(profile: string,
  loader: Pick<AssetLoader, 'resolveApprovedAssetModels' | 'loadModelFull'>,
  phase: number, active: () => boolean = () => true): Promise<RegionalNpcPresentation | null> {
  const models = await loader.resolveApprovedAssetModels(profile, 'characterProfiles');
  if (!models.length || !active()) return null;
  const object = new THREE.LOD(); object.autoUpdate = false;
  const clips: Array<{ mixer: THREE.AnimationMixer; duration: number }> = [];
  let elapsed = 0, disposed = false;
  const releaseRig = (root: THREE.Object3D) => {
    const skeletons = new Set<THREE.Skeleton>();
    root.traverse(node => { if ((node as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((node as THREE.SkinnedMesh).skeleton); });
    skeletons.forEach(skeleton => skeleton.dispose());
  };
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    for (const { mixer } of clips) { mixer.stopAllAction(); mixer.uncacheRoot(mixer.getRoot()); }
    releaseRig(object); object.removeFromParent();
  };
  try {
    for (const [index, model] of models.entries()) {
      const loaded = await loader.loadModelFull(model, () => new THREE.Group());
      if (!active()) { releaseRig(loaded.object); dispose(); return null; }
      let meshCount = 0;
      loaded.object.traverse(node => { if ((node as THREE.Mesh).isMesh) meshCount++; });
      const idle = loaded.animations.find(clip => clip.name.toLowerCase() === 'idle');
      // An unusable level cannot silently become an unanimated replacement.
      if (!meshCount || !idle) { releaseRig(loaded.object); continue; }
      object.addLevel(loaded.object, [0, 30, 85][Math.min(index, 2)], .12);
      const mixer = new THREE.AnimationMixer(loaded.object);
      mixer.clipAction(idle).setLoop(THREE.LoopRepeat, Infinity).play();
      mixer.setTime(phase * idle.duration);
      clips.push({ mixer, duration: idle.duration });
    }
  } catch { dispose(); return null; }
  if (!object.levels.length) { dispose(); return null; }
  object.levels.forEach((level, index) => { level.object.visible = index === 0; });
  return { object, dispose, update(dt, camera) {
    if (disposed) return;
    elapsed += dt;
    if (!object.visible) return;
    object.updateWorldMatrix(true, false); camera.updateWorldMatrix(true, false);
    object.update(camera);
    // Hidden levels keep the same timeline without evaluating every skeleton.
    for (const [index, { mixer, duration }] of clips.entries()) {
      if (object.levels[index].object.visible) mixer.setTime(elapsed + phase * duration);
    }
  } };
}
