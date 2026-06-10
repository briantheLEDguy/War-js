import * as THREE from 'three';
import {
  followObject,
  staticTarget,
  Vfx,
  type TargetProvider,
  type VfxLayer,
} from '../animation/VfxLayer';
import type {
  AbilityCastVfxKind,
  AbilityClassFlair,
  AbilityColorProfile,
  AbilityDefinition,
  AbilityImpactVfxKind,
  AbilityMotionKind,
  AbilityProjectileVfxKind,
  AbilitySchool,
  AbilityTrailVfxKind,
  AbilityVfxProfile,
} from './types';

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
  const school = ability.visual?.school ?? ability.effects[0]?.school ?? 'physical';
  const visual = ability.visual?.vfx ?? fallbackVfxProfile(ability.id, school, shape);
  const windupSec = Math.max(0.22, Math.min(0.72, releaseSec + 0.08));

  layer.spawn(new AbilityCastWindupVfx(source, school, visual, windupSec, 0));
  layer.spawn(new AbilityClassFlairVfx(source, school, visual, Math.max(0.52, windupSec + 0.22), 0));

  if (shape === 'projectile' || shape === 'pet') {
    layer.spawn(new AbilityProjectileVfx(source, target, school, visual, Math.max(0.12, flightSec), releaseSec));
    layer.spawn(new AbilityImpactBurstVfx(target, school, visual, ability.targeting.radius ?? 1.2, 0.48, releaseSec + flightSec));
    layer.spawn(new AbilityContactFlairVfx(target, school, visual, 0.54, releaseSec + flightSec));
    return;
  }

  if (shape === 'beam') {
    layer.spawn(new AbilityBeamVfx(source, target, school, visual, 0.46, releaseSec));
    layer.spawn(new AbilityImpactBurstVfx(target, school, visual, 1.4, 0.42, releaseSec + 0.12));
    layer.spawn(new AbilityContactFlairVfx(target, school, visual, 0.5, releaseSec + 0.12));
    return;
  }

  if (shape === 'area' || shape === 'deployable') {
    const anchor = ability.targeting.target === 'self' ? source : target;
    layer.spawn(new AbilityGroundPulseVfx(anchor, school, visual, ability.targeting.radius ?? 4, 0.88, releaseSec));
    return;
  }

  if (shape === 'cone' || shape === 'melee' || shape === 'dash') {
    layer.spawn(new AbilityMeleeArcVfx(source, school, visual, shape === 'cone' ? 2.8 : 1.6, 0.42, releaseSec));
    if (ability.targeting.target === 'enemy') {
      layer.spawn(new AbilityImpactBurstVfx(target, school, visual, 1.0, 0.34, releaseSec + 0.08));
      layer.spawn(new AbilityContactFlairVfx(target, school, visual, 0.42, releaseSec + 0.08));
    }
    return;
  }

  layer.spawn(new AbilityAuraVfx(source, school, visual, 1.2, 0.62, releaseSec));
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

class AbilityCastWindupVfx extends Vfx {
  private ring: THREE.Mesh | null = null;
  private core: THREE.Mesh | null = null;
  private sigils: THREE.Mesh[] = [];

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    const ringRadius = this.visual.cast === 'ritual' ? 0.82 : 0.56;
    this.ring = new THREE.Mesh(
      new THREE.TorusGeometry(ringRadius, 0.018, 8, 44),
      createVfxMaterial(color, 0.68, THREE.DoubleSide),
    );
    this.ring.position.y = this.visual.cast === 'guard' ? 1.16 : 0.08;
    this.ring.rotation.x = Math.PI / 2;

    this.core = new THREE.Mesh(
      this.visual.cast === 'guard'
        ? new THREE.OctahedronGeometry(0.16, 0)
        : new THREE.SphereGeometry(0.11, 12, 8),
      createVfxMaterial(secondary, 0.82),
    );
    this.core.position.y = this.visual.cast === 'guard' ? 1.25 : 1.34;

    const sigilCount = this.visual.cast === 'ritual' ? 5 : 3;
    for (let i = 0; i < sigilCount; i += 1) {
      const sigil = new THREE.Mesh(
        new THREE.TetrahedronGeometry(0.045, 0),
        createVfxMaterial(i % 2 === 0 ? color : secondary, 0.58),
      );
      const angle = (i / sigilCount) * Math.PI * 2;
      sigil.position.set(Math.cos(angle) * ringRadius, 0.14, Math.sin(angle) * ringRadius);
      this.sigils.push(sigil);
      root.add(sigil);
    }

    root.add(this.ring, this.core);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    const spin = this.visual.cast === 'chant' || this.visual.cast === 'ritual' ? 1 : -1;
    if (this.ring) {
      this.ring.rotation.z += dt * (3.2 + (this.visual.seed % 4)) * spin;
      this.ring.scale.setScalar(0.65 + easeOutQuad(t) * 0.55);
      setOpacity(this.ring, 0.68 * (1 - t * 0.35));
    }
    if (this.core) {
      const pulse = 1 + Math.sin(t * Math.PI * 4) * 0.2;
      this.core.scale.setScalar(pulse * (0.85 + t * 0.55));
      setOpacity(this.core, 0.82 * (1 - t * 0.45));
    }
    for (let i = 0; i < this.sigils.length; i += 1) {
      const sigil = this.sigils[i];
      sigil.rotation.y += dt * (4 + i);
      sigil.position.y = 0.1 + Math.sin(t * Math.PI * 2 + i) * 0.12 + t * 0.45;
      setOpacity(sigil, 0.55 * (1 - t));
    }
  }
}

