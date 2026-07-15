import * as THREE from 'three';
import {
  EQUIP_SLOT_ORDER,
  equipmentEntryKey,
  getEquipmentVisualForKey,
} from '../data/items';
import type { EquipmentVisualFallback } from '../data/items';
import {
  playerModelOverrideForRace,
} from '../data/modelOverrides';
import { playableCharacterProfileKeyFor } from '../data/playableAssets.generated';
import type { CharacterState, EquipmentState, EquipSlot } from '../services/types';
import type { Terrain } from '../world/Terrain';
import {
  AssetLoader,
  type CharacterAssetResolution,
  type EquipmentAssetResolution,
  type EquipmentCompatibilityContext,
} from './AssetLoader';
import { buildCharacterMesh } from './CharacterMeshes';
import type { FollowCamera } from './Camera';
import type { Input } from './Input';
import { DEFAULT_KEYBINDINGS, type Keybindings } from '../data/keybindings';
import type { CharacterAnimator } from './animation/CharacterAnimator';
import { StaticModelAnimator } from './animation/StaticModelAnimator';
import type { AbilityDefinition } from './abilities/types';
import {
  inferWeaponKindFromEquipment,
  inferWeaponKindFromText,
  markImportedWeaponAttachments,
  markWeaponAttachment,
  positionEquipmentWeaponOverlay,
  WeaponAnimationController,
  type WeaponAnimationRequest,
} from './WeaponAnimation';

const MOVE_SPEED = 6.0;
const TURN_SPEED = 6.0;
const JUMP_V = 6.2;
const GRAVITY = 18.0;
const PLAYER_COLLISION_RADIUS = 0.45;
const WALKABLE_SURFACE_STEP_UP = 0.85;
const VISUAL_EQUIP_SLOTS: EquipSlot[] = EQUIP_SLOT_ORDER;
type GroundResolver = (x: number, z: number, currentY?: number) => number;
interface MovementOptions {
  flying?: boolean;
  autoRun?: boolean;
  keybindings?: Pick<Keybindings, 'moveForward' | 'moveBackward' | 'strafeLeft' | 'strafeRight' | 'jump'>;
}

export class Player {
  object!: THREE.Object3D;
  position = new THREE.Vector3();
  rotationY = 0;
  /** Procedural animation driver — null for careers without a rig yet. */
  animator: CharacterAnimator | null = null;
  /** GLB-based animation mixer — active when a rigged .glb model is loaded. */
  private glbMixer: THREE.AnimationMixer | null = null;
  private glbActions = new Map<string, THREE.AnimationAction>();
  private activeGlbAction: THREE.AnimationAction | null = null;
  private activeGlbClipName: string | null = null;
  private defaultGlbClipName: string | null = null;
  private glbActionLock = 0;
  private playerSkeleton: THREE.Skeleton | null = null;
  private playerBodyFamily: string | null = null;
  private playerBodyVariant: string | null = null;
  private playerSkeletonId: string | null = null;
  private playerBindPoseId: string | null = null;
  private loadedCharacterModel: string | null = null;
  private equipmentOverlays = new Map<EquipSlot, THREE.Object3D>();
  private equipmentBaseBody: THREE.Object3D | null = null;
  private equipmentVisualRequestId = 0;
  private usesCompleteCharacterVisual = false;
  private weaponAnimations = new WeaponAnimationController();
  private verticalV = 0;
  private grounded = true;
  /** Horizontal speed (m/s) computed from last frame's displacement. */
  private lastSpeed = 0;

  constructor(
    public character: CharacterState,
    private terrain: Terrain,
    private groundHeightAt: GroundResolver = (x, z) => terrain.heightAt(x, z),
  ) {}

