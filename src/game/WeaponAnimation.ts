import * as THREE from 'three';
import {
  equipmentEntryKey,
  getItemDefinition,
  type WeaponVisualKind,
} from '../data/items';
import type { EquipmentEntry, EquipSlot } from '../services/types';
import type { AbilityMotionKind, AbilitySchool, AbilityShape } from './abilities/types';

export type WeaponAnimationKind = WeaponVisualKind | 'cleaver' | 'unarmed';

export interface WeaponAnimationRequest {
  actionId: string;
  durationSec: number;
  abilityName?: string;
  shape?: AbilityShape;
  school?: AbilitySchool;
  motion?: AbilityMotionKind;
  targetPosition?: { x: number; y: number; z: number } | null;
}

interface WeaponAttachmentOptions {
  slot: EquipSlot;
  kind: WeaponAnimationKind;
  source?: 'baked' | 'equipment';
  key?: string;
}

interface WeaponTarget {
  object: THREE.Object3D;
  slot: EquipSlot;
  kind: WeaponAnimationKind;
  source: 'baked' | 'equipment';
  restPosition: THREE.Vector3;
  restRotation: THREE.Euler;
  restScale: THREE.Vector3;
}

interface ActiveWeaponAction {
  request: WeaponAnimationRequest;
  elapsed: number;
  duration: number;
}

type WeaponIntent =
  | 'aim'
  | 'block'
  | 'cleave'
  | 'ritual'
  | 'shoot'
  | 'slam'
  | 'swing'
  | 'thrust'
  | 'weave';

const MAIN_HAND_ANCHOR = new THREE.Vector3(0.48, 0.9, 0.14);
const OFF_HAND_ANCHOR = new THREE.Vector3(-0.52, 1.05, 0.18);
const TWO_HAND_ANCHOR = new THREE.Vector3(0.44, 0.74, 0.12);

export function markWeaponAttachment<T extends THREE.Object3D>(
  object: T,
  options: WeaponAttachmentOptions,
): T {
  object.userData.weaponAttachment = true;
  object.userData.weaponSlot = options.slot;
  object.userData.weaponKind = options.kind;
  object.userData.weaponSource = options.source ?? 'baked';
  if (options.key) object.userData.weaponKey = options.key;
  return object;
}

export function positionEquipmentWeaponOverlay(
  object: THREE.Object3D,
  slot: EquipSlot,
  kind: WeaponAnimationKind,
): void {
  if (slot === 'offHand') {
    object.position.copy(OFF_HAND_ANCHOR);
    return;
  }

  object.position.copy(kind === 'hammer' || kind === 'staff' ? TWO_HAND_ANCHOR : MAIN_HAND_ANCHOR);
}

export function inferWeaponKindFromEquipment(
  entry: EquipmentEntry | undefined,
  fallback: WeaponAnimationKind = 'generic',
): WeaponAnimationKind {
  const key = equipmentEntryKey(entry);
  if (!key) return fallback;
  const def = getItemDefinition(key);
  if (def?.weaponKind) return def.weaponKind;
  return inferWeaponKindFromText(`${key} ${def?.name ?? ''}`, fallback);
}

export function inferWeaponKindFromText(
  text: string | null | undefined,
  fallback: WeaponAnimationKind = 'generic',
): WeaponAnimationKind {
  const value = text?.toLowerCase() ?? '';
  if (!value) return fallback;
  if (/\bstaff\b|stave|rod|wand|scepter|sceptre/.test(value)) return 'staff';
  if (/hammer|maul|mace|reliquary/.test(value)) return 'hammer';
  if (/axe|hatchet/.test(value)) return 'axe';
  if (/cleaver|choppa/.test(value)) return 'cleaver';
  if (/dagger|knife|razor/.test(value)) return 'dagger';
  if (/spear|pike|glaive|halberd|lance/.test(value)) return 'spear';
  if (/bow|longdraw|arrow/.test(value)) return 'bow';
  if (/gun|rifle|pistol|blunder|muzzle/.test(value)) return 'gun';
  if (/shield|buckler/.test(value)) return 'shield';
  if (/orb|focus|idol|book|rune/.test(value)) return 'focus';
  if (/sword|blade|greatsword|rapier|sabre|saber|edge/.test(value)) return 'sword';
  return fallback;
}

export class WeaponAnimationController {
  private targets = new Map<string, WeaponTarget>();
  private active: ActiveWeaponAction | null = null;

  constructor(private root: THREE.Object3D | null = null) {}

  setRoot(root: THREE.Object3D | null): void {
    this.root = root;
    this.targets.clear();
    this.collectTargets();
  }

  refreshTargets(): void {
    this.collectTargets();
  }

