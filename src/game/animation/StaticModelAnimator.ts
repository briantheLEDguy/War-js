import * as THREE from 'three';
import {
  CharacterAnimator,
  type ActionState,
  easeOut,
} from './CharacterAnimator';

interface StaticModelAnimatorOptions {
  preserveMixedPose?: boolean;
}

interface ImportedHumanoidRig {
  hips?: THREE.Bone;
  spine?: THREE.Bone;
  chest?: THREE.Bone;
  leftUpperLeg?: THREE.Bone;
  leftLowerLeg?: THREE.Bone;
  leftFoot?: THREE.Bone;
  rightUpperLeg?: THREE.Bone;
  rightLowerLeg?: THREE.Bone;
  rightFoot?: THREE.Bone;
  leftUpperArm?: THREE.Bone;
  leftLowerArm?: THREE.Bone;
  rightUpperArm?: THREE.Bone;
  rightLowerArm?: THREE.Bone;
}

interface StaticRigPart {
  object: THREE.Object3D;
  basePosition: THREE.Vector3;
  baseRotation: THREE.Euler;
  baseScale: THREE.Vector3;
}

interface StaticHumanoidRig {
  hips: StaticRigPart[];
  torso: StaticRigPart[];
  leftLeg: StaticRigPart[];
  rightLeg: StaticRigPart[];
  leftArm: StaticRigPart[];
  rightArm: StaticRigPart[];
}

/**
 * Lightweight animation layer for imported static character meshes.
 *
 * This animates the visual child under the player root. It is used for static
 * imports and as a fallback layer when an imported rig has only idle clips.
 * Player collision, movement, and camera follow continue to use the stable
 * root object.
 */
export class StaticModelAnimator extends CharacterAnimator {
  private readonly basePosition = new THREE.Vector3();
  private readonly baseRotation = new THREE.Euler();
  private readonly baseScale = new THREE.Vector3();
  private readonly preserveMixedPose: boolean;
  private readonly humanoidRig: ImportedHumanoidRig;
  private readonly baseBoneRotations = new Map<THREE.Bone, THREE.Euler>();
  private readonly staticRig: StaticHumanoidRig;

  constructor(
    private readonly visualRoot: THREE.Object3D,
    options: StaticModelAnimatorOptions = {},
  ) {
    super();
    this.cadenceHz = 0.16;
    this.preserveMixedPose = options.preserveMixedPose === true;
    this.basePosition.copy(visualRoot.position);
    this.baseRotation.copy(visualRoot.rotation);
    this.baseScale.copy(visualRoot.scale);
    this.humanoidRig = findImportedHumanoidRig(visualRoot);
    for (const bone of Object.values(this.humanoidRig)) {
      if (bone) this.baseBoneRotations.set(bone, bone.rotation.clone());
    }
    this.staticRig = this.baseBoneRotations.size >= 4
      ? emptyStaticRig()
      : findStaticHumanoidRig(visualRoot);
  }

  override playAction(id: string, duration = 0.35): void {
    super.playAction(id, Math.max(0.16, duration || 0.35));
  }

  protected resetPose(): void {
    this.visualRoot.position.copy(this.basePosition);
    this.visualRoot.rotation.copy(this.baseRotation);
    this.visualRoot.scale.copy(this.baseScale);
    if (!this.preserveMixedPose) {
      for (const [bone, rotation] of this.baseBoneRotations) {
        bone.rotation.copy(rotation);
      }
    }
    resetStaticRig(this.staticRig);
  }

  protected applyLocomotion(phase: number, speed: number, blend: number): void {
    const stride = Math.sin(phase);
    const footfall = Math.sin(phase * 2);
    const run = THREE.MathUtils.clamp(speed / 6, 0, 1);
    this.visualRoot.position.y += Math.max(0, footfall) * 0.055 * blend;
    this.visualRoot.rotation.x += -0.045 * run * blend;
    this.visualRoot.rotation.z += stride * 0.045 * blend;
    const squash = 1 + footfall * 0.008 * blend;
    this.visualRoot.scale.set(
      this.baseScale.x * (1 - (squash - 1) * 0.35),
      this.baseScale.y * squash,
      this.baseScale.z * (1 - (squash - 1) * 0.35),
    );
    this.applyHumanoidStride(stride, footfall, run, blend);
    this.applyStaticStride(stride, footfall, run, blend);
  }