  async build(loader: AssetLoader, scene: THREE.Scene): Promise<void> {
    const playableProfileKey = playableCharacterProfileKeyFor(
      this.character.race,
      this.character.className,
      this.character.bodyVariant,
    );
    const playableAsset = await loader.resolveCharacterAsset(
      playableProfileKey,
      this.character.bodyVariant,
    );
    const modelOverride = playerModelOverrideForRace(this.character.race);
    const overrideAsset = playableAsset
      ? null
      : await loader.resolveCharacterAsset(modelOverride.profileKey, this.character.bodyVariant);
    const characterAsset = playableAsset ?? overrideAsset;
    const indexedModel = characterAsset?.model ?? modelOverride.fallbackModel;
    this.loadedCharacterModel = indexedModel;
    const primitive = () => buildCharacterMesh(this.character.race, this.character.className);

    const { object: loadedObject, animations } = await loader.loadModelFull(indexedModel, primitive);
    this.usesCompleteCharacterVisual = !playableAsset;
    this.object = wrapStaticPlayerVisual(loadedObject);
    prepareLoadedPlayerObject(this.object);
    this.playerSkeleton = findFirstSkeleton(this.object);
    this.applyCharacterCompatibilityMetadata(characterAsset);

    if (animations.length > 0) {
      this.glbMixer = new THREE.AnimationMixer(this.object);
      for (const clip of animations) {
        const safeClip = sanitizePlayerAnimationClip(clip);
        this.glbActions.set(safeClip.name, this.glbMixer.clipAction(safeClip));
        this.defaultGlbClipName ??= safeClip.name;
      }
      this.animator = this.hasExplicitGlbLocomotion()
        ? null
        : new StaticModelAnimator(loadedObject, { preserveMixedPose: true });
      this.playGlbClip(this.preferredGlbClip('idle'), true);
    } else {
      this.animator = new StaticModelAnimator(loadedObject);
    }
    this.position.set(
      this.character.position.x,
      this.groundHeightAt(
        this.character.position.x,
        this.character.position.z,
        this.character.position.y,
      ),
      this.character.position.z,
    );
    this.rotationY = this.character.rotationY;
    this.object.position.copy(this.position);
    this.object.rotation.y = this.rotationY;
    this.weaponAnimations.setRoot(this.object);
    scene.add(this.object);
  }

  teleportTo(
    position: { x: number; y: number; z: number },
    rotationY = this.rotationY,
  ): void {
    this.position.set(position.x, position.y, position.z);
    this.rotationY = rotationY;
    this.verticalV = 0;
    this.grounded = true;
    this.object.position.copy(this.position);
    this.object.rotation.y = this.rotationY;
  }

  async applyEquipmentVisuals(
    equipment: EquipmentState | undefined,
    loader: AssetLoader,
  ): Promise<void> {
    if (!this.object) return;
    const requestId = ++this.equipmentVisualRequestId;
    if (this.usesCompleteCharacterVisual) {
      this.clearEquipmentVisuals();
      setOriginalPlayerBodyVisible(this.object, true);
      this.weaponAnimations.refreshTargets();
      return;
    }
    const activeSlots = new Set<EquipSlot>();
    const activeBodyRegions = new Set<string>();
    const activeKeys = VISUAL_EQUIP_SLOTS
      .map((slot) => equipmentEntryKey(equipment?.[slot]))
      .filter((key): key is string => Boolean(key));
    const compatibility = this.equipmentCompatibilityContext();
    const bodyModel = await loader.resolveEquipmentBaseBodyModel(activeKeys, compatibility);

    const baseBodyReady = await this.applyBaseBodyOverride(bodyModel, loader, requestId);
    if (!baseBodyReady) return;

    for (const slot of VISUAL_EQUIP_SLOTS) {
      const key = equipmentEntryKey(equipment?.[slot]);
      const visual = key ? getEquipmentVisualForKey(key) : undefined;
      if (!key || !visual) continue;
      activeSlots.add(slot);

      const resolvedVisual = await loader.resolveEquipmentModel(key, visual.model, compatibility);
      const isWeaponSlot = slot === 'mainHand' || slot === 'offHand';
      if (
        (resolvedVisual.disabled && !isWeaponSlot)
        || (resolvedVisual.skinned && !this.canUseSkinnedEquipment(resolvedVisual))
      ) {
        this.removeEquipmentOverlay(slot);
        continue;
      }

      const existing = this.equipmentOverlays.get(slot);
      if (existing?.userData.equipmentKey === key) {
        if (!resolvedVisual.skinned || existing.userData.skinnedEquipmentOverlay) {
          for (const region of resolvedVisual.coveredRegions ?? []) {
            activeBodyRegions.add(region);
          }
        }
        continue;
      }
      existing?.removeFromParent();
      this.equipmentOverlays.delete(slot);

      // A blocked weapon still needs a visible, animatable representation. The
      // approval gate must prevent the authored asset from loading, but it
      // should not leave the character visibly unarmed when a safe primitive
      // fallback is available.
      const overlay = resolvedVisual.disabled && isWeaponSlot
        ? buildEquipmentVisualFallback(visual.fallback, key)
        : await loader.loadModel(
          resolvedVisual.model,
          () => buildEquipmentVisualFallback(visual.fallback, key),
        );
      if (requestId !== this.equipmentVisualRequestId) {
        overlay.removeFromParent();
        return;
      }

      overlay.name = `EquipmentOverlay_${slot}_${key}`;
      overlay.userData.equipmentKey = key;
      overlay.userData.equipmentSlot = slot;
      overlay.userData.equipmentOverlay = true;
      prepareEquipmentOverlay(overlay);
      if (slot === 'mainHand' || slot === 'offHand') {
        const weaponKind = inferWeaponKindFromEquipment(equipment?.[slot]);
        markWeaponAttachment(overlay, {
          slot,
          kind: weaponKind,
          source: 'equipment',
          key,
        });
        positionEquipmentWeaponOverlay(overlay, slot, weaponKind);
      }
      if (resolvedVisual.skinned) {
        const rebound = bindSkinnedOverlayToPlayer(
          overlay,
          this.playerSkeleton,
        );
        if (!rebound) {
          overlay.removeFromParent();
          continue;
        }
        overlay.userData.skinnedEquipmentOverlay = true;
      }
      for (const region of resolvedVisual.coveredRegions ?? []) {
        activeBodyRegions.add(region);
      }
      this.object.add(overlay);
      this.equipmentOverlays.set(slot, overlay);
    }

    for (const [slot, overlay] of this.equipmentOverlays) {
      if (activeSlots.has(slot)) continue;
      overlay.removeFromParent();
      this.equipmentOverlays.delete(slot);
    }

    if (!this.equipmentBaseBody) {
      applyBodyRegionMask(this.object, activeBodyRegions);
    }
    this.syncBakedWeaponVisibility();
    this.weaponAnimations.refreshTargets();
  }