class AbilityClassFlairVfx extends Vfx {
  private marks: THREE.Mesh[] = [];
  private ring: THREE.Mesh | null = null;

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const accent = accentColor(this.visual, this.school);
    const root = new THREE.Group();
    const radius = flairOrbitRadius(this.visual.flair);
    const count = flairParticleCount(this.visual.flair);

    this.ring = new THREE.Mesh(
      flairRingGeometry(this.visual.flair, radius),
      createVfxMaterial(accent, 0.3, THREE.DoubleSide),
    );
    this.ring.position.y = this.visual.cast === 'guard' ? 1.15 : 0.18;
    this.ring.rotation.x = Math.PI / 2;
    root.add(this.ring);

    for (let i = 0; i < count; i += 1) {
      const mark = new THREE.Mesh(
        flairGlyphGeometry(this.visual.flair, i),
        createVfxMaterial(i % 2 === 0 ? color : accent, 0.62, THREE.DoubleSide),
      );
      const angle = ((i / count) * Math.PI * 2) + seedPhase(this.visual.seed, i);
      mark.position.set(
        Math.cos(angle) * radius,
        0.65 + (i % 3) * 0.18,
        Math.sin(angle) * radius,
      );
      mark.rotation.set(angle * 0.3, angle, angle * 0.5);
      this.marks.push(mark);
      root.add(mark);
    }

    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    const motion = flairMotion(this.visual.flair);
    if (this.ring) {
      this.ring.rotation.z += dt * motion.spin;
      this.ring.scale.setScalar(0.55 + easeOutBack(t) * 0.75);
      setOpacity(this.ring, 0.36 * (1 - t * 0.55));
    }

    const count = Math.max(1, this.marks.length);
    for (let i = 0; i < this.marks.length; i += 1) {
      const mark = this.marks[i];
      const sign = i % 2 === 0 ? 1 : -1;
      const angle = ((i / count) * Math.PI * 2) + seedPhase(this.visual.seed, i) + t * motion.spin * sign;
      const radius = flairOrbitRadius(this.visual.flair) * (0.72 + t * motion.expand);
      const lift = motion.lift * Math.sin(t * Math.PI + i * 0.7);
      mark.position.set(
        Math.cos(angle) * radius,
        0.62 + lift + t * motion.rise + (i % 3) * 0.12,
        Math.sin(angle) * radius,
      );
      mark.rotation.x += dt * (2.4 + i * 0.2);
      mark.rotation.y += dt * motion.spin * sign;
      mark.scale.setScalar(0.75 + Math.sin(t * Math.PI) * 0.55);
      setOpacity(mark, 0.7 * (1 - t * 0.72));
    }
  }
}

class AbilityContactFlairVfx extends Vfx {
  private marks: THREE.Mesh[] = [];
  private ring: THREE.Mesh | null = null;

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const accent = accentColor(this.visual, this.school);
    const root = new THREE.Group();
    const count = Math.max(5, flairParticleCount(this.visual.flair) + 1);

    this.ring = new THREE.Mesh(
      flairRingGeometry(this.visual.flair, 0.5),
      createVfxMaterial(accent, 0.58, THREE.DoubleSide),
    );
    this.ring.position.y = 1.08;
    this.ring.rotation.x = Math.PI / 2;
    root.add(this.ring);

    for (let i = 0; i < count; i += 1) {
      const mark = new THREE.Mesh(
        flairGlyphGeometry(this.visual.flair, i + 3),
        createVfxMaterial(i % 2 === 0 ? color : accent, 0.82, THREE.DoubleSide),
      );
      mark.position.y = 1.08;
      this.marks.push(mark);
      root.add(mark);
    }

    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    if (this.ring) {
      this.ring.rotation.z += dt * (5 + (this.visual.seed % 5));
      this.ring.scale.setScalar(0.3 + easeOutBack(t) * 1.75);
      setOpacity(this.ring, 0.62 * (1 - t));
    }

    const count = Math.max(1, this.marks.length);
    const burst = easeOutQuad(t);
    for (let i = 0; i < this.marks.length; i += 1) {
      const mark = this.marks[i];
      const angle = ((i / count) * Math.PI * 2) + seedPhase(this.visual.seed, i);
      const lift = Math.sin(t * Math.PI + i) * 0.35;
      const dist = 0.18 + burst * (0.75 + (i % 3) * 0.18);
      mark.position.set(
        Math.cos(angle) * dist,
        1.02 + lift + burst * 0.28,
        Math.sin(angle) * dist,
      );
      mark.rotation.x += dt * (4.5 + i * 0.2);
      mark.rotation.y += dt * (6 + i * 0.3);
      mark.scale.setScalar(0.5 + Math.sin(t * Math.PI) * 0.85);
      setOpacity(mark, 0.85 * (1 - t));
    }
  }
}

class AbilityProjectileVfx extends Vfx {
  private orb: THREE.Mesh | null = null;
  private trail: THREE.Mesh | null = null;
  private accent: THREE.Mesh | null = null;
  private light: THREE.PointLight | null = null;
  private tmpFrom = new THREE.Vector3();
  private tmpTo = new THREE.Vector3();
  private tmpPos = new THREE.Vector3();
  private dir = new THREE.Vector3();
  private side = new THREE.Vector3();
  private yAxis = new THREE.Vector3(0, 1, 0);
  private sparks: THREE.Mesh[] = [];