  protected applyAction(action: ActionState, t: number): void {
    const pulse = Math.sin(Math.PI * t);
    if (action.id === 'jump') {
      this.visualRoot.position.y += pulse * 0.12;
      this.visualRoot.rotation.x += -pulse * 0.08;
      this.rotateBone(this.humanoidRig.leftUpperLeg, -pulse * 0.16, 0, 0);
      this.rotateBone(this.humanoidRig.rightUpperLeg, -pulse * 0.16, 0, 0);
      rotateParts(this.staticRig.leftLeg, -pulse * 0.16, 0, 0);
      rotateParts(this.staticRig.rightLeg, -pulse * 0.16, 0, 0);
      return;
    }

    if (/cast|bandage|heal|ultimate/i.test(action.id)) {
      this.visualRoot.position.y += pulse * 0.04;
      this.visualRoot.rotation.z += Math.sin(Math.PI * 2 * t) * 0.05;
      this.rotateBone(this.humanoidRig.leftUpperArm, -pulse * 0.18, 0, pulse * 0.12);
      this.rotateBone(this.humanoidRig.rightUpperArm, -pulse * 0.18, 0, -pulse * 0.12);
      rotateParts(this.staticRig.leftArm, -pulse * 0.34, 0, pulse * 0.16);
      rotateParts(this.staticRig.rightArm, -pulse * 0.34, 0, -pulse * 0.16);
      return;
    }

    if (/ranged|shoot/i.test(action.id)) {
      this.visualRoot.rotation.x += -pulse * 0.1;
      this.visualRoot.position.z += -easeOut(t) * 0.05 * pulse;
      this.rotateBone(this.humanoidRig.leftUpperArm, -pulse * 0.14, 0, pulse * 0.08);
      this.rotateBone(this.humanoidRig.rightUpperArm, -pulse * 0.08, 0, -pulse * 0.05);
      rotateParts(this.staticRig.leftArm, -pulse * 0.26, 0, pulse * 0.1);
      rotateParts(this.staticRig.rightArm, -pulse * 0.18, 0, -pulse * 0.08);
      return;
    }

    this.visualRoot.rotation.x += -pulse * 0.16;
    this.visualRoot.rotation.z += Math.sin(Math.PI * 2 * t) * 0.08;
    this.visualRoot.position.z += -pulse * 0.08;
    this.rotateBone(this.humanoidRig.chest, -pulse * 0.08, 0, Math.sin(Math.PI * 2 * t) * 0.05);
    this.rotateBone(this.humanoidRig.leftUpperArm, -pulse * 0.18, 0, pulse * 0.12);
    this.rotateBone(this.humanoidRig.rightUpperArm, -pulse * 0.1, 0, -pulse * 0.06);
    rotateParts(this.staticRig.torso, -pulse * 0.06, 0, Math.sin(Math.PI * 2 * t) * 0.04);
    rotateParts(this.staticRig.leftArm, -pulse * 0.2, 0, pulse * 0.15);
    rotateParts(this.staticRig.rightArm, -pulse * 0.62, 0, -pulse * 0.28);
  }

