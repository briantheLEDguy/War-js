import * as THREE from 'three';
import {
  followObject,
  staticTarget,
  Vfx,
  type TargetProvider,
  type VfxLayer,
} from '../animation/VfxLayer';
import type { AbilityDefinition, AbilitySchool } from './types';

export interface AbilityVfxTargets {
  source: THREE.Object3D;
  targetObject?: THREE.Object3D | null;
  targetPosition?: { x: number; y: number; z: number } | null;
}

export function spawnAbilityVfx(
  layer: VfxLayer | null,
  ability: AbilityDefinition,
  targets: AbilityVfxTargets,
  releaseSec: number,
  flightSec: number,
): void {
  if (!layer) return;

  const source = followObject(targets.source);
  const target = resolveTarget(targets);
  const shape = ability.targeting.shape;

  if (shape === 'projectile' || shape === 'pet') {
    layer.spawn(new AbilityProjectileVfx(source, target, ability.effects[0]?.school ?? 'physical', Math.max(0.12, flightSec), releaseSec));
    layer.spawn(new AbilityImpactBurstVfx(target, ability.effects[0]?.school ?? 'physical', ability.targeting.radius ?? 1.2, 0.38, releaseSec + flightSec));
    return;
  }

  if (shape === 'beam') {
    layer.spawn(new AbilityBeamVfx(source, target, ability.effects[0]?.school ?? 'arcane', 0.38, releaseSec));
    layer.spawn(new AbilityImpactBurstVfx(target, ability.effects[0]?.school ?? 'arcane', 1.4, 0.34, releaseSec + 0.12));
    return;
  }

  if (shape === 'area' || shape === 'deployable') {
    const anchor = ability.targeting.target === 'self' ? source : target;
    layer.spawn(new AbilityGroundPulseVfx(anchor, ability.effects[0]?.school ?? 'holy', ability.targeting.radius ?? 4, 0.75, releaseSec));
    return;
  }

  if (shape === 'cone' || shape === 'melee' || shape === 'dash') {
    layer.spawn(new AbilityMeleeArcVfx(source, ability.effects[0]?.school ?? 'physical', shape === 'cone' ? 2.8 : 1.6, 0.35, releaseSec));
    if (ability.targeting.target === 'enemy') {
      layer.spawn(new AbilityImpactBurstVfx(target, ability.effects[0]?.school ?? 'physical', 1.0, 0.25, releaseSec + 0.08));
    }
    return;
  }

  layer.spawn(new AbilityAuraVfx(source, ability.effects[0]?.school ?? 'holy', 1.2, 0.55, releaseSec));
}

function resolveTarget(targets: AbilityVfxTargets): TargetProvider {
  if (targets.targetObject) return followObject(targets.targetObject);
  const p = targets.targetPosition ?? { x: 0, y: 0, z: 0 };
  return staticTarget(new THREE.Vector3(p.x, p.y + 1.1, p.z));
}

function createVfxMaterial(
  color: number,
  opacity: number,
  side: THREE.Side = THREE.FrontSide,
): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    side,
    depthWrite: false,
    depthTest: true,
    blending: THREE.AdditiveBlending,
  });
}

function prepareVfxRoot(root: THREE.Group): THREE.Group {
  root.traverse((node) => {
    node.frustumCulled = false;
    node.renderOrder = 20;
  });
  return root;
}

class AbilityProjectileVfx extends Vfx {
  private orb: THREE.Mesh | null = null;
  private light: THREE.PointLight | null = null;
  private tmpFrom = new THREE.Vector3();
  private tmpTo = new THREE.Vector3();
  private tmpPos = new THREE.Vector3();

  constructor(
    private from: TargetProvider,
    private to: TargetProvider,
    private school: AbilitySchool,
    duration: number,
    startDelay: number,
  ) {
    super(from, duration, startDelay);
  }

  build(): THREE.Group {
    const color = colorForSchool(this.school);
    const root = new THREE.Group();
    const mat = createVfxMaterial(color, 0.95);
    this.orb = new THREE.Mesh(new THREE.SphereGeometry(0.13, 14, 10), mat);
    this.light = new THREE.PointLight(color, 1.4, 4);
    root.add(this.orb, this.light);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number): void {
    if (!this.root) return;
    this.from.getWorldPosition(this.tmpFrom);
    this.to.getWorldPosition(this.tmpTo);
    this.tmpFrom.y += 1.25;
    this.tmpTo.y += 1.15;
    this.tmpPos.lerpVectors(this.tmpFrom, this.tmpTo, easeOutQuad(t));
    this.root.position.copy(this.tmpPos);
    const scale = 1 + Math.sin(t * Math.PI) * 0.35;
    this.root.scale.setScalar(scale);
    setOpacity(this.orb, 1 - Math.max(0, t - 0.82) / 0.18);
    if (this.light) this.light.intensity = 1.4 * (1 - t * 0.4);
  }
}

class AbilityBeamVfx extends Vfx {
  private beam: THREE.Mesh | null = null;
  private fromPos = new THREE.Vector3();
  private toPos = new THREE.Vector3();
  private mid = new THREE.Vector3();
  private dir = new THREE.Vector3();
  private yAxis = new THREE.Vector3(0, 1, 0);

  constructor(
    private from: TargetProvider,
    private to: TargetProvider,
    private school: AbilitySchool,
    duration: number,
    startDelay: number,
  ) {
    super(from, duration, startDelay);
  }