  constructor(
    private from: TargetProvider,
    private to: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    duration: number,
    startDelay: number,
  ) {
    super(from, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    this.orb = new THREE.Mesh(projectileGeometry(this.visual.projectile), createVfxMaterial(color, 0.95));
    this.trail = new THREE.Mesh(
      trailGeometry(this.visual.trail),
      createVfxMaterial(secondary, 0.42, THREE.DoubleSide),
    );
    this.trail.position.y = -0.28;
    this.accent = new THREE.Mesh(
      accentGeometry(this.visual.projectile),
      createVfxMaterial(secondary, 0.65, THREE.DoubleSide),
    );
    this.accent.position.y = 0.08;
    this.light = new THREE.PointLight(color, 1.4, 4);
    root.add(this.trail, this.orb, this.accent, this.light);

    const sparkCount = projectileFlairCount(this.visual.flair);
    for (let i = 0; i < sparkCount; i += 1) {
      const spark = new THREE.Mesh(
        flairGlyphGeometry(this.visual.flair, i + 9),
        createVfxMaterial(i % 2 === 0 ? secondary : color, 0.52, THREE.DoubleSide),
      );
      spark.scale.setScalar(0.45);
      this.sparks.push(spark);
      root.add(spark);
    }
    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    if (!this.root) return;
    this.from.getWorldPosition(this.tmpFrom);
    this.to.getWorldPosition(this.tmpTo);
    this.tmpFrom.y += 1.25;
    this.tmpTo.y += 1.15;
    this.tmpPos.lerpVectors(this.tmpFrom, this.tmpTo, easeOutQuad(t));
    this.dir.subVectors(this.tmpTo, this.tmpFrom);
    if (this.dir.lengthSq() < 0.000001) this.dir.copy(this.yAxis);
    else this.dir.normalize();
    this.side.crossVectors(this.dir, this.yAxis);
    if (this.side.lengthSq() < 0.000001) this.side.set(1, 0, 0);
    else this.side.normalize();
    const motion = flairMotion(this.visual.flair);
    const arc = Math.sin(t * Math.PI) * projectileArcHeight(this.visual.flair);
    const sway = Math.sin(t * Math.PI * 2 + seedPhase(this.visual.seed, 2)) * motion.sway;
    this.tmpPos.y += arc;
    this.tmpPos.addScaledVector(this.side, sway);
    this.root.position.copy(this.tmpPos);
    this.root.quaternion.setFromUnitVectors(this.yAxis, this.dir);
    const scale = 1 + Math.sin(t * Math.PI) * 0.35;
    this.root.scale.setScalar(scale);
    setOpacity(this.orb, 1 - Math.max(0, t - 0.82) / 0.18);
    setOpacity(this.trail, 0.42 * (1 - t * 0.25));
    if (this.accent) {
      this.accent.rotation.y += dt * (6 + (this.visual.seed % 5));
      setOpacity(this.accent, 0.65 * (1 - t * 0.35));
    }
    for (let i = 0; i < this.sparks.length; i += 1) {
      const spark = this.sparks[i];
      const angle = t * Math.PI * 8 + (i / Math.max(1, this.sparks.length)) * Math.PI * 2;
      const radius = 0.18 + (i % 2) * 0.05;
      spark.position.set(Math.cos(angle) * radius, -0.18 - i * 0.035, Math.sin(angle) * radius);
      spark.rotation.x += dt * (7 + i);
      spark.rotation.z += dt * (4 + i * 0.5);
      setOpacity(spark, 0.55 * (1 - t * 0.5));
    }
    if (this.light) this.light.intensity = 1.4 * (1 - t * 0.4);
  }
}

class AbilityBeamVfx extends Vfx {
  private beamGroup: THREE.Group | null = null;
  private beam: THREE.Mesh | null = null;
  private pulseRings: THREE.Mesh[] = [];
  private fromPos = new THREE.Vector3();
  private toPos = new THREE.Vector3();
  private mid = new THREE.Vector3();
  private dir = new THREE.Vector3();
  private yAxis = new THREE.Vector3(0, 1, 0);

