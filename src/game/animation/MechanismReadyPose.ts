import * as THREE from 'three';

/** The catapult's construction bind pose is vertical; its authored first fire key is ready. */
export function applyMechanismReadyPose(object: THREE.Object3D, clips: THREE.AnimationClip[]): void {
  const clip = clips.find(clip => clip.name === 'catapult_fire');
  if (!clip) return;
  const mixer = new THREE.AnimationMixer(object);
  mixer.clipAction(clip).play(); mixer.update(0);
  const transforms: Array<{ node: THREE.Object3D; position: THREE.Vector3; rotation: THREE.Quaternion; scale: THREE.Vector3 }> = [];
  object.traverse(node => transforms.push({ node, position: node.position.clone(), rotation: node.quaternion.clone(), scale: node.scale.clone() }));
  // Unbinding restores the construction transforms. Preserve the sampled pose without a live mixer.
  mixer.stopAllAction(); mixer.uncacheRoot(object);
  for (const { node, position, rotation, scale } of transforms) {
    node.position.copy(position); node.quaternion.copy(rotation); node.scale.copy(scale); node.updateMatrix();
  }
  object.updateMatrixWorld(true);
}