  build(): THREE.Group {
    const color = colorForSchool(this.school);
    const root = new THREE.Group();
    this.beam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.045, 0.08, 1, 10),
      createVfxMaterial(color, 0.8),
    );
    root.add(this.beam);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number): void {
    if (!this.root || !this.beam) return;
    this.from.getWorldPosition(this.fromPos);
    this.to.getWorldPosition(this.toPos);
    this.fromPos.y += 1.25;
    this.toPos.y += 1.15;
    this.mid.addVectors(this.fromPos, this.toPos).multiplyScalar(0.5);
    const length = Math.max(0.1, this.fromPos.distanceTo(this.toPos));
    this.root.position.copy(this.mid);
    this.beam.scale.set(1, length, 1);
    this.dir.subVectors(this.toPos, this.fromPos);
    if (this.dir.lengthSq() < 0.000001) this.dir.copy(this.yAxis);
    else this.dir.normalize();
    this.beam.quaternion.setFromUnitVectors(this.yAxis, this.dir);
    setOpacity(this.beam, Math.sin(Math.PI * Math.min(1, t)) * 0.85);
  }
}

class AbilityImpactBurstVfx extends Vfx {
  private ring: THREE.Mesh | null = null;
  private core: THREE.Mesh | null = null;

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = colorForSchool(this.school);
    const root = new THREE.Group();
    const mat = createVfxMaterial(color, 0.75, THREE.DoubleSide);
    this.ring = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.025, 8, 28), mat.clone());
    this.ring.rotation.x = Math.PI / 2;
    this.core = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 8), mat);
    root.add(this.ring, this.core);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number): void {
    const s = 0.35 + this.radius * easeOutQuad(t);
    if (this.ring) {
      this.ring.scale.setScalar(s);
      setOpacity(this.ring, 0.75 * (1 - t));
    }
    if (this.core) {
      this.core.scale.setScalar(1 + t * 1.8);
      setOpacity(this.core, 0.65 * (1 - t));
    }
  }
}

class AbilityGroundPulseVfx extends Vfx {
  private ring: THREE.Mesh | null = null;
  private glow: THREE.Mesh | null = null;

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = colorForSchool(this.school);
    const root = new THREE.Group();
    const mat = createVfxMaterial(color, 0.55, THREE.DoubleSide);
    this.ring = new THREE.Mesh(new THREE.TorusGeometry(this.radius, 0.035, 8, 48), mat.clone());
    this.ring.rotation.x = Math.PI / 2;
    this.glow = new THREE.Mesh(new THREE.CircleGeometry(this.radius, 48), mat);
    this.glow.rotation.x = -Math.PI / 2;
    root.add(this.glow, this.ring);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number): void {
    const pulse = 0.94 + Math.sin(t * Math.PI * 3) * 0.06;
    if (this.ring) {
      this.ring.scale.setScalar(pulse);
      setOpacity(this.ring, 0.75 * (1 - t * 0.65));
    }
    if (this.glow) {
      this.glow.scale.setScalar(0.65 + t * 0.55);
      setOpacity(this.glow, 0.35 * (1 - t));
    }
  }
}

class AbilityMeleeArcVfx extends Vfx {
  private arc: THREE.Mesh | null = null;

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = colorForSchool(this.school);
    const root = new THREE.Group();
    this.arc = new THREE.Mesh(
      new THREE.TorusGeometry(this.radius * 0.45, 0.025, 8, 28, Math.PI * 1.15),
      createVfxMaterial(color, 0.75, THREE.DoubleSide),
    );
    this.arc.position.set(0, 1.05, 0.5);
    this.arc.rotation.set(Math.PI / 2, 0, -Math.PI * 0.58);
    root.add(this.arc);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number): void {
    if (!this.arc) return;
    this.arc.rotation.z = -Math.PI * 0.75 + t * Math.PI * 1.2;
    this.arc.scale.setScalar(0.75 + t * 0.55);
    setOpacity(this.arc, 0.75 * (1 - t));
  }
}

class AbilityAuraVfx extends Vfx {
  private halo: THREE.Mesh | null = null;

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = colorForSchool(this.school);
    const root = new THREE.Group();
    this.halo = new THREE.Mesh(
      new THREE.TorusGeometry(this.radius, 0.025, 8, 36),
      createVfxMaterial(color, 0.65),
    );
    this.halo.position.y = 1.25;
    root.add(this.halo);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number): void {
    if (!this.halo) return;
    this.halo.rotation.y += 0.08;
    this.halo.scale.setScalar(0.7 + t * 0.7);
    setOpacity(this.halo, 0.65 * (1 - t));
  }
}

function colorForSchool(school: AbilitySchool): number {
  switch (school) {
    case 'fire':
      return 0xff6a1a;
    case 'holy':
      return 0xffd978;
    case 'shadow':
      return 0x7d5cff;
    case 'nature':
      return 0x61d56b;
    case 'arcane':
      return 0x66d9ff;
    case 'chaos':
      return 0xb04cff;
    case 'rune':
      return 0x70c8ff;
    case 'engineer':
      return 0xffc14f;
    case 'poison':
      return 0x86d342;
    default:
      return 0xd8d2bd;
  }
}

function setOpacity(mesh: THREE.Mesh | null, opacity: number): void {
  if (!mesh) return;
  const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const mat of materials) {
    mat.opacity = Math.max(0, Math.min(1, opacity));
    mat.transparent = true;
    mat.needsUpdate = true;
  }
}

function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t);
}
