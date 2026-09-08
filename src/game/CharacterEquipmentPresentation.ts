import * as THREE from 'three';

/** Shared visual binding utilities. No movement, combat, services or store dependencies. */
export function sanitizePlayerAnimationClip(clip: THREE.AnimationClip): THREE.AnimationClip {
  const tracks = clip.tracks.filter((track) => {
    const [targetName, propertyName] = track.name.split('.');
    if (targetName === 'root') return false;
    return propertyName !== 'scale';
  });
  if (tracks.length === clip.tracks.length) return clip;
  return new THREE.AnimationClip(clip.name, clip.duration, tracks, clip.blendMode);
}

export function prepareEquipmentOverlay(object: THREE.Object3D): void {
  object.position.set(0, 0, 0);
  object.rotation.set(0, 0, 0);
  object.scale.set(1, 1, 1);
  object.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;

    mesh.visible = true;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;

    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of materials) {
      if (!mat) continue;
      mat.side = THREE.DoubleSide;
      mat.needsUpdate = true;
    }
  });
}

export function findFirstSkeleton(root: THREE.Object3D): THREE.Skeleton | null {
  let skeleton: THREE.Skeleton | null = null;
  root.traverse((node) => {
    if (skeleton) return;
    const mesh = node as THREE.SkinnedMesh;
    if (mesh.isSkinnedMesh) skeleton = mesh.skeleton;
  });
  return skeleton;
}

export function bindSkinnedOverlayToPlayer(
  overlay: THREE.Object3D,
  targetSkeleton: THREE.Skeleton | null,
): boolean {
  if (!targetSkeleton) return false;
  const targetBones = new Map(
    targetSkeleton.bones.map((bone) => [normalizeBoneName(bone.name), bone]),
  );
  let rebound = false;

  overlay.traverse((node) => {
    const mesh = node as THREE.SkinnedMesh;
    if (!mesh.isSkinnedMesh) return;

    const mappedBones = mesh.skeleton.bones.map((bone) =>
      targetBones.get(normalizeBoneName(bone.name)),
    );
    if (mappedBones.some((bone) => !bone)) return;

    const skeleton = new THREE.Skeleton(
      mappedBones as THREE.Bone[],
      mesh.skeleton.boneInverses,
    );
    mesh.bind(skeleton, mesh.bindMatrix);
    mesh.frustumCulled = false;
    rebound = true;
  });

  return rebound;
}

export function normalizeBoneName(name: string): string {
  return name.replace(/\.\d+$/u, '');
}

export function applyBodyRegionMask(root: THREE.Object3D, hiddenRegions: Set<string>): void {
  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh || isEquipmentAttachment(root, node)) return;

    const region = typeof node.userData?.bodyRegion === 'string'
      ? node.userData.bodyRegion
      : null;
    if (!region) return;
    mesh.visible = !hiddenRegions.has(region);
  });
}

export function isEquipmentAttachment(root: THREE.Object3D, node: THREE.Object3D): boolean {
  let current: THREE.Object3D | null = node;
  while (current && current !== root) {
    if (current.userData.equipmentOverlay || current.userData.equipmentBaseBody) {
      return true;
    }
    current = current.parent;
  }
  return false;
}