  constructor(
    private from: TargetProvider,
    private to: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    duration: number,
    startDelay: number,
  ) {
    super(from, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    this.beamGroup = new THREE.Group();
    this.beam = new THREE.Mesh(
      beamGeometry(this.visual.trail),
      createVfxMaterial(this.visual.impact === 'rune' ? secondary : color, 0.8),
    );
    this.beamGroup.add(this.beam);

    const ringCount = beamPulseCount(this.visual.flair);
    for (let i = 0; i < ringCount; i += 1) {
      const ring = new THREE.Mesh(
        flairRingGeometry(this.visual.flair, 0.16 + i * 0.015),
        createVfxMaterial(i % 2 === 0 ? secondary : color, 0.46, THREE.DoubleSide),
      );
      ring.rotation.x = Math.PI / 2;
      this.pulseRings.push(ring);
      this.beamGroup.add(ring);
    }

    root.add(this.beamGroup);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    if (!this.root || !this.beam || !this.beamGroup) return;
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
    this.beamGroup.quaternion.setFromUnitVectors(this.yAxis, this.dir);
    const wave = Math.sin(Math.PI * Math.min(1, t));
    this.beam.scale.x = 0.85 + wave * 0.55;
    this.beam.scale.z = 0.85 + wave * 0.55;
    setOpacity(this.beam, wave * 0.85);
    for (let i = 0; i < this.pulseRings.length; i += 1) {
      const ring = this.pulseRings[i];
      const offsetT = (t + i / Math.max(1, this.pulseRings.length)) % 1;
      ring.position.y = -length / 2 + length * offsetT;
      ring.rotation.z += dt * (6 + i);
      const ringScale = 0.55 + Math.sin(offsetT * Math.PI) * 1.1;
      ring.scale.set(ringScale, ringScale, ringScale);
      setOpacity(ring, 0.58 * Math.sin(offsetT * Math.PI) * (1 - t * 0.2));
    }
  }
}

class AbilityImpactBurstVfx extends Vfx {
  private ring: THREE.Mesh | null = null;
  private core: THREE.Mesh | null = null;
  private shards: THREE.Mesh[] = [];
  private flairMarks: THREE.Mesh[] = [];

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    const mat = createVfxMaterial(color, 0.75, THREE.DoubleSide);
    this.ring = new THREE.Mesh(impactRingGeometry(this.visual.impact), mat.clone());
    this.ring.rotation.x = Math.PI / 2;
    this.core = new THREE.Mesh(impactCoreGeometry(this.visual.impact), createVfxMaterial(secondary, 0.68));
    const shardCount = impactShardCount(this.visual.impact);
    for (let i = 0; i < shardCount; i += 1) {
      const shard = new THREE.Mesh(
        new THREE.TetrahedronGeometry(0.055 + (i % 2) * 0.025, 0),
        createVfxMaterial(i % 2 === 0 ? color : secondary, 0.7),
      );
      const angle = (i / shardCount) * Math.PI * 2;
      shard.position.set(Math.cos(angle) * 0.22, 0.05, Math.sin(angle) * 0.22);
      this.shards.push(shard);
      root.add(shard);
    }
    const flairCount = Math.max(3, Math.floor(flairParticleCount(this.visual.flair) * 0.7));
    for (let i = 0; i < flairCount; i += 1) {
      const mark = new THREE.Mesh(
        flairGlyphGeometry(this.visual.flair, i + 17),
        createVfxMaterial(i % 2 === 0 ? secondary : color, 0.72, THREE.DoubleSide),
      );
      mark.position.y = 0.12;
      this.flairMarks.push(mark);
      root.add(mark);
    }
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
    for (let i = 0; i < this.shards.length; i += 1) {
      const shard = this.shards[i];
      const angle = (i / this.shards.length) * Math.PI * 2;
      const dist = 0.2 + this.radius * (0.25 + t * 0.72);
      shard.position.set(Math.cos(angle) * dist, 0.08 + t * 0.6, Math.sin(angle) * dist);
      shard.rotation.x += 0.12 + i * 0.01;
      shard.rotation.y += 0.18;
      setOpacity(shard, 0.72 * (1 - t));
    }
    const markCount = Math.max(1, this.flairMarks.length);
    for (let i = 0; i < this.flairMarks.length; i += 1) {
      const mark = this.flairMarks[i];
      const angle = (i / markCount) * Math.PI * 2 + seedPhase(this.visual.seed, i + 4);
      const dist = 0.12 + this.radius * (0.18 + t * 0.54);
      mark.position.set(Math.cos(angle) * dist, 0.18 + Math.sin(t * Math.PI) * 0.42, Math.sin(angle) * dist);
      mark.rotation.x += 0.22 + i * 0.02;
      mark.rotation.z += 0.16;
      mark.scale.setScalar(0.45 + Math.sin(t * Math.PI) * 0.85);
      setOpacity(mark, 0.78 * (1 - t));
    }
  }
}

class AbilityGroundPulseVfx extends Vfx {
  private ring: THREE.Mesh | null = null;
  private glow: THREE.Mesh | null = null;
  private spokes: THREE.Mesh[] = [];
  private motes: THREE.Mesh[] = [];

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    const mat = createVfxMaterial(color, 0.55, THREE.DoubleSide);
    this.ring = new THREE.Mesh(groundRingGeometry(this.visual.impact, this.radius), mat.clone());
    this.ring.rotation.x = Math.PI / 2;
    this.glow = new THREE.Mesh(new THREE.CircleGeometry(this.radius, 48), createVfxMaterial(secondary, 0.38, THREE.DoubleSide));
    this.glow.rotation.x = -Math.PI / 2;

    const spokeCount = Math.max(4, flairParticleCount(this.visual.flair));
    for (let i = 0; i < spokeCount; i += 1) {
      const spoke = new THREE.Mesh(
        new THREE.BoxGeometry(0.035, 0.025, this.radius * 0.86),
        createVfxMaterial(i % 2 === 0 ? color : secondary, 0.44, THREE.DoubleSide),
      );
      spoke.position.y = 0.045;
      spoke.rotation.y = (i / spokeCount) * Math.PI * 2;
      this.spokes.push(spoke);
      root.add(spoke);

      const mote = new THREE.Mesh(
        flairGlyphGeometry(this.visual.flair, i + 25),
        createVfxMaterial(i % 2 === 0 ? secondary : color, 0.62, THREE.DoubleSide),
      );
      mote.position.y = 0.22;
      this.motes.push(mote);
      root.add(mote);
    }