  play(request: WeaponAnimationRequest): void {
    this.active = {
      request,
      elapsed: 0,
      duration: Math.max(0.16, request.durationSec || 0.45),
    };
  }

  update(dt: number): void {
    const targets = this.collectTargets();
    for (const target of targets) restoreTarget(target);

    if (!this.active) return;
    this.active.elapsed = Math.min(this.active.duration, this.active.elapsed + Math.max(0, dt));
    const t = this.active.duration > 0 ? this.active.elapsed / this.active.duration : 1;
    this.applyAction(targets, this.active.request, clamp01(t));
    if (this.active.elapsed >= this.active.duration) this.active = null;
  }

  private collectTargets(): WeaponTarget[] {
    if (!this.root) return [];

    const found = new Set<string>();
    const targets: WeaponTarget[] = [];
    this.root.traverse((node) => {
      if (!isWeaponNode(node)) return;
      const slot = readWeaponSlot(node);
      if (!slot) return;

      const uuid = node.uuid;
      found.add(uuid);
      let target = this.targets.get(uuid);
      if (!target) {
        target = {
          object: node,
          slot,
          kind: readWeaponKind(node),
          source: node.userData.weaponSource === 'equipment' ? 'equipment' : 'baked',
          restPosition: node.position.clone(),
          restRotation: node.rotation.clone(),
          restScale: node.scale.clone(),
        };
        this.targets.set(uuid, target);
      } else {
        target.kind = readWeaponKind(node);
        target.slot = slot;
        target.source = node.userData.weaponSource === 'equipment' ? 'equipment' : 'baked';
      }
      targets.push(target);
    });

    for (const uuid of this.targets.keys()) {
      if (!found.has(uuid)) this.targets.delete(uuid);
    }

    return targets;
  }

  private applyAction(
    targets: WeaponTarget[],
    request: WeaponAnimationRequest,
    t: number,
  ): void {
    const visibleTargets = targets.filter((target) => isVisibleInHierarchy(target.object));
    const mainHand = pickPreferredTarget(visibleTargets, 'mainHand');
    const offHand = pickPreferredTarget(visibleTargets, 'offHand');
    const intent = intentForRequest(request, mainHand?.kind ?? 'generic');
    const yawOffset = this.targetYawOffset(request);

    if (mainHand) applyMainHandMotion(mainHand, intent, request, t, yawOffset);

    if (offHand?.kind === 'shield') {
      const shouldBrace = intent === 'block' || request.motion === 'ward' || request.shape === 'melee';
      if (shouldBrace) applyShieldMotion(offHand, t, intent === 'block' || request.motion === 'ward');
    }
  }

  private targetYawOffset(request: WeaponAnimationRequest): number {
    if (!this.root || !request.targetPosition) return 0;
    const dx = request.targetPosition.x - this.root.position.x;
    const dz = request.targetPosition.z - this.root.position.z;
    if (Math.hypot(dx, dz) < 0.001) return 0;
    return clampAngle(Math.atan2(dx, dz) - this.root.rotation.y, -0.85, 0.85);
  }
}

function isWeaponNode(node: THREE.Object3D): boolean {
  if (node.userData.weaponAttachment === true) return true;
  if (node.userData.equipmentOverlay !== true) return false;
  return node.userData.equipmentSlot === 'mainHand' || node.userData.equipmentSlot === 'offHand';
}

function readWeaponSlot(node: THREE.Object3D): EquipSlot | null {
  const slot = node.userData.weaponSlot ?? node.userData.equipmentSlot;
  return slot === 'mainHand' || slot === 'offHand' ? slot : null;
}

function readWeaponKind(node: THREE.Object3D): WeaponAnimationKind {
  const raw = node.userData.weaponKind;
  if (typeof raw === 'string') return raw as WeaponAnimationKind;
  return inferWeaponKindFromText(`${node.name} ${node.userData.weaponKey ?? ''}`, 'generic');
}

function pickPreferredTarget(
  targets: WeaponTarget[],
  slot: EquipSlot,
): WeaponTarget | null {
  const slotTargets = targets.filter((target) => target.slot === slot);
  return (
    slotTargets.find((target) => target.source === 'equipment') ??
    slotTargets[0] ??
    null
  );
}

function restoreTarget(target: WeaponTarget): void {
  target.object.position.copy(target.restPosition);
  target.object.rotation.copy(target.restRotation);
  target.object.scale.copy(target.restScale);
}