  private applyHumanoidStride(stride: number, footfall: number, run: number, blend: number): void {
    if (this.baseBoneRotations.size === 0 || blend <= 0.001) return;

    const swing = (0.22 + run * 0.2) * blend;
    const knee = (0.18 + run * 0.2) * blend;
    const arm = (0.1 + run * 0.08) * blend;

    this.rotateBone(this.humanoidRig.hips, 0, stride * 0.025 * blend, stride * 0.035 * blend);
    this.rotateBone(this.humanoidRig.spine, footfall * 0.025 * blend, 0, -stride * 0.025 * blend);
    this.rotateBone(this.humanoidRig.chest, -run * 0.035 * blend, 0, -stride * 0.03 * blend);

    this.rotateBone(this.humanoidRig.leftUpperLeg, stride * swing, 0, 0);
    this.rotateBone(this.humanoidRig.rightUpperLeg, -stride * swing, 0, 0);
    this.rotateBone(this.humanoidRig.leftLowerLeg, Math.max(0, -stride) * knee, 0, 0);
    this.rotateBone(this.humanoidRig.rightLowerLeg, Math.max(0, stride) * knee, 0, 0);
    this.rotateBone(this.humanoidRig.leftFoot, -stride * 0.09 * blend, 0, 0);
    this.rotateBone(this.humanoidRig.rightFoot, stride * 0.09 * blend, 0, 0);

    this.rotateBone(this.humanoidRig.leftUpperArm, -stride * arm, 0, stride * 0.035 * blend);
    this.rotateBone(this.humanoidRig.rightUpperArm, stride * arm * 0.55, 0, -stride * 0.025 * blend);
    this.rotateBone(this.humanoidRig.leftLowerArm, -stride * arm * 0.45, 0, 0);
    this.rotateBone(this.humanoidRig.rightLowerArm, stride * arm * 0.25, 0, 0);
  }

  private applyStaticStride(stride: number, footfall: number, run: number, blend: number): void {
    if (!hasStaticRigParts(this.staticRig) || blend <= 0.001) return;

    const swing = (0.28 + run * 0.28) * blend;
    const arm = (0.18 + run * 0.12) * blend;
    rotateParts(this.staticRig.hips, 0, stride * 0.02 * blend, stride * 0.025 * blend);
    rotateParts(this.staticRig.torso, footfall * 0.018 * blend, 0, -stride * 0.02 * blend);
    rotateParts(this.staticRig.leftLeg, stride * swing, 0, -stride * 0.015 * blend);
    rotateParts(this.staticRig.rightLeg, -stride * swing, 0, stride * 0.015 * blend);
    rotateParts(this.staticRig.leftArm, -stride * arm, 0, stride * 0.035 * blend);
    rotateParts(this.staticRig.rightArm, stride * arm, 0, -stride * 0.035 * blend);
  }

  private rotateBone(
    bone: THREE.Bone | undefined,
    x: number,
    y: number,
    z: number,
  ): void {
    if (!bone) return;
    bone.rotation.x += x;
    bone.rotation.y += y;
    bone.rotation.z += z;
  }
}

function findImportedHumanoidRig(root: THREE.Object3D): ImportedHumanoidRig {
  const bones = new Map<string, THREE.Bone>();
  root.traverse((node) => {
    const bone = node as THREE.Bone;
    if (bone.isBone) bones.set(bone.name, bone);
  });

  return {
    hips: firstBone(bones, ['hips', 'hips_01', 'hipcontrol', 'root', 'Bone', 'Bone.001']),
    spine: firstBone(bones, ['spine', 'spine_012', 'spinecontrol', 'Bone.002']),
    chest: firstBone(bones, ['chest', 'chest_013', 'chestcontrol', 'Bone.003']),
    leftUpperLeg: firstBone(bones, ['thigh_L', 'upper_leg_L', 'L_leg_02', 'Bone.010']),
    leftLowerLeg: firstBone(bones, ['shin_L', 'lower_leg_L', 'L_knee_03', 'Bone.011']),
    leftFoot: firstBone(bones, ['foot_L', 'L_anke_04', 'L_foot_05', 'Bone.012']),
    rightUpperLeg: firstBone(bones, ['thigh_R', 'upper_leg_R', 'R_leg_07', 'Bone.014']),
    rightLowerLeg: firstBone(bones, ['shin_R', 'lower_leg_R', 'R_knee_08', 'Bone.015']),
    rightFoot: firstBone(bones, ['foot_R', 'R_anke_09', 'R_foot_010', 'Bone.016']),
    leftUpperArm: firstBone(bones, ['upper_arm_L', 'L_arm_015', 'Bone.007']),
    leftLowerArm: firstBone(bones, ['forearm_L', 'L_elbow_016', 'Bone.009']),
    rightUpperArm: firstBone(bones, ['upper_arm_R', 'R_arm_039', 'Bone.006']),
    rightLowerArm: firstBone(bones, ['forearm_R', 'R_elbow_040', 'Bone.008']),
  };
}