    root.add(this.glow, this.ring);
    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    const pulse = 0.94 + Math.sin(t * Math.PI * 3) * 0.06;
    if (this.ring) {
      this.ring.scale.setScalar(pulse);
      setOpacity(this.ring, 0.75 * (1 - t * 0.65));
    }
    if (this.glow) {
      this.glow.scale.setScalar(0.65 + t * 0.55);
      setOpacity(this.glow, 0.35 * (1 - t));
    }
    for (let i = 0; i < this.spokes.length; i += 1) {
      const spoke = this.spokes[i];
      spoke.rotation.y += dt * (0.7 + (this.visual.seed % 5) * 0.06);
      spoke.scale.z = 0.35 + easeOutQuad(t) * 0.95;
      setOpacity(spoke, 0.45 * (1 - t * 0.65));
    }
    const count = Math.max(1, this.motes.length);
    for (let i = 0; i < this.motes.length; i += 1) {
      const mote = this.motes[i];
      const angle = (i / count) * Math.PI * 2 + t * Math.PI * 1.25;
      const orbit = this.radius * (0.35 + 0.42 * Math.sin(t * Math.PI));
      mote.position.set(Math.cos(angle) * orbit, 0.22 + Math.sin(t * Math.PI + i) * 0.32, Math.sin(angle) * orbit);
      mote.rotation.x += dt * (2 + i * 0.2);
      mote.rotation.y += dt * (3 + i * 0.2);
      setOpacity(mote, 0.62 * (1 - t));
    }
  }
}

class AbilityMeleeArcVfx extends Vfx {
  private arc: THREE.Mesh | null = null;
  private echoes: THREE.Mesh[] = [];

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    this.arc = new THREE.Mesh(
      meleeArcGeometry(this.visual.motion, this.radius),
      createVfxMaterial(this.visual.trail === 'sparks' ? secondary : color, 0.75, THREE.DoubleSide),
    );
    this.arc.position.set(0, 1.05, 0.5);
    this.arc.rotation.set(Math.PI / 2, 0, -Math.PI * 0.58);
    root.add(this.arc);

    const echoCount = this.visual.motion === 'cleave' || this.visual.motion === 'leap' ? 3 : 2;
    for (let i = 0; i < echoCount; i += 1) {
      const echo = new THREE.Mesh(
        meleeArcGeometry(this.visual.motion, this.radius * (0.72 + i * 0.14)),
        createVfxMaterial(i % 2 === 0 ? secondary : color, 0.36, THREE.DoubleSide),
      );
      echo.position.set(0, 0.92 + i * 0.12, 0.46 + i * 0.08);
      echo.rotation.set(Math.PI / 2, 0, -Math.PI * (0.45 + i * 0.08));
      this.echoes.push(echo);
      root.add(echo);
    }
    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    if (!this.arc) return;
    this.arc.rotation.z = -Math.PI * 0.75 + t * Math.PI * 1.2;
    this.arc.scale.setScalar(0.75 + t * 0.55);
    setOpacity(this.arc, 0.75 * (1 - t));
    for (let i = 0; i < this.echoes.length; i += 1) {
      const echo = this.echoes[i];
      const offset = i * 0.11;
      echo.rotation.z = -Math.PI * (0.68 - offset) + t * Math.PI * (1.35 + offset);
      echo.rotation.y += dt * (0.8 + i * 0.35);
      echo.scale.setScalar(0.6 + t * (0.75 + i * 0.16));
      setOpacity(echo, 0.38 * (1 - Math.max(0, t - offset)));
    }
  }
}

class AbilityAuraVfx extends Vfx {
  private halo: THREE.Mesh | null = null;
  private markers: THREE.Mesh[] = [];

  constructor(
    target: TargetProvider,
    private school: AbilitySchool,
    private visual: AbilityVfxProfile,
    private radius: number,
    duration: number,
    startDelay: number,
  ) {
    super(target, duration, startDelay);
  }

  build(): THREE.Group {
    const color = primaryColor(this.visual, this.school);
    const secondary = secondaryColor(this.visual, this.school);
    const root = new THREE.Group();
    this.halo = new THREE.Mesh(
      auraGeometry(this.visual.cast, this.radius),
      createVfxMaterial(this.visual.cast === 'guard' ? secondary : color, 0.65, THREE.DoubleSide),
    );
    this.halo.position.y = 1.25;
    root.add(this.halo);

    const markerCount = Math.max(4, Math.floor(flairParticleCount(this.visual.flair) * 0.8));
    for (let i = 0; i < markerCount; i += 1) {
      const marker = new THREE.Mesh(
        flairGlyphGeometry(this.visual.flair, i + 33),
        createVfxMaterial(i % 2 === 0 ? secondary : color, 0.58, THREE.DoubleSide),
      );
      const angle = (i / markerCount) * Math.PI * 2;
      marker.position.set(Math.cos(angle) * this.radius * 0.72, 1.25, Math.sin(angle) * this.radius * 0.72);
      this.markers.push(marker);
      root.add(marker);
    }
    return prepareVfxRoot(root);
  }

  updateEffect(t: number, dt: number): void {
    if (!this.halo) return;
    this.halo.rotation.y += 0.08;
    this.halo.scale.setScalar(0.7 + t * 0.7);
    setOpacity(this.halo, 0.65 * (1 - t));
    const count = Math.max(1, this.markers.length);
    for (let i = 0; i < this.markers.length; i += 1) {
      const marker = this.markers[i];
      const angle = (i / count) * Math.PI * 2 + t * Math.PI * 1.6;
      const radius = this.radius * (0.58 + Math.sin(t * Math.PI) * 0.36);
      marker.position.set(Math.cos(angle) * radius, 1.05 + Math.sin(t * Math.PI + i) * 0.35, Math.sin(angle) * radius);
      marker.rotation.x += dt * (2.5 + i * 0.2);
      marker.rotation.y += dt * (3.2 + i * 0.2);
      marker.scale.setScalar(0.58 + Math.sin(t * Math.PI) * 0.6);
      setOpacity(marker, 0.62 * (1 - t));
    }
  }
}