  private canUseSkinnedEquipment(resolution: EquipmentAssetResolution): boolean {
    if (!this.playerSkeleton) return false;
    if (resolution.bodyVariant && resolution.bodyVariant !== this.playerBodyVariant) {
      return false;
    }
    if (resolution.skeletonId && resolution.skeletonId !== this.playerSkeletonId) {
      return false;
    }
    if (resolution.bodyFamily && resolution.bodyFamily !== this.playerBodyFamily) {
      return false;
    }
    if (resolution.bindPoseId && resolution.bindPoseId !== this.playerBindPoseId) {
      return false;
    }
    return true;
  }

  private applyCharacterCompatibilityMetadata(
    asset: CharacterAssetResolution | null,
  ): void {
    this.playerBodyFamily = asset?.bodyFamily ?? readMetadataString(this.object, 'bodyFamily');
    this.playerBodyVariant = asset?.bodyVariant
      ?? readMetadataString(this.object, 'bodyVariant')
      ?? this.character.bodyVariant;
    this.playerSkeletonId = asset?.skeletonId ?? readMetadataString(this.object, 'skeletonId');
    this.playerBindPoseId = asset?.bindPoseId ?? readMetadataString(this.object, 'bindPoseId');
  }

  private equipmentCompatibilityContext(): EquipmentCompatibilityContext {
    return {
      bodyFamily: this.playerBodyFamily,
      bodyVariant: this.playerBodyVariant,
      skeletonId: this.playerSkeletonId,
      bindPoseId: this.playerBindPoseId,
    };
  }

  private async applyBaseBodyOverride(
    bodyModel: string | null,
    loader: AssetLoader,
    requestId: number,
  ): Promise<boolean> {
    if (!bodyModel || bodyModel === this.loadedCharacterModel) {
      this.equipmentBaseBody?.removeFromParent();
      this.equipmentBaseBody = null;
      setOriginalPlayerBodyVisible(this.object, true);
      return true;
    }

    if (!this.playerSkeleton) {
      this.equipmentBaseBody?.removeFromParent();
      this.equipmentBaseBody = null;
      setOriginalPlayerBodyVisible(this.object, true);
      return true;
    }

    if (!this.equipmentBaseBody) {
      const body = await loader.loadModel(bodyModel, () => new THREE.Group());
      if (requestId !== this.equipmentVisualRequestId) {
        body.removeFromParent();
        return false;
      }
      body.name = 'EquipmentBaseBody_manifest';
      body.userData.equipmentBaseBody = true;
      body.userData.equipmentBodyModel = bodyModel;
      prepareEquipmentOverlay(body);
      if (!bindSkinnedOverlayToPlayer(body, this.playerSkeleton)) {
        body.removeFromParent();
        setOriginalPlayerBodyVisible(this.object, true);
        return true;
      }
      this.object.add(body);
      this.equipmentBaseBody = body;
    } else if (this.equipmentBaseBody.userData.equipmentBodyModel !== bodyModel) {
      this.equipmentBaseBody.removeFromParent();
      this.equipmentBaseBody = null;
      return this.applyBaseBodyOverride(bodyModel, loader, requestId);
    }

    setOriginalPlayerBodyVisible(this.object, false);
    return true;
  }