function firstBone(
  bones: Map<string, THREE.Bone>,
  names: string[],
): THREE.Bone | undefined {
  for (const name of names) {
    const bone = bones.get(name);
    if (bone) return bone;
  }
  return undefined;
}

function emptyStaticRig(): StaticHumanoidRig {
  return {
    hips: [],
    torso: [],
    leftLeg: [],
    rightLeg: [],
    leftArm: [],
    rightArm: [],
  };
}

function findStaticHumanoidRig(root: THREE.Object3D): StaticHumanoidRig {
  const rig = emptyStaticRig();
  root.updateMatrixWorld(true);

  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh || isAnimationExcluded(node, root)) return;

    const box = new THREE.Box3().setFromObject(node);
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    root.worldToLocal(center);
    const size = box.getSize(new THREE.Vector3());
    const part = makeStaticRigPart(node);

    if (center.y < 0.95 && Math.abs(center.x) > 0.06 && size.y > 0.18) {
      (center.x < 0 ? rig.leftLeg : rig.rightLeg).push(part);
      return;
    }

    if (
      center.y >= 0.82 &&
      center.y <= 1.62 &&
      Math.abs(center.x) > 0.24 &&
      size.y > 0.14
    ) {
      (center.x < 0 ? rig.leftArm : rig.rightArm).push(part);
      return;
    }

    if (center.y >= 0.78 && center.y <= 1.42 && Math.abs(center.x) <= 0.2 && size.y > 0.18) {
      rig.torso.push(part);
      return;
    }

    if (center.y >= 0.62 && center.y <= 1.02 && Math.abs(center.x) <= 0.18 && size.y > 0.12) {
      rig.hips.push(part);
    }
  });

  return rig;
}

function makeStaticRigPart(object: THREE.Object3D): StaticRigPart {
  return {
    object,
    basePosition: object.position.clone(),
    baseRotation: object.rotation.clone(),
    baseScale: object.scale.clone(),
  };
}

function resetStaticRig(rig: StaticHumanoidRig): void {
  for (const part of allStaticParts(rig)) {
    part.object.position.copy(part.basePosition);
    part.object.rotation.copy(part.baseRotation);
    part.object.scale.copy(part.baseScale);
  }
}

function rotateParts(
  parts: StaticRigPart[],
  x: number,
  y: number,
  z: number,
): void {
  for (const part of parts) {
    part.object.rotation.x += x;
    part.object.rotation.y += y;
    part.object.rotation.z += z;
  }
}

function hasStaticRigParts(rig: StaticHumanoidRig): boolean {
  return rig.leftLeg.length > 0 ||
    rig.rightLeg.length > 0 ||
    rig.leftArm.length > 0 ||
    rig.rightArm.length > 0;
}

function allStaticParts(rig: StaticHumanoidRig): StaticRigPart[] {
  return [
    ...rig.hips,
    ...rig.torso,
    ...rig.leftLeg,
    ...rig.rightLeg,
    ...rig.leftArm,
    ...rig.rightArm,
  ];
}

function isAnimationExcluded(node: THREE.Object3D, root: THREE.Object3D): boolean {
  let current: THREE.Object3D | null = node;
  while (current && current !== root) {
    if (
      current.userData.weaponAttachment === true ||
      current.userData.equipmentOverlay === true ||
      current.userData.equipmentBaseBody === true
    ) {
      return true;
    }
    current = current.parent;
  }
  return false;
}