function fallbackVfxProfile(
  id: string,
  school: AbilitySchool,
  shape: string,
): AbilityVfxProfile {
  const seed = hashString(id);
  const projectile: AbilityProjectileVfxKind =
    shape === 'projectile' ? (school === 'physical' ? 'arrow' : 'bolt') : 'none';
  return {
    cast: school === 'poison' ? 'venom' : school === 'holy' || school === 'rune' ? 'chant' : 'flare',
    projectile,
    impact: school === 'rune' ? 'rune' : school === 'poison' ? 'venom' : shape === 'area' ? 'quake' : 'burst',
    trail: school === 'fire' ? 'embers' : school === 'poison' ? 'venom' : school === 'shadow' ? 'smoke' : 'sparks',
    motion: shape === 'melee' ? 'cleave' : shape === 'dash' ? 'leap' : shape === 'area' ? 'slam' : 'weave',
    flair: 'neutral',
    colors: fallbackColorProfile(school),
    seed,
  };
}

interface FlairMotion {
  spin: number;
  expand: number;
  lift: number;
  rise: number;
  sway: number;
}

function flairMotion(flair: AbilityClassFlair): FlairMotion {
  switch (flair) {
    case 'doom_axes':
    case 'cleaver_frenzy':
    case 'blood_dance':
      return { spin: 8.5, expand: 1.15, lift: 0.42, rise: 0.42, sway: 0.24 };
    case 'siege_engine':
    case 'void_artillery':
      return { spin: 3.1, expand: 0.82, lift: 0.18, rise: 0.18, sway: 0.1 };
    case 'blade_kata':
    case 'veil_arrows':
    case 'aether_stars':
      return { spin: 6.6, expand: 0.95, lift: 0.36, rise: 0.34, sway: 0.32 };
    case 'bog_hex':
    case 'mutation':
    case 'crimson_siphon':
      return { spin: 4.7, expand: 1.05, lift: 0.46, rise: 0.5, sway: 0.38 };
    case 'sun_banner':
    case 'prelate_hymn':
    case 'glyph_script':
    case 'stone_oath':
      return { spin: 4.4, expand: 0.86, lift: 0.24, rise: 0.26, sway: 0.12 };
    default:
      return { spin: 5.4, expand: 0.92, lift: 0.28, rise: 0.28, sway: 0.18 };
  }
}

function flairOrbitRadius(flair: AbilityClassFlair): number {
  switch (flair) {
    case 'sun_banner':
    case 'dread_aura':
    case 'warbrute_plan':
      return 0.92;
    case 'siege_engine':
    case 'stone_oath':
      return 0.78;
    case 'blade_kata':
    case 'blood_dance':
    case 'cleaver_frenzy':
      return 0.66;
    default:
      return 0.74;
  }
}

function flairParticleCount(flair: AbilityClassFlair): number {
  switch (flair) {
    case 'glyph_script':
    case 'aether_stars':
    case 'ruin_rite':
    case 'dusk_weave':
      return 8;
    case 'doom_axes':
    case 'blood_dance':
    case 'fang_pack':
    case 'cleaver_frenzy':
      return 7;
    case 'siege_engine':
    case 'void_artillery':
    case 'stone_oath':
      return 5;
    default:
      return 6;
  }
}

function projectileFlairCount(flair: AbilityClassFlair): number {
  if (flair === 'siege_engine' || flair === 'void_artillery') return 2;
  if (flair === 'aether_stars' || flair === 'dusk_weave' || flair === 'bog_hex') return 5;
  if (flair === 'fang_pack' || flair === 'pride_beast') return 4;
  return 3;
}

function beamPulseCount(flair: AbilityClassFlair): number {
  if (flair === 'prelate_hymn' || flair === 'glyph_script' || flair === 'aether_stars') return 5;
  if (flair === 'siege_engine' || flair === 'void_artillery') return 3;
  return 4;
}

function projectileArcHeight(flair: AbilityClassFlair): number {
  switch (flair) {
    case 'siege_engine':
    case 'stone_oath':
    case 'void_artillery':
      return 0.08;
    case 'aether_stars':
    case 'ember':
    case 'dusk_weave':
      return 0.72;
    case 'bog_hex':
    case 'mutation':
    case 'fang_pack':
    case 'pride_beast':
      return 0.48;
    default:
      return 0.32;
  }
}

function seedPhase(seed: number, index: number): number {
  return (((seed >> ((index % 5) * 5)) & 31) / 31) * Math.PI * 2;
}

function flairAccentColor(flair: AbilityClassFlair, school: AbilitySchool): number {
  switch (flair) {
    case 'ember':
      return 0xfff06a;
    case 'inquisition':
      return 0xf2f0d0;
    case 'sun_banner':
    case 'prelate_hymn':
      return 0xffffff;
    case 'stone_oath':
    case 'glyph_script':
      return 0xcff6ff;
    case 'doom_axes':
    case 'warbrute_plan':
    case 'cleaver_frenzy':
      return 0xff4f38;
    case 'siege_engine':
    case 'void_artillery':
      return 0xffdd8a;
    case 'blade_kata':
    case 'aether_stars':
      return 0xe4fbff;
    case 'pride_beast':
    case 'fang_pack':
      return 0xfff1b0;
    case 'veil_arrows':
      return 0xd7dcff;
    case 'dread_aura':
    case 'mutation':
    case 'ruin_rite':
      return 0xff73d0;
    case 'bog_hex':
      return 0xc8ff57;
    case 'blood_dance':
    case 'dread_guard':
    case 'crimson_siphon':
      return 0xff6b84;
    case 'dusk_weave':
      return 0xbfa8ff;
    default:
      return secondaryColorForSchool(school);
  }
}