  private clearEquipmentVisuals(): void {
    for (const overlay of this.equipmentOverlays.values()) {
      overlay.removeFromParent();
    }
    this.equipmentOverlays.clear();
    this.equipmentBaseBody?.removeFromParent();
    this.equipmentBaseBody = null;
  }

  private removeEquipmentOverlay(slot: EquipSlot): void {
    this.equipmentOverlays.get(slot)?.removeFromParent();
    this.equipmentOverlays.delete(slot);
  }

  playGlbAction(actionId: string, duration = 0): void {
    if (!this.glbMixer) {
      this.animator?.playAction(actionId, duration);
      return;
    }
    const clipName = glbActionClipName(actionId);
    if (!clipName) {
      this.animator?.playAction(actionId, duration);
      return;
    }
    const action = this.glbActions.get(clipName);
    if (!action) {
      this.animator?.playAction(actionId, duration);
      return;
    }
    this.glbActionLock = Math.max(duration, action.getClip().duration);
    this.playGlbClip(clipName, false);
  }

  playWeaponAction(request: WeaponAnimationRequest): void {
    this.weaponAnimations.play(request);
  }

  playAbilityWeaponAction(
    ability: AbilityDefinition,
    targetPosition: { x: number; y: number; z: number } | null = null,
  ): void {
    const authoredClip = glbActionClipName(ability.animation.actionId);
    const authoredClipOwnsBakedWeapon = authoredClip !== null
      && this.glbActions.has(authoredClip);
    this.playWeaponAction({
      actionId: ability.animation.actionId,
      durationSec: ability.animation.durationSec,
      abilityName: ability.name,
      shape: ability.targeting.shape,
      school: ability.visual.school,
      motion: ability.visual.vfx.motion,
      targetPosition,
      ...(authoredClipOwnsBakedWeapon ? { targetSources: ['equipment'] as const } : {}),
    });
  }

  updateVisuals(dt: number): void {
    if (this.glbMixer) {
      this.updateGlbLocomotion(dt);
      this.glbMixer.update(dt);
    }
    if (this.animator) {
      this.animator.update({ dt, speed: this.lastSpeed, airborne: !this.grounded });
    }
    this.weaponAnimations.update(dt);
  }