function intentForRequest(
  request: WeaponAnimationRequest,
  weaponKind: WeaponAnimationKind,
): WeaponIntent {
  if (request.motion === 'ward' || /shield|guard|bastion|ward|counter/i.test(request.abilityName ?? '')) {
    return 'block';
  }
  if (request.motion === 'ritual') return 'ritual';
  if (request.motion === 'slam') return 'slam';
  if (request.motion === 'cleave') return 'cleave';
  if (request.motion === 'jab') return 'thrust';
  if (request.motion === 'weave') return 'weave';
  if (request.motion === 'leap') return weaponKind === 'staff' ? 'aim' : 'thrust';
  if (request.motion === 'shot') {
    if (weaponKind === 'bow' || weaponKind === 'gun') return 'shoot';
    if (weaponKind === 'staff' || weaponKind === 'focus') return 'aim';
    if (weaponKind === 'spear') return 'thrust';
    return request.shape === 'beam' ? 'aim' : 'shoot';
  }
  if (request.shape === 'projectile' || request.shape === 'beam') return 'aim';
  if (request.shape === 'area' || request.shape === 'deployable') return 'slam';
  if (request.shape === 'melee' || request.shape === 'cone' || request.shape === 'dash') return 'swing';
  return request.actionId.includes('cast') ? 'weave' : 'swing';
}

function applyMainHandMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  request: WeaponAnimationRequest,
  t: number,
  yawOffset: number,
): void {
  switch (target.kind) {
    case 'staff':
    case 'focus':
      applyStaffMotion(target, intent, request, t, yawOffset);
      return;
    case 'hammer':
      applyHammerMotion(target, intent, t);
      return;
    case 'axe':
    case 'cleaver':
      applyAxeMotion(target, intent, t);
      return;
    case 'dagger':
      applyDaggerMotion(target, intent, t, yawOffset);
      return;
    case 'spear':
      applySpearMotion(target, intent, t, yawOffset);
      return;
    case 'bow':
    case 'gun':
      applyRangedWeaponMotion(target, intent, t, yawOffset);
      return;
    case 'sword':
      applySwordMotion(target, intent, t, yawOffset);
      return;
    default:
      applyGenericMotion(target, intent, t, yawOffset);
  }
}

function applySwordMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  t: number,
  yawOffset: number,
): void {
  if (intent === 'thrust') {
    applyThrust(target, t, 0.42, yawOffset);
    target.object.rotation.z += sampleMotion([-0.14, -0.08, 0, 0], t);
    return;
  }
  const heavy = intent === 'cleave' || intent === 'slam';
  target.object.rotation.x += sampleMotion([heavy ? -0.55 : -0.32, heavy ? 0.42 : 0.28, -0.08, 0], t);
  target.object.rotation.y += sampleMotion([-0.2 + yawOffset * 0.25, 0.28 + yawOffset * 0.5, 0.08, 0], t);
  target.object.rotation.z += sampleMotion([heavy ? 0.82 : 0.58, heavy ? -1.18 : -0.86, -0.2, 0], t);
}

function applyAxeMotion(target: WeaponTarget, intent: WeaponIntent, t: number): void {
  const slam = intent === 'slam';
  target.object.rotation.x += sampleMotion([slam ? -1.05 : -0.46, slam ? 0.72 : 0.36, -0.12, 0], t);
  target.object.rotation.y += sampleMotion([-0.18, 0.3, 0.05, 0], t);
  target.object.rotation.z += sampleMotion([slam ? 0.45 : 0.92, slam ? -0.72 : -1.32, -0.18, 0], t);
}

function applyHammerMotion(target: WeaponTarget, intent: WeaponIntent, t: number): void {
  const ritual = intent === 'ritual';
  const slam = intent === 'slam' || intent === 'cleave';
  target.object.rotation.x += sampleMotion([ritual ? -0.55 : -0.92, slam ? 0.82 : 0.42, 0.08, 0], t);
  target.object.rotation.y += sampleMotion([0.18, -0.22, 0.08, 0], t);
  target.object.rotation.z += sampleMotion([slam ? 0.4 : 0.24, slam ? -0.72 : -0.48, -0.1, 0], t);
  if (slam) target.object.position.y += Math.sin(t * Math.PI) * 0.1;
}

function applyDaggerMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  t: number,
  yawOffset: number,
): void {
  if (intent === 'cleave' || intent === 'swing') {
    target.object.rotation.z += sampleMotion([0.42, -0.62, 0.18, 0], t);
    target.object.rotation.y += sampleMotion([-0.22, 0.28 + yawOffset * 0.4, 0, 0], t);
    return;
  }
  applyThrust(target, t, 0.34, yawOffset);
}

function applySpearMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  t: number,
  yawOffset: number,
): void {
  if (intent === 'cleave') {
    target.object.rotation.z += sampleMotion([0.72, -0.96, -0.12, 0], t);
    target.object.rotation.y += sampleMotion([-0.28, 0.34 + yawOffset * 0.4, 0.05, 0], t);
    return;
  }
  applyThrust(target, t, 0.56, yawOffset);
}

function applyRangedWeaponMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  t: number,
  yawOffset: number,
): void {
  const hold = holdCurve(t);
  target.object.rotation.x += Math.PI * 0.5 * hold;
  target.object.rotation.y += yawOffset * hold;
  target.object.position.z += 0.18 * hold - recoilCurve(t) * (intent === 'shoot' ? 0.16 : 0.06);
  target.object.position.y += 0.06 * hold;
}

function applyStaffMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  request: WeaponAnimationRequest,
  t: number,
  yawOffset: number,
): void {
  if (intent === 'ritual' || request.shape === 'area' || request.shape === 'deployable') {
    const lift = holdCurve(t);
    target.object.position.y += 0.28 * lift;
    target.object.rotation.x += sampleMotion([-0.32, -0.54, -0.2, 0], t);
    target.object.rotation.z += sampleMotion([0.28, -0.24, 0.12, 0], t);
    return;
  }

  if (intent === 'slam') {
    target.object.rotation.x += sampleMotion([-0.82, 0.48, 0.06, 0], t);
    target.object.rotation.z += sampleMotion([0.28, -0.34, -0.05, 0], t);
    return;
  }

  const point = intent === 'aim' || intent === 'shoot' || request.shape === 'beam'
    ? holdCurve(t)
    : Math.sin(t * Math.PI);
  target.object.rotation.x += Math.PI * 0.5 * point;
  target.object.rotation.y += yawOffset * point;
  target.object.rotation.z += Math.sin(t * Math.PI * 2) * 0.12 * point;
  target.object.position.z += 0.22 * point;
  target.object.position.y += 0.08 * point;
}

function applyGenericMotion(
  target: WeaponTarget,
  intent: WeaponIntent,
  t: number,
  yawOffset: number,
): void {
  if (intent === 'aim' || intent === 'shoot') {
    applyRangedWeaponMotion(target, intent, t, yawOffset);
    return;
  }
  if (intent === 'thrust') {
    applyThrust(target, t, 0.36, yawOffset);
    return;
  }
  target.object.rotation.z += sampleMotion([0.44, -0.58, -0.08, 0], t);
  target.object.rotation.y += sampleMotion([-0.12, 0.2 + yawOffset * 0.25, 0.05, 0], t);
}

function applyShieldMotion(target: WeaponTarget, t: number, fullGuard: boolean): void {
  const brace = fullGuard ? holdCurve(t) : Math.sin(t * Math.PI);
  target.object.position.z += 0.16 * brace;
  target.object.position.y += 0.08 * brace;
  target.object.rotation.x += -0.16 * brace;
  target.object.rotation.y += -0.34 * brace;
}

function applyThrust(
  target: WeaponTarget,
  t: number,
  distance: number,
  yawOffset: number,
): void {
  const jab = Math.sin(t * Math.PI);
  const hold = holdCurve(t);
  target.object.rotation.x += Math.PI * 0.5 * hold;
  target.object.rotation.y += yawOffset * hold;
  target.object.position.z += distance * jab;
  target.object.position.y += 0.04 * hold;
}

function sampleMotion(values: [number, number, number, number], t: number): number {
  if (t < 0.24) return lerp(0, values[0], easeOutCubic(t / 0.24));
  if (t < 0.48) return lerp(values[0], values[1], easeInOutCubic((t - 0.24) / 0.24));
  if (t < 0.74) return lerp(values[1], values[2], easeOutCubic((t - 0.48) / 0.26));
  return lerp(values[2], values[3], easeInOutCubic((t - 0.74) / 0.26));
}

function holdCurve(t: number): number {
  if (t < 0.28) return easeOutCubic(t / 0.28);
  if (t < 0.76) return 1;
  return 1 - easeInOutCubic((t - 0.76) / 0.24);
}

function recoilCurve(t: number): number {
  if (t < 0.38 || t > 0.68) return 0;
  return Math.sin(((t - 0.38) / 0.3) * Math.PI);
}

function isVisibleInHierarchy(object: THREE.Object3D): boolean {
  let current: THREE.Object3D | null = object;
  while (current) {
    if (!current.visible) return false;
    current = current.parent;
  }
  return true;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function clampAngle(value: number, min: number, max: number): number {
  let angle = value;
  while (angle > Math.PI) angle -= Math.PI * 2;
  while (angle < -Math.PI) angle += Math.PI * 2;
  return Math.max(min, Math.min(max, angle));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * clamp01(t);
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - clamp01(t), 3);
}

function easeInOutCubic(t: number): number {
  const v = clamp01(t);
  return v < 0.5 ? 4 * v * v * v : 1 - Math.pow(-2 * v + 2, 3) / 2;
}