function flairRingGeometry(flair: AbilityClassFlair, radius: number): THREE.BufferGeometry {
  switch (flair) {
    case 'sun_banner':
    case 'warbrute_plan':
      return new THREE.TorusGeometry(radius, 0.018, 6, 4);
    case 'glyph_script':
    case 'stone_oath':
      return new THREE.TorusGeometry(radius, 0.014, 6, 28);
    case 'siege_engine':
    case 'void_artillery':
      return new THREE.TorusGeometry(radius, 0.024, 8, 8);
    case 'blood_dance':
    case 'cleaver_frenzy':
      return new THREE.TorusGeometry(radius, 0.018, 5, 18);
    default:
      return new THREE.TorusGeometry(radius, 0.016, 8, 32);
  }
}

function flairGlyphGeometry(flair: AbilityClassFlair, index: number): THREE.BufferGeometry {
  switch (flair) {
    case 'ember':
      return index % 2 === 0
        ? new THREE.ConeGeometry(0.05, 0.22, 5)
        : new THREE.TetrahedronGeometry(0.075, 0);
    case 'inquisition':
      return index % 2 === 0
        ? new THREE.BoxGeometry(0.045, 0.22, 0.045)
        : new THREE.ConeGeometry(0.06, 0.18, 4);
    case 'sun_banner':
      return index % 2 === 0
        ? new THREE.BoxGeometry(0.12, 0.2, 0.025)
        : new THREE.OctahedronGeometry(0.08, 0);
    case 'prelate_hymn':
      return index % 2 === 0
        ? new THREE.TorusGeometry(0.075, 0.009, 5, 14)
        : new THREE.OctahedronGeometry(0.07, 0);
    case 'stone_oath':
      return new THREE.BoxGeometry(0.13, 0.13, 0.07);
    case 'doom_axes':
    case 'cleaver_frenzy':
      return index % 2 === 0
        ? new THREE.ConeGeometry(0.055, 0.24, 3)
        : new THREE.BoxGeometry(0.16, 0.045, 0.055);
    case 'glyph_script':
      return new THREE.TorusGeometry(0.07, 0.008, 4, 16);
    case 'siege_engine':
    case 'void_artillery':
      return index % 2 === 0
        ? new THREE.BoxGeometry(0.16, 0.08, 0.08)
        : new THREE.SphereGeometry(0.07, 8, 6);
    case 'blade_kata':
    case 'blood_dance':
      return new THREE.ConeGeometry(0.045, 0.26, 4);
    case 'pride_beast':
    case 'fang_pack':
      return index % 2 === 0
        ? new THREE.ConeGeometry(0.05, 0.22, 3)
        : new THREE.TetrahedronGeometry(0.085, 0);
    case 'aether_stars':
      return new THREE.OctahedronGeometry(0.085, 0);
    case 'veil_arrows':
      return new THREE.ConeGeometry(0.045, 0.24, 5);
    case 'dread_aura':
    case 'mutation':
    case 'ruin_rite':
      return index % 2 === 0
        ? new THREE.IcosahedronGeometry(0.075, 0)
        : new THREE.TorusGeometry(0.065, 0.008, 5, 12);
    case 'bog_hex':
      return index % 2 === 0
        ? new THREE.SphereGeometry(0.075, 8, 6)
        : new THREE.ConeGeometry(0.055, 0.18, 6);
    case 'dread_guard':
      return new THREE.ConeGeometry(0.055, 0.24, 4);
    case 'dusk_weave':
      return new THREE.TetrahedronGeometry(0.09, 0);
    case 'crimson_siphon':
      return index % 2 === 0
        ? new THREE.SphereGeometry(0.07, 8, 6)
        : new THREE.ConeGeometry(0.05, 0.2, 5);
    default:
      return new THREE.OctahedronGeometry(0.075, 0);
  }
}

function projectileGeometry(kind: AbilityProjectileVfxKind): THREE.BufferGeometry {
  switch (kind) {
    case 'arrow':
    case 'knife':
    case 'shard':
      return new THREE.ConeGeometry(0.075, 0.42, 8);
    case 'bomb':
      return new THREE.SphereGeometry(0.16, 12, 8);
    case 'chain':
      return new THREE.BoxGeometry(0.09, 0.42, 0.09);
    case 'hammer':
      return new THREE.BoxGeometry(0.2, 0.28, 0.12);
    case 'rune':
      return new THREE.OctahedronGeometry(0.16, 0);
    case 'spirit':
      return new THREE.TetrahedronGeometry(0.18, 0);
    case 'venom':
      return new THREE.IcosahedronGeometry(0.13, 0);
    case 'ember':
    case 'bolt':
    default:
      return new THREE.SphereGeometry(0.13, 14, 10);
  }
}

function trailGeometry(kind: AbilityTrailVfxKind): THREE.BufferGeometry {
  switch (kind) {
    case 'spiral':
    case 'runes':
      return new THREE.TorusGeometry(0.12, 0.012, 6, 20);
    case 'smoke':
      return new THREE.ConeGeometry(0.13, 0.5, 10);
    case 'venom':
      return new THREE.CylinderGeometry(0.055, 0.015, 0.52, 8);
    case 'none':
      return new THREE.SphereGeometry(0.001, 4, 2);
    case 'embers':
    case 'sparks':
    default:
      return new THREE.CylinderGeometry(0.035, 0.006, 0.54, 8);
  }
}