  update(
    dt: number,
    input: Input,
    camera: FollowCamera,
    resolveCollision?: (position: THREE.Vector3, radius: number) => void,
    moveMultiplier = 1,
    options: MovementOptions = {},
  ) {
    const flying = options.flying === true;
    const keybindings = options.keybindings ?? DEFAULT_KEYBINDINGS;
    // Input relative to camera yaw — combine keyboard and touch joystick
    let mx = input.touchMoveX;
    let mz = input.touchMoveZ;
    if (input.isBindingDown(keybindings.moveForward)) mz -= 1;
    if (input.isBindingDown(keybindings.moveBackward)) mz += 1;
    if (input.isBindingDown(keybindings.strafeLeft)) mx -= 1;
    if (input.isBindingDown(keybindings.strafeRight)) mx += 1;
    if (options.autoRun) mz -= 1;
    if (input.mouseLeftDown && input.mouseRightDown) mz -= 1;
    // Clamp combined input to unit circle (keyboard diagonal = √2, joystick max = 1)
    const len = Math.hypot(mx, mz);
    if (len > 1) {
      mx /= len;
      mz /= len;
    }
    // Rotate input through the camera's screen-space basis. Forward is the
    // direction from camera to player, so mouse-look movement follows the view.
    const yaw = camera.yawAngle;
    const sin = Math.sin(yaw);
    const cos = Math.cos(yaw);
    const forwardAmount = -mz;
    const wx = mx * cos + forwardAmount * -sin;
    const wz = mx * -sin + forwardAmount * -cos;

    // Track horizontal displacement so the animator knows the locomotion speed.
    const prevX = this.position.x;
    const prevZ = this.position.z;

    if (len > 0) {
      const speed = MOVE_SPEED * Math.max(0, moveMultiplier);
      this.position.x += wx * speed * dt;
      this.position.z += wz * speed * dt;
      if (!flying) resolveCollision?.(this.position, PLAYER_COLLISION_RADIUS);
      const targetYaw = Math.atan2(wx, wz);
      const turnT = input.mouseRightDown ? 1 : Math.min(1, TURN_SPEED * dt);
      this.rotationY = lerpAngle(this.rotationY, targetYaw, turnT);
    } else if (input.mouseRightDown) {
      this.rotationY = camera.forwardYaw;
    }

    if (flying) {
      const vertical = (input.isDown('KeyE') ? 1 : 0) - (input.isDown('KeyQ') ? 1 : 0);
      this.position.y += vertical * MOVE_SPEED * Math.max(0, moveMultiplier) * dt;
      this.verticalV = 0;
      this.grounded = false;
    } else {
      // Ground check and jump (keyboard Space or touch jump button)
      const groundProbeY = this.grounded
        ? this.position.y
        : this.position.y - WALKABLE_SURFACE_STEP_UP;
      const groundY = this.groundHeightAt(this.position.x, this.position.z, groundProbeY);
      if (this.grounded && (input.wasBindingPressed(keybindings.jump) || input.touchJumpThisFrame)) {
        this.verticalV = JUMP_V;
        this.grounded = false;
        this.animator?.playAction('jump', 0.45);
      }
      if (!this.grounded) {
        this.verticalV -= GRAVITY * dt;
        this.position.y += this.verticalV * dt;
        if (this.position.y <= groundY) {
          this.position.y = groundY;
          this.verticalV = 0;
          this.grounded = true;
        }
      } else {
        this.position.y = groundY;
      }
    }

    this.object.position.copy(this.position);
    this.object.rotation.y = this.rotationY;

    // Animation update — compute planar speed from this frame's displacement
    // (not from input, so the animator reacts correctly to e.g. collision).
    const dx = this.position.x - prevX;
    const dz = this.position.z - prevZ;
    if (dt > 0) {
      const frameSpeed = Math.hypot(dx, dz) / dt;
      this.lastSpeed = this.lastSpeed * 0.6 + frameSpeed * 0.4;
    }

    this.updateVisuals(dt);
  }

  private updateGlbLocomotion(dt: number): void {
    if (this.glbActionLock > 0) {
      this.glbActionLock = Math.max(0, this.glbActionLock - dt);
      return;
    }

    if (!this.grounded && this.glbActions.has('jump')) {
      this.playGlbClip('jump', false);
      return;
    }

    if (this.lastSpeed > MOVE_SPEED * 0.6 && this.glbActions.has('run')) {
      this.playGlbClip('run', true);
      return;
    }

    if (this.lastSpeed > 0.15 && this.glbActions.has('walk')) {
      this.playGlbClip('walk', true);
      return;
    }

    this.playGlbClip(this.preferredGlbClip('idle'), true);
  }

  private preferredGlbClip(name: string): string {
    return this.glbActions.has(name)
      ? name
      : this.defaultGlbClipName ?? name;
  }

  private hasExplicitGlbLocomotion(): boolean {
    return this.glbActions.has('walk') || this.glbActions.has('run');
  }

  private playGlbClip(name: string, loop: boolean): void {
    const next = this.glbActions.get(name);
    if (!next || this.activeGlbClipName === name) return;

    const previous = this.activeGlbAction;
    next.reset();
    next.enabled = true;
    next.clampWhenFinished = !loop;
    next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);
    next.fadeIn(0.15);
    next.play();

    if (previous) previous.fadeOut(0.15);

    this.activeGlbAction = next;
    this.activeGlbClipName = name;
  }

  private syncBakedWeaponVisibility(): void {
    const overlaySlots = new Set(this.equipmentOverlays.keys());
    this.object.traverse((node) => {
      if (node.userData.weaponSource !== 'baked') return;
      const slot = node.userData.weaponSlot;
      if (slot === 'mainHand' || slot === 'offHand') {
        node.visible = !overlaySlots.has(slot);
      }
    });
  }
}

