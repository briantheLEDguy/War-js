import * as THREE from 'three';

const STANCE = .6;
const STRIDE = .48;
export const CIVIC_WALK_SPEED = .9;
export const CIVIC_WALK_DURATION = STRIDE / (STANCE * CIVIC_WALK_SPEED);
interface RestBone {
  bone: THREE.Bone;
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
  scale: THREE.Vector3;
  modelPosition: THREE.Vector3;
  modelQuaternion: THREE.Quaternion;
}

/** Bake the civic rig's own rest axes into a gentle two-bone walk. During stance
 * a foot travels backward at exactly the authored forward speed, avoiding skating. */
export function createCivicWalkClip(root: THREE.Object3D): THREE.AnimationClip | null {
  const weightedLegs = new Set<string>();
  root.traverse(node => {
    if (!(node instanceof THREE.SkinnedMesh)) return;
    const joints = node.geometry.getAttribute('skinIndex'), weights = node.geometry.getAttribute('skinWeight');
    if (!joints || !weights) return;
    for (let vertex = 0; vertex < joints.count; vertex++) for (let channel = 0; channel < 4; channel++) {
      if (weights.getComponent(vertex, channel) <= .05) continue;
      const name = node.skeleton.bones[joints.getComponent(vertex, channel)]?.name;
      if (name && /^(thigh|shin|foot)_[LR]$/.test(name)) weightedLegs.add(name);
    }
  });
  // Idle-only civic releases may contain unweighted leg bones. Keep those residents
  // stationary instead of pretending that invisible bone motion is a usable walk.
  if (['L', 'R'].some(side => ['thigh', 'shin', 'foot'].some(part => !weightedLegs.has(`${part}_${side}`)))) return null;
  root.updateMatrixWorld(true);
  const inverseRoot = root.matrixWorld.clone().invert();
  const rootQuaternion = root.getWorldQuaternion(new THREE.Quaternion());
  const inverseRootQuaternion = rootQuaternion.clone().invert();
  const bones = new Map<string, RestBone>();
  root.traverse(node => {
    if (!(node as THREE.Bone).isBone) return;
    bones.set(node.name, { bone: node as THREE.Bone, position: node.position.clone(), quaternion: node.quaternion.clone(),
      scale: node.scale.clone(), modelPosition: node.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverseRoot),
      modelQuaternion: inverseRootQuaternion.clone().multiply(node.getWorldQuaternion(new THREE.Quaternion())) });
  });
  const names = ['hips', ...['L', 'R'].flatMap(side => [`thigh_${side}`, `shin_${side}`, `foot_${side}`, `upper_arm_${side}`])];
  if (names.some(name => !bones.has(name))) return null;
  const restore = () => {
    for (const rest of bones.values()) {
      rest.bone.position.copy(rest.position); rest.bone.quaternion.copy(rest.quaternion); rest.bone.scale.copy(rest.scale);
    }
    root.updateMatrixWorld(true);
  };
  const modelQuaternion = (rest: RestBone, desired: THREE.Quaternion) => {
    const parentInverse = rest.bone.parent!.getWorldQuaternion(new THREE.Quaternion()).invert();
    rest.bone.quaternion.copy(parentInverse.multiply(rootQuaternion.clone().multiply(desired)));
    rest.bone.updateWorldMatrix(false, true);
  };
  const times: number[] = [];
  const positions = new Map<string, number[]>(), rotations = new Map<string, number[]>();
  for (const name of bones.keys()) { positions.set(name, []); rotations.set(name, []); }
  for (let frame = 0; frame <= 48; frame++) {
    restore();
    const phase = frame / 48;
    times.push(phase * CIVIC_WALK_DURATION);
    const hips = bones.get('hips')!;
    // Slight knee flexion provides enough reach for a planted heel without stretching the legs.
    hips.bone.position.y -= .06;
    root.updateMatrixWorld(true);
    for (const [side, offset] of [['L', 0], ['R', .5]] as const) {
      const thigh = bones.get(`thigh_${side}`)!, shin = bones.get(`shin_${side}`)!, foot = bones.get(`foot_${side}`)!;
      const p = (phase + offset) % 1;
      const swing = p >= STANCE;
      const progress = swing ? (p - STANCE) / (1 - STANCE) : p / STANCE;
      const target = foot.modelPosition.clone();
      target.z += swing ? -STRIDE / 2 + STRIDE * (progress * progress * (3 - 2 * progress)) : STRIDE / 2 - STRIDE * progress;
      target.y += swing ? .09 * Math.sin(progress * Math.PI) : 0;
      const hip = thigh.bone.getWorldPosition(new THREE.Vector3()).applyMatrix4(inverseRoot);
      const upperLength = thigh.modelPosition.distanceTo(shin.modelPosition);
      const lowerLength = shin.modelPosition.distanceTo(foot.modelPosition);
      const direction = target.clone().sub(hip);
      const distance = THREE.MathUtils.clamp(direction.length(), .01, upperLength + lowerLength - .0001);
      direction.normalize();
      const along = (upperLength ** 2 - lowerLength ** 2 + distance ** 2) / (2 * distance);
      const bend = new THREE.Vector3(0, 0, 1).addScaledVector(direction, -direction.z).normalize();
      const knee = hip.clone().addScaledVector(direction, along).addScaledVector(bend, Math.sqrt(Math.max(0, upperLength ** 2 - along ** 2)));
      const upperDelta = new THREE.Quaternion().setFromUnitVectors(
        shin.modelPosition.clone().sub(thigh.modelPosition).normalize(), knee.clone().sub(hip).normalize());
      modelQuaternion(thigh, upperDelta.multiply(thigh.modelQuaternion));
      const lowerDelta = new THREE.Quaternion().setFromUnitVectors(
        foot.modelPosition.clone().sub(shin.modelPosition).normalize(), target.clone().sub(knee).normalize());
      modelQuaternion(shin, lowerDelta.multiply(shin.modelQuaternion));
      modelQuaternion(foot, foot.modelQuaternion);
      const arm = bones.get(`upper_arm_${side}`)!;
      modelQuaternion(arm, new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.sin((phase + offset) * Math.PI * 2) * .16)
        .multiply(arm.modelQuaternion));
    }
    for (const [name, rest] of bones) {
      positions.get(name)!.push(...rest.bone.position.toArray());
      rotations.get(name)!.push(...rest.bone.quaternion.toArray());
    }
  }
  restore();
  const tracks: THREE.KeyframeTrack[] = [];
  for (const [name, rest] of bones) {
    tracks.push(new THREE.VectorKeyframeTrack(`${name}.position`, times, positions.get(name)!),
      new THREE.QuaternionKeyframeTrack(`${name}.quaternion`, times, rotations.get(name)!),
      new THREE.VectorKeyframeTrack(`${name}.scale`, [0, CIVIC_WALK_DURATION], [...rest.scale.toArray(), ...rest.scale.toArray()]));
  }
  return new THREE.AnimationClip('walk', CIVIC_WALK_DURATION, tracks);
}