function accentGeometry(kind: AbilityProjectileVfxKind): THREE.BufferGeometry {
  switch (kind) {
    case 'rune':
    case 'spirit':
      return new THREE.TorusGeometry(0.2, 0.01, 6, 24);
    case 'bomb':
      return new THREE.TorusGeometry(0.12, 0.014, 6, 16);
    case 'chain':
      return new THREE.BoxGeometry(0.16, 0.03, 0.16);
    case 'arrow':
    case 'knife':
      return new THREE.ConeGeometry(0.1, 0.16, 5);
    default:
      return new THREE.OctahedronGeometry(0.08, 0);
  }
}

function beamGeometry(trail: AbilityTrailVfxKind): THREE.BufferGeometry {
  if (trail === 'spiral' || trail === 'runes') return new THREE.CylinderGeometry(0.035, 0.11, 1, 12);
  if (trail === 'smoke') return new THREE.CylinderGeometry(0.075, 0.13, 1, 12);
  return new THREE.CylinderGeometry(0.045, 0.08, 1, 10);
}

function impactRingGeometry(kind: AbilityImpactVfxKind): THREE.BufferGeometry {
  switch (kind) {
    case 'cross':
      return new THREE.TorusGeometry(0.32, 0.018, 8, 32);
    case 'quake':
      return new THREE.TorusGeometry(0.48, 0.035, 8, 36);
    case 'rune':
      return new THREE.TorusGeometry(0.38, 0.016, 6, 30);
    case 'splash':
      return new THREE.TorusGeometry(0.34, 0.03, 8, 24);
    default:
      return new THREE.TorusGeometry(0.35, 0.025, 8, 28);
  }
}

function impactCoreGeometry(kind: AbilityImpactVfxKind): THREE.BufferGeometry {
  switch (kind) {
    case 'cross':
      return new THREE.OctahedronGeometry(0.2, 0);
    case 'quake':
      return new THREE.CylinderGeometry(0.2, 0.28, 0.08, 12);
    case 'rune':
      return new THREE.TorusGeometry(0.18, 0.012, 6, 22);
    case 'venom':
      return new THREE.IcosahedronGeometry(0.18, 0);
    case 'shatter':
      return new THREE.TetrahedronGeometry(0.2, 0);
    default:
      return new THREE.SphereGeometry(0.18, 12, 8);
  }
}

function impactShardCount(kind: AbilityImpactVfxKind): number {
  switch (kind) {
    case 'cross':
      return 4;
    case 'quake':
    case 'shatter':
      return 8;
    case 'rune':
      return 6;
    case 'venom':
      return 5;
    default:
      return 7;
  }
}

function groundRingGeometry(kind: AbilityImpactVfxKind, radius: number): THREE.BufferGeometry {
  const tube =
    kind === 'quake' ? 0.055 :
    kind === 'rune' ? 0.022 :
    0.035;
  return new THREE.TorusGeometry(radius, tube, 8, kind === 'rune' ? 36 : 48);
}

function meleeArcGeometry(motion: AbilityMotionKind, radius: number): THREE.BufferGeometry {
  const arc =
    motion === 'jab' ? Math.PI * 0.55 :
    motion === 'slam' ? Math.PI * 1.55 :
    Math.PI * 1.15;
  return new THREE.TorusGeometry(radius * 0.45, motion === 'slam' ? 0.04 : 0.025, 8, 28, arc);
}

function auraGeometry(cast: AbilityCastVfxKind, radius: number): THREE.BufferGeometry {
  if (cast === 'guard') return new THREE.TorusGeometry(radius * 0.78, 0.035, 8, 4);
  if (cast === 'ritual') return new THREE.TorusGeometry(radius * 1.06, 0.018, 6, 30);
  if (cast === 'venom') return new THREE.TorusGeometry(radius * 0.92, 0.022, 5, 24);
  return new THREE.TorusGeometry(radius, 0.025, 8, 36);
}

function primaryColor(visual: AbilityVfxProfile, school: AbilitySchool): number {
  return cssHexToNumber(visual.colors.primary, colorForSchool(school));
}

function secondaryColor(visual: AbilityVfxProfile, school: AbilitySchool): number {
  return cssHexToNumber(visual.colors.secondary, secondaryColorForSchool(school));
}

function accentColor(visual: AbilityVfxProfile, school: AbilitySchool): number {
  return cssHexToNumber(visual.colors.accent, flairAccentColor(visual.flair, school));
}

function fallbackColorProfile(school: AbilitySchool): AbilityColorProfile {
  return {
    primary: numberToCssHex(colorForSchool(school)),
    secondary: numberToCssHex(secondaryColorForSchool(school)),
    accent: numberToCssHex(flairAccentColor('neutral', school)),
    shadow: '#0a0805',
    glow: 'rgba(216, 210, 189, 0.28)',
  };
}

function cssHexToNumber(value: string | undefined, fallback: number): number {
  if (!value || !value.startsWith('#')) return fallback;
  const hex = value.slice(1);
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return fallback;
  return Number.parseInt(hex, 16);
}

function numberToCssHex(value: number): string {
  return `#${value.toString(16).padStart(6, '0')}`;
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

function secondaryColorForSchool(school: AbilitySchool): number {
  switch (school) {
    case 'fire':
      return 0xffd36a;
    case 'holy':
      return 0xffffff;
    case 'shadow':
      return 0xc8a4ff;
    case 'nature':
      return 0xd7ff9a;
    case 'arcane':
      return 0xd8fbff;
    case 'chaos':
      return 0xff73d0;
    case 'rune':
      return 0xf2fbff;
    case 'engineer':
      return 0xffedb8;
    case 'poison':
      return 0xd5ff7a;
    default:
      return 0xffffff;
  }
}

function hashString(value: string): number {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
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

function easeOutBack(t: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}