function lerpAngle(a: number, b: number, t: number): number {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return a + d * t;
}

function glbActionClipName(actionId: string): string | null {
  switch (actionId) {
    case 'autoattack':
    case 'heavy_strike':
    case 'light_attack_a':
    case 'light_attack_b':
    case 'light_attack_c':
    case 'heavy_attack':
    case 'shield_bash':
      return 'attack_melee';
    case 'ranged_shot':
    case 'shoot_standing':
    case 'shoot_moving':
      return 'attack_ranged';
    case 'bandage':
    case 'cast_short':
    case 'cast_long':
    case 'cast_heal':
    case 'ultimate_cast':
      return 'cast';
    default:
      return null;
  }
}

function sanitizePlayerAnimationClip(clip: THREE.AnimationClip): THREE.AnimationClip {
  const tracks = clip.tracks.filter((track) => {
    const [targetName, propertyName] = track.name.split('.');
    if (targetName === 'root') return false;
    return propertyName !== 'scale';
  });
  if (tracks.length === clip.tracks.length) return clip;
  return new THREE.AnimationClip(clip.name, clip.duration, tracks, clip.blendMode);
}

function wrapStaticPlayerVisual(visual: THREE.Object3D): THREE.Object3D {
  const root = new THREE.Group();
  root.name = 'PlayerStaticModelRoot';
  visual.name = visual.name || 'PlayerStaticModelVisual';
  root.add(visual);
  return root;
}

function prepareLoadedPlayerObject(object: THREE.Object3D): void {
  object.updateMatrixWorld(true);
  markImportedWeaponAttachments(object);
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
      mat.opacity = Math.max(mat.opacity ?? 1, 1);
      mat.transparent = false;
      mat.alphaTest = 0;
      mat.depthWrite = true;
      mat.depthTest = true;
      mat.needsUpdate = true;
    }
  });
}

function prepareEquipmentOverlay(object: THREE.Object3D): void {
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

function findFirstSkeleton(root: THREE.Object3D): THREE.Skeleton | null {
  let skeleton: THREE.Skeleton | null = null;
  root.traverse((node) => {
    if (skeleton) return;
    const mesh = node as THREE.SkinnedMesh;
    if (mesh.isSkinnedMesh) skeleton = mesh.skeleton;
  });
  return skeleton;
}

function readMetadataString(root: THREE.Object3D, key: string): string | null {
  let value: string | null = null;
  root.traverse((node) => {
    if (value) return;
    const raw = node.userData?.[key];
    if (typeof raw === 'string') value = raw;
  });
  return value;
}

function bindSkinnedOverlayToPlayer(
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

function normalizeBoneName(name: string): string {
  return name.replace(/\.\d+$/u, '');
}

function applyBodyRegionMask(root: THREE.Object3D, hiddenRegions: Set<string>): void {
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

function setOriginalPlayerBodyVisible(root: THREE.Object3D, visible: boolean): void {
  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh || isEquipmentAttachment(root, node)) return;
    mesh.visible = visible;
  });
}

function isEquipmentAttachment(root: THREE.Object3D, node: THREE.Object3D): boolean {
  let current: THREE.Object3D | null = node;
  while (current && current !== root) {
    if (current.userData.equipmentOverlay || current.userData.equipmentBaseBody) {
      return true;
    }
    current = current.parent;
  }
  return false;
}

function buildEquipmentVisualFallback(
  kind: EquipmentVisualFallback,
  key: string,
): THREE.Object3D {
  switch (kind) {
    case 'chest':
      return buildChestArmorFallback();
    case 'head':
      return buildHelmetFallback();
    case 'mainHand':
      return buildMainHandFallback(key);
    case 'neck':
      return buildNeckFallback();
    case 'offHand':
      return buildShieldFallback(key);
    default:
      return new THREE.Group();
  }
}

function buildChestArmorFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const chain = new THREE.MeshStandardMaterial({
    color: 0x6f7a76,
    metalness: 0.55,
    roughness: 0.42,
  });
  const trim = new THREE.MeshStandardMaterial({
    color: 0xb89b5a,
    metalness: 0.65,
    roughness: 0.35,
  });

  const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.33, 0.27, 0.62, 16), chain);
  torso.name = 'FallbackChestHauberk';
  torso.position.set(0, 1.17, 0);
  torso.scale.z = 0.72;
  torso.castShadow = true;

  const belt = new THREE.Mesh(new THREE.BoxGeometry(0.58, 0.06, 0.28), trim);
  belt.name = 'FallbackChestBelt';
  belt.position.set(0, 0.88, 0);
  belt.castShadow = true;

  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.21, 0.025, 8, 18), trim);
  collar.name = 'FallbackChestCollar';
  collar.position.set(0, 1.5, 0);
  collar.rotation.x = Math.PI / 2;
  collar.scale.z = 0.65;
  collar.castShadow = true;

  group.add(torso, belt, collar);
  return group;
}

function buildHelmetFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const steel = new THREE.MeshStandardMaterial({
    color: 0x777c80,
    metalness: 0.7,
    roughness: 0.32,
  });
  const brass = new THREE.MeshStandardMaterial({
    color: 0xc5a45b,
    metalness: 0.7,
    roughness: 0.35,
  });

  const helm = new THREE.Mesh(
    new THREE.SphereGeometry(0.23, 16, 8, 0, Math.PI * 2, 0, Math.PI * 0.62),
    steel,
  );
  helm.name = 'FallbackReikguardHelm';
  helm.position.set(0, 1.71, 0);
  helm.scale.z = 0.88;
  helm.castShadow = true;

  const brow = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.045, 0.08), brass);
  brow.name = 'FallbackHelmBrow';
  brow.position.set(0, 1.75, 0.16);
  brow.castShadow = true;

  const crest = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.26, 0.08), brass);
  crest.name = 'FallbackHelmCrest';
  crest.position.set(0, 1.9, -0.01);
  crest.castShadow = true;

  group.add(helm, brow, crest);
  return group;
}

function buildMainHandFallback(key: string): THREE.Object3D {
  const kind = inferWeaponKindFromText(key, 'generic');
  const group = new THREE.Group();
  const steel = new THREE.MeshStandardMaterial({
    color: 0x4a5254,
    metalness: 0.72,
    roughness: 0.42,
  });
  const brass = new THREE.MeshStandardMaterial({
    color: 0xb18a38,
    metalness: 0.65,
    roughness: 0.38,
  });
  const grip = new THREE.MeshStandardMaterial({
    color: 0x261810,
    roughness: 0.86,
  });

  if (kind === 'staff' || kind === 'focus') {
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.04, 2.05, 10), grip);
    shaft.name = 'FallbackStaffShaft';
    shaft.position.y = 0.52;
    shaft.castShadow = true;
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 8), brass);
    cap.name = 'FallbackStaffFocus';
    cap.position.y = 1.62;
    cap.castShadow = true;
    group.add(shaft, cap);
    return group;
  }

  if (kind === 'sword' || kind === 'generic') {
    const h = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.036, 0.38, 8), grip);
    h.name = 'FallbackSwordGrip';
    h.position.y = 0.16;
    h.castShadow = true;
    const guard = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.045, 0.055), brass);
    guard.name = 'FallbackSwordGuard';
    guard.position.y = 0.36;
    guard.castShadow = true;
    const blade = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.92, 0.035), steel);
    blade.name = 'FallbackSwordBlade';
    blade.position.y = 0.84;
    blade.castShadow = true;
    group.add(h, guard, blade);
    return group;
  }

  if (kind === 'hammer') {
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.042, 1.42, 8), grip);
    shaft.name = 'FallbackHammerShaft';
    shaft.position.y = 0.64;
    shaft.castShadow = true;
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.2, 0.16), steel);
    head.name = 'FallbackHammerHead';
    head.position.y = 1.38;
    head.castShadow = true;
    const band = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.04, 0.18), brass);
    band.name = 'FallbackHammerBand';
    band.position.y = 1.5;
    band.castShadow = true;
    group.add(shaft, head, band);
    return group;
  }

  if (kind === 'axe' || kind === 'cleaver') {
    const haft = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.042, 1.26, 8), grip);
    haft.name = 'FallbackAxeHaft';
    haft.position.y = 0.56;
    haft.castShadow = true;
    const blade = new THREE.Mesh(
      new THREE.BoxGeometry(kind === 'cleaver' ? 0.36 : 0.28, kind === 'cleaver' ? 0.44 : 0.34, 0.06),
      steel,
    );
    blade.name = kind === 'cleaver' ? 'FallbackCleaverBlade' : 'FallbackAxeBlade';
    blade.position.set(0.08, 1.24, 0);
    blade.castShadow = true;
    group.add(haft, blade);
    return group;
  }

  if (kind === 'dagger') {
    const h = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.032, 0.24, 8), grip);
    h.name = 'FallbackDaggerGrip';
    h.position.y = 0.1;
    h.castShadow = true;
    const blade = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.52, 0.032), steel);
    blade.name = 'FallbackDaggerBlade';
    blade.position.y = 0.46;
    blade.castShadow = true;
    group.add(h, blade);
    return group;
  }

  if (kind === 'spear') {
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.032, 1.55, 8), grip);
    shaft.name = 'FallbackSpearShaft';
    shaft.position.y = 0.68;
    shaft.castShadow = true;
    const tip = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.26, 8), steel);
    tip.name = 'FallbackSpearTip';
    tip.position.y = 1.58;
    tip.castShadow = true;
    group.add(shaft, tip);
    return group;
  }

  if (kind === 'bow') {
    const stave = new THREE.Mesh(new THREE.CylinderGeometry(0.024, 0.03, 1.55, 8), grip);
    stave.name = 'FallbackBowStave';
    stave.position.set(0.08, 0.7, 0);
    stave.scale.x = 0.55;
    stave.castShadow = true;
    const string = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 1.35, 6), brass);
    string.name = 'FallbackBowString';
    string.position.set(-0.12, 0.7, 0);
    string.castShadow = true;
    group.add(stave, string);
    return group;
  }

  if (kind === 'gun') {
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.032, 0.9, 10), steel);
    barrel.name = 'FallbackGunBarrel';
    barrel.position.y = 0.48;
    barrel.castShadow = true;
    const stock = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.34, 0.08), grip);
    stock.name = 'FallbackGunStock';
    stock.position.set(0, 0.08, -0.03);
    stock.castShadow = true;
    group.add(barrel, stock);
    return group;
  }

  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.04, 1.25, 10), grip);
  shaft.name = 'FallbackMainHandGrip';
  shaft.position.y = 0.5;
  shaft.castShadow = true;

  const head = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.18, 0.16), steel);
  head.name = 'FallbackMainHandHead';
  head.position.y = 1.12;
  head.castShadow = true;

  const band = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.035, 0.18), brass);
  band.name = 'FallbackMainHandBand';
  band.position.y = 1.22;
  band.castShadow = true;

  group.add(shaft, head, band);
  return group;
}

function buildNeckFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const chain = new THREE.MeshStandardMaterial({
    color: 0x303638,
    metalness: 0.58,
    roughness: 0.46,
  });
  const gem = new THREE.MeshStandardMaterial({
    color: 0x6c1116,
    roughness: 0.2,
  });

  const loop = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.008, 8, 30), chain);
  loop.name = 'FallbackNeckLoop';
  loop.position.set(0, 1.49, 0.1);
  loop.rotation.x = Math.PI / 2;
  loop.scale.z = 0.55;
  loop.castShadow = true;

  const pendant = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), gem);
  pendant.name = 'FallbackNeckPendant';
  pendant.position.set(0, 1.38, 0.18);
  pendant.scale.y = 1.25;
  pendant.castShadow = true;

  group.add(loop, pendant);
  return group;
}

function buildShieldFallback(key: string): THREE.Object3D {
  const group = new THREE.Group();
  const isWood = key.includes('wood');
  const face = new THREE.MeshStandardMaterial({
    color: isWood ? 0x6a4222 : 0x7d8587,
    metalness: isWood ? 0.1 : 0.65,
    roughness: isWood ? 0.82 : 0.38,
  });
  const rim = new THREE.MeshStandardMaterial({
    color: 0xb69b5c,
    metalness: 0.7,
    roughness: 0.35,
  });

  const shield = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.06, 24), face);
  shield.name = 'FallbackShieldFace';
  shield.position.set(0, 0, 0.02);
  shield.rotation.x = Math.PI / 2;
  shield.scale.y = 1.2;
  shield.castShadow = true;

  const boss = new THREE.Mesh(new THREE.SphereGeometry(0.08, 12, 8), rim);
  boss.name = 'FallbackShieldBoss';
  boss.position.set(0, 0, 0.08);
  boss.scale.z = 0.35;
  boss.castShadow = true;

  const strap = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.45, 0.03), rim);
  strap.name = 'FallbackShieldStrap';
  strap.position.set(0, 0, -0.04);
  strap.castShadow = true;

  group.add(shield, boss, strap);
  return group;
}
